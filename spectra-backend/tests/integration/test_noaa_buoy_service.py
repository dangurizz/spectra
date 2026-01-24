from datetime import datetime, timedelta, timezone

import pytest

from services.noaa_buoy_service import get_buoy_data
from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

@pytest.mark.integration
@pytest.mark.slow
def test_get_buoy_data_real_api(valid_noaa_station: str) -> None:
    """Test with real NOAA API (requires internet)."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_buoy_data(valid_noaa_station, recent_time)

    logger.debug(f"Result: {result}")

    if result is None:
        pytest.fail(
            "No data returned for station "
            f"{valid_noaa_station} at {recent_time.isoformat()}"
        )
    assert isinstance(result, dict)
    assert "wave_height" in result
    assert "wave_period" in result
    assert "wave_direction" in result
    assert "water_temp" in result
