import pandas as pd
import geopandas as gpd
from shapely import wkt
from pathlib import Path
import os
import sys
import requests
import shutil
from tqdm import tqdm
import s2sphere

print("--- Script (V23): Corrigindo o 'CRS Mismatch' (reprojetando AOI) ---")

# --- 1. DEFINIR CAMINHOS E CONSTANTES ---
aoi_local_path = r"C:\MERX\OKR\OPEN3BUILDING\teste.geojson"
final_output_path = "buildings_AOI_FINAL.gpkg"
temp_download_folder = Path("./temp_downloads")
BASE_DOWNLOAD_URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_6_gzip_no_header/"

COLUMN_NAMES = [
    'latitude',
    'longitude',
    'area_in_meters',
    'confidence',
    'geometry',
    'full_plus_code'  # Este é o nosso ID único
]


# --- 2. FUNÇÕES AUXILIARES (Sem alteração) ---

def get_s2_tokens_for_aoi(aoi_gdf: gpd.GeoDataFrame) -> list[str]:
    print("Calculando S2 Tokens para a AOI...")
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
    print(f"AOI intercepta {len(tokens)} S2 Token(s): {tokens}")
    return tokens


def download_tile(token: str, base_url: str, save_folder: Path) -> Path | None:
    file_name = f"{token}_buildings.csv.gz"
    download_url = f"{base_url}{file_name}"
    output_path = save_folder / file_name

    print(f"\nBaixando tile: {file_name}...")
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            with open(output_path, 'wb') as f, tqdm(
                    total=total_size, unit='iB', unit_scale=True, desc=file_name
            ) as pbar:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))
        print(f"Tile baixado: {output_path}")
        return output_path
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"AVISO: Tile {file_name} não encontrado (404). Pulando.")
            return None
    except Exception as e:
        print(f"ERRO ao baixar {file_name}: {e}")
        return None


# --- 3. EXCUSSÃO PRINCIPAL ---
if __name__ == "__main__":

    temp_download_folder.mkdir(exist_ok=True)

    # --- ETAPA 1: CARREGAR AOI E ACHAR TILES ---
    if not os.path.exists(aoi_local_path):
        print(f"ERRO: O arquivo de AOI não foi encontrado em: {aoi_local_path}")
        sys.exit()
    print(f"Carregando AOI: {aoi_local_path}")
    aoi_gdf = gpd.read_file(aoi_local_path)

    # --- CORREÇÃO V23 ---
    # O 'Left CRS' (download) é EPSG:4326.
    # O 'Right CRS' (seu arquivo) é EPSG:4674.
    # Vamos forçar a AOI a bater com o CRS do download.
    if aoi_gdf.crs.to_epsg() != 4326:
        print(f"Reprojetando AOI de {aoi_gdf.crs} para EPSG:4326...")
        aoi_gdf = aoi_gdf.to_crs(epsg=4326)

    s2_tokens = get_s2_tokens_for_aoi(aoi_gdf)
    if not s2_tokens:
        print("ERRO: Nenhum S2 Token encontrado para a AOI.")
        sys.exit()

    # --- ETAPA 2: BAIXAR OS TILES ---
    downloaded_files = []
    for token in s2_tokens:
        file_path = download_tile(token, BASE_DOWNLOAD_URL, temp_download_folder)
        if file_path:
            downloaded_files.append(file_path)
    if not downloaded_files:
        print("ERRO: Nenhum arquivo CSV foi baixado. A AOI pode estar em uma área sem dados.")
        sys.exit()

    print(f"\n--- Download Concluído. Iniciando Processamento ---")

    # --- ETAPA 3: PROCESSAR OS CSVS ---
    all_gdfs = []
    try:
        for i, csv_path in enumerate(downloaded_files):
            print(f"Processando arquivo {i + 1}/{len(downloaded_files)}: {csv_path.name}")
            print("  Carregando CSV no Pandas (sem cabeçalho)...")
            df = pd.read_csv(
                csv_path,
                header=None,
                names=COLUMN_NAMES
            )
            print("  Convertendo geometrias WKT...")
            df['geometry'] = df['geometry'].apply(wkt.loads)
            print("  Criando GeoDataFrame...")
            # O CRS dos dados baixados é sempre EPSG:4326
            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
            all_gdfs.append(gdf)

        print("Mesclando todos os tiles baixados...")
        full_gdf = pd.concat(all_gdfs, ignore_index=True)

        # --- ETAPA 4: FILTRAR PELA SUA AOI ---
        print("Filtrando construções dentro da sua AOI (sjoin)...")
        # Agora ambos (full_gdf e aoi_gdf) estão em EPSG:4326. O aviso sumirá.
        gdf_filtrado = gpd.sjoin(full_gdf, aoi_gdf, how="inner", predicate="intersects")

        gdf_filtrado = gdf_filtrado.drop_duplicates(subset=['full_plus_code'])
        print(f"Encontradas {len(gdf_filtrado)} construções na AOI.")

        # --- ETAPA 5: FILTRAR POR CONFIANÇA ---
        if 'confidence' in gdf_filtrado.columns:
            print("Filtrando por confiança > 0.70...")
            gdf_final = gdf_filtrado[gdf_filtrado['confidence'] > 0.70]
            print(f"Restaram {len(gdf_final)} construções.")
        else:
            gdf_final = gdf_filtrado

        # --- ETAPA 6: SALVAR RESULTADO FINAL ---
        print(f"Salvando resultado final em: {final_output_path}")
        gdf_final.to_file(final_output_path, driver="GPKG")

        print("\n--- PROCESSO CONCLUÍDO ---")
        print(f"Seu arquivo final está pronto: {final_output_path}")

    except MemoryError:
        print("\n--- ERRO DE MEMÓRIA ---")
        print(f"O arquivo {csv_path.name} é muito grande para o Pandas.")
        print("Precisaremos usar uma biblioteca como 'Dask' para processá-lo.")
    except Exception as e:
        print(f"\n--- ERRO DURANTE O PROCESSAMENTO ---")
        print(f"Detalhe: {e}")

    finally:
        # --- ETAPA 7: LIMPEZA ---
        print("Limpando arquivos CSV temporários...")
        try:
            shutil.rmtree(temp_download_folder)
            print("Pasta temporária removida.")
        except Exception as e:
            print(f"Aviso: não foi possível remover a pasta temporária {temp_download_folder}: {e}")