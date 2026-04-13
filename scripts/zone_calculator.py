"""
PD2 Corrupted Zone Calculator

Determines the current and next Corrupted Zone using the exact same
PRNG rotation logic as:
    https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz.html

Zone data is fetched live from cz-data.js so this script never
goes out of sync with the website.

# =========================================================================
# HOW THE ROTATION WORKS
# =========================================================================
# - Each zone lasts exactly 15 minutes (900 000 ms).
# - A seed is derived from the current 15-min slot: floor(ts/900000) + floor(ts/86400000)
# - A Linear Congruential Generator (LCG) with multiplier 214013 and
#   increment 2531011 maps the seed to a zone index.
# - This is deterministic: the same timestamp always yields the same zone.
#
# UPDATE THIS when a new PD2 season changes the rotation:
#   The zone list, acts, and tags live in cz-data.js on the website.
#   If the PRNG constants or timing ever change, update CYCLE_MS,
#   LCG_MULTIPLIER, and LCG_INCREMENT below.
# =========================================================================
"""

import json
import math
import re
import time
from urllib.request import urlopen, Request

# ---------------------------------------------------------------------------
# Constants  (update if the website ever changes these)
# ---------------------------------------------------------------------------
CYCLE_MS = 900_000  # 15 minutes in milliseconds
LCG_MULTIPLIER = 214013
LCG_INCREMENT = 2531011
CZ_DATA_URL = "https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz-data.js"
LATENCY_TOLERANCE_MS = 120_000  # 2 minutes — snap to next slot if within this window

# ---------------------------------------------------------------------------
# Fetch zone data from the live cz-data.js
# ---------------------------------------------------------------------------

def fetch_zone_data() -> dict:
    """Fetch and parse cz-data.js from the website.

    Returns a dict with keys: zones, zoneAct, expZones, mfZones, redZones
    """
    req = Request(CZ_DATA_URL, headers={"User-Agent": "PD2-CZ-Discord-Bot/1.0"})
    with urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")

    # cz-data.js sets `window.czData = { ... };`
    # Extract the JSON object between the first { and last }
    match = re.search(r"\{[\s\S]+\}", raw)
    if not match:
        raise ValueError("Could not parse cz-data.js — format may have changed")

    return json.loads(match.group())


# ---------------------------------------------------------------------------
# PRNG — mirrors getNextPrng() from the website JS
# ---------------------------------------------------------------------------

def _lcg(seed: int, mul: int, inc: int) -> int:
    """Linear Congruential Generator matching the JS implementation:
        (((seed * mul + inc) >> 16) & 0x7FFF)
    Uses Python's arbitrary-precision ints so no BigInt issues.
    """
    return ((seed * mul + inc) >> 16) & 0x7FFF


# ---------------------------------------------------------------------------
# Core: get zone for a given timestamp (ms) + optional offset (# of slots)
# ---------------------------------------------------------------------------

