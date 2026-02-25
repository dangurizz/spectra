from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from api.routes import auth, sessions, spots, stats
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)

app = FastAPI(title="Spectra API")

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(spots.router)
app.include_router(stats.router)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Spectra API starting up")


@app.get("/health")
def health_check() -> dict:
    logger.debug("Health check requested")
    return {"status": "ok"}
