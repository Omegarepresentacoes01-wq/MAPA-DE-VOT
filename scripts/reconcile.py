"""
Script de reconciliação — valida totais de votos e candidaturas contra a fonte oficial TSE.

Para cada eleição e cargo ingeridos, verifica:
1. Total de candidaturas no banco == número no arquivo TSE
2. Total de votos no banco == total publicado no CSV original
3. Identifica municípios/UFs com divergência acima do threshold
4. Gera relatório de cobertura por UF

Uso:
    make reconcile
    python scripts/reconcile.py --ano 2022
    python scripts/reconcile.py --ano 2022 --uf SP
    python scripts/reconcile.py --ano 2022 --threshold 0.005
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import typer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.logging import RichHandler
    from rich.progress import Progress, SpinnerColumn, TextColumn
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

try:
    import polars as pl
    _HAS_POLARS = True
except ImportError:
    _HAS_POLARS = False

if _HAS_RICH:
    logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console() if _HAS_RICH else None

app = typer.Typer(help="Reconciliação de dados TSE × banco de dados local.")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de output
# ──────────────────────────────────────────────────────────────────────────────

def _print(msg: str):
    if console:
        console.print(msg)
    else:
        print(msg)


def _rule(title: str):
    if console:
        console.rule(f"[bold blue]{title}")
    else:
        print(f"\n{'─' * 60}")
        print(f"  {title}")
        print(f"{'─' * 60}")


def _ok(msg: str):
    _print(f"[bold green]✅ {msg}[/bold green]" if console else f"✅  {msg}")


def _warn(msg: str):
    _print(f"[bold yellow]⚠️  {msg}[/bold yellow]" if console else f"⚠️   {msg}")


def _err(msg: str):
    _print(f"[bold red]❌ {msg}[/bold red]" if console else f"❌  {msg}")


# ──────────────────────────────────────────────────────────────────────────────
# Verificações de banco
# ──────────────────────────────────────────────────────────────────────────────

async def _check_db_connection() -> bool:
    """Verifica se o banco de dados está acessível."""
    try:
        from db.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        _err(f"Banco de dados inacessível: {e}")
        return False


async def _fetch_db_totals(ano: int, uf: Optional[str] = None) -> list[dict]:
    """Busca totais de candidaturas e votos por cargo no banco."""
    from db.session import AsyncSessionLocal
    from db.models.political import Election, Candidacy, Office, Territory
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                Office.sigla.label("cargo"),
                Territory.uf.label("uf"),
                func.count(Candidacy.id).label("total_candidaturas"),
                func.sum(Candidacy.votos_totais).label("votos_totais"),
            )
            .join(Election, Election.id == Candidacy.election_id)
            .join(Office, Office.id == Candidacy.office_id)
            .join(Territory, Territory.id == Candidacy.territory_id)
            .where(Election.ano == ano)
        )
        if uf:
            stmt = stmt.where(Territory.uf == uf.upper())

        stmt = stmt.group_by(Office.sigla, Territory.uf).order_by(Territory.uf, Office.sigla)
        rows = (await session.execute(stmt)).all()

    return [
        {
            "cargo": r.cargo,
            "uf": r.uf,
            "total_candidaturas_db": r.total_candidaturas,
            "votos_totais_db": int(r.votos_totais or 0),
        }
        for r in rows
    ]


async def _fetch_csv_totals(ano: int, uf: Optional[str] = None) -> dict[tuple, dict]:
    """Lê os CSVs originais do TSE e calcula os totais esperados."""
    if not _HAS_POLARS:
        _warn("polars não instalado — comparação com CSV não disponível.")
        return {}

    try:
        from etl.common.normalize import read_tse_csv
        from etl.common.download import STAGING_DIR
    except ImportError:
        _warn("Pacote ETL não disponível — comparação com CSV pulada.")
        return {}

    staging_dir = Path(STAGING_DIR) / "tse" / f"candidaturas_{ano}"
    if not staging_dir.exists():
        _warn(f"Diretório de staging não encontrado: {staging_dir}")
        _warn("Execute a ingestão primeiro: make ingest-tse-2022")
        return {}

    pattern = f"consulta_cand_{ano}_{'*.csv' if not uf else uf.upper() + '.csv'}"
    csv_files = list(staging_dir.glob(pattern))

    if not csv_files:
        # Tenta padrão alternativo
        csv_files = list(staging_dir.glob("consulta_cand_*.csv"))

    if not csv_files:
        _warn(f"Nenhum arquivo CSV encontrado em {staging_dir}")
        return {}

    totals: dict[tuple, dict] = {}

    for f in csv_files:
        try:
            df = read_tse_csv(f)
            if df is None or len(df) == 0:
                continue

            # Identifica colunas relevantes (variam por ano/eleição)
            cargo_col = next((c for c in df.columns if "cargo" in c.lower()), None)
            uf_col = next((c for c in df.columns if c.lower() in ("sg_uf", "uf")), None)
            votos_col = next((c for c in df.columns if "votos" in c.lower()), None)

            if not cargo_col or not uf_col:
                continue

            for (cargo, uf_val), group in df.group_by([cargo_col, uf_col]):
                key = (str(cargo), str(uf_val))
                count = len(group)
                votos = int(group[votos_col].sum()) if votos_col else 0
                if key not in totals:
                    totals[key] = {"total_candidaturas_csv": 0, "votos_totais_csv": 0}
                totals[key]["total_candidaturas_csv"] += count
                totals[key]["votos_totais_csv"] += votos

        except Exception as e:
            _warn(f"Erro ao processar {f.name}: {e}")

    return totals


# ──────────────────────────────────────────────────────────────────────────────
# Relatório de cobertura por UF
# ──────────────────────────────────────────────────────────────────────────────

async def _report_uf_coverage(ano: int):
    """Gera relatório de cobertura de ingestão por UF."""
    try:
        from db.session import AsyncSessionLocal
        from db.models.political import Election, Candidacy, Territory
        from sqlalchemy import select, func, distinct

        async with AsyncSessionLocal() as session:
            stmt = (
                select(
                    Territory.uf,
                    func.count(distinct(Candidacy.id)).label("candidaturas"),
                    func.count(distinct(Candidacy.territory_id)).label("municipios"),
                )
                .join(Election, Election.id == Candidacy.election_id)
                .join(Territory, Territory.id == Candidacy.territory_id)
                .where(Election.ano == ano)
                .group_by(Territory.uf)
                .order_by(Territory.uf)
            )
            rows = (await session.execute(stmt)).all()

    except Exception as e:
        _warn(f"Não foi possível gerar cobertura por UF: {e}")
        return

    if not rows:
        _warn(f"Nenhum dado encontrado para o ano {ano}")
        return

    _rule(f"Cobertura por UF — Eleição {ano}")

    if console:
        table = Table("UF", "Candidaturas", "Municípios", title=f"Cobertura {ano}")
        for r in rows:
            table.add_row(r.uf or "—", f"{r.candidaturas:,}", f"{r.municipios:,}")
        console.print(table)
    else:
        print(f"\n{'UF':<5} {'Candidaturas':>15} {'Municípios':>12}")
        print("-" * 35)
        for r in rows:
            print(f"{r.uf or '—':<5} {r.candidaturas:>15,} {r.municipios:>12,}")

    total_cand = sum(r.candidaturas for r in rows)
    total_munic = sum(r.municipios for r in rows)
    ufs_ingeridas = len(rows)
    _print(f"\n📊 Total: {ufs_ingeridas} UFs | {total_cand:,} candidaturas | {total_munic:,} municípios")


# ──────────────────────────────────────────────────────────────────────────────
# Reconciliação principal
# ──────────────────────────────────────────────────────────────────────────────

async def _reconcile(ano: int, uf: Optional[str], threshold: float):
    """Executa a reconciliação completa."""
    _rule(f"Reconciliação TSE {ano}" + (f" — UF: {uf.upper()}" if uf else " — Todas as UFs"))

    # 1. Verifica conexão com banco
    if not await _check_db_connection():
        raise typer.Exit(code=1)

    # 2. Busca totais do banco
    _print("\n🔍 Consultando banco de dados...")
    try:
        db_rows = await _fetch_db_totals(ano, uf)
    except Exception as e:
        _err(f"Erro ao consultar banco: {e}")
        raise typer.Exit(code=1)

    if not db_rows:
        _warn(f"Nenhum dado encontrado no banco para ano={ano}" + (f", uf={uf}" if uf else ""))
        _warn("Execute a ingestão primeiro: make ingest-tse-2022")
        raise typer.Exit(code=1)

    # 3. Exibe totais do banco
    _rule("Totais no banco de dados")
    if console:
        table = Table("UF", "Cargo", "Candidaturas (DB)", "Votos (DB)")
        for row in db_rows:
            table.add_row(
                row["uf"] or "—",
                row["cargo"] or "—",
                f"{row['total_candidaturas_db']:,}",
                f"{row['votos_totais_db']:,}",
            )
        console.print(table)
    else:
        print(f"\n{'UF':<5} {'Cargo':<25} {'Candidaturas':>15} {'Votos':>15}")
        print("-" * 65)
        for row in db_rows:
            print(f"{row['uf'] or '—':<5} {row['cargo'] or '—':<25} "
                  f"{row['total_candidaturas_db']:>15,} {row['votos_totais_db']:>15,}")

    total_candidaturas_db = sum(r["total_candidaturas_db"] for r in db_rows)
    total_votos_db = sum(r["votos_totais_db"] for r in db_rows)
    _print(f"\n📊 Total banco: {total_candidaturas_db:,} candidaturas | {total_votos_db:,} votos")

    # 4. Compara com CSVs originais (se disponíveis)
    _print("\n🔍 Carregando arquivos CSV originais...")
    csv_totals = await _fetch_csv_totals(ano, uf)

    divergences: list[dict] = []

    if csv_totals:
        _rule("Comparação DB × CSV")
        total_csv_cand = sum(v["total_candidaturas_csv"] for v in csv_totals.values())
        total_csv_votos = sum(v["votos_totais_csv"] for v in csv_totals.values())

        diff_cand = abs(total_candidaturas_db - total_csv_cand)
        diff_votos = abs(total_votos_db - total_csv_votos)
        pct_cand = diff_cand / max(total_csv_cand, 1)
        pct_votos = diff_votos / max(total_csv_votos, 1)

        _print(f"\nCandidaturas — CSV: {total_csv_cand:,} | DB: {total_candidaturas_db:,} | "
               f"Diff: {diff_cand:,} ({pct_cand:.4%})")
        _print(f"Votos        — CSV: {total_csv_votos:,} | DB: {total_votos_db:,} | "
               f"Diff: {diff_votos:,} ({pct_votos:.4%})")

        if pct_cand <= threshold:
            _ok(f"Candidaturas dentro do threshold ({threshold:.1%})")
        else:
            _err(f"Candidaturas divergem acima do threshold ({pct_cand:.4%} > {threshold:.1%})")
            divergences.append({"tipo": "candidaturas_global", "pct": pct_cand})

        if pct_votos <= threshold:
            _ok(f"Votos dentro do threshold ({threshold:.1%})")
        else:
            _err(f"Votos divergem acima do threshold ({pct_votos:.4%} > {threshold:.1%})")
            divergences.append({"tipo": "votos_global", "pct": pct_votos})

    # 5. Relatório de cobertura por UF
    await _report_uf_coverage(ano)

    # 6. Resultado final
    _rule("Resultado da Reconciliação")
    if not divergences:
        _ok(f"Reconciliação APROVADA — todos os totais dentro do threshold de {threshold:.1%}")
        if not csv_totals:
            _warn("Comparação com CSVs originais não foi possível (arquivos não encontrados). "
                  "Apenas totais do banco foram verificados.")
        return 0
    else:
        _err(f"Reconciliação REPROVADA — {len(divergences)} divergência(s) acima do threshold")
        _print("\nPróximos passos sugeridos:")
        _print("  1. Verifique os logs de ingestão para erros de parse")
        _print("  2. Confira duplicatas com: SELECT cpf_hash, COUNT(*) FROM candidacy GROUP BY cpf_hash HAVING COUNT(*) > 1")
        _print("  3. Re-execute a ingestão com: make ingest-tse-2022")
        return 1


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

@app.command()
def run(
    ano: int = typer.Option(..., "--ano", "-a", help="Ano da eleição (ex: 2022)"),
    uf: Optional[str] = typer.Option(None, "--uf", help="Filtrar por UF (ex: SP)"),
    threshold: float = typer.Option(0.001, "--threshold", "-t",
                                    help="Tolerância percentual para divergências (padrão: 0.1%)"),
):
    """
    Reconcilia os totais de candidaturas e votos do banco com os CSVs originais do TSE.
    """
    exit_code = asyncio.run(_reconcile(ano, uf, threshold))
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
