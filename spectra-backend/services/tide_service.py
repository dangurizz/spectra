"""NOAA CO-OPS Tide Service.

Fetches tide data from NOAA CO-OPS (Center for Operational Oceanographic
Products and Services) for water level and tide phase information.

API Documentation: https://tidesandcurrents.noaa.gov/api/

Key SoCal Tide Stations:
    9410230 - La Jolla
    9411340 - Santa Monica
    9410580 - Los Angeles
    9410660 - San Pedro
    9410840 - Santa Barbara
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

# NOAA CO-OPS API endpoint
BASE_URL = "https://tidesandcurrents.noaa.gov/api/datagetter"

# Missing/fill values used by NOAA CO-OPS
MISSING_VALUES = {"", "N/A", "NA", "NaN"}


def _parse_float(value: str) -> Optional[float]:
    """Parse a string to float, handling missing values.

    Args:
        value: String value to parse

    Returns:
        Float value or None if missing/invalid
    """
    if value in MISSING_VALUES:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _format_date(dt: datetime) -> str:
    """Format datetime for NOAA CO-OPS API.

    Args:
        dt: Datetime to format

    Returns:
        Formatted string in YYYYMMDD HH:MM format
    """
    return dt.strftime("%Y%m%d %H:%M")


def _fetch_water_levels(
    station_id: str, begin_date: datetime, end_date: datetime
) -> Optional[list[dict]]:
    """Fetch water level data from NOAA CO-OPS API.

    Args:
        station_id: NOAA tide station ID (e.g., "9410230" for La Jolla)
        begin_date: Start of time range (UTC)
        end_date: End of time range (UTC)

    Returns:
        List of water level readings or None on failure
    """
    params = {
        "begin_date": _format_date(begin_date),
        "end_date": _format_date(end_date),
        "station": station_id,
        "product": "water_level",
        "datum": "MLLW",
        "time_zone": "gmt",
        "units": "english",
        "format": "json",
    }

    logger.info(
        "NOAA CO-OPS fetching tide data for station %s from %s to %s",
        station_id,
        begin_date.isoformat(),
        end_date.isoformat(),
    )

    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("NOAA CO-OPS request failed for station %s: %s", station_id, exc)
        return None

    try:
        data = response.json()
    except ValueError as exc:
        logger.warning("NOAA CO-OPS response parse error: %s", exc)
        return None

    # Check for API error response
    if "error" in data:
        error_msg = data.get("error", {}).get("message", "Unknown error")
        logger.warning("NOAA CO-OPS API error for station %s: %s", station_id, error_msg)
        return None

    if "data" not in data:
        logger.warning("NOAA CO-OPS response missing 'data' field for station %s", station_id)
        return None

    return data["data"]


def _parse_timestamp(time_str: str) -> Optional[datetime]:
    """Parse NOAA CO-OPS timestamp string.

    Args:
        time_str: Timestamp string in format "YYYY-MM-DD HH:MM"

    Returns:
        Datetime object (UTC) or None on parse failure
    """
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _find_closest_reading(
    readings: list[dict], target: datetime, max_diff_seconds: float = 3600
) -> tuple[Optional[dict], Optional[int]]:
    """Find the reading closest to target timestamp.

    Args:
        readings: List of water level readings
        target: Target datetime (UTC)
        max_diff_seconds: Maximum allowed difference in seconds

    Returns:
        Tuple of (closest reading, index) or (None, None) if no match
    """
    best_reading = None
    best_idx = None
    best_diff = None

    for idx, reading in enumerate(readings):
        time_str = reading.get("t")
        if not time_str:
            continue

        reading_time = _parse_timestamp(time_str)
        if reading_time is None:
            continue

        diff = abs((reading_time - target).total_seconds())
        if diff <= max_diff_seconds and (best_diff is None or diff < best_diff):
            best_diff = diff
            best_reading = reading
            best_idx = idx

    if best_reading and best_diff is not None:
        logger.debug("Best tide reading match: index %d, diff %.0f seconds", best_idx, best_diff)

    return best_reading, best_idx


def _calculate_tide_phase(
    readings: list[dict], current_idx: int
) -> str:
    """Calculate the tide phase based on surrounding water levels.

    The phase is determined by looking at the trend of water levels
    around the current reading:
    - "rising": Water level is increasing
    - "falling": Water level is decreasing
    - "high": At or near a local maximum
    - "low": At or near a local minimum

    Args:
        readings: List of water level readings
        current_idx: Index of the current reading

    Returns:
        Tide phase string: "rising", "falling", "high", or "low"
    """
    if len(readings) < 3:
        # Not enough data to determine phase, check simple trend
        if len(readings) == 2:
            v0 = _parse_float(readings[0].get("v", ""))
            v1 = _parse_float(readings[1].get("v", ""))
            if v0 is not None and v1 is not None:
                return "rising" if v1 > v0 else "falling"
        return "unknown"

    # Get current value
    current_value = _parse_float(readings[current_idx].get("v", ""))
    if current_value is None:
        return "unknown"

    # Look at values before and after to determine trend
    # Use up to 3 readings on each side for better trend detection
    before_values = []
    after_values = []

    for i in range(max(0, current_idx - 3), current_idx):
        val = _parse_float(readings[i].get("v", ""))
        if val is not None:
            before_values.append(val)

    for i in range(current_idx + 1, min(len(readings), current_idx + 4)):
        val = _parse_float(readings[i].get("v", ""))
        if val is not None:
            after_values.append(val)

    if not before_values and not after_values:
        return "unknown"

    # Calculate averages for trend comparison
    avg_before = sum(before_values) / len(before_values) if before_values else current_value
    avg_after = sum(after_values) / len(after_values) if after_values else current_value

    # Determine if we're at an extremum
    # Threshold for considering values "equal" (0.1 feet)
    threshold = 0.1

    is_local_max = (
        before_values
        and after_values
        and current_value >= max(before_values) - threshold
        and current_value >= max(after_values) - threshold
    )
    is_local_min = (
        before_values
        and after_values
        and current_value <= min(before_values) + threshold
        and current_value <= min(after_values) + threshold
    )

    if is_local_max:
        return "high"
    elif is_local_min:
        return "low"
    elif avg_after > avg_before + threshold:
        return "rising"
    elif avg_after < avg_before - threshold:
        return "falling"
    elif current_value > avg_before:
        return "rising"
    elif current_value < avg_before:
        return "falling"
    else:
        return "rising"  # Default to rising if truly flat


def get_tide_data(station_id: str, timestamp: datetime) -> Optional[dict]:
    """Fetch tide data for a specific station and timestamp.

    Fetches water level data from NOAA CO-OPS and calculates the tide phase
    based on the trend of water levels around the requested time.

    Args:
        station_id: NOAA tide station ID (e.g., "9410230" for La Jolla)
        timestamp: UTC timestamp for which to fetch data

    Returns:
        dict with:
            - tide_height (float): Water level in feet relative to MLLW
            - tide_phase (str): One of "rising", "falling", "high", "low"
        or None if data unavailable

    Example:
        >>> from datetime import datetime, timezone
        >>> data = get_tide_data("9410230", datetime.now(timezone.utc))
        >>> if data:
        ...     print(f"Tide: {data['tide_height']:.1f}ft, {data['tide_phase']}")
    """
    # Ensure timestamp is UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    # Fetch 2 hours of data centered around the target timestamp
    # This gives us enough data points to calculate tide phase
    begin_date = timestamp - timedelta(hours=1)
    end_date = timestamp + timedelta(hours=1)

    readings = _fetch_water_levels(station_id, begin_date, end_date)
    if not readings:
        logger.info("NOAA CO-OPS no tide data available for station %s", station_id)
        return None

    logger.debug("NOAA CO-OPS received %d readings for station %s", len(readings), station_id)

    # Find the reading closest to our target timestamp
    closest_reading, idx = _find_closest_reading(readings, timestamp)
    if closest_reading is None or idx is None:
        logger.info(
            "NOAA CO-OPS no tide reading within 1 hour of %s for station %s",
            timestamp.isoformat(),
            station_id,
        )
        return None

    # Parse the water level
    tide_height = _parse_float(closest_reading.get("v", ""))
    if tide_height is None:
        logger.warning("NOAA CO-OPS invalid water level value for station %s", station_id)
        return None

    # Calculate tide phase
    tide_phase = _calculate_tide_phase(readings, idx)

    logger.debug(
        "NOAA CO-OPS station %s at %s: height=%.2f ft, phase=%s",
        station_id,
        timestamp.isoformat(),
        tide_height,
        tide_phase,
    )

    return {
        "tide_height": tide_height,
        "tide_phase": tide_phase,
    }
