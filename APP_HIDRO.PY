import streamlit as st
# O módulo MDE_LULC foi movido para o diretório 'mod1_SRTM_LULC'
from scripts.MDE_LULC import app as mde_app #Módulo 1 para obter SRTM + MAPBIOMAS
#from



##     streamlit run app_hidro.py


def main():
    # Configuração da página
    st.set_page_config(
        page_title="Hydro-Analysis Integrado",
        page_icon="🌿",
        layout="wide"
    )
    
    # Cabeçalho principal
    st.title("🌿 Análise Hidrográfica Integrada 🛰️")
    
    # Como a aplicação foi simplificada, não usamos mais abas.
    # Chamamos diretamente a função do módulo de análise de MDE e Uso do Solo.
    mde_app()

if __name__ == "__main__":
    main()
