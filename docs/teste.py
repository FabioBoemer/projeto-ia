r"""Teste rápido dos alvos em pipeline.ml_targets.

Execute na raiz do repositório:

  cd caminho\para\projeto-ia
  py -3.12 docs\teste.py

Parquet da Gold: defina GOLD_PARQUET ou rode o pipeline antes. O script
procura apartment_kpis.parquet em pastas comuns.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from pipeline.ml_targets import add_ml_targets, feature_columns_for_light_comfort


def _resolve_gold_parquet() -> Path:
    env = os.environ.get("GOLD_PARQUET")
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
        raise FileNotFoundError(f"GOLD_PARQUET definido mas arquivo não existe: {p}")

    version = os.environ.get("DATASET_VERSION", "")
    candidates: list[Path] = [
        _ROOT / "apartment_kpis.parquet",
        _ROOT / "data" / "gold" / "apartment_kpis.parquet",
    ]
    if version:
        candidates.insert(1, _ROOT / "gold" / version / "apartment_kpis.parquet")

    for p in candidates:
        if p.is_file():
            return p

    # Último recurso: primeiro Parquet com esse nome sob projeto-ia (pode ser lento)
    for p in _ROOT.rglob("apartment_kpis.parquet"):
        if p.is_file():
            return p

    msg = (
        "Não encontrei apartment_kpis.parquet.\n"
        "  1) Rode o pipeline Medallion (Gold), ou\n"
        "  2) Exporte o Parquet do MinIO, ou\n"
        "  3) Defina: $env:GOLD_PARQUET='caminho\\completo\\apartment_kpis.parquet'\n"
        f"Tentados: {[str(c) for c in candidates]}"
    )
    raise FileNotFoundError(msg)


_parquet = _resolve_gold_parquet()
print("Usando:", _parquet)
df = pd.read_parquet(_parquet)
df = add_ml_targets(df)
y = df["target_light_comfort"]
X = df[feature_columns_for_light_comfort(df)]
print("X shape:", X.shape, "y shape:", y.shape)
