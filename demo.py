import os

# Artefatos vao para MinIO (S3) — mesmo usuario/senha do docker-compose
os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://127.0.0.1:9000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "minio")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "minio123")
BUCKET = "mlflow"

import boto3

_s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)
from botocore.exceptions import ClientError

try:
    _s3.create_bucket(Bucket=BUCKET)
except ClientError as e:
    code = e.response.get("Error", {}).get("Code", "")
    if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
        raise

import mlflow
import mlflow.sklearn
from sklearn.datasets import make_regression
from sklearn.linear_model import LinearRegression

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("meu_experimento")

with mlflow.start_run():
    X, y = make_regression(n_samples=100, n_features=1, noise=0.1)
    model = LinearRegression()
    model.fit(X, y)

    mlflow.log_param("coeficiente", model.coef_[0])
    mlflow.log_metric("Score", model.score(X, y))
    mlflow.sklearn.log_model(model, name="model")

    print(f"modelo salvo com sucesso no mlflow: {mlflow.get_artifact_uri()}")    