"""Descarga y construye la base de datos de taxonomía NCBI en una ruta propia
del proyecto, en vez de en el directorio por defecto de ETE4 (que puede no
ser escribible, p.ej. en Docker/HF Spaces).

Uso:
    python scripts/setup_taxonomy.py [--dest DIR]

Resultado: <DIR>/taxa.sqlite, listo para usarse vía la variable de entorno
OGD_TAXONOMY_DB=<DIR>/taxa.sqlite.
"""

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAXONOMY_DIR = REPO_ROOT / "data" / "taxonomy"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_TAXONOMY_DIR)
    args = parser.parse_args()

    taxonomy_dir = args.dest
    taxonomy_dir.mkdir(parents=True, exist_ok=True)
    taxdump_file = taxonomy_dir / "taxdump.tar.gz"
    dbfile = taxonomy_dir / "taxa.sqlite"

    if dbfile.exists():
        print(f"Ya existe {dbfile}, no se reconstruye.")
        return

    from ete4 import NCBITaxa
    from ete4.ncbi_taxonomy.ncbiquery import update_local_taxdump

    print(f"Descargando taxdump en {taxdump_file} ...")
    update_local_taxdump(str(taxdump_file))

    print(f"Construyendo {dbfile} a partir del taxdump local ...")
    NCBITaxa(dbfile=str(dbfile), taxdump_file=str(taxdump_file))

    print("Listo.")


if __name__ == "__main__":
    main()
