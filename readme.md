## Turma
TAN1

## Product Owner (PO)
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
**Arquitetura** - Dataset "*Swiss Dwellings*", obtido por download no **Zenodo**: [https://zenodo.org/records/7070952](https://zenodo.org/records/7070952) — DOI [10.5281/zenodo.7070952](https://doi.org/10.5281/zenodo.7070952). Licença **CC-BY-4.0**

## Nome da Empresa:
*Home Swiss Home*

## Problema de negócio:
Durante a busca por um imóvel ideal, moradores e interessados são facilmente atraídos pelas características de preço e metragem de uma determinada propriedade, desconsiderando outros aspectos importantes como a incidência de iluminação natural, poluição sonora e visual, layout, localização, entre outras. Até mesmo os clientes mais observadores que buscam se informar sobre todas essas características podem acabar se deparando com uma falta de informações por parte do vendedor, dificultando uma tomada de decisão certeira.

## Objetivo:
Com esse projeto, a equipe teve como objetivo a construção de uma pipeline de treinamento funcional com algoritmos de regressão que utilizam o dataset "*Swiss Dwellings*" como dados de treinamento, tendo como finalidade prever os atributos de **qualidade ambiental (target_env_quality)** e **conforto luminoso (target_light_comfort)** dos apartamentos do dataset. 

Para tal, os arquivos de dados presentes no dataset serão organizados considerando a arquitetura **Medallion (Camadas Bronze / Silver / Gold)** e armazenados na plataforma **MinIO**. Em seguida, os dados da camada Gold serão utilizados por cinco algoritmos de regressão diferentes, sendo eles: **Regressão Linear**, **Regressão Ridge**, **K-Nearest Neighbors (KNN)**, **Random Forest** e **Extreme Gradient Boosting (XGBoost)**. Todos os modelos treinados ficarão armazenados no **MiniIO** e os seus metadados no **PostgreSQL**. Por fim, a plataforma **MLFlow** permitirá a análise dos modelos armazenados para determinar qual é o mais capaz de prever a qualidade ambiental e o conforto luminoso de um determinado apartamento.

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


