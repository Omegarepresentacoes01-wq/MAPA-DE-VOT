"""
Núcleo Financeiro — CampaignRevenue, CampaignExpense.
Fonte: TSE DivulgaCandContas.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class CampaignRevenue(Base):
    """Receita eleitoral declarada ao TSE."""
    __tablename__ = "campaign_revenue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidacy.id"), nullable=False, index=True)

    data: Mapped[Optional[date]] = mapped_column(Date)
    origem: Mapped[str] = mapped_column(String(100), nullable=False)
    # ex: PARTIDO POLÍTICO | PESSOA FÍSICA | PESSOA JURÍDICA | FUNDO ESPECIAL
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)

    # Doador
    cnpj_cpf_doador: Mapped[Optional[str]] = mapped_column(String(20))
    nome_doador: Mapped[Optional[str]] = mapped_column(String(255))

    # Rastreabilidade
    tse_seq_receita: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidacy: Mapped["Candidacy"] = relationship(back_populates="revenues")  # type: ignore[name-defined]


class CampaignExpense(Base):
    """Despesa eleitoral declarada ao TSE."""
    __tablename__ = "campaign_expense"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidacy.id"), nullable=False, index=True)

    data: Mapped[Optional[date]] = mapped_column(Date)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    # ex: MATERIAL IMPRESSO | COMBUSTÍVEL | PESSOAL | SERVIÇOS
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)

    # Fornecedor
    cnpj_fornecedor: Mapped[Optional[str]] = mapped_column(String(20))
    nome_fornecedor: Mapped[Optional[str]] = mapped_column(String(255))

    tse_seq_despesa: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidacy: Mapped["Candidacy"] = relationship(back_populates="expenses")  # type: ignore[name-defined]


from db.models.political import Candidacy  # noqa: E402
from db.models.governance import DatasetVersion  # noqa: E402
