import os

from supabase import Client, create_client


def _require_url() -> str:
    url = os.getenv("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL must be set.")
    return url


def get_supabase_auth_client() -> Client:
    """Anon-key client for signup, login, and JWT verification."""
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
    if not key:
        raise ValueError("SUPABASE_ANON_KEY (or SUPABASE_KEY) must be set.")
    return create_client(_require_url(), key)


def get_supabase_client() -> Client:
    """Service-role client for database access.

    Bypasses Row Level Security. FastAPI authenticates the user via JWT and
    scopes queries to that user_id — the anon key cannot insert sessions
    because RLS checks auth.uid(), which is null without a user JWT.
    """
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY must be set. "
            "Use the service_role secret from Supabase → Settings → API. "
            "The anon key cannot write sessions under RLS."
        )
    return create_client(_require_url(), key)
