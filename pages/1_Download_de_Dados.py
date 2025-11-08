import streamlit as st
import geopandas as gpd
import ee
import geemap.foliumap as geemap
import requests
import os
# Importa as funções do novo módulo de scripts
from streamlit_vertical_slider import vertical_slider
from scripts.gee_helpers import initialize_earth_engine, download_image_ano, export_to_drive

st.set_page_config(
    page_title="Download de Dados GEE",  # Você pode customizar o título para cada página
    page_icon="🛰️",                     # Mantenha o mesmo ícone
    layout="wide"                      # E o mesmo layout
)


#st.title("Download de Dados Geoespaciais")

st.markdown("""
    <style>
    html, body, [class*="st-"] {
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

with st.expander("Controles para Download de dados", expanded=True):
    user_id = st.text_input("Seu User ID do Google Earth Engine:",
                            help="Seu projeto GEE deve ter o nome 'ee-SEU_USER_ID'")
    uploaded_gpkg = st.file_uploader("Upload de arquivo GPKG/GeoJSON", type=["gpkg", "geojson"])

if user_id and uploaded_gpkg:
    if initialize_earth_engine(user_id):
        gdf = gpd.read_file(uploaded_gpkg)
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)

        AOI = ee.FeatureCollection(gdf.__geo_interface__)
        clip_geometry = AOI.geometry().bounds()

        data_type = st.selectbox("Escolha o tipo de dado:",
                                 ["Elevação - USGS/SRTMGL1_003", "Declividade - USGS/SRTMGL1_003", "Aspecto - USGS/SRTMGL1_003",
                                  "Uso e Cobertura do Solo (MapBiomas)",
                                  "Solos (AD_Solos_30m) - EMBRAPA"])

        image_to_process = None
        vis_params = {}
        scale = 30  # Define uma escala padrão

        if data_type == "Elevação - USGS/SRTMGL1_003":
            elevation_palette = st.selectbox("Paleta de Cores (Elevação - USGS/SRTMGL1_003):",
                                             ['terrain', 'viridis', 'inferno', 'gist_earth'])
            image_to_process = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(clip_geometry)
            stats = image_to_process.reduceRegion(reducer=ee.Reducer.minMax(), geometry=clip_geometry, scale=30,
                                                  maxPixels=1e9).getInfo()
            vis_params = {'min': stats['elevation_min'], 'max': stats['elevation_max'], 'palette': elevation_palette}
            # scale continua 30

        elif data_type == "Declividade - USGS/SRTMGL1_003":
            slope_palette_name = st.selectbox("Paleta de Cores (Declividade - USGS/SRTMGL1_003):",
                                              ['Padrão (Verde-Amarelo-Vermelho)', 'Reds', 'plasma'])
            slope_palettes = {
                'Padrão (Verde-Amarelo-Vermelho)': ['#4CAF50', '#FFF176', '#FF7043', '#E53935'],
                'Reds': 'Reds',
                'plasma': 'plasma'
            }
            elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
            image_to_process = ee.Terrain.slope(elevation).clip(clip_geometry)
            stats = image_to_process.reduceRegion(reducer=ee.Reducer.minMax(), geometry=clip_geometry, scale=30,
                                                  maxPixels=1e9).getInfo()
            vis_params = {'min': stats['slope_min'], 'max': stats['slope_max'],
                          'palette': slope_palettes[slope_palette_name]}
            # scale continua 30

        elif data_type == "Aspecto - USGS/SRTMGL1_003":
            elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
            image_to_process = ee.Terrain.hillshade(elevation).clip(clip_geometry)
            vis_params = {}
            # scale continua 30

        elif data_type == "Uso e Cobertura do Solo (MapBiomas)":
            mapbiomas_color_map = {"1": "#1f8d49", "3": "#1f8d49", "4": "#7dc975", "5": "#04381d", "6": "#026975",
                                   "9": "#7a5900", "10": "#ad975a", "11": "#519799", "12": "#d6bc74", "14": "#FFFFB2",
                                   "15": "#edde8e", "18": "#E974ED", "19": "#C27BA0", "20": "#db7093", "21": "#ffefc3",
                                   "22": "#d4271e", "23": "#ffa07a", "24": "#d4271e", "25": "#db4d4f", "26": "#0000FF",
                                   "27": "#ffffff", "29": "#ffaa5f", "30": "#9c0027", "31": "#091077", "32": "#fc8114",
                                   "33": "#2532e4", "35": "#9065d0", "36": "#d082de", "39": "#f5b3c8", "40": "#c71585",
                                   "41": "#f54ca9", "46": "#d68fe2", "47": "#9932cc", "48": "#e6ccff", "49": "#02d659",
                                   "50": "#ad5100", "62": "#ff69b4"}
            max_id = max([int(k) for k in mapbiomas_color_map.keys()])
            min_id = 0
            full_palette = [mapbiomas_color_map.get(str(i), '00000000').replace('#', '') for i in
                            range(min_id, max_id + 1)]
            vis_params = {'min': min_id, 'max': max_id, 'palette': full_palette}
            selected_year = st.slider("Ano (MapBiomas):", 1985, 2023, 2023)
            band_name = f'classification_{selected_year}'
            image_to_process = ee.Image(
                f'projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1').select(
                band_name).clip(clip_geometry)
            # scale continua 30

        # --- INÍCIO DO BLOCO MODIFICADO ---
        elif data_type == "Solos (AD_Solos_30m) - EMBRAPA":
            image_to_process = ee.Image("projects/ee-phccasagrande20/assets/AD_Solos_30m_EMBRAPA").clip(clip_geometry)

            # Tenta obter a escala nativa
            try:
                native_projection = image_to_process.projection()
                scale = native_projection.nominalScale().getInfo()
                st.info(f"Usando escala nativa do asset: {scale:.2f} metros.")
            except Exception as e:
                st.warning(f"Não foi possível obter escala nativa, usando 30m (padrão). Erro: {e}")
                scale = 30  # Fallback

            # --- PALETA DE CORES ORIGINAL ---
            soil_palette = [
                '#5c2714',  # 1 - Argiloso Saturado
                '#ab4a27',  # 2 - Argiloso Médio
                '#f27244',  # 3 - Argiloso Baixo
                '#f2a65e',  # 4 - Arenoso Baixo
                '#f5d473',  # 5 - Arenoso Médio
                '#f0db9e',  # 6 - Arenoso Alto
                '#CCCCCC',  # 7 - Urbano/Água
            ]

            # Para mapas categóricos, definimos min e max para corresponder aos índices da paleta
            vis_params = {
                'min': 0,
                'max': 6,
                'palette': soil_palette
            }
        # --- FIM DO BLOCO MODIFICADO ---

        if image_to_process is not None:
            action = st.radio("Escolha a ação:", ["Baixar Direto", "Exportar para Google Drive"], horizontal=True)
            if action == "Baixar Direto":
                file_name = st.text_input("Nome do arquivo para salvar (.tif):", "dados_processados.tif")
                if st.button("Iniciar Download"):

                    # Cria a pasta 'outputs/1' se ela não existir
                    output_dir = "outputs/1"
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    # Salva o arquivo dentro da pasta 'outputs/1'
                    output_path = os.path.join(output_dir, file_name)

                    # Passa a 'scale' para a função
                    download_image_ano(image_to_process, output_path, AOI, scale=scale)

            elif action == "Exportar para Google Drive":
                folder_name = st.text_input("Nome da pasta no Google Drive:", "GEE_Downloader_Exports")
                if st.button("Iniciar Exportação"):
                    # Passa a 'scale' para a função
                    export_to_drive(image_to_process, AOI, folder_name, scale=scale)

        st.subheader("Visualização do Mapa")

        m = geemap.Map(center=[-15.78, -47.92], zoom=4, plugin_Draw=True, Draw_export=True)
        m.add_basemap("HYBRID")

        # --- ORDEM DAS CAMADAS MODIFICADA ---

        # Centraliza o mapa na AOI
        if AOI is not None:
            m.centerObject(AOI, 10)

        # 1. Adiciona a camada de dados (raster) PRIMEIRO
        if image_to_process is not None:
            m.addLayer(image_to_process, vis_params, f'Visualização: {data_type}')

        # 2. Adiciona a AOI (vetor) DEPOIS, para que fique por cima
        if AOI is not None:
            # Usei um ciano mais escuro para o contorno para dar mais contraste
            m.addLayer(AOI, {'color': '#00FFFF', 'fillColor': 'cyan'}, 'Área de Interesse', True, 0.3)

            # --- FIM DA MODIFICAÇÃO DE ORDEM ---

        # --- CONTROLES DE DIMENSÃO E LAYOUT DO MAPA ---
        map_width = st.slider("Largura do mapa (pixels):", min_value=400, max_value=1200, value=700, step=50)

        col1, col2 = st.columns([1, 4])  # Coluna para slider (1) e para o mapa (4)

        with col1:
            # Usando o slider vertical customizado
            map_height = vertical_slider(
                key="height_slider",
                min_value=400,
                max_value=1200,
                default_value=500,
                step=50
            )
        with col2:
            m.to_streamlit(width=map_width, height=map_height)

else:
    st.info("Por favor, insira seu User ID do GEE e faça o upload de um arquivo para continuar.")
