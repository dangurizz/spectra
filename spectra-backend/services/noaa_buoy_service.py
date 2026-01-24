from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import requests

from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

HISTORICAL_URL = (
    "https://www.ndbc.noaa.gov/view_text_file.php"
    "?filename={station_id}h{year}.txt.gz&dir=data/historical/stdmet/"
)
REALTIME_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"

MISSING_VALUES = {
    "MM",
    "99",
    "99.0",
    "999",
    "999.0",
    "9999",
    "9999.0",
    "99999",
    "99999.0",
}


def _parse_float(value: str) -> Optional[float]:
    if value in MISSING_VALUES:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _normalize_year(year: int) -> int:
    if year < 100:
        return 2000 + year if year < 70 else 1900 + year
    return year


def _parse_timestamp(fields: Dict[str, str]) -> Optional[datetime]:
    try:
        year_key = "YY" if "YY" in fields else "YYYY" if "YYYY" in fields else None
        if not year_key:
            return None
        year = _normalize_year(int(fields[year_key]))
        month = int(fields["MM"])
        day = int(fields["DD"])
        hour = int(fields["hh"])
        minute = int(fields["mm"])
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    except (KeyError, ValueError):
        return None


def _select_period(fields: Dict[str, str]) -> Optional[float]:
    if "DPD" in fields:
        value = _parse_float(fields["DPD"])
        if value is not None:
            return value
    if "APD" in fields:
        return _parse_float(fields["APD"])
    return None


def _fetch_lines(url: str) -> Optional[list[str]]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("NOAA request failed for %s: %s", url, exc)
        return None

    lines = response.text.strip().splitlines()
    if not lines:
        logger.info("NOAA response empty for %s", url)
        return None
    return lines


def _find_best_row(lines: list[str], timestamp: datetime) -> Optional[Dict[str, str]]:
    header = None
    for line in lines:
        if line.startswith("#"):
            header = line.lstrip("#").split()
            break
    if not header:
        logger.debug("No header found in NOAA response")
        return None
    logger.debug("NOAA header: %s", header)

    best_row = None
    best_diff = None
    first_ts_logged = False

    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < len(header):
            continue
        row = dict(zip(header, parts))
        row_timestamp = _parse_timestamp(row)
        if row_timestamp is None:
            continue
        if not first_ts_logged:
            logger.debug("First data row timestamp: %s (target: %s)", row_timestamp.isoformat(), timestamp.isoformat())
            first_ts_logged = True
        diff_seconds = abs((row_timestamp - timestamp).total_seconds())
        if diff_seconds <= 3600 and (best_diff is None or diff_seconds < best_diff):
            best_diff = diff_seconds
            best_row = row

    if best_row and best_diff is not None:
        logger.debug("Best match diff: %.0f seconds", best_diff)

    return best_row


def get_buoy_data(station_id: str, timestamp: datetime) -> Optional[dict]:
    """
    Fetch NOAA NDBC buoy data for a specific station and timestamp.

    Args:
        station_id: NOAA station ID (e.g., "46224" for Point Reyes)
        timestamp: UTC timestamp for which to fetch data

    Returns:
        dict with wave_height, wave_period, wave_direction, water_temp
        or None if data unavailable
    """
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=45)
    if timestamp >= recent_cutoff:
        # For recent timestamps, try realtime first (more reliable for current data)
        sources = [
            ("realtime", REALTIME_URL.format(station_id=station_id)),
            ("historical", HISTORICAL_URL.format(station_id=station_id, year=timestamp.year)),
        ]
    else:
        sources = [("historical", HISTORICAL_URL.format(station_id=station_id, year=timestamp.year))]

    for label, url in sources:
        logger.info("NOAA fetch %s data from %s", label, url)
        lines = _fetch_lines(url)
        if not lines:
            continue
        best_row = _find_best_row(lines, timestamp)
        if not best_row:
            logger.info("NOAA %s data has no match within 1 hour of %s", label, timestamp.isoformat())
            continue

        logger.debug("Found matching row: %s", best_row)
        return {
            "wave_height": _parse_float(best_row.get("WVHT", "MM")),
            "wave_period": _select_period(best_row),
            "wave_direction": _parse_float(best_row.get("MWD", "MM")),
            "water_temp": _parse_float(best_row.get("WTMP", "MM")),
        }

    logger.info("NOAA data unavailable for station %s at %s", station_id, timestamp.isoformat())
    return None
