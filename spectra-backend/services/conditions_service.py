"""Orchestrates fetching all conditions (wave, wind, tide) for a spot at a given time."""

from datetime import datetime
from typing import Optional

from models.conditions import Conditions
from services.cdip_buoy_service import get_cdip_data
from services.noaa_buoy_service import get_buoy_data
from services.tide_service import get_tide_data
from services.wind_service import get_wind_data_by_station
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)

# CDIP realtime only covers ~45 days. Map each SoCal CDIP buoy to a nearby
# NOAA NDBC station that reports historical waves + water temp.
CDIP_TO_NDBC = {
    "028": "46221",  # Santa Monica Bay
    "100": "46225",  # Torrey Pines Outer
    "111": "46218",  # Harvest
    "191": "46224",  # Oceanside Offshore / San Clemente
}

_WAVE_FIELDS = ("wave_height", "wave_period", "wave_direction", "water_temp")


def _ndbc_station_for_spot(spot: dict) -> Optional[str]:
    """Pick an NDBC station to use when CDIP data is missing."""
    buoy_id = spot.get("nearest_buoy_id")
    if buoy_id and buoy_id in CDIP_TO_NDBC:
        return CDIP_TO_NDBC[buoy_id]
    wind_station = spot.get("nearest_wind_station")
    if wind_station and wind_station.isdigit() and len(wind_station) >= 5:
        return wind_station
    return None


def _fill_wave_fields(conditions: Conditions, data: Optional[dict]) -> None:
    if not data:
        return
    if conditions.wave_height is None:
        conditions.wave_height = data.get("wave_height")
    if conditions.wave_period is None:
        conditions.wave_period = data.get("wave_period")
    if conditions.wave_direction is None:
        conditions.wave_direction = data.get("wave_direction")
    if conditions.water_temp is None:
        conditions.water_temp = data.get("water_temp")


def _wave_fields_missing(conditions: Conditions) -> bool:
    return any(getattr(conditions, field) is None for field in _WAVE_FIELDS)


def fetch_conditions(spot: dict, timestamp: datetime) -> Conditions:
    """Fetch all available conditions for a spot at a given timestamp.

    Queries CDIP buoy (waves + water temp), NOAA NDBC (wind), and NOAA CO-OPS
    (tide) using the station IDs stored on the spot record. If CDIP has no
    data (common for sessions older than ~45 days), falls back to a mapped
    NOAA NDBC buoy for historical waves. Any unavailable source is skipped —
    Conditions fields remain None.

    Args:
        spot: Spot dict from Supabase with nearest_buoy_id, nearest_wind_station,
              nearest_tide_station fields.
        timestamp: UTC datetime for which to fetch conditions.

    Returns:
        Conditions model populated with whatever data was available.
    """
    conditions = Conditions()

    buoy_id = spot.get("nearest_buoy_id")
    if buoy_id:
        try:
            cdip = get_cdip_data(buoy_id, timestamp)
            if cdip:
                _fill_wave_fields(conditions, cdip)
                logger.info(
                    "CDIP buoy %s: %.2fm @ %.1fs",
                    buoy_id,
                    conditions.wave_height or 0,
                    conditions.wave_period or 0,
                )
        except Exception as exc:
            logger.warning("CDIP fetch failed for buoy %s: %s", buoy_id, exc)

    if _wave_fields_missing(conditions):
        ndbc_id = _ndbc_station_for_spot(spot)
        if ndbc_id:
            try:
                noaa = get_buoy_data(ndbc_id, timestamp)
                if noaa:
                    _fill_wave_fields(conditions, noaa)
                    logger.info(
                        "NOAA NDBC fallback %s: %.2fm @ %.1fs",
                        ndbc_id,
                        conditions.wave_height or 0,
                        conditions.wave_period or 0,
                    )
            except Exception as exc:
                logger.warning("NOAA NDBC fallback failed for station %s: %s", ndbc_id, exc)

    wind_station = spot.get("nearest_wind_station")
    if wind_station:
        try:
            wind = get_wind_data_by_station(wind_station, timestamp)
            if wind:
                conditions.wind_speed = wind.get("wind_speed")
                conditions.wind_direction = wind.get("wind_direction")
                logger.info(
                    "Wind station %s: %.1f mph @ %s°",
                    wind_station,
                    conditions.wind_speed or 0,
                    conditions.wind_direction,
                )
        except Exception as exc:
            logger.warning("Wind fetch failed for station %s: %s", wind_station, exc)

    tide_station = spot.get("nearest_tide_station")
    if tide_station:
        try:
            tide = get_tide_data(tide_station, timestamp)
            if tide:
                conditions.tide_height = tide.get("tide_height")
                conditions.tide_phase = tide.get("tide_phase")
                logger.info(
                    "Tide station %s: %.2f ft, %s",
                    tide_station,
                    conditions.tide_height or 0,
                    conditions.tide_phase,
                )
        except Exception as exc:
            logger.warning("Tide fetch failed for station %s: %s", tide_station, exc)

    return conditions
