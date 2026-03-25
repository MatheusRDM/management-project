"""
=============================================================================
ECO RODOVIAS — entry point (slim)
=============================================================================
BR-050 (Eco Minas Goiás) + BR-365 (Eco Cerrado)
Checklist APP + Ensaios AEVIAS + Rastreamento Logos
=============================================================================
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from styles import aplicar_estilos
from page_auth import proteger_pagina

# =============================================================================
st.set_page_config(
    page_title="Eco Rodovias | Afirma E-vias",
    page_icon="Imagens/logo_icon.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)
aplicar_estilos()
proteger_pagina("Eco Rodovias")
# =============================================================================

# ── CSS (cal-table styles + component styles needed at runtime) ───────────────
st.markdown("""
<style>
/* Esconder navegacao automatica lateral do Streamlit */
[data-testid="stSidebarNav"],[data-testid="stSidebarNavItems"],[data-testid="collapsedControl"]{display:none!important}

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

/* ═══════════════════════════════════════════════════════════
   MOBILE-FIRST RESPONSIVE OVERRIDES
   Forçar st.columns a empilhar em telas < 768px
   ═══════════════════════════════════════════════════════════ */

/* ── Streamlit columns → stack vertical no mobile ────────── */
@media (max-width: 768px) {
    /* Força colunas do Streamlit a empilharem */
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 4px !important;
    }
    [data-testid="stHorizontalBlock"] > div {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 0 !important;
    }
    /* Container principal: remove padding lateral */
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 1rem !important;
    }
    /* Sidebar expandida no mobile */
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 280px !important;
        min-width: 280px !important;
        overflow: visible !important;
    }
    /* Sidebar colapsada: ocultar no mobile */
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
        overflow: hidden !important;
    }
    /* Tabs: fonte menor, scroll horizontal */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        flex-wrap: nowrap !important;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.72rem !important;
        padding: 8px 10px !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
    }
    /* Header: ajuste de texto */
    .eco-header h1 { font-size: 1.1rem !important; }
    .eco-header p  { font-size: 0.70rem !important; }
    .eco-header { padding: 10px 0 6px 0 !important; margin-bottom: 12px !important; }
    /* KPI cards: compactos no mobile */
    .eco-kpi {
        padding: 10px 8px !important;
        border-radius: 8px !important;
    }
    .eco-kpi .val { font-size: 1.4rem !important; }
    .eco-kpi .lbl { font-size: 0.62rem !important; }
    /* Calendar table: touch scroll + nomes menores */
    .cal-wrap { -webkit-overflow-scrolling: touch; }
    .cal-table { font-size: 0.60rem !important; min-width: 700px !important; }
    .cal-table th { font-size: 0.55rem !important; padding: 4px 2px !important; }
    .cal-table td { padding: 4px 2px !important; }
    .cal-table td.colab { min-width: 100px !important; max-width: 130px !important; font-size: 0.62rem !important; }
    .cal-table td.funcao { min-width: 70px !important; max-width: 100px !important; font-size: 0.55rem !important; }
    /* Legenda: wrap */
    .legend-item { font-size: 0.65rem !important; margin-right: 8px !important; }
    /* Plotly: garante full width */
    .js-plotly-plot, .plotly { width: 100% !important; }
    /* Streamlit dataframe: scroll horizontal */
    [data-testid="stDataFrame"] { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
    /* Selectbox / inputs: altura mínima touch-friendly */
    .stSelectbox > div > div,
    .stDateInput > div > div,
    .stMultiSelect > div > div {
        min-height: 42px !important;
    }
    /* Buttons: maiores no mobile */
    .stButton > button {
        min-height: 44px !important;
        font-size: 0.82rem !important;
    }
    /* Folium map: full width */
    iframe[title*="streamlit_folium"] {
        width: 100% !important;
        height: 400px !important;
    }
    /* Flex stat cards dos módulos (min-width inline) */
    div[style*="display:flex"][style*="gap"] > div[style*="min-width"] {
        min-width: 0 !important;
        flex: 1 1 calc(50% - 4px) !important;
    }
}

/* ── Tablet (768–960px): 2 colunas max ──────────────────── */
@media (min-width: 769px) and (max-width: 960px) {
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 6px !important;
    }
    [data-testid="stHorizontalBlock"] > div {
        min-width: calc(50% - 6px) !important;
        flex: 1 1 calc(50% - 6px) !important;
    }
    .eco-header h1 { font-size: 1.3rem !important; }
    .eco-kpi .val { font-size: 1.6rem !important; }
}

/* ═══════════════════════════════════════════════════════════
   ESTILOS BASE (desktop-first original, agora com overrides acima)
   ═══════════════════════════════════════════════════════════ */

.eco-header {
    padding: 18px 0 8px 0;
    border-bottom: 2px solid rgba(86,110,61,0.4);
    margin-bottom: 24px;
}
.eco-header h1 {
    font-family: 'Poppins', sans-serif;
    font-size: 1.55rem;
    font-weight: 700;
    color: #BFCF99;
    margin: 0;
}
.eco-header p {
    font-family: 'Poppins', sans-serif;
    font-size: 0.82rem;
    color: #8FA882;
    margin: 4px 0 0 0;
}
.eco-kpi {
    background: rgba(26,31,46,0.85);
    border: 1px solid rgba(86,110,61,0.35);
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
    margin-bottom: 10px;
}
.eco-kpi .val {
    font-family: 'Poppins', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}
