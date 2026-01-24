from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

import requests

from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

BASE_URL = (
    "http://thredds.cdip.ucsd.edu/thredds/dodsC/cdip/realtime/{buoy_id}p1_rt.nc.ascii"
)
REQUEST_TIMEOUT_SECONDS = 10
MAX_TIME_DIFF_SECONDS = 3600
MISSING_VALUE_THRESHOLD = -999.0

_HEADER_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\[\d+\]$")


def _ensure_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _fetch_ascii(url: str) -> Optional[str]:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("CDIP request failed for %s: %s", url, exc)
        return None

    text = response.text.strip()
    if not text:
        logger.info("CDIP response empty for %s", url)
        return None
    return text


def _parse_numeric_buffer(lines: Iterable[str]) -> list[float]:
    joined = " ".join(line.strip() for line in lines if line.strip())
    if not joined:
        return []
    tokens = re.split(r"[,\s]+", joined)
    values: list[float] = []
    for token in tokens:
        if not token:
            continue
        try:
            values.append(float(token))
        except ValueError:
            logger.debug("CDIP skipping invalid token: %s", token)
            values.append(math.nan)
    return values


def _parse_ascii_blocks(text: str) -> Dict[str, list[float]]:
    if "---------------------------------------------" not in text:
        return {}
    _, data_section = text.split("---------------------------------------------", 1)
    lines = data_section.strip().splitlines()

    blocks: Dict[str, list[float]] = {}
    current_var: Optional[str] = None
    buffer: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_var is not None:
                blocks[current_var] = _parse_numeric_buffer(buffer)
                current_var = None
                buffer = []
            continue

        header_match = _HEADER_RE.match(stripped)
        if header_match:
            if current_var is not None:
                blocks[current_var] = _parse_numeric_buffer(buffer)
            current_var = header_match.group("name")
            buffer = []
            continue

        if current_var is not None:
            buffer.append(stripped)

    if current_var is not None:
        blocks[current_var] = _parse_numeric_buffer(buffer)

    return blocks


def _sanitize_value(value: Optional[float]) -> Optional[float]:
    if value is None or not math.isfinite(value):
        return None
    if value <= MISSING_VALUE_THRESHOLD:
        return None
    return float(value)


def _fetch_variable_array(buoy_id: str, var_name: str) -> Optional[list[float]]:
    url = f"{BASE_URL.format(buoy_id=buoy_id)}?{var_name}"
    text = _fetch_ascii(url)
    if not text:
        return None

    blocks = _parse_ascii_blocks(text)
    values = blocks.get(var_name)
    if not values:
        logger.info("CDIP response missing %s for buoy %s", var_name, buoy_id)
        return None
    return values


def _fetch_variables_at_index(
    buoy_id: str, index: int, variables: Iterable[str]
) -> Dict[str, Optional[float]]:
    query = ",".join(f"{var}[{index}]" for var in variables)
    url = f"{BASE_URL.format(buoy_id=buoy_id)}?{query}"
    text = _fetch_ascii(url)
    if not text:
        return {var: None for var in variables}

    blocks = _parse_ascii_blocks(text)
    results: Dict[str, Optional[float]] = {}
    for var in variables:
        values = blocks.get(var)
        value = values[0] if values else None
        results[var] = _sanitize_value(value)
    return results


def _find_closest_index(
    times: list[float], target_epoch: float
) -> tuple[Optional[int], Optional[float]]:
    best_idx = None
    best_diff = None
    for idx, value in enumerate(times):
        if not math.isfinite(value):
            continue
        diff = abs(value - target_epoch)
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_idx = idx
    return best_idx, best_diff


def get_cdip_data(buoy_id: str, timestamp: datetime) -> Optional[dict]:
    """
    Fetch CDIP buoy data for a specific buoy and timestamp.

    Args:
        buoy_id: CDIP buoy ID (e.g., "100" for Torrey Pines Outer)
        timestamp: Timestamp for which to fetch data (UTC)

    Returns:
        dict with wave_height, wave_period, wave_direction, water_temp
        or None if data unavailable within the time window.
    """
    timestamp = _ensure_utc(timestamp)
    target_epoch = timestamp.timestamp()

    wave_times = _fetch_variable_array(buoy_id, "waveTime")
    if not wave_times:
        logger.info("CDIP waveTime unavailable for buoy %s", buoy_id)
        return None

    wave_idx, wave_diff = _find_closest_index(wave_times, target_epoch)
    if wave_idx is None or wave_diff is None:
        logger.info("CDIP waveTime parsing failed for buoy %s", buoy_id)
        return None
    if wave_diff > MAX_TIME_DIFF_SECONDS:
        logger.info(
            "CDIP wave data no match within %s seconds (diff %.0f)",
            MAX_TIME_DIFF_SECONDS,
            wave_diff,
        )
        return None

    wave_values = _fetch_variables_at_index(
        buoy_id, wave_idx, ("waveHs", "waveTp", "waveDp")
    )

    water_temp = None
    sst_times = _fetch_variable_array(buoy_id, "sstTime")
    if sst_times:
        sst_idx, sst_diff = _find_closest_index(sst_times, target_epoch)
        if sst_idx is not None and sst_diff is not None:
            if sst_diff <= MAX_TIME_DIFF_SECONDS:
                sst_values = _fetch_variables_at_index(
                    buoy_id, sst_idx, ("sstSeaSurfaceTemperature",)
                )
                water_temp = sst_values.get("sstSeaSurfaceTemperature")
            else:
                logger.info(
                    "CDIP sst data no match within %s seconds (diff %.0f)",
                    MAX_TIME_DIFF_SECONDS,
                    sst_diff,
                )
    else:
        logger.info("CDIP sstTime unavailable for buoy %s", buoy_id)

    return {
        "wave_height": wave_values.get("waveHs"),
        "wave_period": wave_values.get("waveTp"),
        "wave_direction": wave_values.get("waveDp"),
        "water_temp": water_temp,
    }
