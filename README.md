# PD2 Corrupted Zone Discord Alerts

**Get automatic Discord notifications when your favorite Corrupted Zones are active in Project Diablo 2.**

100% free. No server needed. No login required. Runs entirely on GitHub Actions.

> Zone data powered by [PD2 Corrupted Zone Tracker](https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz.html)

---

## How It Works

A GitHub Actions workflow runs every 15 minutes and:

1. Fetches the latest zone rotation data from [cz-data.js](https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz-data.js) (always in sync with the website)
2. Calculates the current Corrupted Zone using the same PRNG logic as the website
3. Checks if it matches your favorite zones or tags (if `FILTER_ALERTS` is enabled)
4. Sends a rich Discord embed with zone info, time remaining, when the zone returns, and your next favorite zone

---

## Setup Guide

### Step 1: Create Your Own Copy

1. Click the green **"Use this template"** button at the top of this repo
2. Choose **"Create a new repository"**
3. Name it whatever you like (e.g. `my-pd2-alerts`)
4. Set it to **Private** (recommended — your webhook URL is in secrets, but private is safer)
5. Click **"Create repository"**

> **Note for repo owners**: To enable the "Use this template" button, go to repository **Settings** and check **"Template repository"** under the repository name.

### Step 2: Create a Discord Webhook

1. Open your Discord server
2. Go to **Server Settings** → **Integrations** → **Webhooks**
3. Click **"New Webhook"**
4. Give it a name (e.g. `PD2 CZ Alerts`)
5. Choose which **channel** should receive the alerts
6. Click **"Copy Webhook URL"** — save this, you'll need it next

### Step 3: Add Your Webhook as a GitHub Secret

1. In **your new repo**, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"**
3. Name: `DISCORD_WEBHOOK_URL`
4. Value: paste the webhook URL you copied from Discord
5. Click **"Add secret"**

### Step 4: Done!

The workflow will start running automatically every 15 minutes (at :00, :15, :30, :45). You can also trigger it manually:

1. Go to the **Actions** tab in your repo
2. Click **"PD2 Corrupted Zone Alert"** in the left sidebar
3. Click **"Run workflow"** → **"Run workflow"**

---

## Customizing Your Alerts

Edit `config.json` in the root of your repo to filter which zones trigger alerts.

### Alert on Specific Zones

Set `FAVORITE_ZONES` to a comma-separated list of zone names (partial matches work):

```json
{
  "FAVORITE_ZONES": "Chaos Sanctuary, Durance of Hate, Travincal",
  "TAG_ZONES": "",
  "FILTER_ALERTS": true
}
```

### Alert on Tagged Zones (TOP / GOOD)

Set `TAG_ZONES` to filter by the website's TOP and GOOD tags:

```json
{
  "FAVORITE_ZONES": "",
  "TAG_ZONES": "TOP, GOOD",
  "FILTER_ALERTS": true
}
```

### Combine Both (Additive)

If both are set, you get alerts when **either** condition matches:

```json
{
  "FAVORITE_ZONES": "Chaos Sanctuary, Cow Level",
  "TAG_ZONES": "TOP",
  "FILTER_ALERTS": true
}
```

This alerts on Chaos Sanctuary, Cow Level, **or** any zone tagged TOP.

### Pre-Warning for Upcoming Zones

Want a heads-up *before* your favorite zone goes live? This requires changes in **two places**: `config.json` and the GitHub Actions workflow cron schedule.

#### Step 1: Set `PRE_WARNING_MINUTES` in `config.json`

Set the lookahead window to the number of minutes before a zone rotation you want to be notified:

```json
{
  "FAVORITE_ZONES": "Chaos Sanctuary, Cow Level",
  "TAG_ZONES": "TOP",
  "FILTER_ALERTS": true,
  "PRE_WARNING_MINUTES": 5
}
```

This tells the bot to send an orange "Corrupted Zone Incoming!" alert whenever a zone matching your favorites or tags is starting within the next 5 minutes.

#### Step 2: Adjust the cron schedule in the workflow

The default cron schedule runs every 15 minutes at `:00`, `:15`, `:30`, `:45` -- exactly when each zone rotation starts. For pre-warnings to fire, the workflow **must also run before** the rotation so the bot can detect the upcoming zone.

Edit `.github/workflows/pd2-cz-alert.yml` and add run times that match your `PRE_WARNING_MINUTES` value. For example, for a **5-minute** pre-warning, add runs at 5 minutes before each rotation (`:10`, `:25`, `:40`, `:55`):

```yaml
on:
  schedule:
    # Zone rotations happen at :00, :15, :30, :45
    # Pre-warnings need an extra run N minutes before each rotation
    - cron: '0,10,15,25,30,40,45,55 * * * *'  # every 15 min + 5 min before
```

For a **10-minute** pre-warning:

```yaml
on:
  schedule:
    - cron: '0,5,15,20,30,35,45,50 * * * *'   # every 15 min + 10 min before
```