.eco-kpi .lbl {
    font-family: 'Poppins', sans-serif;
    font-size: 0.72rem;
    color: #8FA882;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.cal-wrap { overflow-x: auto; width: 100%; -webkit-overflow-scrolling: touch; }
.cal-table {
    border-collapse: collapse;
    font-family: 'Poppins', sans-serif;
    font-size: 0.68rem;
    width: 100%;
    min-width: 900px;
}
.cal-table th {
    background: rgba(86,110,61,0.25);
    color: #BFCF99;
    padding: 5px 3px;
    text-align: center;
    font-weight: 600;
    border: 1px solid rgba(86,110,61,0.2);
    white-space: nowrap;
    font-size: 0.62rem;
}
.cal-table td {
    padding: 5px 4px;
    border: 1px solid rgba(255,255,255,0.05);
    text-align: center;
    white-space: nowrap;
}
.cal-table td.colab {
    text-align: left;
    font-weight: 500;
    color: #E8EFD8;
    padding-left: 8px;
    min-width: 160px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cal-table td.funcao {
    text-align: left;
    color: #8FA882;
    font-size: 0.60rem;
    min-width: 120px;
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.status-ok    { background: rgba(60,180,75,0.25);  color: #3cb44b; font-weight:600; border-radius:3px; }
.status-cobrar{ background: rgba(230,25,75,0.25);  color: #ff5577; font-weight:600; border-radius:3px; }
.status-ne    { background: rgba(58,74,94,0.4);    color: #7a90a8; }
.status-elab  { background: rgba(67,99,216,0.25);  color: #6ec6ff; font-weight:600; border-radius:3px; }
.status-vazio { background: transparent; color: #3a4a5e; }
.legend-item { display:inline-flex; align-items:center; gap:6px; margin-right:14px; font-size:0.75rem; font-family:'Poppins',sans-serif; color:#E8EFD8; }
.legend-dot { width:12px; height:12px; border-radius:3px; display:inline-block; }
</style>
""", unsafe_allow_html=True)

# ── Module imports (after sys.path is set) ────────────────────────────────────
from _eco_shared import _IS_CLOUD
from _eco_checklist import _aba_checklist
from _eco_ensaios import _aba_ensaios
from _eco_rastreamento import _aba_rastreamento
from _eco_resumo import _aba_resumo
from _eco_diario import _aba_diario


# =============================================================================
# SIDEBAR
# =============================================================================

def _sidebar():
    with st.sidebar:
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] { background: #0D1B2A !important; }
        .eco-sidebar-title {
            font-family:'Poppins',sans-serif; font-size:0.78rem;
            color:#8FA882; text-transform:uppercase; letter-spacing:.06em;
            margin: 8px 0 4px 0;
        }
        div[data-testid="stButton"] button {
            background: rgba(86,110,61,0.15) !important;
            border: 1px solid rgba(86,110,61,0.4) !important;
            color: #BFCF99 !important;
            font-family:'Poppins',sans-serif !important;
            font-size:0.78rem !important;
            padding:0.2rem 0.6rem !important;
            border-radius:6px !important;
            margin-bottom:0.5rem !important;
        }
        </style>""", unsafe_allow_html=True)

        if st.button("< Menu Principal", key="back_menu_eco"):
            st.switch_page("app.py")

        try:
            st.image("Imagens/AE - Logo Hor Principal_2.png", use_container_width=True)
        except Exception:
            st.markdown('<h3 style="color:white;text-align:center">AFIRMA E-VIAS</h3>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="eco-sidebar-title">Contrato</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-family:'Poppins',sans-serif; font-size:0.80rem; color:#E8EFD8; line-height:1.6">
            <b style="color:#BFCF99">ECO RODOVIAS 6771</b><br>
            ️ BR-050 — Eco Minas Goiás<br>
            ️ BR-365 — Eco Cerrado<br>
            <span style="color:#8FA882; font-size:0.72rem">Supervisão de Obras</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="eco-sidebar-title">Acesso ao Servidor</div>', unsafe_allow_html=True)
        if _IS_CLOUD:
            st.warning(" Modo Cloud — dados do cache", icon=None)
        else:
            st.success(" Servidor Y: conectado", icon=None)


# =============================================================================
# MAIN
# =============================================================================

def main():
    _sidebar()

    st.markdown("""
    <div class="eco-header">
        <h1>️ Eco Rodovias — Contrato 6771</h1>
        <p>BR-050 (Eco Minas Goiás) · BR-365 (Eco Cerrado) · Supervisão de Obras AFIRMA E-VIAS</p>
    </div>""", unsafe_allow_html=True)

    tab_resumo, tab_checklist, tab_diario, tab_ensaios, tab_rastr = st.tabs([
        "Resumo",
        "Checklist",
        "Diario de Obra",
        "Ensaios",
        "Rastreamento",
    ])

    with tab_resumo:
        _aba_resumo()

    with tab_checklist:
        _aba_checklist()

    with tab_diario:
        _aba_diario()

    with tab_ensaios:
        _aba_ensaios()

    with tab_rastr:
        _aba_rastreamento()


if __name__ == "__main__" or True:
    main()
