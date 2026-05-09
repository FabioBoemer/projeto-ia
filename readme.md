## Turma
TAN1

## PO
- João Antonio Tonollo da Silva RA: 222652

## Grupo
- Bruno Bagatella RA: 211653
- Eduardo Henrique dos Santos de Souza Lima RA: 211990
- Fábio Boemer Figueira RA: 211999
- Gabriel Oliveira Ventura da Costa RA: 212086
- Gustavo Gonçalves Tuda RA: 222919
- João Antonio Tonollo da Silva RA: 222652
- João Vitor Fragoso de Camargo RA: 212057
- João Pedro Sanches Rodrigues RA: 223205
- Lucas Rogério do Couto RA: 223466
- Matheus Benite Disegna RA: 211958
- Vinícius Muniz Ferraz RA: 212190
- Sivaldo Castro Araújo Neto RA: 212181

## Tema
Arquitetura - https://github.com/awesomedata/awesome-public-datasets?tab=readme-ov-file#architecture

## Nome da Empresa:
Home Swiss Home

## Objetivo:
Construir a **base de dados em camadas Medallion (Bronze / Silver / Gold)** sobre o dataset suíço, com **scripts** (ETL e treino de modelo) lendo e gravando no **MinIO**, **metadados e versionamento em PostgreSQL** e **MLflow** registrando experimentos, métricas e artefatos. **Sem API e sem RAG neste ciclo** — foco em dados, pipeline e MLOps leve.

## Problema de negócio:
Moradores e interessados em imóveis na Suíça precisam comparar apartamentos além de preço e metragem: iluminação natural, ruído, vista, conectividade do layout etc. Essas informações estão em dados técnicos volumosos (geometrias e simulações). O projeto consiste em **estruturar esses dados**, **governança** e **experimentos de modelagem**.

## Dados brutos (fora do Git)

Os arquivos **`geometries.csv`** e **`simulations.csv`** não são versionados (`.gitignore`) por serem muito grandes para o GitHub.

**Fonte:** dataset **Swiss Dwellings**, obtido por download no **Zenodo**: [https://zenodo.org/records/7070952](https://zenodo.org/records/7070952) — DOI [10.5281/zenodo.7070952](https://doi.org/10.5281/zenodo.7070952). Licença **CC-BY-4.0** (atribuir a fonte ao usar).

**Uso local:** após baixar, coloque os dois CSV na **raiz deste repositório** (`projeto-ia/`), ao lado do `readme.md`, para o pipeline Medallion encontrá-los por padrão. Detalhes em [`docs/MEDALLION_GOVERNANCA.md`](docs/MEDALLION_GOVERNANCA.md).

### Diagrama (arquitetura até Sprint 4 — sem API / sem RAG)

Fluxo: **scripts** (local ou container) orquestram ETL e treino; **MinIO** guarda Bronze, Silver e Gold; **MLflow** registra runs e pode armazenar artefatos no mesmo MinIO; **PostgreSQL** serve ao backend do MLflow e às tabelas de metadados do dataset.

```mermaid
flowchart TB
  subgraph dev [Maquina local - runs e experimentos]
    PY[Scripts_LSTM_KNN_ETC]
  end
  subgraph docker [Rede Docker Compose]
    subgraph minio [MinIO - dados em arquivo Medallão]
      direction TB
      BRZ[Bronze]
      SLV[Silver]
      GLD[Gold]
    end
    PG[(PostgreSQL)]
    MLF[MLflow Tracking]
  end
  PY -->|leitura_gravação| BRZ
  PY -->|leitura_gravação| SLV
  PY -->|leitura_gravação| GLD
  PY -->|HTTP_tracking| MLF
  MLF -->|metadados_SQL| PG
  MLF -->|artefatos_arquivo| GLD
  PY -->|SQL_Sprint4_metadados| PG
```

**Legenda:** igual ao quadro — **runs/experimentos** (scripts: ETL, LSTM, KNN…) trocam dados com **MinIO + Postgres**; **MLflow** guarda **metadados** no Postgres e **artefatos** (modelos, etc.) como arquivos no MinIO.

---

## Sprint 4 — Modelagem e Treinamento (ML + MLflow)

Tudo da modelagem está no pacote [`ml/`](ml/) (treino) + [`pipeline/ml_targets.py`](pipeline/ml_targets.py) (alvos). A defesa completa (justificativa de cada escolha) está em [`docs/ML_TREINO.md`](docs/ML_TREINO.md).

### Resumo do que foi feito

- **Problema:** regressão tabular sobre `gold/<versão>/apartment_kpis.parquet` (1 linha = 1 apartamento).
- **Alvos** (definidos em [`docs/ML_DEFINICAO_ALVOS.md`](docs/ML_DEFINICAO_ALVOS.md)):
  - `target_light_comfort` — média das colunas `avg__sun_*`.
  - `target_env_quality` — índice composto luz + vista + ruído invertido, em `[0, 1]`.
- **Modelos:** `linear`, `ridge`, `knn`, `rf`, `xgb` (XGBoost). LSTM/TCN foram descartados porque os dados não são série temporal.
- **Tracking:** MLflow em `http://localhost:5000`, experimento `home_swiss_home`. Artefatos em `s3://mlflow/...` (MinIO).

### Como treinar

1. Subir a infra: `docker compose up -d` e confirmar MLflow em `http://localhost:5000` e MinIO em `http://localhost:9001`.
2. Garantir que existe a Gold (uma vez): `py -3.12 -m pipeline.run_pipeline --max-rows 50000` (ou completo).
3. Instalar dependências de ML: `py -3.12 -m pip install -r requirements-ml.txt`.
4. Rodar a matriz inteira (uma run MLflow por combinação):

```powershell
py -3.12 -m ml.run_all
```

Ou um treino isolado:

```powershell
py -3.12 -m ml.train --target light_comfort --model xgb
py -3.12 -m ml.train --target env_quality   --model rf
```

5. Abrir `http://localhost:5000`, experimento **home_swiss_home**, e comparar runs (R², RMSE, MAE, MAPE).


