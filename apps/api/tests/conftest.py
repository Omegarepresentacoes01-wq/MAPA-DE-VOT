"""
conftest.py — fixtures compartilhadas para os testes de integração da API.

Usa SQLite em memória para isolar os testes do PostgreSQL de produção.
Não requer serviços Docker rodando.
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# ── variáveis de ambiente antes de qualquer import do projeto ──────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MEILISEARCH_URL", "http://localhost:7700")
os.environ.setdefault("MEILISEARCH_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


# ── engine de testes (SQLite async em memória) ─────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine, expire_on_commit=False, class_=AsyncSession
)


@pytest.fixture(scope="session")
def event_loop():
    """Event loop compartilhado para toda a sessão de testes."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_schema():
    """Cria o schema do banco de dados em memória uma única vez por sessão."""
    try:
        from db.models.base import Base
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ImportError:
        # Quando o pacote db ainda não está instalado no ambiente de teste local
        pass
    yield
    async with test_engine.begin() as conn:
        try:
            from db.models.base import Base
            await conn.run_sync(Base.metadata.drop_all)
        except ImportError:
            pass


@pytest_asyncio.fixture
async def db_session(db_schema) -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco de dados isolada por teste (rollback automático)."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app() -> FastAPI:
    """Instância da aplicação FastAPI para testes."""
    from apps.api.main import app as fastapi_app
    return fastapi_app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP assíncrono apontado para a aplicação de testes."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
