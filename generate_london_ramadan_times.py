#!/usr/bin/env python3
"""Generate a Ramadan prayer timetable JSON from London Unified Prayer Times."""

from __future__ import annotations

import json
import os
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_URL = "https://www.londonprayertimes.com/api/times/"
LONDON_TZ = ZoneInfo("Europe/London")
OUTPUT_PATH = Path(__file__).parent / "data" / "london-ramadan-times.json"
REQUEST_TIMEOUT_SECONDS = 20


class PrayerGenerationError(RuntimeError):
    """Raised when the prayer feed cannot be generated."""


def _api_key() -> str:
    api_key = os.getenv("LONDON_PRAYER_TIMES_API_KEY", "").strip()
    if not api_key:
        raise PrayerGenerationError("LONDON_PRAYER_TIMES_API_KEY environment variable is not set. Please set it in .env or export it.")
    return api_key


def _fetch_year(year: int, api_key: str) -> dict[str, dict[str, str]]:
    params = {
        "format": "json",
        "key": api_key,
        "24hours": "true",
        "year": str(year),
    }

    response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    payload = response.json()
    times = payload.get("times")

    if not isinstance(times, dict):
        raise PrayerGenerationError(f"API response for year {year} does not include a valid 'times' object")

    return times


def _is_ramadan_date(gregorian_date: date) -> bool:
    """Check if a Gregorian date falls within Ramadan (9th Islamic month)."""
    try:
        from hijri_converter import Gregorian
        hijri = Gregorian(gregorian_date.year, gregorian_date.month, gregorian_date.day).to_hijri()
        # Ramadan is the 9th month (return True if month is 9)
        return hijri.month == 9
    except ImportError:
        raise PrayerGenerationError("hijri-converter library is required. Install with: pip install hijri-converter")


def _get_ramadan_range(year: int) -> tuple[date, date]:
    """Get the start and end dates of Ramadan for the given Gregorian year."""
    try:
        from hijri_converter import Hijri
    except ImportError:
        raise PrayerGenerationError("hijri-converter library is required. Install with: pip install hijri-converter")

    # Find which Islamic year corresponds to this Gregorian year
    # We'll search for the 9th month (Ramadan) that falls mostly in this Gregorian year
    for hijri_year in range(1440, 1460):  # reasonable range for 2018-2038
        ramadan_1st = Hijri(hijri_year, 9, 1).to_gregorian()
        if ramadan_1st.year == year or (ramadan_1st.year == year - 1 and ramadan_1st.month == 12):
            # Found Ramadan for this year
            ramadan_start = ramadan_1st
            # Ramadan has 29 or 30 days, estimate end
            try:
                ramadan_end = Hijri(hijri_year, 9, 30).to_gregorian()
                # If it rolls into next year, use that year's date
                return (ramadan_start, ramadan_end)
            except:
                # If 30th doesn't work, try 29th
                ramadan_end = Hijri(hijri_year, 9, 29).to_gregorian()
                return (ramadan_start, ramadan_end)

    raise PrayerGenerationError(f"Could not determine Ramadan dates for year {year}")


def _normalise_ramadan_day(date_key: str, raw: dict[str, str], ramadan_day: int) -> dict[str, str]:
    """Normalize a day during Ramadan with prayer times including suhoor and iftar."""
    return {
        "date": date_key,
        "ramadan_day": ramadan_day,
        "fajr": raw.get("fajr", ""),
        "suhoor_end": raw.get("fajr", ""),  # Suhoor ends at Fajr time
        "sunrise": raw.get("sunrise", ""),
        "dhuhr": raw.get("dhuhr", ""),
        "asr": raw.get("asr", ""),
        "asr_hanafi": raw.get("asr_2", ""),
        "maghrib": raw.get("magrib", ""),
        "iftar": raw.get("magrib", ""),  # Iftar is at Maghrib time
        "isha": raw.get("isha", ""),
    }


def main() -> None:
    now_london = datetime.now(LONDON_TZ)
    current_year = now_london.year

    key = _api_key()
    if not key:
        raise PrayerGenerationError("Missing London Prayer Times API key")

    # Determine Ramadan date range
    try:
        ramadan_start, ramadan_end = _get_ramadan_range(current_year)
    except PrayerGenerationError:
        # Try previous or next year if not found
        try:
            ramadan_start, ramadan_end = _get_ramadan_range(current_year + 1)
        except PrayerGenerationError:
            ramadan_start, ramadan_end = _get_ramadan_range(current_year - 1)

    # Fetch prayer times for relevant years
    years_needed = sorted({ramadan_start.year, ramadan_end.year})
    combined_times: dict[str, dict[str, str]] = {}

    for year in years_needed:
        combined_times.update(_fetch_year(year, key))

    # Build list of Ramadan days
    days: list[dict[str, str]] = []
    missing_dates: list[str] = []
    ramadan_day = 1
    current_date = ramadan_start

    while current_date <= ramadan_end:
        date_key = current_date.isoformat()
        day_data = combined_times.get(date_key)

        if not isinstance(day_data, dict):
            missing_dates.append(date_key)
            current_date = date(current_date.year, current_date.month, current_date.day + 1) if current_date.day < 28 else date(current_date.year, current_date.month + 1, 1)
            ramadan_day += 1
            continue

        days.append(_normalise_ramadan_day(date_key, day_data, ramadan_day))
        ramadan_day += 1

        # Move to next day
        if current_date.month == 12 and current_date.day == 31:
            current_date = date(current_date.year + 1, 1, 1)
        elif current_date.day == 28 and current_date.month == 2:
            current_date = date(current_date.year, 3, 1)
        else:
            try:
                current_date = date(current_date.year, current_date.month, current_date.day + 1)
            except ValueError:
                current_date = date(current_date.year, current_date.month + 1, 1)

    if missing_dates:
        missing_joined = ", ".join(missing_dates[:5])  # Show first 5
        raise PrayerGenerationError(f"Missing timetable data for dates: {missing_joined}")

    payload = {
        "source": {
            "name": "London Unified Prayer Times API",
            "url": "https://www.londonprayertimes.com/api",
        },
        "timezone": "Europe/London",
        "generated_at": now_london.isoformat(),
        "ramadan_year": current_year,
        "start_date": ramadan_start.isoformat(),
        "end_date": ramadan_end.isoformat(),
        "days_count": len(days),
        "days": days,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(days)} Ramadan days)")


if __name__ == "__main__":
    main()
