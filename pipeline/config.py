"""Configuração do data lake Medallion (MinIO) — Home Swiss Home."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

# MinIO / S3 (mesmo padrão do docker-compose)
MINIO_ENDPOINT = os.environ.get("MLFLOW_S3_ENDPOINT_URL", "http://127.0.0.1:9000")
AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "minio")
AWS_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY", "minio123")

# Bucket dedicado aos dados do domínio (criado pelo pipeline se não existir)
DATA_BUCKET = os.environ.get("HOME_SWISS_BUCKET", "homesswiss")

# Prefixos por camada (layout estilo Hive / Medallion)
PREFIX_BRONZE = "bronze"
PREFIX_SILVER = "silver"
PREFIX_GOLD = "gold"

# Fontes locais (fora de projeto-ia por padrão: pasta pai FACENS/IA)
_DEFAULT_PARENT = Path(__file__).resolve().parent.parent.parent
GEOMETRIES_CSV = Path(os.environ.get("GEOMETRIES_CSV", str(_DEFAULT_PARENT / "geometries.csv")))
SIMULATIONS_CSV = Path(os.environ.get("SIMULATIONS_CSV", str(_DEFAULT_PARENT / "simulations.csv")))

# PostgreSQL (metadados de pipeline — mesmo host do compose; DB mlflow ou outro)
PG_URI = os.environ.get(
    "SWISS_PG_URI",
    "postgresql://mlflow:mlflow@127.0.0.1:5432/mlflow",
)


def dataset_version() -> str:
    """Versão lógica do dataset (pasta no object storage)."""
    return os.environ.get("DATASET_VERSION", datetime.now(timezone.utc).strftime("%Y-%m-%d"))


def key(layer: str, version: str, filename: str) -> str:
    """Chave S3: layer/version/filename — sem barra inicial."""
    layer = layer.strip("/")
    return f"{layer}/{version}/{filename}"
