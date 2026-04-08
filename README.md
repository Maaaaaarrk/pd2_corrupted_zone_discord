# PD2 Corrupted Zone Discord Alerts

**Get automatic Discord notifications when your favorite Corrupted Zones are active in Project Diablo 2.**

100% free. No server needed. No login required. Runs entirely on GitHub Actions.

> Zone data powered by [PD2 Corrupted Zone Tracker](https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz.html)

---

## How It Works

A GitHub Actions workflow runs every 5 minutes and:

1. Fetches the latest zone rotation data from [cz-data.js](https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz-data.js) (always in sync with the website)
2. Calculates the current Corrupted Zone using the same PRNG logic as the website
3. Checks if it matches your favorite zones or tags
4. Sends a rich Discord embed if it matches

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

The workflow will start running automatically every 5 minutes. You can also trigger it manually:

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
  "TAG_ZONES": ""
}
```

### Alert on Tagged Zones (EXP / MF)

Set `TAG_ZONES` to filter by the website's EXP and MF tags:

```json
{
  "FAVORITE_ZONES": "",
  "TAG_ZONES": "MF, EXP"
}
```

### Combine Both (Additive)

If both are set, you get alerts when **either** condition matches:

```json
{
  "FAVORITE_ZONES": "Chaos Sanctuary, Cow Level",
  "TAG_ZONES": "EXP"
}
```

This alerts on Chaos Sanctuary, Cow Level, **or** any zone tagged EXP.

### Alert on Every Zone

Leave both fields empty (the default):

```json
{
  "FAVORITE_ZONES": "",
  "TAG_ZONES": ""
}
```

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
> **Chaos Sanctuary** — Act 4  |  `MF`
>
> | Time Left | Next Zone |
> |-----------|-----------|
> | 11.3 minutes | Arreat Plateau, Crystalline Passage, and Frozen River (Act 5) |
>
> *PD2 Corrupted Zones - https://maaaaaarrk.github.io/Hiim-PD2-Resources/cz.html*

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

- Set `FAVORITE_ZONES` or `TAG_ZONES` in `config.json` to filter alerts.
- The workflow runs every 5 minutes but zones last 15 minutes, so you may get up to 3 alerts per zone. To reduce this, you can change the cron schedule in `.github/workflows/pd2-cz-alert.yml` to `'*/15 * * * *'`.

---

## Project Structure

```
.
├── .github/workflows/
│   └── pd2-cz-alert.yml      # GitHub Actions workflow (runs every 5 min)
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
