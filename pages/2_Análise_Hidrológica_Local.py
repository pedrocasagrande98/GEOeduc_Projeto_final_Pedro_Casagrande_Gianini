import streamlit as st
import os
import tempfile
import time
from scripts.local_analysis_helpers import run_preprocessing, run_delineation

st.set_page_config(
    page_title="🌊 Análise Hidrológica Local (PySheds)",  # Você pode customizar o título para cada página
    page_icon="🛰️",                     # Mantenha o mesmo ícone
    layout="wide"                      # E o mesmo layout
)


# Garante que o diretório de saída existe
OUTPUT_DIR = "outputs/2"
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

# --- ETAPA 1: PRÉ-PROCESSAMENTO ---
st.header("Etapa 1: Pré-processamento do MDE")
st.info(
    "Faça o upload do seu MDE (ex: `srtm_data.tif`). Esta etapa irá condicionar o MDE, calcular direção/acumulação de fluxo, declividade, TWI e extrair a rede de drenagem completa.")

uploaded_mde = st.file_uploader("Selecione o arquivo MDE (.tif, .tiff)", type=["tif", "tiff"])
stream_threshold = st.number_input("Limiar de Drenagem (células)", min_value=100, max_value=10000, value=1000, step=100,
                                   help="Define a área mínima para formar um 'rio'.")

if st.button("Executar Pré-processamento", type="primary"):
    if uploaded_mde is not None:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Salva o MDE uploadado em um local temporário
            mde_temp_path = os.path.join(temp_dir, uploaded_mde.name)
            with open(mde_temp_path, "wb") as f:
                f.write(uploaded_mde.getbuffer())

            st.info(f"Arquivo MDE '{uploaded_mde.name}' carregado.")

            # Placeholder para barra de progresso e status
            progress_bar = st.progress(0, text="Iniciando pré-processamento...")
            status_text = st.empty()


            # Função de callback para atualizar o progresso
            def update_progress(message, percentage):
                status_text.info(message)
                progress_bar.progress(percentage, text=message)
                time.sleep(0.1)  # Pequena pausa para UI atualizar


            try:
                # Chama a função de lógica pesada
                with st.spinner("Processando MDE... Isso pode levar vários minutos."):
                    results = run_preprocessing(mde_temp_path, OUTPUT_DIR, stream_threshold, update_progress)

                # Armazena os resultados no session_state para a Etapa 2
                st.session_state['preprocessing_results'] = results
                st.session_state['preprocessing_complete'] = True

                progress_bar.progress(100, text="Pré-processamento concluído!")
                status_text.success(f"Pré-processamento concluído com sucesso! Arquivos gerados em '{OUTPUT_DIR}'.")
                st.success("Pronto para a Etapa 2.")

            except Exception as e:
                st.error(f"Erro durante o pré-processamento: {e}")
                st.exception(e)

# --- ETAPA 2: DELINEAMENTO DA BACIA E HAND ---
if 'preprocessing_complete' in st.session_state and st.session_state['preprocessing_complete']:
    st.markdown("---")
    st.header("Etapa 2: Delinear Bacia e Mancha de Inundação")
    st.info(
        "Insira as coordenadas do exutório (ponto de saída) e a profundidade do canal para simular a inundação (HAND).")

    col1, col2 = st.columns(2)
    with col1:
        outlet_lon = st.number_input("Longitude do Exutório (X)", value=-44.118627, format="%.6f")
    with col2:
        outlet_lat = st.number_input("Latitude do Exutório (Y)", value=-20.316243, format="%.6f")

    channel_depth = st.number_input("Profundidade do Canal (metros)", min_value=1.0, max_value=50.0, value=10.0,
                                    step=0.5,
                                    help="Altura da água no canal para simulação HAND (ex: 10.0 para TR 100 anos).")
    
    generate_flu_distance = st.checkbox("Gerar camada de Distância do Fluxo (flu_distance.tif)", value=False,
                                        help="Opcional. Gera a camada de distância de fluxo. Pode consumir muitos recursos para áreas grandes.")

    if st.button("Executar Delineamento e Simulação HAND", type="primary"):
        # Recupera os dados da Etapa 1
        preproc_results = st.session_state['preprocessing_results']

        # Placeholder para progresso
        progress_bar_2 = st.progress(0, text="Iniciando delineamento...")
        status_text_2 = st.empty()


        # Função de callback
        def update_progress_2(message, percentage):
            status_text_2.info(message)
            progress_bar_2.progress(percentage, text=message)
            time.sleep(0.1)


        try:
            with st.spinner("Calculando bacia, HAND e mancha de inundação..."):
                delineation_results = run_delineation(
                    preproc_data=preproc_results,
                    outlet_coords=(outlet_lon, outlet_lat),
                    channel_depth=channel_depth,
                    stream_threshold=stream_threshold,
                    output_dir=OUTPUT_DIR,
                    progress_callback=update_progress_2,
                    generate_flu_distance=generate_flu_distance
                )

            progress_bar_2.progress(100, text="Processo concluído!")
            status_text_2.success("Delineamento e simulação HAND concluídos!")

            # Exibe os botões de download
            st.subheader("Resultados para Download")
            st.markdown(f"Arquivos salvos no diretório `{OUTPUT_DIR}`.")

            col_res1, col_res2, col_res3 = st.columns(3)

            with col_res1:
                st.markdown("**Bacia e Canais**")
                if delineation_results.get('bacia_path'):
                    with open(delineation_results['bacia_path'], "rb") as f:
                        st.download_button("Baixar Bacia (bacia.geojson)", f, file_name="bacia.geojson")
                if delineation_results.get('canais_path'):
                    with open(delineation_results['canais_path'], "rb") as f:
                        st.download_button("Baixar Canais (canais_strahler.geojson)", f,
                                           file_name="canais_strahler.geojson")
                if delineation_results.get('exutorio_path'):
                    with open(delineation_results['exutorio_path'], "rb") as f:
                        st.download_button("Baixar Exutório (exutorio.geojson)", f, file_name="exutorio.geojson")

            with col_res2:
                st.markdown("**Mancha de Inundação (HAND)**")
                suffix = delineation_results.get('suffix', 'simulacao')
                if delineation_results.get('inundacao_vetor_path'):
                    fname_vec = f"inundacao_{suffix}.geojson"
                    with open(delineation_results['inundacao_vetor_path'], "rb") as f:
                        st.download_button(f"Baixar Inundação (Vetor)", f, file_name=fname_vec)
                if delineation_results.get('inundacao_raster_path'):
                    fname_ras = f"inundacao_mapa_{suffix}.tif"
                    with open(delineation_results['inundacao_raster_path'], "rb") as f:
                        st.download_button(f"Baixar Inundação (Raster)", f, file_name=fname_ras)

            with col_res3:
                st.markdown("**Rasters Hidrológicos**")
                if delineation_results.get('dist_path'):
                    with open(delineation_results['dist_path'], "rb") as f:
                        st.download_button("Baixar Distância do Fluxo (flu_distance.tif)", f,
                                           file_name="flu_distance.tif")


        except Exception as e:
            st.error(f"Erro durante o delineamento: {e}")
            st.exception(e)

else:
    st.info("Execute a Etapa 1 para habilitar o delineamento da bacia.")