"""Punto de entrada de la aplicación FastAPI de OGD-live."""

from fastapi import FastAPI

from app.api.routes_pipeline import router as pipeline_router

app = FastAPI(title="OGD-live", version="0.1.0")
app.include_router(pipeline_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
