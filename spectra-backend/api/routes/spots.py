from fastapi import APIRouter

router = APIRouter(prefix="/spots", tags=["spots"])


@router.get("")
async def list_spots() -> dict:
    return {"message": "Not implemented"}
