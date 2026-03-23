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
    initial_sidebar_state="expanded"
)
aplicar_estilos()
proteger_pagina("Eco Rodovias")
# =============================================================================

# ── CSS (cal-table styles + component styles needed at runtime) ───────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

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
.cal-wrap { overflow-x: auto; width: 100%; }
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
from _eco_despacho import render_aba_despacho


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
            🛣️ BR-050 — Eco Minas Goiás<br>
            🛣️ BR-365 — Eco Cerrado<br>
            <span style="color:#8FA882; font-size:0.72rem">Supervisão de Obras</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="eco-sidebar-title">Acesso ao Servidor</div>', unsafe_allow_html=True)
        if _IS_CLOUD:
            st.warning("🌐 Modo Cloud — dados do cache", icon=None)
        else:
            st.success("✅ Servidor Y: conectado", icon=None)


# =============================================================================
# MAIN
# =============================================================================

def main():
    _sidebar()

    st.markdown("""
    <div class="eco-header">
        <h1>🛣️ Eco Rodovias — Contrato 6771</h1>
        <p>BR-050 (Eco Minas Goiás) · BR-365 (Eco Cerrado) · Supervisão de Obras AFIRMA E-VIAS</p>
    </div>""", unsafe_allow_html=True)

    tab_checklist, tab_ensaios, tab_rastr, tab_despacho = st.tabs([
        "📋 Checklist APP",
        "🔬 Ensaios AEVIAS",
        "🛰️ Rastreamento",
        "🚌 Despacho",
    ])

    with tab_checklist:
        _aba_checklist()

    with tab_ensaios:
        _aba_ensaios()

    with tab_rastr:
        _aba_rastreamento()

    with tab_despacho:
        render_aba_despacho()


if __name__ == "__main__" or True:
    main()
