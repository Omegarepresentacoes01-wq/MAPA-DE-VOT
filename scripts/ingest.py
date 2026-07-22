"""
CLI de ingestão — ponto de entrada unificado para todos os pipelines.

Uso:
  python scripts/ingest.py tse --ano 2022
  python scripts/ingest.py tse --ano 2022 --uf SP
  python scripts/ingest.py tse --ano 2022 --pipeline resultados
  python scripts/ingest.py ibge --tipo territories
  python scripts/ingest.py ibge --tipo census --ano 2022
"""
import logging
import os
import sys
from typing import Optional

import typer
from rich.logging import RichHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=True)],
)

app = typer.Typer(help="Mapa de Voto — CLI de ingestão de dados oficiais")
tse_app = typer.Typer(help="Pipelines TSE")
ibge_app = typer.Typer(help="Pipelines IBGE")
app.add_typer(tse_app, name="tse")
app.add_typer(ibge_app, name="ibge")


@tse_app.command("candidaturas")
def tse_candidaturas(
    ano: int = typer.Option(..., help="Ano da eleição"),
    uf: Optional[str] = typer.Option(None, help="UF (ex: SP). Omitir para nacional."),
    no_minio: bool = typer.Option(False, help="Desabilita upload MinIO"),
):
    """Ingestão de candidaturas TSE."""
    from etl.tse.candidatures import run
    run(ano=ano, uf=uf, upload_minio=not no_minio)


@tse_app.command("resultados")
def tse_resultados(
    ano: int = typer.Option(...),
    turno: int = typer.Option(1),
    uf: Optional[str] = typer.Option(None),
    no_minio: bool = typer.Option(False),
):
    """Ingestão de resultados eleitorais TSE."""
    from etl.tse.results import run
    run(ano=ano, turno=turno, uf=uf, upload_minio=not no_minio)


@tse_app.command("financas")
def tse_financas(
    ano: int = typer.Option(...),
    uf: Optional[str] = typer.Option(None),
    no_minio: bool = typer.Option(False),
):
    """Ingestão de receitas e despesas TSE."""
    from etl.tse.finances import run
    run(ano=ano, uf=uf, upload_minio=not no_minio)


@tse_app.callback(invoke_without_command=False)
def tse_main(
    ano: int = typer.Option(..., help="Ano da eleição (obrigatório)"),
    uf: Optional[str] = typer.Option(None, help="UF (ex: SP). Omitir para nacional."),
    pipeline: str = typer.Option(
        "tudo",
        help="Pipeline a executar: candidaturas | resultados | financas | tudo",
    ),
    no_minio: bool = typer.Option(False),
):
    """
    Executa pipelines TSE. Quando chamado sem subcomando, use --pipeline.
    """
    if pipeline in ("candidaturas", "tudo"):
        from etl.tse.candidatures import run
        run(ano=ano, uf=uf, upload_minio=not no_minio)

    if pipeline in ("resultados", "tudo"):
        from etl.tse.results import run
        run(ano=ano, uf=uf, upload_minio=not no_minio)

    if pipeline in ("financas", "tudo"):
        from etl.tse.finances import run
        run(ano=ano, uf=uf, upload_minio=not no_minio)


@ibge_app.command("territories")
def ibge_territories(
    uf: Optional[str] = typer.Option(None, help="UF específica ou todas"),
    no_minio: bool = typer.Option(False),
):
    """Ingestão de malhas territoriais IBGE (municípios)."""
    from etl.ibge.territories import run
    run(uf=uf, upload_minio=not no_minio)


@ibge_app.command("census")
def ibge_census(
    ano: int = typer.Option(2022, help="Ano do Censo"),
    no_minio: bool = typer.Option(False),
):
    """Ingestão de dados do Censo IBGE via SIDRA."""
    from etl.ibge.census import run
    run(ano=ano, upload_minio=not no_minio)


@ibge_app.callback(invoke_without_command=False)
def ibge_main(
    tipo: str = typer.Option("territories", help="territories | census"),
    uf: Optional[str] = typer.Option(None),
    ano: int = typer.Option(2022),
    no_minio: bool = typer.Option(False),
):
    """Executa pipeline IBGE."""
    if tipo == "territories":
        from etl.ibge.territories import run
        run(uf=uf, upload_minio=not no_minio)
    elif tipo == "census":
        from etl.ibge.census import run
        run(ano=ano, upload_minio=not no_minio)


if __name__ == "__main__":
    app()
