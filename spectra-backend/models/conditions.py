from typing import Optional

from pydantic import BaseModel


class Conditions(BaseModel):
    wave_height: Optional[float] = None   # meters (from CDIP)
    wave_period: Optional[float] = None   # seconds
    wave_direction: Optional[float] = None  # degrees
    wind_speed: Optional[float] = None    # mph (from NOAA NDBC)
    wind_direction: Optional[float] = None  # degrees
    tide_height: Optional[float] = None   # feet MLLW (from NOAA CO-OPS)
    tide_phase: Optional[str] = None      # "rising", "falling", "high", "low"
    water_temp: Optional[float] = None    # Celsius (from CDIP)
