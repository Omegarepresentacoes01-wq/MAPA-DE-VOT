FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgdal-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/worker/pyproject.toml apps/worker/
COPY packages/ packages/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -e packages/shared -e packages/db -e packages/etl
RUN pip install --no-cache-dir -e apps/worker[dev]

COPY apps/worker/ apps/worker/
