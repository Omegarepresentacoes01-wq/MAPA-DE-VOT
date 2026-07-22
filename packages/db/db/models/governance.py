"""
Núcleo de Governança — DataSource, DatasetVersion, RecordLineage.
Garante rastreabilidade completa de toda ingestão.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class DataSource(Base):
    """Fonte de dados oficial cadastrada."""
    __tablename__ = "data_source"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    # ex: API_REST | BULK_CSV | BULK_SHP | PAINEL
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    # ground_truth | proxy
    classificacao: Mapped[str] = mapped_column(String(30), default="ground_truth")
    limitacoes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="source")


class DatasetVersion(Base):
    """Versão de um dataset ingerido — registro de cada carga."""
    __tablename__ = "dataset_version"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_source.id"), nullable=False, index=True)
    nome_dataset: Mapped[str] = mapped_column(String(255), nullable=False)
    ano_referencia: Mapped[Optional[int]] = mapped_column(Integer)
    data_ingestao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_publicacao_fonte: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Integridade do arquivo bruto
    hash_arquivo: Mapped[Optional[str]] = mapped_column(String(128))
    caminho_raw: Mapped[Optional[str]] = mapped_column(Text)  # path no MinIO
    tamanho_bytes: Mapped[Optional[int]] = mapped_column()

    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | running | success | failed | reconciled
    erros: Mapped[Optional[str]] = mapped_column(Text)
    registros_inseridos: Mapped[Optional[int]] = mapped_column(Integer)
    registros_atualizados: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    source: Mapped["DataSource"] = relationship(back_populates="versions")
    lineages: Mapped[list["RecordLineage"]] = relationship(back_populates="dataset_version")


class RecordLineage(Base):
    """Rastreia qual dataset alimentou qual registro em qual tabela."""
    __tablename__ = "record_lineage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_version.id"), nullable=False, index=True)
    tabela_destino: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    registro_id: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset_version: Mapped["DatasetVersion"] = relationship(back_populates="lineages")