def get_zone(zones: list, zone_act: list, ts_ms: int, offset: int = 0) -> dict:
    """Return the zone info for a given UTC timestamp in milliseconds.

    Exactly mirrors the JS function:
        getZone(ts, n) {
            ts = ~~(ts / 900e3) * 900e3;
            ts += 900e3 * n;
            var a = ~~(ts / 900000);
            var b = ~~(ts / 86400000);
            var seed = a + b;
            var idx = getNextPrng(seed, 214013, 2531011) % zones.length;
            ...
        }
    """
    # Snap to 15-min boundary and apply offset
    ts_ms = (ts_ms // CYCLE_MS) * CYCLE_MS
    ts_ms += CYCLE_MS * offset

    a = ts_ms // 900_000
    b = ts_ms // 86_400_000
    seed = a + b

    idx = _lcg(seed, LCG_MULTIPLIER, LCG_INCREMENT) % len(zones)

    return {
        "zone": zones[idx],
        "act": zone_act[idx],
        "ts": ts_ms,
        "seed": seed,
        "idx": idx,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_corrupted_zone() -> dict:
    """Return full info about the current and next corrupted zone.

    Returns:
        {
            "zone":          str   — current zone name,
            "act":           int   — act number (1-5),
            "tags":          list  — e.g. ["EXP"], ["MF"], ["RED"], or [],
            "minutes_left":  float — minutes remaining in current zone,
            "next_zone":     str   — name of the next zone,
            "next_act":      int   — act of the next zone,
            "next_tags":     list  — tags for the next zone,
            "zone_returns_offset": int — how many slots until this zone appears again,
            "zone_returns_minutes": float — minutes until this zone returns,
            "zones":         list  — full zone list (for lookahead searches),
            "zone_act":      list  — full act list,
            "exp_zones":     set   — indices tagged EXP,
            "mf_zones":      set   — indices tagged MF,
            "red_zones":     set   — indices tagged RED,
            "now_ms":        int   — current timestamp in ms,
        }
    """
    data = fetch_zone_data()
    zones = data["zones"]
    zone_act = data["zoneAct"]
    exp_zones = set(data.get("expZones", []))
    mf_zones = set(data.get("mfZones", []))
    red_zones = set(data.get("redZones", []))

    now_ms = int(time.time() * 1000)

    # Snap forward to the next slot boundary if within the latency tolerance.
    # This prevents cron jobs that fire slightly early from computing the
    # wrong (old) zone.  See GitHub issue #12.
    slot_start = (now_ms // CYCLE_MS) * CYCLE_MS
    next_slot_start = slot_start + CYCLE_MS
    if (next_slot_start - now_ms) <= LATENCY_TOLERANCE_MS:
        now_ms = next_slot_start

    current = get_zone(zones, zone_act, now_ms, offset=0)
    nxt = get_zone(zones, zone_act, now_ms, offset=1)

    # Time remaining: difference between the next slot boundary and now
    slot_end_ms = current["ts"] + CYCLE_MS
    minutes_left = round((slot_end_ms - now_ms) / 60_000, 1)

    def _tags(idx):
        tags = []
        if idx in exp_zones:
            tags.append("EXP")
        if idx in mf_zones:
            tags.append("MF")
        if idx in red_zones:
            tags.append("RED")
        return tags

    # Scan ahead to find when this zone returns (up to 24 hours = 96 slots)
    zone_returns_offset = None
    for i in range(2, 97):
        future = get_zone(zones, zone_act, now_ms, offset=i)
        if future["idx"] == current["idx"]:
            zone_returns_offset = i
            break

    zone_returns_ts = None
    if zone_returns_offset is not None:
        # Unix timestamp (seconds) of when this zone returns
        zone_returns_ts = (current["ts"] + CYCLE_MS * zone_returns_offset) // 1000

    # Unix timestamp (seconds) of when the current zone ends
    slot_end_ts = slot_end_ms // 1000

    return {
        "zone": current["zone"],
        "act": current["act"],
        "tags": _tags(current["idx"]),
        "minutes_left": minutes_left,
        "slot_end_ts": slot_end_ts,
        "next_zone": nxt["zone"],
        "next_act": nxt["act"],
        "next_tags": _tags(nxt["idx"]),
        "zone_returns_offset": zone_returns_offset,
        "zone_returns_ts": zone_returns_ts,
        # Pass through for lookahead searches in the alert script
        "zones": zones,
        "zone_act": zone_act,
        "exp_zones": exp_zones,
        "mf_zones": mf_zones,
        "red_zones": red_zones,
        "now_ms": now_ms,
        "current_ts": current["ts"],
    }


# Quick test when run directly
if __name__ == "__main__":
    info = get_current_corrupted_zone()
    tag_str = f" [{', '.join(info['tags'])}]" if info["tags"] else ""
    print(f"Current CZ: {info['zone']} (Act {info['act']}){tag_str}")
    print(f"  Time left: {info['minutes_left']} min")
    next_tag_str = f" [{', '.join(info['next_tags'])}]" if info["next_tags"] else ""
    print(f"  Next up:   {info['next_zone']} (Act {info['next_act']}){next_tag_str}")
