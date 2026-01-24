from typing import Optional

from pydantic import BaseModel


class Conditions(BaseModel):
    wave_height: Optional[float] = None
    wave_period: Optional[float] = None
    wave_direction: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    tide_height: Optional[float] = None
    water_temp: Optional[float] = None
