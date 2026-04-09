from fastapi import FastAPI

from la_traffic.api.routes import router as api_router

app = FastAPI(title="Louisiana Live Traffic Model API")
app.include_router(api_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
