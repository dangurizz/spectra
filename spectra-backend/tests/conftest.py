import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def valid_noaa_station() -> str:
    """NOAA NDBC buoy station ID for testing."""
    return os.getenv("NOAA_TEST_STATION_ID", "46221")


@pytest.fixture
def valid_cdip_station() -> str:
    """CDIP buoy station ID for testing.
    
    Key SoCal CDIP Buoys:
        100 - Torrey Pines Outer (Blacks, La Jolla)
        191 - San Clemente (Trestles, Newport)
        111 - Harvest (Rincon area)
        028 - Santa Monica Bay (Malibu, Manhattan Beach)
    """
    return os.getenv("CDIP_TEST_STATION_ID", "100")


@pytest.fixture
def valid_tide_station() -> str:
    """NOAA CO-OPS tide station ID for testing.
    
    Key SoCal Tide Stations:
        9410230 - La Jolla
        9411340 - Santa Monica
        9410580 - Los Angeles
        9410660 - San Pedro
        9410840 - Santa Barbara
    """
    return os.getenv("TIDE_TEST_STATION_ID", "9410230")
  
  
@pytest.fixture
def valid_wind_station() -> str:
    """NOAA NDBC station ID for wind data testing.
    
    Key SoCal NOAA Stations with wind data:
        46221 - Santa Monica Bay
        46222 - San Pedro
        46225 - Torrey Pines Outer
        LJAC1 - La Jolla
        SDBC1 - San Diego Bay
    """
    return os.getenv("WIND_TEST_STATION_ID", "46221")
