"""
Helpers de configuração do MLflow para o Sprint 4.

Centraliza:
- URI de tracking (default: http://localhost:5000 — mesmo do docker-compose).
- Endpoint S3 do MinIO (artefatos vão para s3://mlflow/...).
- Nome canônico do experimento ("home_swiss_home").
- Função `build_model_factories()` com a matriz de modelos suportados.

Mantém o `demo.py` antigo intacto (ele continua funcional como hello-world).
"""
from __future__ import annotations

import os
from typing import Callable

import mlflow

DEFAULT_EXPERIMENT = "home_swiss_home"
DEFAULT_TRACKING_URI = "http://localhost:5000"
DEFAULT_S3_ENDPOINT = "http://127.0.0.1:9000"
DEFAULT_AWS_KEY = "minio"
DEFAULT_AWS_SECRET = "minio123"
DEFAULT_ARTIFACT_BUCKET = "mlflow"


def _ensure_experiment_active(experiment: str) -> None:
    """Restaura o experimento se estiver no estado 'deleted' (soft delete da UI).

    O MLflow não permite ``set_experiment`` em um experimento deletado e o nome
    fica reservado até ser restaurado ou removido permanentemente. Esta função
    cobre o caso comum de alguém ter clicado em "Delete" na UI por engano.
    """
    from mlflow.tracking import MlflowClient

    client = MlflowClient()
    info = client.get_experiment_by_name(experiment)
    if info is None:
        return
    if getattr(info, "lifecycle_stage", "active") == "deleted":
        client.restore_experiment(info.experiment_id)


def configure_mlflow(experiment: str = DEFAULT_EXPERIMENT) -> str:
    """Garante variáveis MLflow + MinIO antes de abrir uma run.

    Retorna o nome do experimento configurado para conveniência de log.
    """
    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", DEFAULT_S3_ENDPOINT)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", DEFAULT_AWS_KEY)
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", DEFAULT_AWS_SECRET)

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
    mlflow.set_tracking_uri(tracking_uri)
    _ensure_experiment_active(experiment)
    mlflow.set_experiment(experiment)
    return experiment


def ensure_mlflow_bucket(bucket: str = DEFAULT_ARTIFACT_BUCKET) -> None:
    """Cria o bucket de artefatos do MLflow no MinIO se ainda não existir.

    O servidor MLflow já costuma criá-lo na primeira run, mas garantir aqui
    evita falhas silenciosas em ambientes onde o usuário ainda não rodou
    nada antes do treino.
    """
    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get("MLFLOW_S3_ENDPOINT_URL", DEFAULT_S3_ENDPOINT),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", DEFAULT_AWS_KEY),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", DEFAULT_AWS_SECRET),
    )
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


ModelFactory = Callable[[], object]


def build_model_factories() -> dict[str, ModelFactory]:
    """Mapa ``nome_curto -> factory`` para os modelos do Sprint 4.

    Cada factory retorna um `Pipeline` sklearn com imputação + (opcional)
    padronização. Justificativas em `docs/ML_TREINO.md`.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    def linear() -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ]
        )

    def ridge() -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0, random_state=42)),
            ]
        )

    def knn() -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", KNeighborsRegressor(n_neighbors=10, weights="distance")),
            ]
        )

    def rf() -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        max_depth=None,
                        min_samples_leaf=2,
                        n_jobs=-1,
                        random_state=42,
                    ),
                ),
            ]
        )

    factories: dict[str, ModelFactory] = {
        "linear": linear,
        "ridge": ridge,
        "knn": knn,
        "rf": rf,
    }

    try:
        from xgboost import XGBRegressor

        def xgb() -> Pipeline:
            return Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        XGBRegressor(
                            n_estimators=400,
                            max_depth=6,
                            learning_rate=0.05,
                            subsample=0.9,
                            colsample_bytree=0.9,
                            random_state=42,
                            n_jobs=-1,
                            tree_method="hist",
                        ),
                    ),
                ]
            )

        factories["xgb"] = xgb
    except ImportError:
        pass

    return factories
