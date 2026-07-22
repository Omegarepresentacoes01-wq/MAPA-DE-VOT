"""
Utilitários de download compartilhados entre os pipelines ETL.
- Download com retry e barra de progresso
- Extração de ZIP
- Registro de DatasetVersion
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

import httpx
from rich.progress import Progress, DownloadColumn, BarColumn, TimeRemainingColumn, TransferSpeedColumn

from etl.common.storage import compute_sha256, upload_raw, BUCKET_RAW

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"

RAW_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Download
# ──────────────────────────────────────────────────────────────────────────────

def download_file(
    url: str,
    dest: Path,
    max_retries: int = 3,
    timeout: int = 300,
) -> Path:
    """
    Faz download de um arquivo com retry e barra de progresso.
    Se o arquivo já existir e tiver tamanho > 0, pula o download.
    """
    if dest.exists() and dest.stat().st_size > 0:
        logger.info(f"Cache local: {dest} (pulando download)")
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Baixando [{attempt}/{max_retries}]: {url}")
            with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))

                with Progress(
                    "[progress.description]{task.description}",
                    BarColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task(dest.name, total=total or None)
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))

            logger.info(f"Download concluído: {dest} ({dest.stat().st_size:,} bytes)")
            return dest

        except Exception as exc:
            logger.warning(f"Tentativa {attempt} falhou: {exc}")
            if dest.exists():
                dest.unlink()
            if attempt == max_retries:
                raise
            time.sleep(5 * attempt)

    raise RuntimeError(f"Falha após {max_retries} tentativas: {url}")


# ──────────────────────────────────────────────────────────────────────────────
# Extração de ZIP
# ──────────────────────────────────────────────────────────────────────────────

def extract_zip(zip_path: Path, dest_dir: Path, pattern: str = "") -> list[Path]:
    """
    Extrai arquivos de um ZIP para dest_dir.
    Se pattern for informado, extrai apenas arquivos que contenham o pattern no nome.
    Retorna lista de arquivos extraídos.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = [
            m for m in zf.namelist()
            if (pattern.lower() in m.lower() if pattern else True)
            and not m.endswith("/")
        ]
        for member in members:
            target = dest_dir / Path(member).name
            with zf.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
            extracted.append(target)
            logger.info(f"  Extraído: {target.name}")

    return extracted


# ──────────────────────────────────────────────────────────────────────────────
# Registro de DatasetVersion no banco
# ──────────────────────────────────────────────────────────────────────────────

async def register_dataset_version(
    session,
    source_id: UUID,
    nome_dataset: str,
    ano_referencia: int,
    local_path: Path,
    upload_to_minio: bool = True,
) -> "DatasetVersion":  # type: ignore[name-defined]
    """
    Registra uma versão de dataset no banco:
    - calcula hash SHA-256 do arquivo
    - faz upload para MinIO (opcional, pode falhar silenciosamente em dev)
    - cria registro DatasetVersion com status 'running'
    """
    from db.models.governance import DatasetVersion

    file_hash = compute_sha256(local_path)
    caminho_raw: Optional[str] = None

    if upload_to_minio:
        try:
            minio_key = f"tse/{ano_referencia}/{local_path.name}"
            caminho_raw = upload_raw(local_path, minio_key)
        except Exception as e:
            logger.warning(f"Upload MinIO falhou (continuando): {e}")

    version = DatasetVersion(
        source_id=source_id,
        nome_dataset=nome_dataset,
        ano_referencia=ano_referencia,
        data_ingestao=datetime.now(timezone.utc),
        hash_arquivo=file_hash,
        caminho_raw=caminho_raw or str(local_path),
        tamanho_bytes=local_path.stat().st_size,
        status="running",
    )
    session.add(version)
    await session.flush()  # gera o ID sem commitar
    return version


async def mark_version_done(
    session,
    version,
    inseridos: int = 0,
    atualizados: int = 0,
) -> None:
    version.status = "success"
    version.registros_inseridos = inseridos
    version.registros_atualizados = atualizados
    await session.flush()


async def mark_version_failed(session, version, erro: str) -> None:
    version.status = "failed"
    version.erros = erro[:2000]
    await session.flush()
