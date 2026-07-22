"""
Celery tasks — pipeline IBGE.
Fila: 'etl'
"""
from __future__ import annotations

import logging
from typing import Optional

from apps.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="etl.ibge.territories",
    bind=True,
    max_retries=2,
    default_retry_delay=600,   # 10 min (arquivos grandes)
    queue="etl",
    acks_late=True,
    time_limit=7200,           # 2h máximo
    soft_time_limit=6000,
)
def ingest_territories(self, uf: Optional[str] = None, ano: int = 2022, upload_minio: bool = True):
    """
    Ingestão de malhas territoriais IBGE (shapefile de municípios).
    Após ingestão, reconcilia os códigos proxy criados na Etapa 3.
    """
    try:
        logger.info(f"[Celery] Iniciando malhas IBGE {ano} uf={uf}")
        from etl.ibge.territories import run
        run(uf=uf, ano=ano, upload_minio=upload_minio)
        logger.info("[Celery] Malhas IBGE concluídas")
    except Exception as exc:
        logger.error(f"[Celery] Erro malhas IBGE: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="etl.ibge.census",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="etl",
    acks_late=True,
)
def ingest_census(self, ano: int = 2022, upload_minio: bool = True):
    """Ingestão de dados Censo via SIDRA API."""
    try:
        logger.info(f"[Celery] Iniciando Censo IBGE {ano}")
        from etl.ibge.census import run
        run(ano=ano, upload_minio=upload_minio)
        logger.info("[Celery] Censo IBGE concluído")
    except Exception as exc:
        logger.error(f"[Celery] Erro Censo IBGE: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="etl.ibge.build_indexes",
    queue="etl",
    acks_late=True,
)
def build_spatial_indexes():
    """Constrói índices espaciais GIST após ingestão das geometrias."""
    import asyncio
    from etl.ibge.territories import build_spatial_indexes as _build
    asyncio.run(_build())


@celery_app.task(
    name="search.reindex",
    queue="etl",
    acks_late=True,
    time_limit=3600,
)
def reindex_search():
    """Reindexação completa do Meilisearch."""
    import asyncio
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../scripts"))
    from index_search import run_indexer
    asyncio.run(run_indexer())
