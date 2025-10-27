# Projeto de Análise Geoespacial

Este projeto consiste em uma série de módulos para análise de dados geoespaciais, utilizando o Google Earth Engine (GEE) e uma interface interativa construída com Streamlit.

---

## MÓDULO 1: Análise de MDE e Uso do Solo

O Módulo 1 é a fundação do projeto, uma aplicação web que permite a visualização e o download de dados de Modelo Digital de Elevação (MDE) e Uso e Cobertura do Solo (LULC) diretamente do catálogo do Google Earth Engine.

### Funcionalidades Principais

- **Interface Interativa**: Construída com Streamlit, a interface permite que o usuário controle os dados a serem processados e visualizados de forma simples e intuitiva.
- **Upload de Área de Interesse (AOI)**: O usuário pode carregar sua própria área de estudo nos formatos `.gpkg` ou `.geojson`.
- **Seleção de Dados**: Estão disponíveis para análise as seguintes camadas:
  - **Elevação**: Modelo Digital de Elevação (SRTM).
  - **Declividade**: Calculada em graus a partir do MDE.
  - **Aspecto (Hillshade)**: Visualização de relevo sombreado para melhor percepção de profundidade.
  - **Uso e Cobertura do Solo**: Dados anuais do MapBiomas Brasil (Coleção 9).
- **Visualização Dinâmica e Personalizada**:
  - **Renderização Assertiva**: Para as camadas de **Elevação** e **Declividade**, a paleta de cores é ajustada dinamicamente com base nos valores mínimo e máximo encontrados **dentro da área de interesse do usuário**. Isso garante que a visualização sempre utilize 100% da escala de cores, proporcionando o máximo de detalhe, independentemente da localização geográfica (seja uma planície ou uma cadeia de montanhas).
  - **Seleção de Paletas**: O usuário pode escolher diferentes paletas de cores para as camadas de Elevação (`terrain`, `viridis`, `inferno`, `gist_earth`) e Declividade (`Padrão`, `Reds`, `plasma`), permitindo análises visuais distintas.
  - **Legenda Oficial MapBiomas**: A camada de Uso e Cobertura do Solo é renderizada utilizando a paleta de cores oficial do projeto MapBiomas, garantindo a correta interpretação das classes.
- **Layout Flexível**: A interface possui uma barra lateral recolhível e um controle para ajustar a altura do mapa, permitindo que o usuário otimize o espaço de visualização em diferentes tamanhos de tela.

### Requisitos

Para utilizar a aplicação, é necessário atender aos seguintes requisitos:

1.  **Conta no Google Earth Engine**: É preciso ter uma conta ativa no GEE.
2.  **Projeto GEE**: A conta deve estar associada a um projeto na Google Cloud Platform. O nome do projeto deve seguir o padrão `ee-SEU_USER_ID`.
3.  **Autenticação**: O usuário precisa estar autenticado no GEE em sua máquina local. Caso não esteja, deve executar o seguinte comando no terminal e seguir as instruções:
    ```bash
    earthengine authenticate
    ```

### Limitações e Recomendações

- **Download Direto vs. Exportação para Google Drive**:
  - A opção **"Baixar Direto"** é ideal para áreas pequenas e processamentos simples (como a camada de Elevação).
  - Para áreas grandes ou processamentos computacionalmente intensivos (como Declividade, Aspecto ou MapBiomas), a solicitação pode exceder o tempo limite do GEE, resultando em um erro de "Computation timed out".
  - **Recomendação**: Para garantir o sucesso da exportação em todos os casos, utilize a opção **"Exportar para Google Drive"**. Ela inicia uma tarefa em segundo plano nos servidores do Google, que é mais robusta e não possui tempo limite.

### Como Executar o Módulo 1

1.  Clone ou baixe este repositório.
2.  Instale as dependências necessárias:
    ```bash
    pip install -r requirements.txt
    ```
3.  Execute o aplicativo Streamlit:
    ```bash
    streamlit run scripts/MDE_LULC.py
    ```
