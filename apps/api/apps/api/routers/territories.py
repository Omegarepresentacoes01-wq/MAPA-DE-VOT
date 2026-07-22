"""
Router de Territórios — /api/v1/territories
Ficha de município, resultados eleitorais, comparecimento e comparação entre eleições.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from db.models.territorial import Territory
from db.models.political import Candidacy, Election, Party, Office
from db.models.analytical import VoteResult, TurnoutSummary
from shared.schemas import (
    TerritoryOut, VoteResultOut, ElectionOut,
    ComparisonOut, ComparisonRow, PaginatedResponse, SourceMeta
)

router = APIRouter()

_SOURCE_TSE = SourceMeta(
    fonte="TSE — Portal de Dados Abertos",
    url="https://dadosabertos.tse.jus.br/",
    cobertura_temporal="2000–2024",
    cobertura_geografica="Nacional",
    limitacoes="Resultados por seção disponíveis a partir de 2002",
)

_SOURCE_IBGE = SourceMeta(
    fonte="IBGE — Malhas Territoriais + Censo 2022",
    url="https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html",
    cobertura_temporal="2022",
    cobertura_geografica="Nacional",
)


def _territory_to_out(t: Territory) -> TerritoryOut:
    return TerritoryOut(
        id=str(t.id),
        tipo=t.tipo,
        codigo_ibge=t.codigo_ibge,
        nome=t.nome,
        uf=t.uf,
        populacao=t.populacao,
        eleitorado=t.eleitorado,
        meta=_SOURCE_IBGE,
    )


# ─────────────────────────────────────────────
# GET /territories
# ─────────────────────────────────────────────

@router.get("/territories", response_model=PaginatedResponse[TerritoryOut])
async def list_territories(
    uf: Optional[str] = Query(None, description="Filtra por UF"),
    q: Optional[str] = Query(None, description="Busca por nome"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TerritoryOut]:
    """Lista municípios com filtros por UF e nome."""
    stmt = select(Territory).where(Territory.tipo == "municipio")

    if uf:
        stmt = stmt.where(Territory.uf == uf.upper())
    if q:
        stmt = stmt.where(func.lower(Territory.nome).contains(q.lower()))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Territory.nome).limit(size).offset((page - 1) * size)
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedResponse(
        items=[_territory_to_out(t) for t in rows],
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size),
        meta=_SOURCE_IBGE,
    )


# ─────────────────────────────────────────────
# GET /territories/{codigo_ibge}
# ─────────────────────────────────────────────

@router.get("/territories/{codigo_ibge}", response_model=TerritoryOut)
async def get_territory(
    codigo_ibge: str,
    db: AsyncSession = Depends(get_db),
) -> TerritoryOut:
    """Ficha do município com dados geográficos e demográficos."""
    stmt = select(Territory).where(Territory.codigo_ibge == codigo_ibge)
    t = (await db.execute(stmt)).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail=f"Município {codigo_ibge} não encontrado")
    return _territory_to_out(t)


# ─────────────────────────────────────────────
# GET /territories/{codigo_ibge}/results
# ─────────────────────────────────────────────

@router.get("/territories/{codigo_ibge}/results", response_model=List[VoteResultOut])
async def get_territory_results(
    codigo_ibge: str,
    election_id: Optional[str] = Query(None, description="UUID da eleição"),
    cargo_codigo: Optional[str] = Query(None, description="Código do cargo (ex: 11=Vereador)"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> List[VoteResultOut]:
    """
    Resultados eleitorais de um município.
    Retorna os candidatos mais votados por padrão.
    """
    # Resolve territory
    stmt_t = select(Territory).where(Territory.codigo_ibge == codigo_ibge)
    territory = (await db.execute(stmt_t)).scalar_one_or_none()
    if not territory:
        raise HTTPException(status_code=404, detail=f"Município {codigo_ibge} não encontrado")

    stmt = (
        select(VoteResult, Candidacy, Party, Office)
        .join(Candidacy, Candidacy.id == VoteResult.candidacy_id)
        .join(Party, Party.id == Candidacy.party_id)
        .join(Office, Office.id == Candidacy.office_id)
        .where(VoteResult.territory_id == territory.id)
        .order_by(VoteResult.votos.desc())
        .limit(limit)
    )

    if election_id:
        try:
            eid = uuid.UUID(election_id)
            stmt = stmt.where(VoteResult.election_id == eid)
        except ValueError:
            raise HTTPException(status_code=422, detail="election_id inválido")

    if cargo_codigo:
        stmt = stmt.where(Office.codigo == cargo_codigo)

    rows = (await db.execute(stmt)).unique().all()

    return [
        VoteResultOut(
            candidacy_id=str(vr.candidacy_id),
            territory_codigo_ibge=codigo_ibge,
            territory_nome=territory.nome,
            votos=vr.votos,
            percentual=float(vr.percentual) if vr.percentual else None,
            meta=_SOURCE_TSE,
        )
        for vr, candidacy, party, office in rows
    ]


# ─────────────────────────────────────────────
# GET /territories/{codigo_ibge}/turnout
# ─────────────────────────────────────────────

@router.get("/territories/{codigo_ibge}/turnout")
async def get_territory_turnout(
    codigo_ibge: str,
    election_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Comparecimento e abstenção de um município."""
    stmt_t = select(Territory).where(Territory.codigo_ibge == codigo_ibge)
    territory = (await db.execute(stmt_t)).scalar_one_or_none()
    if not territory:
        raise HTTPException(status_code=404, detail="Município não encontrado")

    stmt = (
        select(TurnoutSummary, Election)
        .join(Election, Election.id == TurnoutSummary.election_id)
        .where(TurnoutSummary.territory_id == territory.id)
        .order_by(Election.ano.desc(), Election.turno.desc())
    )
    if election_id:
        try:
            eid = uuid.UUID(election_id)
            stmt = stmt.where(TurnoutSummary.election_id == eid)
        except ValueError:
            raise HTTPException(status_code=422, detail="election_id inválido")

    rows = (await db.execute(stmt)).unique().all()

    return {
        "territorio": _territory_to_out(territory),
        "comparecimento": [
            {
                "election_id": str(ts.election_id),
                "eleicao": f"{el.ano} T{el.turno}",
                "aptos": ts.aptos,
                "comparecimento": ts.comparecimento,
                "abstencao": ts.abstencao,
                "pct_comparecimento": round(ts.comparecimento / ts.aptos * 100, 2) if ts.aptos else None,
                "pct_abstencao": round(ts.abstencao / ts.aptos * 100, 2) if ts.aptos else None,
                "votos_brancos": ts.votos_brancos,
                "votos_nulos": ts.votos_nulos,
            }
            for ts, el in rows
        ],
        "meta": _SOURCE_TSE.model_dump(),
    }


