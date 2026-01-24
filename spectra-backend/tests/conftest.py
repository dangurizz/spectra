import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def valid_noaa_station() -> str:
    return os.getenv("NOAA_TEST_STATION_ID", "46221")


@pytest.fixture
def valid_cdip_buoy() -> str:
    return os.getenv("CDIP_TEST_BUOY_ID", "100")
