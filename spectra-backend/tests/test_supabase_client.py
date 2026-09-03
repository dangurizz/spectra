import os
from unittest.mock import patch

import pytest

from database.supabase_client import get_supabase_auth_client, get_supabase_client


@patch("database.supabase_client.create_client")
def test_db_client_uses_service_role_key(mock_create) -> None:
    env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "service-secret",
    }
    with patch.dict(os.environ, env, clear=True):
        get_supabase_client()

    mock_create.assert_called_once_with("https://example.supabase.co", "service-secret")


@patch("database.supabase_client.create_client")
def test_auth_client_uses_anon_key(mock_create) -> None:
    env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "service-secret",
    }
    with patch.dict(os.environ, env, clear=True):
        get_supabase_auth_client()

    mock_create.assert_called_once_with("https://example.supabase.co", "anon-key")


@patch("database.supabase_client.create_client")
def test_auth_client_falls_back_to_legacy_supabase_key(mock_create) -> None:
    env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "legacy-anon",
    }
    with patch.dict(os.environ, env, clear=True):
        get_supabase_auth_client()

    mock_create.assert_called_once_with("https://example.supabase.co", "legacy-anon")


def test_db_client_requires_service_role_key() -> None:
    env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon-key",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
            get_supabase_client()
