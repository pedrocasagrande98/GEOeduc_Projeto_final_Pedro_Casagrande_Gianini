import streamlit as st
import os
import tempfile
import time
import pandas as pd
import shutil
from scripts.local_analysis_helpers import run_soil_intersection, run_proportional_buffer

st.set_page_config(
    page_title="🌱 Modelo de Risco Ponderado por Solo",  # Você pode customizar o título para cada página
    page_icon="🛰️",                     # Mantenha o mesmo ícone
    layout="wide"                      # E o mesmo layout
)


# Garante que o diretório de saída existe
OUTPUT_DIR = "outputs/3"
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
    .st-emotion-cache-10trblm { /* Expander header */
        font-weight: bold;
        color: #FF4B4B; /* Cor chamativa para o título dos pesos */
    }
    </style>
""", unsafe_allow_html=True)


# --- FUNÇÃO PARA RENDERIZAR OS PESOS (CORRIGIDA E REORGANIZADA) ---
def render_weight_editor(key_prefix: str):
    """
    Renderiza a seção de edição de pesos do modelo com layout horizontal.
    (Versão corrigida sem a Classe 0).

    Args:
        key_prefix (str): Um prefixo único para as chaves dos widgets.
    """

    st.markdown("---")
    st.markdown("### ⚠️ Definições de Pesos (Modelo de Risco)")
    st.caption(
        "Defina a porcentagem de buffer (+/-) para cada classe de solo. Valores baseados na hipótese de capacidade de infiltração (Argiloso = buffer +, Arenoso = buffer -).")

    # Valores padrão (CORRIGIDO: Classe 0 removida)
    default_weights = {
        # 0: 0.0,   # <-- Reclassificado para 7
        1: 55.0,  # AD1 (Argiloso/Saturado)
        2: 35.0,  # AD2 (Argiloso/Médio)
        3: 15.0,  # AD3 (Argiloso/Pouco)
        4: -15.0, # AD4 (Arenoso/Pouco)
        5: -35.0, # AD5 (Arenoso/Médio)
        6: -55.0, # AD6 (Arenoso/Saturado)
        7: 0.0,   # Classe 7 (Urbano/Água, assumindo neutro)
    }

    weights = {}

    # --- NOVA ORGANIZAÇÃO (LINHA POR LINHA) ---

    # LINHA 1 (Classes 1, 2, 3)
    col1, col2, col3 = st.columns(3)
    with col1:
        # A Classe 0 foi removida daqui
        weights[1] = st.number_input("Peso Classe 1 (%)", value=default_weights[1], step=1.0,
                                     key=f"{key_prefix}_class_1")
    with col2:
        weights[2] = st.number_input("Peso Classe 2 (%)", value=default_weights[2], step=1.0,
                                     key=f"{key_prefix}_class_2")
    with col3:
        weights[3] = st.number_input("Peso Classe 3 (%)", value=default_weights[3], step=1.0,
                                     key=f"{key_prefix}_class_3")

    # LINHA 2 (Classes 4, 5, 6)
    col1, col2, col3 = st.columns(3) # Chamamos st.columns() DE NOVO para uma nova linha
    with col1:
        weights[4] = st.number_input("Peso Classe 4 (%)", value=default_weights[4], step=1.0,
                                     key=f"{key_prefix}_class_4")
    with col2:
        weights[5] = st.number_input("Peso Classe 5 (%)", value=default_weights[5], step=1.0,
                                     key=f"{key_prefix}_class_5")
    with col3:
        weights[6] = st.number_input("Peso Classe 6 (%)", value=default_weights[6], step=1.0,
                                     key=f"{key_prefix}_class_6")

    # LINHA 3 (Classe 7)
    col1, col2, col3 = st.columns(3) # E mais uma vez...
    with col1:
        weights[7] = st.number_input("Peso Classe 7 (%)", value=default_weights[7], step=1.0,
                                     key=f"{key_prefix}_class_7")
    # col2 e col3 ficam vazias, o que está correto para 7 itens.

    return weights

# --- FUNÇÃO PARA EXECUTAR O BUFFER (MODIFICADA) ---
def execute_buffer_logic(input_file_path, reference_column, weights_mapping, temp_dir):
    """Função reutilizável para executar a lógica de buffer."""

    progress_bar = st.progress(0, text="Iniciando buffer proporcional...")
    status_text = st.empty()

    def update_progress(message, percentage):
        status_text.info(message)
        progress_bar.progress(percentage, text=message)
        time.sleep(0.1)

    try:
        with st.spinner("Calculando buffers proporcionais... (Pode demorar)"):
            buffer_results = run_proportional_buffer(
                geojson_path=input_file_path,
                reference_column=reference_column,
                percentage_mapping=weights_mapping,
                output_dir=temp_dir,  # Salva resultados no temp_dir
                progress_callback=update_progress
            )

        progress_bar.progress(100, text="Buffer concluído!")
        status_text.success("Modelo de Risco (Buffer) concluído!")

        # --- MODIFICADO: Salvar automaticamente, sem botão de download ---
        if buffer_results.get('merge_path'):

            # Caminho do arquivo final dentro do temp_dir
            source_path = buffer_results['merge_path']

            # Nome do arquivo final (padrão)
            file_name = "inundacao_adsolo_buffer.geojson"

            # Caminho de destino na pasta 'outputs'
            destination_path = os.path.join(OUTPUT_DIR, file_name)

            # Move o arquivo do temp_dir para o 'outputs/'
            shutil.move(source_path, destination_path)

            st.subheader("Resultado Salvo!")
            st.success(f"Arquivo final salvo automaticamente em:\n`{destination_path}`")

        else:
            st.warning("Nenhum arquivo de merge foi gerado.")
        # --- FIM DA MODIFICAÇÃO ---

    except Exception as e:
        st.error(f"Erro durante o cálculo do buffer: {e}")
        st.exception(e)


# --- INTERFACE DE ABAS ---
tab1, tab2 = st.tabs([
    "Fluxo Completo (Etapa 1 + 2)",
    "Apenas Etapa 2 (Já tenho os dados)"
])

# --- ABA 1: FLUXO COMPLETO (MODIFICADA) ---
with tab1:
    st.header("Etapa 1: Interseção Raster + Vetor")
    st.info("Faça upload do Raster de Solos e do Vetor de Inundação (ou AOI) para criar a camada segmentada.")

    uploaded_raster = st.file_uploader("Upload do Raster de Solos (ex: ad_solo.tif)", type=["tif", "tiff"],
                                       key="tab1_raster")
    uploaded_vector = st.file_uploader("Upload do Vetor de Inundação (ou AOI)", type=["geojson", "gpkg", "zip"],
                                       key="tab1_vector")

    if st.button("Executar Etapa 1: Interseção", type="primary"):
        if uploaded_raster and uploaded_vector:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Salva arquivos temporários
                raster_temp_path = os.path.join(temp_dir, uploaded_raster.name)
                with open(raster_temp_path, "wb") as f:
                    f.write(uploaded_raster.getbuffer())

                vector_temp_path = os.path.join(temp_dir, uploaded_vector.name)
                with open(vector_temp_path, "wb") as f:
                    f.write(uploaded_vector.getbuffer())

                progress_bar_1 = st.progress(0, text="Iniciando interseção...")
                status_text_1 = st.empty()


                def update_progress_1(message, percentage):
                    status_text_1.info(message)
                    progress_bar_1.progress(percentage, text=message)


                try:
                    with st.spinner("Processando interseção (rasterio mask)..."):
                        intersect_results = run_soil_intersection(
                            raster_path=raster_temp_path,
                            vector_path=vector_temp_path,
                            output_dir=temp_dir,  # <-- Salva no temp_dir
                            progress_callback=update_progress_1
                        )

                    progress_bar_1.progress(100, "Interseção concluída!")
                    status_text_1.success("Arquivo segmentado gerado com sucesso!")

                    # --- MODIFICAÇÃO: Mover arquivo intermediário para 'outputs' ---

                    # 1. Obter o caminho do arquivo temporário
                    intermediate_source_path = intersect_results['output_path']
                    intermediate_file_name = "inundacao_segmentada_por_solo.geojson"

                    # 2. Definir o caminho de destino permanente
                    intermediate_dest_path = os.path.join(OUTPUT_DIR, intermediate_file_name)

                    # 3. Mover o arquivo
                    shutil.move(intermediate_source_path, intermediate_dest_path)

                    # 4. Salvar o NOVO caminho (permanente) na session_state
                    st.session_state['segmented_file_path_tab1'] = intermediate_dest_path
                    st.session_state['ready_for_buffer_tab1'] = True

                    # 5. Atualizar o botão de download para usar o novo caminho
                    st.success(f"Arquivo intermediário salvo em: `{intermediate_dest_path}`")
                    with open(intermediate_dest_path, "rb") as f:
                        st.download_button(
                            "Baixar Resultado Intermediário (Opcional)",
                            f,
                            file_name=intermediate_file_name
                        )
                    # --- FIM DA MODIFICAÇÃO ---

                except Exception as e:
                    st.error(f"Erro na Etapa 1: {e}")
                    st.exception(e)
        else:
            st.warning("Por favor, faça o upload do raster e do vetor.")

    # --- Etapa 2 da Aba 1 ---
    # Verifica se a Etapa 1 foi concluída com sucesso
    if st.session_state.get('ready_for_buffer_tab1', False):

        # Chama a função de pesos com uma CHAVE ÚNICA
        weights = render_weight_editor(key_prefix="tab1_weights")

        if st.button("Executar Etapa 2: Buffer Proporcional", type="primary", key="tab1_buffer_btn"):
            if 'segmented_file_path_tab1' in st.session_state and os.path.exists(
                    st.session_state['segmented_file_path_tab1']):
                # Usamos um novo temp_dir para a lógica do buffer
                with tempfile.TemporaryDirectory() as temp_dir_2:
                    execute_buffer_logic(
                        input_file_path=st.session_state['segmented_file_path_tab1'],  # <-- Usa o caminho permanente
                        reference_column="valor_solo",  # Padrão da Etapa 1
                        weights_mapping=weights,
                        temp_dir=temp_dir_2  # Passa o novo temp_dir
                    )
            else:
                st.error(
                    "Erro: O arquivo da Etapa 1 não foi encontrado (ou foi removido). Por favor, execute a Etapa 1 novamente.")

# --- ABA 2: APENAS ETAPA 2 (BUFFER) ---
with tab2:
    st.header("Etapa 2: Buffer Proporcional com Pesos")
    st.info("Use esta aba se você já possui um arquivo vetorial com uma coluna de classes de solo (ex: 'valor_solo').")

    uploaded_segmented_vector = st.file_uploader("Upload do Vetor Segmentado", type=["geojson", "gpkg", "zip"],
                                                 key="tab2_vector")
    ref_col = st.text_input("Nome da Coluna de Referência", value="valor_solo",
                            help="O nome da coluna que contém os valores de 0 a 6.")

    # Chama a função de pesos com uma CHAVE ÚNICA diferente
    weights_tab2 = render_weight_editor(key_prefix="tab2_weights")

    if st.button("Executar Etapa 2: Buffer Proporcional", type="primary", key="tab2_buffer_btn"):
        if uploaded_segmented_vector and ref_col:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Salva o arquivo temporário
                vector_temp_path = os.path.join(temp_dir, uploaded_segmented_vector.name)
                with open(vector_temp_path, "wb") as f: f.write(uploaded_segmented_vector.getbuffer())

                # Executa a lógica de buffer
                execute_buffer_logic(
                    input_file_path=vector_temp_path,
                    reference_column=ref_col,
                    weights_mapping=weights_tab2,
                    temp_dir=temp_dir
                )
        else:
            st.warning("Por favor, faça o upload do vetor e especifique a coluna de referência.")