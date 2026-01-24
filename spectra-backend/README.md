# Spectra Backend

FastAPI backend for the Spectra MVP.

## Setup
- Copy `.env.example` to `.env` and fill values
- Install dependencies: `poetry install`
- Run server: `poetry run uvicorn main:app --reload`

## Health Check
- `GET /health`
