import streamlit as st
import os
import tempfile
import time
import pandas as pd
import geopandas as gpd
from shapely import wkt
from pathlib import Path
import requests
import s2sphere
import shutil
import leafmap.foliumap as leafmap

st.set_page_config(
    page_title="🏢 Downloader de Dados (Google Open Buildings V3)",
    page_icon="🛰️",
    layout="wide"
)

# Garante que o diretório de saída existe
OUTPUT_DIR = "outputs/5"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Funções do script ---

def get_s2_tokens_for_aoi(aoi_gdf: gpd.GeoDataFrame, status_placeholder) -> list[str]:
    """Calcula os tokens S2 de nível 6 que cobrem a área de interesse."""
    status_placeholder.info("Calculando S2 Tokens para a AOI...")
    bounds = aoi_gdf.total_bounds
    min_lon, min_lat, max_lon, max_lat = bounds
    rect = s2sphere.LatLngRect.from_point_pair(
        s2sphere.LatLng.from_degrees(min_lat, min_lon),
        s2sphere.LatLng.from_degrees(max_lat, max_lon)
    )
    coverer = s2sphere.RegionCoverer()
    coverer.min_level = 6
    coverer.max_level = 6
    cell_ids = coverer.get_covering(rect)
    tokens = [cell_id.to_token() for cell_id in cell_ids]
    status_placeholder.info(f"AOI intercepta {len(tokens)} S2 Token(s).")
    return tokens

def download_tile(token: str, base_url: str, save_folder: Path, status_placeholder) -> Path | None:
    """Baixa um único tile de dados do Open Buildings de forma robusta."""
    file_name = f"{token}_buildings.csv.gz"
    download_url = f"{base_url}{file_name}"
    output_path = save_folder / file_name

    try:
        with st.spinner(f"Baixando {file_name}..."):
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
        status_placeholder.info(f"Tile baixado: {output_path.name}")
        return output_path
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            st.warning(f"AVISO: Tile {file_name} não encontrado (404). Pulando.")
        else:
            st.error(f"ERRO de HTTP ao baixar {file_name}: {e}")
        return None
    except Exception as e:
        st.error(f"ERRO geral ao baixar {file_name}: {e}")
        return None

def display_map(gdf_buildings):
    """Exibe um mapa com os polígonos de construções baixados."""
    st.subheader("Visualização dos Dados Baixados")
    m = leafmap.Map()
    style = {"color": "#FF5733", "fillColor": "#FFC300", "weight": 1, "fillOpacity": 0.6}
    if not gdf_buildings.empty:
        m.add_gdf(gdf_buildings, layer_name="Construções", style=style)
    m.to_streamlit()

# --- Interface do Streamlit ---

st.markdown('''
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
''', unsafe_allow_html=True)

st.info(
    "Faça upload de um arquivo vetorial (GeoJSON, GPKG, Shapefile .zip) contendo o polígono da sua área de interesse (AOI).")
st.warning("O processo usará o *limite total (envelope)* da sua AOI para baixar os dados do Google Open Buildings.")

uploaded_aoi = st.file_uploader("Selecione o arquivo da AOI (.geojson, .gpkg, .zip)", type=["geojson", "gpkg", "zip"], key="open_buildings_uploader")

if st.button("Baixar Dados do Open Buildings", type="primary"):
    if uploaded_aoi is not None:
        with tempfile.TemporaryDirectory() as temp_dir:
            aoi_temp_path = os.path.join(temp_dir, uploaded_aoi.name)
            with open(aoi_temp_path, "wb") as f:
                f.write(uploaded_aoi.getbuffer())

            st.info(f"Arquivo AOI '{uploaded_aoi.name}' carregado.")
            status_text = st.empty()

            try:
                final_output_path = os.path.join(OUTPUT_DIR, "open_buildings_result.gpkg")
                temp_download_folder = Path(temp_dir) / "temp_downloads"
                temp_download_folder.mkdir(exist_ok=True)
                BASE_DOWNLOAD_URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_6_gzip_no_header/"
                COLUMN_NAMES = ['latitude', 'longitude', 'area_in_meters', 'confidence', 'geometry', 'full_plus_code']

                status_text.info(f"Carregando AOI: {uploaded_aoi.name}")
                aoi_gdf = gpd.read_file(aoi_temp_path)

                if aoi_gdf.crs.to_epsg() != 4326:
                    status_text.info(f"Reprojetando AOI de {aoi_gdf.crs} para EPSG:4326...")
                    aoi_gdf = aoi_gdf.to_crs(epsg=4326)

                s2_tokens = get_s2_tokens_for_aoi(aoi_gdf, status_text)
                if not s2_tokens:
                    st.error("ERRO: Nenhum S2 Token encontrado para a AOI.")
                    st.stop()

                downloaded_files = []
                for token in s2_tokens:
                    file_path = download_tile(token, BASE_DOWNLOAD_URL, temp_download_folder, status_text)
                    if file_path:
                        downloaded_files.append(file_path)

                if not downloaded_files:
                    st.error("ERRO: Nenhum arquivo CSV foi baixado. A AOI pode estar em uma área sem dados.")
                    st.stop()

                status_text.info("Download Concluído. Iniciando Processamento...")

                gdf_final = gpd.GeoDataFrame()
                with st.spinner("Processando e mesclando arquivos..."):
                    all_gdfs = []
                    for i, csv_path in enumerate(downloaded_files):
                        df = pd.read_csv(csv_path, header=None, names=COLUMN_NAMES)
                        df['geometry'] = df['geometry'].apply(wkt.loads)
                        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
                        all_gdfs.append(gdf)

                    full_gdf = pd.concat(all_gdfs, ignore_index=True)

                    status_text.info("Filtrando construções dentro da sua AOI...")
                    gdf_filtrado = gpd.sjoin(full_gdf, aoi_gdf, how="inner", predicate="intersects")
                    gdf_filtrado = gdf_filtrado.drop_duplicates(subset=['full_plus_code'])
                    st.success(f"Encontradas {len(gdf_filtrado)} construções na AOI.")

                    if 'confidence' in gdf_filtrado.columns:
                        status_text.info("Filtrando por confiança > 0.70...")
                        gdf_final = gdf_filtrado[gdf_filtrado['confidence'] > 0.70]
                        st.success(f"Restaram {len(gdf_final)} construções após filtro de confiança.")
                    else:
                        gdf_final = gdf_filtrado

                    if not gdf_final.empty:
                        status_text.info(f"Salvando resultado final em: {final_output_path}")
                        gdf_final.to_file(final_output_path, driver="GPKG")

                status_text.success("Processo concluído!")

                st.subheader("Resultado para Download")
                st.markdown(f"Arquivo salvo em `{final_output_path}`.")

                if not gdf_final.empty:
                    with open(final_output_path, "rb") as f:
                        st.download_button(
                            "Baixar Construções (open_buildings_result.gpkg)",
                            f,
                            file_name="open_buildings_result.gpkg"
                        )
                    # Exibe o mapa com os resultados
                    display_map(gdf_final)
                else:
                    st.info("Nenhuma construção encontrada para exibir no mapa.")

            except Exception as e:
                st.error(f"Ocorreu um erro durante o processo: {e}")
                st.exception(e)

    else:
        st.warning("Por favor, faça o upload de um arquivo de AOI.")
