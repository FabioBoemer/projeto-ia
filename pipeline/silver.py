"""
Camada Silver: dados limpos, tipados e integrados (qualidade + join lógico).

Métodos aplicados:
- Chaves apartment_id (string) e area_id (Int64 nullable) alinhadas entre fontes.
- Contagem de entidades geométricas por (apartment_id, area_id).
- Junção às métricas de simulations.
- Saída Parquet em streaming (evita carregar simulations inteiro na RAM).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import DATA_BUCKET, GEOMETRIES_CSV, PREFIX_SILVER, SIMULATIONS_CSV, dataset_version, key
from .s3_utils import ensure_bucket, upload_file


def _norm_apartment(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip()


def _norm_area(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def _geo_entity_counts(
    geometries_path: Path,
    chunksize: int = 100_000,
    max_rows: int | None = None,
) -> pd.Series:
    parts: list[pd.Series] = []
    read_rows = 0
    usecols = ["apartment_id", "area_id"]
    for chunk in pd.read_csv(
        geometries_path,
        chunksize=chunksize,
        usecols=usecols,
        encoding="utf-8",
        low_memory=False,
    ):
        chunk = chunk.assign(
            apartment_id=_norm_apartment(chunk["apartment_id"]),
            area_id=_norm_area(chunk["area_id"]),
        )
        parts.append(chunk.groupby(["apartment_id", "area_id"], sort=False).size())
        read_rows += len(chunk)
        if max_rows and read_rows >= max_rows:
            break
    if not parts:
        return pd.Series(dtype="int64")
    counts = pd.concat(parts)
    return counts.groupby(level=[0, 1]).sum()


def run_silver(
    geometries_path: Path | None = None,
    simulations_path: Path | None = None,
    version: str | None = None,
    chunksize: int = 50_000,
    max_rows: int | None = None,
) -> dict:
    geometries_path = Path(geometries_path or GEOMETRIES_CSV)
    simulations_path = Path(simulations_path or SIMULATIONS_CSV)
    version = version or dataset_version()
    ensure_bucket()

    geo_counts = _geo_entity_counts(geometries_path, chunksize=chunksize, max_rows=max_rows)

    tmpdir = Path(tempfile.mkdtemp(prefix="silver_"))
    area_path = tmpdir / "area_features.parquet"
    writer: pq.ParquetWriter | None = None
    pa_schema: pa.Schema | None = None
    total_rows = 0
    result: dict | None = None
    try:
        read_rows = 0
        for chunk in pd.read_csv(
            simulations_path,
            chunksize=chunksize,
            encoding="utf-8",
            low_memory=False,
        ):
            if max_rows is not None:
                remaining = max_rows - read_rows
                if remaining <= 0:
                    break
                if len(chunk) > remaining:
                    chunk = chunk.iloc[:remaining].copy()
            chunk = chunk.assign(
                apartment_id=_norm_apartment(chunk["apartment_id"]),
                area_id=_norm_area(chunk["area_id"]),
            )
            idx = pd.MultiIndex.from_arrays([chunk["apartment_id"], chunk["area_id"]])
            matched = geo_counts.reindex(idx)
            chunk = chunk.assign(
                geometry_entity_count=matched.fillna(0).astype("int64").values
            )
            table = pa.Table.from_pandas(chunk, preserve_index=False)
            if writer is None:
                pa_schema = table.schema
                writer = pq.ParquetWriter(
                    area_path, pa_schema, compression="snappy", use_dictionary=True
                )
            else:
                table = table.cast(pa_schema)
            writer.write_table(table)
            total_rows += len(chunk)
            read_rows += len(chunk)
        if writer is None:
            raise ValueError("Silver: nenhum bloco lido de simulations.")
        writer.close()
        writer = None

        out_key = key(PREFIX_SILVER, version, "area_features.parquet")
        size = upload_file(area_path, DATA_BUCKET, out_key)
        result = {
            "layer": "silver",
            "version": version,
            "rows": total_rows,
            "s3_key": out_key,
            "bytes": size,
            "method": "stream_parquet_snappy",
        }
    finally:
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)

    if result is None:
        raise RuntimeError("Silver: falha antes de concluir a escrita.")
    return result
