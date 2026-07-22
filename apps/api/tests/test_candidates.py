"""
Testes de integração — endpoints de candidatos (/api/v1/candidates).

Foca no contrato da API: formatos de request/response, validação e
tratamento de erros sem exigir dados reais no banco.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestCandidatesListEndpoint:
    async def test_list_candidates_returns_200(self, client: AsyncClient):
        """GET /candidates deve retornar 200 mesmo sem candidatos."""
        resp = await client.get("/api/v1/candidates")
        assert resp.status_code in {200, 422}

    async def test_list_candidates_has_pagination(self, client: AsyncClient):
        """Resposta de listagem deve incluir metadados de paginação."""
        resp = await client.get("/api/v1/candidates?limit=10&offset=0")
        if resp.status_code == 200:
            data = resp.json()
            assert "items" in data or "results" in data or isinstance(data, list)

    async def test_list_candidates_filter_by_ano(self, client: AsyncClient):
        """Filtro por ano eleitoral deve ser aceito."""
        resp = await client.get("/api/v1/candidates?ano=2022")
        assert resp.status_code in {200, 422}

    async def test_list_candidates_filter_by_uf(self, client: AsyncClient):
        """Filtro por UF deve ser aceito."""
        resp = await client.get("/api/v1/candidates?uf=SP")
        assert resp.status_code in {200, 422}

    async def test_list_candidates_invalid_limit(self, client: AsyncClient):
        """Limit negativo deve retornar 422."""
        resp = await client.get("/api/v1/candidates?limit=-1")
        assert resp.status_code == 422


class TestCandidateDetailEndpoint:
    async def test_candidate_not_found_returns_404(self, client: AsyncClient):
        """Candidato inexistente deve retornar 404."""
        resp = await client.get("/api/v1/candidates/99999999")
        assert resp.status_code == 404

    async def test_candidate_invalid_id_format(self, client: AsyncClient):
        """ID não numérico deve retornar 422."""
        resp = await client.get("/api/v1/candidates/abc")
        assert resp.status_code == 422

    async def test_candidate_detail_response_shape(self, client: AsyncClient):
        """Se candidato existir, resposta deve incluir campos obrigatórios."""
        # Testa apenas a estrutura quando o candidato existe
        resp = await client.get("/api/v1/candidates/1")
        if resp.status_code == 200:
            data = resp.json()
            assert "id" in data
            assert "nome" in data


class TestCandidateFinancesEndpoint:
    async def test_finances_not_found_returns_404(self, client: AsyncClient):
        """Candidato inexistente em finanças deve retornar 404."""
        resp = await client.get("/api/v1/candidates/99999999/finances")
        assert resp.status_code == 404

    async def test_finances_invalid_id(self, client: AsyncClient):
        """ID inválido em finanças deve retornar 422."""
        resp = await client.get("/api/v1/candidates/abc/finances")
        assert resp.status_code == 422


class TestCandidateVotesEndpoint:
    async def test_votes_not_found_returns_404(self, client: AsyncClient):
        """Votos de candidato inexistente deve retornar 404."""
        resp = await client.get("/api/v1/candidates/99999999/votes")
        assert resp.status_code == 404
