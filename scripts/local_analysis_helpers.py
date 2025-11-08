import rasterio
from rasterio import features
from rasterio.mask import mask
import geopandas as gpd
from pyproj import CRS
import osmnx as ox
import numpy as np
from shapely.geometry import box, shape, LineString, Point
import warnings
import os
import zipfile
import glob
import pandas as pd
from scipy.optimize import brentq

# Tenta importar pysheds
try:
    from pysheds.grid import Grid
except ImportError:
    print("Erro: Biblioteca 'pysheds' não encontrada. Instale com 'pip install pysheds'")
    raise

# Ignorar warnings futuros
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


# --- FUNÇÕES DA PÁGINA 2 (HIDROLOGIA) ---

def run_preprocessing(mde_path, output_dir, stream_threshold, progress_callback):
    """
    Executa a Etapa 1: Pré-processamento do MDE.
    Combina as células 2, 2.5, 2.6 e 3 do notebook.
    """
    results = {}

    progress_callback("Carregando MDE e instanciando Grid PySheds...", 5)
    if not os.path.exists(mde_path):
        raise FileNotFoundError(f"Arquivo MDE '{mde_path}' não encontrado.")

    grid = Grid.from_raster(mde_path, data_name='dem')
    dem = grid.read_raster(mde_path)

    progress_callback("Condicionando MDE (fill_pits, resolve_flats)... (Pode demorar)", 15)
    pit_filled_dem = grid.fill_pits(dem)
    flooded_dem = grid.fill_depressions(pit_filled_dem)
    inflated_dem = grid.resolve_flats(flooded_dem)  # MDE condicionado

    progress_callback("Calculando direção e acumulação do fluxo...", 30)
    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    fdir = grid.flowdir(inflated_dem, dirmap=dirmap)
    acc = grid.accumulation(fdir, dirmap=dirmap)

    # Salvar rasters intermediários
    fdir_path = os.path.join(output_dir, 'flow_direction.tif')
    acc_path = os.path.join(output_dir, 'flow_accumulation.tif')

    progress_callback("Salvando rasters de direção e acumulação...", 40)
    grid.to_raster(fdir, fdir_path, nodata=-9999)
    grid.to_raster(acc, acc_path, nodata=-9999)
    results['fdir_path'] = fdir_path
    results['acc_path'] = acc_path

    # Cálculo do Aspect
    progress_callback("Calculando Aspect...", 45)
    gy, gx = np.gradient(inflated_dem)
    aspect_rad = np.arctan2(gy, -gx)
    aspect_deg = np.degrees(aspect_rad)
    aspect = (aspect_deg + 360) % 360
    aspect[((gx == 0) & (gy == 0))] = -1  # Marcar áreas planas
    aspect_path = os.path.join(output_dir, 'aspect.tif')
    grid.to_raster(aspect, aspect_path, nodata=-1)
    results['aspect_path'] = aspect_path

    # Cálculo do Slope (Declividade)
    progress_callback("Calculando Declividade (Slope)...", 50)
    x_res = grid.viewfinder.affine[0]
    y_res = -grid.viewfinder.affine[4]  # É negativo na affine
    gy, gx = np.gradient(inflated_dem, y_res, x_res)
    slope_rad = np.arctan(np.sqrt(gx ** 2 + gy ** 2))
    slope_deg = np.degrees(slope_rad)
    slope_path = os.path.join(output_dir, 'slope.tif')
    grid.to_raster(slope_deg, slope_path, nodata=-9999)
    results['slope_path'] = slope_path

    # Cálculo do TWI (Índice de Umidade Topográfica)
    progress_callback("Calculando Índice de Umidade Topográfica (TWI)...", 60)
    cell_area = x_res * y_res
    slope_rad_twi = np.arctan(np.sqrt(gx ** 2 + gy ** 2))
    slope_rad_twi[slope_rad_twi == 0] = 0.001  # Evitar divisão por zero
    sca = (acc + 1) * cell_area
    twi = np.log(sca / np.tan(slope_rad_twi))
    twi_path = os.path.join(output_dir, 'twi.tif')
    grid.to_raster(twi, twi_path, nodata=-9999)
    results['twi_path'] = twi_path

    # Vetorização da Rede de Drenagem (Total)
    progress_callback("Vetorizando rede de drenagem total...", 75)
    streams_mask = acc > stream_threshold
    network = grid.extract_river_network(fdir, streams_mask, distance=1)

    features_list = network.get('features', [])
    geometries = []
    if features_list:
        for feature in features_list:
            coords = feature['geometry']['coordinates']
            if len(coords) >= 2:
                geometries.append(LineString(coords))

        if geometries:
            streams_gdf = gpd.GeoDataFrame(geometry=geometries, crs=grid.viewfinder.crs)
            canais_path = os.path.join(output_dir, 'rede_drenagem_total.geojson')
            streams_gdf.to_file(canais_path, driver='GeoJSON')
            results['canais_total_path'] = canais_path
            progress_callback("Rede de drenagem total salva.", 95)

    progress_callback("Pré-processamento concluído.", 100)

    # Adiciona os objetos em memória para a próxima etapa
    results['grid'] = grid
    results['fdir'] = fdir
    results['acc'] = acc
    results['inflated_dem'] = inflated_dem
    results['dirmap'] = dirmap

    return results


