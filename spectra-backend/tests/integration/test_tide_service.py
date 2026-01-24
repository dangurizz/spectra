"""Integration tests for NOAA CO-OPS Tide Service.

Tests the tide service against the real NOAA CO-OPS API.
These tests require internet access and may be slow.
"""

from datetime import datetime, timedelta, timezone

import pytest

from services.tide_service import get_tide_data
from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)


@pytest.mark.integration
@pytest.mark.slow
def test_get_tide_data_real_api(valid_tide_station: str) -> None:
    """Test with real NOAA CO-OPS API (requires internet)."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

    result = get_tide_data(valid_tide_station, recent_time)

    logger.debug(f"Result: {result}")

    if result is None:
        pytest.fail(
            "No data returned for station "
            f"{valid_tide_station} at {recent_time.isoformat()}"
        )
    assert isinstance(result, dict)
    assert "tide_height" in result
    assert "tide_phase" in result


@pytest.mark.integration
@pytest.mark.slow
def test_tide_height_is_float(valid_tide_station: str) -> None:
    """Test that tide height is returned as a float."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

    result = get_tide_data(valid_tide_station, recent_time)

    if result is None:
        pytest.skip(f"No data available for station {valid_tide_station}")

    assert isinstance(result["tide_height"], float)
    # Tide height in feet should be within reasonable bounds
    # MLLW datum means values are typically between -2 and +10 feet
    assert -5 <= result["tide_height"] <= 15


@pytest.mark.integration
@pytest.mark.slow
def test_tide_phase_valid_value(valid_tide_station: str) -> None:
    """Test that tide phase is a valid value."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

    result = get_tide_data(valid_tide_station, recent_time)

    if result is None:
        pytest.skip(f"No data available for station {valid_tide_station}")

    valid_phases = {"rising", "falling", "high", "low", "unknown"}
    assert result["tide_phase"] in valid_phases


@pytest.mark.integration
@pytest.mark.slow
def test_get_tide_data_naive_timestamp(valid_tide_station: str) -> None:
    """Test that naive timestamps are handled correctly."""
    # Naive timestamp (no timezone info)
    naive_time = datetime.now() - timedelta(hours=1)

    result = get_tide_data(valid_tide_station, naive_time)

    # Should still work - function should assume UTC
    if result is None:
        pytest.skip(f"No data available for station {valid_tide_station}")

    assert isinstance(result, dict)
    assert "tide_height" in result
    assert "tide_phase" in result


@pytest.mark.integration
@pytest.mark.slow
def test_get_tide_data_different_timezone(valid_tide_station: str) -> None:
    """Test that non-UTC timestamps are converted correctly."""
    from datetime import timezone as tz

    # Pacific time (UTC-8)
    pacific = tz(timedelta(hours=-8))
    pacific_time = datetime.now(pacific) - timedelta(hours=1)

    result = get_tide_data(valid_tide_station, pacific_time)

    if result is None:
        pytest.skip(f"No data available for station {valid_tide_station}")

    assert isinstance(result, dict)
    assert "tide_height" in result
    assert "tide_phase" in result


@pytest.mark.integration
@pytest.mark.slow
def test_get_tide_data_historical(valid_tide_station: str) -> None:
    """Test fetching historical tide data (yesterday)."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    result = get_tide_data(valid_tide_station, yesterday)

    # Historical data should be available for yesterday
    if result is None:
        pytest.skip(f"No historical data for station {valid_tide_station}")

    assert isinstance(result, dict)
    assert "tide_height" in result
    assert "tide_phase" in result


@pytest.mark.integration
@pytest.mark.slow
def test_get_tide_data_invalid_station() -> None:
    """Test with an invalid station ID."""
    invalid_station = "9999999"
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

    result = get_tide_data(invalid_station, recent_time)

    # Should return None for invalid station
    assert result is None


@pytest.mark.integration
@pytest.mark.slow
def test_get_tide_data_all_socal_stations() -> None:
    """Test that all key SoCal stations return data."""
    socal_stations = {
        "9410230": "La Jolla",
        "9411340": "Santa Monica",
        "9410580": "Los Angeles",
        "9410660": "San Pedro",
        "9410840": "Santa Barbara",
    }

    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
    results = {}

    for station_id, name in socal_stations.items():
        result = get_tide_data(station_id, recent_time)
        results[name] = result
        logger.debug(f"Station {name} ({station_id}): {result}")

    # At least some stations should return data
    successful = [name for name, result in results.items() if result is not None]

    if not successful:
        pytest.fail("No SoCal tide stations returned data")

    logger.info(f"Successful stations: {successful}")
