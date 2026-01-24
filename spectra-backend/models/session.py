from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .conditions import Conditions


class Session(BaseModel):
    id: str
    user_id: str
    spot_id: str
    start_time: datetime
    end_time: datetime
    rating: float = Field(..., ge=1, le=5)
    notes: Optional[str] = None
    conditions: Optional[Conditions] = None
