# Spectra Backend

FastAPI backend for the Spectra MVP.

## Setup
1. Copy `.env.example` to `.env` and fill values from Supabase → Settings → API:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY` (public anon key — used for signup/login)
   - `SUPABASE_SERVICE_ROLE_KEY` (secret — used for database writes; bypasses RLS)
2. In the Supabase SQL editor, run `database/schema.sql`
3. Install dependencies: `poetry install`
4. Seed spots: `poetry run python -m database.seed_spots`
5. Run server: `poetry run uvicorn main:app --reload --port 8000`

## Smoke test
With `.env` filled and spots seeded:

```
poetry run python run_smoke.py
```

This signs up (or logs in), lists spots, creates a session with auto-captured conditions, checks stats, then deletes the session.

If signup returns an empty `access_token`, disable **Confirm email** in Supabase → Authentication → Providers → Email (or confirm the smoke-test user manually).

## Logging

Centralized logging configuration is available via `utils.logging_config`:

```python
from utils.logging_config import setup_logging

logger = setup_logging("DEBUG", __name__)
logger.info("Your log message here")
```

The `setup_logging` function accepts:
- `level`: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger_name`: Logger name (defaults to root logger)
- `format_string`: Optional custom format string

## Health Check
- `GET /health`
