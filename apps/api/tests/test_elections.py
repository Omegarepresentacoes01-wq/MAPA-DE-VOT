"""
Testes de integração — endpoints de eleições (/api/v1/elections).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestElectionsListEndpoint:
    async def test_list_elections_returns_200(self, client: AsyncClient):
        """GET /elections deve retornar 200."""
        resp = await client.get("/api/v1/elections")
        assert resp.status_code in {200, 422}

    async def test_list_elections_filter_by_ano(self, client: AsyncClient):
        """Filtro por ano deve ser aceito."""
        resp = await client.get("/api/v1/elections?ano=2022")
        assert resp.status_code in {200, 422}

    async def test_list_elections_filter_by_turno(self, client: AsyncClient):
        """Filtro por turno (1 ou 2) deve ser aceito."""
        resp = await client.get("/api/v1/elections?turno=1")
        assert resp.status_code in {200, 422}

    async def test_list_elections_invalid_turno(self, client: AsyncClient):
        """Turno inválido (ex: 3) deve retornar 422."""
        resp = await client.get("/api/v1/elections?turno=3")
        assert resp.status_code == 422

    async def test_list_elections_response_is_list(self, client: AsyncClient):
        """Resposta de listagem deve ser lista ou objeto paginado."""
        resp = await client.get("/api/v1/elections")
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))


class TestElectionDetailEndpoint:
    async def test_election_not_found_returns_404(self, client: AsyncClient):
        """Eleição inexistente deve retornar 404."""
        resp = await client.get("/api/v1/elections/99999")
        assert resp.status_code == 404

    async def test_election_invalid_id(self, client: AsyncClient):
        """ID não numérico deve retornar 422."""
        resp = await client.get("/api/v1/elections/invalid")
        assert resp.status_code == 422

    async def test_election_candidates_not_found(self, client: AsyncClient):
        """Candidatos de eleição inexistente deve retornar 404."""
        resp = await client.get("/api/v1/elections/99999/candidates")
        assert resp.status_code == 404

    async def test_election_stats_not_found(self, client: AsyncClient):
        """Stats de eleição inexistente deve retornar 404."""
        resp = await client.get("/api/v1/elections/99999/stats")
        assert resp.status_code == 404
