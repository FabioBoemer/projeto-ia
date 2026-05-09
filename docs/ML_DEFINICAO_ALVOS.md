# Definição dos alvos de ML — conforto de luz e qualidade ambiental

- **Conforto de luz:** A média aritmética de todas as variáveis `avg__sun_*` disponíveis na camada Gold por apartamento, refletindo o padrão médio de iluminação simulada (klx) ao longo dos cenários do Swiss Dwellings.

- **Qualidade ambiental:** Um índice composto entre 0 e 1 combinando, com pesos iguais, a luminosidade média, a visibilidade média (`view_*`) e o ruído médio em área (`noise_*`), após normalização min–max e inversão do ruído para que valores menores de dBA aumentem o índice.

As definições abaixo batem com o código em [`pipeline/ml_targets.py`](../pipeline/ml_targets.py).

**Fonte dos dados:** camada **Gold** `apartment_kpis.parquet` (uma linha por `apartment_id`, colunas `avg__*` vindas da média por apartamento na Silver).

**Referência do dataset:** Swiss Dwellings, Zenodo [7070952](https://zenodo.org/records/7070952), DOI [10.5281/zenodo.7070952](https://doi.org/10.5281/zenodo.7070952). Unidades típicas: sol em **kilolux (klx)** (simulações `sun_*`), ruído em **dBA** (`noise_*`), vista em **esterradianos** (`view_*`).

---

## 1. Conforto de luz (`light_comfort` / `target_light_comfort`)

### Conceito
Indicador **por apartamento** de exposição luminosa média ao longo dos cenários de simulação disponíveis na Gold.

### Definição operacional
\[
\text{light\_comfort}_i = \frac{1}{|S_i|}\sum_{c \in S_i} x_{i,c}
\]

onde:
- \(i\) é o apartamento,
- \(S_i\) é o conjunto de colunas da linha \(i\) cujo nome começa com **`avg__sun_`** (ou seja, todas as métricas de sol já agregadas em nível de apartamento),
- \(x_{i,c}\) é o valor numérico nessa coluna.

### Interpretação
Quanto **maior** o valor (em média aritmética das colunas de sol), maior o **conforto de luz** segundo o conjunto de instantes/angulações que o dataset Swiss Dwellings já consolidou em `sun_*`.

### Regressão sugerida
- **Alvo:** `target_light_comfort` (= `light_comfort`).
- **Features (`X`):** colunas numéricas da Gold **exceto** `apartment_id`, os alvos derivados e **todas** as colunas `avg__sun_*` (evita vazamento: não prever sol usando o próprio sol).
- **Features típicas:** `avg__noise_*`, `avg__view_*`, `avg__connectivity_*`, `avg__layout_*`, `avg__window_noise_*`, `n_areas_in_sample`, etc.

---

## 2. Qualidade ambiental (`env_quality_score` / `target_env_quality`)

### Conceito
Índice **composto** em escala aproximada **\[0, 1\]**, alinhado a três dimensões: **luz** (quanto melhor, maior), **vista** (maior visibilidade de paisagem/elementos desejáveis, maior), **ruído de área** (quanto menor o dBA médio, melhor).

### Passos (implementação)
1. **Luz:** mesma série `light_comfort` (seção 1).
2. **Vista:** média das colunas **`avg__view_*`** na linha (se não houver colunas, usa 0).
3. **Ruído:** média das colunas **`avg__noise_*`** na linha (ruído propagado na área; não incluímos aqui `avg__window_noise_*` para não duplicar família — opcional evoluir no trabalho).
4. **Normalização global (min–max) por componente** em todo o conjunto de apartamentos:
   - \(L = \mathrm{norm}(\text{light\_comfort})\)
   - \(V = \mathrm{norm}(\text{vista\_média})\)
   - \(N_{\mathrm{inv}} = 1 - \mathrm{norm}(\text{ruído\_médio})\) (inverte para que **menos ruído** aumente o índice)
5. **Score:**
   \[
   \text{env\_quality\_score} = \frac{L + V + N_{\mathrm{inv}}}{3}
   \]

Se min = max em uma série, a normalização devolve **0,5** constante naquele componente (evita divisão por zero).

### Interpretação
Valores **mais altos** indicam combinação relativamente melhor de **luz, vista e baixo ruído** dentro da amostra analisada. É **relativo** ao conjunto de apartamentos do Parquet (não é um índice absoluto oficial do Zenodo).

### Regressão sugerida
- **Alvo:** `target_env_quality` (= `env_quality_score`).
- **Features (`X`):** colunas numéricas **exceto** identificadores/alvos e **sem** `avg__sun_*`, `avg__view_*` e `avg__noise_*` — porque essas famílias **entram direto** no cálculo do índice; usar como feature seria **vazamento** (o modelo “veria” o que compõe o alvo).
- **Features típicas:** `avg__connectivity_*`, `avg__layout_*`, `avg__window_noise_*`, `n_areas_in_sample`, etc.

---

## 3. Uso rápido no Python

```python
import pandas as pd
from pipeline.ml_targets import add_ml_targets, feature_columns_for_light_comfort, feature_columns_for_env_quality

df = pd.read_parquet("apartment_kpis.parquet")  # ou caminho local após download do MinIO
df = add_ml_targets(df)

# Regressão: conforto de luz
y = df["target_light_comfort"]
X = df[feature_columns_for_light_comfort(df)]

# Regressão: qualidade ambiental
y2 = df["target_env_quality"]
X2 = df[feature_columns_for_env_quality(df)]
```

---
