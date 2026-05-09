"""
Carga do dataset Gold para treino — Sprint 4.

Resolve `apartment_kpis.parquet` em três níveis (nessa ordem):

1. Variável de ambiente `GOLD_PARQUET` apontando para um arquivo local.
2. Caminhos locais conhecidos (raiz do repo, data/gold/, gold/<versão>/).
3. Download direto do MinIO em `gold/<DATASET_VERSION>/apartment_kpis.parquet`
   usando as credenciais já definidas em `pipeline/config.py`.

Em todos os casos, devolve `(X_train, X_test, y_train, y_test, feature_names)`
prontos para treino, usando os helpers de `pipeline/ml_targets.py` para
evitar vazamento de features.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
from sklearn.model_selection import train_test_split

from pipeline.config import (
    DATA_BUCKET,
    PREFIX_GOLD,
    dataset_version,
    key,
)
from pipeline.ml_targets import (
    add_ml_targets,
    feature_columns_for_env_quality,
    feature_columns_for_light_comfort,
)
from pipeline.s3_utils import client as s3_client

TargetName = Literal["light_comfort", "env_quality"]

_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class GoldDataset:
    """Container imutável com tudo que o `train.py` precisa."""

    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    feature_names: list[str]
    target_name: str
    source: str
    n_rows_total: int
    dataset_version: str


def _local_candidates(version: str) -> list[Path]:
    return [
        _REPO_ROOT / "apartment_kpis.parquet",
        _REPO_ROOT / "data" / "gold" / "apartment_kpis.parquet",
        _REPO_ROOT / "gold" / version / "apartment_kpis.parquet",
    ]


def _download_from_minio(version: str) -> Path:
    """Baixa gold/<versão>/apartment_kpis.parquet do MinIO para um tmp e retorna o path."""
    s3_key = key(PREFIX_GOLD, version, "apartment_kpis.parquet")
    c = s3_client()
    obj = c.get_object(Bucket=DATA_BUCKET, Key=s3_key)
    tmp = Path(tempfile.mkdtemp(prefix="gold_dl_")) / "apartment_kpis.parquet"
    tmp.write_bytes(obj["Body"].read())
    return tmp


def resolve_gold_parquet(version: str | None = None) -> tuple[Path, str]:
    """Retorna `(caminho, descrição da fonte)` do Parquet Gold.

    Estratégia de busca:
    - `GOLD_PARQUET` (env): caminho explícito (erro se inválido).
    - Caminhos locais conhecidos.
    - Download via MinIO (S3) usando `DATASET_VERSION` (default: data UTC).
    """
    version = version or dataset_version()

    env = os.environ.get("GOLD_PARQUET")
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            raise FileNotFoundError(
                f"GOLD_PARQUET aponta para arquivo inexistente: {p}"
            )
        return p, f"env:GOLD_PARQUET={p}"

    for candidate in _local_candidates(version):
        if candidate.is_file():
            return candidate, f"local:{candidate}"

    try:
        downloaded = _download_from_minio(version)
        return downloaded, f"minio:{DATA_BUCKET}/gold/{version}/apartment_kpis.parquet"
    except Exception as exc:
        msg = (
            "Não foi possível obter apartment_kpis.parquet.\n"
            "  1) Defina GOLD_PARQUET com o caminho do arquivo, ou\n"
            "  2) Coloque o arquivo em projeto-ia/ ou data/gold/, ou\n"
            "  3) Suba o MinIO e rode `py -3.12 -m pipeline.run_pipeline`.\n"
            f"Versão tentada: {version}. Erro MinIO: {exc!r}"
        )
        raise FileNotFoundError(msg) from exc


def _select_xy(df: pd.DataFrame, target: TargetName) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    if target == "light_comfort":
        feature_names = feature_columns_for_light_comfort(df)
        y = df["target_light_comfort"]
    elif target == "env_quality":
        feature_names = feature_columns_for_env_quality(df)
        y = df["target_env_quality"]
    else:
        raise ValueError(
            f"target inválido: {target!r} (use 'light_comfort' ou 'env_quality')"
        )

    if not feature_names:
        raise ValueError(
            "Nenhuma feature numérica disponível na Gold para este alvo. "
            "Confira se o pipeline Silver/Gold rodou com colunas de domínio."
        )
    X = df[feature_names].copy()
    return X, y, feature_names


def load_gold_dataset(
    target: TargetName,
    test_size: float = 0.2,
    random_state: int = 42,
    version: str | None = None,
) -> GoldDataset:
    """Lê a Gold, monta X/y pelos helpers anti-vazamento e faz o split."""
    parquet_path, source = resolve_gold_parquet(version=version)
    df = pd.read_parquet(parquet_path, engine="pyarrow")
    df = add_ml_targets(df)

    X, y, feature_names = _select_xy(df, target)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=True
    )

    return GoldDataset(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        feature_names=feature_names,
        target_name=target,
        source=source,
        n_rows_total=len(df),
        dataset_version=version or dataset_version(),
    )
