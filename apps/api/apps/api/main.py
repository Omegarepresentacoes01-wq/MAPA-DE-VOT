"""
FastAPI — aplicação principal.
Mapa de Voto — Plataforma de Inteligência Eleitoral e Territorial.
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🗳️  Mapa de Voto API iniciando...")
    # Aqui podemos inicializar conexão com Meilisearch, Redis etc.
    yield
    logger.info("API encerrando.")


# ─────────────────────────────────────────────
# Aplicação
# ─────────────────────────────────────────────

app = FastAPI(
    title="Mapa de Voto — API",
    description=(
        "Plataforma de Inteligência Eleitoral e Territorial. "
        "Dados oficiais TSE + IBGE com rastreabilidade total de fonte."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────
# Middlewares
# ─────────────────────────────────────────────

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# ─────────────────────────────────────────────
# Middleware de timing
# ─────────────────────────────────────────────

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    return response


# ─────────────────────────────────────────────
# Handler global de erros
# ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno. Por favor, tente novamente."},
    )


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────

from apps.api.routers import (
    search,
    candidates,
    elections,
    territories,
    maps,
    exports,
    sources,
)

PREFIX = "/api/v1"

app.include_router(search.router, prefix=PREFIX, tags=["Busca"])
app.include_router(candidates.router, prefix=PREFIX, tags=["Candidatos"])
app.include_router(elections.router, prefix=PREFIX, tags=["Eleições"])
app.include_router(territories.router, prefix=PREFIX, tags=["Territórios"])
app.include_router(maps.router, prefix=PREFIX, tags=["Mapas"])
app.include_router(exports.router, prefix=PREFIX, tags=["Exportações"])
app.include_router(sources.router, prefix=PREFIX, tags=["Fontes"])


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health():
    """Health check — retorna status dos serviços dependentes."""
    from db.session import engine
    import redis.asyncio as aioredis

    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Redis
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = aioredis.from_url(redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Meilisearch
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{os.environ.get('MEILISEARCH_URL', 'http://meilisearch:7700')}/health")
        checks["meilisearch"] = "ok" if resp.status_code == 200 else f"status {resp.status_code}"
    except Exception as e:
        checks["meilisearch"] = f"error: {e}"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

    return {"status": overall, "services": checks, "version": "0.1.0"}


@app.get("/", tags=["Sistema"])
async def root():
    return {
        "service": "Mapa de Voto API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
