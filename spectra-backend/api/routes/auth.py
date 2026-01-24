from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
async def signup() -> dict:
    return {"message": "Not implemented"}


@router.post("/login")
async def login() -> dict:
    return {"message": "Not implemented"}
