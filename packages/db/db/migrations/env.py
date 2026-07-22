"""
Alembic env.py — configurado para usar os models SQLAlchemy do pacote db.
Suporta migrations online (com banco conectado) e offline (gera SQL).
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importa Base e todos os models para que Alembic os descubra automaticamente
from db.base import Base
import db.models  # noqa: F401 — registra todos os models no metadata

config = context.config

# Lê DATABASE_URL_SYNC do ambiente (fallback para valor do alembic.ini)
database_url = os.environ.get("DATABASE_URL_SYNC") or config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera SQL sem conexão de banco."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """Ignora tabelas que não estão no metadata."""
    if type_ == "table" and reflected and name not in target_metadata.tables:
        return False
    return True

def run_migrations_online() -> None:
    """Executa migrations com conexão de banco."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
