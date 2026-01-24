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
