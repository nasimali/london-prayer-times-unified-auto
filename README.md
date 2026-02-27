# London Prayer Times (Unified) — Auto Feed

This repository generates **multiple London prayer timetables** (7‑day, yearly, and Ramadan) as JSON files, sourced from the **London Unified Prayer Times** API, and keeps them updated automatically via **GitHub Actions**.

## What it does

This repository generates **three separate prayer time feeds** from the London Unified Prayer Times API:

### 1. **7-Day Rolling Forecast** (Weekly)

- Fetches the next 7 days of prayer times
- Runs: **Dec 25-31 annually** (covers first week of new year)
- Output: `london-prayer-times-7d.json`
- Branch: `release/london-prayer-times`

### 2. **Full Year Calendar** (Yearly)

- Fetches all 365/366 days for the calendar year
- Runs: **Jan 1st at midnight UTC** (annually)
- Output: `london-prayer-times-1yr.json`
- Branch: `release/london-prayer-times-yearly`

### 3. **Ramadan Timetable** (Annual Islamic Month)

- Fetches prayer times for the entire Ramadan month
- Automatically calculates Islamic dates and Ramadan period
- Runs: **Jan 1st at 1am UTC** (annually)
- Output: `london-ramadan-times.json`
- Branch: `release/london-prayer-times-ramadan`

All feeds:

- Normalise API responses into stable JSON shapes for frontend/consumer apps
- Support manual triggering via GitHub Actions `workflow_dispatch`

## Repository layout

```
london-prayer-times-unified-auto/
  generate_london_prayer_times.py             # 7-day generator
  generate_london_prayer_times_1yr.py         # yearly generator
  generate_london_ramadan_times.py            # Ramadan generator
  data/
    london-prayer-times-7d.json               # 7-day output
    london-prayer-times-1yr.json              # yearly output
    london-ramadan-times.json                 # Ramadan output
  .github/workflows/
    update-weekly-london-prayer-times.yml     # 7-day automation
    update-yearly-london-prayer-times.yml     # yearly automation
    update-ramadan-london-prayer-times.yml    # Ramadan automation
```

## Output formats

### 7-Day Feed (`london-prayer-times-7d.json`)

JSON document with metadata plus a `days` array:

- `timezone`: always `Europe/London`
- `generated_at`: ISO timestamp (London time)
- `effective_today`: ISO date for the first day of the 7‑day window
- `days_count`: number of days (should be `7`)
- `days`: list of day entries, each containing:

| Key                                 | Meaning                                 |
| ----------------------------------- | --------------------------------------- |
| `date`                              | `YYYY-MM-DD`                            |
| `fajr` / `fajr_jamaah`              | Fajr start / jama'ah                    |
| `sunrise`                           | Sunrise                                 |
| `dhuhr` / `dhuhr_jamaah`            | Dhuhr start / jama'ah                   |
| `asr` / `asr_hanafi` / `asr_jamaah` | Asr (standard) / Asr (Hanafi) / jama'ah |
| `maghrib` / `maghrib_jamaah`        | Maghrib start / jama'ah                 |
| `isha` / `isha_jamaah`              | Isha start / jama'ah                    |

Example (truncated):

```json
{
  "timezone": "Europe/London",
  "generated_at": "2026-02-27T12:00:00+00:00",
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

### Yearly Feed (`london-prayer-times-1yr.json`)

Same structure as 7-day feed, but with all 365/366 days of the calendar year:

- `year`: the Gregorian calendar year
- `start_date`: `YYYY-01-01`
- `end_date`: `YYYY-12-31`
- `days_count`: must be `365` or `366`
- Prayer times same as 7-day format

### Ramadan Feed (`london-ramadan-times.json`)

Specialised format for the Islamic month of Ramadan:

- `ramadan_year`: the Gregorian calendar year when Ramadan occurs
- `start_date`: ISO date when Ramadan begins
- `end_date`: ISO date when Ramadan ends (30 days)
- `days_count`: `30` (Ramadan is always 30 days in this API)
- `days`: list of day entries, each containing:

| Key                  | Meaning                                    |
| -------------------- | ------------------------------------------ |
| `date`               | `YYYY-MM-DD`                               |
| `ramadan_day`        | Day number in Ramadan (1-30)               |
| `fajr`               | Fajr prayer time                           |
| `suhoor_end`         | Suhoor (pre-dawn meal) ends at Fajr time   |
| `dhuhr`              | Dhuhr prayer time                          |
| `asr` / `asr_hanafi` | Asr (standard) / Asr (Hanafi)              |
| `maghrib`            | Maghrib prayer time                        |
| `iftar`              | Iftar (meal to break fast) at Maghrib time |
| `isha`               | Isha prayer time                           |

Example (Ramadan 2026):

```json
{
  "timezone": "Europe/London",
  "generated_at": "2026-01-01T01:00:00+00:00",
  "ramadan_year": 2026,
  "start_date": "2026-02-18",
  "end_date": "2026-03-19",
  "days_count": 30,
  "days": [
    {
      "date": "2026-02-18",
      "ramadan_day": 1,
      "fajr": "05:29",
      "suhoor_end": "05:29",
      "dhuhr": "12:20",
      "asr": "14:50",
      "asr_hanafi": "15:31",
      "maghrib": "17:24",
      "iftar": "17:24",
      "isha": "18:53"
    }
  ]
}
```

## Running locally

### Requirements

- Python 3.10+ (uses `zoneinfo`)
- `requests` - for API calls
- `hijri-converter` - for Ramadan date calculations

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install requests hijri-converter
```

