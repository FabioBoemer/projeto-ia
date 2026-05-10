# Modelagem, Treinamento e Tracking (MLflow)

---

## 1. Problema de ML — por que **regressão**?

### 1.1 De onde vêm os dados (origem)

- **Fonte primária:** dataset **Swiss Dwellings** (Zenodo, registro [7070952](https://zenodo.org/records/7070952), DOI [10.5281/zenodo.7070952](https://doi.org/10.5281/zenodo.7070952), licença **CC-BY-4.0**).
- **Arquivos brutos:** `geometries.csv` (uma linha por entidade geométrica, com a coluna `geometry` em WKT) e `simulations.csv` (uma linha por área, com famílias `sun_*`, `noise_*`, `view_*`, `connectivity_*`, `layout_*`, `window_noise_*`).
- **Pipeline Medallion:**
  - **Bronze:** subiu os CSVs brutos para `s3://homesswiss/bronze/<versão>/` no MinIO + `manifest.json` com SHA-256 (ver [`pipeline/bronze.py`](../pipeline/bronze.py)).
  - **Silver:** uma linha por **(apartment_id, area_id)** — métricas de simulação tipadas + `geometry_entity_count`, escrito como `silver/<versão>/area_features.parquet` (Snappy, streaming) — ver [`pipeline/silver.py`](../pipeline/silver.py).
  - **Gold:** **uma linha por apartamento**, com colunas `avg__<família>__<sub>` (média) + `n_areas_in_sample`, em `gold/<versão>/apartment_kpis.parquet` — ver [`pipeline/gold.py`](../pipeline/gold.py).

### 1.2 Por que regressão (e não classificação ou série temporal)?

| Tipo de tarefa | Cabe aqui? | Justificativa |
|---|---|---|
| **Regressão** | **SIM (escolhido)** | Os alvos são **valores contínuos** por apartamento: `light_comfort` é uma média de iluminação (klx) e `env_quality_score` é um índice em `[0, 1]`. Nenhum dos dois é uma categoria. |
| Classificação | Não (sem retrabalho) | Não temos rótulo categórico no Swiss Dwellings. Para virar classificação seria preciso **binarizar** o índice (ex.: alto/baixo conforto), o que descarta informação numérica útil e exigiria justificar um corte arbitrário. |
| Série temporal | **NÃO** | A Gold tem **uma linha por apartamento** (sem eixo temporal). Os campos `sun_*` já são o resultado de simulações ao longo de cenários — eles **não** trazem timestamps por apartamento. Por isso `LSTM`/`TCN` **não se aplicam** a este dataset, e seriam um erro técnico forçar essa modelagem. |

Definiu-se o problema como regressão tabular porque, após o pipeline Medallion, a Gold entrega exatamente uma observação por apartamento e os alvos são contínuos. Séries temporais foram descartadas porque o Swiss Dwellings não traz eixo temporal — os cenários `sun_*` já vêm pré-agregados.

### 1.3 Alvos definidos

Definidos em [`docs/ML_DEFINICAO_ALVOS.md`](ML_DEFINICAO_ALVOS.md) e implementados em [`pipeline/ml_targets.py`](../pipeline/ml_targets.py).

1. **`target_light_comfort`** = média de todas as colunas `avg__sun_*`.
   - **Interpretação:** quanto maior, mais iluminação simulada média no apartamento.
2. **`target_env_quality`** = índice em `[0, 1]` combinando, com pesos iguais e normalização min–max:
   - Luz (média de `avg__sun_*`),
   - Vista (média de `avg__view_*`),
   - Ruído invertido (`1 − norm(media de avg__noise_*)`).
   - **Interpretação:** quanto maior, melhor a combinação relativa de luz + vista + silêncio.

---

## 2. Features (X) — sem vazamento

A função `add_ml_targets` cria os alvos. Para montar `X`, utilizam-se os helpers que **excluem** as colunas que compõem o alvo:

- `feature_columns_for_light_comfort(df)` — exclui `apartment_id`, alvos derivados e **toda** a família `avg__sun_*`. Resultado típico: `avg__noise_*`, `avg__view_*`, `avg__connectivity_*`, `avg__layout_*`, `avg__window_noise_*`, `n_areas_in_sample`.
- `feature_columns_for_env_quality(df)` — exclui também `avg__view_*` e `avg__noise_*` (porque entram direto no índice). Resultado típico: `avg__connectivity_*`, `avg__layout_*`, `avg__window_noise_*`, `n_areas_in_sample`.

O helpers são importantes, pois se fossem incluídos `avg__sun_*` como feature ao prever `light_comfort`, o R² ficaria artificialmente próximo de 1.0 (vazamento). O código **bloqueia** essa armadilha por construção.

---

## 3. Seleção de modelos

A seleção mistura **interpretáveis** (baseline de defesa) e **não-lineares de alto desempenho** (para realmente medir ganho). Todos rodam em `Pipeline` sklearn com `SimpleImputer(median)` e, quando aplicável, `StandardScaler` — para tratar `NaN` e diferenças de escala entre famílias `avg__*`.

| Modelo | Por que está aqui | Hiperparâmetros (default) |
|---|---|---|
| **LinearRegression** | Baseline interpretável (coeficientes por feature). Se o problema for quase linear, ele já entrega. | — |
| **Ridge** | Regularização L2 — espera-se forte multicolinearidade entre colunas `avg__*` da mesma família. Reduz variância sem perder a estrutura linear. | `alpha=1.0` |
| **KNeighborsRegressor** | Não-paramétrico, captura vizinhança no espaço de features padronizadas. | `n_neighbors=10`, `weights="distance"` |
| **RandomForestRegressor** | Robusto, lida com não-linearidade e interações sem feature engineering pesada. | `n_estimators=300`, `min_samples_leaf=2` |
| **XGBoost** | Estado da arte em tabular.| `n_estimators=400`, `max_depth=6`, `lr=0.05`, `tree_method="hist"` |

Comparam-se os cinco modelos em ordem crescente de capacidade — Linear → Ridge → KNN → Random Forest → XGBoost — para evidenciar quanto **ganho real** os modelos não-lineares trazem em relação ao baseline. Todos passam pelo mesmo pré-processamento (imputação por mediana e padronização quando o modelo é sensível a escala), garantindo comparabilidade.

---

## 4. Métricas

Para cada run foram logadas as métricas **MAE, RMSE, R² e MAPE**:

| Métrica | O que mede | Quando olhar |
|---|---|---|
| **MAE** (Mean Absolute Error) | Erro médio absoluto, na mesma unidade do alvo. | "Em média, erra X klx (light_comfort) ou X pontos do índice (env_quality)." |
| **RMSE** (Root MSE) | Penaliza erros grandes mais forte. | Sensibilidade a outliers de apartamentos atípicos. |
| **R²** (coeficiente de determinação) | Fração da variância do alvo explicada pelo modelo. | Métrica principal para **ranquear** modelos comparáveis. |
| **MAPE** | Erro percentual médio (com proteção contra y≈0). | Leitura de negócio: "errei X% da iluminação típica". |

O `ml/run_all.py` mostra o ranking por **R²** ao final.

---

## 5. Tracking — como o MLflow é usado

Cada execução do `ml/train.py` cria **uma run** dentro do experimento `home_swiss_home`, com:

- **Tags:** `target`, `model`, `dataset_version`, `source` (URI da Gold usada — local ou MinIO).
- **Parâmetros:** `target`, `model`, `dataset_version`, `test_size`, `random_state`, `n_features`, `n_train`, `n_test`, `n_rows_total` e os hiperparâmetros do estimador (`hp__*`).
- **Métricas:** `mae`, `rmse`, `r2`, `mape`.
- **Artefatos** (em `s3://mlflow/...`):
  - `dataset/feature_list.txt` — quais colunas viraram X (auditoria anti-vazamento).
  - `dataset/predictions_sample.csv` — 200 pares `(y_true, y_pred)` para inspeção visual.
  - `dataset/dataset_summary.json` — resumo da fonte/versão usada.
  - `model/` — o estimador serializado (flavor `mlflow.sklearn` ou `mlflow.xgboost`).
- **(Opcional) Model Registry:** com `--register-as <nome>` o modelo entra no Registry e fica versionado.

### Por que este desenho

1. **Reprodutibilidade:** são logados `dataset_version` + `source` + `random_state` em cada run. Dado o mesmo Parquet Gold, qualquer pessoa reproduz a métrica.
2. **Comparabilidade:** o experimento único `home_swiss_home` permite filtrar por `target` e ranquear por R² na UI do MLflow.
3. **Governança leve:** o `feature_list.txt` artefato comprova **quais colunas entraram em X**.

---

## 6. Execução da pipeline de treino

```powershell
# 1) Infra
docker compose up -d
# MLflow:  http://localhost:5000
# MinIO:   http://localhost:9001  (login: minio / minio123)

# 2) Garantir Gold
py -3.12 -m pip install -r requirements-pipeline.txt
py -3.12 -m pipeline.run_pipeline --max-rows 50000

# 3) Instalar deps de ML
py -3.12 -m pip install -r requirements-ml.txt

# 4) Rodar tudo (uma run MLflow por combinação)
py -3.12 -m ml.run_all

# 5) (Opcional) Treinar 1 modelo só
py -3.12 -m ml.train --target light_comfort --model xgb
py -3.12 -m ml.train --target env_quality   --model rf

# 6) (Opcional) Promover melhor modelo ao Registry
py -3.12 -m ml.train --target env_quality --model xgb --register-as home_swiss_env_quality
```

Saída esperada do `ml.run_all` (exemplo ilustrativo):

```text
=== Ranking por R² (maior melhor) ===
  R²=0.8612 | RMSE=0.0421 | MAE=0.0312 | env_quality   | xgb    | run=8a3f...
  R²=0.8401 | RMSE=0.0455 | MAE=0.0340 | env_quality   | rf     | run=2bd7...
  R²=0.7203 | RMSE=0.0581 | MAE=0.0440 | light_comfort | xgb    | run=44ac...
  ...
```

---

## 7. Mapeamento Sprint 4 (PDF) → entregáveis no repositório

| Item do PDF | Onde está |
|---|---|
| Definição do problema de ML | Seção 1 deste documento + [`docs/ML_DEFINICAO_ALVOS.md`](ML_DEFINICAO_ALVOS.md) |
| Seleção de modelos | Seção 3 + [`ml/registry.py`](../ml/registry.py) (`build_model_factories`) |
| Criação dos scripts de treinamento | [`ml/data.py`](../ml/data.py), [`ml/train.py`](../ml/train.py), [`ml/run_all.py`](../ml/run_all.py) |
| Integração com MLflow (tracking) | [`ml/registry.py`](../ml/registry.py) (`configure_mlflow`) + uso de `mlflow.log_*` em `ml/train.py` |
| **Entregável:** pipeline de treino funcional | `py -3.12 -m ml.run_all` |
| **Entregável:** experimentos registrados no MLflow | UI em `http://localhost:5000`, experimento `home_swiss_home` |

---

## 8. Riscos e decisões registradas

- **Vazamento de features:** mitigado por `feature_columns_for_*` em `pipeline/ml_targets.py`. Auditável via artefato `feature_list.txt` em cada run.
- **MAPE com y≈0:** o `_safe_mape` ignora amostras com `|y| < 1e-9` para evitar divisão por zero (especialmente relevante em `env_quality` quando algum apartamento cai em 0 após normalização).
- **Sem timeseries:** documentado e justificado (Seção 1.2). Se o dataset evoluir e ganhar `timestamp` por apartamento, abrir um Sprint adicional para LSTM/TCN.
- **Tamanho do dataset:** se a Gold for gerada com `--max-rows`, as métricas refletem **só essa amostra**. O nome da fonte no log MLflow (`source`) e `dataset_version` deixam isso explícito.

---

*Home Swiss Home — TAN1 — Sprint 4 (Modelagem e Treinamento + MLflow).*
