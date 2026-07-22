"""
Núcleo Político — Person, Party, Election, Office, Candidacy.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Person(Base):
    """Pessoa física — candidato ou referência eleitoral."""
    __tablename__ = "person"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # CPF nunca em claro — apenas hash para deduplicação interna
    cpf_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome_urna: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    nascimento: Mapped[Optional[date]] = mapped_column(Date)
    genero: Mapped[Optional[str]] = mapped_column(String(50))
    raca_cor: Mapped[Optional[str]] = mapped_column(String(50))
    escolaridade: Mapped[Optional[str]] = mapped_column(String(100))
    ocupacao: Mapped[Optional[str]] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidacies: Mapped[List["Candidacy"]] = relationship(back_populates="person")


class Party(Base):
    """Partido político."""
    __tablename__ = "party"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sigla: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    numero: Mapped[Optional[int]] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("sigla", "numero", name="uq_party_sigla_numero"),
    )

    candidacies: Mapped[List["Candidacy"]] = relationship(back_populates="party")


class Election(Base):
    """Eleição — instância de um pleito."""
    __tablename__ = "election"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    turno: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_eleicao: Mapped[str] = mapped_column(String(100), nullable=False)  # ex: ELEIÇÃO GERAL
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ano", "turno", "tipo_eleicao", name="uq_election_ano_turno_tipo"),
    )

    candidacies: Mapped[List["Candidacy"]] = relationship(back_populates="election")
    vote_results: Mapped[List["VoteResult"]] = relationship(back_populates="election")  # type: ignore[name-defined]


class Office(Base):
    """Cargo disputado."""
    __tablename__ = "office"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    descricao: Mapped[str] = mapped_column(String(100), nullable=False)
    nivel: Mapped[str] = mapped_column(String(50))  # federal | estadual | municipal
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidacies: Mapped[List["Candidacy"]] = relationship(back_populates="office")


class Candidacy(Base):
    """Candidatura de uma pessoa em uma eleição para um cargo."""
    __tablename__ = "candidacy"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"), nullable=False, index=True)
    election_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("election.id"), nullable=False, index=True)
    party_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("party.id"), nullable=False, index=True)
    office_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("office.id"), nullable=False, index=True)
    territory_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("territory.id"), index=True)

    numero_urna: Mapped[Optional[str]] = mapped_column(String(20))
    situacao: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # ex: ELEITO, NÃO ELEITO, CASSADO, RENÚNCIA
    situacao_detalhada: Mapped[Optional[str]] = mapped_column(Text)
    votos_totais: Mapped[Optional[int]] = mapped_column(BigInteger)
    percentual_votos: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    bens_declarados_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2))

    # Código original do TSE para idempotência
    tse_sq_candidato: Mapped[Optional[str]] = mapped_column(String(50), index=True)

    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    ingestao_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tse_sq_candidato", "election_id", name="uq_candidacy_tse_election"),
    )

    person: Mapped["Person"] = relationship(back_populates="candidacies")
    election: Mapped["Election"] = relationship(back_populates="candidacies")
    party: Mapped["Party"] = relationship(back_populates="candidacies")
    office: Mapped["Office"] = relationship(back_populates="candidacies")
    territory: Mapped[Optional["Territory"]] = relationship()  # type: ignore[name-defined]
    vote_results: Mapped[List["VoteResult"]] = relationship(back_populates="candidacy")  # type: ignore[name-defined]
    revenues: Mapped[List["CampaignRevenue"]] = relationship(back_populates="candidacy")  # type: ignore[name-defined]
    expenses: Mapped[List["CampaignExpense"]] = relationship(back_populates="candidacy")  # type: ignore[name-defined]


# Import late to resolve forward references
from db.models.territorial import Territory  # noqa: E402
from db.models.analytical import VoteResult  # noqa: E402
from db.models.financial import CampaignRevenue, CampaignExpense  # noqa: E402
from db.models.governance import DatasetVersion  # noqa: E402
