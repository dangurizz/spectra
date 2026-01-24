from typing import Optional

from pydantic import BaseModel


class Spot(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    region: str
    nearest_buoy_id: Optional[str] = None
    nearest_wind_station: Optional[str] = None
    nearest_tide_station: Optional[str] = None
