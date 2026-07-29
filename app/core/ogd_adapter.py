"""Único punto de entrada al pipeline `run_ogd_pipeline` de OG_Delineation.

Tanto los endpoints REST (app/api) como las tools FastMCP (app/mcp) deben
llamar exclusivamente a `run_analysis` en vez de invocar `ogd.ogd_core`
directamente, para garantizar la misma paridad de comportamiento en ambos
canales.
"""

import argparse
import time

import ogd.utils as ogd_utils
from ogd.ogd_core import run_ogd_pipeline

from app.schemas import OgdParams, OgdResult


def _build_namespace(params: OgdParams) -> argparse.Namespace:
    """Traduce OgdParams a la argparse.Namespace que espera run_ogd_pipeline.

    Los campos relativos a eggNOG-mapper y al módulo de recovery quedan
    fijados a sus valores "desactivados" porque están fuera de alcance
    para la v1.
    """
    return argparse.Namespace(
        tree=params.tree_path,
        out_path=params.output_path,
        taxonomy_type=params.taxonomy_type,
        user_taxonomy=params.user_taxonomy,
        user_taxonomy_counter=params.user_taxonomy_counter,
        reftree=params.reftree,
        sp_delim=params.sp_delimitator,
        rooting=params.rooting,
        so_all=params.sp_ovlap_all,
        so_euk=params.sp_ovlap_euk,
        so_bact=params.sp_ovlap_bact,
        so_arq=params.sp_ovlap_arq,
        lineage_thr=params.lineage_threshold,
        best_tax_thr=params.best_taxa_threshold,
        sp_loss_perc=params.species_losses_perct,
        no_inherit_outliers=params.no_inherit_outliers,
        alg=params.raw_alg,
        skip_get_pairs=params.skip_get_pairs,
        # Fuera de alcance en v1: recovery y eggNOG-mapper siempre desactivados.
        run_recovery=None,
        run_emapper=False,
        emapper_cpu=4,
        emapper_num_workers=4,
        emapper_num_servers=1,
        emapper_no_usemem=False,
        emapper_dmnd=None,
        emapper_pfam=None,
        path2emapper_main=None,
        path2emapper_pfams=None,
        # La visualización se gestiona aparte (smartview_manager), no aquí.
        open_visualization=False,
        only_visualization=False,
        user_ip=None,
    )


def run_analysis(params: OgdParams) -> OgdResult:
    """Ejecuta el pipeline OGD completo y devuelve las rutas de sus resultados."""
    args = _build_namespace(params)
    args.out_path.mkdir(parents=True, exist_ok=True)

    start = time.monotonic()
    run_ogd_pipeline(args)
    elapsed = time.monotonic() - start

    # Reutiliza la misma función que usa el pipeline para nombrar sus salidas,
    # para no duplicar (y desincronizar) esa lógica de naming.
    clean_tree_name = ogd_utils.remove_file_extension(params.tree_path.name)
    out = params.output_path

    return OgdResult(
        output_path=out,
        tree_annot_path=out / f"{clean_tree_name}.tree_annot.nw",
        ogs_info_path=out / f"{clean_tree_name}.ogs_info.tsv",
        seq2ogs_tsv_path=out / f"{clean_tree_name}.seq2ogs.tsv",
        seq2ogs_jsonl_path=out / f"{clean_tree_name}.seq2ogs.jsonl",
        pairs_path=None if params.skip_get_pairs else out / f"{clean_tree_name}.pairs.tsv",
        strict_pairs_path=None if params.skip_get_pairs else out / f"{clean_tree_name}.strict_pairs.tsv",
        elapsed_seconds=elapsed,
    )
