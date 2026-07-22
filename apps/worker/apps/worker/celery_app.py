"""
Celery app — configurado com Redis broker e result backend.
Queues: default | etl | exports
"""
from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery(
    "mapa_voto",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "apps.worker.tasks.etl_tse",
        "apps.worker.tasks.etl_ibge",
        "apps.worker.tasks.exports",
    ],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_routes={
        "apps.worker.tasks.etl_*": {"queue": "etl"},
        "apps.worker.tasks.exports.*": {"queue": "exports"},
    },
    task_track_started=True,
    worker_prefetch_multiplier=1,  # ETL tasks são pesadas — sem prefetch
)
