"""
Script para construir índices espaciais no PostgreSQL/PostGIS após ingestão IBGE.
Executar uma vez após: make ingest-ibge

Índices criados:
  - GIST em territory.geom
  - GIST em census_sector.geom
  - GIST em polling_place.geom
  - B-tree em territory.codigo_ibge (para JOINs com TSE)
  - B-tree em territory.nome, territory.uf (para busca)
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.logging import RichHandler
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])
logger = logging.getLogger(__name__)


INDEXES = [
    # Índices espaciais GIST
    ("idx_territory_geom",      "territory",     "GIST",   "geom"),
    ("idx_census_sector_geom",  "census_sector", "GIST",   "geom"),
    ("idx_polling_place_geom",  "polling_place", "GIST",   "geom"),

    # Índices B-tree para performance de queries
    ("idx_territory_codigo_ibge", "territory", "BTREE", "codigo_ibge"),
    ("idx_territory_uf_nome",     "territory", "BTREE", "uf, nome"),
    ("idx_candidacy_tse_sq",      "candidacy", "BTREE", "tse_sq_candidato"),
    ("idx_vote_result_election",  "vote_result", "BTREE", "election_id, territory_id"),
    ("idx_person_nome",           "person",    "BTREE",  "nome text_pattern_ops"),

    # Índice trigrama para busca textual por nome (requer pg_trgm)
    ("idx_person_nome_trgm",      "person",    "GIN",   "nome gin_trgm_ops"),
    ("idx_territory_nome_trgm",   "territory", "GIN",   "nome gin_trgm_ops"),
]


async def build_indexes():
    from db.session import engine

    logger.info(f"Criando {len(INDEXES)} índices no PostgreSQL...")

    async with engine.connect() as conn:
        for name, table, method, cols in INDEXES:
            sql = (
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} "
                f"ON {table} USING {method} ({cols})"
            )
            try:
                await conn.execute(text(sql))
                await conn.commit()
                logger.info(f"  ✅ {name}")
            except Exception as e:
                logger.warning(f"  ⚠ {name}: {e}")

    logger.info("Construção de índices concluída.")


if __name__ == "__main__":
    asyncio.run(build_indexes())
