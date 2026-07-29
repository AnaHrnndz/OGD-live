"""Gestiona el proceso ETE4 Smartview.

v1: una única visualización activa a la vez (ver plan de desarrollo) — se
mata la sesión anterior antes de lanzar una nueva. Se invoca `og-delineation
--only_visualization` (la propia CLI de OG_Delineation, sin tocar su código)
en vez de reimplementar la carga del árbol.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Optional

import httpx

SMARTVIEW_HOST = "127.0.0.1"
SMARTVIEW_PORT = 5000
STARTUP_TIMEOUT_SECONDS = 20
STOP_TIMEOUT_SECONDS = 5


class SmartviewManager:
    def __init__(self) -> None:
        self._process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def start(self, tree_path: Path, dummy_output_dir: Path) -> None:
        """Lanza Smartview sobre tree_path, matando cualquier sesión previa."""
        async with self._lock:
            await self._stop_locked()

            og_delineation_bin = shutil.which("og-delineation")
            if og_delineation_bin is None:
                raise RuntimeError("og-delineation no está instalado en este entorno")

            dummy_output_dir.mkdir(parents=True, exist_ok=True)

            self._process = await asyncio.create_subprocess_exec(
                og_delineation_bin,
                "--tree", str(tree_path),
                "--output_path", str(dummy_output_dir),
                "--only_visualization",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            await self._wait_until_ready()

    async def _wait_until_ready(self) -> None:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + STARTUP_TIMEOUT_SECONDS
        async with httpx.AsyncClient() as client:
            while loop.time() < deadline:
                if self._process.returncode is not None:
                    raise RuntimeError(
                        f"El proceso Smartview terminó antes de arrancar "
                        f"(código {self._process.returncode})"
                    )
                try:
                    resp = await client.get(
                        f"http://{SMARTVIEW_HOST}:{SMARTVIEW_PORT}/trees", timeout=1.0
                    )
                    if resp.status_code == 200:
                        return
                except httpx.TransportError:
                    pass
                await asyncio.sleep(0.3)

        await self._stop_locked()
        raise RuntimeError("Smartview no respondió a tiempo al arrancar")

    async def stop(self) -> None:
        async with self._lock:
            await self._stop_locked()

    async def _stop_locked(self) -> None:
        if self._process is not None and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=STOP_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
        self._process = None


smartview_manager = SmartviewManager()
