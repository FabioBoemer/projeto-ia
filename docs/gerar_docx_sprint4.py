"""Gera um DOCX de defesa do Sprint 4 sem depender de python-docx.

O arquivo gerado pode ser aberto no Microsoft Word, Google Docs ou LibreOffice.
"""
from __future__ import annotations

import html
import zipfile
from pathlib import Path


OUT = Path(__file__).resolve().parent / "Sprint4_Modelagem_MLflow_Defesa.docx"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def p(text: str = "", style: str | None = None) -> str:
    style_xml = ""
    if style:
        style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
    return f"<w:p>{style_xml}<w:r><w:t>{esc(text)}</w:t></w:r></w:p>"


def bullet(text: str) -> str:
    return p("• " + text)


def table(rows: list[list[str]]) -> str:
    grid = "".join("<w:gridCol w:w=\"2400\"/>" for _ in rows[0])
    body = []
    for row in rows:
        cells = []
        for cell in row:
            cells.append(
                "<w:tc>"
                "<w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
                f"{p(cell)}"
                "</w:tc>"
            )
        body.append("<w:tr>" + "".join(cells) + "</w:tr>")
    return (
        "<w:tbl>"
        "<w:tblPr><w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "</w:tblBorders></w:tblPr>"
        f"<w:tblGrid>{grid}</w:tblGrid>"
        + "".join(body)
        + "</w:tbl>"
    )


