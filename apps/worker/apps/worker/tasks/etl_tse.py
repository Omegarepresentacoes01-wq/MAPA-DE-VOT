"""
Celery tasks — pipeline TSE.
Fila: 'etl'
"""
from __future__ import annotations

import logging
from typing import Optional

from apps.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="etl.tse.candidatures",
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 5 min
    queue="etl",
    acks_late=True,
)
def ingest_candidatures(self, ano: int, uf: Optional[str] = None, upload_minio: bool = True):
    """
    Ingestão de candidaturas TSE para um ano.
    Chama o pipeline etl.tse.candidatures.run().

    Uso:
      ingest_candidatures.delay(ano=2022, uf="SP")
      ingest_candidatures.delay(ano=2022)  # todas as UFs
    """
    try:
        logger.info(f"[Celery] Iniciando candidaturas TSE {ano} uf={uf}")
        from etl.tse.candidatures import run
        run(ano=ano, uf=uf, upload_minio=upload_minio)
        logger.info(f"[Celery] Candidaturas TSE {ano} concluídas")
    except Exception as exc:
        logger.error(f"[Celery] Erro candidaturas: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="etl.tse.results",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="etl",
    acks_late=True,
)
def ingest_results(self, ano: int, turno: int = 1, uf: Optional[str] = None, upload_minio: bool = True):
    """Ingestão de resultados eleitorais TSE."""
    try:
        logger.info(f"[Celery] Iniciando resultados TSE {ano} T{turno} uf={uf}")
        from etl.tse.results import run
        run(ano=ano, turno=turno, uf=uf, upload_minio=upload_minio)
    except Exception as exc:
        logger.error(f"[Celery] Erro resultados: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="etl.tse.finances",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="etl",
    acks_late=True,
)
def ingest_finances(self, ano: int, uf: Optional[str] = None, upload_minio: bool = True):
    """Ingestão de receitas e despesas de campanha TSE."""
    try:
        logger.info(f"[Celery] Iniciando finanças TSE {ano}")
        from etl.tse.finances import run
        run(ano=ano, uf=uf, upload_minio=upload_minio)
    except Exception as exc:
        logger.error(f"[Celery] Erro finanças: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="etl.tse.full_pipeline",
    bind=True,
    max_retries=1,
    queue="etl",
    acks_late=True,
)
def full_tse_pipeline(self, ano: int, upload_minio: bool = True):
    """
    Pipeline completo TSE: candidaturas → resultados → finanças.
    Executa sequencialmente (candidaturas devem existir antes dos resultados).
    """
    try:
        logger.info(f"[Celery] Pipeline completo TSE {ano} iniciando")

        from etl.tse.candidatures import run as run_cand
        run_cand(ano=ano, upload_minio=upload_minio)

        from etl.tse.results import run as run_res
        run_res(ano=ano, turno=1, upload_minio=upload_minio)
        try:
            run_res(ano=ano, turno=2, upload_minio=upload_minio)
        except Exception:
            logger.info("Segundo turno não disponível ou sem dados.")

        from etl.tse.finances import run as run_fin
        run_fin(ano=ano, upload_minio=upload_minio)

        logger.info(f"[Celery] Pipeline TSE {ano} concluído")
    except Exception as exc:
        logger.error(f"[Celery] Pipeline TSE falhou: {exc}", exc_info=True)
        raise self.retry(exc=exc)
