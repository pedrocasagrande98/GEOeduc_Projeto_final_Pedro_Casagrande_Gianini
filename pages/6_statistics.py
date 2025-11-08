import streamlit as st
import geopandas as gpd
import leafmap.foliumap as leafmap
import os

# Configuração da página
st.set_page_config(
    page_title="📊 Análise Quantitativa",
    page_icon="🛰️",
    layout="wide"
)

# Garante que o diretório de saída existe
OUTPUT_DIR = "outputs/6"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Função para calcular o impacto
def calculate_impact(analysis_gdf, data_gdf):
    """
    Calcula a interseção, a porcentagem de impacto e as feições não afetadas.
    """
    try:
        if analysis_gdf.empty or data_gdf.empty:
            st.warning("Uma ou ambas as camadas estão vazias.")
            return 0.0, gpd.GeoDataFrame(), gpd.GeoDataFrame(), 0

        total_data_count = len(data_gdf)

        # Cria uma cópia para o dissolve, preservando o original para o summary
        analysis_dissolved = analysis_gdf.copy()
        analysis_dissolved['temp_id'] = 1
        analysis_dissolved = analysis_dissolved.dissolve(by='temp_id')

        if analysis_dissolved.crs != data_gdf.crs:
            data_gdf = data_gdf.to_crs(analysis_dissolved.crs)

        affected_features = gpd.sjoin(data_gdf, analysis_dissolved, how='inner', predicate='intersects')
        affected_features = affected_features[~affected_features.index.duplicated(keep='first')]

        affected_count = len(affected_features)
        percentage_affected = (affected_count / total_data_count) * 100 if total_data_count > 0 else 0.0

        unaffected_indices = ~data_gdf.index.isin(affected_features.index)
        unaffected_features = data_gdf.loc[unaffected_indices]

        return percentage_affected, affected_features, unaffected_features, total_data_count

    except Exception as e:
        st.error(f"Erro ao calcular o impacto: {e}")
        return 0.0, gpd.GeoDataFrame(), gpd.GeoDataFrame(), 0

# Função para exibir o mapa
def display_map(gdf_analysis, gdf_data, affected_features):
    """Exibe o mapa com as camadas de análise, dados e feições afetadas."""
    st.header("Visualização do Mapa")
    m = leafmap.Map()

    style_analysis = {'color': 'blue', 'fillColor': 'blue', 'weight': 1.5, 'fillOpacity': 0.4}
    style_data = {'color': 'orange', 'fillColor': '#black', 'weight': 0.5, 'fillOpacity': 0.5}
    style_affected = {'color': 'red', 'weight': 2.5, 'fillColor': 'red', 'fillOpacity': 0.7}

    m.add_gdf(gdf_analysis, layer_name='Camada de Análise', style=style_analysis)
    m.add_gdf(gdf_data, layer_name='Camada de Dados', style=style_data)
    if affected_features is not None and not affected_features.empty:
        m.add_gdf(affected_features, layer_name='Feições Afetadas', style=style_affected)
    
    m.to_streamlit(key="map_quantitative")

# --- Interface Principal ---

st.markdown(
    """
    Esta análise quantitativa calcula o número e a porcentagem de feições de uma camada de dados
    que são interceptadas por uma camada de análise (poligonal). 
    Faça o upload das duas camadas para iniciar.
    """
)

col1, col2 = st.columns([1, 1])

with col1:
    st.header("Upload de Camadas")
    analysis_layer = st.file_uploader(
        "Carregue a camada de Análise (Polígono)",
        type=["geojson", "gpkg", "shp", "zip"],
        key="analysis"
    )
    data_layer = st.file_uploader(
        "Carregue a camada de Dados (Pontos, Linhas ou Polígonos)",
        type=["geojson", "gpkg", "shp", "zip"],
        key="data"
    )
    run_analysis = st.button("Iniciar Análise Quantitativa", key="run_analysis")

# A análise só é executada quando o botão é pressionado
if run_analysis:
    if not analysis_layer or not data_layer:
        st.warning("Por favor, carregue as duas camadas (Análise e Dados) antes de iniciar a análise.")
        st.stop()

    try:
        gdf_analysis = gpd.read_file(analysis_layer)
        gdf_data = gpd.read_file(data_layer)
        
        percentage_affected, affected_features, unaffected_features, total_count = calculate_impact(gdf_analysis, gdf_data)

        if percentage_affected is not None:
            with col2:
                st.header("Resultados da Análise")
                st.metric("Total de feições na camada de dados", f"{total_count:,}")
                st.metric("Feições afetadas pela camada de análise", f"{len(affected_features):,}")
                st.metric("Percentual de feições afetadas", f"{percentage_affected:.2f}%")

                # --- GERAÇÃO E DOWNLOAD DOS ARQUIVOS DE SAÍDA ---

                # 1. Arquivo com as feições impactadas
                if not affected_features.empty:
                    output_path_impactados = os.path.join(OUTPUT_DIR, "impactados.geojson")
                    affected_features.to_file(output_path_impactados, driver='GeoJSON')
                    st.success(f"Arquivo de feições impactadas salvo em: `{output_path_impactados}`")

                    with open(output_path_impactados, "rb") as fp:
                        st.download_button(
                            label="Baixar Feições Afetadas (impactados.geojson)",
                            data=fp,
                            file_name="impactados.geojson",
                            mime="application/geo+json",
                            key="download_impactados"
                        )

                # 2. Arquivo de resumo com estatísticas
                analysis_summary_gdf = gdf_analysis.copy()
                analysis_summary_gdf['temp_id'] = 1
                analysis_summary_gdf = analysis_summary_gdf.dissolve(by='temp_id')

                analysis_summary_gdf['total'] = total_count
                analysis_summary_gdf['afetados'] = len(affected_features)
                analysis_summary_gdf['percent'] = round(percentage_affected, 2)

                output_path_summary = os.path.join(OUTPUT_DIR, "camada_analise_stats.geojson")
                analysis_summary_gdf.to_file(output_path_summary, driver='GeoJSON')
                st.success(f"Arquivo de resumo da análise salvo em: `{output_path_summary}`")

                with open(output_path_summary, "rb") as fp:
                    st.download_button(
                        label="Baixar Resumo da Análise (camada_analise_stats.geojson)",
                        data=fp,
                        file_name="camada_analise_stats.geojson",
                        mime="application/geo+json",
                        key="download_summary"
                    )

            # O mapa é exibido fora da coluna para ocupar a largura total
            display_map(gdf_analysis, gdf_data, affected_features)

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os arquivos: {e}")
else:
    with col2:
        st.info("Aguardando o upload das duas camadas para iniciar a análise.")
