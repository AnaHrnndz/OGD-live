"""Proxy hacia el proceso Smartview activo.

Smartview sirve sus assets y su API en rutas absolutas fijas desde la raíz
(`/static/...`, `/trees...`) que su JS no permite parametrizar con un
prefijo — así que en vez de reescribir el HTML/JS servido, exponemos esas
mismas rutas absolutas en nuestra propia app (no colisionan con nada
existente) y usamos `/viewer` como punto de entrada, reenviando tal cual la
redirección que hace Smartview hacia `/static/gui.html?tree=...`.

Único ajuste necesario: la cabecera `Location` que emite Smartview en sus
redirects es una URL absoluta a su propio host:puerto interno
(`http://127.0.0.1:5000/...`); si se reenvía tal cual, el navegador saltaría
directamente a ese puerto interno saltándose el proxy. Se reescribe para
que apunte de vuelta a nuestra propia ruta.
"""

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.smartview_manager import SMARTVIEW_HOST, SMARTVIEW_PORT, smartview_manager

router = APIRouter(tags=["viewer"])

_SMARTVIEW_BASE = f"http://{SMARTVIEW_HOST}:{SMARTVIEW_PORT}"
_DROP_HEADERS = {"content-length", "transfer-encoding", "connection", "date", "server"}


def _forward_headers(headers: httpx.Headers) -> dict:
    forwarded = {k: v for k, v in headers.items() if k.lower() not in _DROP_HEADERS}
    location = forwarded.get("location")
    if location and location.startswith(_SMARTVIEW_BASE):
        forwarded["location"] = location[len(_SMARTVIEW_BASE):]
    return forwarded


async def _proxy_get(upstream_path: str, request: Request) -> Response:
    if not smartview_manager.is_running:
        raise HTTPException(status_code=409, detail="No hay ninguna visualización activa")

    async with httpx.AsyncClient(follow_redirects=False) as client:
        upstream = await client.get(
            f"{_SMARTVIEW_BASE}{upstream_path}", params=request.query_params
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_forward_headers(upstream.headers),
    )


@router.get("/viewer")
async def viewer_entry(request: Request) -> Response:
    """Punto de entrada: reenvía la redirección de Smartview hacia el árbol cargado."""
    return await _proxy_get("/", request)


@router.get("/static/{path:path}")
async def viewer_static(path: str, request: Request) -> Response:
    return await _proxy_get(f"/static/{path}", request)


@router.get("/trees")
async def viewer_trees_list(request: Request) -> Response:
    return await _proxy_get("/trees", request)


@router.get("/trees/{path:path}")
async def viewer_trees(path: str, request: Request) -> Response:
    return await _proxy_get(f"/trees/{path}", request)
