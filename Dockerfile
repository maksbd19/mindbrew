FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libcairo2 \
        libcairo2-dev \
        libexpat1 \
        libgdk-pixbuf-2.0-0 \
        libglpk40 \
        libpango-1.0-0 \
        pkg-config \
        shared-mime-info \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y gcc libcairo2-dev pkg-config \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY api/ api/
COPY mindbrew_v2/ mindbrew_v2/
COPY alembic.ini .
COPY scripts/docker-entrypoint-api.sh scripts/docker-entrypoint-api.sh
COPY data/models/ data/models/
COPY data/scenarios/ data/scenarios/

RUN chmod +x scripts/docker-entrypoint-api.sh \
    && mkdir -p data/gem_models

EXPOSE 8000

ENTRYPOINT ["scripts/docker-entrypoint-api.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
