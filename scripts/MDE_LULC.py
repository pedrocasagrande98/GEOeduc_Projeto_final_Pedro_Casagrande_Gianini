import streamlit as st
import geopandas as gpd
import ee
import geemap.foliumap as geemap # Importa a biblioteca geemap para visualização de mapas
import requests
import os

# Configuração da página para layout amplo
st.set_page_config(layout="wide")

# Título centralizado
st.markdown("<h1 style='text-align: center;'>Análise de MDE e Uso do Solo</h1>", unsafe_allow_html=True)


# Adiciona uma nota sobre a instalação de dependências
st.sidebar.info("Esta aplicação requer a biblioteca `geemap`. Instale-a com `pip install geemap`.")

# Função para autenticar e inicializar o GEE
def initialize_earth_engine(user_id):
    try:
        ee.Initialize(project=f'ee-{user_id}')
        return True
    except Exception as e:
        st.error(f"Falha na inicialização do Earth Engine: {e}")
        st.warning("Verifique se você está autenticado. Execute `earthengine authenticate` no seu terminal.")
        return False

# Função para fazer o download da imagem
def download_image_ano(image, output_path, AOI):
    try:
        download_url = image.getDownloadURL({
            'scale': 30,
            'region': AOI.geometry().bounds(),
            'format': 'GeoTIFF',
            'crs': 'EPSG:4326',
            'maxPixels': 1e13
        })
        response = requests.get(download_url)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            st.success(f"Imagem salva em: {output_path}")
            return True
        else:
            st.error(f"Erro ao baixar a imagem: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        st.error(f"Ocorreu um erro durante o download: {e}")
        return False

# Função para exportar para o Google Drive
def export_to_drive(image, AOI, folder_name):
    task = ee.batch.Export.image.toDrive(
        image=image,
        description="Export_HydroAnalysis",
        folder=folder_name,
        fileNamePrefix="hydro_analysis_data",
        region=AOI.geometry().bounds(),
        scale=30,
        crs="EPSG:4326",
        fileFormat="GeoTIFF"
    )
    task.start()
    st.info(f"Exportação iniciada para a pasta '{folder_name}' no Google Drive.")

# Função principal do Streamlit
def app():
    st.markdown("""<p style='text-align: center;'>Visualize e baixe dados de elevação, declividade, aspecto e cobertura do solo diretamente do Google Earth Engine.</p>""", unsafe_allow_html=True)

    # Inicializa variáveis para garantir que estejam sempre definidas no escopo correto
    AOI = None
    image_to_process = None
    vis_params = {}
    data_type = "Elevação" # Valor padrão

    # Controles na barra lateral
    with st.sidebar:
        st.subheader("⚙️ Controles")
        user_id = st.text_input("Seu User ID do Google Earth Engine:", help="Seu projeto GEE deve ter o nome 'ee-SEU_USER_ID'")
        uploaded_file = st.file_uploader("Carregue sua área de interesse (.gpkg ou .geojson):", type=["gpkg", "geojson"])
        
        if user_id and uploaded_file:
            if initialize_earth_engine(user_id):
                gdf = gpd.read_file(uploaded_file)
                if gdf.crs != "EPSG:4326":
                    gdf = gdf.to_crs(epsg=4326)
                
                AOI = ee.FeatureCollection(gdf.__geo_interface__)
                clip_geometry = AOI.geometry().bounds()

                data_type = st.selectbox("Escolha o tipo de dado:", 
                                        ["Elevação", "Declividade", "Aspecto", "Uso e Cobertura do Solo (MapBiomas)"])

                # Lógica condicional para paletas
                if data_type == "Elevação":
                    elevation_palette = st.selectbox("Paleta de Cores (Elevação):", 
                                                     ['terrain', 'viridis', 'inferno', 'gist_earth'])
                
                if data_type == "Declividade":
                    slope_palette_name = st.selectbox("Paleta de Cores (Declividade):",
                                                      ['Padrão (Verde-Vermelho)', 'Reds', 'plasma'])

                if data_type == "Elevação":
                    image_to_process = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(clip_geometry)
                    stats = image_to_process.reduceRegion(reducer=ee.Reducer.minMax(), geometry=clip_geometry, scale=30, maxPixels=1e9).getInfo()
                    vis_params = {'min': stats['elevation_min'], 'max': stats['elevation_max'], 'palette': elevation_palette}
                
                elif data_type == "Declividade":
                    slope_palettes = {
                        'Padrão (Verde-Vermelho)': ['#4CAF50', '#FFF176', '#FF7043', '#E53935'],
                        'Reds': 'Reds',
                        'plasma': 'plasma'
                    }
                    elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
                    image_to_process = ee.Terrain.slope(elevation).clip(clip_geometry)
                    stats = image_to_process.reduceRegion(reducer=ee.Reducer.minMax(), geometry=clip_geometry, scale=30, maxPixels=1e9).getInfo()
                    vis_params = {'min': stats['slope_min'], 'max': stats['slope_max'], 'palette': slope_palettes[slope_palette_name]}

                elif data_type == "Aspecto":
                    elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
                    image_to_process = ee.Terrain.hillshade(elevation).clip(clip_geometry)
                    vis_params = {}

                elif data_type == "Uso e Cobertura do Solo (MapBiomas)":
                    # Dicionário de cores extraído do arquivo JSON oficial do MapBiomas
                    mapbiomas_color_map = {
    "1": "#1f8d49",
    "3": "#1f8d49",
    "4": "#7dc975",
    "5": "#04381d",
    "6": "#026975",
    "9": "#7a5900",
    "10": "#ad975a",
    "11": "#519799",
    "12": "#d6bc74",
    "14": "#FFFFB2",
    "15": "#edde8e",
    "18": "#E974ED",
    "19": "#C27BA0",
    "20": "#db7093",
    "21": "#ffefc3",
    "22": "#d4271e",
    "23": "#ffa07a",
    "24": "#d4271e",
    "25": "#db4d4f",
    "26": "#0000FF",
    "27": "#ffffff",
    "29": "#ffaa5f",
    "30": "#9c0027",
    "31": "#091077",
    "32": "#fc8114",
    "33": "#2532e4",
    "35": "#9065d0",
    "36": "#d082de",
    "39": "#f5b3c8",
    "40": "#c71585",
    "41": "#f54ca9",
    "46": "#d68fe2",
    "47": "#9932cc",
    "48": "#e6ccff",
    "49": "#02d659",
    "50": "#ad5100",
    "62": "#ff69b4"
}

                    # As chaves do dicionário são strings, convertemos para int para encontrar o max
                    max_id = max([int(k) for k in mapbiomas_color_map.keys()])
                    min_id = 0 # A paleta precisa de um range contínuo, começando de 0

                    # Cria a paleta completa do min_id ao max_id
                    full_palette = []
                    for i in range(min_id, max_id + 1):
                        # Usa a cor do dicionário ou uma cor transparente para valores não definidos
                        color = mapbiomas_color_map.get(str(i), '00000000') # Preto transparente para buracos na legenda
                        full_palette.append(color.replace('#', ''))

                    vis_params = {'min': min_id, 'max': max_id, 'palette': full_palette}

                    selected_year = st.slider("Ano (MapBiomas):", 1985, 2023, 2023)
                    band_name = f'classification_{selected_year}'
                    image_to_process = ee.Image(f'projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1').select(band_name).clip(clip_geometry)


                if image_to_process is not None:
                    action = st.radio("Escolha a ação:", ["Baixar Direto", "Exportar para Google Drive"], horizontal=True)

                    if action == "Baixar Direto":
                        file_name = st.text_input("Nome do arquivo para salvar (.tif):", "dados_processados.tif")
                        if st.button("Iniciar Download"):
                            output_dir = "D:/POS/!FW_HAND_Osmnx/!PROJETO_FINAL_4_modulos/resultado/mod1"
                            if not os.path.exists(output_dir):
                                os.makedirs(output_dir)
                            output_path = os.path.join(output_dir, file_name)
                            download_image_ano(image_to_process, output_path, AOI)
                    
                    elif action == "Exportar para Google Drive":
                        folder_name = st.text_input("Nome da pasta no Google Drive:", "Hydro_Analysis_Exports")
                        if st.button("Iniciar Exportação"):
                            export_to_drive(image_to_process, AOI, folder_name)
        
        st.subheader("Visualização do Mapa")
        map_height = st.slider("Altura do mapa (pixels):", min_value=400, max_value=1200, value=700, step=50)

    # Mapa na área principal
    st.subheader("🗺️ Pré-visualização do Mapa")
    m = geemap.Map(center=[-15.78, -47.92], zoom=4, plugin_Draw=True, Draw_export=True)
    m.add_basemap("HYBRID")

    # Centraliza o mapa na AOI, se ela existir
    if AOI is not None:
        m.centerObject(AOI, 10)

    # Adiciona a camada de dados (imagem) primeiro, se ela existir
    if image_to_process is not None:
        m.addLayer(image_to_process, vis_params, f'Visualização: {data_type}')

    # Adiciona a camada da AOI por último, se ela existir
    if AOI is not None:
        m.addLayer(AOI, {'color': 'cyan', 'fillColor': 'cyan'}, 'Área de Interesse', True, 0.5)
    
    m.to_streamlit(height=map_height)

if __name__ == "__main__":
    app()