def run_delineation(preproc_data, outlet_coords, channel_depth, stream_threshold, output_dir, progress_callback, generate_flu_distance=False):
    """
    Executa a Etapa 2: Delineamento da Bacia e HAND.
    """
    results = {}

    # Recupera dados da etapa anterior
    grid = preproc_data['grid']
    fdir = preproc_data['fdir']
    acc = preproc_data['acc']
    inflated_dem = preproc_data['inflated_dem']
    dirmap = preproc_data['dirmap']

    x_outlet, y_outlet = outlet_coords

    progress_callback("Realizando snap do exutório...", 10)
    streams_mask = acc > stream_threshold
    try:
        x_snap, y_snap = grid.snap_to_mask(streams_mask, (x_outlet, y_outlet))
    except ValueError as e:
        raise ValueError(
            f"Erro ao fazer snap: {e}. Verifique se as coordenadas estão dentro da área do MDE e próximas a um canal com acumulação > {stream_threshold}.")

    # --- INÍCIO DA EXPORTAÇÃO DO EXUTÓRIO ---
    progress_callback("Exportando exutório...", 15)
    outlet_geom = [Point(x_snap, y_snap)]
    outlet_gdf = gpd.GeoDataFrame(geometry=outlet_geom, crs=grid.viewfinder.crs)
    exutorio_path = os.path.join(output_dir, 'exutorio.geojson')
    outlet_gdf.to_file(exutorio_path, driver='GeoJSON')
    results['exutorio_path'] = exutorio_path
    # --- FIM DA EXPORTAÇÃO DO EXUTÓRIO ---

    progress_callback("Delimitando bacia hidrográfica...", 20)
    catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, xytype='coordinate')

    if generate_flu_distance:
        progress_callback("Calculando distância de fluxo...", 30)
        dist = grid.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, xytype='coordinate')

    progress_callback("Recortando grid para a bacia...", 40)
    grid.clip_to(catch)

    if generate_flu_distance:
        # Salva Distância de Fluxo (recortada)
        dist_view = grid.view(dist)
        dist_path = os.path.join(output_dir, 'flu_distance.tif')
        grid.to_raster(dist_view, dist_path, dtype=rasterio.float32, nodata=-9999.0)
        results['dist_path'] = dist_path

    progress_callback("Extraindo rede de drenagem e ordem de Strahler...", 50)
    fdir_clipped = grid.view(fdir)
    clipped_acc = grid.accumulation(fdir_clipped, dirmap=dirmap)
    clipped_streams_mask = clipped_acc > stream_threshold
    stream_order_raster = grid.stream_order(fdir_clipped, clipped_streams_mask)
    network = grid.extract_river_network(fdir_clipped, clipped_streams_mask, distance=1)

    progress_callback("Vetorizando a bacia...", 60)
    catch_view = grid.view(catch)
    catchment_shapes = rasterio.features.shapes(
        catch_view.astype(np.uint8),
        mask=catch_view,
        transform=grid.viewfinder.affine
    )
    catchment_geoms = [shape(geom) for geom, value in catchment_shapes if value == 1]
    if not catchment_geoms:
        raise RuntimeError("Não foi possível vetorizar a bacia.")

    catchment_gdf = gpd.GeoDataFrame(geometry=catchment_geoms, crs=grid.viewfinder.crs).dissolve()
    bacia_path = os.path.join(output_dir, 'bacia.geojson')
    catchment_gdf.to_file(bacia_path, driver='GeoJSON')
    results['bacia_path'] = bacia_path

    progress_callback("Atribuindo ordem de Strahler aos canais...", 70)
    features_list = network.get('features', [])
    geometries, strahler_orders = [], []
    if features_list:
        vf_affine = grid.viewfinder.affine
        inv_vf_affine = ~vf_affine
        vf_height, vf_width = grid.viewfinder.shape

        for feature in features_list:
            coords = feature['geometry']['coordinates']
            if len(coords) >= 2:
                geometries.append(LineString(coords))
                start_coord = coords[0]
                col_frac, row_frac = inv_vf_affine * (start_coord[0], start_coord[1])
                row, col = int(row_frac), int(col_frac)

                order_val = None
                if 0 <= row < vf_height and 0 <= col < vf_width:
                    order_val = stream_order_raster[row, col]

                strahler_orders.append(int(order_val) if order_val is not None and not np.isnan(order_val) else None)

        if geometries:
            streams_gdf = gpd.GeoDataFrame({'strahler_order': strahler_orders}, geometry=geometries,
                                           crs=grid.viewfinder.crs)
            canais_path = os.path.join(output_dir, 'canais_strahler.geojson')
            streams_gdf.to_file(canais_path, driver='GeoJSON')
            results['canais_path'] = canais_path

    # Cálculo do HAND
    progress_callback("Calculando HAND dentro da bacia...", 80)
    streams_mask_global = acc > stream_threshold
    hand = grid.compute_hand(fdir, inflated_dem, streams_mask_global)

    progress_callback(f"Calculando mancha de inundação para {channel_depth}m...", 90)
    hand_view = grid.view(hand, nodata=np.nan)
    inundation_depth = np.where(hand_view < channel_depth, channel_depth - hand_view, np.nan)

    # Salvar Raster de Inundação
    profile = {
        'crs': grid.viewfinder.crs, 'transform': grid.viewfinder.affine,
        'height': grid.viewfinder.shape[0], 'width': grid.viewfinder.shape[1],
        'driver': 'GTiff', 'count': 1, 'dtype': rasterio.float32, 'nodata': np.nan
    }

    if channel_depth == int(channel_depth):
        suffix_nome_arquivo = f"{int(channel_depth)}m"
    else:
        suffix_nome_arquivo = f"{str(channel_depth).replace('.', '_')}m"

    results['suffix'] = suffix_nome_arquivo

    inundacao_raster_path = os.path.join(output_dir, f'inundacao_mapa_{suffix_nome_arquivo}.tif')
    with rasterio.open(inundacao_raster_path, 'w', **profile) as dst:
        dst.write(inundation_depth.astype(rasterio.float32), 1)
    results['inundacao_raster_path'] = inundacao_raster_path

    # Vetorizar Mancha de Inundação
    progress_callback("Vetorizando mancha de inundação...", 95)
    inundation_mask = ~np.isnan(inundation_depth)
    if np.any(inundation_mask):
        shapes_generator = rasterio.features.shapes(
            inundation_mask.astype(np.uint8),
            mask=inundation_mask,
            transform=profile['transform']
        )
        flood_geometries = [shape(geom) for geom, value in shapes_generator if value == 1]
        if flood_geometries:
            flood_gdf = gpd.GeoDataFrame(geometry=flood_geometries, crs=profile['crs']).dissolve()
            inundacao_vetor_path = os.path.join(output_dir, f'inundacao_{suffix_nome_arquivo}.geojson')
            flood_gdf.to_file(inundacao_vetor_path, driver='GeoJSON')
            results['inundacao_vetor_path'] = inundacao_vetor_path

    progress_callback("Delineamento e HAND concluídos.", 100)
    return results


