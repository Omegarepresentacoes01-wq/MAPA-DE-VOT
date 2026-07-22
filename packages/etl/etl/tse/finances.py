"""
Pipeline de finanças eleitorais TSE — receitas e despesas.

Fonte: dadosabertos.tse.jus.br
Arquivos:
  receitas_candidatos_{ano}.zip → receitas_candidatos_{ano}_{UF}.csv
  despesas_candidatos_{ano}.zip → despesas_candidatos_{ano}_{UF}.csv
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

import polars as pl

from etl.tse.constants import TSE_REVENUES_URL, TSE_EXPENSES_URL
from etl.common.download import (
    download_file, extract_zip,
    register_dataset_version, mark_version_done, mark_version_failed,
    RAW_DIR, STAGING_DIR,
)
from etl.common.normalize import clean_str_expr, parse_tse_money_expr, parse_tse_date_expr, read_tse_csv

logger = logging.getLogger(__name__)

REVENUE_COLUMNS = {
    "ANO_ELEICAO":                    "ano_eleicao",
    "SQ_CANDIDATO":                   "sq_candidato",
    "DT_RECEITA":                     "data",
    "DS_ORIGEM_RECEITA":              "origem",
    "DS_RECEITA":                     "descricao",
    "VR_RECEITA":                     "valor",
    "NR_CPF_CNPJ_DOADOR":             "cnpj_cpf_doador",
    "NM_DOADOR":                      "nome_doador",
    "NM_DOADOR_RFB":                  "nome_doador_rfb",
    "SQ_RECEITA":                     "tse_seq_receita",
}

EXPENSE_COLUMNS = {
    "ANO_ELEICAO":                    "ano_eleicao",
    "SQ_CANDIDATO":                   "sq_candidato",
    "DT_DESPESA":                     "data",
    "DS_ORIGEM_DESPESA":              "categoria",
    "DS_DESPESA":                     "descricao",
    "VR_DESPESA_CONTRATADA":          "valor",
    "NR_CPF_CNPJ_FORNECEDOR":         "cnpj_fornecedor",
    "NM_FORNECEDOR":                  "nome_fornecedor",
    "NM_FORNECEDOR_RFB":              "nome_fornecedor_rfb",
    "SQ_DESPESA":                     "tse_seq_despesa",
}


def _normalize_finance_df(path: Path, col_map: dict, money_col: str) -> pl.DataFrame:
    df = read_tse_csv(path)
    cols = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(cols).select(list(cols.values()))

    if money_col in df.columns:
        df = df.with_columns(parse_tse_money_expr(money_col))

    if "data" in df.columns:
        df = df.with_columns(parse_tse_date_expr("data"))

    for col in ["origem", "categoria", "descricao", "nome_doador", "nome_fornecedor"]:
        if col in df.columns:
            df = df.with_columns(clean_str_expr(col))

    logger.info(f"Normalizado: {path.name} → {len(df):,} registros")
    return df


async def _load_revenues(session, df: pl.DataFrame, election_id: UUID, version_id: UUID, fonte_url: str) -> int:
    from sqlalchemy import select
    from db.models.political import Candidacy
    from db.models.financial import CampaignRevenue

    inseridos = 0
    BATCH = 500

    rows = df.filter(pl.col("valor").is_not_null()).to_dicts()
    for i in range(0, len(rows), BATCH):
        for row in rows[i:i + BATCH]:
            sq = str(row.get("sq_candidato") or "")
            if not sq:
                continue

            stmt = select(Candidacy).where(
                Candidacy.tse_sq_candidato == sq,
                Candidacy.election_id == election_id,
            )
            candidacy = (await session.execute(stmt)).scalar_one_or_none()
            if not candidacy:
                continue

            seq = str(row.get("tse_seq_receita") or "")
            if seq:
                exists = (await session.execute(
                    select(CampaignRevenue).where(CampaignRevenue.tse_seq_receita == seq)
                )).scalar_one_or_none()
                if exists:
                    continue

            rev = CampaignRevenue(
                candidacy_id=candidacy.id,
                data=row.get("data"),
                origem=str(row.get("origem") or "NÃO INFORMADO"),
                descricao=row.get("descricao"),
                valor=row["valor"],
                cnpj_cpf_doador=row.get("cnpj_cpf_doador"),
                nome_doador=row.get("nome_doador") or row.get("nome_doador_rfb"),
                tse_seq_receita=seq or None,
                fonte_url=fonte_url,
                dataset_version_id=version_id,
            )
            session.add(rev)
            inseridos += 1

        await session.commit()
    return inseridos


async def _load_expenses(session, df: pl.DataFrame, election_id: UUID, version_id: UUID, fonte_url: str) -> int:
    from sqlalchemy import select
    from db.models.political import Candidacy
    from db.models.financial import CampaignExpense

    inseridos = 0
    BATCH = 500

    rows = df.filter(pl.col("valor").is_not_null()).to_dicts()
    for i in range(0, len(rows), BATCH):
        for row in rows[i:i + BATCH]:
            sq = str(row.get("sq_candidato") or "")
            if not sq:
                continue

            stmt = select(Candidacy).where(
                Candidacy.tse_sq_candidato == sq,
                Candidacy.election_id == election_id,
            )
            candidacy = (await session.execute(stmt)).scalar_one_or_none()
            if not candidacy:
                continue

            seq = str(row.get("tse_seq_despesa") or "")
            if seq:
                exists = (await session.execute(
                    select(CampaignExpense).where(CampaignExpense.tse_seq_despesa == seq)
                )).scalar_one_or_none()
                if exists:
                    continue

            exp = CampaignExpense(
                candidacy_id=candidacy.id,
                data=row.get("data"),
                categoria=str(row.get("categoria") or "NÃO CATEGORIZADO"),
                descricao=row.get("descricao"),
                valor=row["valor"],
                cnpj_fornecedor=row.get("cnpj_fornecedor"),
                nome_fornecedor=row.get("nome_fornecedor") or row.get("nome_fornecedor_rfb"),
                tse_seq_despesa=seq or None,
                fonte_url=fonte_url,
                dataset_version_id=version_id,
            )
            session.add(exp)
            inseridos += 1

        await session.commit()
    return inseridos


async def _run_async(ano: int, uf: Optional[str] = None, upload_minio: bool = True):
    from db.session import AsyncSessionLocal
    from db.models.governance import DataSource
    from db.models.political import Election
    from sqlalchemy import select

    logger.info(f"=== Ingestão de finanças TSE {ano} ===")

    async with AsyncSessionLocal() as session:
        stmt_src = select(DataSource).where(DataSource.nome == "TSE — DivulgaCandContas")
        src = (await session.execute(stmt_src)).scalar_one_or_none()
        source_id = src.id if src else None

        stmt_el = select(Election).where(Election.ano == ano, Election.turno == 1)
        election = (await session.execute(stmt_el)).scalar_one_or_none()
        if not election:
            raise ValueError(f"Election {ano} não encontrada. Execute candidaturas primeiro.")

        fonte_url = TSE_REVENUES_URL.format(ano=ano)

        # ── Receitas ──
        rev_zip = download_file(
            TSE_REVENUES_URL.format(ano=ano),
            RAW_DIR / "tse" / f"receitas_candidatos_{ano}.zip",
        )
        rev_dir = STAGING_DIR / "tse" / f"receitas_{ano}"
        pattern = f"_{uf.upper()}." if uf else "receitas_candidatos"
        rev_files = extract_zip(rev_zip, rev_dir, pattern=pattern)

        version = await register_dataset_version(
            session, source_id, f"receitas_candidatos_{ano}", ano, rev_zip, upload_minio
        )
        await session.commit()

        total_rev = 0
        try:
            for f in rev_files:
                if f.suffix.lower() != ".csv":
                    continue
                df = _normalize_finance_df(f, REVENUE_COLUMNS, "valor")
                total_rev += await _load_revenues(session, df, election.id, version.id, fonte_url)
            await mark_version_done(session, version, total_rev, 0)
            await session.commit()
        except Exception as e:
            await mark_version_failed(session, version, str(e))
            await session.commit()
            raise

        # ── Despesas ──
        exp_zip = download_file(
            TSE_EXPENSES_URL.format(ano=ano),
            RAW_DIR / "tse" / f"despesas_candidatos_{ano}.zip",
        )
        exp_dir = STAGING_DIR / "tse" / f"despesas_{ano}"
        exp_files = extract_zip(exp_zip, exp_dir, pattern=(f"_{uf.upper()}." if uf else "despesas_candidatos"))

        version2 = await register_dataset_version(
            session, source_id, f"despesas_candidatos_{ano}", ano, exp_zip, upload_minio
        )
        await session.commit()

        total_exp = 0
        try:
            for f in exp_files:
                if f.suffix.lower() != ".csv":
                    continue
                df = _normalize_finance_df(f, EXPENSE_COLUMNS, "valor")
                total_exp += await _load_expenses(session, df, election.id, version2.id, TSE_EXPENSES_URL.format(ano=ano))
            await mark_version_done(session, version2, total_exp, 0)
            await session.commit()
        except Exception as e:
            await mark_version_failed(session, version2, str(e))
            await session.commit()
            raise

    logger.info(f"=== Finanças concluídas: {total_rev} receitas, {total_exp} despesas ===")


def run(ano: int, uf: Optional[str] = None, upload_minio: bool = True):
    asyncio.run(_run_async(ano=ano, uf=uf, upload_minio=upload_minio))
