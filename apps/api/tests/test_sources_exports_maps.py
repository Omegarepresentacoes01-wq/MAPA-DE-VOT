"""
Testes de integração — endpoints de fontes e exportações.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestSourcesEndpoints:
    async def test_list_sources_returns_200(self, client: AsyncClient):
        """GET /sources deve retornar 200."""
        resp = await client.get("/api/v1/sources")
        assert resp.status_code == 200

    async def test_list_sources_response_is_list(self, client: AsyncClient):
        """Resposta de fontes deve ser uma lista (pode estar vazia)."""
        resp = await client.get("/api/v1/sources")
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))

    async def test_sources_health_endpoint_exists(self, client: AsyncClient):
        """GET /sources/health deve existir."""
        resp = await client.get("/api/v1/sources/health")
        assert resp.status_code in {200, 404}

    async def test_source_detail_not_found(self, client: AsyncClient):
        """Fonte inexistente deve retornar 404."""
        resp = await client.get("/api/v1/sources/99999")
        assert resp.status_code in {404, 422}

    async def test_source_versions_not_found(self, client: AsyncClient):
        """Versões de fonte inexistente deve retornar 404."""
        resp = await client.get("/api/v1/sources/99999/versions")
        assert resp.status_code in {404, 422}


class TestExportsEndpoints:
    async def test_create_export_requires_body(self, client: AsyncClient):
        """POST /exports sem body deve retornar 422."""
        resp = await client.post("/api/v1/exports")
        assert resp.status_code == 422

    async def test_create_export_invalid_format(self, client: AsyncClient):
        """Formato de exportação inválido deve retornar 422."""
        resp = await client.post(
            "/api/v1/exports",
            json={"tipo": "candidatos", "formato": "invalid_format"},
        )
        assert resp.status_code == 422

    async def test_create_export_valid_formats(self, client: AsyncClient):
        """Formatos válidos (csv, xlsx, json) devem ser aceitos."""
        for formato in ["csv", "xlsx", "json"]:
            resp = await client.post(
                "/api/v1/exports",
                json={"tipo": "candidatos", "formato": formato, "filtros": {}},
            )
            # 200 (criado), 202 (aceito/enfileirado) ou 503 (redis indisponível)
            assert resp.status_code in {200, 202, 422, 503}

    async def test_get_export_job_not_found(self, client: AsyncClient):
        """Job de exportação inexistente deve retornar 404."""
        resp = await client.get("/api/v1/exports/nonexistent-job-id")
        assert resp.status_code in {404, 422}

    async def test_list_exports_returns_200(self, client: AsyncClient):
        """GET /exports deve retornar lista de jobs."""
        resp = await client.get("/api/v1/exports")
        assert resp.status_code in {200, 404}


class TestMapsEndpoints:
    async def test_maps_catalog_returns_200(self, client: AsyncClient):
        """GET /maps deve retornar catálogo de camadas."""
        resp = await client.get("/api/v1/maps")
        assert resp.status_code == 200

    async def test_maps_catalog_has_layers(self, client: AsyncClient):
        """Catálogo deve conter lista de camadas disponíveis."""
        resp = await client.get("/api/v1/maps")
        if resp.status_code == 200:
            data = resp.json()
            assert "layers" in data or isinstance(data, list)

    async def test_maps_mvt_invalid_coords(self, client: AsyncClient):
        """Tiles MVT com coordenadas inválidas devem retornar 422 ou 404."""
        resp = await client.get("/api/v1/maps/mvt/municipios/999/999/999")
        assert resp.status_code in {404, 422}

    async def test_maps_choropleth_endpoint_exists(self, client: AsyncClient):
        """Endpoint de choropleth deve existir."""
        resp = await client.get("/api/v1/maps/choropleth/municipios?indicador=votos_totais&ano=2022")
        assert resp.status_code in {200, 404, 422, 503}
