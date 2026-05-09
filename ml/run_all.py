"""
Roda a matriz completa de experimentos do Sprint 4.

Para cada combinação `(target, model)` na matriz padrão, dispara
`ml.train.train_one` — gerando uma run MLflow por combinação.
Ao final, imprime um ranking por R² no console.

Uso:

    py -3.12 -m ml.run_all
    py -3.12 -m ml.run_all --models linear ridge xgb
    py -3.12 -m ml.run_all --targets light_comfort
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable

from .data import TargetName
from .registry import DEFAULT_EXPERIMENT, build_model_factories
from .train import VALID_TARGETS, train_one

DEFAULT_MODELS_ORDER: tuple[str, ...] = ("linear", "ridge", "knn", "rf", "xgb")


def _resolve_models(requested: Iterable[str] | None) -> list[str]:
    available = list(build_model_factories().keys())
    if not requested:
        return [m for m in DEFAULT_MODELS_ORDER if m in available]
    chosen = list(requested)
    missing = [m for m in chosen if m not in available]
    if missing:
        raise SystemExit(
            f"Modelos não disponíveis: {missing} (instalados: {available})."
        )
    return chosen


def _resolve_targets(requested: Iterable[str] | None) -> list[TargetName]:
    if not requested:
        return list(VALID_TARGETS)
    invalid = [t for t in requested if t not in VALID_TARGETS]
    if invalid:
        raise SystemExit(
            f"Alvos inválidos: {invalid}. Use {list(VALID_TARGETS)}."
        )
    return list(requested)


def run_matrix(
    targets: list[TargetName],
    models: list[str],
    experiment: str = DEFAULT_EXPERIMENT,
    test_size: float = 0.2,
    random_state: int = 42,
) -> list[dict]:
    results: list[dict] = []
    for target in targets:
        for model_name in models:
            print(f"\n=== {target} × {model_name} ===")
            try:
                res = train_one(
                    target=target,
                    model_name=model_name,
                    test_size=test_size,
                    random_state=random_state,
                    experiment=experiment,
                )
                results.append(res)
            except Exception as exc:
                print(f"[erro] {target} × {model_name}: {exc!r}", file=sys.stderr)
                results.append(
                    {"target": target, "model": model_name, "error": repr(exc)}
                )
    return results


def _print_ranking(results: list[dict]) -> None:
    ok = [r for r in results if "metrics" in r]
    if not ok:
        print("\n(nenhum resultado válido para ranquear)")
        return
    print("\n=== Ranking por R² (maior melhor) ===")
    ranked = sorted(ok, key=lambda r: r["metrics"]["r2"], reverse=True)
    for r in ranked:
        m = r["metrics"]
        print(
            f"  R²={m['r2']:.4f} | RMSE={m['rmse']:.4f} | MAE={m['mae']:.4f} "
            f"| {r['target']:<14s} | {r['model']:<6s} | run={r['run_id'][:8]}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Executa a matriz Sprint 4 (target × model) e loga no MLflow."
    )
    parser.add_argument("--targets", nargs="*", default=None)
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args(argv)

    targets = _resolve_targets(args.targets)
    models = _resolve_models(args.models)

    print(f"Alvos: {targets}")
    print(f"Modelos: {models}")
    print(f"Experimento MLflow: {args.experiment}")

    results = run_matrix(
        targets=targets,
        models=models,
        experiment=args.experiment,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    _print_ranking(results)

    print("\n=== Resumo JSON ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
