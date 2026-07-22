"""
Utilitários de storage — MinIO/S3.
Usado por todos os pipelines para guardar arquivos brutos.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import boto3
from botocore.client import Config

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "changeme_minio_secret")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
BUCKET_RAW = os.environ.get("MINIO_BUCKET_RAW", "raw-data")
BUCKET_EXPORTS = os.environ.get("MINIO_BUCKET_EXPORTS", "exports")


def get_s3_client():
    """Retorna cliente boto3 configurado para MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if MINIO_SECURE else 'http'}://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_buckets() -> None:
    """Cria buckets se não existirem."""
    client = get_s3_client()
    for bucket in [BUCKET_RAW, BUCKET_EXPORTS]:
        try:
            client.head_bucket(Bucket=bucket)
        except Exception:
            client.create_bucket(Bucket=bucket)


def upload_raw(local_path: Path, key: str, bucket: str = BUCKET_RAW) -> str:
    """
    Faz upload de arquivo bruto para MinIO.
    Retorna o caminho (bucket/key) para registrar no DatasetVersion.
    """
    client = get_s3_client()
    client.upload_file(str(local_path), bucket, key)
    return f"{bucket}/{key}"


def compute_sha256(path: Path) -> str:
    """Calcula SHA-256 de um arquivo local."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
