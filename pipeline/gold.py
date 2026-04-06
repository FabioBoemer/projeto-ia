"""
Camada Gold: visão analítica / negócio — agregações por apartamento.

Métricas (exemplos alinhados ao problema de negócio Home Swiss Home):
- Conforto solar médio (média das colunas sun_*_mean por apartamento).
- Ruído e tráfego (média de noise_* e window_noise_* quando numéricas).
- Conectividade do layout (média de connectivity_*).
- Vista / paisagem (média de view_*).
- Metadados: número de áreas (contagem de linhas Silver por apartment_id).
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pandas as pd

from .config import DATA_BUCKET, PREFIX_GOLD, PREFIX_SILVER, dataset_version, key
from .s3_utils import client, ensure_bucket, upload_file


def _aggregate_apartment(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega métricas numéricas relevantes por apartment_id."""
    id_col = "apartment_id"
    if id_col not in df.columns:
        raise ValueError("Gold: coluna apartment_id ausente na entrada Silver.")

    num = df.select_dtypes(include=["float64", "float32", "int64", "int32"])
    # Mantém apenas colunas de domínio (prefixos conhecidos)
    pat = re.compile(r"^(sun_|noise_|view_|connectivity_|layout_|window_noise_)")
    keep = [c for c in num.columns if pat.match(c)]
    if not keep:
        # fallback: todas numéricas exceto chaves
        drop = {"area_id", "building_id", "floor_id", "site_id", "unit_id", "layout_area_type"}
        keep = [c for c in num.columns if c not in drop]

    agg_mean = df.groupby(id_col, sort=False)[keep].mean(numeric_only=True)
    agg_mean.columns = [f"avg__{c}" for c in agg_mean.columns]

    n_areas = df.groupby(id_col, sort=False).size().rename("n_areas_in_sample")
    out = agg_mean.join(n_areas, how="left")
    out = out.reset_index()
    return out


def run_gold(
    silver_version: str | None = None,
    version: str | None = None,
) -> dict:
    """
    Lê area_features.parquet da Silver no MinIO, agrega Gold e envia Parquet.

    silver_version: versão da pasta silver (default = mesma DATASET_VERSION).
    """
    silver_version = silver_version or dataset_version()
    version = version or dataset_version()
    ensure_bucket()

    src_key = key(PREFIX_SILVER, silver_version, "area_features.parquet")
    c = client()
    obj = c.get_object(Bucket=DATA_BUCKET, Key=src_key)
    tmp = Path(tempfile.mkdtemp(prefix="gold_")) / "in.parquet"
    tmp.write_bytes(obj["Body"].read())
    try:
        df = pd.read_parquet(tmp, engine="pyarrow")
        gold_df = _aggregate_apartment(df)
        out_local = tmp.parent / "apartment_kpis.parquet"
        gold_df.to_parquet(out_local, index=False, engine="pyarrow", compression="snappy")
        out_key = key(PREFIX_GOLD, version, "apartment_kpis.parquet")
        size = upload_file(out_local, DATA_BUCKET, out_key)
        return {
            "layer": "gold",
            "version": version,
            "silver_source_key": src_key,
            "rows": len(gold_df),
            "columns": len(gold_df.columns),
            "s3_key": out_key,
            "bytes": size,
        }
    finally:
        import shutil

        shutil.rmtree(tmp.parent, ignore_errors=True)
