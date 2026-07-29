"""Punto de entrada de la aplicación FastAPI de OGD-live."""

from fastapi import FastAPI

from app.api.routes_pipeline import router as pipeline_router
from app.api.routes_viewer import router as viewer_router
from app.mcp.server import mcp
from app.web.routes import router as web_router

# La app MCP se monta en /mcp. Su lifespan debe propagarse explícitamente a
# FastAPI: si no, el SessionManager de MCP no se inicializa y el montaje
# falla en silencio (ver plan de desarrollo, M3).
mcp_app = mcp.http_app(path="/", transport="streamable-http")

app = FastAPI(title="OGD-live", version="0.1.0", lifespan=mcp_app.lifespan)
app.include_router(pipeline_router)
app.include_router(viewer_router)
app.include_router(web_router)
app.mount("/mcp", mcp_app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
