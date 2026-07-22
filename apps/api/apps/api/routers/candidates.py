"""
Router de Candidatos — /api/v1/candidates
Ficha 360 do candidato: dados pessoais, histórico, finanças, votos por território.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from db.models.political import Person, Candidacy, Party, Office, Election
from db.models.financial import CampaignRevenue, CampaignExpense
from db.models.analytical import VoteResult
from db.models.territorial import Territory
from shared.schemas import (
    CandidateOut, CandidacyDetailOut, SourceMeta, PaginatedResponse
)

router = APIRouter()

_SOURCE_TSE = SourceMeta(
    fonte="TSE — Portal de Dados Abertos + DivulgaCandContas",
    url="https://dadosabertos.tse.jus.br/",
    cobertura_temporal="2000–2024",
    cobertura_geografica="Nacional",
)


def _candidacy_to_out(c: Candidacy) -> CandidateOut:
    person = c.person if hasattr(c, "person") and c.person else None
    party = c.party if hasattr(c, "party") and c.party else None
    office = c.office if hasattr(c, "office") and c.office else None
    territory = c.territory if hasattr(c, "territory") and c.territory else None

    return CandidateOut(
        candidacy_id=str(c.id),
        person_id=str(c.person_id),
        nome=person.nome if person else "",
        nome_urna=person.nome_urna if person else None,
        nascimento=person.nascimento.isoformat() if person and person.nascimento else None,
        genero=person.genero,
        raca_cor=person.raca_cor,
        escolaridade=person.escolaridade,
        ocupacao=person.ocupacao,
        partido_sigla=party.sigla if party else None,
        partido_nome=party.nome if party else None,
        cargo_codigo=office.codigo if office else None,
        cargo_descricao=office.descricao if office else None,
        cargo_nivel=office.nivel if office else None,
        territorio_nome=territory.nome if territory else None,
        territorio_codigo_ibge=territory.codigo_ibge if territory else None,
        territorio_uf=territory.uf if territory else None,
        situacao=c.situacao,
        numero_urna=c.numero_urna,
        bens_declarados=float(c.bens_declarados_total) if c.bens_declarados_total else None,
        votos_totais=c.votos_totais,
        meta=_SOURCE_TSE,
    )


# ─────────────────────────────────────────────
# GET /candidates/{candidacy_id}
# ─────────────────────────────────────────────

@router.get("/candidates/{candidacy_id}", response_model=CandidacyDetailOut)
async def get_candidate_ficha360(
    candidacy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CandidacyDetailOut:
    """
    Ficha 360 do candidato: dados pessoais, histórico eleitoral,
    finanças de campanha, distribuição de votos por território.
    """
    stmt = (
        select(Candidacy)
        .options(
            selectinload(Candidacy.person),
            selectinload(Candidacy.party),
            selectinload(Candidacy.office),
            selectinload(Candidacy.territory),
            selectinload(Candidacy.election),
        )
        .where(Candidacy.id == candidacy_id)
    )
    c = (await db.execute(stmt)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada")

    # Histórico completo do candidato (outras candidaturas da mesma pessoa)
    historico_stmt = (
        select(Candidacy)
        .options(
            selectinload(Candidacy.election),
            selectinload(Candidacy.party),
            selectinload(Candidacy.office),
        )
        .where(
            Candidacy.person_id == c.person_id,
            Candidacy.id != c.id,
        )
        .order_by(Candidacy.created_at.desc())
    )
    historico = (await db.execute(historico_stmt)).scalars().all()

    # Finanças: receitas por origem
    rev_stmt = (
        select(
            CampaignRevenue.origem,
            func.count(CampaignRevenue.id).label("qty"),
            func.sum(CampaignRevenue.valor).label("total"),
        )
        .where(CampaignRevenue.candidacy_id == candidacy_id)
        .group_by(CampaignRevenue.origem)
        .order_by(func.sum(CampaignRevenue.valor).desc())
    )
    receitas = (await db.execute(rev_stmt)).all()

    # Finanças: despesas por categoria
    exp_stmt = (
        select(
            CampaignExpense.categoria,
            func.count(CampaignExpense.id).label("qty"),
            func.sum(CampaignExpense.valor).label("total"),
        )
        .where(CampaignExpense.candidacy_id == candidacy_id)
        .group_by(CampaignExpense.categoria)
        .order_by(func.sum(CampaignExpense.valor).desc())
    )
    despesas = (await db.execute(exp_stmt)).all()

    # Top 10 municípios por votos
    votos_stmt = (
        select(Territory.nome, Territory.codigo_ibge, VoteResult.votos)
        .join(Territory, Territory.id == VoteResult.territory_id)
        .where(VoteResult.candidacy_id == candidacy_id)
        .order_by(VoteResult.votos.desc())
        .limit(10)
    )
    votos_por_municipio = (await db.execute(votos_stmt)).all()

    return CandidacyDetailOut(
        candidatura=_candidacy_to_out(c),
        historico_eleitoral=[
            {
                "eleicao": f"{h.election.ano} T{h.election.turno}" if h.election else "?",
                "cargo": h.office.descricao if h.office else "?",
                "partido": h.party.sigla if h.party else "?",
                "situacao": h.situacao,
            }
            for h in historico
        ],
        financas={
            "total_receitas": float(sum(r.total or 0 for r in receitas)),
            "total_despesas": float(sum(d.total or 0 for d in despesas)),
            "receitas_por_origem": [
                {"origem": r.origem, "quantidade": r.qty, "total": float(r.total or 0)}
                for r in receitas
            ],
            "despesas_por_categoria": [
                {"categoria": d.categoria, "quantidade": d.qty, "total": float(d.total or 0)}
                for d in despesas
            ],
        },
        votos_por_municipio=[
            {"nome": v.nome, "codigo_ibge": v.codigo_ibge, "votos": v.votos}
            for v in votos_por_municipio
        ],
        meta=_SOURCE_TSE,
    )


# ─────────────────────────────────────────────
# GET /candidates/by-person/{person_id}
# ─────────────────────────────────────────────

@router.get("/candidates/by-person/{person_id}")
async def get_person_history(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Histórico completo de candidaturas de uma pessoa."""
    stmt = (
        select(Candidacy)
        .options(
            selectinload(Candidacy.election),
            selectinload(Candidacy.party),
            selectinload(Candidacy.office),
            selectinload(Candidacy.territory),
        )
        .where(Candidacy.person_id == person_id)
        .order_by(Candidacy.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada ou sem candidaturas")

    return {
        "person_id": str(person_id),
        "candidaturas": [_candidacy_to_out(c) for c in rows],
        "meta": _SOURCE_TSE.model_dump(),
    }
