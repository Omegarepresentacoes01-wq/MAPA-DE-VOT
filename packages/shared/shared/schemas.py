"""
Schemas Pydantic — contratos internos da API.
Toda resposta da API inclui SourceMeta para rastreabilidade.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ─────────────────────────────────────────────
# Metadados de fonte (transparência obrigatória)
# ─────────────────────────────────────────────

class SourceMeta(BaseModel):
    """Bloco de transparência exibido em toda tela analítica."""
    fonte: str
    url: Optional[str] = None
    data_atualizacao: Optional[date] = None
    cobertura_temporal: Optional[str] = None
    cobertura_geografica: Optional[str] = None
    limitacoes: Optional[str] = None
    e_proxy: bool = False


# ─────────────────────────────────────────────
# Paginação genérica
# ─────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Busca global
# ─────────────────────────────────────────────

class SearchResult(BaseModel):
    id: str
    tipo: str          # candidato | municipio | partido | eleicao
    titulo: str
    subtitulo: Optional[str] = None
    uf: Optional[str] = None
    partido_sigla: Optional[str] = None
    situacao: Optional[str] = None
    score: Optional[float] = None
    meta: Optional[SourceMeta] = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]
    tempo_ms: Optional[int] = None
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Candidato
# ─────────────────────────────────────────────

class CandidateOut(BaseModel):
    candidacy_id: str
    person_id: str
    nome: str
    nome_urna: Optional[str] = None
    nascimento: Optional[str] = None
    genero: Optional[str] = None
    raca_cor: Optional[str] = None
    escolaridade: Optional[str] = None
    ocupacao: Optional[str] = None
    partido_sigla: Optional[str] = None
    partido_nome: Optional[str] = None
    cargo_codigo: Optional[str] = None
    cargo_descricao: Optional[str] = None
    cargo_nivel: Optional[str] = None
    territorio_nome: Optional[str] = None
    territorio_codigo_ibge: Optional[str] = None
    territorio_uf: Optional[str] = None
    situacao: Optional[str] = None
    numero_urna: Optional[str] = None
    bens_declarados: Optional[float] = None
    votos_totais: Optional[int] = None
    meta: Optional[SourceMeta] = None


class FinanceItemOut(BaseModel):
    categoria_ou_origem: str
    quantidade: int
    total: float


class CandidacyDetailOut(BaseModel):
    """Ficha 360 completa do candidato."""
    candidatura: CandidateOut
    historico_eleitoral: List[Dict[str, Any]] = Field(default_factory=list)
    financas: Dict[str, Any] = Field(default_factory=dict)
    votos_por_municipio: List[Dict[str, Any]] = Field(default_factory=list)
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Território
# ─────────────────────────────────────────────

class TerritoryOut(BaseModel):
    id: str
    tipo: str           # municipio | uf | pais
    codigo_ibge: str
    nome: str
    uf: str
    populacao: Optional[int] = None
    eleitorado: Optional[int] = None
    area_km2: Optional[float] = None
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Eleição
# ─────────────────────────────────────────────

class ElectionOut(BaseModel):
    id: str
    ano: int
    turno: int
    tipo: str
    descricao: Optional[str] = None
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Resultado de votos
# ─────────────────────────────────────────────

class VoteResultOut(BaseModel):
    candidacy_id: str
    territory_codigo_ibge: str
    territory_nome: str
    votos: int
    percentual: Optional[float] = None
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Finanças
# ─────────────────────────────────────────────

class RevenueOut(BaseModel):
    id: str
    data: Optional[date] = None
    origem: str
    descricao: Optional[str] = None
    valor: float
    nome_doador: Optional[str] = None
    meta: Optional[SourceMeta] = None


class ExpenseOut(BaseModel):
    id: str
    data: Optional[date] = None
    categoria: str
    descricao: Optional[str] = None
    valor: float
    nome_fornecedor: Optional[str] = None
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Comparação entre eleições
# ─────────────────────────────────────────────

class ComparisonRow(BaseModel):
    territory_nome: str
    territory_codigo_ibge: str
    votos_a: Optional[int] = None
    votos_b: Optional[int] = None
    variacao_absoluta: Optional[int] = None
    variacao_percentual: Optional[float] = None


class ComparisonOut(BaseModel):
    election_a: ElectionOut
    election_b: ElectionOut
    rows: List[ComparisonRow]
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Data Sources
# ─────────────────────────────────────────────

class DataSourceOut(BaseModel):
    id: str
    nome: str
    url: Optional[str] = None
    tipo: Optional[str] = None
    descricao: Optional[str] = None
    classificacao: Optional[str] = None
    limitacoes: Optional[str] = None


class DatasetVersionOut(BaseModel):
    id: str
    source_id: str
    nome_dataset: str
    ano_referencia: Optional[int] = None
    data_ingestao: Optional[datetime] = None
    status: str
    registros_inseridos: Optional[int] = None
    registros_atualizados: Optional[int] = None
    tamanho_bytes: Optional[int] = None


# ─────────────────────────────────────────────
# Maps / Tile metadata
# ─────────────────────────────────────────────

class TileLayerOut(BaseModel):
    id: str
    nome: str
    tile_url: str
    tipo: str           # mvt | geojson
    descricao: Optional[str] = None
    meta: Optional[SourceMeta] = None


# ─────────────────────────────────────────────
# Export job
# ─────────────────────────────────────────────

class ExportJobOut(BaseModel):
    job_id: str
    status: str         # pending | running | done | failed
    formato: str        # csv | xlsx | json
    url_download: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
