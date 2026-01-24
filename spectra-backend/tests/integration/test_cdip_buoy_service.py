from datetime import datetime, timedelta, timezone

import pytest

from services.cdip_buoy_service import get_cdip_data
from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)

@pytest.mark.integration
@pytest.mark.slow
def test_get_cdip_data_real_api() -> None:
    """Test CDIP service with real API (requires internet)."""
    # Use Torrey Pines Outer (100) which is a reliable station
    station_id = "100"
    
    # CDIP realtime data might be slightly delayed, so look back a bit if needed.
    # But usually "now" works because we look for closest.
    # However, to be safe and ensure we get data, let's use a time from a few hours ago
    # to avoid any very-recent-gap issues, though 'realtime' file should be up to date.
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_cdip_data(station_id, recent_time)

    logger.debug(f"Result: {result}")

    if result is None:
        pytest.fail(
            "No data returned for station "
            f"{station_id} at {recent_time.isoformat()}"
        )
    assert isinstance(result, dict)
    assert "wave_height" in result
    assert "wave_period" in result
    assert "wave_direction" in result
    # water_temp is optional in my code (if index not found), but usually present for 100
    if result.get("water_temp") is not None:
         assert isinstance(result["water_temp"], float)
    
    # Check values are reasonable
    assert result["wave_height"] > 0
    assert result["wave_period"] > 0
