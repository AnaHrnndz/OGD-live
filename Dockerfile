# ete4 no publica wheel manylinux para esta combinación de Python/plataforma
# (se comprobó localmente: pip lo compila desde código fuente), así que hace
# falta un compilador C. FastRoot/numpy/scipy/cvxopt sí usan wheels binarios.
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar primero solo lo necesario para instalar dependencias: aprovecha la
# cache de capas de Docker cuando solo cambia el código de la app.
COPY requirements.txt ./
COPY third_party/OG_Delineation ./third_party/OG_Delineation
RUN pip install --no-cache-dir -r requirements.txt

# Construir la base de datos de taxonomía NCBI en build-time (no en cada
# arranque): en Hugging Face Spaces (tier gratis) el contenedor se reinicia
# tras dormir por inactividad con disco efímero, así que descargarla en cada
# arranque añadiría varios minutos de espera en cada "despertar" del Space.
# Se borra el taxdump.tar.gz tras construir la base (ya no hace falta) en el
# mismo RUN para que no quede en la capa de la imagen.
COPY scripts/setup_taxonomy.py ./scripts/setup_taxonomy.py
RUN python scripts/setup_taxonomy.py --dest /app/data/taxonomy \
    && rm -f /app/data/taxonomy/taxdump.tar.gz

COPY app ./app

ENV OGD_TAXONOMY_DB=/app/data/taxonomy/taxa.sqlite
ENV PORT=7860

EXPOSE 7860

# tini como PID 1: hace de proceso init y reaping de zombis para el
# subproceso de Smartview que lanza app/core/smartview_manager.py.
ENTRYPOINT ["tini", "-g", "--"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
