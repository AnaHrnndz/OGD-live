"""Prueba manual del adaptador OGD contra el árbol de ejemplo del submodule.

Uso:
    python scripts/test_adapter.py
"""

import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.core.ogd_adapter import run_analysis
from app.schemas import OgdParams

EXAMPLE_TREE = REPO_ROOT / "third_party" / "OG_Delineation" / "data" / "P53.fa.nw"
OUTPUT_DIR = REPO_ROOT / "data" / "results" / "test_adapter"

# Base de datos NCBITaxa ya construida (evita depender del directorio por
# defecto de ETE4, no escribible en este entorno). Sobreescribible por
# entorno para no depender de una ruta local de una máquina en concreto.
TAXONOMY_DB = os.environ.get(
    "OGD_TAXONOMY_DB", "/data2/databases/ETE/eggnog6/e6.taxa.sqlite"
)


def main() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    params = OgdParams(
        tree_path=EXAMPLE_TREE,
        output_path=OUTPUT_DIR,
        user_taxonomy=Path(TAXONOMY_DB),
    )
    result = run_analysis(params)

    print(f"Tiempo de ejecución: {result.elapsed_seconds:.2f}s")
    for field_name in (
        "tree_annot_path",
        "ogs_info_path",
        "seq2ogs_tsv_path",
        "seq2ogs_jsonl_path",
        "pairs_path",
        "strict_pairs_path",
    ):
        path = getattr(result, field_name)
        status = "OK" if path and path.is_file() else "FALTA"
        print(f"[{status}] {field_name}: {path}")


if __name__ == "__main__":
    main()
