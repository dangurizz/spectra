from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from database.supabase_client import get_supabase_client
from models.spot import Spot
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)
router = APIRouter(prefix="/spots", tags=["spots"])


@router.get("", response_model=List[Spot])
async def list_spots(current_user: dict = Depends(get_current_user)) -> List[Spot]:
    client = get_supabase_client()
    result = client.table("spots").select("*").order("name").execute()
    if result.data is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch spots")
    return [Spot(**row) for row in result.data]
