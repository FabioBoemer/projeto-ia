# Projeto IA - RAC

## Tema
Arquitetura

Base de referência para dados:
[Awesome Public Datasets - Architecture](https://github.com/awesomedata/awesome-public-datasets?tab=readme-ov-file#architecture)

## Objetivo
Organizar o repositório do RAC para separar documentação, referências, dados, experimentos e código, facilitando o trabalho em grupo e a evolução do projeto.

## Estrutura do repositório

```text
projeto-ia/
|-- apresentacao/
|-- data/
|   |-- processed/
|   `-- raw/
|-- docs/
|-- entregas/
|-- notebooks/
|-- referencias/
|-- src/
|-- .gitignore
`-- readme.md
```

- `docs/`: atas, escopo, decisões e rascunhos do RAC.
- `entregas/`: versões finais para envio.
- `referencias/`: links, artigos, datasets e materiais de apoio.
- `data/raw/`: dados brutos, sem alteração.
- `data/processed/`: dados tratados para análise ou treinamento.
- `notebooks/`: exploração, testes e experimentos.
- `src/`: código reutilizável do projeto.
- `apresentacao/`: slides e materiais de apresentação.

## Fluxo de trabalho sugerido
1. Registrar alinhamentos e decisões em `docs/`.
2. Salvar referências e links úteis em `referencias/`.
3. Colocar dados originais em `data/raw/`.
4. Salvar versões tratadas em `data/processed/`.
5. Usar `notebooks/` para exploração inicial.
6. Mover rotinas reutilizáveis para `src/`.
7. Guardar slides em `apresentacao/` e arquivos finais em `entregas/`.

## Observações
- O `.gitignore` já foi preparado para evitar subir caches, ambientes virtuais, checkpoints de notebook e dados pesados por engano.
- Se o grupo definir Python como base principal, a estrutura atual já suporta notebooks e scripts sem precisar reorganizar o projeto.

## Grupo
- Bruno Bagatella
- Eduardo Henrique dos Santos de Souza Lima
- Fábio Boemer Figueira
- Gabriel Oliveira Ventura da Costa
- Gustavo Gonçalves Tuda
- João Antonio Tonollo da Silva
- João Vitor Fragoso de Camargo
- João Pedro Sanches Rodrigues
- Lucas Rogério do Couto
- Matheus Benite Disegna
- Vinícius Muniz Ferraz
- Sivaldo Castro Araújo Neto