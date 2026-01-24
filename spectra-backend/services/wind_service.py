"""Wind Service for fetching wind data from NOAA weather stations.

Fetches wind data from NOAA NDBC (National Data Buoy Center) stations,
which provide real-time and historical meteorological observations including
wind speed, direction, and gusts.

API Documentation: https://www.ndbc.noaa.gov/
Data Format: Standard meteorological data (stdmet)

Key fields:
    WSPD - Wind speed (m/s) - converted to mph for output
    WDIR - Wind direction (degrees true)
    GST  - Gust speed (m/s) - converted to mph for output
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests

from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

# NOAA NDBC data URLs
HISTORICAL_URL = (
    "https://www.ndbc.noaa.gov/view_text_file.php"
    "?filename={station_id}h{year}.txt.gz&dir=data/historical/stdmet/"
)
REALTIME_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"

# Station list URL for finding active stations
STATION_LIST_URL = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"

# Missing value indicators used by NOAA
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

# Conversion factor: meters per second to miles per hour
MPS_TO_MPH = 2.23694

# Known coastal weather stations with coordinates for SoCal region
# These are reliable NDBC stations that report wind data
KNOWN_STATIONS: Dict[str, Tuple[float, float, str]] = {
    "46221": (33.856, -118.633, "Santa Monica Bay"),
    "46222": (33.618, -118.317, "San Pedro"),
    "46223": (33.458, -117.767, "Dana Point"),
    "46224": (33.178, -117.472, "Oceanside Offshore"),
    "46225": (32.933, -117.392, "Torrey Pines Outer"),
    "46232": (32.530, -117.431, "Point Loma South"),
    "46253": (33.576, -118.181, "Long Beach Channel"),
    "46254": (33.430, -117.771, "San Clemente Basin"),
    "46256": (34.454, -120.471, "Point Conception"),
    "46218": (34.454, -120.782, "Harvest Platform"),
    "46069": (33.667, -120.200, "South Santa Rosa Island"),
    "NTBC1": (33.354, -117.498, "Oceanside Harbor"),
    "LJAC1": (32.867, -117.257, "La Jolla"),
    "SDBC1": (32.714, -117.173, "San Diego Bay"),
    "SXRFC1": (33.951, -118.435, "Santa Monica Pier"),
}


def _parse_float(value: str) -> Optional[float]:
    """Parse a string to float, returning None for missing values.

    Args:
        value: String value to parse

    Returns:
        Float value or None if missing/invalid
    """
    if value in MISSING_VALUES:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _normalize_year(year: int) -> int:
    """Normalize 2-digit years to 4-digit years.

    Args:
        year: Year value (2 or 4 digits)

    Returns:
        4-digit year
    """
    if year < 100:
        return 2000 + year if year < 70 else 1900 + year
    return year


def _parse_timestamp(fields: Dict[str, str]) -> Optional[datetime]:
    """Parse timestamp from NOAA data row.

    Args:
        fields: Dictionary of field name to value

    Returns:
        datetime in UTC or None if parsing fails
    """
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


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers.

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def _find_nearest_station(
    lat: float, lon: float, max_distance_km: float = 100.0
) -> Optional[Tuple[str, float]]:
    """Find the nearest NOAA station to a given location.

    Args:
        lat: Latitude of target location
        lon: Longitude of target location
        max_distance_km: Maximum acceptable distance in kilometers

    Returns:
        Tuple of (station_id, distance_km) or None if no station within range
    """
    nearest_station = None
    nearest_distance = float("inf")

    for station_id, (station_lat, station_lon, _) in KNOWN_STATIONS.items():
        distance = _haversine_distance(lat, lon, station_lat, station_lon)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_station = station_id

    if nearest_station and nearest_distance <= max_distance_km:
        logger.debug(
            "Found nearest station %s at %.1f km from (%.3f, %.3f)",
            nearest_station,
            nearest_distance,
            lat,
            lon,
        )
        return (nearest_station, nearest_distance)

    logger.warning(
        "No station within %.1f km of (%.3f, %.3f). Nearest is %.1f km away.",
        max_distance_km,
        lat,
        lon,
        nearest_distance,
    )
    return None


def _fetch_lines(url: str) -> Optional[List[str]]:
    """Fetch and return lines from a NOAA data URL.

    Args:
        url: NOAA data URL

    Returns:
        List of text lines or None on failure
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("NOAA request failed for %s: %s", url, exc)
        return None

    lines = response.text.strip().splitlines()
    if not lines:
        logger.info("NOAA response empty for %s", url)
        return None
    return lines


