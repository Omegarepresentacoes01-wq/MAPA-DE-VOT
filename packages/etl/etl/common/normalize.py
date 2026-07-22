"""
Utilitários de normalização e validação de dados TSE/IBGE.
- Hash de CPF
- Limpeza de strings
- Conversão de datas TSE (DD/MM/YYYY)
- Validação de colunas obrigatórias
- Conversão de valores monetários TSE (vírgula como decimal)
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import date
from typing import Optional

import polars as pl

logger = logging.getLogger(__name__)

# Salt do CPF vindo do ambiente — NUNCA deixar padrão em produção
_CPF_SALT = os.environ.get("CPF_HASH_SALT", "dev_salt_change_in_production_immediately")


# ──────────────────────────────────────────────────────────────────────────────
# Hash de CPF (LGPD compliance)
# ──────────────────────────────────────────────────────────────────────────────

def hash_cpf(cpf_raw: Optional[str]) -> Optional[str]:
    """
    Retorna SHA-256(salt + CPF_digits_only).
    CPF em claro NUNCA é persistido no banco.
    Retorna None se CPF for vazio, nulo ou '########'.
    """
    if not cpf_raw:
        return None
    digits = re.sub(r"\D", "", str(cpf_raw))
    if not digits or digits == "00000000000" or len(digits) not in (11,):
        return None
    payload = f"{_CPF_SALT}:{digits}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# Limpeza de strings TSE
# ──────────────────────────────────────────────────────────────────────────────

def clean_str(value: Optional[str]) -> Optional[str]:
    """Remove espaços extras e normaliza nulos do TSE ('#NULO', '#NE', '-1')."""
    if value is None:
        return None
    v = str(value).strip()
    if v in ("#NULO#", "#NULO", "#NE#", "#NE", "-1", "", "N/A"):
        return None
    return v


def clean_str_expr(col: str) -> pl.Expr:
    """Expressão Polars equivalente a clean_str para uso em select/with_columns."""
    return (
        pl.col(col)
        .str.strip_chars()
        .str.replace_many(["#NULO#", "#NULO", "#NE#", "#NE", "-1", "N/A"], "")
        .replace("", None)
    )


# ──────────────────────────────────────────────────────────────────────────────
# Conversão de datas TSE (DD/MM/YYYY)
# ──────────────────────────────────────────────────────────────────────────────

def parse_tse_date(value: Optional[str]) -> Optional[date]:
    """Converte string DD/MM/YYYY para date. Retorna None se inválido."""
    if not value:
        return None
    v = str(value).strip()
    try:
        day, month, year = v.split("/")
        return date(int(year), int(month), int(day))
    except Exception:
        return None


def parse_tse_date_expr(col: str) -> pl.Expr:
    """Expressão Polars para converter coluna de data TSE."""
    return pl.col(col).str.strptime(pl.Date, "%d/%m/%Y", strict=False)


# ──────────────────────────────────────────────────────────────────────────────
# Conversão de valores monetários TSE (vírgula como decimal)
# ──────────────────────────────────────────────────────────────────────────────

def parse_tse_money_expr(col: str) -> pl.Expr:
    """
    TSE usa '1.234.567,89' como formato monetário.
    Converte para Float64 removendo pontos e substituindo vírgula por ponto.
    """
    return (
        pl.col(col)
        .str.strip_chars()
        .str.replace_all(r"\.", "")
        .str.replace(",", ".")
        .cast(pl.Float64, strict=False)
    )


# ──────────────────────────────────────────────────────────────────────────────
# Validação de colunas
# ──────────────────────────────────────────────────────────────────────────────

def validate_columns(df: pl.DataFrame, required: list[str], dataset: str) -> None:
    """Levanta ValueError se alguma coluna obrigatória estiver ausente."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{dataset}] Colunas obrigatórias ausentes: {missing}. "
            f"Colunas encontradas: {df.columns[:20]}"
        )
    logger.info(f"[{dataset}] Colunas validadas OK ({len(df.columns)} colunas, {len(df):,} linhas)")


# ──────────────────────────────────────────────────────────────────────────────
# Leitura de CSV TSE com Polars
# ──────────────────────────────────────────────────────────────────────────────

def read_tse_csv(path, separator: str = ";", encoding: str = "latin-1") -> pl.DataFrame:
    """
    Lê um CSV do TSE com Polars.
    Todos os campos são lidos como String inicialmente (TSE tem tipos inconsistentes).
    """
    from pathlib import Path as _Path
    path = _Path(path)

    df = pl.read_csv(
        path,
        separator=separator,
        encoding=encoding,
        infer_schema_length=0,       # tudo como String
        ignore_errors=True,
        truncate_ragged_lines=True,
        quote_char='"',
        null_values=["#NULO#", "#NULO", "#NE#", "#NE", ""],
    )
    logger.info(f"Lido: {path.name} → {len(df):,} linhas, {len(df.columns)} colunas")
    return df
