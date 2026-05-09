"""Lista o conteudo do bucket mlflow no MinIO para conferir Logged Models."""
from __future__ import annotations

import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://127.0.0.1:9000",
    aws_access_key_id="minio",
    aws_secret_access_key="minio123",
)

sufixos: dict[str, int] = {}
prefixos_topo: dict[str, int] = {}
total = 0
size_total = 0
modelo_exemplos: list[tuple[str, int]] = []

for page in s3.get_paginator("list_objects_v2").paginate(Bucket="mlflow"):
    for o in page.get("Contents", []):
        total += 1
        size_total += o["Size"]
        nome = o["Key"].split("/")[-1]
        sufixos[nome] = sufixos.get(nome, 0) + 1
        topo = o["Key"].split("/")[0]
        prefixos_topo[topo] = prefixos_topo.get(topo, 0) + 1
        if "model" in o["Key"].lower():
            modelo_exemplos.append((o["Key"], o["Size"]))

print(f"Total: {total} objetos, {size_total / 1e6:.2f} MB")
print(f"Prefixos de topo: {prefixos_topo}")

print("\nArquivos por nome (top 15):")
for n, c in sorted(sufixos.items(), key=lambda x: -x[1])[:15]:
    print(f"  {c:3d}x {n}")

print(f"\nObjetos com 'model' no caminho: {len(modelo_exemplos)}")
for k, sz in modelo_exemplos[:15]:
    print(f"  {sz:>12} B  {k}")
