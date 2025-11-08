---
config:
  theme: redux
---
graph TD
    A["Início: Executar streamlit run HOME.py"] --> B{"Navegar no Menu Lateral"}

    B --> C1["Página: Downloader de Dados GEE"]
    C1 --> D1["Definir Área de Interesse (AOI)"]
    D1 --> E1["Selecionar Dados: MDE, Solo, Mapbiomas"]
    E1 --> F1["Processar e Baixar Dados do GEE"]
    F1 --> G1["Salvar Saídas em /cache"]

    B --> C2["Página: Análise Hidrológica"]
    C2 --> D2["Fazer Upload do MDE (GeoTIFF)"]
    D2 --> E2{"Executar Pré-processamento"}
    E2 --> F2["Preencher depressões (Fill Sinks)"]
    F2 --> G2["Corrigir fluxo (Resolve Flats)"]
    G2 --> H2["Calcular direção do fluxo (Flow Direction)"]
    H2 --> I2["Calcular acumulação do fluxo (Flow Accumulation)"]
    I2 --> J2["Extrair Rede de Drenagem"]
    J2 --> K2["Delinear Bacia Hidrográfica"]
    K2 --> L2["Calcular Mapa HAND"]
    L2 --> M2["Salvar Resultados"]

    B --> C3["Página: Modelo de Risco Ponderado por Solo"]
    C3 --> D3["Fazer Upload da Camada de Solo e Mancha de Inundação"]
    D3 --> E3["Aplicar Buffer Ponderado por Classe de Solo"]
    E3 --> F3["Gerar Mapa de Risco Ajustado"]
    F3 --> G3["Salvar Resultado"]

    B --> C4["Página: Downloader de Dados OSM"]
    C4 --> D4["Definir Área de Interesse (AOI)"]
    D4 --> E4["Selecionar Feições: Arruamento, Construções, etc."]
    E4 --> F4["Baixar Dados do OpenStreetMap via OSMnx"]
    F4 --> G4["Salvar Saídas Vetoriais"]

    B --> C5["Página: Downloader de Dados Open Buildings"]
    C5 --> D5["Definir Área de Interesse (AOI)"]
    D5 --> E5["Baixar Polígonos de Construções do Google"]
    E5 --> F5["Salvar Saídas Vetoriais"]

    B --> C6["Página: Análise Quantitativa"]
    C6 --> D6["Fazer Upload da Camada de Feições e da Camada de Análise"]
    D6 --> E6["Executar Interseção Espacial"]
    E6 --> F6["Calcular Estatísticas de Impacto (Contagem, %)"]
    F6 --> G6["Exibir Relatório de Resultados"]

    subgraph Fim
        direction LR
        G1 --_--> H_FIM["Fim"]
        M2 --_--> H_FIM["Fim"]
        G3 --_--> H_FIM["Fim"]
        G4 --_--> H_FIM["Fim"]
        F5 --_--> H_FIM["Fim"]
        G6 --_--> H_FIM["Fim"]
    end