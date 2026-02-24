#!/usr/bin/env python3
"""Generate a London 7-day prayer timetable JSON from London Unified Prayer Times."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URLS = (
    "https://www.londonprayertimes.com/api/times/",
    "https://londonprayertimes.com/api/times/",
)
DEFAULT_API_KEY = "2a99f189-6e3b-4015-8fb8-ff277642561d"
LONDON_TZ = ZoneInfo("Europe/London")
OUTPUT_PATH = Path(__file__).parent / "data" / "london-prayer-times-7d.json"
REQUEST_TIMEOUT_SECONDS = (10, 25)
MAX_NETWORK_ATTEMPTS = 3


class PrayerGenerationError(RuntimeError):
    """Raised when the prayer feed cannot be generated."""


def _api_key() -> str:
    value = os.getenv("LONDON_PRAYER_TIMES_API_KEY")
    if value and value.strip():
        return value.strip()

    return DEFAULT_API_KEY


def _build_session() -> Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        }
    )
    return session


def _fetch_month(session: Session, year: int, month: int, api_key: str) -> dict[str, dict[str, str]]:
    params = {
        "format": "json",
        "key": api_key,
        "24hours": "true",
        "year": str(year),
        "month": str(month),
    }

    last_error: Exception | None = None

    for attempt in range(1, MAX_NETWORK_ATTEMPTS + 1):
        for api_url in API_URLS:
            try:
                response = session.get(api_url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()

                payload = response.json()
                times = payload.get("times")

                if not isinstance(times, dict):
                    raise PrayerGenerationError(
                        f"API response for {year}-{month:02d} does not include a valid 'times' object"
                    )

                return times
            except Exception as error:  # noqa: BLE001
                last_error = error
                print(f"Attempt {attempt}/{MAX_NETWORK_ATTEMPTS} failed for {api_url} ({year}-{month:02d}): {error}")

    raise PrayerGenerationError(f"Failed to fetch data for {year}-{month:02d}: {last_error}")


def _load_existing_days() -> list[dict[str, str]]:
    if not OUTPUT_PATH.exists():
        return []

    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    days = payload.get("days")
    if not isinstance(days, list):
        return []

    result: list[dict[str, str]] = []
    for item in days:
        if isinstance(item, dict) and isinstance(item.get("date"), str):
            result.append(item)

    return result


def _dates_map(days: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    mapped: dict[str, dict[str, str]] = {}
    for day in days:
        date_key = day.get("date")
        if date_key:
            mapped[date_key] = day

    return mapped


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

    month_pairs = sorted({(value.year, value.month) for value in target_dates})
    combined_times: dict[str, dict[str, str]] = {}
    existing_days = _load_existing_days()
    existing_days_by_date = _dates_map(existing_days)
    session = _build_session()

    network_failed = False

    try:
        for year, month in month_pairs:
            combined_times.update(_fetch_month(session, year, month, key))
    except PrayerGenerationError as error:
        network_failed = True
        print(f"Network fetch failed, attempting stale fallback: {error}")
    finally:
        session.close()

    days: list[dict[str, str]] = []
    missing_dates: list[str] = []

    for date_obj in target_dates:
        date_key = date_obj.isoformat()
        day_data = combined_times.get(date_key)

        if not isinstance(day_data, dict):
            stale_day = existing_days_by_date.get(date_key)
            if isinstance(stale_day, dict):
                days.append(stale_day)
                continue

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
        "fallback_used": network_failed,
        "days": days,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(days)} days)")


if __name__ == "__main__":
    main()