def _find_best_row(
    lines: List[str], timestamp: datetime, max_diff_seconds: float = 3600
) -> Optional[Dict[str, str]]:
    """Find the data row closest to the target timestamp.

    Args:
        lines: Lines from NOAA data file
        timestamp: Target timestamp (UTC)
        max_diff_seconds: Maximum acceptable time difference in seconds

    Returns:
        Dictionary of field name to value, or None if no match found
    """
    header = None
    for line in lines:
        if line.startswith("#"):
            header = line.lstrip("#").split()
            break
    if not header:
        logger.debug("No header found in NOAA response")
        return None
    logger.debug("NOAA wind data header: %s", header)

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
            logger.debug(
                "First data row timestamp: %s (target: %s)",
                row_timestamp.isoformat(),
                timestamp.isoformat(),
            )
            first_ts_logged = True
        diff_seconds = abs((row_timestamp - timestamp).total_seconds())
        if diff_seconds <= max_diff_seconds and (best_diff is None or diff_seconds < best_diff):
            best_diff = diff_seconds
            best_row = row

    if best_row and best_diff is not None:
        logger.debug("Best match diff: %.0f seconds", best_diff)

    return best_row


def _convert_mps_to_mph(value: Optional[float]) -> Optional[float]:
    """Convert meters per second to miles per hour.

    Args:
        value: Speed in m/s or None

    Returns:
        Speed in mph or None
    """
    if value is None:
        return None
    return round(value * MPS_TO_MPH, 1)


def get_wind_data_by_station(station_id: str, timestamp: datetime) -> Optional[dict]:
    """Fetch wind data for a specific NOAA station and timestamp.

    Args:
        station_id: NOAA station ID (e.g., "46221")
        timestamp: UTC timestamp for which to fetch data

    Returns:
        dict with wind_speed (mph), wind_direction (degrees), gust_speed (mph)
        or None if data unavailable
    """
    # Ensure timestamp is UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=45)
    if timestamp >= recent_cutoff:
        # For recent timestamps, try realtime first
        sources = [
            ("realtime", REALTIME_URL.format(station_id=station_id)),
            ("historical", HISTORICAL_URL.format(station_id=station_id, year=timestamp.year)),
        ]
    else:
        sources = [
            ("historical", HISTORICAL_URL.format(station_id=station_id, year=timestamp.year))
        ]

    for label, url in sources:
        logger.info("Fetching NOAA wind data (%s) from %s", label, url)
        lines = _fetch_lines(url)
        if not lines:
            continue
        best_row = _find_best_row(lines, timestamp)
        if not best_row:
            logger.info(
                "NOAA %s wind data has no match within 1 hour of %s",
                label,
                timestamp.isoformat(),
            )
            continue

        logger.debug("Found matching wind data row: %s", best_row)

        # Parse wind values - NOAA reports in m/s, we convert to mph
        wind_speed_mps = _parse_float(best_row.get("WSPD", "MM"))
        wind_dir = _parse_float(best_row.get("WDIR", "MM"))
        gust_speed_mps = _parse_float(best_row.get("GST", "MM"))

        return {
            "wind_speed": _convert_mps_to_mph(wind_speed_mps),
            "wind_direction": wind_dir,
            "gust_speed": _convert_mps_to_mph(gust_speed_mps),
        }

    logger.info(
        "NOAA wind data unavailable for station %s at %s",
        station_id,
        timestamp.isoformat(),
    )
    return None


def get_wind_data(lat: float, lon: float, timestamp: datetime) -> Optional[dict]:
    """Fetch wind data for a specific location and timestamp.

    Finds the nearest NOAA weather station to the given coordinates and
    retrieves wind data for the specified time.

    Args:
        lat: Latitude of location
        lon: Longitude of location
        timestamp: UTC timestamp for which to fetch data

    Returns:
        dict with:
            - wind_speed (mph): Wind speed in miles per hour
            - wind_direction (degrees): Wind direction in degrees true
            - gust_speed (mph): Gust speed in miles per hour
            - station_id: ID of the station used
            - station_distance_km: Distance to station in kilometers
        or None if data unavailable

    Example:
        >>> from datetime import datetime, timezone
        >>> # Get wind data for San Diego
        >>> data = get_wind_data(32.7157, -117.1611, datetime.now(timezone.utc))
        >>> if data:
        ...     print(f"Wind: {data['wind_speed']} mph from {data['wind_direction']}°")
    """
    # Find nearest station
    result = _find_nearest_station(lat, lon)
    if result is None:
        logger.warning("No NOAA station found near (%.3f, %.3f)", lat, lon)
        return None

    station_id, distance_km = result

    # Fetch wind data from that station
    wind_data = get_wind_data_by_station(station_id, timestamp)
    if wind_data is None:
        return None

    # Add station metadata
    wind_data["station_id"] = station_id
    wind_data["station_distance_km"] = round(distance_km, 1)

    return wind_data


def fetch_wind_data(station_id: str, timestamp_iso: str) -> Dict[str, float]:
    """Legacy function for backward compatibility.

    Args:
        station_id: NOAA station ID
        timestamp_iso: ISO format timestamp string

    Returns:
        dict with wind_speed, wind_direction, gust_speed

    Raises:
        ValueError: If timestamp format is invalid or no data available
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp format: {timestamp_iso}") from exc

    result = get_wind_data_by_station(station_id, timestamp)
    if result is None:
        raise ValueError(f"No wind data available for station {station_id} at {timestamp_iso}")

    # Return only float values for backward compatibility
    return {
        "wind_speed": result["wind_speed"] or 0.0,
        "wind_direction": result["wind_direction"] or 0.0,
        "gust_speed": result["gust_speed"] or 0.0,
    }
