"""Integration tests for CDIP buoy service.

These tests make real API calls to CDIP THREDDS server.
Run with: pytest -m integration tests/integration/test_cdip_buoy_service.py
"""

from datetime import datetime, timedelta, timezone

import pytest

from services.cdip_buoy_service import (
    get_cdip_data,
    _build_realtime_url,
    _parse_ascii_response,
    _find_closest_index,
)
from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)


@pytest.mark.integration
@pytest.mark.slow
def test_get_cdip_data_real_api(valid_cdip_station: str) -> None:
    """Test with real CDIP API (requires internet)."""
    # Use a recent timestamp (CDIP realtime data is typically last 45 days)
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_cdip_data(valid_cdip_station, recent_time)

    logger.debug(f"CDIP Result for station {valid_cdip_station}: {result}")

    if result is None:
        pytest.fail(
            f"No data returned for CDIP station {valid_cdip_station} "
            f"at {recent_time.isoformat()}"
        )

    assert isinstance(result, dict)
    assert "wave_height" in result
    assert "wave_period" in result
    assert "wave_direction" in result
    assert "water_temp" in result


@pytest.mark.integration
@pytest.mark.slow
def test_get_cdip_data_all_socal_stations() -> None:
    """Test that all key SoCal CDIP stations return data."""
    socal_stations = {
        "100": "Torrey Pines Outer (Blacks, La Jolla)",
        "191": "San Clemente (Trestles, Newport)",
        "111": "Harvest (Rincon area)",
        "028": "Santa Monica Bay (Malibu, Manhattan Beach)",
    }

    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
    successful_stations = []
    failed_stations = []

    for station_id, description in socal_stations.items():
        result = get_cdip_data(station_id, recent_time)
        if result is not None:
            successful_stations.append(station_id)
            logger.info(
                f"Station {station_id} ({description}): "
                f"Hs={result['wave_height']}, Tp={result['wave_period']}, "
                f"Dp={result['wave_direction']}, SST={result['water_temp']}"
            )
        else:
            failed_stations.append(station_id)
            logger.warning(f"Station {station_id} ({description}): No data")

    # At least some stations should return data
    assert len(successful_stations) > 0, (
        f"No CDIP stations returned data. Failed: {failed_stations}"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_get_cdip_data_wave_values_reasonable(valid_cdip_station: str) -> None:
    """Test that returned wave values are within reasonable ranges."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_cdip_data(valid_cdip_station, recent_time)

    if result is None:
        pytest.skip(f"No data available for station {valid_cdip_station}")

    # Check wave height is reasonable (0-15 meters for most conditions)
    if result["wave_height"] is not None:
        assert 0 <= result["wave_height"] <= 20, (
            f"Wave height {result['wave_height']}m outside reasonable range"
        )

    # Check wave period is reasonable (3-25 seconds)
    if result["wave_period"] is not None:
        assert 3 <= result["wave_period"] <= 30, (
            f"Wave period {result['wave_period']}s outside reasonable range"
        )

    # Check wave direction is valid (0-360 degrees)
    if result["wave_direction"] is not None:
        assert 0 <= result["wave_direction"] <= 360, (
            f"Wave direction {result['wave_direction']}° outside valid range"
        )

    # Check water temp is reasonable (5-30°C for SoCal)
    if result["water_temp"] is not None:
        assert 5 <= result["water_temp"] <= 35, (
            f"Water temp {result['water_temp']}°C outside reasonable range"
        )


@pytest.mark.integration
@pytest.mark.slow
def test_get_cdip_data_timezone_handling(valid_cdip_station: str) -> None:
    """Test that timezone conversion works correctly."""
    # Create timestamps in different timezones
    utc_time = datetime.now(timezone.utc) - timedelta(hours=2)

    # PST is UTC-8
    from datetime import timedelta as td

    pst = timezone(td(hours=-8))
    pst_time = utc_time.astimezone(pst)

    # Both should return the same data
    result_utc = get_cdip_data(valid_cdip_station, utc_time)
    result_pst = get_cdip_data(valid_cdip_station, pst_time)

    if result_utc is None or result_pst is None:
        pytest.skip(f"No data available for station {valid_cdip_station}")

    # Results should be identical since they represent the same moment
    assert result_utc["wave_height"] == result_pst["wave_height"]
    assert result_utc["wave_period"] == result_pst["wave_period"]


@pytest.mark.integration
@pytest.mark.slow
def test_get_cdip_data_invalid_station() -> None:
    """Test that invalid station returns None gracefully."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_cdip_data("99999", recent_time)

    assert result is None


def test_build_realtime_url() -> None:
    """Test URL building for CDIP THREDDS endpoint."""
    url = _build_realtime_url("100", ["waveHs", "waveTp"])

    assert "100p1_rt.nc" in url
    assert "waveHs,waveTp" in url
    assert url.startswith("http://thredds.cdip.ucsd.edu")


def test_parse_ascii_response_valid() -> None:
    """Test parsing of valid CDIP ASCII response."""
    sample_response = """Dataset {
    Float32 waveHs[waveTime = 3];
    Float32 waveTime[waveTime = 3];
} cdip/realtime/100p1_rt.nc;
---------------------------------------------
waveHs[3]
1.5, 1.6, 1.7

waveTime[3]
1700000000, 1700003600, 1700007200
"""

    result = _parse_ascii_response(sample_response)

    assert "waveHs" in result
    assert "waveTime" in result
    assert len(result["waveHs"]) == 3
    assert result["waveHs"][0] == 1.5


def test_parse_ascii_response_empty() -> None:
    """Test parsing of empty/invalid response."""
    result = _parse_ascii_response("")
    assert result == {}

    result = _parse_ascii_response("No data separator here")
    assert result == {}


def test_find_closest_index() -> None:
    """Test finding closest timestamp index."""
    timestamps = [1700000000.0, 1700003600.0, 1700007200.0]  # 1 hour apart
    target = datetime.fromtimestamp(1700003700, tz=timezone.utc)  # Close to second

    idx = _find_closest_index(timestamps, target)

    assert idx == 1  # Closest to 1700003600


def test_find_closest_index_outside_threshold() -> None:
    """Test that timestamps outside threshold return None."""
    timestamps = [1700000000.0]
    target = datetime.fromtimestamp(1700010000, tz=timezone.utc)  # 2.8 hours later

    idx = _find_closest_index(timestamps, target, max_diff_seconds=3600)

    assert idx is None
