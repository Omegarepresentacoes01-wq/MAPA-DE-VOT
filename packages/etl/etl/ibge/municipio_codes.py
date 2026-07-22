"""
Utilitário de mapeamento entre códigos TSE (5 dígitos) e IBGE (7 dígitos).

O TSE usa um código municipal próprio de 5 dígitos que NÃO é o mesmo
que o código IBGE de 7 dígitos.

Estratégia de resolução (em ordem de prioridade):
  1. Tabela de correspondência da API de localidades IBGE (nome + UF → IBGE 7d)
  2. Cache local em memória para evitar chamadas repetidas
  3. Atualiza Territory.codigo_ibge após o pipeline IBGE carregar os municípios reais
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from etl.ibge.constants import IBGE_LOCALIDADES_URL

logger = logging.getLogger(__name__)

# Cache global: (nome_normalizado, uf) → codigo_ibge_7d
_MUNICIPIO_CACHE: dict[tuple[str, str], str] = {}
_CACHE_LOADED = False


def _normalize_nome(nome: str) -> str:
    """Normaliza nome para matching: uppercase, sem acentos."""
    import unicodedata
    nome = nome.upper().strip()
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def load_municipio_cache() -> dict[tuple[str, str], str]:
    """
    Carrega a tabela de municípios da API IBGE e constrói o cache
    (nome_normalizado, uf) → codigo_ibge_7d.
    Chamada única — resultado fica em _MUNICIPIO_CACHE.
    """
    global _MUNICIPIO_CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return _MUNICIPIO_CACHE

    logger.info("Carregando tabela de municípios IBGE (API localidades)...")
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(IBGE_LOCALIDADES_URL)
            resp.raise_for_status()
            data = resp.json()

        for mun in data:
            codigo = str(mun["id"])
            nome = mun["nome"]
            uf = mun["microrregiao"]["mesorregiao"]["UF"]["sigla"]
            key = (_normalize_nome(nome), uf.upper())
            _MUNICIPIO_CACHE[key] = codigo

        _CACHE_LOADED = True
        logger.info(f"Cache carregado: {len(_MUNICIPIO_CACHE):,} municípios")
    except Exception as e:
        logger.warning(f"Falha ao carregar cache IBGE: {e}. Usando placeholder codes.")

    return _MUNICIPIO_CACHE


def resolve_ibge_code(nome_municipio: str, uf: str) -> Optional[str]:
    """
    Resolve código IBGE 7 dígitos a partir do nome e UF do município.
    Retorna None se não encontrar.
    """
    cache = load_municipio_cache()
    key = (_normalize_nome(nome_municipio), uf.upper())

    # Busca exata
    if key in cache:
        return cache[key]

    # Busca parcial (nome do TSE pode ter abreviações)
    nome_norm = key[0]
    for (cached_nome, cached_uf), codigo in cache.items():
        if cached_uf == uf.upper() and (
            cached_nome.startswith(nome_norm[:10]) or nome_norm.startswith(cached_nome[:10])
        ):
            return codigo

    return None


def get_ibge_municipios_list() -> list[dict]:
    """Retorna lista completa de municípios da API IBGE com id, nome e UF."""
    logger.info("Buscando lista de municípios via API IBGE...")
    with httpx.Client(timeout=60) as client:
        resp = client.get(IBGE_LOCALIDADES_URL)
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "codigo_ibge": str(m["id"]),
            "nome": m["nome"],
            "uf": m["microrregiao"]["mesorregiao"]["UF"]["sigla"],
        }
        for m in data
    ]
