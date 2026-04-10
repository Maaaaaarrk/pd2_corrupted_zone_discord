# PD2 Corrupted Zone Discord Alerts

## Project Overview
GitHub Template Repository that sends Discord notifications when specific Corrupted Zones are active in Project Diablo 2. Runs entirely on GitHub Actions (no server needed).

## Architecture
- **Zone data**: Fetched live from `https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz-data.js` on every run to stay in sync with the website
- **Zone calculation**: PRNG-based (Linear Congruential Generator) — exact port of the JavaScript logic from cz.html
- **Scheduling**: GitHub Actions cron every 5 minutes
- **Notifications**: Discord webhooks with rich embeds

## Key Files
- `scripts/zone_calculator.py` — Core zone rotation logic (fetches cz-data.js, runs PRNG)
- `scripts/send_discord_alert.py` — Discord alert sender with config filtering
- `config.json` — User preferences (FAVORITE_ZONES, TAG_ZONES)
- `.github/workflows/pd2-cz-alert.yml` — GitHub Actions workflow

## Dependencies
- Python 3.12
- `requests` (only non-stdlib dependency)

## Configuration
- `DISCORD_WEBHOOK_URL` — Required GitHub Actions secret
- `config.json` — Optional zone/tag filters (empty = alert on all zones), plus PRE_WARNING_MINUTES for advance alerts

## Commands
- Test zone calculator: `python scripts/zone_calculator.py`
- Test full alert (needs DISCORD_WEBHOOK_URL env var): `python scripts/send_discord_alert.py`