### Configure API key

Set an environment variable:

```bash
export LONDON_PRAYER_TIMES_API_KEY="YOUR_KEY_HERE"
```

> Note: the script contains a default key constant for convenience/testing, but for production you should always set `LONDON_PRAYER_TIMES_API_KEY` (and in GitHub Actions, store it in repository secrets).

### Generate the JSON files

**7-day feed:**

```bash
python london-prayer-times-unified-auto/generate_london_prayer_times.py
```

Output: `Wrote .../data/london-prayer-times-7d.json (7 days)`

**Yearly feed:**

```bash
python london-prayer-times-unified-auto/generate_london_prayer_times_1yr.py
```

Output: `Wrote .../data/london-prayer-times-1yr.json (365 days)`

**Ramadan feed:**

```bash
python london-prayer-times-unified-auto/generate_london_ramadan_times.py
```

Output: `Wrote .../data/london-ramadan-times.json (30 Ramadan days)`

## Automation (GitHub Actions)

Three independent workflows handle automatic generation and publishing:

### 1. Weekly Feed Workflow

**File:** `.github/workflows/update-weekly-london-prayer-times.yml`

- **Schedule:** `0 0 25-31 12 *` (Dec 25-31 each year at midnight UTC)
- **Purpose:** Ensures 7-day rolling forecast covers first week of new year
- **Output branch:** `release/london-prayer-times`
- **Output file:** `london-prayer-times-7d.json`

### 2. Yearly Feed Workflow

**File:** `.github/workflows/update-yearly-london-prayer-times.yml`

- **Schedule:** `0 0 1 1 *` (Jan 1st at midnight UTC each year)
- **Purpose:** Generates complete calendar year at new year
- **Output branch:** `release/london-prayer-times-yearly`
- **Output file:** `london-prayer-times-1yr.json`

### 3. Ramadan Feed Workflow

**File:** `.github/workflows/update-ramadan-london-prayer-times.yml`

- **Schedule:** `0 1 1 1 *` (Jan 1st at 1am UTC each year)
- **Purpose:** Generates Ramadan prayer times for the Islamic year
- **Output branch:** `release/london-prayer-times-ramadan`
- **Output file:** `london-ramadan-times.json`

**All workflows:**

- Support manual runs via **workflow_dispatch**
- Install dependencies (`requests`, `hijri-converter`, `ruff`)
- Lint the repo with Ruff
- Check Python syntax
- Generate their respective JSON feed
- Commit and force-push to their respective release branch

### Required secret

Create a GitHub Actions secret in your repository:

- `LONDON_PRAYER_TIMES_API_KEY` - Your London Prayer Times API key (all workflows use this)

## Linting / checks

If you want to run the same checks as CI:

```bash
pip install ruff
ruff check london-prayer-times-unified-auto
python -m py_compile london-prayer-times-unified-auto/generate_london_prayer_times.py
```

## Notes

- **7-day generator:** Produces a rolling window starting from **today in Europe/London**
- **Yearly generator:** Generates from Jan 1 to Dec 31 of the current calendar year
- **Ramadan generator:** Automatically calculates Ramadan dates using the Islamic calendar (Hijri)
- All generators fail with clear error messages if the API is missing required dates
- All generators respect the `LONDON_PRAYER_TIMES_API_KEY` environment variable (or use default API key for testing)

## License

Add a license file if you plan to publish/distribute this repo.
