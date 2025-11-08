import streamlit as st

st.set_page_config(

    page_title="🌎 Análise Geoespacial Integrada",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ Análise Geoespacial Integrada - Inundação + tipo do solo + impacto urbano 🌎")
st.markdown("---")
st.markdown("Bem-vindo à Plataforma de Análise Geoespacial. Esta aplicação integra ferramentas de geoprocessamento e sensoriamento remoto para análises hidrológicas, de risco e de impacto.")
st.markdown("### Como usar:")
st.info("""
1.  **Navegue para a página desejada no menu lateral.**
2.  **Siga as instruções específicas de cada página para fazer upload dos seus dados (GeoJSON, GPKG, Shapefile, GeoTIFF, etc.).**
3.  **Ajuste os parâmetros, se necessário, e inicie o processamento.**
4.  **Os resultados serão disponibilizados para visualização e download ao final de cada processo.**
""")

st.markdown("### Páginas disponíveis:")
st.markdown("""
*   **`Downloader de Dados (GEE)`**: Baixe dados MDE (elevação, declividade, aspecto) , Água disponível no solo e Mapbiomas para [area uma área de interesse específica.

*   **`Análise Hidrológica`**: Execute o pré-processamento de Modelos Digitais de Elevação (MDE), delineie bacias hidrográficas e calcule o mapa de altura acima do canal mais próximo (HAND).

*   **`Modelo de Risco Ponderado por Solo`**: Aplique um modelo de risco que ajusta áreas de inundação com base em diferentes classes de solo, aplicando buffers proporcionais.

*   **`Downloader de Dados (OSM)`**: Baixe dados de arruamento, construções e outras feições do OpenStreetMap para uma área de interesse específica.

*   **`Downloader de Dados (Open Buildings)`**: Baixe dados de construções do projeto Google Open Buildings para a sua área de interesse.

*   **`Análise Quantitativa`**: Calcule estatísticas de impacto, como a contagem e a porcentagem de feições de uma camada que são interceptadas por outra.
""")
st.markdown("---")
# st.image("https://i.imgur.com/rztB5pr.png", caption="Visualização da Bacia Hidrográfica e Rede de Drenagem")

st.markdown("""
    <style>
    html, body, [class*="st-"] {
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)
