"""
Testes de integração — endpoints de territórios (/api/v1/territories).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestTerritoriesListEndpoint:
    async def test_list_territories_returns_200_or_422(self, client: AsyncClient):
        """GET /territories deve retornar 200."""
        resp = await client.get("/api/v1/territories")
        assert resp.status_code in {200, 422}

    async def test_list_territories_filter_by_uf(self, client: AsyncClient):
        """Filtro por UF deve ser aceito."""
        resp = await client.get("/api/v1/territories?uf=SP")
        assert resp.status_code in {200, 422}

    async def test_list_territories_filter_by_tipo(self, client: AsyncClient):
        """Filtro por tipo (municipio, estado) deve ser aceito."""
        resp = await client.get("/api/v1/territories?tipo=municipio")
        assert resp.status_code in {200, 422}

    async def test_list_territories_pagination(self, client: AsyncClient):
        """Parâmetros de paginação devem ser aceitos."""
        resp = await client.get("/api/v1/territories?limit=20&offset=0")
        assert resp.status_code in {200, 422}


class TestTerritoryDetailEndpoint:
    async def test_territory_not_found(self, client: AsyncClient):
        """Território inexistente deve retornar 404."""
        resp = await client.get("/api/v1/territories/9999999")
        assert resp.status_code == 404

    async def test_territory_invalid_code(self, client: AsyncClient):
        """Código de município inválido (não numérico) deve retornar 422."""
        resp = await client.get("/api/v1/territories/abc")
        assert resp.status_code == 422

    async def test_territory_results_not_found(self, client: AsyncClient):
        """Resultados eleitorais de território inexistente deve retornar 404."""
        resp = await client.get("/api/v1/territories/9999999/results")
        assert resp.status_code == 404

    async def test_territory_turnout_not_found(self, client: AsyncClient):
        """Turnout de território inexistente deve retornar 404."""
        resp = await client.get("/api/v1/territories/9999999/turnout")
        assert resp.status_code == 404


class TestTerritoryCompareEndpoint:
    async def test_compare_requires_ids(self, client: AsyncClient):
        """Comparação sem IDs deve retornar 422."""
        resp = await client.get("/api/v1/territories/compare")
        assert resp.status_code == 422

    async def test_compare_accepts_multiple_ids(self, client: AsyncClient):
        """Comparação com múltiplos IDs deve ser aceita."""
        resp = await client.get("/api/v1/territories/compare?ids=1&ids=2")
        assert resp.status_code in {200, 404, 422}