> **Important:** If `PRE_WARNING_MINUTES` is set but the cron only runs at `:00/:15/:30/:45`, the pre-warning check will never find an upcoming zone within the window because the bot only runs at the exact moment zones rotate. The cron schedule and the config value must be aligned.

**How it works:**
- Pre-warnings are only sent when `FILTER_ALERTS` is `true` (otherwise you already get notified for every zone).
- The value is the lookahead window in minutes. Common values: `5` (5 min heads-up), `10`, or `15` (one full rotation ahead).
- Set to `0` (the default) to disable pre-warnings.
- Pre-warnings are sent *in addition to* the normal "Corrupted Zone Active!" alert when the zone actually starts.
- The built-in debounce step ensures duplicate alerts are not sent if the workflow runs multiple times in the same 15-minute window.

### Alert on Every Zone (Default)

Set `FILTER_ALERTS` to `false` (or leave it out). You'll get an alert for every zone rotation, but the embed will still show your **Next Favorite Zone** based on your favorites/tags:

```json
{
  "FAVORITE_ZONES": "Chaos Sanctuary",
  "TAG_ZONES": "TOP",
  "FILTER_ALERTS": false,
  "PRE_WARNING_MINUTES": 0
}
```

### Config Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `FAVORITE_ZONES` | string | `""` | Comma-separated zone names (partial match, e.g. `"Chaos"` matches `"Chaos Sanctuary"`) |
| `TAG_ZONES` | string | `""` | Comma-separated tags: `"TOP"`, `"GOOD"`, or any combination like `"TOP, GOOD"` |
| `FILTER_ALERTS` | boolean | `false` | `true` = only alert on matching zones. `false` = alert on every zone |
| `PRE_WARNING_MINUTES` | number | `0` | Lookahead window in minutes. When `> 0` and `FILTER_ALERTS` is `true`, sends an early "incoming" alert for matching zones about to start. Set to `15` for one rotation ahead, `30` for two, etc. `0` = disabled |

---

## Updating for a New Season

When a new PD2 season starts and the zone rotation changes:

**You don't need to do anything!** The zone list is fetched live from `cz-data.js` on every run, so it stays in sync with the website automatically.

If the rotation *timing* or *algorithm* changes (rare), update the constants at the top of `scripts/zone_calculator.py`:

```python
CYCLE_MS = 900_000        # 15 minutes per zone
LCG_MULTIPLIER = 214013   # PRNG multiplier
LCG_INCREMENT = 2531011   # PRNG increment
```

---

## What the Alert Looks Like

You'll get a Discord embed like this:

> **Corrupted Zone Active!**
>
> **Chaos Sanctuary** — Act 4  |  `TOP`
>
> **Ends:** *in 12 minutes*
> **Next Zone:** Arreat Plateau, Crystalline Passage, and Frozen River (Act 5)
> **Zone Returns:** April 8, 2026 4:15 PM (*in 8 hours*)
> **Next Favorite Zone:** Durance of Hate (Act 3) — April 8, 2026 6:30 PM (*in 10 hours*)
>
> *PD2 Corrupted Zones - https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz.html*

All timestamps use Discord's native formatting, so they automatically display in each user's local timezone and count down in real time.

---

## Troubleshooting

### Alerts aren't sending

1. **Check the Actions tab** — look for failed workflow runs and read the error logs
2. **Verify your secret** — go to Settings → Secrets → make sure `DISCORD_WEBHOOK_URL` is set
3. **Test the webhook** — try the manual "Run workflow" button in the Actions tab
4. **Check your Discord channel** — make sure the webhook channel still exists and the webhook hasn't been deleted

### Wrong zone is showing

The zone calculation mirrors the website exactly. If they don't match:
1. Check your system clock / timezone — the calculation uses UTC
2. Make sure `cz-data.js` is accessible (try opening it in a browser)
3. If the website itself changed its logic, open an issue

### Workflow isn't running

- GitHub may delay or skip scheduled workflows on **inactive repos** (no commits in 60 days). Push a small commit to re-activate.
- Make sure GitHub Actions is enabled: go to **Settings** → **Actions** → **General** → allow actions to run.

### Too many notifications

- Set `FILTER_ALERTS` to `true` in `config.json` and configure `FAVORITE_ZONES` or `TAG_ZONES` to only get alerts for zones you care about.

---

## Project Structure

```
.
├── .github/workflows/
│   └── pd2-cz-alert.yml      # GitHub Actions workflow (runs every 15 min)
├── scripts/
│   ├── zone_calculator.py     # Core zone rotation logic (fetches cz-data.js)
│   └── send_discord_alert.py  # Discord webhook sender
├── config.json                # Your alert preferences (favorite zones / tags)
├── .env.example               # Example environment variables
└── README.md
```

---

## Credits

- Zone rotation data and tracker: [PD2 Corrupted Zone Tracker](https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz.html)
- [Project Diablo 2](https://www.projectdiablo2.com/)

---

## License

MIT — use it, fork it, share it.
