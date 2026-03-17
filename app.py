"""
Afirma E-vias - Sistema de Gestão de Ensaios
Página Principal com Login e Navegação
"""
import streamlit as st

# Importar estilos globais padronizados
from styles import aplicar_estilos, renderizar_footer, CORES
from auth import mostrar_tela_login, verificar_autenticacao, fazer_logout, get_paginas_permitidas
from cloud_config import get_logo_path

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

# Ocultar sidebar e botão de toggle
st.markdown("""
<style>
    section[data-testid="stSidebar"] { display: none !important; }
    button[data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ======================================================================================
# LÓGICA DE AUTENTICAÇÃO
# ======================================================================================
if not verificar_autenticacao():
    mostrar_tela_login()
    st.stop()

# ======================================================================================
# DASHBOARD (após login)
# ======================================================================================
usuario = st.session_state.get('usuario', '')
paginas_permitidas = get_paginas_permitidas(usuario)

def main():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    # Header com Logo e botão de logout
    col_logo, col_titulo, col_logout = st.columns([1, 4, 1])
    with col_logo:
        _logo = get_logo_path("selo_c_ass")
        if _logo:
            try:
                st.image(_logo, use_container_width=True)
            except Exception:
                pass
        if not _logo:
            st.markdown(f"""
            <div style="background: {CORES['secundario']}; padding: 1rem; border-radius: 8px; text-align: center;">
                <h3 style="color: white; margin: 0;">AFIRMA E-VIAS</h3>
            </div>
            """, unsafe_allow_html=True)

    with col_titulo:
        st.markdown(f"""
        <div style="padding-left: 1rem;">
            <h1 style="margin: 0; font-size: 2.5rem !important;">AE - Dashboard</h1>
            <p style="color: {CORES['destaque']}; font-size: 1.2rem; margin-top: 0.5rem;">
                Sistema de Gestão de Ensaios e Relatórios Técnicos &nbsp;|&nbsp;
                <span style="font-weight: bold;">👤 {usuario}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_logout:
        st.write("")
        if st.button("🚪 Logout", use_container_width=True):
            fazer_logout()

    st.markdown("---")

    # Definição de todos os cards
    CARDS = [
        {
            "pagina": "Dashboard de Certificados",
            "icon": "📊",
            "titulo": "Dashboard de Certificados",
            "descricao": "Análise Quantitativa de Ensaios - FORM 067",
            "btn_label": "Acessar Dashboard",
            "btn_key": "dashboard_btn",
            "arquivo": "pages/01_Dashboard_Certificados.py"
        },
        {
            "pagina": "Cronograma de Ensaios",
            "icon": "📅",
            "titulo": "Cronograma de Ensaios",
            "descricao": "Panorama Geral de Ensaios",
            "btn_label": "Acessar Cronograma",
            "btn_key": "cronograma_btn",
            "arquivo": "pages/02_Cronograma_Relatorios.py"
        },
        {
            "pagina": "EPR Litoral Pioneiro",
            "icon": "🛣️",
            "titulo": "EPR Litoral Pioneiro",
            "descricao": "Acompanhamento de Ensaios — FORM 022A",
            "btn_label": "Acessar EPR",
            "btn_key": "epr_btn",
            "arquivo": "pages/03_EPR_Litoral_Pioneiro.py"
        },
        {
            "pagina": "Mapeamento de Projetos CAUQ",
            "icon": "🗺️",
            "titulo": "Mapeamento de Projetos CAUQ",
            "descricao": "Distribuição Geográfica · Marshall · Ensaios de Agregados",
            "btn_label": "Acessar Mapeamento CAUQ",
            "btn_key": "cauq_btn",
            "arquivo": "pages/04_Mapeamento_CAUQ.py"
        },
        {
            "pagina": "Performance de Contratos",
            "icon": "📊",
            "titulo": "Performance de Contratos",
            "descricao": "Rateio de Pessoal · Alocação por Contrato · Medições",
            "btn_label": "Acessar Performance",
            "btn_key": "performance_btn",
            "arquivo": "pages/05_Performance_Contratos.py"
        },
    ]

    # Filtrar apenas as páginas que o usuário tem acesso
    cards_visiveis = [c for c in CARDS if c["pagina"] in paginas_permitidas]

    # Renderizar em linhas de 3 colunas
    for i in range(0, len(cards_visiveis), 3):
        grupo = cards_visiveis[i:i+3]
        cols = st.columns(len(grupo), gap="large")
        for col, card in zip(cols, grupo):
            with col:
                st.markdown(f"""
                <div class="nav-card">
                    <div class="icon">{card['icon']}</div>
                    <h3>{card['titulo']}</h3>
                    <p>{card['descricao']}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(card["btn_label"], key=card["btn_key"], use_container_width=True):
                    st.switch_page(card["arquivo"])

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # Card informativo
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #566E3D 0%, #6a8a4a 100%);
                border-radius: 16px; border: 3px solid #BFCF99; max-width: min(600px, 90vw); margin: 0 auto;">
        <h4 style="color: #FFFFFF; margin-bottom: 1rem; font-size: 1.3rem;">Laboratório Acreditado - ISO 17025</h4>
        <p style="color: #EFEBDC; font-size: 1.1rem; margin: 0;">Centro de Pesquisa Rodoviária</p>
    </div>
    """, unsafe_allow_html=True)

    renderizar_footer()
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
