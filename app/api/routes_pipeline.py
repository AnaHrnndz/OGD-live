"""Endpoint REST mínimo y bloqueante para lanzar un análisis OGD.

Sin cola de jobs ni progreso (SSE) todavía: ver M2 en el plan de desarrollo.
"""

import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import config
from app.core.ogd_adapter import run_analysis
from app.schemas import OgdParams

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


class AnalysisResponse(BaseModel):
    job_id: str
    elapsed_seconds: float
    files: dict[str, str]


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


@router.post("", response_model=AnalysisResponse)
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
) -> AnalysisResponse:
    job_id = uuid.uuid4().hex

    upload_dir = config.UPLOAD_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    tree_path = upload_dir / (Path(tree.filename or "tree.nw").name)

    size = 0
    with tree_path.open("wb") as out_file:
        while chunk := await tree.read(1024 * 1024):
            size += len(chunk)
            if size > config.MAX_UPLOAD_SIZE_BYTES:
                shutil.rmtree(upload_dir, ignore_errors=True)
                raise HTTPException(status_code=413, detail="Árbol demasiado grande")
            out_file.write(chunk)

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

    try:
        result = run_analysis(params)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    files = {}
    for logical_name, path in (
        ("tree_annot", result.tree_annot_path),
        ("ogs_info", result.ogs_info_path),
        ("seq2ogs_tsv", result.seq2ogs_tsv_path),
        ("seq2ogs_jsonl", result.seq2ogs_jsonl_path),
        ("pairs", result.pairs_path),
        ("strict_pairs", result.strict_pairs_path),
    ):
        if path is not None and path.is_file():
            files[logical_name] = f"/api/analyses/{job_id}/files/{path.name}"

    return AnalysisResponse(job_id=job_id, elapsed_seconds=result.elapsed_seconds, files=files)


@router.get("/{job_id}/files/{filename}")
async def download_file(job_id: str, filename: str) -> FileResponse:
    job_dir = _job_dir(job_id)
    file_path = _safe_file(job_dir, filename)
    return FileResponse(file_path, filename=filename)
