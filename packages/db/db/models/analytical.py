"""
Núcleo Analítico — VoteResult, TurnoutSummary.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class VoteResult(Base):
    """Resultado de votos por candidato e recorte geográfico."""
    __tablename__ = "vote_result"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidacy.id"), nullable=False, index=True)
    election_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("election.id"), nullable=False, index=True)

    # Recortes disponíveis (nullable = dado não granular até esse nível)
    territory_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("territory.id"), index=True)
    polling_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("polling_zone.id"), index=True)
    polling_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("polling_section.id"), index=True)

    votos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    percentual: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "candidacy_id", "territory_id", "polling_zone_id", "polling_section_id",
            name="uq_vote_result_candidacy_granularity",
        ),
    )

    candidacy: Mapped["Candidacy"] = relationship(back_populates="vote_results")  # type: ignore[name-defined]
    election: Mapped["Election"] = relationship(back_populates="vote_results")  # type: ignore[name-defined]
    territory: Mapped[Optional["Territory"]] = relationship()  # type: ignore[name-defined]


class TurnoutSummary(Base):
    """Resumo de comparecimento e abstenção por eleição e território."""
    __tablename__ = "turnout_summary"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("election.id"), nullable=False, index=True)
    territory_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("territory.id"), index=True)
    polling_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("polling_zone.id"), index=True)

    aptos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    comparecimento: Mapped[int] = mapped_column(BigInteger, nullable=False)
    abstencao: Mapped[int] = mapped_column(BigInteger, nullable=False)
    votos_brancos: Mapped[Optional[int]] = mapped_column(BigInteger)
    votos_nulos: Mapped[Optional[int]] = mapped_column(BigInteger)

    fonte_url: Mapped[Optional[str]] = mapped_column(Text)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("dataset_version.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "election_id", "territory_id", "polling_zone_id",
            name="uq_turnout_election_territory_zone",
        ),
    )


# Late imports
from db.models.political import Candidacy, Election  # noqa: E402
from db.models.territorial import Territory, PollingZone, PollingSection  # noqa: E402
from db.models.governance import DatasetVersion  # noqa: E402
