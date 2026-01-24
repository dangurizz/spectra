from fastapi import APIRouter

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats() -> dict:
    return {"message": "Not implemented"}
