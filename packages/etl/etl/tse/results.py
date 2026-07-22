"""
Pipeline de resultados eleitorais TSE — Etapa 4.

Fonte: dadosabertos.tse.jus.br
Arquivo: votacao_candidato_munzona_{ano}.zip → votacao_candidato_munzona_{ano}_{UF}.csv

Este pipeline depende da Etapa 3 (candidaturas já ingeridas) para fazer o
JOIN via sq_candidato → candidacy_id.

Carrega:
  - VoteResult por candidato, município e zona
  - TurnoutSummary por município (comparecimento e abstenção)
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

import polars as pl

from etl.tse.constants import (
    TSE_RESULTS_MUNZONA_URL, RESULT_COLUMNS,
    TSE_ENCODING, TSE_SEPARATOR,
)
from etl.common.download import (
    download_file, extract_zip,
    register_dataset_version, mark_version_done, mark_version_failed,
    RAW_DIR, STAGING_DIR,
)
from etl.common.normalize import (
    clean_str_expr, validate_columns, read_tse_csv,
)

logger = logging.getLogger(__name__)

# Arquivo alternativo para turnout (comparecimento)
TSE_TURNOUT_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/"
    "votacao_partido_munzona_{ano}.zip"
)

TURNOUT_COLUMNS = {
    "ANO_ELEICAO":           "ano_eleicao",
    "NR_TURNO":              "turno",
    "SG_UF":                 "uf",
    "CD_MUNICIPIO":          "cd_municipio_tse",
    "NM_MUNICIPIO":          "nm_municipio",
    "NR_ZONA":               "nr_zona",
    "CD_CARGO":              "cd_cargo",
    "QT_APTOS":              "aptos",
    "QT_COMPARECIMENTO":     "comparecimento",
    "QT_ABSTENCOES":         "abstencao",
    "QT_VOTOS_BRANCOS":      "votos_brancos",
    "QT_VOTOS_NULOS":        "votos_nulos",
}


# ──────────────────────────────────────────────────────────────────────────────
# Normalização
# ──────────────────────────────────────────────────────────────────────────────

def normalize_results_df(raw_path: Path) -> pl.DataFrame:
    """Normaliza CSV de resultados por município/zona."""
    df = read_tse_csv(raw_path)
    cols = {k: v for k, v in RESULT_COLUMNS.items() if k in df.columns}
    df = df.rename(cols).select(list(cols.values()))

    for col in ["ano_eleicao", "turno", "cd_cargo", "nr_zona"]:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Int32, strict=False))

    if "votos" in df.columns:
        df = df.with_columns(pl.col("votos").cast(pl.Int64, strict=False))

    for col in ["uf", "nm_municipio", "situacao"]:
        if col in df.columns:
            df = df.with_columns(clean_str_expr(col))

    logger.info(f"Normalizado: {raw_path.name} → {len(df):,} linhas de resultado")
    return df


def normalize_turnout_df(raw_path: Path) -> pl.DataFrame:
    """Normaliza CSV de comparecimento."""
    df = read_tse_csv(raw_path)
    cols = {k: v for k, v in TURNOUT_COLUMNS.items() if k in df.columns}
    df = df.rename(cols).select(list(cols.values()))

    for col in ["aptos", "comparecimento", "abstencao", "votos_brancos", "votos_nulos"]:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Int64, strict=False))

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Upsert de VoteResult
# ──────────────────────────────────────────────────────────────────────────────

async def load_vote_results(session, df: pl.DataFrame, election_id: UUID, version_id: UUID, fonte_url: str):
    """
    Insere/atualiza VoteResult para cada linha do DataFrame.
    JOIN com candidacy via sq_candidato + election_id.
    JOIN com territory via cd_municipio_tse (proxy).
    """
    from sqlalchemy import select
    from db.models.political import Candidacy
    from db.models.territorial import Territory
    from db.models.analytical import VoteResult

    BATCH_SIZE = 1000
    inseridos = 0
    ignorados = 0

    rows = df.to_dicts()
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]

        for row in batch:
            sq = str(row.get("sq_candidato") or "")
            if not sq:
                ignorados += 1
                continue

            # Resolve candidacy
            stmt_c = select(Candidacy).where(
                Candidacy.tse_sq_candidato == sq,
                Candidacy.election_id == election_id,
            )
            result_c = await session.execute(stmt_c)
            candidacy = result_c.scalar_one_or_none()
            if not candidacy:
                ignorados += 1
                continue

            # Resolve territory (municipio)
            cd_mun = row.get("cd_municipio_tse")
            codigo_proxy = f"{cd_mun}00" if cd_mun else None
            territory = None
            if codigo_proxy:
                stmt_t = select(Territory).where(Territory.codigo_ibge == codigo_proxy)
                result_t = await session.execute(stmt_t)
                territory = result_t.scalar_one_or_none()

            votos = row.get("votos")
            if not votos:
                ignorados += 1
                continue

            # Upsert VoteResult
            stmt_v = select(VoteResult).where(
                VoteResult.candidacy_id == candidacy.id,
                VoteResult.territory_id == (territory.id if territory else None),
                VoteResult.polling_zone_id.is_(None),
                VoteResult.polling_section_id.is_(None),
            )
            result_v = await session.execute(stmt_v)
            vr = result_v.scalar_one_or_none()

            if not vr:
                vr = VoteResult(
                    candidacy_id=candidacy.id,
                    election_id=election_id,
                    territory_id=territory.id if territory else None,
                    votos=int(votos),
                    dataset_version_id=version_id,
                    fonte_url=fonte_url,
                )
                session.add(vr)
                inseridos += 1
            else:
                vr.votos = int(votos)

        await session.commit()
        logger.info(f"  Lote {i // BATCH_SIZE + 1}: {inseridos} inseridos, {ignorados} ignorados")

    return inseridos


# ──────────────────────────────────────────────────────────────────────────────
# Upsert de TurnoutSummary
# ──────────────────────────────────────────────────────────────────────────────

async def load_turnout(session, df: pl.DataFrame, election_id: UUID, version_id: UUID, fonte_url: str):
    """Insere TurnoutSummary por município."""
    from sqlalchemy import select
    from db.models.territorial import Territory
    from db.models.analytical import TurnoutSummary

    # Agrega por município (soma sobre as zonas)
    agg_cols = ["aptos", "comparecimento", "abstencao", "votos_brancos", "votos_nulos"]
    existing_agg = [c for c in agg_cols if c in df.columns]
    df_agg = (
        df.group_by(["uf", "cd_municipio_tse"])
        .agg([pl.col(c).sum() for c in existing_agg])
    )

    inseridos = 0
    for row in df_agg.iter_rows(named=True):
        cd_mun = row.get("cd_municipio_tse")
        codigo_proxy = f"{cd_mun}00" if cd_mun else None
        if not codigo_proxy:
            continue

        stmt_t = select(Territory).where(Territory.codigo_ibge == codigo_proxy)
        result_t = await session.execute(stmt_t)
        territory = result_t.scalar_one_or_none()

        stmt_ts = select(TurnoutSummary).where(
            TurnoutSummary.election_id == election_id,
            TurnoutSummary.territory_id == (territory.id if territory else None),
        )
        result_ts = await session.execute(stmt_ts)
        ts = result_ts.scalar_one_or_none()

        if not ts:
            ts = TurnoutSummary(
                election_id=election_id,
                territory_id=territory.id if territory else None,
                aptos=int(row.get("aptos") or 0),
                comparecimento=int(row.get("comparecimento") or 0),
                abstencao=int(row.get("abstencao") or 0),
                votos_brancos=int(row.get("votos_brancos") or 0) if row.get("votos_brancos") else None,
                votos_nulos=int(row.get("votos_nulos") or 0) if row.get("votos_nulos") else None,
                dataset_version_id=version_id,
                fonte_url=fonte_url,
            )
            session.add(ts)
            inseridos += 1

    await session.commit()
    logger.info(f"TurnoutSummary: {inseridos} municípios carregados")


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────────────────────

async def _run_async(ano: int, turno: int = 1, uf: Optional[str] = None, upload_minio: bool = True):
    from db.session import AsyncSessionLocal
    from db.models.governance import DataSource
    from db.models.political import Election
    from sqlalchemy import select

    logger.info(f"=== Ingestão de resultados TSE {ano} T{turno} {'(' + uf + ')' if uf else ''} ===")

    # Download
    zip_url = TSE_RESULTS_MUNZONA_URL.format(ano=ano)
    zip_path = download_file(zip_url, RAW_DIR / "tse" / f"votacao_candidato_munzona_{ano}.zip")
    extract_dir = STAGING_DIR / "tse" / f"resultados_{ano}"
    pattern = f"_{uf.upper()}." if uf else "votacao_candidato_munzona"
    csv_files = extract_zip(zip_path, extract_dir, pattern=pattern)

    if not csv_files:
        raise FileNotFoundError(f"Nenhum CSV de resultados encontrado para ano={ano} uf={uf}")

    async with AsyncSessionLocal() as session:
        stmt_src = select(DataSource).where(DataSource.nome == "TSE — Portal de Dados Abertos")
        src = (await session.execute(stmt_src)).scalar_one_or_none()
        source_id = src.id if src else None

        version = await register_dataset_version(
            session, source_id, f"votacao_candidato_munzona_{ano}", ano, zip_path, upload_minio
        )
        await session.commit()

        # Resolve election_id (filtra por turno)
        stmt_el = select(Election).where(Election.ano == ano, Election.turno == turno)
        el_result = await session.execute(stmt_el)
        election = el_result.scalar_one_or_none()

        if not election:
            raise ValueError(
                f"Election {ano} turno {turno} não encontrada. "
                "Execute primeiro o pipeline de candidaturas."
            )

        try:
            total_inseridos = 0
            for csv_file in csv_files:
                if csv_file.suffix.lower() != ".csv":
                    continue

                # Filtra por turno dentro do CSV
                df = normalize_results_df(csv_file)
                if "turno" in df.columns:
                    df = df.filter(pl.col("turno") == turno)

                n = await load_vote_results(
                    session, df, election.id, version.id, zip_url
                )
                total_inseridos += n

            await mark_version_done(session, version, total_inseridos, 0)
            await session.commit()
            logger.info(f"=== Resultados concluídos: {total_inseridos} inseridos ===")

        except Exception as exc:
            logger.error(f"Erro: {exc}", exc_info=True)
            await mark_version_failed(session, version, str(exc))
            await session.commit()
            raise


def run(ano: int, turno: int = 1, uf: Optional[str] = None, upload_minio: bool = True):
    asyncio.run(_run_async(ano=ano, turno=turno, uf=uf, upload_minio=upload_minio))


if __name__ == "__main__":
    import typer
    from rich.logging import RichHandler
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO, handlers=[RichHandler()])
    app = typer.Typer()

    @app.command()
    def main(
        ano: int = typer.Option(...),
        turno: int = typer.Option(1),
        uf: Optional[str] = typer.Option(None),
        no_minio: bool = typer.Option(False),
    ):
        run(ano=ano, turno=turno, uf=uf, upload_minio=not no_minio)

    app()
