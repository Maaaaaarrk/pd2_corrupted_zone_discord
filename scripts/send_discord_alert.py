"""
PD2 Corrupted Zone → Discord Alert

Checks the current Corrupted Zone, compares it against the user's
FAVORITE_ZONES and TAG_ZONES config, and sends a rich Discord embed
if it matches (or if no filters are configured, alerts on every zone).

Optionally sends a pre-warning alert before a matching zone goes active
(configured via PRE_WARNING_MINUTES in config.json).
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from zone_calculator import get_current_corrupted_zone, get_zone, CYCLE_MS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
CZ_PAGE_URL = "https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz.html"
EMBED_COLOR = 0x9B59B6  # Purple
PRE_WARNING_COLOR = 0xF1C40F  # Gold/yellow for pre-warnings


def load_config() -> dict:
    """Load config.json if it exists."""
    if CONFIG_PATH.is_file():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def should_alert(zone_info: dict, config: dict) -> bool:
    """Decide whether to fire an alert for the current zone.

    Rules:
      - If neither FAVORITE_ZONES nor TAG_ZONES is set → always alert.
      - FAVORITE_ZONES: alert if the zone name contains any favorite (case-insensitive).
      - TAG_ZONES: alert if the zone has any matching tag.
      - If both are present, they are ADDITIVE (match either one).
    """
    fav_raw = config.get("FAVORITE_ZONES", "")
    tag_raw = config.get("TAG_ZONES", "")

    favorites = [z.strip().lower() for z in fav_raw.split(",") if z.strip()] if fav_raw else []
    tags = [t.strip().upper() for t in tag_raw.split(",") if t.strip()] if tag_raw else []

    # No filters → alert on everything
    if not favorites and not tags:
        return True

    zone_lower = zone_info["zone"].lower()
    zone_tags = [t.upper() for t in zone_info.get("tags", [])]

    # Favorite match (substring so "Chaos" matches "Chaos Sanctuary")
    if favorites and any(fav in zone_lower for fav in favorites):
        return True

    # Tag match
    if tags and any(t in zone_tags for t in tags):
        return True

    return False


def find_next_alert(zone_info: dict, config: dict) -> dict | None:
    """Scan future slots to find the next zone that would trigger an alert.

    Returns {"zone", "act", "tags", "timestamp"} or None.
    Only meaningful when filters are active.
    """
    zones = zone_info["zones"]
    zone_act = zone_info["zone_act"]
    exp_zones = zone_info["exp_zones"]
    mf_zones = zone_info["mf_zones"]
    now_ms = zone_info["now_ms"]
    current_ts = zone_info["current_ts"]

    def _tags(idx):
        tags = []
        if idx in exp_zones:
            tags.append("EXP")
        if idx in mf_zones:
            tags.append("MF")
        return tags

    # Scan up to 24 hours ahead (96 slots)
    for i in range(1, 97):
        future = get_zone(zones, zone_act, now_ms, offset=i)
        future_info = {
            "zone": future["zone"],
            "act": future["act"],
            "tags": _tags(future["idx"]),
        }
        if should_alert(future_info, config):
            # Unix timestamp (seconds) of when this slot starts
            future_ts = (current_ts + CYCLE_MS * i) // 1000
            return {
                "zone": future["zone"],
                "act": future["act"],
                "tags": _tags(future["idx"]),
                "timestamp": future_ts,
            }
    return None



def find_pre_warning_zones(zone_info: dict, config: dict) -> list[dict]:
    """Find upcoming zones within the PRE_WARNING_MINUTES window that match filters.

    Returns a list of dicts with zone info and timestamps for zones that:
      1. Start within PRE_WARNING_MINUTES from now
      2. Match the user's FAVORITE_ZONES / TAG_ZONES filters
      3. Are NOT the current zone (offset >= 1)
    """
    pre_warning_minutes = config.get("PRE_WARNING_MINUTES", 0)
    if not pre_warning_minutes or pre_warning_minutes <= 0:
        return []

    zones = zone_info["zones"]
    zone_act = zone_info["zone_act"]
    exp_zones = zone_info["exp_zones"]
    mf_zones = zone_info["mf_zones"]
    now_ms = zone_info["now_ms"]
    current_ts = zone_info["current_ts"]

    def _tags(idx):
        tags = []
        if idx in exp_zones:
            tags.append("EXP")
        if idx in mf_zones:
            tags.append("MF")
        return tags

    warning_window_ms = pre_warning_minutes * 60 * 1000
    results = []

    # Check future slots that start within the warning window
    max_slots = (pre_warning_minutes // 15) + 1
    for i in range(1, max_slots + 1):
        future = get_zone(zones, zone_act, now_ms, offset=i)
        future_start_ms = current_ts + CYCLE_MS * i
        time_until_ms = future_start_ms - now_ms

        if time_until_ms > warning_window_ms:
            break

        future_info = {
            "zone": future["zone"],
            "act": future["act"],
            "tags": _tags(future["idx"]),
        }

        if should_alert(future_info, config):
            results.append({
                "zone": future["zone"],
                "act": future["act"],
                "tags": _tags(future["idx"]),
                "timestamp": future_start_ms // 1000,
                "minutes_until": round(time_until_ms / 60_000, 1),
            })

    return results


def build_embed(zone_info: dict, config: dict) -> dict:
    """Build a Discord rich embed for the current Corrupted Zone."""
    tag_str = ""
    if zone_info["tags"]:
        tag_str = "  |  " + " ".join(f"`{t}`" for t in zone_info["tags"])

    next_tag_str = ""
    if zone_info["next_tags"]:
        next_tag_str = " " + " ".join(f"`{t}`" for t in zone_info["next_tags"])

    description = f"**{zone_info['zone']}** — Act {zone_info['act']}{tag_str}"

    fields = [
        {
            "name": "\u23f1\ufe0f Ends",
            "value": f"<t:{zone_info['slot_end_ts']}:R>",
            "inline": True,
        },
        {
            "name": "\u27a1\ufe0f Next Zone",
            "value": f"{zone_info['next_zone']} (Act {zone_info['next_act']}){next_tag_str}",
            "inline": True,
        },
    ]

    # Zone Returns — when this same zone comes back
    if zone_info.get("zone_returns_ts") is not None:
        fields.append({
            "name": "\U0001f504 Zone Returns",
            "value": f"<t:{zone_info['zone_returns_ts']}:f>\n<t:{zone_info['zone_returns_ts']}:R>",
            "inline": True,
        })

    # Next Alert — only shown when filters are active
    fav_raw = config.get("FAVORITE_ZONES", "")
    tag_raw = config.get("TAG_ZONES", "")
    has_filters = bool(fav_raw and fav_raw.strip()) or bool(tag_raw and tag_raw.strip())

    if has_filters:
        next_alert = find_next_alert(zone_info, config)
        if next_alert:
            na_tags = " ".join(f"`{t}`" for t in next_alert["tags"])
            na_tag_str = f"  {na_tags}" if na_tags else ""
            fields.append({
                "name": "\U0001f514 Next Favorite Zone",
                "value": f"{next_alert['zone']} (Act {next_alert['act']}){na_tag_str}\n<t:{next_alert['timestamp']}:f> (<t:{next_alert['timestamp']}:R>)",
                "inline": False,
            })

    embed = {
        "title": "\u2705 Corrupted Zone Active!",
        "description": description,
        "color": EMBED_COLOR,
        "fields": fields,
        "footer": {
            "text": f"PD2 Corrupted Zones \u2022 {CZ_PAGE_URL}",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return embed



def build_pre_warning_embed(upcoming_zone: dict) -> dict:
    """Build a Discord rich embed for an upcoming zone pre-warning."""
    tag_str = ""
    if upcoming_zone["tags"]:
        tag_str = "  |  " + " ".join(f"`{t}`" for t in upcoming_zone["tags"])

    description = f"**{upcoming_zone['zone']}** — Act {upcoming_zone['act']}{tag_str}"

    fields = [
        {
            "name": "🕒 Starts",
            "value": f"<t:{upcoming_zone['timestamp']}:R>",
            "inline": True,
        },
        {
            "name": "📅 Start Time",
            "value": f"<t:{upcoming_zone['timestamp']}:f>",
            "inline": True,
        },
    ]

    embed = {
        "title": "🔔 Corrupted Zone Coming Up!",
        "description": description,
        "color": PRE_WARNING_COLOR,
        "fields": fields,
        "footer": {
            "text": f"PD2 Corrupted Zones • {CZ_PAGE_URL}",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return embed


def send_alert(webhook_url: str, embed: dict) -> None:
    """POST the embed to the Discord webhook."""
    payload = {
        "embeds": [embed],
    }

    resp = requests.post(webhook_url, json=payload, timeout=15)
    resp.raise_for_status()
    print(f"Alert sent successfully (HTTP {resp.status_code})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL secret is not set.")
        print("Add it in: Repository Settings → Secrets and variables → Actions")
        sys.exit(1)

    # Get current zone info
    try:
        zone_info = get_current_corrupted_zone()
    except Exception as e:
        print(f"ERROR: Failed to calculate corrupted zone: {e}")
        sys.exit(1)

    tag_str = f" [{', '.join(zone_info['tags'])}]" if zone_info["tags"] else ""
    print(f"Current CZ: {zone_info['zone']} (Act {zone_info['act']}){tag_str}")
    print(f"  Time left: {zone_info['minutes_left']} min")
    print(f"  Next: {zone_info['next_zone']} (Act {zone_info['next_act']})")

    config = load_config()

    # --- Pre-warning alerts ---
    pre_warning_minutes = config.get("PRE_WARNING_MINUTES", 0)
    if pre_warning_minutes and pre_warning_minutes > 0:
        upcoming = find_pre_warning_zones(zone_info, config)
        for uz in upcoming:
            print(f"Pre-warning: {uz['zone']} (Act {uz['act']}) starts in {uz['minutes_until']} min")
            embed = build_pre_warning_embed(uz)
            try:
                send_alert(WEBHOOK_URL, embed)
            except requests.RequestException as e:
                print(f"ERROR: Failed to send pre-warning alert: {e}")
                sys.exit(1)

    # --- Current zone alert ---
    filter_alerts = config.get("FILTER_ALERTS", False)
    if filter_alerts and not should_alert(zone_info, config):
        print("Zone does not match favorites/tags — skipping alert.")
        return

    # Build and send
    embed = build_embed(zone_info, config)

    try:
        send_alert(WEBHOOK_URL, embed)
    except requests.RequestException as e:
        print(f"ERROR: Failed to send Discord alert: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