# --- FUNÇÕES DA PÁGINA 3 (OSM) ---

def run_osmnx_download(aoi_path, output_dir, progress_callback):
    """
    Executa a Etapa 3: Download de Dados OSM.
    """
    results = {}

    progress_callback("Lendo arquivo de AOI...", 10)

    if aoi_path.endswith('.zip'):
        temp_shapefile_dir = os.path.join(os.path.dirname(aoi_path), 'shp_unzipped')
        os.makedirs(temp_shapefile_dir, exist_ok=True)
        with zipfile.ZipFile(aoi_path, 'r') as zip_ref:
            zip_ref.extractall(temp_shapefile_dir)

        shp_files = glob.glob(os.path.join(temp_shapefile_dir, '*.shp'))
        if not shp_files:
            raise FileNotFoundError("Nenhum arquivo .shp encontrado dentro do .zip.")
        aoi_file_to_read = shp_files[0]
        progress_callback("Arquivo .zip extraído, lendo .shp...", 15)
    else:
        aoi_file_to_read = aoi_path

    src_gdf = gpd.read_file(aoi_file_to_read)

    progress_callback("Definindo AOI e reprojetando para EPSG:4326...", 20)
    flood_crs = src_gdf.crs
    flood_bounds = src_gdf.total_bounds
    aoi_bbox_native = box(*flood_bounds)
    aoi_gdf_native = gpd.GeoDataFrame([1], geometry=[aoi_bbox_native], crs=flood_crs)

    if flood_crs.to_epsg() != 4326:
        aoi_gdf_4326 = aoi_gdf_native.to_crs(epsg=4326)
    else:
        aoi_gdf_4326 = aoi_gdf_native

    aoi_polygon_4326 = aoi_gdf_4326.geometry.iloc[0]

    progress_callback("Baixando dados do OpenStreetMap (pode demorar)...", 30)
    tags_to_fetch = {
        'building': True, 'building:part': True, 'roof': True, 'man_made': True,
        'highway': True, 'railway': True, 'aeroway': True, 'public_transport': True,
        'natural': True, 'waterway': True, 'landuse': True,
        'amenity': True, 'shop': True, 'office': True, 'leisure': True, 'tourism': True, 'historic': True,
        'power': True, 'telecom': True, 'pipeline': True,
        'boundary': True, 'wall': ['flood_wall', 'retaining_wall'], 'barrier': True, 'flood_asset': True,
        'flood_prone': ['yes'], 'emergency': True, 'place': True
    }

    osm_features_gdf = ox.features_from_polygon(aoi_polygon_4326, tags_to_fetch)
    progress_callback(f"Download concluído. {len(osm_features_gdf)} feições encontradas.", 60)

    if osm_features_gdf.crs is None:
        osm_features_gdf.crs = CRS.from_epsg(4326)

    progress_callback("Filtrando feições administrativas...", 70)
    keys_to_exclude = ['boundary', 'place']
    exclusion_mask = False
    for key in keys_to_exclude:
        if key in osm_features_gdf.columns:
            exclusion_mask |= osm_features_gdf[key].notna()
    osm_features_gdf = osm_features_gdf[~exclusion_mask].copy()

    progress_callback("Filtrando corpos d'água ('natural'='water')...", 75)
    if 'natural' in osm_features_gdf.columns:
        initial_count = len(osm_features_gdf)
        osm_features_gdf = osm_features_gdf[osm_features_gdf['natural'] != 'water']
        filtered_count = initial_count - len(osm_features_gdf)
        progress_callback(f"Filtro de água concluído. {filtered_count} feições removidas.", 78)

    progress_callback("Salvando Polígonos...", 80)
    osm_polygons_path = os.path.join(output_dir, 'osm_polygons.gpkg')
    osm_polygons_gdf = osm_features_gdf[osm_features_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])].copy()
    if not osm_polygons_gdf.empty:
        osm_polygons_gdf.to_file(osm_polygons_path, driver="GPKG")
        results['polygons_path'] = osm_polygons_path

    progress_callback("Salvando Linhas...", 90)
    osm_lines_path = os.path.join(output_dir, 'osm_lines.gpkg')
    osm_lines_gdf = osm_features_gdf[osm_features_gdf.geometry.type.isin(['LineString', 'MultiLineString'])].copy()
    if not osm_lines_gdf.empty:
        osm_lines_gdf.to_file(osm_lines_path, driver="GPKG")
        results['lines_path'] = osm_lines_path

    progress_callback("Salvando Pontos...", 95)
    osm_points_path = os.path.join(output_dir, 'osm_points.gpkg')
    osm_points_gdf = osm_features_gdf[osm_features_gdf.geometry.type == 'Point'].copy()
    if not osm_points_gdf.empty:
        osm_points_gdf.to_file(osm_points_path, driver="GPKG")
        results['points_path'] = osm_points_path

    progress_callback("Processamento OSM concluído.", 100)
    return results


