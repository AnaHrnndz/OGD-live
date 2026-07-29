"""Gestión de jobs en memoria para ejecutar el pipeline OGD sin bloquear el
event loop de FastAPI.

v1: un único análisis activo a la vez (ver plan de desarrollo) — no hay cola,
un segundo intento mientras hay uno en curso se rechaza explícitamente.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.core.ogd_adapter import run_analysis
from app.schemas import OgdParams, OgdResult


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class JobAlreadyRunningError(Exception):
    def __init__(self, job_id: str):
        super().__init__(f"Ya hay un análisis en curso: {job_id}")
        self.job_id = job_id


@dataclass
class Job:
    job_id: str
    params: OgdParams
    status: JobStatus = JobStatus.PENDING
    result: Optional[OgdResult] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.monotonic)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._active_job_id: Optional[str] = None

    async def reserve_job_id(self) -> str:
        """Reserva un hueco para un job nuevo, o lanza si ya hay uno activo."""
        async with self._lock:
            if self._active_job_id is not None:
                raise JobAlreadyRunningError(self._active_job_id)
            job_id = uuid.uuid4().hex
            self._active_job_id = job_id
            return job_id

    def release(self, job_id: str) -> None:
        """Libera el hueco reservado sin llegar a registrar/lanzar el job."""
        if self._active_job_id == job_id:
            self._active_job_id = None

    def register(self, job_id: str, params: OgdParams) -> Job:
        job = Job(job_id=job_id, params=params)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def start(self, job: Job) -> None:
        """Lanza la ejecución del job en background (fire-and-forget)."""
        asyncio.create_task(self._run(job))

    async def _run(self, job: Job) -> None:
        job.status = JobStatus.RUNNING
        try:
            job.result = await asyncio.to_thread(run_analysis, job.params)
            job.status = JobStatus.DONE
        except Exception as exc:
            job.error = str(exc)
            job.status = JobStatus.ERROR
        finally:
            if self._active_job_id == job.job_id:
                self._active_job_id = None


# Singleton compartido por los endpoints REST (app/api) y, en un hito
# posterior, por las tools FastMCP (app/mcp) — mismo punto de entrada para
# ambos canales.
job_manager = JobManager()
