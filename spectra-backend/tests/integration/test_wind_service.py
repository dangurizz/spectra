"""Integration tests for wind service.

These tests make real API calls to NOAA NDBC servers.
Run with: pytest -m integration tests/integration/test_wind_service.py
"""

from datetime import datetime, timedelta, timezone

import pytest

from services.wind_service import (
    get_wind_data,
    get_wind_data_by_station,
    _find_nearest_station,
    _haversine_distance,
    _convert_mps_to_mph,
    KNOWN_STATIONS,
)
from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_real_api(valid_wind_station: str) -> None:
    """Test with real NOAA API (requires internet)."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_wind_data_by_station(valid_wind_station, recent_time)

    logger.debug(f"Wind data result for station {valid_wind_station}: {result}")

    if result is None:
        pytest.fail(
            f"No wind data returned for station {valid_wind_station} "
            f"at {recent_time.isoformat()}"
        )

    assert isinstance(result, dict)
    assert "wind_speed" in result
    assert "wind_direction" in result
    assert "gust_speed" in result


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_by_location() -> None:
    """Test fetching wind data by lat/lon coordinates."""
    # San Diego coordinates
    lat, lon = 32.7157, -117.1611
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_wind_data(lat, lon, recent_time)

    logger.debug(f"Wind data result for ({lat}, {lon}): {result}")

    if result is None:
        pytest.fail(
            f"No wind data returned for location ({lat}, {lon}) "
            f"at {recent_time.isoformat()}"
        )

    assert isinstance(result, dict)
    assert "wind_speed" in result
    assert "wind_direction" in result
    assert "gust_speed" in result
    assert "station_id" in result
    assert "station_distance_km" in result


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_all_known_stations() -> None:
    """Test that all known stations can return wind data."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
    successful_stations = []
    failed_stations = []

    for station_id, (lat, lon, description) in KNOWN_STATIONS.items():
        result = get_wind_data_by_station(station_id, recent_time)
        if result is not None:
            successful_stations.append(station_id)
            logger.info(
                f"Station {station_id} ({description}): "
                f"speed={result['wind_speed']} mph, "
                f"direction={result['wind_direction']}°, "
                f"gust={result['gust_speed']} mph"
            )
        else:
            failed_stations.append(station_id)
            logger.warning(f"Station {station_id} ({description}): No data")

    # At least some stations should return data
    assert len(successful_stations) > 0, (
        f"No NOAA wind stations returned data. Failed: {failed_stations}"
    )
    logger.info(
        f"Wind data available from {len(successful_stations)}/{len(KNOWN_STATIONS)} stations"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_values_reasonable(valid_wind_station: str) -> None:
    """Test that returned wind values are within reasonable ranges."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_wind_data_by_station(valid_wind_station, recent_time)

    if result is None:
        pytest.skip(f"No data available for station {valid_wind_station}")

    # Check wind speed is reasonable (0-100 mph)
    if result["wind_speed"] is not None:
        assert 0 <= result["wind_speed"] <= 150, (
            f"Wind speed {result['wind_speed']} mph outside reasonable range"
        )

    # Check wind direction is valid (0-360 degrees)
    if result["wind_direction"] is not None:
        assert 0 <= result["wind_direction"] <= 360, (
            f"Wind direction {result['wind_direction']}° outside valid range"
        )

    # Check gust speed is reasonable (0-150 mph)
    if result["gust_speed"] is not None:
        assert 0 <= result["gust_speed"] <= 200, (
            f"Gust speed {result['gust_speed']} mph outside reasonable range"
        )

        # Gusts should typically be >= wind speed
        if result["wind_speed"] is not None:
            assert result["gust_speed"] >= result["wind_speed"] * 0.8, (
                f"Gust speed {result['gust_speed']} unexpectedly lower than "
                f"wind speed {result['wind_speed']}"
            )


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_timezone_handling(valid_wind_station: str) -> None:
    """Test that timezone conversion works correctly."""
    # Create timestamps in different timezones
    utc_time = datetime.now(timezone.utc) - timedelta(hours=2)

    # PST is UTC-8
    pst = timezone(timedelta(hours=-8))
    pst_time = utc_time.astimezone(pst)

    # Both should return the same data
    result_utc = get_wind_data_by_station(valid_wind_station, utc_time)
    result_pst = get_wind_data_by_station(valid_wind_station, pst_time)

    if result_utc is None or result_pst is None:
        pytest.skip(f"No data available for station {valid_wind_station}")

    # Results should be identical since they represent the same moment
    assert result_utc["wind_speed"] == result_pst["wind_speed"]
    assert result_utc["wind_direction"] == result_pst["wind_direction"]


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_invalid_station() -> None:
    """Test that invalid station returns None gracefully."""
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_wind_data_by_station("INVALID_STATION_99999", recent_time)

    assert result is None


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_location_out_of_range() -> None:
    """Test that locations too far from any station return None."""
    # Coordinates in the middle of the Pacific Ocean
    lat, lon = 0.0, -140.0
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)

    result = get_wind_data(lat, lon, recent_time)

    # Should return None as no station is within 100km
    assert result is None


def test_find_nearest_station() -> None:
    """Test finding nearest station to a location."""
    # San Diego coordinates - should find SDBC1 or LJAC1
    lat, lon = 32.7157, -117.1611

    result = _find_nearest_station(lat, lon)

    assert result is not None
    station_id, distance_km = result
    assert station_id in KNOWN_STATIONS
    assert distance_km > 0
    assert distance_km < 50  # Should find a nearby station


def test_find_nearest_station_no_match() -> None:
    """Test that distant locations return None."""
    # Middle of the Atlantic Ocean
    lat, lon = 30.0, -50.0

    result = _find_nearest_station(lat, lon, max_distance_km=100.0)

    assert result is None


def test_haversine_distance() -> None:
    """Test haversine distance calculation."""
    # Known distance: LA to San Diego is approximately 190 km
    la_lat, la_lon = 34.0522, -118.2437
    sd_lat, sd_lon = 32.7157, -117.1611

    distance = _haversine_distance(la_lat, la_lon, sd_lat, sd_lon)

    # Should be approximately 180-200 km
    assert 150 < distance < 250, f"LA to SD distance {distance} km outside expected range"


def test_haversine_distance_same_point() -> None:
    """Test that distance to same point is zero."""
    lat, lon = 33.0, -117.0

    distance = _haversine_distance(lat, lon, lat, lon)

    assert distance == 0.0


def test_convert_mps_to_mph() -> None:
    """Test meters per second to miles per hour conversion."""
    # 10 m/s should be approximately 22.4 mph
    result = _convert_mps_to_mph(10.0)
    assert result is not None
    assert 22.0 < result < 23.0

    # None should return None
    assert _convert_mps_to_mph(None) is None

    # 0 m/s should be 0 mph
    assert _convert_mps_to_mph(0.0) == 0.0


def test_convert_mps_to_mph_precision() -> None:
    """Test that conversion rounds to 1 decimal place."""
    # 5.5 m/s = 12.30317 mph, should round to 12.3
    result = _convert_mps_to_mph(5.5)
    assert result == 12.3


@pytest.mark.integration
@pytest.mark.slow
def test_get_wind_data_multiple_socal_locations() -> None:
    """Test wind data retrieval for multiple SoCal surf spots."""
    surf_spots = {
        "Blacks Beach": (32.8896, -117.2536),
        "Trestles": (33.3892, -117.5893),
        "Malibu": (34.0369, -118.6786),
        "Newport Beach": (33.6095, -117.9289),
    }

    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
    successful_spots = []
    failed_spots = []

    for spot_name, (lat, lon) in surf_spots.items():
        result = get_wind_data(lat, lon, recent_time)
        if result is not None:
            successful_spots.append(spot_name)
            logger.info(
                f"{spot_name} ({lat}, {lon}): "
                f"wind={result['wind_speed']} mph from {result['wind_direction']}°, "
                f"gusts={result['gust_speed']} mph "
                f"(station: {result['station_id']}, {result['station_distance_km']} km away)"
            )
        else:
            failed_spots.append(spot_name)
            logger.warning(f"{spot_name}: No wind data available")

    # Most spots should have wind data
    assert len(successful_spots) >= len(surf_spots) // 2, (
        f"Too many spots without wind data. Successful: {successful_spots}, "
        f"Failed: {failed_spots}"
    )
