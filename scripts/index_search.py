"""
Indexador Meilisearch — Etapa 7.

Constrói o índice "eleitoral" com:
  - Candidatos (nome, nome_urna, partido, cargo, UF, situação)
  - Municípios (nome, UF, população)
  - Partidos (sigla, nome)

Configurações do índice:
  - searchableAttributes: titulo, subtitulo, partido_sigla, uf
  - filterableAttributes: tipo, uf, partido_sigla, situacao, cargo_codigo
  - sortableAttributes: votos_totais, populacao
  - rankingRules: typo, words, proximity, attribute, sort, exactness

Uso:
  python scripts/index_search.py
  make index-search
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import meilisearch
from rich.console import Console
from rich.progress import Progress, BarColumn, SpinnerColumn, TimeElapsedColumn
from rich.logging import RichHandler

logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])
logger = logging.getLogger(__name__)
console = Console()

MEILI_URL = os.environ.get("MEILISEARCH_URL", "http://localhost:7700")
MEILI_KEY = os.environ.get("MEILISEARCH_MASTER_KEY", "")
INDEX_NAME = "eleitoral"
BATCH_SIZE = 5000


# ─────────────────────────────────────────────
# Configuração do índice
# ─────────────────────────────────────────────

INDEX_CONFIG = {
    "searchableAttributes": [
        "titulo",
        "subtitulo",
        "partido_sigla",
        "partido_nome",
        "uf",
        "cargo_descricao",
        "codigo_ibge",
    ],
    "filterableAttributes": [
        "tipo",
        "uf",
        "partido_sigla",
        "situacao",
        "cargo_codigo",
        "eleicao_ano",
    ],
    "sortableAttributes": [
        "votos_totais",
        "populacao",
        "titulo",
    ],
    "rankingRules": [
        "words",
        "typo",
        "proximity",
        "attribute",
        "sort",
        "exactness",
    ],
    "typoTolerance": {
        "enabled": True,
        "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8},
    },
}


# ─────────────────────────────────────────────
# Extração de documentos do banco
# ─────────────────────────────────────────────

async def extract_candidatos() -> List[Dict[str, Any]]:
    """Extrai candidatos para indexação."""
    from db.session import AsyncSessionLocal
    from db.models.political import Candidacy, Person, Party, Office, Election
    from db.models.territorial import Territory
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    logger.info("Extraindo candidatos...")
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Candidacy)
            .options(
                selectinload(Candidacy.person),
                selectinload(Candidacy.party),
                selectinload(Candidacy.office),
                selectinload(Candidacy.territory),
                selectinload(Candidacy.election),
            )
        )
        rows = (await session.execute(stmt)).scalars().all()

    docs = []
    for c in rows:
        p = c.person
        party = c.party
        office = c.office
        terr = c.territory
        el = c.election

        docs.append({
            "id": f"candidato_{c.id}",
            "tipo": "candidato",
            "titulo": (p.nome_urna or p.nome) if p else "",
            "subtitulo": f"{party.sigla if party else ''} · {office.descricao if office else ''}",
            "uf": terr.uf if terr else None,
            "partido_sigla": party.sigla if party else None,
            "partido_nome": party.nome if party else None,
            "cargo_codigo": office.codigo if office else None,
            "cargo_descricao": office.descricao if office else None,
            "situacao": c.situacao,
            "eleicao_ano": el.ano if el else None,
            "votos_totais": c.votos_totais,
            "municipio": terr.nome if terr else None,
        })

    logger.info(f"Candidatos: {len(docs):,}")
    return docs


async def extract_municipios() -> List[Dict[str, Any]]:
    """Extrai municípios para indexação."""
    from db.session import AsyncSessionLocal
    from db.models.territorial import Territory
    from sqlalchemy import select

    logger.info("Extraindo municípios...")
    async with AsyncSessionLocal() as session:
        stmt = select(Territory).where(Territory.tipo == "municipio")
        rows = (await session.execute(stmt)).scalars().all()

    docs = [
        {
            "id": f"municipio_{t.id}",
            "tipo": "municipio",
            "titulo": t.nome,
            "subtitulo": t.uf,
            "uf": t.uf,
            "codigo_ibge": t.codigo_ibge,
            "populacao": t.populacao,
            "eleitorado": t.eleitorado,
        }
        for t in rows
    ]
    logger.info(f"Municípios: {len(docs):,}")
    return docs


async def extract_partidos() -> List[Dict[str, Any]]:
    """Extrai partidos para indexação."""
    from db.session import AsyncSessionLocal
    from db.models.political import Party
    from sqlalchemy import select

    logger.info("Extraindo partidos...")
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Party))).scalars().all()

    docs = [
        {
            "id": f"partido_{p.id}",
            "tipo": "partido",
            "titulo": p.sigla,
            "subtitulo": p.nome,
            "partido_sigla": p.sigla,
            "partido_nome": p.nome,
        }
        for p in rows
    ]
    logger.info(f"Partidos: {len(docs):,}")
    return docs


# ─────────────────────────────────────────────
# Indexação
# ─────────────────────────────────────────────

def upload_batch(idx, docs: List[Dict], entity: str) -> None:
    """Envia docs em batches e aguarda conclusão."""
    total = len(docs)
    with Progress(
        SpinnerColumn(),
        f"[cyan]{entity}[/cyan]",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(entity, total=total)

        for i in range(0, total, BATCH_SIZE):
            batch = docs[i:i + BATCH_SIZE]
            task_info = idx.add_documents(batch)
            # Aguarda conclusão do task Meilisearch
            _wait_task(idx._http_requests, task_info["taskUid"])
            progress.update(task, advance=len(batch))


def _wait_task(client_requests, task_uid: int, timeout: int = 120) -> None:
    """Polling até o task Meilisearch completar."""
    import meilisearch
    start = time.monotonic()
    # Usa a instância do client para verificar status
    # Acesso direto à API REST
    import httpx
    url = f"{MEILI_URL}/tasks/{task_uid}"
    headers = {"Authorization": f"Bearer {MEILI_KEY}"} if MEILI_KEY else {}

    while time.monotonic() - start < timeout:
        resp = httpx.get(url, headers=headers)
        if resp.status_code == 200:
            status = resp.json().get("status")
            if status in ("succeeded", "failed"):
                if status == "failed":
                    logger.warning(f"Task {task_uid} failed: {resp.json()}")
                return
        time.sleep(0.5)


async def run_indexer():
    """Entry point principal."""
    console.rule("[bold blue]Meilisearch Indexer — Mapa de Voto")

    # Conecta ao Meilisearch
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        health = client.health()
        console.print(f"[green]✓ Meilisearch conectado: {health}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Falha ao conectar Meilisearch ({MEILI_URL}): {e}[/red]")
        return

    # Garante que o índice existe
    try:
        idx = client.get_index(INDEX_NAME)
        console.print(f"[yellow]Índice existente: {INDEX_NAME}[/yellow]")
    except Exception:
        client.create_index(INDEX_NAME, {"primaryKey": "id"})
        idx = client.get_index(INDEX_NAME)
        console.print(f"[green]Índice criado: {INDEX_NAME}[/green]")

    # Aplica configurações
    idx.update_searchable_attributes(INDEX_CONFIG["searchableAttributes"])
    idx.update_filterable_attributes(INDEX_CONFIG["filterableAttributes"])
    idx.update_sortable_attributes(INDEX_CONFIG["sortableAttributes"])
    idx.update_ranking_rules(INDEX_CONFIG["rankingRules"])
    idx.update_typo_tolerance(INDEX_CONFIG["typoTolerance"])
    console.print("[green]✓ Configurações aplicadas[/green]")

    # Extrai documentos
    candidatos = await extract_candidatos()
    municipios = await extract_municipios()
    partidos = await extract_partidos()

    all_docs = candidatos + municipios + partidos
    console.print(f"\nTotal de documentos: [bold]{len(all_docs):,}[/bold]")

    # Indexa
    if all_docs:
        upload_batch(idx, all_docs, "Indexando")

    # Stats finais
    stats = idx.get_stats()
    console.print(f"\n[bold green]✅ Indexação concluída![/bold green]")
    console.print(f"   Documentos no índice: {stats.get('numberOfDocuments', '?'):,}")
    console.print(f"   Última atualização: {stats.get('lastUpdate', '?')}")


if __name__ == "__main__":
    asyncio.run(run_indexer())
