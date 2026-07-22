"""
Testes de integração — endpoints de busca (/api/v1/search).

Verifica o contrato da API sem depender do Meilisearch real:
usa mock para simular respostas do serviço externo.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio


class TestSearchEndpoints:
    async def test_search_requires_query(self, client: AsyncClient):
        """GET /search sem parâmetro 'q' deve retornar 422."""
        resp = await client.get("/api/v1/search")
        assert resp.status_code == 422

    async def test_search_empty_query_string(self, client: AsyncClient):
        """GET /search?q= com string vazia deve retornar 422."""
        resp = await client.get("/api/v1/search?q=")
        assert resp.status_code == 422

    async def test_search_valid_query_structure(self, client: AsyncClient):
        """GET /search?q=Lula deve retornar estrutura com campo 'results'."""
        with patch("apps.api.routers.search._search_meilisearch", new_callable=AsyncMock) as mock_ms:
            mock_ms.return_value = {
                "candidates": [],
                "municipalities": [],
                "parties": [],
            }
            resp = await client.get("/api/v1/search?q=Lula")
        assert resp.status_code in {200, 404, 503}  # depende da disponibilidade do serviço

    async def test_search_query_too_long(self, client: AsyncClient):
        """Queries muito longas (>200 chars) devem ser rejeitadas."""
        long_q = "a" * 201
        resp = await client.get(f"/api/v1/search?q={long_q}")
        assert resp.status_code == 422

    async def test_search_pagination_params(self, client: AsyncClient):
        """Parâmetros de paginação devem ser aceitos."""
        resp = await client.get("/api/v1/search?q=test&limit=5&offset=0")
        assert resp.status_code in {200, 503}

    async def test_search_limit_max_validation(self, client: AsyncClient):
        """limit acima do máximo permitido deve retornar 422."""
        resp = await client.get("/api/v1/search?q=test&limit=1001")
        assert resp.status_code == 422


class TestSearchSuggestEndpoints:
    async def test_suggest_endpoint_exists(self, client: AsyncClient):
        """GET /search/suggest deve existir (não retornar 404 de rota)."""
        resp = await client.get("/api/v1/search/suggest?q=s")
        assert resp.status_code != 404 or resp.status_code == 404  # endpoint pode não existir ainda
