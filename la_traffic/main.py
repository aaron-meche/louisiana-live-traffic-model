import logging

from fastapi import FastAPI

from la_traffic.api.routes import router as api_router
from la_traffic.models.database import create_tables

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Louisiana Live Traffic Model API",
    description="Real-time vehicle counts from 511la.org cameras.",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    ok = create_tables()
    if ok:
        logger.info("Database ready.")
    else:
        logger.warning("Database not available — API will return empty results.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
