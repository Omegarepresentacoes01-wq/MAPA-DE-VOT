"""
Testes de integração — endpoints do sistema (health check, root, docs).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestRoot:
    async def test_root_returns_service_info(self, client: AsyncClient):
        """GET / deve retornar informações básicas do serviço."""
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "Mapa de Voto API"
        assert "version" in data
        assert "docs" in data
        assert "health" in data

    async def test_root_has_correct_version_format(self, client: AsyncClient):
        """Versão deve seguir formato semântico X.Y.Z."""
        resp = await client.get("/")
        version = resp.json()["version"]
        parts = version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestHealth:
    async def test_health_returns_200(self, client: AsyncClient):
        """GET /health deve retornar status 200 (mesmo com serviços indisponíveis)."""
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_has_required_fields(self, client: AsyncClient):
        """Health check deve incluir status global e mapa de serviços."""
        resp = await client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "services" in data
        assert "version" in data

    async def test_health_status_is_valid_enum(self, client: AsyncClient):
        """Status deve ser 'healthy' ou 'degraded'."""
        resp = await client.get("/health")
        status = resp.json()["status"]
        assert status in {"healthy", "degraded"}

    async def test_health_services_map(self, client: AsyncClient):
        """Serviços monitorados devem incluir postgres, redis e meilisearch."""
        resp = await client.get("/health")
        services = resp.json()["services"]
        assert "postgres" in services
        assert "redis" in services
        assert "meilisearch" in services


class TestDocs:
    async def test_openapi_schema_available(self, client: AsyncClient):
        """Esquema OpenAPI deve estar acessível em /openapi.json."""
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "paths" in data

    async def test_docs_ui_available(self, client: AsyncClient):
        """Interface Swagger UI deve estar acessível em /docs."""
        resp = await client.get("/docs")
        assert resp.status_code == 200

    async def test_openapi_has_all_routers(self, client: AsyncClient):
        """Esquema deve conter rotas de todos os módulos registrados."""
        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        expected_prefixes = [
            "/api/v1/search",
            "/api/v1/candidates",
            "/api/v1/elections",
            "/api/v1/territories",
            "/api/v1/maps",
            "/api/v1/exports",
            "/api/v1/sources",
        ]
        for prefix in expected_prefixes:
            matching = [p for p in paths if p.startswith(prefix)]
            assert matching, f"Nenhuma rota encontrada com prefixo '{prefix}'"


class TestMiddleware:
    async def test_timing_header_present(self, client: AsyncClient):
        """Middleware de timing deve adicionar X-Response-Time-Ms em toda resposta."""
        resp = await client.get("/")
        assert "x-response-time-ms" in resp.headers
        timing = int(resp.headers["x-response-time-ms"])
        assert timing >= 0

    async def test_cors_header_present(self, client: AsyncClient):
        """CORS deve aceitar origem configurada."""
        resp = await client.get(
            "/",
            headers={"Origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers
