import streamlit as st
import os
import tempfile
import time
import geopandas as gpd
import leafmap.foliumap as leafmap
from scripts.local_analysis_helpers import run_osmnx_download

st.set_page_config(
    page_title="🏙️ Downloader de Dados (OpenStreetMap)",
    page_icon="🛰️",
    layout="wide"
)

# Garante que o diretório de saída existe
OUTPUT_DIR = "outputs/4"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define o estilo CSS
st.markdown("""
    <style>
    html, body, [class*="st-"] {
        font-size: 1.1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stDownloadButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)


def display_osm_map(osm_results):
    """Exibe um mapa com as camadas OSM baixadas."""
    st.subheader("Visualização dos Dados Baixados")
    m = leafmap.Map()

    # Estilo para Polígonos
    style_polygons = {"color": "orange", "fillColor": "orange", "weight": 1, "fillOpacity": 0.4}

    # Estilos para Linhas (Borda e Núcleo)
    style_line_border = {"color": "white", "weight": 3.5, "opacity": 1}
    style_line_core = {"color": "gray", "weight": 1.5, "opacity": 1}

    # ESTILO ATUALIZADO PARA PONTOS: Círculo Verde
    style_points = {
        'radius': 8,  # Tamanho do círculo
        'color': 'white',  # Cor da borda
        'weight': 1,
        'fillColor': '#00FF00',  # Cor de preenchimento (verde)
        'fillOpacity': 0.8  # Transparência
    }

    if osm_results.get('polygons_path') and os.path.exists(osm_results['polygons_path']):
        gdf_polygons = gpd.read_file(osm_results['polygons_path'])
        if not gdf_polygons.empty:
            m.add_gdf(gdf_polygons, layer_name="Polígonos", style=style_polygons)

    if osm_results.get('lines_path') and os.path.exists(osm_results['lines_path']):
        gdf_lines = gpd.read_file(osm_results['lines_path'])
        if not gdf_lines.empty:
            m.add_gdf(gdf_lines, layer_name="Linhas (Borda)", style=style_line_border)
            m.add_gdf(gdf_lines, layer_name="Linhas (Núcleo)", style=style_line_core)

    # --- INÍCIO DA CORREÇÃO PARA ESTILO DE PONTOS ---
    if osm_results.get('points_path') and os.path.exists(osm_results['points_path']):
        gdf_points = gpd.read_file(osm_results['points_path'])
        if not gdf_points.empty:
            # Extrai coordenadas X e Y para usar a função correta
            gdf_points['lon'] = gdf_points.geometry.x
            gdf_points['lat'] = gdf_points.geometry.y
            
            # Usa add_points_from_xy para garantir a aplicação do estilo
            m.add_points_from_xy(
                gdf_points,
                x='lon',
                y='lat',
                layer_name="Pontos",
                color=style_points['color'],
                radius=style_points['radius'],
                fill_color=style_points['fillColor'],
                fill_opacity=style_points['fillOpacity'],
                weight=style_points['weight']
            )
    # --- FIM DA CORREÇÃO ---

    m.to_streamlit()


# --- STREAMLIT UI ---

st.info(
    "Faça upload de um arquivo vetorial (GeoJSON, GPKG, Shapefile .zip) contendo o polígono da sua área de interesse (AOI).")
st.warning("O processo usará o *limite total (envelope)* da sua AOI para baixar os dados do OSM.")

uploaded_aoi = st.file_uploader("Selecione o arquivo da AOI (.geojson, .gpkg, .zip)", type=["geojson", "gpkg", "zip"])

if st.button("Baixar Dados do OSM", type="primary"):
    if uploaded_aoi is not None:
        with tempfile.TemporaryDirectory() as temp_dir:
            aoi_temp_path = os.path.join(temp_dir, uploaded_aoi.name)
            with open(aoi_temp_path, "wb") as f:
                f.write(uploaded_aoi.getbuffer())

            st.info(f"Arquivo AOI '{uploaded_aoi.name}' carregado.")

            progress_bar = st.progress(0, text="Iniciando download do OSM...")
            status_text = st.empty()


            def update_progress(message, percentage):
                status_text.info(message)
                progress_bar.progress(percentage, text=message)
                time.sleep(0.1)


            try:
                with st.spinner("Baixando e processando dados do OpenStreetMap..."):
                    osm_results = run_osmnx_download(aoi_temp_path, OUTPUT_DIR, update_progress)

                progress_bar.progress(100, text="Download concluído!")
                status_text.success("Dados do OSM baixados e processados!")

                st.subheader("Resultados para Download")
                st.markdown(f"Arquivos salvos no diretório `{OUTPUT_DIR}`.")

                col1, col2, col3 = st.columns(3)

                if osm_results.get('polygons_path'):
                    with open(osm_results['polygons_path'], "rb") as f:
                        col1.download_button("Baixar Polígonos (osm_polygons.gpkg)", f, file_name="osm_polygons.gpkg")
                else:
                    col1.info("Nenhum polígono encontrado.")

                if osm_results.get('lines_path'):
                    with open(osm_results['lines_path'], "rb") as f:
                        col2.download_button("Baixar Linhas (osm_lines.gpkg)", f, file_name="osm_lines.gpkg")
                else:
                    col2.info("Nenhuma linha encontrada.")

                if osm_results.get('points_path'):
                    with open(osm_results['points_path'], "rb") as f:
                        col3.download_button("Baixar Pontos (osm_points.gpkg)", f, file_name="osm_points.gpkg")
                else:
                    col3.info("Nenhum ponto encontrado.")

                # Exibe o mapa com os resultados
                display_osm_map(osm_results)

            except Exception as e:
                st.error(f"Erro durante o download do OSM: {e}")
                st.exception(e)
    else:
        st.warning("Por favor, faça o upload de um arquivo de AOI.")