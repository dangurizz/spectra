from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from database.supabase_client import get_supabase_auth_client
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest) -> AuthResponse:
    client = get_supabase_auth_client()
    try:
        result = client.auth.sign_up({"email": body.email, "password": body.password})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not result.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Check your email for a confirmation link.",
        )
    # Session may be None if email confirmation is required
    access_token = result.session.access_token if result.session else ""
    logger.info("New user signed up: %s", result.user.id)
    return AuthResponse(access_token=access_token, user_id=result.user.id)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest) -> AuthResponse:
    client = get_supabase_auth_client()
    try:
        result = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not result.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed")
    logger.info("User logged in: %s", result.user.id)
    return AuthResponse(
        access_token=result.session.access_token,
        user_id=result.user.id,
    )
