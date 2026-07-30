"""Configuración centralizada: rutas de datos, límites y base de datos de taxonomía.

La base de datos NCBITaxa se pasa siempre vía `--user_taxonomy` (ver
app/core/ogd_adapter.py): el directorio por defecto de ETE4 puede no ser
escribible (Docker, HF Spaces, o este mismo entorno de desarrollo).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "data" / "uploads"
RESULTS_DIR = BASE_DIR / "data" / "results"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TAXONOMY_DB = Path(
    os.environ.get("OGD_TAXONOMY_DB", "/data2/databases/ETE/eggnog6/e6.taxa.sqlite")
)

MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("OGD_MAX_UPLOAD_MB", "20")) * 1024 * 1024

# Las bases de datos NCBITaxa (.sqlite) que un usuario podría subir como
# taxonomía propia pesan cientos de MB o más de 1GB (ver M5) — necesitan un
# límite mucho mayor que el de los árboles Newick.
MAX_TAXONOMY_UPLOAD_SIZE_BYTES = (
    int(os.environ.get("OGD_MAX_TAXONOMY_UPLOAD_MB", "2048")) * 1024 * 1024
)

# Tablas de resultados de eggNOG-mapper (.emapper.annotations): normalmente
# unos pocos MB a decenas de MB, pero se deja margen para proteomas grandes.
MAX_ANNOTATION_UPLOAD_SIZE_BYTES = (
    int(os.environ.get("OGD_MAX_ANNOTATION_UPLOAD_MB", "200")) * 1024 * 1024
)
