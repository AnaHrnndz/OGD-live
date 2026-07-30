"""Contrato de datos único para el pipeline OGD, compartido por la web y las tools MCP."""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


class OgdParams(BaseModel):
    """Parámetros de entrada para un análisis de delineación de OGs.

    Deliberadamente NO expone la ejecución de eggNOG-mapper en sí (Linux-only,
    requiere binarios y bases de datos externas pesadas) ni el módulo de
    recovery: siguen fuera de alcance para la v1. Sí permite anotar el árbol
    con una tabla de resultados de eggNOG-mapper ya calculada por el usuario
    (emapper_main_table), sin ejecutar eggNOG-mapper en el servidor.
    """

    tree_path: Path
    output_path: Path

    taxonomy_type: Literal["NCBI", "GTDB"] = "NCBI"
    user_taxonomy: Optional[Path] = None
    user_taxonomy_counter: Optional[Path] = None
    reftree: Optional[Path] = None
    sp_delimitator: str = "."

    rooting: Literal["Midpoint", "MinVar"] = "Midpoint"

    sp_ovlap_all: float = 0.1
    sp_ovlap_euk: Optional[float] = None
    sp_ovlap_bact: Optional[float] = None
    sp_ovlap_arq: Optional[float] = None
    lineage_threshold: float = 0.05
    best_taxa_threshold: float = 0.9
    species_losses_perct: float = 0.7
    no_inherit_outliers: bool = False

    raw_alg: Optional[Path] = None
    skip_get_pairs: bool = True

    emapper_main_table: Optional[Path] = None


class OgdResult(BaseModel):
    """Rutas a los archivos generados por un análisis, más su tiempo de ejecución."""

    output_path: Path
    tree_annot_path: Path
    ogs_info_path: Path
    seq2ogs_tsv_path: Path
    seq2ogs_jsonl_path: Path
    pairs_path: Optional[Path] = None
    strict_pairs_path: Optional[Path] = None
    elapsed_seconds: float