def _handle_zip(file_path, temp_dir):
    if file_path.endswith('.zip'):
        extract_dir = os.path.join(temp_dir, 'unzipped_vector')
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        shp_files = glob.glob(os.path.join(extract_dir, '*.shp'))
        if shp_files:
            return shp_files[0]

        geojson_files = glob.glob(os.path.join(extract_dir, '*.geojson'))
        if geojson_files:
            return geojson_files[0]

        raise FileNotFoundError("Nenhum .shp ou .geojson encontrado dentro do .zip.")
    return file_path


def run_soil_intersection(raster_path, vector_path, output_dir, progress_callback):
    results = {}
    temp_dir = os.path.join(output_dir, "temp_intersect")
    os.makedirs(temp_dir, exist_ok=True)

    progress_callback("Lendo vetor e raster...", 10)

    vector_file_to_read = _handle_zip(vector_path, temp_dir)

    gdf_vector = gpd.read_file(vector_file_to_read)

    with rasterio.open(raster_path) as src_raster:
        raster_crs = src_raster.crs
        progress_callback(f"CRS do Raster: {raster_crs}", 20)

        if gdf_vector.crs != raster_crs:
            progress_callback(f"Reprojetando vetor de {gdf_vector.crs} para {raster_crs}...", 25)
            gdf_vector = gdf_vector.to_crs(raster_crs)

        progress_callback("Recortando (mascarando) o raster para a área do vetor...", 30)
        geoms = [feature["geometry"] for feature in gdf_vector.iterfeatures()]

        try:
            out_image, out_transform = mask(
                src_raster, geoms, crop=True, filled=True, nodata=src_raster.nodata
            )
            nodata_value = src_raster.nodata if src_raster.nodata is not None else -9999

        except ValueError as e:
            raise ValueError(f"Erro ao mascarar: {e}. Verifique se o vetor sobrepõe o raster.")

        progress_callback("Vetorizando o raster recortado...", 50)
        image = out_image[0].astype('int32')
        shapes = rasterio.features.shapes(image, transform=out_transform)

        polygons, values = [], []
        for geom, value in shapes:
            if value != nodata_value:
                polygons.append(shape(geom))
                values.append(value)

        if not polygons:
            raise ValueError("Nenhuma feição foi vetorizada. O raster pode estar vazio na área de interseção.")

        gdf_solos = gpd.GeoDataFrame(
            data={'valor_solo': values},
            geometry=polygons,
            crs=raster_crs
        )
        progress_callback(f"Foram criados {len(gdf_solos)} polígonos de classes de solo.", 70)

        progress_callback("Intersectando feições do vetor com os polígonos de solo...", 85)
        gdf_intersected = gpd.overlay(
            gdf_vector,
            gdf_solos,
            how='intersection',
            keep_geom_type=True
        )

        gdf_intersected['valor_solo'] = pd.to_numeric(gdf_intersected['valor_solo'])

        output_path = os.path.join(output_dir, "inundacao_segmentada_por_solo.geojson")
        gdf_intersected.to_file(output_path, driver="GeoJSON")
        results['output_path'] = output_path

        progress_callback("Interseção concluída!", 100)
        return results


