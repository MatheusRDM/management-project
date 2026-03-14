"""
Afirma E-vias - Sistema de Gestão de Ensaios
Página Principal com Navegação
"""
import streamlit as st

# Importar estilos globais padronizados
from styles import aplicar_estilos, renderizar_sidebar, renderizar_footer, CORES

# ======================================================================================
# CONFIGURAÇÃO DA PÁGINA PRINCIPAL
# ======================================================================================
st.set_page_config(
    page_title="Afirma E-vias | Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Aplicar estilos globais
aplicar_estilos()

# Ocultar sidebar e botão de toggle na página principal (home/login)
st.markdown("""
<style>
    section[data-testid="stSidebar"] { display: none !important; }
    button[data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ======================================================================================
# LÓGICA PRINCIPAL
# ======================================================================================

def main():
    # Container principal
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Header com Logo
    col_logo, col_titulo = st.columns([0.8, 4])
    with col_logo:
        try:
            logo_path = r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias\Manual Completo\Identidade Visual\Logotipo e Variações\Símbolo e Selos\PNG\Selo C Ass\Selo C Ass_4.png"
            st.image(logo_path, width=195)
        except Exception:
            st.markdown(f"""
            <div style="background: {CORES['secundario']}; padding: 1rem; border-radius: 8px; text-align: center;">
                <h3 style="color: white; margin: 0;">AFIRMA E-VIAS</h3>
            </div>
            """, unsafe_allow_html=True)
    
    with col_titulo:
        st.markdown(f"""
        <div style="padding-left: 1rem;">
            <h1 style="margin: 0; font-size: 2.5rem !important;">AE - Dashboard</h1>
            <p style="color: {CORES['destaque']}; font-size: 1.2rem; margin-top: 0.5rem;">Sistema de Gestão de Ensaios e Relatórios Técnicos</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Cards de navegação - Linha 1
    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        st.markdown("""
        <div class="nav-card">
            <div class="icon">📊</div>
            <h3>Dashboard de Certificados</h3>
            <p>Análise Quantitativa de Ensaios - FORM 067</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Acessar Dashboard", key="dashboard_btn", use_container_width=True):
            st.switch_page("pages/01_Dashboard_Certificados.py")

    with col2:
        st.markdown("""
        <div class="nav-card">
            <div class="icon">📅</div>
            <h3>Cronograma de Ensaios</h3>
            <p>Panorama Geral de Ensaios</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Acessar Cronograma", key="cronograma_btn", use_container_width=True):
            st.switch_page("pages/02_Cronograma_Relatorios.py")

    with col3:
        st.markdown("""
        <div class="nav-card">
            <div class="icon">🛣️</div>
            <h3>EPR Litoral Pioneiro</h3>
            <p>Acompanhamento de Ensaios — FORM 022A</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Acessar EPR", key="epr_btn", use_container_width=True):
            st.switch_page("pages/03_EPR_Litoral_Pioneiro.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # Cards de navegação - Linha 2
    col4, col5, col6 = st.columns(3, gap="large")

    with col4:
        st.markdown("""
        <div class="nav-card">
            <div class="icon">🗺️</div>
            <h3>Mapeamento de Projetos CAUQ</h3>
            <p>Distribuição Geográfica · Marshall · Ensaios de Agregados</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Acessar Mapeamento CAUQ", key="cauq_btn", use_container_width=True):
            st.switch_page("pages/04_Mapeamento_CAUQ.py")
    
    # Informações adicionais
    st.markdown("---")
    
    # Card informativo
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #566E3D 0%, #6a8a4a 100%); 
                border-radius: 16px; border: 3px solid #BFCF99; transition: all 0.3s ease; max-width: 600px; margin: 0 auto;"
         onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 15px 40px rgba(86,110,61,0.5)';"
         onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
        <h4 style="color: #FFFFFF; margin-bottom: 1rem; font-size: 1.3rem;">Laboratório Acreditado - ISO 17025</h4>
        <p style="color: #EFEBDC; font-size: 1.1rem; margin: 0;">Centro de Pesquisa Rodoviária</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Footer padronizado
    renderizar_footer()
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
