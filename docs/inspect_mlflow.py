"""Inspeciona o que o MLflow registrou no experimento home_swiss_home."""
from __future__ import annotations

import os

os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://127.0.0.1:9000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "minio")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "minio123")

from mlflow.tracking import MlflowClient

EXPERIMENT = "home_swiss_home"
TRACKING = "http://localhost:5000"


def main() -> None:
    c = MlflowClient(TRACKING)
    exp = c.get_experiment_by_name(EXPERIMENT)
    if exp is None:
        print(f"Experimento '{EXPERIMENT}' nao encontrado em {TRACKING}.")
        return

    print(
        f"Experimento: name={exp.name} id={exp.experiment_id} "
        f"stage={exp.lifecycle_stage} artifact={exp.artifact_location}"
    )
    runs = c.search_runs(
        [exp.experiment_id], order_by=["metrics.r2 DESC"], max_results=50
    )
    print(f"Total de runs: {len(runs)}\n")

    header = f"{'target':<14} {'model':<7} {'r2':>7} {'rmse':>8} {'mae':>8}  run_id"
    print(header)
    print("-" * len(header))
    for r in runs:
        t = r.data.tags
        m = r.data.metrics
        print(
            f"{t.get('target',''):<14} {t.get('model',''):<7} "
            f"{m.get('r2',0):>7.4f} {m.get('rmse',0):>8.4f} "
            f"{m.get('mae',0):>8.4f}  {r.info.run_id[:8]}"
        )

    if not runs:
        return

    best = runs[0]
    print(f"\nDetalhe da melhor run ({best.info.run_id}):")
    print(f"  params (n={len(best.data.params)}):")
    for k, v in list(best.data.params.items())[:12]:
        print(f"    {k} = {v}")
    print("  metrics:")
    for k, v in best.data.metrics.items():
        print(f"    {k} = {v}")
    print("  tags (sem mlflow.*):")
    for k, v in best.data.tags.items():
        if not k.startswith("mlflow."):
            print(f"    {k} = {v}")

    print("  artefatos:")
    for a in c.list_artifacts(best.info.run_id):
        suffix = "/" if a.is_dir else ""
        print(f"    {a.path}{suffix}")
        if a.is_dir:
            for sub in c.list_artifacts(best.info.run_id, a.path):
                print(f"      {sub.path}")


if __name__ == "__main__":
    main()
