"""
Pipeline IBGE — Malhas Territoriais (municípios + estados).

Etapa 5 do MVP.

Fontes:
  - Malhas municipais: GeoFTP IBGE → BR_Municipios_{ano}.zip (Shapefile)
  - API localidades IBGE: todos os municípios com código e UF

Etapas:
  1. Busca tabela completa de municípios via API localidades (JSON)
  2. Download do ZIP da malha municipal do GeoFTP
  3. Leitura do Shapefile com GeoPandas (projeção → WGS84)
  4. Upsert em Territory com geometria PostGIS
  5. Atualização dos Territory com código placeholder (da Etapa 3):
     substitui os codes proxy (cd_municipio_tse + '00') pelos reais IBGE 7d
  6. Registro de DatasetVersion

Uso:
  python -m etl.ibge.territories
  python scripts/ingest.py ibge territories
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import geopandas as gpd
import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import mapping, shape
from shapely.ops import transform
import pyproj

from etl.ibge.constants import (
    IBGE_MUNICIPIOS_URL_2022, IBGE_ESTADOS_URL,
    MUNICIPIOS_SHP_COLUMNS, POSTGIS_SRID,
    IBGE_LOCALIDADES_URL,
)
from etl.ibge.municipio_codes import get_ibge_municipios_list, load_municipio_cache
from etl.common.download import (
    download_file, extract_zip,
    register_dataset_version, mark_version_done, mark_version_failed,
    RAW_DIR, STAGING_DIR,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Busca lista de municípios via API
# ──────────────────────────────────────────────────────────────────────────────

def fetch_municipios_api() -> list[dict]:
    """
    Retorna todos os municípios do Brasil via API IBGE localidades.
    Lista de dicts com: codigo_ibge, nome, uf
    """
    logger.info("Buscando municípios via API IBGE localidades...")
    municipios = get_ibge_municipios_list()
    logger.info(f"API retornou {len(municipios):,} municípios")
    return municipios


# ──────────────────────────────────────────────────────────────────────────────
# 2. Download e leitura da malha geográfica
# ──────────────────────────────────────────────────────────────────────────────

def download_malha_municipal(ano: int = 2022) -> Path:
    url = IBGE_MUNICIPIOS_URL_2022 if ano == 2022 else (
        f"https://geoftp.ibge.gov.br/organizacao_do_territorio/"
        f"malhas_territoriais/malhas_municipais/{ano}/Brasil/BR/BR_Municipios_{ano}.zip"
    )
    dest = RAW_DIR / "ibge" / f"BR_Municipios_{ano}.zip"
    return download_file(url, dest)


def read_municipios_shp(zip_path: Path, ano: int = 2022) -> gpd.GeoDataFrame:
    """
    Extrai e lê o Shapefile de municípios.
    Reprojecta para WGS84 (SRID 4326) se necessário.
    """
    extract_dir = STAGING_DIR / "ibge" / f"municipios_{ano}"
    shp_files = extract_zip(zip_path, extract_dir, pattern=".shp")

    # Encontra o .shp principal (não o .shx)
    shp_path = next(
        (f for f in extract_dir.iterdir() if f.suffix == ".shp" and "Municipios" in f.name),
        None,
    )
    if not shp_path:
        # Tenta qualquer .shp
        shp_path = next((f for f in extract_dir.iterdir() if f.suffix == ".shp"), None)

    if not shp_path:
        raise FileNotFoundError(f"Shapefile não encontrado em {extract_dir}")

    logger.info(f"Lendo shapefile: {shp_path}")
    gdf = gpd.read_file(shp_path, engine="pyogrio")
    logger.info(f"GeoDataFrame: {len(gdf):,} municípios, CRS: {gdf.crs}")

    # Reprojectar para WGS84 se necessário
    if gdf.crs and gdf.crs.to_epsg() != POSTGIS_SRID:
        logger.info(f"Reprojetando de {gdf.crs} → EPSG:{POSTGIS_SRID}")
        gdf = gdf.to_crs(epsg=POSTGIS_SRID)

    return gdf


# ──────────────────────────────────────────────────────────────────────────────
# 3. Upsert de Territory com geometria
# ──────────────────────────────────────────────────────────────────────────────

async def upsert_territories_from_gdf(
    session,
    gdf: gpd.GeoDataFrame,
    version_id,
    municipios_api: list[dict],
) -> tuple[int, int]:
    """
    Upsert de Territory para cada município do GeoDataFrame.
    Usa código IBGE 7d como chave de deduplicação.
    Retorna (inseridos, atualizados).
    """
    from sqlalchemy import select
    from db.models.territorial import Territory

    # Índice de código IBGE → dados da API para enriquecer
    api_index = {m["codigo_ibge"]: m for m in municipios_api}

    inseridos = 0
    atualizados = 0
    BATCH_SIZE = 200

    # Determina nome da coluna de código IBGE no GDF
    cod_col = next(
        (c for c in gdf.columns if "CD_MUN" in c.upper() or "COD_MUN" in c.upper()), None
    )
    nome_col = next(
        (c for c in gdf.columns if "NM_MUN" in c.upper() or "NOME" in c.upper()), None
    )
    uf_col = next(
        (c for c in gdf.columns if "SIGLA_UF" in c.upper() or "UF" in c.upper()), None
    )
    area_col = next(
        (c for c in gdf.columns if "AREA" in c.upper()), None
    )

    logger.info(f"Colunas detectadas: cod={cod_col}, nome={nome_col}, uf={uf_col}, area={area_col}")

    rows = list(gdf.itertuples(index=False))
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]

        for row in batch:
            codigo = str(getattr(row, cod_col) if cod_col else "")
            if not codigo or len(codigo) < 6:
                continue

            nome = str(getattr(row, nome_col) if nome_col else "")
            uf = str(getattr(row, uf_col) if uf_col else "")
            area = float(getattr(row, area_col)) if area_col and getattr(row, area_col) else None

            # Geometry → WKB para PostGIS
            geom_shapely = row.geometry
            geom_postgis = None
            if geom_shapely is not None and not geom_shapely.is_empty:
                geom_postgis = from_shape(geom_shapely, srid=POSTGIS_SRID)

            # Busca ou cria Territory
            stmt = select(Territory).where(Territory.codigo_ibge == codigo)
            result = await session.execute(stmt)
            territory = result.scalar_one_or_none()

            if not territory:
                territory = Territory(
                    tipo="municipio",
                    codigo_ibge=codigo,
                    nome=nome,
                    uf=uf,
                    geom=geom_postgis,
                    area_km2=area,
                )
                session.add(territory)
                inseridos += 1
            else:
                # Atualiza geometria e nome se já existia (placeholder da Etapa 3)
                territory.nome = nome
                territory.uf = uf
                territory.geom = geom_postgis
                if area:
                    territory.area_km2 = area
                atualizados += 1

        await session.commit()
        logger.info(f"  Lote {i // BATCH_SIZE + 1}: {inseridos} inseridos / {atualizados} atualizados")

    return inseridos, atualizados


# ──────────────────────────────────────────────────────────────────────────────
# 4. Reconciliação dos códigos proxy da Etapa 3
# ──────────────────────────────────────────────────────────────────────────────

async def reconcile_tse_territory_codes(session):
    """
    Após carregar os Territories com código IBGE real,
    atualiza os Territory criados na Etapa 3 com código proxy (cd_mun_tse + '00')
    substituindo pelo código IBGE 7d correto via match nome+UF.

    Também atualiza Candidacy.territory_id para apontar para o Territory correto.
    """
    from sqlalchemy import select
    from db.models.territorial import Territory
    from db.models.political import Candidacy

    logger.info("Reconciliando códigos proxy TSE → IBGE...")

    # Carrega cache nome → código IBGE
    cache = load_municipio_cache()

    # Busca territories com código proxy (terminam em '00' ou 'UF_')
    stmt = select(Territory).where(
        Territory.codigo_ibge.like("%00") | Territory.codigo_ibge.like("UF_%")
    )
    result = await session.execute(stmt)
    proxies = result.scalars().all()
    logger.info(f"Territories com código proxy: {len(proxies)}")

    import unicodedata

    def norm(s: str) -> str:
        s = s.upper().strip()
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    reconciliados = 0
    for proxy in proxies:
        key = (norm(proxy.nome), proxy.uf.upper())
        ibge_code = cache.get(key)
        if not ibge_code:
            continue

        # Verifica se já existe Territory com o código real
        stmt_real = select(Territory).where(Territory.codigo_ibge == ibge_code)
        real = (await session.execute(stmt_real)).scalar_one_or_none()

        if real:
            # Redireciona Candidacies para o territory real
            stmt_cand = select(Candidacy).where(Candidacy.territory_id == proxy.id)
            cands = (await session.execute(stmt_cand)).scalars().all()
            for c in cands:
                c.territory_id = real.id

            # Remove proxy
            await session.delete(proxy)
            reconciliados += 1
        else:
            # Atualiza código do proxy para o real
            proxy.codigo_ibge = ibge_code
            reconciliados += 1

    await session.commit()
    logger.info(f"Reconciliação concluída: {reconciliados} territories atualizados")
    return reconciliados


# ──────────────────────────────────────────────────────────────────────────────
# 5. Pipeline principal
# ──────────────────────────────────────────────────────────────────────────────

async def _run_async(uf: Optional[str] = None, ano: int = 2022, upload_minio: bool = True):
    from db.session import AsyncSessionLocal
    from db.models.governance import DataSource
    from sqlalchemy import select

    logger.info(f"=== Ingestão de malhas territoriais IBGE {ano} ===")

    # 1. Lista municípios via API
    municipios_api = fetch_municipios_api()

    # 2. Download da malha geográfica
    zip_path = download_malha_municipal(ano)

    # 3. Leitura do Shapefile
    gdf = read_municipios_shp(zip_path, ano)

    # Filtra por UF se especificado
    if uf:
        uf_col = next((c for c in gdf.columns if "SIGLA_UF" in c.upper()), None)
        if uf_col:
            gdf = gdf[gdf[uf_col].str.upper() == uf.upper()]
            logger.info(f"Filtrado para UF={uf}: {len(gdf):,} municípios")

    async with AsyncSessionLocal() as session:
        # Busca DataSource IBGE
        stmt_src = select(DataSource).where(DataSource.nome == "IBGE — Malhas Territoriais")
        src = (await session.execute(stmt_src)).scalar_one_or_none()
        source_id = src.id if src else None

        version = await register_dataset_version(
            session, source_id,
            f"BR_Municipios_{ano}",
            ano, zip_path, upload_minio,
        )
        await session.commit()

        try:
            # 4. Upsert territories com geometria
            inseridos, atualizados = await upsert_territories_from_gdf(
                session, gdf, version.id, municipios_api
            )

            # 5. Reconcilia códigos proxy da Etapa 3
            reconciliados = await reconcile_tse_territory_codes(session)

            await mark_version_done(session, version, inseridos, atualizados)
            await session.commit()

            logger.info(
                f"=== IBGE Malhas concluído: {inseridos} inseridos, "
                f"{atualizados} atualizados, {reconciliados} códigos reconciliados ==="
            )

        except Exception as exc:
            logger.error(f"Erro: {exc}", exc_info=True)
            await mark_version_failed(session, version, str(exc))
            await session.commit()
            raise


def run(uf: Optional[str] = None, ano: int = 2022, upload_minio: bool = True):
    """Entry point síncrono — chamado pelo Celery e CLI."""
    asyncio.run(_run_async(uf=uf, ano=ano, upload_minio=upload_minio))


# ──────────────────────────────────────────────────────────────────────────────
# Script para construir índices espaciais após ingestão
# ──────────────────────────────────────────────────────────────────────────────

async def build_spatial_indexes():
    """
    Cria índices GIST nas colunas de geometria após carga inicial.
    Executar uma vez após a ingestão de territories.
    """
    from sqlalchemy import text
    from db.session import AsyncSessionLocal

    logger.info("Construindo índices espaciais...")
    async with AsyncSessionLocal() as session:
        await session.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_territory_geom "
            "ON territory USING GIST (geom)"
        ))
        await session.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_census_sector_geom "
            "ON census_sector USING GIST (geom)"
        ))
        await session.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_polling_place_geom "
            "ON polling_place USING GIST (geom)"
        ))
        await session.commit()
    logger.info("Índices espaciais criados.")


if __name__ == "__main__":
    import typer
    from rich.logging import RichHandler
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO, handlers=[RichHandler()])
    app = typer.Typer()

    @app.command()
    def main(
        uf: Optional[str] = typer.Option(None, help="UF (ex: SP). Omitir para nacional."),
        ano: int = typer.Option(2022, help="Ano da malha"),
        no_minio: bool = typer.Option(False),
        build_indexes: bool = typer.Option(False, help="Constrói índices GIST após carga"),
    ):
        run(uf=uf, ano=ano, upload_minio=not no_minio)
        if build_indexes:
            asyncio.run(build_spatial_indexes())

    app()
