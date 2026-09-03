from datetime import datetime, timezone
from unittest.mock import patch

from services.conditions_service import (
    CDIP_TO_NDBC,
    _ndbc_station_for_spot,
    fetch_conditions,
)

BLACKS = {
    "name": "Blacks Beach",
    "nearest_buoy_id": "100",
    "nearest_wind_station": "LJAC1",
    "nearest_tide_station": "9410230",
}

NOW = datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc)


def test_ndbc_station_maps_cdip_buoy() -> None:
    assert _ndbc_station_for_spot(BLACKS) == "46225"
    assert CDIP_TO_NDBC["028"] == "46221"


def test_ndbc_station_falls_back_to_numeric_wind_station() -> None:
    spot = {
        "nearest_buoy_id": "999",
        "nearest_wind_station": "46221",
    }
    assert _ndbc_station_for_spot(spot) == "46221"


def test_ndbc_station_skips_met_wind_stations() -> None:
    spot = {
        "nearest_buoy_id": "999",
        "nearest_wind_station": "LJAC1",
    }
    assert _ndbc_station_for_spot(spot) is None


@patch("services.conditions_service.get_tide_data", return_value=None)
@patch("services.conditions_service.get_wind_data_by_station", return_value=None)
@patch("services.conditions_service.get_buoy_data")
@patch("services.conditions_service.get_cdip_data")
def test_fetch_conditions_uses_cdip_and_skips_noaa(mock_cdip, mock_noaa, _wind, _tide) -> None:
    mock_cdip.return_value = {
        "wave_height": 1.2,
        "wave_period": 12.0,
        "wave_direction": 270.0,
        "water_temp": 18.5,
    }

    result = fetch_conditions(BLACKS, NOW)

    assert result.wave_height == 1.2
    assert result.wave_period == 12.0
    assert result.water_temp == 18.5
    mock_noaa.assert_not_called()


@patch("services.conditions_service.get_tide_data", return_value=None)
@patch("services.conditions_service.get_wind_data_by_station", return_value=None)
@patch("services.conditions_service.get_buoy_data")
@patch("services.conditions_service.get_cdip_data", return_value=None)
def test_fetch_conditions_falls_back_to_noaa_when_cdip_missing(
    _cdip, mock_noaa, _wind, _tide
) -> None:
    mock_noaa.return_value = {
        "wave_height": 0.9,
        "wave_period": 10.0,
        "wave_direction": 250.0,
        "water_temp": 17.0,
    }

    result = fetch_conditions(BLACKS, NOW)

    mock_noaa.assert_called_once_with("46225", NOW)
    assert result.wave_height == 0.9
    assert result.wave_period == 10.0
    assert result.water_temp == 17.0


@patch("services.conditions_service.get_tide_data", return_value=None)
@patch("services.conditions_service.get_wind_data_by_station", return_value=None)
@patch("services.conditions_service.get_buoy_data")
@patch("services.conditions_service.get_cdip_data")
def test_fetch_conditions_fills_missing_cdip_fields_from_noaa(
    mock_cdip, mock_noaa, _wind, _tide
) -> None:
    mock_cdip.return_value = {
        "wave_height": 1.4,
        "wave_period": 11.0,
        "wave_direction": None,
        "water_temp": None,
    }
    mock_noaa.return_value = {
        "wave_height": 9.9,
        "wave_period": 9.9,
        "wave_direction": 260.0,
        "water_temp": 16.0,
    }

    result = fetch_conditions(BLACKS, NOW)

    assert result.wave_height == 1.4
    assert result.wave_period == 11.0
    assert result.wave_direction == 260.0
    assert result.water_temp == 16.0
