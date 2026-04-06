"""
Camada Bronze: cópia fiel das fontes (CSV brutos), sem regra de negócio.

- Preserva nomes de colunas e texto original.
- Adiciona apenas metadados de ingestão (manifest JSON ao lado dos arquivos).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_BUCKET, GEOMETRIES_CSV, PREFIX_BRONZE, SIMULATIONS_CSV, dataset_version, key
from .s3_utils import ensure_bucket, put_json, upload_file, file_sha256


def run_bronze(
    geometries: Path | None = None,
    simulations: Path | None = None,
    version: str | None = None,
) -> dict:
    geometries = Path(geometries or GEOMETRIES_CSV)
    simulations = Path(simulations or SIMULATIONS_CSV)
    version = version or dataset_version()

    if not geometries.is_file():
        raise FileNotFoundError(f"Bronze: geometries não encontrado: {geometries}")
    if not simulations.is_file():
        raise FileNotFoundError(f"Bronze: simulations não encontrado: {simulations}")

    ensure_bucket()
    manifest = {
        "layer": "bronze",
        "version": version,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }

    for label, path in (("geometries.csv", geometries), ("simulations.csv", simulations)):
        s3_key = key(PREFIX_BRONZE, version, label)
        size = upload_file(path, DATA_BUCKET, s3_key)
        sha = file_sha256(path)
        manifest["files"].append(
            {
                "filename": label,
                "s3_key": s3_key,
                "bytes": size,
                "sha256": sha,
                "source_path": str(path.resolve()),
            }
        )

    manifest_key = key(PREFIX_BRONZE, version, "manifest.json")
    put_json(DATA_BUCKET, manifest_key, manifest)

    manifest["manifest_s3_key"] = manifest_key
    return manifest