METRIC_CRS = 'esri:102033'
BRENTQ_UPPER_LIMIT_M = 500.0


def find_buffer_distance_for_area(geometry, target_area, search_min, search_max):

    def area_difference(distance):
        return geometry.buffer(distance).area - target_area

    try:
        distance_needed = brentq(area_difference, a=search_min, b=search_max, xtol=0.01)
        return distance_needed
    except ValueError as e:
        raise ValueError(f"Scipy brentq falhou no range [{search_min}, {search_max}m]. {e}")


def calculate_area_buffers(gdf, metric_crs, percent_change):
    if gdf.empty:
        return gdf.copy(), gdf.copy()

    gdf_proj = gdf.to_crs(metric_crs)
    geoms_plus, geoms_minus = [], []

    factor_plus = 1.0 + (percent_change / 100.0)
    factor_minus = 1.0 - (percent_change / 100.0)

    for index, row in gdf_proj.iterrows():
        geom = row.geometry
        if geom.is_empty or not geom.is_valid:
            geoms_plus.append(geom)
            geoms_minus.append(geom)
            continue

        area_original_m2 = geom.area
        area_target_plus = area_original_m2 * factor_plus
        area_target_minus = area_original_m2 * factor_minus

        dist_pos, dist_neg = None, None

        try:
            dist_pos = find_buffer_distance_for_area(geom, area_target_plus, 0.0, BRENTQ_UPPER_LIMIT_M)
        except ValueError:
            pass

        try:
            dist_neg = find_buffer_distance_for_area(geom, area_target_minus, -BRENTQ_UPPER_LIMIT_M, 0.0)
        except ValueError:
            pass

        geoms_plus.append(geom.buffer(dist_pos) if dist_pos is not None else geom)
        geoms_minus.append(geom.buffer(dist_neg) if dist_neg is not None else geom)

    gdf_plus = gdf_proj.copy()
    gdf_plus['geometry'] = geoms_plus
    gdf_minus = gdf_proj.copy()
    gdf_minus['geometry'] = geoms_minus

    return gdf_plus, gdf_minus


