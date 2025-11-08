# 🛰️ Plataforma de Análise Geoespacial Integrada 🌎

## Descrição

Esta plataforma é uma aplicação web de análise geoespacial que integra diversas ferramentas de geoprocessamento e sensoriamento remoto. O objetivo principal é fornecer uma interface amigável para realizar análises hidrológicas, de risco e de impacto, utilizando dados de fontes como Google Earth Engine (GEE), OpenStreetMap (OSM) e Google Open Buildings. O projeto resolve a necessidade de uma ferramenta unificada para processar e analisar dados geoespaciais de múltiplas fontes, automatizando tarefas complexas e permitindo que usuários, mesmo sem profundo conhecimento em programação, possam realizar análises robustas.

## Fluxograma do Projeto

![Fluxograma do Projeto](Fluxograma/GEOEDUC-2025-11-08-000248.png)

## Principais Funcionalidades

*   **Delimitação de Bacias Hidrográficas**: A partir de um ponto de exutório definido pelo usuário, a plataforma delimita automaticamente a bacia hidrográfica correspondente.
*   **Cálculo do Índice HAND**: Processa o Modelo Digital de Elevação (MDE) para gerar o mapa de Altura Acima do Canal mais Próximo (HAND), essencial para modelagem de inundações.
*   **Análise de Risco e Impacto**: Identifica e quantifica feições (como construções e arruamentos) que estão dentro de áreas de risco, com base em uma cota de inundação definida pelo usuário.
*   **Integração de Dados**: Automatiza o download e a integração de dados de elevação (GEE), arruamento (OSM) e edificações (Open Buildings).
*   **Visualização Interativa**: Todos os resultados são exibidos em um mapa interativo, permitindo uma análise visual imediata.
*   **Exportação de Resultados**: Permite o download dos dados gerados (rasters e vetores) para uso em outros softwares de SIG.

## Pré-requisitos

As seguintes bibliotecas são necessárias para executar o projeto. Elas podem ser instaladas de uma vez com o arquivo `requirements.txt`.

*   earthengine-api
*   geemap
*   geopandas
*   numpy
*   osmnx
*   pandas
*   pyproj
*   pysheds
*   rasterio
*   requests
*   s2sphere
*   shapely
*   streamlit
*   tqdm

## Instalação

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_REPOSITORIO>
    cd 7_ENTREGA
    ```

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows, use `venv\Scripts\activate`
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

## Como Usar

Para um guia detalhado, consulte o arquivo `INSTRUCOES.txt`.

1.  **Execute a aplicação Streamlit:**
    ```bash
    streamlit run HOME.py
    ```

2.  **Acesse a aplicação no seu navegador:**
    Abra o endereço `http://localhost:8501`.

3.  **Navegue e utilize as funcionalidades:**
    *   Use o menu na barra lateral para selecionar a análise desejada (`Delimitar Bacia`, `Processar HAND`, `Análise de Risco`).
    *   Siga as instruções em cada página para fazer o upload dos seus dados e definir os parâmetros.
    *   Visualize e baixe os resultados diretamente na interface.

## Estrutura do Projeto

```
.
├── HOME.py                # Script principal da aplicação Streamlit (página inicial)
├── pages/                 # Diretório contendo os scripts de cada página/análise
│   ├── 1_Delimitar_Bacia.py
│   ├── 2_Processar_HAND.py
│   └── 3_Análise_de_Risco.py
├── scripts/               # Módulos com a lógica de processamento principal
│   └── ...
├── insumos/               # Documentação e explicação das camadas e processos
├── Fluxograma/            # Arquivo Mermaid.js e imagem PNG do fluxograma
├── INSTRUCOES.txt         # Tutorial passo a passo para o usuário final
├── readme.md              # Documentação geral do projeto (este arquivo)
└── requirements.txt       # Lista de dependências Python
```