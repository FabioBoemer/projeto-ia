"""Utilitários MinIO (S3 API)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from .config import AWS_KEY, AWS_SECRET, DATA_BUCKET, MINIO_ENDPOINT


def client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
    )


def ensure_bucket(name: str = DATA_BUCKET) -> None:
    c = client()
    try:
        c.create_bucket(Bucket=name)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def put_json(bucket: str, key: str, obj: dict) -> None:
    import json

    c = client()
    c.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )


def upload_file(local_path: Path, bucket: str, key: str) -> int:
    """Envia arquivo local; retorna tamanho em bytes."""
    c = client()
    path = Path(local_path)
    c.upload_file(str(path), bucket, key)
    return path.stat().st_size


def file_sha256(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
