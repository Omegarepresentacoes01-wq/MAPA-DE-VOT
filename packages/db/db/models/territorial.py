"""
Núcleo Territorial — Territory, PollingZone, PollingPlace, PollingSection, CensusSector.
Geometrias armazenadas em WGS84 (SRID 4326) via GeoAlchemy2.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Territory(Base):
    """Território administrativo — país, UF ou município."""
    __tablename__ = "territory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)  # pais | uf | municipio
    codigo_ibge: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    uf: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    # Geometria MultiPolygon em WGS84
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
    )
    populacao: Mapped[Optional[int]] = mapped_column(BigInteger)
    eleitorado: Mapped[Optional[int]] = mapped_column(BigInteger)
    area_km2: Mapped[Optional[float]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    polling_zones: Mapped[List["PollingZone"]] = relationship(back_populates="territory")
    census_sectors: Mapped[List["CensusSector"]] = relationship(back_populates="territory")


class PollingZone(Base):
    """Zona eleitoral (TSE)."""
    __tablename__ = "polling_zone"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    territory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("territory.id"), nullable=False, index=True)
    numero_zona: Mapped[int] = mapped_column(Integer, nullable=False)
    nome_municipio: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("territory_id", "numero_zona", name="uq_zone_territory_numero"),
    )

    territory: Mapped["Territory"] = relationship(back_populates="polling_zones")
    polling_places: Mapped[List["PollingPlace"]] = relationship(back_populates="polling_zone")


class PollingPlace(Base):
    """Local de votação."""
    __tablename__ = "polling_place"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    polling_zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("polling_zone.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    endereco: Mapped[Optional[str]] = mapped_column(Text)
    # Ponto georreferenciado para cruzamento com setor censitário
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    polling_zone: Mapped["PollingZone"] = relationship(back_populates="polling_places")
    polling_sections: Mapped[List["PollingSection"]] = relationship(back_populates="polling_place")


class PollingSection(Base):
    """Seção eleitoral."""
    __tablename__ = "polling_section"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    polling_place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("polling_place.id"), nullable=False, index=True)
    numero_secao: Mapped[int] = mapped_column(Integer, nullable=False)
    eleitorado_aptos: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("polling_place_id", "numero_secao", name="uq_section_place_numero"),
    )

    polling_place: Mapped["PollingPlace"] = relationship(back_populates="polling_sections")


class CensusSector(Base):
    """Setor censitário IBGE (Censo 2022)."""
    __tablename__ = "census_sector"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    territory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("territory.id"), nullable=False, index=True)
    codigo_setor: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(50))  # URBANO | RURAL | etc
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
    )
    populacao: Mapped[Optional[int]] = mapped_column(Integer)
    domicilios: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    territory: Mapped["Territory"] = relationship(back_populates="census_sectors")