# ─────────────────────────────────────────────
# GET /territories/{codigo_ibge}/compare
# ─────────────────────────────────────────────

@router.get("/territories/{codigo_ibge}/compare", response_model=ComparisonOut)
async def compare_elections_in_territory(
    codigo_ibge: str,
    election_a: str = Query(..., description="UUID da eleição A (mais antiga)"),
    election_b: str = Query(..., description="UUID da eleição B (mais recente)"),
    cargo_codigo: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ComparisonOut:
    """
    Compara resultados eleitorais entre duas eleições no mesmo território.
    Retorna variação absoluta e percentual de votos por candidato/partido.
    """
    stmt_t = select(Territory).where(Territory.codigo_ibge == codigo_ibge)
    territory = (await db.execute(stmt_t)).scalar_one_or_none()
    if not territory:
        raise HTTPException(status_code=404, detail="Município não encontrado")

    try:
        eid_a = uuid.UUID(election_a)
        eid_b = uuid.UUID(election_b)
    except ValueError:
        raise HTTPException(status_code=422, detail="election_id inválido")

    # Busca eleições
    el_a = (await db.execute(select(Election).where(Election.id == eid_a))).scalar_one_or_none()
    el_b = (await db.execute(select(Election).where(Election.id == eid_b))).scalar_one_or_none()
    if not el_a or not el_b:
        raise HTTPException(status_code=404, detail="Eleição não encontrada")

    async def get_votes_by_party(election_id):
        """Agrega votos por partido para o território."""
        stmt = (
            select(
                Party.sigla,
                Party.nome,
                func.sum(VoteResult.votos).label("total"),
            )
            .join(Candidacy, Candidacy.id == VoteResult.candidacy_id)
            .join(Party, Party.id == Candidacy.party_id)
            .join(Office, Office.id == Candidacy.office_id)
            .where(
                VoteResult.election_id == election_id,
                VoteResult.territory_id == territory.id,
            )
            .group_by(Party.sigla, Party.nome)
            .order_by(func.sum(VoteResult.votos).desc())
        )
        if cargo_codigo:
            stmt = stmt.where(Office.codigo == cargo_codigo)
        return {
            r.sigla: {"nome": r.nome, "votos": r.total or 0}
            for r in (await db.execute(stmt)).all()
        }

    votes_a = await get_votes_by_party(eid_a)
    votes_b = await get_votes_by_party(eid_b)

    # Todos os partidos que aparecem em pelo menos uma eleição
    all_parties = set(votes_a.keys()) | set(votes_b.keys())

    rows = []
    for sigla in sorted(all_parties):
        va = votes_a.get(sigla, {}).get("votos", 0) or 0
        vb = votes_b.get(sigla, {}).get("votos", 0) or 0
        diff = vb - va
        pct = round((diff / va * 100), 2) if va else None
        rows.append(
            ComparisonRow(
                territory_nome=f"{sigla} — {votes_b.get(sigla, votes_a.get(sigla, {})).get('nome', '')}",
                territory_codigo_ibge=codigo_ibge,
                votos_a=va if va else None,
                votos_b=vb if vb else None,
                variacao_absoluta=diff,
                variacao_percentual=pct,
            )
        )

    # Ordena por variação absoluta decrescente
    rows.sort(key=lambda r: abs(r.variacao_absoluta or 0), reverse=True)

    return ComparisonOut(
        election_a=ElectionOut(
            id=str(el_a.id), ano=el_a.ano, turno=el_a.turno,
            tipo=el_a.tipo_eleicao, descricao=el_a.descricao,
        ),
        election_b=ElectionOut(
            id=str(el_b.id), ano=el_b.ano, turno=el_b.turno,
            tipo=el_b.tipo_eleicao, descricao=el_b.descricao,
        ),
        rows=rows,
        meta=_SOURCE_TSE,
    )
