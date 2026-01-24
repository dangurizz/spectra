from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("")
async def create_session() -> dict:
    return {"message": "Not implemented"}


@router.get("")
async def list_sessions() -> dict:
    return {"message": "Not implemented"}


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    return {"message": "Not implemented", "session_id": session_id}


@router.put("/{session_id}")
async def update_session(session_id: str) -> dict:
    return {"message": "Not implemented", "session_id": session_id}


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict:
    return {"message": "Not implemented", "session_id": session_id}
