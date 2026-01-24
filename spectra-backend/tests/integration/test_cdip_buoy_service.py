from datetime import datetime, timedelta, timezone

import pytest

from services.cdip_buoy_service import get_cdip_data
from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)


@pytest.mark.integration
@pytest.mark.slow
def test_get_cdip_data_real_api(valid_cdip_buoy: str) -> None:
    """Test with real CDIP API (requires internet)."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_cdip_data(valid_cdip_buoy, recent_time)

    logger.debug("Result: %s", result)

    if result is None:
        pytest.fail(
            "No data returned for buoy "
            f"{valid_cdip_buoy} at {recent_time.isoformat()}"
        )

    assert isinstance(result, dict)
    assert "wave_height" in result
    assert "wave_period" in result
    assert "wave_direction" in result
    assert "water_temp" in result
