from fastapi import FastAPI

from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)

app = FastAPI(title="Spectra API")


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Spectra API starting up")


@app.get("/health")
def health_check() -> dict:
    logger.debug("Health check requested")
    return {"status": "ok"}
