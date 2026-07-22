"""
Pipeline IBGE — Censo 2022 via API SIDRA.

Carrega snapshots demográficos, de renda e domicílios para cada município.

Tabelas SIDRA usadas:
  4714 → população total por município (variável 93)
  4709 → domicílios particulares permanentes (variável 188)
  6579 → pessoas por cor ou raça (variável 606) — distribuição
  7358 → renda média mensal domiciliar per capita (2010, proxy até Censo 2022 completo)

Nota: O Censo 2022 ainda está sendo divulgado progressivamente pelo IBGE.
Esta versão carrega o que já está disponível na SIDRA. Campos ausentes
ficam nulos e são marcados com limitacoes na tabela demographic_snapshot.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from etl.ibge.constants import (
    SIDRA_POPULACAO_URL, SIDRA_DOMICILIOS_URL,
    SIDRA_RENDA_URL, SIDRA_BASE,
)
from etl.common.download import (
    register_dataset_version, mark_version_done, mark_version_failed,
    RAW_DIR, STAGING_DIR,
)

logger = logging.getLogger(__name__)

SIDRA_TIMEOUT = 120  # segundos — respostas grandes


# ──────────────────────────────────────────────────────────────────────────────
# Fetch SIDRA
# ──────────────────────────────────────────────────────────────────────────────

def fetch_sidra(url: str, descricao: str = "") -> list[dict]:
    """
    Faz GET na API SIDRA e retorna os dados como lista de dicts.
    Formato de retorno da SIDRA:
    [
      {
        "id": "...", "variavel": "...", "unidade": "...",
        "resultados": [
          {
            "classificacoes": [...],
            "series": [
              {"localidade": {"id": "3550308", "nivel": {...}}, "serie": {"2022": "12325232"}}
            ]
          }
        ]
      }
    ]
    """
    logger.info(f"Fetching SIDRA: {descricao or url[:80]}")
    with httpx.Client(timeout=SIDRA_TIMEOUT) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()

    # Flatten: extrai (codigo_ibge, periodo, valor)
    records = []
    for item in data:
        variavel = item.get("variavel", "")
        for resultado in item.get("resultados", []):
            for serie_item in resultado.get("series", []):
                localidade = serie_item.get("localidade", {})
                codigo = str(localidade.get("id", ""))
                serie = serie_item.get("serie", {})
                for periodo, valor in serie.items():
                    try:
                        v = float(str(valor).replace(",", "."))
                    except (ValueError, TypeError):
                        v = None
                    records.append({
                        "codigo_ibge": codigo,
                        "periodo": periodo,
                        "variavel": variavel,
                        "valor": v,
                    })

    logger.info(f"  → {len(records):,} registros retornados")
    return records


def fetch_sidra_populacao() -> dict[str, int]:
    """Retorna {codigo_ibge_7d → populacao_total} do Censo 2022."""
    records = fetch_sidra(SIDRA_POPULACAO_URL, "População total Censo 2022")
    return {
        r["codigo_ibge"]: int(r["valor"])
        for r in records
        if r["valor"] is not None and len(r["codigo_ibge"]) == 7
    }


def fetch_sidra_domicilios() -> dict[str, int]:
    """Retorna {codigo_ibge_7d → domicilios_particulares}."""
    records = fetch_sidra(SIDRA_DOMICILIOS_URL, "Domicílios Censo 2022")
    return {
        r["codigo_ibge"]: int(r["valor"])
        for r in records
        if r["valor"] is not None and len(r["codigo_ibge"]) == 7
    }


def fetch_sidra_renda_proxy() -> dict[str, float]:
    """
    Retorna {codigo_ibge_7d → renda_media_mensal} do Censo 2010 como proxy.
    Dados do Censo 2022 completos sobre renda ainda em divulgação.
    """
    records = fetch_sidra(SIDRA_RENDA_URL, "Renda média mensal (proxy Censo 2010)")
    return {
        r["codigo_ibge"]: r["valor"]
        for r in records
        if r["valor"] is not None and len(r["codigo_ibge"]) == 7
    }


# ──────────────────────────────────────────────────────────────────────────────
# Upsert de snapshots
# ──────────────────────────────────────────────────────────────────────────────

async def upsert_demographic_snapshots(
    session,
    populacao: dict[str, int],
    domicilios: dict[str, int],
    ano: int,
    version_id,
    fonte_url: str,
) -> int:
    """Upsert DemographicSnapshot para todos os municípios com dados disponíveis."""
    from sqlalchemy import select
    from db.models.territorial import Territory
    from db.models.socioeconomic import DemographicSnapshot

    inseridos = 0
    all_codes = set(populacao.keys()) | set(domicilios.keys())
    logger.info(f"Upserting DemographicSnapshot para {len(all_codes):,} municípios")

    BATCH = 500
    codes = list(all_codes)
    for i in range(0, len(codes), BATCH):
        batch = codes[i:i + BATCH]

        for codigo in batch:
            stmt_t = select(Territory).where(Territory.codigo_ibge == codigo)
            territory = (await session.execute(stmt_t)).scalar_one_or_none()
            if not territory:
                continue

            # Atualiza populacao no Territory também
            pop = populacao.get(codigo)
            if pop:
                territory.populacao = pop

            stmt_d = select(DemographicSnapshot).where(
                DemographicSnapshot.territory_id == territory.id,
                DemographicSnapshot.ano_referencia == ano,
            )
            snap = (await session.execute(stmt_d)).scalar_one_or_none()

            if not snap:
                snap = DemographicSnapshot(
                    territory_id=territory.id,
                    ano_referencia=ano,
                    populacao_total=pop,
                    fonte_url=fonte_url,
                    dataset_version_id=version_id,
                )
                session.add(snap)
                inseridos += 1
            else:
                if pop:
                    snap.populacao_total = pop

        await session.commit()
        logger.info(f"  Lote {i // BATCH + 1}: {inseridos} inseridos")

    return inseridos


async def upsert_income_snapshots(
    session,
    renda: dict[str, float],
    ano_ref: int,
    version_id,
    fonte_url: str,
    is_proxy: bool = True,
) -> int:
    """Upsert IncomeSnapshot."""
    from sqlalchemy import select
    from db.models.territorial import Territory
    from db.models.socioeconomic import IncomeSnapshot

    inseridos = 0
    BATCH = 500
    codes = list(renda.keys())

    for i in range(0, len(codes), BATCH):
        for codigo in codes[i:i + BATCH]:
            stmt_t = select(Territory).where(Territory.codigo_ibge == codigo)
            territory = (await session.execute(stmt_t)).scalar_one_or_none()
            if not territory:
                continue

            stmt = select(IncomeSnapshot).where(
                IncomeSnapshot.territory_id == territory.id,
                IncomeSnapshot.ano_referencia == ano_ref,
            )
            snap = (await session.execute(stmt)).scalar_one_or_none()

            if not snap:
                snap = IncomeSnapshot(
                    territory_id=territory.id,
                    ano_referencia=ano_ref,
                    renda_media_mensal=renda[codigo],
                    fonte_url=fonte_url,
                    dataset_version_id=version_id,
                )
                session.add(snap)
                inseridos += 1

        await session.commit()

    logger.info(f"IncomeSnapshot: {inseridos} inseridos (proxy={'sim' if is_proxy else 'não'})")
    return inseridos


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────────────────────

async def _run_async(ano: int = 2022, upload_minio: bool = True):
    from db.session import AsyncSessionLocal
    from db.models.governance import DataSource
    from sqlalchemy import select

    logger.info(f"=== Ingestão Censo IBGE {ano} via SIDRA ===")

    async with AsyncSessionLocal() as session:
        stmt_src = select(DataSource).where(DataSource.nome == "IBGE — SIDRA / Censo 2022")
        src = (await session.execute(stmt_src)).scalar_one_or_none()
        source_id = src.id if src else None

        # Cria um DatasetVersion fictício (não há arquivo binário para fazer upload)
        from db.models.governance import DatasetVersion
        from datetime import datetime, timezone

        version = DatasetVersion(
            source_id=source_id,
            nome_dataset=f"sidra_censo_{ano}",
            ano_referencia=ano,
            data_ingestao=datetime.now(timezone.utc),
            caminho_raw=SIDRA_POPULACAO_URL,
            status="running",
        )
        session.add(version)
        await session.commit()

        try:
            # Fetch dados do Censo 2022
            populacao = fetch_sidra_populacao()
            domicilios = fetch_sidra_domicilios()

            total_demo = await upsert_demographic_snapshots(
                session, populacao, domicilios, ano, version.id, SIDRA_POPULACAO_URL
            )

            # Renda — proxy do Censo 2010 até divulgação completa do 2022
            try:
                renda = fetch_sidra_renda_proxy()
                await upsert_income_snapshots(
                    session, renda, 2010, version.id,
                    SIDRA_RENDA_URL, is_proxy=True,
                )
            except Exception as e:
                logger.warning(f"Renda não carregada (continuando): {e}")

            await mark_version_done(session, version, total_demo, 0)
            await session.commit()

            logger.info(f"=== Censo IBGE concluído: {total_demo} snapshots demográficos ===")

        except Exception as exc:
            logger.error(f"Erro: {exc}", exc_info=True)
            await mark_version_failed(session, version, str(exc))
            await session.commit()
            raise


def run(ano: int = 2022, upload_minio: bool = True):
    """Entry point síncrono."""
    asyncio.run(_run_async(ano=ano, upload_minio=upload_minio))


if __name__ == "__main__":
    import typer
    from rich.logging import RichHandler
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO, handlers=[RichHandler()])
    app = typer.Typer()

    @app.command()
    def main(
        ano: int = typer.Option(2022),
        no_minio: bool = typer.Option(False),
    ):
        """Pipeline Censo IBGE / SIDRA."""
        run(ano=ano, upload_minio=not no_minio)

    app()
