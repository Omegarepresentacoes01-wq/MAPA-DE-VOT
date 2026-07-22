"""
Router de busca global — /api/v1/search
Meilisearch como motor principal, fallback para PostgreSQL pg_trgm.
"""
from __future__ import annotations

import logging
import os
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models.political import Person, Candidacy, Party, Office, Election
from db.models.territorial import Territory
from shared.schemas import SearchResult, SearchResponse, SourceMeta

router = APIRouter()
logger = logging.getLogger(__name__)

MEILISEARCH_URL = os.environ.get("MEILISEARCH_URL", "http://meilisearch:7700")
MEILISEARCH_KEY = os.environ.get("MEILISEARCH_MASTER_KEY", "")

_SOURCE_SEARCH = SourceMeta(
    fonte="Meilisearch + PostgreSQL pg_trgm",
    cobertura_temporal="Depende dos dados ingeridos",
    cobertura_geografica="Nacional",
)


# ─────────────────────────────────────────────
# Cliente Meilisearch (lazy singleton)
# ─────────────────────────────────────────────

_meili_client = None


def get_meili():
    global _meili_client
    if _meili_client is None:
        try:
            import meilisearch
            _meili_client = meilisearch.Client(MEILISEARCH_URL, MEILISEARCH_KEY)
        except Exception as e:
            logger.warning(f"Meilisearch não disponível: {e}")
            _meili_client = False
    return _meili_client if _meili_client is not False else None


# ─────────────────────────────────────────────
# Busca via Meilisearch
# ─────────────────────────────────────────────

def search_meilisearch(q: str, tipos: Optional[List[str]], limit: int) -> List[SearchResult]:
    client = get_meili()
    if not client:
        return []

    try:
        # Índice unificado "tudo" ou filtro por tipo
        idx = client.index("eleitoral")
        filter_str = None
        if tipos:
            filter_str = "tipo IN [" + ", ".join(f'"{t}"' for t in tipos) + "]"

        params = {
            "limit": limit,
            "attributesToHighlight": ["titulo", "subtitulo"],
            "highlightPreTag": "<mark>",
            "highlightPostTag": "</mark>",
        }
        if filter_str:
            params["filter"] = filter_str

        result = idx.search(q, params)
        hits = result.get("hits", [])

        return [
            SearchResult(
                id=str(h.get("id", "")),
                tipo=h.get("tipo", ""),
                titulo=h.get("titulo", ""),
                subtitulo=h.get("subtitulo"),
                uf=h.get("uf"),
                partido_sigla=h.get("partido_sigla"),
                situacao=h.get("situacao"),
                score=h.get("_rankingScore"),
            )
            for h in hits
        ]
    except Exception as e:
        logger.warning(f"Erro Meilisearch: {e}")
        return []


# ─────────────────────────────────────────────
# Fallback: busca via PostgreSQL pg_trgm
# ─────────────────────────────────────────────

async def search_postgres(
    q: str,
    tipos: Optional[List[str]],
    limit: int,
    db: AsyncSession,
) -> List[SearchResult]:
    results: List[SearchResult] = []

    # Candidatos
    if not tipos or "candidato" in tipos:
        stmt = (
            select(Person, Candidacy, Party, Office)
            .join(Candidacy, Candidacy.person_id == Person.id)
            .join(Party, Party.id == Candidacy.party_id)
            .join(Office, Office.id == Candidacy.office_id)
            .where(
                or_(
                    func.similarity(Person.nome, q) > 0.25,
                    func.similarity(Person.nome_urna, q) > 0.25,
                    Person.nome.ilike(f"%{q}%"),
                )
            )
            .order_by(func.similarity(Person.nome, q).desc())
            .limit(limit // 2)
        )
        rows = (await db.execute(stmt)).unique().all()
        for person, cand, party, office in rows:
            results.append(SearchResult(
                id=str(cand.id),
                tipo="candidato",
                titulo=person.nome_urna or person.nome,
                subtitulo=f"{party.sigla} · {office.descricao}",
                uf=cand.territory.uf if hasattr(cand, "territory") and cand.territory else None,
                partido_sigla=party.sigla,
                situacao=cand.situacao,
            ))

    # Municípios
    if not tipos or "municipio" in tipos:
        stmt = (
            select(Territory)
            .where(
                Territory.tipo == "municipio",
                or_(
                    func.similarity(Territory.nome, q) > 0.3,
                    Territory.nome.ilike(f"%{q}%"),
                )
            )
            .order_by(func.similarity(Territory.nome, q).desc())
            .limit(limit // 4)
        )
        territories = (await db.execute(stmt)).scalars().all()
        for t in territories:
            results.append(SearchResult(
                id=str(t.id),
                tipo="municipio",
                titulo=t.nome,
                subtitulo=t.uf,
                uf=t.uf,
            ))

    # Partidos
    if not tipos or "partido" in tipos:
        stmt = (
            select(Party)
            .where(
                or_(
                    Party.sigla.ilike(f"%{q}%"),
                    func.similarity(Party.nome, q) > 0.3,
                )
            )
            .limit(5)
        )
        parties = (await db.execute(stmt)).scalars().all()
        for p in parties:
            results.append(SearchResult(
                id=str(p.id),
                tipo="partido",
                titulo=p.sigla,
                subtitulo=p.nome,
                partido_sigla=p.sigla,
            ))

    return results[:limit]


# ─────────────────────────────────────────────
# GET /search
# ─────────────────────────────────────────────

@router.get("/search", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=2, description="Termo de busca"),
    tipos: Optional[str] = Query(None, description="Tipos separados por vírgula: candidato,municipio,partido"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Busca global unificada.
    Motor: Meilisearch (tipado, fuzzy) → fallback PostgreSQL pg_trgm.
    """
    start = time.monotonic()
    tipos_list = [t.strip() for t in tipos.split(",")] if tipos else None

    # 1. Tenta Meilisearch
    results = search_meilisearch(q, tipos_list, limit)

    # 2. Fallback para PostgreSQL se Meilisearch vazio ou indisponível
    if not results:
        results = await search_postgres(q, tipos_list, limit, db)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    return SearchResponse(
        query=q,
        total=len(results),
        results=results,
        tempo_ms=elapsed_ms,
        meta=_SOURCE_SEARCH,
    )


# ─────────────────────────────────────────────
# GET /search/suggest
# ─────────────────────────────────────────────

@router.get("/search/suggest")
async def suggest(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=30),
) -> dict:
    """Sugestões de autocompletar (apenas Meilisearch)."""
    client = get_meili()
    if not client:
        return {"suggestions": []}
    try:
        idx = client.index("eleitoral")
        result = idx.search(q, {"limit": limit, "attributesToSearchOn": ["titulo"]})
        return {
            "suggestions": [
                {"label": h.get("titulo", ""), "tipo": h.get("tipo", ""), "id": h.get("id", "")}
                for h in result.get("hits", [])
            ]
        }
    except Exception as e:
        logger.warning(f"Suggest error: {e}")
        return {"suggestions": []}
