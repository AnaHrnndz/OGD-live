"""Tools FastMCP: mismo canal de análisis (job_manager + ogd_adapter) que la
interfaz web, para que un agente IA pueda hacer todo lo que un usuario
humano puede hacer desde el formulario.
"""

import csv
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from app import config
from app.core.jobs import JobAlreadyRunningError, job_manager
from app.schemas import OgdParams

mcp = FastMCP("OGD-live")


def _write_tree_file(job_id: str, newick_content: str, filename: str) -> Path:
    upload_dir = config.UPLOAD_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    tree_path = upload_dir / Path(filename).name
    tree_path.write_text(newick_content)
    return tree_path


@mcp.tool
async def run_ogd_analysis(
    newick_content: str,
    tree_filename: str = "tree.nwk",
    taxonomy_type: str = "NCBI",
    rooting: str = "Midpoint",
    sp_delimitator: str = ".",
    sp_ovlap_all: float = 0.1,
    sp_ovlap_euk: Optional[float] = None,
    sp_ovlap_bact: Optional[float] = None,
    sp_ovlap_arq: Optional[float] = None,
    lineage_threshold: float = 0.05,
    best_taxa_threshold: float = 0.9,
    species_losses_perct: float = 0.7,
    no_inherit_outliers: bool = False,
    skip_get_pairs: bool = False,
) -> dict:
    """Lanza un análisis de delineación de Grupos Ortólogos (OGs) sobre un
    árbol génico en formato Newick.

    Devuelve inmediatamente un job_id (el análisis corre en segundo plano);
    usa get_job_status para consultar el progreso y get_results para leer
    los resultados una vez que el estado sea "done". Solo puede haber un
    análisis activo a la vez: si ya hay uno en curso, devuelve un error con
    el job_id del que está corriendo.
    """
    try:
        job_id = await job_manager.reserve_job_id()
    except JobAlreadyRunningError as exc:
        return {"error": str(exc), "active_job_id": exc.job_id}

    try:
        tree_path = _write_tree_file(job_id, newick_content, tree_filename)
    except OSError as exc:
        job_manager.release(job_id)
        return {"error": f"No se pudo guardar el árbol: {exc}"}

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

    return {"job_id": job_id, "status": job.status.value}


@mcp.tool
def get_job_status(job_id: str) -> dict:
    """Consulta el estado (pending/running/done/error) de un análisis
    lanzado con run_ogd_analysis."""
    job = job_manager.get(job_id)
    if job is None:
        return {"error": "Job no encontrado"}
    return {"job_id": job.job_id, "status": job.status.value, "error": job.error}


@mcp.tool
def list_jobs() -> list[dict]:
    """Lista todos los análisis conocidos por este servidor (de esta sesión)."""
    return [{"job_id": job.job_id, "status": job.status.value} for job in job_manager.list_jobs()]


@mcp.tool
def get_results(job_id: str, max_rows: int = 100) -> dict:
    """Devuelve un resumen parseado de los resultados de un análisis
    terminado, incluyendo hasta max_rows filas de la tabla de OGs
    (ogs_info.tsv), para que el agente pueda razonar sobre el contenido sin
    tener que descargar y parsear el archivo por su cuenta.
    """
    job = job_manager.get(job_id)
    if job is None:
        return {"error": "Job no encontrado"}
    if job.status.value != "done" or job.result is None:
        return {"error": f"El job no ha terminado (estado: {job.status.value})"}

    result = job.result
    ogs_info_rows: list[dict] = []
    if result.ogs_info_path.is_file():
        with result.ogs_info_path.open(newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                ogs_info_rows.append(row)

    return {
        "job_id": job_id,
        "elapsed_seconds": result.elapsed_seconds,
        "num_ogs_returned": len(ogs_info_rows),
        "ogs_info": ogs_info_rows,
    }
