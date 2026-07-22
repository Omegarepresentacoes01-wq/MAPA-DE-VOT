"""
Router de Fontes de Dados — /api/v1/sources
Expõe DataSource, DatasetVersion e lineage para transparência total.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models.governance import DataSource, DatasetVersion
from shared.schemas import DataSourceOut, DatasetVersionOut, PaginatedResponse, SourceMeta

router = APIRouter()

_SOURCE_SELF = SourceMeta(
    fonte="Plataforma — Metadados de ingestão",
    cobertura_geografica="Nacional",
)


def _source_to_out(s: DataSource) -> DataSourceOut:
    return DataSourceOut(
        id=str(s.id),
        nome=s.nome,
        url=s.url,
        tipo=s.tipo,
        descricao=s.descricao,
        classificacao=s.classificacao,
        limitacoes=s.limitacoes,
    )


def _version_to_out(v: DatasetVersion) -> DatasetVersionOut:
    return DatasetVersionOut(
        id=str(v.id),
        source_id=str(v.source_id) if v.source_id else "",
        nome_dataset=v.nome_dataset,
        ano_referencia=v.ano_referencia,
        data_ingestao=v.data_ingestao,
        status=v.status,
        registros_inseridos=v.registros_inseridos,
        registros_atualizados=v.registros_atualizados,
        tamanho_bytes=v.tamanho_bytes,
    )


@router.get("/sources", response_model=PaginatedResponse[DataSourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[DataSourceOut]:
    """Lista todas as fontes de dados registradas."""
    stmt = select(DataSource).order_by(DataSource.nome)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.limit(size).offset((page - 1) * size)
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedResponse(
        items=[_source_to_out(s) for s in rows],
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size),
        meta=_SOURCE_SELF,
    )


@router.get("/sources/{source_id}", response_model=DataSourceOut)
async def get_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> DataSourceOut:
    """Detalhes de uma fonte de dados."""
    s = (await db.execute(select(DataSource).where(DataSource.id == source_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Fonte não encontrada")
    return _source_to_out(s)


@router.get("/sources/{source_id}/versions", response_model=PaginatedResponse[DatasetVersionOut])
async def list_dataset_versions(
    source_id: uuid.UUID,
    status: str = Query(None, description="Filtrar por status: success | failed | running"),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[DatasetVersionOut]:
    """Histórico de versões de dataset de uma fonte."""
    s = (await db.execute(select(DataSource).where(DataSource.id == source_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Fonte não encontrada")

    stmt = (
        select(DatasetVersion)
        .where(DatasetVersion.source_id == source_id)
        .order_by(desc(DatasetVersion.data_ingestao))
    )
    if status:
        stmt = stmt.where(DatasetVersion.status == status)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.limit(size).offset((page - 1) * size)
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedResponse(
        items=[_version_to_out(v) for v in rows],
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size),
        meta=_SOURCE_SELF,
    )


@router.get("/sources/versions/latest")
async def get_latest_versions(db: AsyncSession = Depends(get_db)):
    """Retorna a versão mais recente de cada dataset — para dashboard de saúde."""
    stmt = (
        select(
            DataSource.nome,
            DatasetVersion.nome_dataset,
            DatasetVersion.data_ingestao,
            DatasetVersion.status,
            DatasetVersion.registros_inseridos,
        )
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .distinct(DatasetVersion.source_id)
        .order_by(DatasetVersion.source_id, desc(DatasetVersion.data_ingestao))
    )
    rows = (await db.execute(stmt)).all()

    return {
        "fontes": [
            {
                "fonte": r.nome,
                "dataset": r.nome_dataset,
                "ultima_ingestao": r.data_ingestao.isoformat() if r.data_ingestao else None,
                "status": r.status,
                "registros": r.registros_inseridos,
            }
            for r in rows
        ],
        "meta": _SOURCE_SELF.model_dump(),
    }
