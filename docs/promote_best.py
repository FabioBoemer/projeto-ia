"""
Higieniza o experimento `home_swiss_home` no MLflow:

1. Apaga (soft-delete) runs sem modelo logado (orfas da primeira execucao
   que quebrou no UnboundLocalError do `_log_model`).
2. Registra os melhores modelos por alvo no Model Registry:
   - `home_swiss_light_comfort`  -> melhor run de target=light_comfort (por R^2)
   - `home_swiss_env_quality`    -> melhor run de target=env_quality   (por R^2)

Uso:

    py -3.12 docs\promote_best.py
"""
from __future__ import annotations

import os

os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://127.0.0.1:9000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "minio")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "minio123")

import mlflow
from mlflow.tracking import MlflowClient

EXPERIMENT = "home_swiss_home"
TRACKING = "http://localhost:5000"

REGISTRY_BY_TARGET = {
    "light_comfort": "home_swiss_light_comfort",
    "env_quality": "home_swiss_env_quality",
}


def has_logged_model(run) -> bool:
    outputs = getattr(run, "outputs", None)
    if outputs is None:
        return False
    return bool(getattr(outputs, "model_outputs", []))


def main() -> None:
    mlflow.set_tracking_uri(TRACKING)
    client = MlflowClient(TRACKING)
    exp = client.get_experiment_by_name(EXPERIMENT)
    if exp is None:
        raise SystemExit(f"Experimento '{EXPERIMENT}' nao encontrado em {TRACKING}.")

    runs = client.search_runs(
        [exp.experiment_id], order_by=["metrics.r2 DESC"], max_results=200
    )
    print(f"Total runs: {len(runs)}")

    deleted = 0
    for r in runs:
        if not has_logged_model(r):
            client.delete_run(r.info.run_id)
            deleted += 1
            print(f"  apaguei run orfa: {r.info.run_id[:8]}  "
                  f"target={r.data.tags.get('target')} model={r.data.tags.get('model')}")
    print(f"Runs orfas apagadas: {deleted}")

    runs = client.search_runs(
        [exp.experiment_id],
        order_by=["metrics.r2 DESC"],
        max_results=200,
    )
    runs = [r for r in runs if has_logged_model(r)]
    print(f"\nRuns com modelo: {len(runs)}")

    best_by_target: dict[str, object] = {}
    for r in runs:
        tgt = r.data.tags.get("target")
        if tgt and tgt not in best_by_target:
            best_by_target[tgt] = r

    print("\nMelhores por alvo:")
    for tgt, r in best_by_target.items():
        print(
            f"  {tgt:<14s}  model={r.data.tags.get('model'):<6s}  "
            f"r2={r.data.metrics['r2']:.4f}  run={r.info.run_id[:8]}"
        )

    print("\nRegistrando no Model Registry:")
    for tgt, name in REGISTRY_BY_TARGET.items():
        r = best_by_target.get(tgt)
        if r is None:
            print(f"  (sem run para {tgt})")
            continue
        model_id = r.outputs.model_outputs[0].model_id
        model_uri = f"models:/{model_id}"
        try:
            mv = mlflow.register_model(model_uri=model_uri, name=name)
            client.set_tag(r.info.run_id, "registered_as", name)
            client.set_tag(r.info.run_id, "registered_version", str(mv.version))
            print(
                f"  {name:<28s}  v{mv.version}  <- run {r.info.run_id[:8]} "
                f"(r2={r.data.metrics['r2']:.4f})"
            )
        except Exception as exc:
            print(f"  ERRO ao registrar {name}: {exc!r}")


if __name__ == "__main__":
    main()
