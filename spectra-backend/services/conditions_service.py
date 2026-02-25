"""Orchestrates fetching all conditions (wave, wind, tide) for a spot at a given time."""

from datetime import datetime

from models.conditions import Conditions
from services.cdip_buoy_service import get_cdip_data
from services.tide_service import get_tide_data
from services.wind_service import get_wind_data_by_station
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)


def fetch_conditions(spot: dict, timestamp: datetime) -> Conditions:
    """Fetch all available conditions for a spot at a given timestamp.

    Queries CDIP buoy (waves + water temp), NOAA NDBC (wind), and NOAA CO-OPS
    (tide) in parallel using the station IDs stored on the spot record.
    Any unavailable data source is silently skipped — Conditions fields remain None.

    Args:
        spot: Spot dict from Supabase with nearest_buoy_id, nearest_wind_station,
              nearest_tide_station fields.
        timestamp: UTC datetime for which to fetch conditions.

    Returns:
        Conditions model populated with whatever data was available.
    """
    conditions = Conditions()

    # Wave + water temp from CDIP buoy
    buoy_id = spot.get("nearest_buoy_id")
    if buoy_id:
        try:
            cdip = get_cdip_data(buoy_id, timestamp)
            if cdip:
                conditions.wave_height = cdip.get("wave_height")
                conditions.wave_period = cdip.get("wave_period")
                conditions.wave_direction = cdip.get("wave_direction")
                conditions.water_temp = cdip.get("water_temp")
                logger.info(
                    "CDIP buoy %s: %.2fm @ %.1fs",
                    buoy_id,
                    conditions.wave_height or 0,
                    conditions.wave_period or 0,
                )
        except Exception as exc:
            logger.warning("CDIP fetch failed for buoy %s: %s", buoy_id, exc)

    # Wind from NOAA NDBC
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

    # Tide from NOAA CO-OPS
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