def run_proportional_buffer(geojson_path, reference_column, percentage_mapping, output_dir, progress_callback):
    results = {}
    progress_callback("Iniciando buffer proporcional...", 5)

    temp_dir = os.path.join(output_dir, "temp_buffer")
    os.makedirs(temp_dir, exist_ok=True)

    geojson_file_to_read = _handle_zip(geojson_path, temp_dir)

    try:
        gdf_original = gpd.read_file(geojson_file_to_read)
    except Exception as e:
        raise FileNotFoundError(f"ERRO: Falha ao carregar GeoDataFrame: {e}")

    if reference_column not in gdf_original.columns:
        raise ValueError(
            f"ERRO: A coluna de referência '{reference_column}' não foi encontrada. Colunas disponíveis: {list(gdf_original.columns)}")

    try:
        gdf_original[reference_column] = pd.to_numeric(gdf_original[reference_column])
    except ValueError:
        raise ValueError(f"ERRO: Não foi possível converter a coluna '{reference_column}' para numérico.")

    original_crs = gdf_original.crs if gdf_original.crs else 'EPSG:4326'
    buffered_gdfs = []

    mapping_float_keys = {float(k): float(v) for k, v in percentage_mapping.items()}

    unique_values_in_gdf = gdf_original[reference_column].dropna().unique()
    values_to_process = [val for val in unique_values_in_gdf if val in mapping_float_keys]

    if not values_to_process:
        raise ValueError(
            f"Nenhum valor na coluna '{reference_column}' corresponde às chaves no Mapeamento de Pesos. Valores do GDF: {unique_values_in_gdf}")

    total_steps = len(values_to_process)
    current_step = 0

    for col_value in sorted(values_to_process):
        percent = mapping_float_keys[col_value]
        current_step += 1
        progress_percentage = 10 + int((current_step / total_steps) * 80)
        progress_callback(f"Processando valor '{col_value}' com Buffer de {percent:+}%...", progress_percentage)

        gdf_filtered = gdf_original[gdf_original[reference_column] == col_value].copy()
        if gdf_filtered.empty:
            continue

        gdf_plus_proj, gdf_minus_proj = calculate_area_buffers(
            gdf_filtered,
            METRIC_CRS,
            abs(percent)
        )

        is_positive = percent >= 0
        gdf_final_proj = gdf_plus_proj if is_positive else gdf_minus_proj

        gdf_final_crs = gdf_final_proj.to_crs(original_crs)
        buffered_gdfs.append(gdf_final_crs)

    if buffered_gdfs:
        progress_callback("Mesclando resultados...", 95)
        gdf_merged = gpd.GeoDataFrame(
            pd.concat(buffered_gdfs, ignore_index=True),
            crs=original_crs
        )

        final_merge_path = os.path.join(output_dir, "inundacao_adsolo_buffer.geojson")
        gdf_merged.to_file(final_merge_path, driver='GeoJSON')
        results['merge_path'] = final_merge_path
        progress_callback("Buffer proporcional concluído!", 100)
    else:
        raise ValueError("Nenhuma geometria foi processada para o merge final.")

    return results