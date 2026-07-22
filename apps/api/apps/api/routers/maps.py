"""
Router de Mapas — /api/v1/maps
Proxy para pg_tileserv (MVT) + metadados de camadas disponíveis.

pg_tileserv serve automaticamente todas as tabelas PostGIS como tiles MVT.
Este router expõe:
  - /maps/layers — catálogo de camadas disponíveis
  - /maps/layers/{layer_id} — metadados de uma camada
  - /maps/tiles/{layer_id}/{z}/{x}/{y}.mvt — proxy para pg_tileserv
  - /maps/geojson/{codigo_ibge} — boundary de um município (GeoJSON)

Camadas disponíveis após ingestão IBGE:
  - public.territory (municípios com geometria)
  - public.census_sector (setores censitários)
  - public.polling_place (locais de votação)
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from shared.schemas import TileLayerOut, SourceMeta

router = APIRouter()
logger = logging.getLogger(__name__)

PG_TILESERV_URL = os.environ.get("PG_TILESERV_URL", "http://pg_tileserv:7800")

_SOURCE_IBGE = SourceMeta(
    fonte="IBGE — Malhas Territoriais + pg_tileserv",
    url="https://www.ibge.gov.br/geociencias",
    cobertura_temporal="2022",
    cobertura_geografica="Nacional",
)

# Camadas pré-definidas (mapeiam para tabelas PostGIS)
LAYERS = [
    TileLayerOut(
        id="public.territory",
        nome="Municípios",
        tile_url=f"{PG_TILESERV_URL}/public.territory/{{z}}/{{x}}/{{y}}.pbf",
        tipo="mvt",
        descricao="Malha municipal brasileira — IBGE 2022",
        meta=_SOURCE_IBGE,
    ),
    TileLayerOut(
        id="public.census_sector",
        nome="Setores Censitários",
        tile_url=f"{PG_TILESERV_URL}/public.census_sector/{{z}}/{{x}}/{{y}}.pbf",
        tipo="mvt",
        descricao="Setores censitários — IBGE Censo 2022",
        meta=_SOURCE_IBGE,
    ),
    TileLayerOut(
        id="public.polling_place",
        nome="Locais de Votação",
        tile_url=f"{PG_TILESERV_URL}/public.polling_place/{{z}}/{{x}}/{{y}}.pbf",
        tipo="mvt",
        descricao="Locais de votação com coordenadas georreferenciadas",
        meta=_SOURCE_IBGE,
    ),
]


# ─────────────────────────────────────────────
# GET /maps/layers
# ─────────────────────────────────────────────

@router.get("/maps/layers", response_model=List[TileLayerOut])
async def list_layers() -> List[TileLayerOut]:
    """Lista todas as camadas de mapa disponíveis."""
    return LAYERS


@router.get("/maps/layers/{layer_id:path}", response_model=TileLayerOut)
async def get_layer(layer_id: str) -> TileLayerOut:
    """Metadados de uma camada específica."""
    layer = next((l for l in LAYERS if l.id == layer_id), None)
    if not layer:
        raise HTTPException(status_code=404, detail=f"Camada '{layer_id}' não encontrada")
    return layer


# ─────────────────────────────────────────────
# GET /maps/tiles/{layer_id}/{z}/{x}/{y}.mvt
# Proxy para pg_tileserv
# ─────────────────────────────────────────────

@router.get("/maps/tiles/{layer_id:path}/{z}/{x}/{y}.mvt")
async def proxy_tile(layer_id: str, z: int, x: int, y: int) -> Response:
    """
    Proxy MVT para pg_tileserv.
    Permite adicionar autenticação e CORS no futuro sem mudar o cliente.
    """
    url = f"{PG_TILESERV_URL}/{layer_id}/{z}/{x}/{y}.pbf"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)

        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Tile não encontrado")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Erro do servidor de tiles")

        return Response(
            content=resp.content,
            media_type="application/x-protobuf",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Servidor de tiles indisponível")


# ─────────────────────────────────────────────
# GET /maps/geojson/{codigo_ibge}
# Boundary de um município como GeoJSON
# ─────────────────────────────────────────────

@router.get("/maps/geojson/{codigo_ibge}")
async def get_municipality_geojson(codigo_ibge: str) -> JSONResponse:
    """
    Retorna o polígono de um município como GeoJSON Feature.
    Útil para highlight no mapa sem precisar de tiles.
    """
    from db.session import AsyncSessionLocal
    from db.models.territorial import Territory
    from geoalchemy2.shape import to_shape
    from sqlalchemy import select
    import json

    async with AsyncSessionLocal() as session:
        stmt = select(Territory).where(Territory.codigo_ibge == codigo_ibge)
        t = (await session.execute(stmt)).scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=404, detail=f"Município {codigo_ibge} não encontrado")

    if not t.geom:
        raise HTTPException(status_code=404, detail="Geometria não disponível para este município")

    shape = to_shape(t.geom)
    geojson = {
        "type": "Feature",
        "geometry": json.loads(shape.__geo_interface__.__repr__()
                               if hasattr(shape, "__geo_interface__")
                               else "{}"),
        "properties": {
            "codigo_ibge": t.codigo_ibge,
            "nome": t.nome,
            "uf": t.uf,
            "populacao": t.populacao,
            "eleitorado": t.eleitorado,
        },
    }
    # Usa mapping() do shapely para serialização correta
    import shapely.geometry
    geojson["geometry"] = shapely.geometry.mapping(shape)

    return JSONResponse(
        content=geojson,
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ─────────────────────────────────────────────
# GET /maps/electoral-results/{election_id}/{codigo_ibge}
# GeoJSON com votos por município para choropleth
# ─────────────────────────────────────────────

@router.get("/maps/electoral-results/{election_id}")
async def get_electoral_results_geojson(
    election_id: str,
    cargo_codigo: Optional[str] = Query(None, description="Código do cargo"),
    partido: Optional[str] = Query(None, description="Sigla do partido"),
    limit: int = Query(5572, description="Max municípios"),
) -> JSONResponse:
    """
    Retorna FeatureCollection GeoJSON com geometrias + votos por município.
    Usado para mapas coropléticos de resultado eleitoral.
    """
    import uuid as _uuid
    from db.session import AsyncSessionLocal
    from db.models.political import Candidacy, Party, Office, Election
    from db.models.territorial import Territory
    from db.models.analytical import VoteResult
    from sqlalchemy import select, func
    from geoalchemy2.shape import to_shape
    import shapely.geometry

    try:
        eid = _uuid.UUID(election_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="election_id inválido")

    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                Territory.codigo_ibge,
                Territory.nome,
                Territory.uf,
                Territory.geom,
                func.sum(VoteResult.votos).label("votos"),
            )
            .join(VoteResult, VoteResult.territory_id == Territory.id)
            .join(Candidacy, Candidacy.id == VoteResult.candidacy_id)
            .where(VoteResult.election_id == eid)
            .group_by(
                Territory.codigo_ibge,
                Territory.nome,
                Territory.uf,
                Territory.geom,
            )
            .order_by(func.sum(VoteResult.votos).desc())
            .limit(limit)
        )

        if cargo_codigo:
            stmt = stmt.join(Office, Office.id == Candidacy.office_id).where(
                Office.codigo == cargo_codigo
            )
        if partido:
            stmt = stmt.join(Party, Party.id == Candidacy.party_id).where(
                Party.sigla.ilike(partido)
            )

        rows = (await session.execute(stmt)).all()

    features = []
    for r in rows:
        geom = None
        if r.geom:
            try:
                geom = shapely.geometry.mapping(to_shape(r.geom))
            except Exception:
                geom = None

        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "codigo_ibge": r.codigo_ibge,
                "nome": r.nome,
                "uf": r.uf,
                "votos": r.votos,
            },
        })

    return JSONResponse(
        content={"type": "FeatureCollection", "features": features},
        headers={"Cache-Control": "public, max-age=1800"},
    )
