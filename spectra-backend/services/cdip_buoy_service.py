"""CDIP (Coastal Data Information Program) Buoy Service.

Fetches wave data from CDIP buoys, which provide excellent coverage for
Southern California surf spots.

API Documentation: http://cdip.ucsd.edu/
Data Access: Uses THREDDS/OpenDAP ASCII endpoint for simplicity.

Key SoCal CDIP Buoys:
    100 - Torrey Pines Outer (Blacks, La Jolla)
    191 - San Clemente (Trestles, Newport)
    111 - Harvest (Rincon area)
    028 - Santa Monica Bay (Malibu, Manhattan Beach)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import requests

from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

# CDIP THREDDS OpenDAP ASCII endpoint for realtime data
REALTIME_BASE_URL = "http://thredds.cdip.ucsd.edu/thredds/dodsC/cdip/realtime"

# Variables we need from CDIP data
# waveHs - Significant wave height (meters)
# waveTp - Peak wave period (seconds)
# waveDp - Peak wave direction (degrees, direction waves are coming FROM)
# waveTime - Timestamp (seconds since 1970-01-01 UTC)
# sstSeaSurfaceTemperature - Water temperature (Celsius)
WAVE_VARIABLES = ["waveHs", "waveTp", "waveDp", "waveTime"]
SST_VARIABLES = ["sstSeaSurfaceTemperature", "sstTime"]

# Missing/fill values used by CDIP
FILL_VALUE = 999.99


def _build_realtime_url(buoy_id: str, variables: list[str]) -> str:
    """Build the THREDDS ASCII URL for realtime data.

    Args:
        buoy_id: CDIP buoy station ID (e.g., "100")
        variables: List of variable names to fetch

    Returns:
        Complete URL for the ASCII data request
    """
    # Format: {buoy_id}p1_rt.nc for realtime data
    dataset = f"{buoy_id}p1_rt.nc"
    var_query = ",".join(variables)
    return f"{REALTIME_BASE_URL}/{dataset}.ascii?{var_query}"


def _parse_ascii_response(text: str) -> dict[str, list[float]]:
    """Parse CDIP THREDDS ASCII response into variable arrays.

    The ASCII format looks like:
        Dataset {
            Float32 waveHs[waveTime = 1234];
            ...
        }
        ---------------------------------------------
        waveHs[1234]
        1.5, 1.6, 1.7, ...

    Args:
        text: Raw ASCII response text

    Returns:
        Dictionary mapping variable names to lists of float values
    """
    result: dict[str, list[float]] = {}

    # Split by the separator line
    parts = text.split("---------------------------------------------")
    if len(parts) < 2:
        logger.warning("CDIP response missing data separator")
        return result

    data_section = parts[1].strip()

    current_var = None
    current_values: list[float] = []

    for line in data_section.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Check for variable header like "waveHs[1234]"
        if "[" in line and "]" in line and not line[0].isdigit() and "," not in line:
            # Save previous variable if exists
            if current_var and current_values:
                result[current_var] = current_values

            # Extract variable name
            var_name = line.split("[")[0].strip()
            current_var = var_name
            current_values = []
            continue

        # Parse data values (comma-separated floats)
        if current_var:
            # Handle lines with data values
            values_str = line.replace("[", "").replace("]", "")
            for val_str in values_str.split(","):
                val_str = val_str.strip()
                if not val_str:
                    continue
                try:
                    # Skip index values (they appear as "0 1.5" for indexed arrays)
                    parts_list = val_str.split()
                    if len(parts_list) == 2:
                        # This is likely "index value" format
                        val = float(parts_list[1])
                    else:
                        val = float(val_str)
                    current_values.append(val)
                except ValueError:
                    continue

    # Save last variable
    if current_var and current_values:
        result[current_var] = current_values

    return result


def _find_closest_index(
    timestamps: list[float], target: datetime, max_diff_seconds: float = 3600
) -> Optional[int]:
    """Find the index of the timestamp closest to target.

    Args:
        timestamps: List of Unix timestamps (seconds since epoch)
        target: Target datetime (must be UTC)
        max_diff_seconds: Maximum allowed difference in seconds

    Returns:
        Index of closest timestamp, or None if no match within threshold
    """
    target_ts = target.timestamp()

    best_idx = None
    best_diff = None

    for idx, ts in enumerate(timestamps):
        diff = abs(ts - target_ts)
        if diff <= max_diff_seconds and (best_diff is None or diff < best_diff):
            best_diff = diff
            best_idx = idx

    if best_idx is not None and best_diff is not None:
        logger.debug("Best timestamp match: index %d, diff %.0f seconds", best_idx, best_diff)

    return best_idx


def _get_value_at_index(
    data: dict[str, list[float]], var_name: str, idx: int
) -> Optional[float]:
    """Get a value from the data dict, handling missing values.

    Args:
        data: Parsed data dictionary
        var_name: Variable name to fetch
        idx: Index in the array

    Returns:
        Float value or None if missing/invalid
    """
    if var_name not in data:
        return None

    values = data[var_name]
    if idx >= len(values):
        return None

    value = values[idx]

    # Check for CDIP fill/missing values
    if value >= FILL_VALUE or value < -999:
        return None

    return value


def _fetch_wave_data(buoy_id: str) -> Optional[dict[str, list[float]]]:
    """Fetch wave data from CDIP.

    Args:
        buoy_id: CDIP buoy station ID

    Returns:
        Parsed data dictionary or None on failure
    """
    url = _build_realtime_url(buoy_id, WAVE_VARIABLES)
    logger.info("CDIP fetching wave data from %s", url)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("CDIP wave data request failed for buoy %s: %s", buoy_id, exc)
        return None

    return _parse_ascii_response(response.text)


def _fetch_sst_data(buoy_id: str) -> Optional[dict[str, list[float]]]:
    """Fetch sea surface temperature data from CDIP.

    Args:
        buoy_id: CDIP buoy station ID

    Returns:
        Parsed data dictionary or None on failure
    """
    url = _build_realtime_url(buoy_id, SST_VARIABLES)
    logger.info("CDIP fetching SST data from %s", url)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("CDIP SST data request failed for buoy %s: %s", buoy_id, exc)
        return None

    return _parse_ascii_response(response.text)


def get_cdip_data(buoy_id: str, timestamp: datetime) -> Optional[dict]:
    """Fetch CDIP buoy data for a specific station and timestamp.

    Args:
        buoy_id: CDIP station ID (e.g., "100" for Torrey Pines Outer)
        timestamp: UTC timestamp for which to fetch data

    Returns:
        dict with wave_height (m), wave_period (s), wave_direction (degrees),
        water_temp (C), or None if data unavailable

    Example:
        >>> from datetime import datetime, timezone
        >>> data = get_cdip_data("100", datetime.now(timezone.utc))
        >>> if data:
        ...     print(f"Wave height: {data['wave_height']}m")
    """
    # Ensure timestamp is UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    # Fetch wave data
    wave_data = _fetch_wave_data(buoy_id)
    if not wave_data:
        logger.info("CDIP wave data unavailable for buoy %s", buoy_id)
        return None

    # Find timestamp closest to target
    if "waveTime" not in wave_data:
        logger.warning("CDIP response missing waveTime for buoy %s", buoy_id)
        return None

    wave_idx = _find_closest_index(wave_data["waveTime"], timestamp)
    if wave_idx is None:
        logger.info(
            "CDIP no wave data within 1 hour of %s for buoy %s",
            timestamp.isoformat(),
            buoy_id,
        )
        return None

    # Extract wave values
    wave_height = _get_value_at_index(wave_data, "waveHs", wave_idx)
    wave_period = _get_value_at_index(wave_data, "waveTp", wave_idx)
    wave_direction = _get_value_at_index(wave_data, "waveDp", wave_idx)

    # Fetch SST data separately (different time resolution)
    water_temp = None
    sst_data = _fetch_sst_data(buoy_id)
    if sst_data and "sstTime" in sst_data:
        sst_idx = _find_closest_index(sst_data["sstTime"], timestamp)
        if sst_idx is not None:
            water_temp = _get_value_at_index(
                sst_data, "sstSeaSurfaceTemperature", sst_idx
            )

    logger.debug(
        "CDIP buoy %s at %s: height=%.2f, period=%.1f, direction=%.0f, temp=%s",
        buoy_id,
        timestamp.isoformat(),
        wave_height or 0,
        wave_period or 0,
        wave_direction or 0,
        water_temp,
    )

    return {
        "wave_height": wave_height,
        "wave_period": wave_period,
        "wave_direction": wave_direction,
        "water_temp": water_temp,
    }
