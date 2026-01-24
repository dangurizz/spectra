# Spectra Backend

FastAPI backend for the Spectra MVP.

## Setup
- Copy `.env.example` to `.env` and fill values
- Install dependencies: `poetry install`
- Run server: `poetry run uvicorn main:app --reload`

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
