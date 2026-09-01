from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from database.supabase_client import get_supabase_client
from models.conditions import Conditions
from services.conditions_service import fetch_conditions
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    spot_id: str
    start_time: datetime
    end_time: datetime
    rating: float = Field(..., ge=1, le=5)
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    user_id: str
    spot_id: str
    start_time: datetime
    end_time: datetime
    rating: float
    notes: Optional[str] = None
    conditions: Optional[Conditions] = None


def _row_to_response(row: dict) -> SessionResponse:
    conditions = Conditions(
        wave_height=row.get("wave_height"),
        wave_period=row.get("wave_period"),
        wave_direction=row.get("wave_direction"),
        wind_speed=row.get("wind_speed"),
        wind_direction=row.get("wind_direction"),
        tide_height=row.get("tide_height"),
        tide_phase=row.get("tide_phase"),
        water_temp=row.get("water_temp"),
    )
    return SessionResponse(
        id=row["id"],
        user_id=row["user_id"],
        spot_id=row["spot_id"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        rating=row["rating"],
        notes=row.get("notes"),
        conditions=conditions,
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    current_user: dict = Depends(get_current_user),
) -> SessionResponse:
    client = get_supabase_client()

    # Look up spot for its station IDs
    spot_result = client.table("spots").select("*").eq("id", body.spot_id).execute()
    if not spot_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")
    spot = spot_result.data[0]

    # Auto-fetch conditions at session start time
    conditions = fetch_conditions(spot, body.start_time)
    logger.info("Fetched conditions for spot %s at %s", spot["name"], body.start_time)

    row = {
        "user_id": current_user["id"],
        "spot_id": body.spot_id,
        "start_time": body.start_time.isoformat(),
        "end_time": body.end_time.isoformat(),
        "rating": body.rating,
        "notes": body.notes,
        "wave_height": conditions.wave_height,
        "wave_period": conditions.wave_period,
        "wave_direction": conditions.wave_direction,
        "wind_speed": conditions.wind_speed,
        "wind_direction": conditions.wind_direction,
        "tide_height": conditions.tide_height,
        "tide_phase": conditions.tide_phase,
        "water_temp": conditions.water_temp,
    }

    result = client.table("sessions").insert(row).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create session"
        )
    return _row_to_response(result.data[0])


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
) -> List[SessionResponse]:
    client = get_supabase_client()
    result = (
        client.table("sessions")
        .select("*")
        .eq("user_id", current_user["id"])
        .order("start_time", desc=True)
        .execute()
    )
    return [_row_to_response(row) for row in result.data]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> SessionResponse:
    client = get_supabase_client()
    result = (
        client.table("sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _row_to_response(result.data[0])


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    current_user: dict = Depends(get_current_user),
) -> SessionResponse:
    client = get_supabase_client()

    # Verify ownership
    existing = (
        client.table("sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = client.table("sessions").update(updates).eq("id", session_id).execute()
    return _row_to_response(result.data[0])


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    client = get_supabase_client()

    # Verify ownership
    existing = (
        client.table("sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    client.table("sessions").delete().eq("id", session_id).execute()
