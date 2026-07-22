FROM python:3.12-slim

WORKDIR /app

# System dependencies (GDAL for geopandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgdal-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY apps/api/pyproject.toml apps/api/
COPY packages/ packages/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -e packages/shared -e packages/db
RUN pip install --no-cache-dir -e apps/api[dev]

COPY apps/api/ apps/api/

EXPOSE 8000
