from typing import Any, Dict

from fastapi import HTTPException, status


async def get_current_user() -> Dict[str, Any]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication not implemented yet.",
    )
