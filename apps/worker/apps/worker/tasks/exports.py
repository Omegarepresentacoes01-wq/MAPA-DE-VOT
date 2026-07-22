"""Tasks de exportação assíncrona — XLSX, PDF, CSV."""
from apps.worker.celery_app import app


@app.task(name="apps.worker.tasks.exports.export_candidate", bind=True)
def export_candidate(self, candidacy_id: str, formato: str = "xlsx") -> str:
    """Gera exportação de candidato e retorna URL do arquivo no MinIO."""
    # Implementação completa na Etapa 12
    raise NotImplementedError("Exportações na Etapa 12")


@app.task(name="apps.worker.tasks.exports.export_territory", bind=True)
def export_territory(self, codigo_ibge: str, election_id: str, formato: str = "xlsx") -> str:
    """Gera exportação de resultados de um território."""
    raise NotImplementedError("Exportações na Etapa 12")
