# London Prayer Times (Unified) — Auto 7‑Day Feed

This repository generates a **7‑day London prayer timetable** as a single JSON file, sourced from the **London Unified Prayer Times** API, and keeps it updated automatically via **GitHub Actions**.

## What it does

- Fetches prayer times from `https://www.londonprayertimes.com/api/times/`
- Normalises the API response into a stable JSON shape for frontend/consumer apps
- Writes the output to:

```
london-prayer-times-unified-auto/data/london-prayer-times-7d.json
```

- A GitHub Actions workflow runs on a schedule (every 6 hours) and force-pushes updates to the branch:

```
release/london-prayer-times
```

## Repository layout

```
london-prayer-times-unified-auto/
  generate_london_prayer_times.py     # main generator script
  data/
    london-prayer-times-7d.json       # generated output (7 days)
  .github/workflows/
    update-london-prayer-times.yml    # scheduled automation
```

## Output format

The generator produces a JSON document with metadata plus a `days` array:

- `timezone`: always `Europe/London`
- `generated_at`: ISO timestamp (London time)
- `effective_today`: ISO date for the first day of the 7‑day window
- `days_count`: number of days (should be `7`)
- `days`: list of day entries, each containing:

| Key | Meaning |
|---|---|
| `date` | `YYYY-MM-DD` |
| `fajr` / `fajr_jamaah` | Fajr start / jama'ah |
| `sunrise` | Sunrise |
| `dhuhr` / `dhuhr_jamaah` | Dhuhr start / jama'ah |
| `asr` / `asr_hanafi` / `asr_jamaah` | Asr (standard) / Asr (Hanafi) / jama'ah |
| `maghrib` / `maghrib_jamaah` | Maghrib start / jama'ah |
| `isha` / `isha_jamaah` | Isha start / jama'ah |

Example (truncated):

```json
{
  "timezone": "Europe/London",
  "effective_today": "2026-02-24",
  "days_count": 7,
  "days": [
    {
      "date": "2026-02-24",
      "fajr": "05:17",
      "fajr_jamaah": "05:37",
      "sunrise": "06:54",
      "dhuhr": "12:19",
      "dhuhr_jamaah": "12:45",
      "asr": "14:58",
      "asr_hanafi": "15:41",
      "asr_jamaah": "16:00",
      "maghrib": "17:35",
      "maghrib_jamaah": "17:50",
      "isha": "19:03",
      "isha_jamaah": "19:45"
    }
  ]
}
```

## Running locally

### Requirements
- Python 3.10+ (uses `zoneinfo`)
- `requests`

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install requests
```

### Configure API key

Set an environment variable:

```bash
export LONDON_PRAYER_TIMES_API_KEY="YOUR_KEY_HERE"
```

> Note: the script contains a default key constant for convenience/testing, but for production you should always set `LONDON_PRAYER_TIMES_API_KEY` (and in GitHub Actions, store it in repository secrets).

### Generate the JSON

```bash
python london-prayer-times-unified-auto/generate_london_prayer_times.py
```

You should see output like:

```
Wrote .../data/london-prayer-times-7d.json (7 days)
```

## Automation (GitHub Actions)

Workflow file: `.github/workflows/update-london-prayer-times.yml`

- Runs on a cron schedule: '0 0 * * *' (every 24 hours at 12am)
- Also supports manual runs via **workflow_dispatch**
- Installs dependencies (`requests`, `ruff`)
- Lints the repo with Ruff
- Generates the JSON feed
- Commits and force-pushes the JSON to `release/london-prayer-times`

### Required secret

Create a GitHub Actions secret:

- `LONDON_PRAYER_TIMES_API_KEY`

## Linting / checks

If you want to run the same checks as CI:

```bash
pip install ruff
ruff check london-prayer-times-unified-auto
python -m py_compile london-prayer-times-unified-auto/generate_london_prayer_times.py
```

## Notes

- The generator always produces a rolling 7‑day window starting from **today in Europe/London**.
- If the API is missing any of the required dates, the script fails with a clear error message.

## License

Add a license file if you plan to publish/distribute this repo.
