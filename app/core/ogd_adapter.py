"""Único punto de entrada al pipeline `run_ogd_pipeline` de OG_Delineation.

Tanto los endpoints REST (app/api) como las tools FastMCP (app/mcp) deben
llamar exclusivamente a `run_analysis` en vez de invocar `ogd.ogd_core`
directamente, para garantizar la misma paridad de comportamiento en ambos
canales.
"""

import argparse
import logging
import time

import ogd.utils as ogd_utils
from ogd.ogd_core import run_ogd_pipeline

from app.schemas import OgdParams, OgdResult


class _ErrorCapturingHandler(logging.Handler):
    """Captura los `logging.error(...)` que OGD emite justo antes de un
    `sys.exit(1)` en validaciones de entrada (delimitador de especie que no
    coincide, taxid no encontrado, etc.).

    `sys.exit` lanza `SystemExit`, que NO hereda de `Exception` y no lleva
    el mensaje real (solo el código de salida) — sin esto, el error se
    perdería y el job se quedaría colgado en "running" para siempre (ver
    memoria del proyecto: JobManager solo captura `Exception`).
    """

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


# Mensajes de OGD orientados a un usuario de CLI (referencian flags como
# --sp_delim que no existen en el formulario web) — se les añade una pista
# en el contexto de la web, sin ocultar el mensaje técnico original.
_ERROR_HINTS = (
    (
        "Species delimiter",
        "This usually means the 'Species delimiter' field in the form doesn't "
        "match how species IDs are encoded in your tree's leaf names (e.g. "
        "'9606.ENSP00000269305' uses '.' as the delimiter).",
    ),
    (
        "Taxid not found in taxonomy DB",
        "This can happen if a species ID in your tree isn't a valid NCBI taxid, "
        "or if your tree uses a different taxonomy convention (e.g. GTDB) than "
        "the taxonomy database in use — try uploading your own under "
        "'Advanced options' if you're using a non-NCBI naming scheme.",
    ),
    (
        "valid Newick format",
        "Check that the uploaded file is really a Newick tree (.nw/.nwk) and "
        "not something else (e.g. an alignment or a plain text file).",
    ),
)


def _enhance_error_message(message: str) -> str:
    for marker, hint in _ERROR_HINTS:
        if marker in message:
            return f"{message} {hint}"
    return message


def _check_emapper_overlap(tree_path, emapper_table_path) -> None:
    """Comprueba que al menos una secuencia de la tabla de eggNOG-mapper
    coincide con una hoja del árbol antes de lanzar el pipeline completo.

    OGD anota por lookup exacto de `node.name` contra la primera columna de
    la tabla (ver `_annot_tree_main_table` en emapper_annotate.py); si
    ninguna coincide, el árbol se anota igualmente pero sin ningún dato
    (todo "-") y sin ningún aviso — lo comprobamos nosotros para no dejar
    pasar un análisis "correcto" que en realidad no anotó nada.
    """
    from ete4 import Tree

    tree = Tree(open(tree_path))
    leaf_names = {leaf.name for leaf in tree.leaves()}

    table_seqs = set()
    with emapper_table_path.open() as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            table_seqs.add(line.split("\t", 1)[0])

    if table_seqs and leaf_names.isdisjoint(table_seqs):
        raise ValueError(
            "None of the sequences in the eggNOG-mapper table match the tree's "
            "leaf names — the tree would be annotated with no data. Check that "
            "the 'query' column of your table uses the same sequence naming as "
            "your tree's leaves."
        )


def _build_namespace(params: OgdParams) -> argparse.Namespace:
    """Traduce OgdParams a la argparse.Namespace que espera run_ogd_pipeline.

    Los campos relativos a ejecutar eggNOG-mapper y al módulo de recovery
    quedan fijados a sus valores "desactivados" porque están fuera de
    alcance para la v1. `path2emapper_main` sí se expone: anota el árbol con
    una tabla de resultados de eggNOG-mapper ya calculada, sin ejecutar
    eggNOG-mapper (requiere third_party/OG_Delineation con el fix de
    ogd_dev@d384326 o posterior — ver memoria del proyecto).
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
        path2emapper_main=params.emapper_main_table,
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

    if params.emapper_main_table is not None:
        _check_emapper_overlap(params.tree_path, params.emapper_main_table)

    handler = _ErrorCapturingHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    try:
        start = time.monotonic()
        run_ogd_pipeline(args)
        elapsed = time.monotonic() - start
    except SystemExit as exc:
        # Varios puntos de validación de OGD hacen varias llamadas a
        # logging.error(...) para describir un único fallo (mensaje
        # principal + detalle + sugerencia) antes del sys.exit(1) — se unen
        # todas para no perder contexto.
        detail = " ".join(handler.messages) if handler.messages else (
            f"OG_Delineation terminó con un error (código de salida {exc.code}) sin más detalle."
        )
        raise RuntimeError(_enhance_error_message(detail)) from exc
    finally:
        root_logger.removeHandler(handler)

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
