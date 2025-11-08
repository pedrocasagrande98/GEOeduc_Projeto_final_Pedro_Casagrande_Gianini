# Descrição das Camadas de Dados

Este documento detalha as camadas de dados utilizadas e geradas pela Plataforma de Análise Geoespacial Integrada.

---

## 1. Camadas de Download (Fonte: GEE)

Estas camadas são baixadas através da página `Download de Dados GEE` e servem como insumos primários para as análises.

*   **Elevação - USGS/SRTMGL1_003**
    *   **Descrição:** Modelo Digital de Elevação (MDE) global com resolução de aproximadamente 30 metros. Representa a altitude da superfície terrestre. É a base para todas as análises hidrológicas.
    *   **Fonte:** NASA / USGS Shuttle Radar Topography Mission (SRTM).
    *   **Tipo:** Raster.

*   **Declividade - USGS/SRTMGL1_003**
    *   **Descrição:** Mapa de declividade do terreno, calculado em graus a partir do MDE SRTM. Indica a inclinação da superfície. É útil para análises de risco de deslizamento e para entender a velocidade do fluxo da água.
    *   **Fonte:** Derivado do SRTM.
    *   **Tipo:** Raster.

*   **Aspecto - USGS/SRTMGL1_003**
    *   **Descrição:** Representa a orientação da declividade do terreno (ex: face norte, sul, leste, oeste). É medido em graus de 0 a 360. Influencia a exposição solar, umidade do solo e padrões de vegetação.
    *   **Fonte:** Derivado do SRTM.
    *   **Tipo:** Raster.

*   **Uso e Cobertura do Solo (MapBiomas)**
    *   **Descrição:** Classificação anual do uso e cobertura do solo para o Brasil, com resolução de 30 metros. As classes incluem formações florestais, pastagens, agricultura, áreas urbanas, corpos d'água, etc.
    *   **Fonte:** Projeto MapBiomas.
    *   **Tipo:** Raster (Categórico).

*   **Solos (AD_Solos_30m) - EMBRAPA**
    *   **Descrição:** Mapa de classes de solo baseado na capacidade de infiltração e textura (arenoso vs. argiloso), com resolução de 30 metros. É um insumo crucial para o modelo de risco ponderado.
    *   **Fonte:** EMBRAPA (adaptado para o GEE).
    *   **Tipo:** Raster (Categórico).

---

## 2. Camadas Geradas (Análise Hidrológica)

Estas camadas são geradas na página `Análise Hidrológica Local` a partir de um MDE de entrada. A ordem segue o fluxo de processamento típico.

*   **MDE Condicionado (`filled_dem.tif`)**
    *   **Descrição:** Versão corrigida do MDE original, onde depressões espúrias (sinks) foram preenchidas e áreas planas (flats) foram resolvidas. 
    * Garante um fluxo hidrologicamente consistente através do terreno, sendo a base para os cálculos seguintes.
    *   **Tipo:** Raster.

*   **Declividade (`slope.tif`)**
    *   **Descrição:** Mapa que indica a inclinação do terreno em graus, calculado a partir do MDE condicionado. 
    * Essencial para entender a velocidade do escoamento superficial e para modelos de erosão.
    *   **Tipo:** Raster.

*   **Aspecto (`aspect.tif`)**
    *   **Descrição:** Representa a orientação da declividade do terreno (ex: face norte, sul, leste, oeste), medida em graus de 0 a 360. 
    * Influencia a exposição solar, umidade e vegetação.
    *   **Tipo:** Raster.

*   **Direção de Fluxo (`flow_direction.tif`)**
    *   **Descrição:** Raster que indica a direção para a qual a água fluirá de cada célula, com base na vizinhança de 8 células (método D8). 
    * É um passo intermediário crucial para determinar como a água se move na paisagem.
    *   **Tipo:** Raster (Categórico).

*   **Acumulação de Fluxo (`flow_accumulation.tif`)**
    *   **Descrição:** Raster onde o valor de cada célula representa o número total de células a montante que drenam para ela. 
    * Valores altos indicam a localização provável de canais de rios e vales.
    *   **Tipo:** Raster.

*   **Distância do Fluxo (`flow_distance.tif`)**
    *   **Descrição:** Raster que calcula, para cada célula, a distância horizontal ou vertical até o canal de drenagem mais próximo na rede fluvial. 
    * É um componente chave para o cálculo do HAND.
    *   **Tipo:** Raster.

*   **Índice Topográfico de Umidade (TWI - `twi.tif`)**
    *   **Descrição:** O 'Topographic Wetness Index' quantifica a tendência de uma área acumular água, com base na área de contribuição a montante e na declividade local.
    * Valores altos indicam áreas mais propensas à saturação hídrica (mais úmidas).
    *   **Tipo:** Raster.

*   **Rede de Drenagem (`canais_strahler.geojson`)**
    *   **Descrição:** Camada vetorial de linhas que representa a rede de drenagem (rios e córregos), extraída a partir de um limiar no mapa de acumulação de fluxo. 
    * Frequentemente classificada pela ordem de Strahler para hierarquizar os canais.
    *   **Tipo:** Vetor (Linhas).

*   **Bacia Hidrográfica (`bacia.geojson`)**
    *   **Descrição:** Polígono que delimita a área total de drenagem para um ponto de saída (exutório) específico. 
    * Todas as chuvas que caem dentro desta área contribuem para o fluxo no exutório.
    *   **Tipo:** Vetor (Polígono).

*   **Mapa HAND (`hand_map.tif`)**
    *   **Descrição:** 'Height Above Nearest Drainage' (Altura Acima da Drenagem Mais Próxima). 
    * É um mapa normalizado que mostra a elevação vertical de cada ponto do terreno em relação ao canal de drenagem mais próximo. 
    * É um excelente indicador de propensão à inundação.
    *   **Tipo:** Raster.

*   **Mancha de Inundação (`inundacao_mapa_Xm.tif`, `inundacao_Xm.geojson`)**
    *   **Descrição:** Representa a área inundada com base em uma profundidade de canal simulada. 
    * É gerada a partir do mapa HAND, mostrando todas as áreas com valor HAND menor ou igual à profundidade definida. Disponível em formato raster e vetor.
    *   **Tipo:** Raster e Vetor (Polígono).

---

## 3. Camadas Geradas (Modelo de Risco)

Estas camadas são o resultado do processo na página `Modelo de Risco Ponderado por Solo`.

*   **Inundação Segmentada por Solo (`inundacao_segmentada_por_solo.geojson`)**
    *   **Descrição:** Camada vetorial resultante da interseção entre a mancha de inundação e o mapa de solos. 
    * Cada polígono na mancha de inundação agora carrega a informação da classe de solo subjacente.
    *   **Tipo:** Vetor (Polígono).

*   **Inundação com Buffer Ponderado (`inundacao_adsolo_buffer.geojson`)**
    *   **Descrição:** O resultado final do modelo de risco. É uma mancha de inundação ajustada onde as bordas foram expandidas 
    * (buffer positivo) em áreas de solo com baixa infiltração (argiloso) e contraídas (buffer negativo) em áreas com alta infiltração (arenoso). Representa uma estimativa de risco mais refinada.
    *   **Tipo:** Vetor (Polígono).
