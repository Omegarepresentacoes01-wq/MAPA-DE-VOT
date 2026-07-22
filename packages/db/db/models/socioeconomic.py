"""
Núcleo Socioeconômico — snapshots por território e ano de referência.
Fontes: IBGE Censo 2022, SIDRA, CadÚnico, ANEEL, SINISA, CNES.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, BigInteger, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class DemographicSnapshot(Base):
    """Snapshot demográfico por território e ano."""
    __tablename__ = "demographic_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    territory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("territory.id"), nullable=False, index=True)
    ano_referencia: Mapped[int] = mapped_column(Integer, nullable=False)

    populacao_total: Mapped[Optional[int]] = mapped_column(BigInteger)
    proporcao_feminina: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    mediana_idade: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    densidade_demografica: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("territory_id", "ano_referencia", name="uq_demographic_territory_ano"),
    )


class IncomeSnapshot(Base):
    """Snapshot de renda por território e ano."""
    __tablename__ = "income_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    territory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("territory.id"), nullable=False, index=True)
    ano_referencia: Mapped[int] = mapped_column(Integer, nullable=False)

    renda_media_mensal: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    renda_mediana_mensal: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    proporcao_ate_1sm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    proporcao_1a3sm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    proporcao_acima_3sm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    gini: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))

    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("territory_id", "ano_referencia", name="uq_income_territory_ano"),
    )


class SocialProgramSnapshot(Base):
    """Snapshot de programas sociais (CadÚnico, Bolsa Família) por território e ano."""
    __tablename__ = "social_program_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    territory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("territory.id"), nullable=False, index=True)
    ano_referencia: Mapped[int] = mapped_column(Integer, nullable=False)
    mes_referencia: Mapped[Optional[int]] = mapped_column(Integer)

    familias_cadunico: Mapped[Optional[int]] = mapped_column(BigInteger)
    beneficiarios_bolsa_familia: Mapped[Optional[int]] = mapped_column(BigInteger)
    valor_pago_bolsa_familia: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2))

    # NOTA: dado proxy — não representa população total
    e_ground_truth: Mapped[bool] = mapped_column(default=False)
    limitacao_nota: Mapped[Optional[str]] = mapped_column(Text)

    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("territory_id", "ano_referencia", "mes_referencia", name="uq_social_territory_ano_mes"),
    )


from db.models.governance import DatasetVersion  # noqa: E402