def document_xml() -> str:
    parts: list[str] = []

    parts.append(p("Sprint 4 - Modelagem, Treinamento e MLflow", "Title"))
    parts.append(p("Projeto: Home Swiss Home - FACENS - TAN1"))
    parts.append(p("Tema: Arquitetura / Swiss Dwellings / Pipeline Medallion + Machine Learning"))
    parts.append(p(""))

    parts.append(p("1. Objetivo do Sprint 4", "Heading1"))
    parts.append(
        p(
            "O Sprint 4 tem como objetivo transformar a camada Gold do pipeline Medallion "
            "em um pipeline de treino funcional, com seleção de modelos, avaliação por "
            "métricas e registro completo de experimentos no MLflow."
        )
    )
    parts.append(
        table(
            [
                ["Item do PDF", "Entrega implementada"],
                ["Definição do problema de ML", "Regressão tabular sobre apartamentos"],
                ["Seleção de modelos", "Linear, Ridge, KNN, Random Forest e XGBoost"],
                ["Scripts de treinamento", "ml/data.py, ml/train.py e ml/run_all.py"],
                ["Integração com MLflow", "Experimento home_swiss_home, runs, métricas, tags, artefatos e Logged Models"],
                ["Entregável final", "Pipeline funcional + Model Registry com os melhores modelos"],
            ]
        )
    )

    parts.append(p("2. Origem dos dados", "Heading1"))
    parts.append(
        p(
            "Os dados vêm do dataset Swiss Dwellings, publicado no Zenodo, registro 7070952, "
            "DOI 10.5281/zenodo.7070952, licença CC-BY-4.0. O projeto utiliza dois arquivos "
            "principais: geometries.csv e simulations.csv."
        )
    )
    parts.append(bullet("geometries.csv: uma linha por entidade geométrica do apartamento, com geometria em WKT."))
    parts.append(bullet("simulations.csv: uma linha por área, com métricas de sol, ruído, vista, conectividade e layout."))
    parts.append(
        p(
            "Esses dados brutos passam por uma arquitetura Medallion: Bronze, Silver e Gold. "
            "A camada Gold, arquivo apartment_kpis.parquet, é a entrada oficial do treinamento."
        )
    )

    parts.append(p("3. Pipeline Medallion usado antes do treino", "Heading1"))
    parts.append(
        table(
            [
                ["Camada", "Função", "Arquivo gerado"],
                ["Bronze", "Cópia fiel dos CSVs brutos no MinIO, com manifest.json e SHA-256", "bronze/<versão>/"],
                ["Silver", "Dados limpos, tipados e integrados por apartment_id e area_id", "silver/<versão>/area_features.parquet"],
                ["Gold", "Agregação por apartamento com médias das famílias numéricas", "gold/<versão>/apartment_kpis.parquet"],
            ]
        )
    )
    parts.append(
        p(
            "A Gold possui uma linha por apartamento. No experimento executado foram usados "
            "42.207 apartamentos, divididos em 33.765 para treino e 8.442 para teste."
        )
    )

    parts.append(p("4. Por que o problema é regressão?", "Heading1"))
    parts.append(
        p(
            "O problema foi definido como regressão porque os alvos são valores contínuos. "
            "O target_light_comfort representa uma média de iluminação simulada, enquanto "
            "o target_env_quality é um índice numérico entre 0 e 1."
        )
    )
    parts.append(
        table(
            [
                ["Tipo de ML", "Decisão", "Justificativa"],
                ["Regressão", "Escolhido", "Os alvos são números reais contínuos."],
                ["Classificação", "Descartado", "Não há rótulo categórico original; binarizar criaria corte arbitrário."],
                ["Série temporal", "Descartado", "A Gold tem uma linha por apartamento e não possui timestamp."],
            ]
        )
    )
    parts.append(
        p(
            "Frase de defesa: definimos regressão tabular porque cada observação é um apartamento "
            "e os alvos são contínuos. LSTM e TCN foram descartados por ausência de eixo temporal."
        )
    )

    parts.append(p("5. Alvos de Machine Learning", "Heading1"))
    parts.append(p("5.1 target_light_comfort", "Heading2"))
    parts.append(
        p(
            "O target_light_comfort é calculado como a média de todas as colunas avg__sun_* "
            "da camada Gold. Quanto maior o valor, maior a exposição luminosa média simulada."
        )
    )
    parts.append(p("5.2 target_env_quality", "Heading2"))
    parts.append(
        p(
            "O target_env_quality é um índice composto entre 0 e 1. Ele combina três dimensões: "
            "luz, vista e ruído. Luz e vista aumentam o índice; ruído é invertido, pois menor "
            "ruído significa maior qualidade ambiental."
        )
    )
    parts.append(
        p(
            "A fórmula conceitual é: env_quality_score = (L + V + N_inv) / 3, onde L é luz "
            "normalizada, V é vista normalizada e N_inv é 1 menos o ruído normalizado."
        )
    )

    parts.append(p("6. Anti-vazamento de dados", "Heading1"))
    parts.append(
        p(
            "Um ponto crítico do projeto é impedir vazamento de features. Se o modelo usasse "
            "avg__sun_* para prever target_light_comfort, ele estaria vendo diretamente o que "
            "compõe o alvo. Por isso pipeline/ml_targets.py remove essas colunas de X."
        )
    )
    parts.append(
        table(
            [
                ["Alvo", "Famílias bloqueadas em X", "Motivo"],
                ["target_light_comfort", "avg__sun_*", "Sol compõe diretamente o alvo de luz."],
                ["target_env_quality", "avg__sun_*, avg__view_*, avg__noise_*", "Luz, vista e ruído compõem diretamente o índice."],
            ]
        )
    )
    parts.append(
        p(
            "Além disso, cada run do MLflow recebe o artefato feature_list.txt, permitindo auditar "
            "quais colunas entraram no treinamento."
        )
    )

    parts.append(p("7. Por que cada modelo foi escolhido?", "Heading1"))
    parts.append(
        table(
            [
                ["Modelo", "Por que foi escolhido", "Papel na comparação"],
                ["LinearRegression", "Modelo simples e interpretável, serve como baseline.", "Mostra o desempenho mínimo esperado."],
                ["Ridge", "Linear com regularização L2, útil com colunas correlacionadas.", "Testa se regularização melhora estabilidade."],
                ["KNN", "Modelo não-paramétrico baseado em vizinhança.", "Captura padrões locais sem assumir forma linear."],
                ["RandomForest", "Conjunto de árvores robusto a não-linearidades e interações.", "Bom modelo forte para tabular."],
                ["XGBoost", "Booster de árvores, estado da arte em dados tabulares e citado no enunciado.", "Modelo de maior capacidade preditiva."],
            ]
        )
    )
    parts.append(
        p(
            "A lógica da seleção foi comparar modelos em ordem crescente de capacidade: Linear, "
            "Ridge, KNN, Random Forest e XGBoost. Assim, conseguimos mostrar se a complexidade "
            "extra realmente gera ganho sobre um baseline simples."
        )
    )

    parts.append(p("8. Como o treinamento funciona", "Heading1"))
    parts.append(bullet("ml/data.py localiza a Gold: primeiro GOLD_PARQUET, depois caminhos locais, depois MinIO."))
    parts.append(bullet("add_ml_targets cria os alvos target_light_comfort e target_env_quality."))
    parts.append(bullet("feature_columns_for_* monta X sem colunas que vazam informação do alvo."))
    parts.append(bullet("train_test_split separa 80% treino e 20% teste, com random_state=42."))
    parts.append(bullet("Cada modelo é um Pipeline com SimpleImputer e, quando necessário, StandardScaler."))
    parts.append(bullet("ml/train.py treina um modelo e cria uma run no MLflow."))
    parts.append(bullet("ml/run_all.py roda todos os modelos para os dois alvos e imprime o ranking por R²."))

    parts.append(p("9. Pré-processamento", "Heading1"))
    parts.append(
        p(
            "O SimpleImputer(strategy='median') foi escolhido porque algumas features podem ter "
            "valores ausentes. A mediana é mais robusta do que a média em presença de outliers. "
            "O StandardScaler é aplicado em modelos sensíveis à escala, como Linear, Ridge e KNN. "
            "Árvores como RandomForest e XGBoost não precisam de padronização para funcionar bem."
        )
    )

    parts.append(p("10. Métricas usadas", "Heading1"))
    parts.append(
        table(
            [
                ["Métrica", "O que mede", "Por que usamos"],
                ["MAE", "Erro absoluto médio", "Fácil de explicar na unidade do alvo."],
                ["RMSE", "Erro quadrático médio com raiz", "Penaliza mais erros grandes."],
                ["R²", "Variância explicada pelo modelo", "Principal métrica para ranquear modelos."],
                ["MAPE", "Erro percentual médio", "Ajuda na leitura de negócio."],
            ]
        )
    )

    parts.append(p("11. Integração com MLflow", "Heading1"))
    parts.append(
        p(
            "Cada execução de treino cria uma run no experimento home_swiss_home. O MLflow registra "
            "tags, parâmetros, métricas, artefatos de dataset e o modelo serializado como Logged Model."
        )
    )
    parts.append(bullet("Tags: target, model, dataset_version e source."))
    parts.append(bullet("Parâmetros: alvo, modelo, versão do dataset, tamanho de treino/teste, número de features e hiperparâmetros."))
    parts.append(bullet("Métricas: MAE, RMSE, R² e MAPE."))
    parts.append(bullet("Artefatos: feature_list.txt, predictions_sample.csv e dataset_summary.json."))
    parts.append(bullet("Modelos: salvos como Logged Models no MinIO e registrados no Model Registry."))

    parts.append(p("12. Resultados obtidos", "Heading1"))
    parts.append(
        table(
            [
                ["Alvo", "Melhor modelo", "R²", "RMSE", "MAE", "Interpretação"],
                ["light_comfort", "XGBoost", "0.9759", "0.1033", "0.0751", "Excelente previsibilidade."],
                ["env_quality", "RandomForest", "0.7429", "0.0295", "0.0200", "Boa previsibilidade, problema mais difícil."],
            ]
        )
    )
    parts.append(
        p(
            "O alvo light_comfort teve desempenho muito alto porque há várias features correlacionadas "
            "com conforto de luz mesmo após remover avg__sun_*. Já env_quality é mais difícil porque "
            "as famílias que compõem o índice foram bloqueadas, restando conectividade, layout, ruído "
            "de janela e contagem de áreas."
        )
    )

    parts.append(p("13. Model Registry", "Heading1"))
    parts.append(
        p(
            "Após o treinamento, os melhores modelos foram promovidos ao Model Registry do MLflow:"
        )
    )
    parts.append(bullet("home_swiss_light_comfort v1: XGBoost, R² = 0.9759."))
    parts.append(bullet("home_swiss_env_quality v1: RandomForest, R² = 0.7429."))
    parts.append(
        p(
            "Isso mostra maturidade de MLOps: o projeto não apenas treina modelos, mas também "
            "versiona os melhores candidatos para uso futuro."
        )
    )

    parts.append(p("14. Como reproduzir", "Heading1"))
    parts.append(p("Comandos principais:"))
    parts.append(p("docker compose up -d"))
    parts.append(p("py -3.12 -m pip install -r requirements-pipeline.txt -r requirements-ml.txt"))
    parts.append(p("py -3.12 -m pipeline.run_pipeline --max-rows 50000"))
    parts.append(p("py -3.12 -m ml.run_all"))
    parts.append(p("py -3.12 docs\\promote_best.py"))

    parts.append(p("15. Resumo executivo para apresentação", "Heading1"))
    parts.append(
        p(
            "Construímos sobre a Gold do Sprint 3 dois alvos de regressão, comparamos cinco "
            "modelos em ordem crescente de capacidade, registramos cada experimento no MLflow "
            "com tags, parâmetros, métricas e artefatos auditáveis, e promovemos os dois melhores "
            "ao Model Registry: XGBoost para luz e Random Forest para qualidade ambiental."
        )
    )

    body = "".join(parts)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:rPr><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="table" w:styleId="TableGrid">
    <w:name w:val="Table Grid"/>
    <w:tblPr>
      <w:tblBorders>
        <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        <w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      </w:tblBorders>
    </w:tblPr>
  </w:style>
</w:styles>
"""


def write_docx() -> None:
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
""",
        )
        z.writestr(
            "word/_rels/document.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>
""",
        )
        z.writestr("word/document.xml", document_xml())
        z.writestr("word/styles.xml", styles_xml())


if __name__ == "__main__":
    write_docx()
    print(OUT)
