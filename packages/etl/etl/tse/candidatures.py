"""
Pipeline de candidaturas TSE — Etapa 3.

Fonte: dadosabertos.tse.jus.br
Arquivo: consulta_cand_{ano}.zip → consulta_cand_{ano}_{UF}.csv

Etapas:
  1. Download do ZIP
  2. Extração e validação de colunas
  3. Normalização com Polars (hash CPF, datas, strings)
  4. Upsert no banco: election, party, office, territory (lookup), person, candidacy
  5. Registro de DatasetVersion + lineage
  6. Ingestão de bens declarados (bem_candidato)

Uso via CLI:
  python -m etl.tse.candidatures --ano 2022
  python -m etl.tse.candidatures --ano 2022 --uf SP

Ou via Celery:
  from apps.worker.tasks.etl_tse import ingest_candidatures
  ingest_candidatures.delay(ano=2022)
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from uuid import UUID

import polars as pl

from etl.tse.constants import (
    TSE_CANDIDATURES_URL, TSE_ASSETS_URL,
    CAND_COLUMNS, ASSET_COLUMNS,
    TSE_ENCODING, TSE_SEPARATOR,
    CARGO_NIVEL, UFS,
)
from etl.common.download import (
    download_file, extract_zip,
    register_dataset_version, mark_version_done, mark_version_failed,
    RAW_DIR, STAGING_DIR,
)
from etl.common.normalize import (
    hash_cpf, clean_str, clean_str_expr,
    parse_tse_date_expr, parse_tse_money_expr,
    validate_columns, read_tse_csv,
)

logger = logging.getLogger(__name__)

# Colunas obrigatórias para validação
REQUIRED_COLUMNS = [
    "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_CARGO", "DS_CARGO",
    "SQ_CANDIDATO", "NM_CANDIDATO", "NM_URNA_CANDIDATO",
    "NR_PARTIDO", "SG_PARTIDO", "NM_PARTIDO",
    "DS_SIT_TOT_TURNO",
]


# ──────────────────────────────────────────────────────────────────────────────
# 1. Download
# ──────────────────────────────────────────────────────────────────────────────

def download_candidatures(ano: int) -> Path:
    """Baixa o ZIP de candidaturas do TSE para o diretório raw."""
    url = TSE_CANDIDATURES_URL.format(ano=ano)
    dest = RAW_DIR / f"tse" / f"consulta_cand_{ano}.zip"
    return download_file(url, dest)


def download_assets(ano: int) -> Path:
    """Baixa o ZIP de bens declarados."""
    url = TSE_ASSETS_URL.format(ano=ano)
    dest = RAW_DIR / "tse" / f"bem_candidato_{ano}.zip"
    return download_file(url, dest)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Normalização (Polars — sem banco)
# ──────────────────────────────────────────────────────────────────────────────

def normalize_candidatures_df(raw_path: Path) -> pl.DataFrame:
    """
    Lê e normaliza um CSV de candidaturas TSE.
    Retorna DataFrame limpo e tipado, sem CPF em claro.
    """
    df = read_tse_csv(raw_path)

    # Filtra apenas colunas que existem neste arquivo
    cols_available = {k: v for k, v in CAND_COLUMNS.items() if k in df.columns}
    df = df.rename(cols_available).select(list(cols_available.values()))

    validate_columns(df, [v for v in [
        "ano_eleicao", "turno", "uf", "cd_cargo", "ds_cargo",
        "sq_candidato", "nome", "nome_urna", "sigla_partido", "nome_partido", "situacao"
    ] if v in df.columns], raw_path.name)

    # Hash do CPF
    if "cpf_raw" in df.columns:
        df = df.with_columns(
            pl.col("cpf_raw")
            .map_elements(hash_cpf, return_dtype=pl.String)
            .alias("cpf_hash")
        ).drop("cpf_raw")

    # Limpeza de strings
    str_cols = ["nome", "nome_urna", "nome_social", "genero", "escolaridade",
                "raca_cor", "ocupacao", "situacao", "sigla_partido", "nome_partido",
                "ds_cargo", "uf", "nm_municipio"]
    for col in str_cols:
        if col in df.columns:
            df = df.with_columns(clean_str_expr(col))

    # Data de nascimento
    if "nascimento" in df.columns:
        df = df.with_columns(parse_tse_date_expr("nascimento"))

    # Tipos numéricos
    for col in ["ano_eleicao", "turno", "cd_cargo", "numero_partido", "nr_zona"]:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Int32, strict=False))

    # Normaliza situação para uppercase
    if "situacao" in df.columns:
        df = df.with_columns(pl.col("situacao").str.to_uppercase().str.strip_chars())

    logger.info(f"Normalizado: {raw_path.name} → {len(df):,} candidaturas")
    return df


def normalize_assets_df(raw_path: Path) -> pl.DataFrame:
    """Lê e normaliza um CSV de bens declarados."""
    df = read_tse_csv(raw_path)
    cols_available = {k: v for k, v in ASSET_COLUMNS.items() if k in df.columns}
    df = df.rename(cols_available).select(list(cols_available.values()))

    if "valor" in df.columns:
        df = df.with_columns(parse_tse_money_expr("valor"))

    for col in ["tipo", "descricao"]:
        if col in df.columns:
            df = df.with_columns(clean_str_expr(col))

    return df


# ──────────────────────────────────────────────────────────────────────────────
# 3. Upsert no banco
# ──────────────────────────────────────────────────────────────────────────────

async def upsert_election(session, ano: int, turno: int, tipo: str, descricao: str):
    """Upsert de Election — retorna instância."""
    from sqlalchemy import select
    from db.models.political import Election

    stmt = select(Election).where(
        Election.ano == ano,
        Election.turno == turno,
        Election.tipo_eleicao == tipo,
    )
    result = await session.execute(stmt)
    election = result.scalar_one_or_none()
    if not election:
        election = Election(ano=ano, turno=turno, tipo_eleicao=tipo, descricao=descricao)
        session.add(election)
        await session.flush()
    return election


async def upsert_party(session, sigla: str, nome: str, numero: Optional[int]):
    """Upsert de Party."""
    from sqlalchemy import select
    from db.models.political import Party

    stmt = select(Party).where(Party.sigla == sigla, Party.numero == numero)
    result = await session.execute(stmt)
    party = result.scalar_one_or_none()
    if not party:
        party = Party(sigla=sigla, nome=nome, numero=numero)
        session.add(party)
        await session.flush()
    elif party.nome != nome:
        party.nome = nome
        await session.flush()
    return party


async def upsert_office(session, codigo: str, descricao: str, nivel: str):
    """Upsert de Office."""
    from sqlalchemy import select
    from db.models.political import Office

    stmt = select(Office).where(Office.codigo == codigo)
    result = await session.execute(stmt)
    office = result.scalar_one_or_none()
    if not office:
        office = Office(codigo=codigo, descricao=descricao, nivel=nivel)
        session.add(office)
        await session.flush()
    return office


async def upsert_territory(session, uf: str, cd_municipio_tse: Optional[str], nm_municipio: Optional[str]):
    """
    Lookup de Territory por UF + código IBGE estimado.
    O código IBGE definitivo vem do pipeline IBGE (Etapa 5).
    Aqui usamos o código TSE como proxy temporário.
    """
    from sqlalchemy import select
    from db.models.territorial import Territory

    # TSE usa código de 5 dígitos; IBGE usa 7. Usamos código TSE + '00' como placeholder.
    codigo_proxy = f"{cd_municipio_tse}00" if cd_municipio_tse else f"UF_{uf}"

    stmt = select(Territory).where(Territory.codigo_ibge == codigo_proxy)
    result = await session.execute(stmt)
    territory = result.scalar_one_or_none()
    if not territory and nm_municipio:
        territory = Territory(
            tipo="municipio",
            codigo_ibge=codigo_proxy,
            nome=nm_municipio,
            uf=uf,
        )
        session.add(territory)
        await session.flush()
    return territory


async def upsert_person(session, row: dict) -> "Person":  # type: ignore[name-defined]
    """Upsert de Person por cpf_hash. Sem CPF usa nome+nascimento como chave."""
    from sqlalchemy import select
    from db.models.political import Person

    cpf_hash = row.get("cpf_hash")
    person = None

    if cpf_hash:
        stmt = select(Person).where(Person.cpf_hash == cpf_hash)
        result = await session.execute(stmt)
        person = result.scalar_one_or_none()

    if not person:
        person = Person(
            cpf_hash=cpf_hash,
            nome=row.get("nome", ""),
            nome_urna=row.get("nome_urna"),
            nascimento=row.get("nascimento"),
            genero=row.get("genero"),
            raca_cor=row.get("raca_cor"),
            escolaridade=row.get("escolaridade"),
            ocupacao=row.get("ocupacao"),
        )
        session.add(person)
        await session.flush()
    else:
        # Atualiza campos que podem mudar entre eleições
        for field in ["nome_urna", "genero", "raca_cor", "escolaridade", "ocupacao"]:
            val = row.get(field)
            if val and getattr(person, field) != val:
                setattr(person, field, val)
        await session.flush()

    return person


async def upsert_candidacy(
    session,
    person,
    election,
    party,
    office,
    territory,
    row: dict,
    version_id: UUID,
    fonte_url: str,
) -> tuple["Candidacy", bool]:  # type: ignore[name-defined]
    """Upsert de Candidacy por sq_candidato + election_id. Retorna (candidacy, criada)."""
    from sqlalchemy import select
    from db.models.political import Candidacy

    sq = row.get("sq_candidato")
    stmt = select(Candidacy).where(
        Candidacy.tse_sq_candidato == sq,
        Candidacy.election_id == election.id,
    )
    result = await session.execute(stmt)
    candidacy = result.scalar_one_or_none()
    created = False

    if not candidacy:
        candidacy = Candidacy(
            person_id=person.id,
            election_id=election.id,
            party_id=party.id,
            office_id=office.id,
            territory_id=territory.id if territory else None,
            numero_urna=row.get("numero_urna"),
            situacao=row.get("situacao", ""),
            tse_sq_candidato=sq,
            fonte_url=fonte_url,
            dataset_version_id=version_id,
        )
        session.add(candidacy)
        created = True
    else:
        candidacy.situacao = row.get("situacao", candidacy.situacao)
        candidacy.dataset_version_id = version_id

    await session.flush()
    return candidacy, created


# ──────────────────────────────────────────────────────────────────────────────
# 4. Pipeline de bens declarados
# ──────────────────────────────────────────────────────────────────────────────

async def load_assets(session, df_assets: pl.DataFrame, sq_to_candidacy: dict[str, UUID]):
    """Atualiza bens_declarados_total na candidacy a partir do df de bens."""
    from db.models.political import Candidacy
    from sqlalchemy import select
    from decimal import Decimal

    # Agrega total por sq_candidato
    totais = (
        df_assets
        .filter(pl.col("valor").is_not_null())
        .group_by("sq_candidato")
        .agg(pl.col("valor").sum().alias("total"))
    )

    for row in totais.iter_rows(named=True):
        sq = str(row["sq_candidato"])
        candidacy_id = sq_to_candidacy.get(sq)
        if not candidacy_id:
            continue
        stmt = select(Candidacy).where(Candidacy.id == candidacy_id)
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()
        if c:
            c.bens_declarados_total = Decimal(str(row["total"]))
    await session.flush()


# ──────────────────────────────────────────────────────────────────────────────
# 5. Função principal run() — chamada pelo CLI e pelo Celery
# ──────────────────────────────────────────────────────────────────────────────

async def _run_async(ano: int, uf: Optional[str] = None, upload_minio: bool = True):
    """Execução async da ingestão de candidaturas."""
    from db.session import AsyncSessionLocal
    from db.models.governance import DataSource
    from sqlalchemy import select

    logger.info(f"=== Ingestão de candidaturas TSE {ano} {'(' + uf + ')' if uf else '(todas UFs)'} ===")

    # 1. Download
    zip_path = download_candidatures(ano)
    extract_dir = STAGING_DIR / "tse" / f"candidaturas_{ano}"

    # 2. Extração (filtra por UF se especificado)
    pattern = f"_{uf.upper()}." if uf else "consulta_cand"
    csv_files = extract_zip(zip_path, extract_dir, pattern=pattern)

    if not csv_files:
        raise FileNotFoundError(f"Nenhum CSV encontrado no ZIP para UF={uf}")

    # 3. Bens declarados (download paralelo)
    try:
        assets_zip = download_assets(ano)
        assets_dir = STAGING_DIR / "tse" / f"bens_{ano}"
        assets_files = extract_zip(assets_zip, assets_dir, pattern=(f"_{uf.upper()}." if uf else ""))
        df_assets_list = [normalize_assets_df(f) for f in assets_files if f.suffix == ".csv"]
        df_assets = pl.concat(df_assets_list) if df_assets_list else pl.DataFrame()
    except Exception as e:
        logger.warning(f"Bens declarados não carregados: {e}")
        df_assets = pl.DataFrame()

    fonte_url = TSE_CANDIDATURES_URL.format(ano=ano)
    total_inseridos = 0
    total_atualizados = 0

    async with AsyncSessionLocal() as session:
        # Busca source_id do TSE
        stmt = select(DataSource).where(DataSource.nome == "TSE — Portal de Dados Abertos")
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()
        if not source:
            logger.warning("DataSource TSE não encontrado — execute 'make seed-sources' primeiro")
            source_id = None
        else:
            source_id = source.id

        # Registra DatasetVersion
        version = await register_dataset_version(
            session=session,
            source_id=source_id,
            nome_dataset=f"consulta_cand_{ano}",
            ano_referencia=ano,
            local_path=zip_path,
            upload_to_minio=upload_minio,
        )
        await session.commit()

        sq_to_candidacy: dict[str, UUID] = {}

        try:
            for csv_file in csv_files:
                if csv_file.suffix.lower() != ".csv":
                    continue

                logger.info(f"Processando: {csv_file.name}")
                df = normalize_candidatures_df(csv_file)

                # Cache de dimensões por sessão para reduzir queries
                elections_cache: dict[tuple, object] = {}
                parties_cache: dict[tuple, object] = {}
                offices_cache: dict[tuple, object] = {}
                territories_cache: dict[tuple, object] = {}

                BATCH_SIZE = 500
                rows = df.to_dicts()
                for i in range(0, len(rows), BATCH_SIZE):
                    batch = rows[i:i + BATCH_SIZE]

                    for row in batch:
                        # Election
                        e_key = (row.get("ano_eleicao"), row.get("turno"), row.get("nm_tipo_eleicao", "GERAL"))
                        if e_key not in elections_cache:
                            elections_cache[e_key] = await upsert_election(
                                session,
                                ano=int(row.get("ano_eleicao") or ano),
                                turno=int(row.get("turno") or 1),
                                tipo=str(row.get("nm_tipo_eleicao") or "ELEIÇÃO GERAL"),
                                descricao=str(row.get("nm_tipo_eleicao") or f"Eleição {ano}"),
                            )
                        election = elections_cache[e_key]

                        # Party
                        p_key = (row.get("sigla_partido"), row.get("numero_partido"))
                        if p_key not in parties_cache:
                            parties_cache[p_key] = await upsert_party(
                                session,
                                sigla=str(row.get("sigla_partido") or ""),
                                nome=str(row.get("nome_partido") or ""),
                                numero=int(row["numero_partido"]) if row.get("numero_partido") else None,
                            )
                        party = parties_cache[p_key]

                        # Office
                        o_key = (str(row.get("cd_cargo") or ""),)
                        if o_key not in offices_cache:
                            nivel = CARGO_NIVEL.get(str(row.get("cd_cargo") or ""), "municipal")
                            offices_cache[o_key] = await upsert_office(
                                session,
                                codigo=str(row.get("cd_cargo") or ""),
                                descricao=str(row.get("ds_cargo") or ""),
                                nivel=nivel,
                            )
                        office = offices_cache[o_key]

                        # Territory
                        t_key = (row.get("uf"), row.get("cd_municipio_tse"))
                        if t_key not in territories_cache:
                            territories_cache[t_key] = await upsert_territory(
                                session,
                                uf=str(row.get("uf") or ""),
                                cd_municipio_tse=row.get("cd_municipio_tse"),
                                nm_municipio=row.get("nm_municipio"),
                            )
                        territory = territories_cache[t_key]

                        # Person
                        person = await upsert_person(session, row)

                        # Candidacy
                        candidacy, created = await upsert_candidacy(
                            session, person, election, party, office, territory,
                            row, version.id, fonte_url,
                        )

                        sq = row.get("sq_candidato")
                        if sq:
                            sq_to_candidacy[str(sq)] = candidacy.id

                        if created:
                            total_inseridos += 1
                        else:
                            total_atualizados += 1

                    # Commit por batch
                    await session.commit()
                    logger.info(f"  Batch {i // BATCH_SIZE + 1}: {total_inseridos} inseridos / {total_atualizados} atualizados")

            # Bens declarados
            if not df_assets.is_empty() and "sq_candidato" in df_assets.columns:
                logger.info(f"Carregando bens declarados: {len(df_assets):,} registros")
                await load_assets(session, df_assets, sq_to_candidacy)
                await session.commit()

            await mark_version_done(session, version, total_inseridos, total_atualizados)
            await session.commit()

            logger.info(
                f"=== Ingestão concluída: {total_inseridos} inseridos, "
                f"{total_atualizados} atualizados ==="
            )

        except Exception as exc:
            logger.error(f"Erro durante ingestão: {exc}", exc_info=True)
            await mark_version_failed(session, version, str(exc))
            await session.commit()
            raise


def run(ano: int, uf: Optional[str] = None, upload_minio: bool = True):
    """Entry point síncrono — chamado pelo Celery e CLI."""
    asyncio.run(_run_async(ano=ano, uf=uf, upload_minio=upload_minio))


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import typer
    from rich.logging import RichHandler
    import logging as _logging

    _logging.basicConfig(
        level=_logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    app = typer.Typer()

    @app.command()
    def main(
        ano: int = typer.Option(..., help="Ano da eleição (ex: 2022)"),
        uf: Optional[str] = typer.Option(None, help="UF (ex: SP). Omitir para todas."),
        no_minio: bool = typer.Option(False, help="Desabilita upload para MinIO (dev)"),
    ):
        """Pipeline de candidaturas TSE."""
        run(ano=ano, uf=uf, upload_minio=not no_minio)

    app()
