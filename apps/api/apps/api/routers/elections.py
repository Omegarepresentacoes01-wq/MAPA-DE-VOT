"""
Router de Eleições — /api/v1/elections
Lista, detalhe e comparação entre eleições.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from db.models.political import Election, Candidacy, Party, Office
from db.models.analytical import VoteResult, TurnoutSummary
from shared.schemas import ElectionOut, PaginatedResponse, SourceMeta

router = APIRouter()

_SOURCE_TSE = SourceMeta(
    fonte="TSE — Portal de Dados Abertos",
    url="https://dadosabertos.tse.jus.br/",
    cobertura_temporal="2000–2024",
    cobertura_geografica="Nacional",
)


def _election_to_out(e: Election) -> ElectionOut:
    return ElectionOut(
        id=str(e.id),
        ano=e.ano,
        turno=e.turno,
        tipo=e.tipo_eleicao,
        descricao=e.descricao,
        meta=_SOURCE_TSE,
    )


@router.get("/elections", response_model=PaginatedResponse[ElectionOut])
async def list_elections(
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    turno: Optional[int] = Query(None, description="Filtrar por turno (1 ou 2)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ElectionOut]:
    """Lista todas as eleições disponíveis no sistema."""
    stmt = select(Election)
    if ano:
        stmt = stmt.where(Election.ano == ano)
    if turno:
        stmt = stmt.where(Election.turno == turno)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Election.ano.desc(), Election.turno).limit(size).offset((page - 1) * size)
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedResponse(
        items=[_election_to_out(e) for e in rows],
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size),
        meta=_SOURCE_TSE,
    )


@router.get("/elections/{election_id}", response_model=ElectionOut)
async def get_election(
    election_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ElectionOut:
    """Detalhe de uma eleição."""
    e = (await db.execute(select(Election).where(Election.id == election_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Eleição não encontrada")
    return _election_to_out(e)


@router.get("/elections/{election_id}/stats")
async def get_election_stats(
    election_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Estatísticas gerais de uma eleição: total de candidatos, votos, municípios."""
    e = (await db.execute(select(Election).where(Election.id == election_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Eleição não encontrada")

    total_candidatos = (await db.execute(
        select(func.count(Candidacy.id)).where(Candidacy.election_id == election_id)
    )).scalar_one()

    total_votos = (await db.execute(
        select(func.sum(VoteResult.votos)).where(VoteResult.election_id == election_id)
    )).scalar_one()

    total_aptos = (await db.execute(
        select(func.sum(TurnoutSummary.aptos)).where(TurnoutSummary.election_id == election_id)
    )).scalar_one()

    total_comparecimento = (await db.execute(
        select(func.sum(TurnoutSummary.comparecimento)).where(TurnoutSummary.election_id == election_id)
    )).scalar_one()

    # Top partidos por votos
    top_partidos = (await db.execute(
        select(Party.sigla, func.sum(VoteResult.votos).label("votos"))
        .join(Candidacy, Candidacy.id == VoteResult.candidacy_id)
        .join(Party, Party.id == Candidacy.party_id)
        .where(VoteResult.election_id == election_id)
        .group_by(Party.sigla)
        .order_by(func.sum(VoteResult.votos).desc())
        .limit(10)
    )).all()

    return {
        "eleicao": _election_to_out(e),
        "stats": {
            "total_candidatos": total_candidatos,
            "total_votos_nominais": total_votos,
            "total_aptos": total_aptos,
            "total_comparecimento": total_comparecimento,
            "pct_comparecimento": round(total_comparecimento / total_aptos * 100, 2)
                if total_aptos and total_comparecimento else None,
        },
        "top_partidos": [
            {"sigla": r.sigla, "votos": r.votos} for r in top_partidos
        ],
        "meta": _SOURCE_TSE.model_dump(),
    }


@router.get("/elections/{election_id}/candidates")
async def get_election_candidates(
    election_id: uuid.UUID,
    cargo_codigo: Optional[str] = Query(None),
    uf: Optional[str] = Query(None),
    partido: Optional[str] = Query(None),
    situacao: Optional[str] = Query(None, description="ex: ELEITO"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Lista candidatos de uma eleição com filtros."""
    from db.models.political import Person
    from db.models.territorial import Territory
    from shared.schemas import CandidateOut

    stmt = (
        select(Candidacy)
        .options(
            selectinload(Candidacy.person),
            selectinload(Candidacy.party),
            selectinload(Candidacy.office),
            selectinload(Candidacy.territory),
        )
        .where(Candidacy.election_id == election_id)
        .order_by(Candidacy.votos_totais.desc().nulls_last())
    )

    if cargo_codigo:
        stmt = stmt.join(Office, Office.id == Candidacy.office_id).where(Office.codigo == cargo_codigo)
    if partido:
        stmt = stmt.join(Party, Party.id == Candidacy.party_id).where(
            Party.sigla.ilike(f"%{partido}%")
        )
    if situacao:
        stmt = stmt.where(Candidacy.situacao.ilike(f"%{situacao}%"))
    if uf:
        stmt = stmt.join(Territory, Territory.id == Candidacy.territory_id).where(
            Territory.uf == uf.upper()
        )

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.limit(size).offset((page - 1) * size)
    rows = (await db.execute(stmt)).scalars().all()

    from apps.api.routers.candidates import _candidacy_to_out
    return PaginatedResponse(
        items=[_candidacy_to_out(c) for c in rows],
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size),
        meta=_SOURCE_TSE,
    )
