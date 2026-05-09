"""
Script de treinamento — Sprint 4 (Home Swiss Home).

Cada execução:
1. Carrega o Parquet Gold (MinIO ou local) — `ml.data.load_gold_dataset`.
2. Monta `Pipeline` (imputer + scaler + estimador) — `ml.registry`.
3. Treina, avalia e registra **uma run** no MLflow com:
   - parâmetros (modelo, alvo, versão de dataset, hiperparâmetros, n_features…),
   - métricas (MAE, RMSE, R², MAPE),
   - tags (`target`, `model`, `dataset_version`, `source`),
   - artefatos (`feature_list.txt`, `predictions_sample.csv`),
   - o próprio modelo (sklearn / xgboost) registrado em ``s3://mlflow/...``.

Uso típico:

    py -3.12 -m ml.train --target light_comfort --model xgb
    py -3.12 -m ml.train --target env_quality   --model rf

Para registrar no Model Registry:

    py -3.12 -m ml.train --target env_quality --model xgb --register-as home_swiss_env_quality
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    import mlflow.xgboost as _mlflow_xgb

    _HAS_MLFLOW_XGB = True
except ImportError:
    _HAS_MLFLOW_XGB = False

from .data import GoldDataset, TargetName, load_gold_dataset
from .registry import (
    DEFAULT_EXPERIMENT,
    build_model_factories,
    configure_mlflow,
    ensure_mlflow_bucket,
)

VALID_TARGETS: tuple[TargetName, ...] = ("light_comfort", "env_quality")


def _safe_mape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    """MAPE robusto a y=0 (ignora amostras com |y| < 1e-9)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.abs(y_true) > 1e-9
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def _evaluate(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(math.sqrt(mse))
    r2 = float(r2_score(y_true, y_pred))
    mape = _safe_mape(y_true, y_pred)
    return {"mae": mae, "rmse": rmse, "r2": r2, "mape": mape}


def _flatten_estimator_params(estimator) -> dict[str, str]:
    """Pega params do último step (o estimador real) para logar no MLflow."""
    try:
        last = estimator.steps[-1][1]
    except Exception:
        last = estimator
    params = {}
    try:
        raw = last.get_params(deep=False)
    except Exception:
        return params
    for k, v in raw.items():
        if v is None or isinstance(v, (int, float, str, bool)):
            params[f"hp__{k}"] = str(v)
    return params


def _log_artifacts(
    dataset: GoldDataset,
    y_pred: np.ndarray,
    out_dir: Path,
) -> None:
    feat_path = out_dir / "feature_list.txt"
    feat_path.write_text(
        "\n".join(dataset.feature_names), encoding="utf-8"
    )
    mlflow.log_artifact(str(feat_path), artifact_path="dataset")

    sample = pd.DataFrame(
        {
            "y_true": dataset.y_test.reset_index(drop=True),
            "y_pred": pd.Series(y_pred, name="y_pred"),
        }
    ).head(200)
    sample_path = out_dir / "predictions_sample.csv"
    sample.to_csv(sample_path, index=False, encoding="utf-8")
    mlflow.log_artifact(str(sample_path), artifact_path="dataset")

    summary = {
        "target": dataset.target_name,
        "dataset_version": dataset.dataset_version,
        "source": dataset.source,
        "n_rows_total": dataset.n_rows_total,
        "n_features": len(dataset.feature_names),
        "n_train": len(dataset.X_train),
        "n_test": len(dataset.X_test),
    }
    summary_path = out_dir / "dataset_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    mlflow.log_artifact(str(summary_path), artifact_path="dataset")


def _log_model(estimator, model_name: str) -> None:
    """Registra o modelo no MLflow com o flavor correto.

    Os imports `mlflow.sklearn` e `mlflow.xgboost` ficam no topo do módulo
    para evitar `UnboundLocalError` por escopo (qualquer `import mlflow.x`
    dentro da função faria `mlflow` virar local em todo o corpo).
    """
    if model_name == "xgb" and _HAS_MLFLOW_XGB:
        try:
            last = estimator.steps[-1][1]
            _mlflow_xgb.log_model(last, name="model")
            return
        except Exception:
            pass
    mlflow.sklearn.log_model(estimator, name="model")


def train_one(
    target: TargetName,
    model_name: str,
    test_size: float = 0.2,
    random_state: int = 42,
    experiment: str = DEFAULT_EXPERIMENT,
    register_as: str | None = None,
    run_name: str | None = None,
) -> dict:
    """Roda 1 treino + 1 run MLflow. Retorna dict com métricas e ids úteis."""
    factories = build_model_factories()
    if model_name not in factories:
        raise SystemExit(
            f"Modelo desconhecido: {model_name!r}. "
            f"Disponíveis: {sorted(factories)}."
        )

    configure_mlflow(experiment)
    ensure_mlflow_bucket()

    dataset = load_gold_dataset(
        target=target, test_size=test_size, random_state=random_state
    )
    estimator = factories[model_name]()

    with mlflow.start_run(run_name=run_name or f"{model_name}__{target}") as run:
        mlflow.set_tag("target", target)
        mlflow.set_tag("model", model_name)
        mlflow.set_tag("dataset_version", dataset.dataset_version)
        mlflow.set_tag("source", dataset.source)

        mlflow.log_param("target", target)
        mlflow.log_param("model", model_name)
        mlflow.log_param("dataset_version", dataset.dataset_version)
        mlflow.log_param("test_size", test_size)
        mlflow.log_param("random_state", random_state)
        mlflow.log_param("n_features", len(dataset.feature_names))
        mlflow.log_param("n_train", len(dataset.X_train))
        mlflow.log_param("n_test", len(dataset.X_test))
        mlflow.log_param("n_rows_total", dataset.n_rows_total)
        for k, v in _flatten_estimator_params(estimator).items():
            mlflow.log_param(k, v)

        estimator.fit(dataset.X_train, dataset.y_train)
        y_pred = estimator.predict(dataset.X_test)
        metrics = _evaluate(dataset.y_test, y_pred)
        mlflow.log_metrics(metrics)

        with tempfile.TemporaryDirectory(prefix="mlrun_") as tmp:
            _log_artifacts(dataset, y_pred, Path(tmp))

        _log_model(estimator, model_name)

        if register_as:
            try:
                model_uri = f"runs:/{run.info.run_id}/model"
                mlflow.register_model(model_uri=model_uri, name=register_as)
                mlflow.set_tag("registered_as", register_as)
            except Exception as exc:
                print(
                    f"[warn] register_model falhou ({register_as}): {exc!r}",
                    file=sys.stderr,
                )

        result = {
            "run_id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "target": target,
            "model": model_name,
            "metrics": metrics,
            "n_train": len(dataset.X_train),
            "n_test": len(dataset.X_test),
            "n_features": len(dataset.feature_names),
            "dataset_source": dataset.source,
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Treina um modelo de regressão sobre a Gold e registra no MLflow.",
    )
    parser.add_argument(
        "--target",
        choices=list(VALID_TARGETS),
        required=True,
        help="Alvo de regressão (ver docs/ML_DEFINICAO_ALVOS.md).",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Modelo: linear | ridge | knn | rf | xgb (xgb requer xgboost).",
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--experiment",
        default=DEFAULT_EXPERIMENT,
        help="Nome do experimento MLflow (default: home_swiss_home).",
    )
    parser.add_argument(
        "--register-as",
        default=None,
        help="Se informado, registra o modelo no Model Registry com esse nome.",
    )
    parser.add_argument("--run-name", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    train_one(
        target=args.target,
        model_name=args.model,
        test_size=args.test_size,
        random_state=args.random_state,
        experiment=args.experiment,
        register_as=args.register_as,
        run_name=args.run_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
