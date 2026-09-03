"""Seed the Supabase spots table with 20 hardcoded SoCal surf spots.

Station IDs:
  CDIP buoys  : 028 (Santa Monica Bay), 100 (Torrey Pines Outer),
                111 (Harvest/Rincon), 191 (San Clemente/Trestles)
  Tide stations: 9410230 (La Jolla), 9410580 (Los Angeles),
                 9410660 (San Pedro), 9410840 (Santa Barbara),
                 9411340 (Santa Monica)
  Wind stations: NOAA NDBC IDs (see wind_service.py KNOWN_STATIONS)

Run:
    poetry run python -m database.seed_spots
"""

from typing import Dict, List

from database.supabase_client import get_supabase_client
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)

INITIAL_SPOTS: List[Dict[str, object]] = [
    # ── San Diego County ──────────────────────────────────────────────
    {
        "name": "Blacks Beach",
        "latitude": 32.884,
        "longitude": -117.253,
        "region": "San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "LJAC1",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Windansea Beach",
        "latitude": 32.836,
        "longitude": -117.277,
        "region": "San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "LJAC1",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Pacific Beach",
        "latitude": 32.795,
        "longitude": -117.258,
        "region": "San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "LJAC1",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Ocean Beach",
        "latitude": 32.745,
        "longitude": -117.252,
        "region": "San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "SDBC1",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Imperial Beach",
        "latitude": 32.578,
        "longitude": -117.133,
        "region": "San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "SDBC1",
        "nearest_tide_station": "9410230",
    },
    # ── North County San Diego ────────────────────────────────────────
    {
        "name": "Swamis",
        "latitude": 33.027,
        "longitude": -117.293,
        "region": "North County San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "NTBC1",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Cardiff Reef",
        "latitude": 33.017,
        "longitude": -117.278,
        "region": "North County San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "NTBC1",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Carlsbad State Beach",
        "latitude": 33.158,
        "longitude": -117.353,
        "region": "North County San Diego",
        "nearest_buoy_id": "100",
        "nearest_wind_station": "NTBC1",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Oceanside Harbor",
        "latitude": 33.219,
        "longitude": -117.397,
        "region": "North County San Diego",
        "nearest_buoy_id": "191",
        "nearest_wind_station": "NTBC1",
        "nearest_tide_station": "9410230",
    },
    # ── Orange County ─────────────────────────────────────────────────
    {
        "name": "Trestles (Lower)",
        "latitude": 33.388,
        "longitude": -117.589,
        "region": "Orange County",
        "nearest_buoy_id": "191",
        "nearest_wind_station": "46254",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "San Onofre",
        "latitude": 33.368,
        "longitude": -117.561,
        "region": "Orange County",
        "nearest_buoy_id": "191",
        "nearest_wind_station": "46254",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Dana Point",
        "latitude": 33.460,
        "longitude": -117.697,
        "region": "Orange County",
        "nearest_buoy_id": "191",
        "nearest_wind_station": "46223",
        "nearest_tide_station": "9410230",
    },
    {
        "name": "Huntington Beach",
        "latitude": 33.663,
        "longitude": -118.001,
        "region": "Orange County",
        "nearest_buoy_id": "191",
        "nearest_wind_station": "46253",
        "nearest_tide_station": "9410580",
    },
    {
        "name": "Newport Beach (Wedge)",
        "latitude": 33.598,
        "longitude": -117.879,
        "region": "Orange County",
        "nearest_buoy_id": "191",
        "nearest_wind_station": "46223",
        "nearest_tide_station": "9410580",
    },
    # ── Los Angeles County ────────────────────────────────────────────
    {
        "name": "Manhattan Beach",
        "latitude": 33.887,
        "longitude": -118.411,
        "region": "Los Angeles",
        "nearest_buoy_id": "028",
        "nearest_wind_station": "46221",
        "nearest_tide_station": "9410580",
    },
    {
        "name": "Hermosa Beach",
        "latitude": 33.862,
        "longitude": -118.401,
        "region": "Los Angeles",
        "nearest_buoy_id": "028",
        "nearest_wind_station": "46221",
        "nearest_tide_station": "9410580",
    },
    {
        "name": "El Porto",
        "latitude": 33.916,
        "longitude": -118.418,
        "region": "Los Angeles",
        "nearest_buoy_id": "028",
        "nearest_wind_station": "46221",
        "nearest_tide_station": "9410580",
    },
    {
        "name": "Malibu (First Point)",
        "latitude": 34.036,
        "longitude": -118.678,
        "region": "Los Angeles",
        "nearest_buoy_id": "028",
        "nearest_wind_station": "SXRFC1",
        "nearest_tide_station": "9411340",
    },
    {
        "name": "Zuma Beach",
        "latitude": 34.015,
        "longitude": -118.824,
        "region": "Los Angeles",
        "nearest_buoy_id": "028",
        "nearest_wind_station": "SXRFC1",
        "nearest_tide_station": "9411340",
    },
    # ── Ventura / Santa Barbara ───────────────────────────────────────
    {
        "name": "Rincon Point",
        "latitude": 34.373,
        "longitude": -119.472,
        "region": "Ventura/Santa Barbara",
        "nearest_buoy_id": "111",
        "nearest_wind_station": "46256",
        "nearest_tide_station": "9410840",
    },
]


def seed_spots() -> None:
    """Insert all INITIAL_SPOTS into the Supabase spots table.

    Skips spots whose name already exists to allow re-running safely.
    Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or a .env file).
    """
    client = get_supabase_client()

    # Fetch existing spot names to avoid duplicates
    existing = client.table("spots").select("name").execute()
    existing_names = {row["name"] for row in (existing.data or [])}

    to_insert = [s for s in INITIAL_SPOTS if s["name"] not in existing_names]
    if not to_insert:
        logger.info("All spots already seeded, nothing to do.")
        return

    result = client.table("spots").insert(to_insert).execute()
    inserted = len(result.data) if result.data else 0
    logger.info("Seeded %d spots (%d skipped as duplicates).", inserted, len(INITIAL_SPOTS) - inserted)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    seed_spots()
