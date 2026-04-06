"""
Orquestra Bronze -> Silver -> Gold.

Uso (na pasta projeto-ia, com MinIO no ar):

  py -3.12 -m pipeline.run_pipeline --max-rows 10000

Variáveis úteis:
  DATASET_VERSION=2025-04-05
  GEOMETRIES_CSV=C:\\caminho\\geometries.csv
  SIMULATIONS_CSV=C:\\caminho\\simulations.csv
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> int:
    # Permite executar como script: python -m pipeline.run_pipeline
    os.environ.setdefault("PYTHONUTF8", "1")

    parser = argparse.ArgumentParser(description="Pipeline Medallion Home Swiss Home")
    parser.add_argument("--version", default=None, help="Versão lógica (padrão: data UTC)")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Limita linhas lidas em geometries+simulations (teste rápido; None = tudo)",
    )
    parser.add_argument("--skip-bronze", action="store_true")
    parser.add_argument("--skip-silver", action="store_true")
    parser.add_argument("--skip-gold", action="store_true")
    args = parser.parse_args()

    if args.version:
        os.environ["DATASET_VERSION"] = args.version

    from . import bronze, gold, silver
    from .config import dataset_version
    from .metadata_db import register_run

    version = args.version or dataset_version()
    out: dict = {"version": version}

    if not args.skip_bronze:
        b = bronze.run_bronze(version=version)
        out["bronze"] = b
        register_run("bronze", version, b)
        print(json.dumps({"bronze": b}, indent=2, ensure_ascii=False))

    if not args.skip_silver:
        s = silver.run_silver(version=version, max_rows=args.max_rows)
        out["silver"] = s
        register_run("silver", version, s)
        print(json.dumps({"silver": s}, indent=2, ensure_ascii=False))

    if not args.skip_gold:
        g = gold.run_gold(silver_version=version, version=version)
        out["gold"] = g
        register_run("gold", version, g)
        print(json.dumps({"gold": g}, indent=2, ensure_ascii=False))

    print("OK:", json.dumps(out, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
