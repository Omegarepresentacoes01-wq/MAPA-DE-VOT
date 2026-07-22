"""
Base declarativa SQLAlchemy compartilhada entre todos os modelos.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
