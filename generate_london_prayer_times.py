#!/usr/bin/env python3
"""Generate a London 7-day prayer timetable JSON from London Unified Prayer Times."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://www.londonprayertimes.com/api/times/"
DEFAULT_API_KEY = "2a99f189-6e3b-4015-8fb8-ff277642561d"
LONDON_TZ = ZoneInfo("Europe/London")
OUTPUT_PATH = Path(__file__).parent / "data" / "london-prayer-times-7d.json"
REQUEST_TIMEOUT_SECONDS = 20


class PrayerGenerationError(RuntimeError):
    """Raised when the prayer feed cannot be generated."""


def _api_key() -> str:
    value = os.getenv("LONDON_PRAYER_TIMES_API_KEY")
    if value and value.strip():
        return value.strip()

    return DEFAULT_API_KEY


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


def _normalise_day(date_key: str, raw: dict[str, str]) -> dict[str, str]:
    # Keep keys explicit/consistent for frontend consumers.
    return {
        "date": date_key,
        "fajr": raw.get("fajr", ""),
        "fajr_jamaah": raw.get("fajr_jamat", ""),
        "sunrise": raw.get("sunrise", ""),
        "dhuhr": raw.get("dhuhr", ""),
        "dhuhr_jamaah": raw.get("dhuhr_jamat", ""),
        "asr": raw.get("asr", ""),
        "asr_hanafi": raw.get("asr_2", ""),
        "asr_jamaah": raw.get("asr_jamat", ""),
        "maghrib": raw.get("magrib", ""),
        "maghrib_jamaah": raw.get("magrib_jamat", ""),
        "isha": raw.get("isha", ""),
        "isha_jamaah": raw.get("isha_jamat", ""),
    }


def main() -> None:
    now_london = datetime.now(LONDON_TZ)
    today_london = now_london.date()
    target_dates = [today_london + timedelta(days=offset) for offset in range(7)]

    key = _api_key()
    if not key:
        raise PrayerGenerationError("Missing London Prayer Times API key")

    years_needed = sorted({value.year for value in target_dates})
    combined_times: dict[str, dict[str, str]] = {}

    for year in years_needed:
        combined_times.update(_fetch_year(year, key))

    days: list[dict[str, str]] = []
    missing_dates: list[str] = []

    for date_obj in target_dates:
        date_key = date_obj.isoformat()
        day_data = combined_times.get(date_key)

        if not isinstance(day_data, dict):
            missing_dates.append(date_key)
            continue

        days.append(_normalise_day(date_key, day_data))

    if missing_dates:
        missing_joined = ", ".join(missing_dates)
        raise PrayerGenerationError(f"Missing timetable data for dates: {missing_joined}")

    payload = {
        "source": {
            "name": "London Unified Prayer Times API",
            "url": "https://www.londonprayertimes.com/api",
        },
        "timezone": "Europe/London",
        "generated_at": now_london.isoformat(),
        "effective_today": today_london.isoformat(),
        "days_count": len(days),
        "days": days,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(days)} days)")


if __name__ == "__main__":
    main()
