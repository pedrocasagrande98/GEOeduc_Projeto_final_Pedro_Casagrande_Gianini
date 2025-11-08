import streamlit as st
import geopandas as gpd
import ee
import geemap.foliumap as geemap
import requests
import os

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
# ATUALIZADO: Adicionado parâmetro 'scale'
def download_image_ano(image, output_path, AOI, scale=30):
    try:
        download_url = image.getDownloadURL({
            'scale': scale, # <-- MODIFICADO
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
# ATUALIZADO: Adicionado parâmetro 'scale'
def export_to_drive(image, AOI, folder_name, scale=30):
    task = ee.batch.Export.image.toDrive(
        image=image,
        description="Export_GEE_Downloader",
        folder=folder_name,
        fileNamePrefix="gee_download_data",
        region=AOI.geometry().bounds(),
        scale=scale, # <-- MODIFICADO
        crs="EPSG:4326",
        fileFormat="GeoTIFF"
    )
    task.start()
    st.info(f"Exportação iniciada para a pasta '{folder_name}' no Google Drive.")