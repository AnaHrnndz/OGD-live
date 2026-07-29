"""Endpoints REST para lanzar análisis OGD, seguir su progreso y descargar
resultados. La ejecución es asíncrona (JobManager); ver M1 para la versión
bloqueante original.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app import config
from app.core.jobs import Job, JobAlreadyRunningError, JobStatus, job_manager
from app.schemas import OgdParams, OgdResult

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

_RESULT_FILE_FIELDS = (
    ("tree_annot", "tree_annot_path"),
    ("ogs_info", "ogs_info_path"),
    ("seq2ogs_tsv", "seq2ogs_tsv_path"),
    ("seq2ogs_jsonl", "seq2ogs_jsonl_path"),
    ("pairs", "pairs_path"),
    ("strict_pairs", "strict_pairs_path"),
)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    error: Optional[str] = None
    files: dict[str, str] = {}


def _files_for_result(job_id: str, result: Optional[OgdResult]) -> dict[str, str]:
    if result is None:
        return {}
    files = {}
    for logical_name, attr in _RESULT_FILE_FIELDS:
        path = getattr(result, attr)
        if path is not None and path.is_file():
            files[logical_name] = f"/api/analyses/{job_id}/files/{path.name}"
    return files


def _job_status_response(job: Job) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        error=job.error,
        files=_files_for_result(job.job_id, job.result),
    )


def _job_dir(job_id: str) -> Path:
    """Resuelve el directorio de resultados de un job, rechazando path traversal."""
    results_root = config.RESULTS_DIR.resolve()
    job_dir = (results_root / job_id).resolve()
    if job_dir.parent != results_root:
        raise HTTPException(status_code=400, detail="job_id inválido")
    return job_dir


def _safe_file(job_dir: Path, filename: str) -> Path:
    """Resuelve un archivo dentro de job_dir, rechazando path traversal."""
    file_path = (job_dir / filename).resolve()
    if file_path.parent != job_dir or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return file_path


@router.post("", response_model=JobStatusResponse, status_code=202)
async def create_analysis(
    tree: UploadFile = File(..., description="Árbol génico en formato Newick (.nwk/.nw)"),
    taxonomy_type: str = Form("NCBI"),
    rooting: str = Form("Midpoint"),
    sp_delimitator: str = Form("."),
    sp_ovlap_all: float = Form(0.1),
    sp_ovlap_euk: Optional[float] = Form(None),
    sp_ovlap_bact: Optional[float] = Form(None),
    sp_ovlap_arq: Optional[float] = Form(None),
    lineage_threshold: float = Form(0.05),
    best_taxa_threshold: float = Form(0.9),
    species_losses_perct: float = Form(0.7),
    no_inherit_outliers: bool = Form(False),
    skip_get_pairs: bool = Form(False),
) -> JobStatusResponse:
    try:
        job_id = await job_manager.reserve_job_id()
    except JobAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    upload_dir = config.UPLOAD_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    tree_path = upload_dir / Path(tree.filename or "tree.nw").name

    try:
        size = 0
        with tree_path.open("wb") as out_file:
            while chunk := await tree.read(1024 * 1024):
                size += len(chunk)
                if size > config.MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(status_code=413, detail="Árbol demasiado grande")
                out_file.write(chunk)
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        job_manager.release(job_id)
        raise

    params = OgdParams(
        tree_path=tree_path,
        output_path=config.RESULTS_DIR / job_id,
        taxonomy_type=taxonomy_type,
        user_taxonomy=config.TAXONOMY_DB,
        rooting=rooting,
        sp_delimitator=sp_delimitator,
        sp_ovlap_all=sp_ovlap_all,
        sp_ovlap_euk=sp_ovlap_euk,
        sp_ovlap_bact=sp_ovlap_bact,
        sp_ovlap_arq=sp_ovlap_arq,
        lineage_threshold=lineage_threshold,
        best_taxa_threshold=best_taxa_threshold,
        species_losses_perct=species_losses_perct,
        no_inherit_outliers=no_inherit_outliers,
        skip_get_pairs=skip_get_pairs,
    )

    job = job_manager.register(job_id, params)
    await job_manager.start(job)

    return _job_status_response(job)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_analysis(job_id: str) -> JobStatusResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return _job_status_response(job)


@router.get("/{job_id}/events")
async def stream_analysis_events(job_id: str) -> StreamingResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    async def event_stream():
        last_status = None
        while True:
            if job.status != last_status:
                last_status = job.status
                yield f"event: status\ndata: {job.status.value}\n\n"
            if job.status in (JobStatus.DONE, JobStatus.ERROR):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{job_id}/files/{filename}")
async def download_file(job_id: str, filename: str) -> FileResponse:
    job_dir = _job_dir(job_id)
    file_path = _safe_file(job_dir, filename)
    return FileResponse(file_path, filename=filename)
