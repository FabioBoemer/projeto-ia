"""
Registro de metadados de execução no PostgreSQL (mesmo servidor do compose).

Tabela `swiss_pipeline_runs`: versionamento e auditoria das cargas Bronze/Silver/Gold.
"""
from __future__ import annotations

import json
from typing import Any

from .config import PG_URI


def register_run(layer: str, version: str, payload: dict[str, Any]) -> None:
    try:
        import psycopg2
    except ImportError:
        return

    try:
        conn = psycopg2.connect(PG_URI)
    except Exception:
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS swiss_pipeline_runs (
                    id BIGSERIAL PRIMARY KEY,
                    layer VARCHAR(16) NOT NULL,
                    version VARCHAR(64) NOT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                INSERT INTO swiss_pipeline_runs (layer, version, payload)
                VALUES (%s, %s, %s::jsonb);
                """,
                (layer, version, json.dumps(payload, default=str)),
            )
        conn.commit()
    finally:
        conn.close()
