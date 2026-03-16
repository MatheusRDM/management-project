"""
=========================================================================
ESTILOS GLOBAIS - AFIRMA E-VIAS
=========================================================================
Sistema de Design Padronizado baseado no Manual de Marca
Alto Contraste | Fontes Poppins/Exo | Paleta Corporativa
=========================================================================
"""

import streamlit as st
import os

# ======================================================================================
# PALETA DE CORES CORPORATIVA OFICIAL - AFIRMA E-VIAS
# ======================================================================================
CORES = {
    # Cores Primárias (Extraídas da Paleta Oficial)
    'primario': '#00233B',           # Azul Escuro (Principal)
    'secundario': '#566E3D',         # Verde Oliva (Ação/Status)
    'destaque': '#BFCF99',           # Verde Claro (Destaques/Bordas)
    
    # Tons Neutros e Fundo
    'fundo_claro': '#EFEBDC',        # Bege Claro
    'neutro': '#F2F1EF',             # Cinza Acetinado
    'branco': '#FFFFFF',             # Branco Puro
    
    # Mapeamento para Interface do Usuário (UI)
    'fundo_escuro': '#00233B',       # Fundo principal
    'fundo_card': '#0a3d5f',         # Azul variante para elevação de cards
    'fundo_hover': '#0d4a6f',        # Azul sutil para estados de hover
    
    # Cores de Texto (Garantindo Alto Contraste)
    'texto_primario': '#FFFFFF',     # Branco puro
    'texto_secundario': '#F2F1EF',   # Cinza acetinado para textos de apoio
    'texto_destaque': '#BFCF99',     # Verde claro para títulos e ênfase
    'texto_escuro': '#00233B',       # Azul escuro para leitura em fundos claros
    
    # Cores de Status (Alinhadas à Identidade Visual)
    'sucesso': '#566E3D',            # Verde Oliva (Padronizado)
    'finalizado': '#566E3D',         # Verde Oliva
    'alerta': '#f59e0b',             # Amarelo Corporativo
    'erro': '#dc2626',               # Vermelho Corporativo
    'info': '#3b82f6',               # Azul Informativo
    'em_andamento': '#3b82f6',       
    'aguardando': '#f59e0b',         
    'urgente': '#dc2626',            
    'vencido': '#7f1d1d',            
    
    # Bordas e Divisores
    'borda_primaria': '#566E3D',     # Verde Oliva
    'borda_destaque': '#BFCF99',     # Verde Claro
    'borda_sutil': '#566E3D',        # Azul Marinho Médio
}

# ======================================================================================
# CONFIGURAÇÕES DE FONTE
# ======================================================================================
FONTES = {
    'primaria': 'Poppins',
    'secundaria': 'Exo',
    'fallback': 'sans-serif',
}

# ======================================================================================
# CSS GLOBAL - ALTO CONTRASTE E DESIGN PROFISSIONAL
# ======================================================================================
def get_css_global():
    """Retorna o CSS global padronizado para todas as páginas"""
    return f"""
<style>
    /* ==================== IMPORTAÇÃO DE FONTES ==================== */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Exo:wght@300;400;500;600;700;800&display=swap');

    /* ==================== RESET E CONFIGURAÇÕES BASE ==================== */
    .stApp {{
        background: linear-gradient(180deg, {CORES['primario']} 0%, #001829 100%);
        font-family: '{FONTES['primaria']}', '{FONTES['secundaria']}', {FONTES['fallback']};
        color: {CORES['texto_primario']};
        font-size: 16px;
        line-height: 1.6;
    }}

    /* OCULTAR NOME DO ARQUIVO NA SIDEBAR (app, pages, etc) */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] {{
        display: none !important;
    }}
    
    /* Ocultar link de navegação do Streamlit */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {{
        display: none !important;
    }}
    
    /* Ocultar header da sidebar */
    section[data-testid="stSidebar"] header {{
        display: none !important;
    }}

    /* ==================== TIPOGRAFIA - ALTO CONTRASTE ==================== */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        font-family: '{FONTES['primaria']}', {FONTES['fallback']};
        color: {CORES['texto_primario']} !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    
    h1 {{
        font-size: 2.8rem !important;
        line-height: 1.2;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }}
    
    h2 {{
        font-size: 2rem !important;
        line-height: 1.3;
        color: {CORES['texto_destaque']} !important;
    }}
    
    h3 {{
        font-size: 1.5rem !important;
        line-height: 1.4;
    }}

    /* Textos gerais com alto contraste */
    p, div, span, label, li {{
        font-family: '{FONTES['primaria']}', {FONTES['fallback']};
        color: {CORES['texto_primario']};
        font-size: 15px;
        line-height: 1.6;
    }}

    /* ==================== SIDEBAR - DESIGN PROFISSIONAL ==================== */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {CORES['primario']} 0%, #001829 100%);
        border-right: 3px solid {CORES['secundario']};
    }}
    
    section[data-testid="stSidebar"] > div {{
        padding-top: 1rem;
    }}
    
    /* Logo na Sidebar */
    section[data-testid="stSidebar"] img {{
        max-width: 200px !important;
        margin: 0 auto 1.5rem auto;
        display: block;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
    }}
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {CORES['texto_destaque']} !important;
        font-size: 1.3rem !important;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {CORES['secundario']};
    }}
    
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p {{
        color: {CORES['texto_secundario']} !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }}

    /* ==================== CARDS DE MÉTRICAS/KPI - INTERATIVOS ==================== */
    div[data-testid="stMetric"] {{
        background: linear-gradient(135deg, {CORES['secundario']} 0%, #6a8a4a 100%);
        border: 2px solid {CORES['borda_destaque']};
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 20px rgba(86, 110, 61, 0.4);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
    }}
    
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 12px 40px rgba(86, 110, 61, 0.6);
        border-color: {CORES['texto_primario']};
        background: linear-gradient(135deg, #6a8a4a 0%, #7da058 100%);
    }}
    
    div[data-testid="stMetric"]:active {{
        transform: translateY(-2px) scale(1.01);
    }}
    
    /* Labels dos KPIs */
    div[data-testid="stMetric"] label {{
        font-size: 14px !important;
        font-weight: 600 !important;
        color: {CORES['texto_destaque']} !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    /* Valores dos KPIs - ALTO CONTRASTE */
    div[data-testid="stMetric"] > div > div > div:nth-child(2) {{
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: {CORES['texto_primario']} !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    
    /* Delta dos KPIs */
    div[data-testid="stMetric"] > div > div > div:nth-child(3) {{
        font-size: 13px !important;
        font-weight: 600 !important;
    }}
    
    /* Cores das bordas laterais por posição */
    div[data-testid="column"]:nth-of-type(1) div[data-testid="stMetric"] {{ 
        border-left: 5px solid {CORES['primario']};
    }}
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stMetric"] {{ 
        border-left: 5px solid {CORES['secundario']};
    }}
    div[data-testid="column"]:nth-of-type(3) div[data-testid="stMetric"] {{ 
        border-left: 5px solid {CORES['destaque']};
    }}
    div[data-testid="column"]:nth-of-type(4) div[data-testid="stMetric"] {{ 
        border-left: 5px solid {CORES['info']};
    }}
    div[data-testid="column"]:nth-of-type(5) div[data-testid="stMetric"] {{ 
        border-left: 5px solid {CORES['alerta']};
    }}
    div[data-testid="column"]:nth-of-type(6) div[data-testid="stMetric"] {{ 
        border-left: 5px solid {CORES['erro']};
    }}

    /* ==================== BOTÕES ==================== */
    div.stButton > button {{
        background: linear-gradient(135deg, {CORES['secundario']} 0%, #6a8a4a 100%);
        color: {CORES['texto_primario']};
        border: 2px solid {CORES['borda_destaque']};
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-family: '{FONTES['primaria']}', {FONTES['fallback']};
        font-weight: 600;
        font-size: 15px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(86, 110, 61, 0.4);
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    
    div.stButton > button:hover {{
        background: linear-gradient(135deg, #6a8a4a 0%, #7da058 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(86, 110, 61, 0.6);
        border-color: {CORES['texto_primario']};
    }}
    
    div.stButton > button:active {{
        transform: translateY(0);
    }}

    /* ==================== INPUTS E SELECTS ==================== */
    /* Selectbox na área principal */
    div[data-testid="stSelectbox"] > div > div {{
        background-color: {CORES['fundo_card']};
        border: 2px solid {CORES['borda_primaria']};
        border-radius: 8px;
        color: {CORES['texto_primario']};
        font-size: 14px;
    }}
    
    div[data-testid="stSelectbox"] > div > div:hover {{
        border-color: {CORES['borda_destaque']};
    }}
    
    /* Selectbox na Sidebar - FUNDO ESCURO COM FONTE CLARA */
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div > div {{
        background-color: {CORES['primario']} !important;
        border: 2px solid {CORES['borda_destaque']} !important;
        color: {CORES['texto_primario']} !important;
    }}
    
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div > div > div {{
        color: {CORES['texto_primario']} !important;
    }}
    
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] svg {{
        fill: {CORES['texto_primario']} !important;
    }}
    
    /* Label dos selectbox na sidebar */
    section[data-testid="stSidebar"] label {{
        color: {CORES['texto_primario']} !important;
    }}

    /* Multiselect */
    div[data-testid="stMultiSelect"] > div > div {{
        background-color: {CORES['fundo_card']};
        border: 2px solid {CORES['borda_primaria']};
        border-radius: 8px;
        color: {CORES['texto_primario']};
    }}
    
    div[data-testid="stMultiSelect"] > div > div:hover {{
        border-color: {CORES['borda_destaque']};
    }}
    
    /* Tags do Multiselect */
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
        background-color: {CORES['secundario']} !important;
        color: {CORES['texto_primario']} !important;
        border-radius: 4px;
        font-weight: 500;
    }}
    
    /* Dropdown menu - POPUP DOS FILTROS */
    div[data-baseweb="popover"] {{
        background-color: {CORES['primario']} !important;
    }}
    
    div[data-baseweb="popover"] div[data-baseweb="menu"] {{
        background-color: {CORES['primario']} !important;
        border: 2px solid {CORES['borda_destaque']} !important;
        border-radius: 8px !important;
    }}
    
    /* Itens do dropdown */
    ul[data-baseweb="menu"] {{
        background-color: {CORES['primario']} !important;
    }}
    
    li[data-baseweb="menu-item"] {{
        background-color: {CORES['primario']} !important;
    }}
    
    li[data-baseweb="menu-item"] > div {{
        background-color: transparent !important;
        color: {CORES['texto_primario']} !important;
        padding: 10px 15px !important;
    }}
    
    li[data-baseweb="menu-item"]:hover {{
        background-color: {CORES['secundario']} !important;
    }}
    
    li[data-baseweb="menu-item"]:hover > div {{
        background-color: {CORES['secundario']} !important;
        color: {CORES['texto_primario']} !important;
    }}
    
    /* Highlight do item selecionado */
    li[data-baseweb="menu-item"][aria-selected="true"] {{
        background-color: {CORES['secundario']} !important;
    }}
    
    li[data-baseweb="menu-item"][aria-selected="true"] > div {{
        background-color: {CORES['secundario']} !important;
        color: {CORES['texto_primario']} !important;
    }}

    /* ==================== TABELAS E DATAFRAMES ==================== */
    [data-testid="stDataFrame"] {{
        background: linear-gradient(135deg, {CORES['primario']} 0%, {CORES['fundo_card']} 100%);
        border-radius: 12px;
        padding: 1rem;
        border: 2px solid {CORES['borda_primaria']};
        box-shadow: 0 4px 20px rgba(0, 35, 59, 0.4);
    }}
    
    .dataframe {{
        background-color: transparent;
        color: {CORES['texto_primario']};
    }}
    
    .dataframe th {{
        background-color: {CORES['secundario']} !important;
        color: {CORES['texto_primario']} !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 12px !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    
    .dataframe td {{
        background-color: rgba(0, 35, 59, 0.6) !important;
        color: {CORES['texto_secundario']} !important;
        font-size: 13px !important;
        padding: 10px !important;
        border-bottom: 1px solid {CORES['borda_sutil']} !important;
    }}
    
    .dataframe tr:hover td {{
        background-color: rgba(86, 110, 61, 0.3) !important;
    }}

    /* ==================== GRÁFICOS PLOTLY ==================== */
    .stPlotlyChart {{
        background: linear-gradient(135deg, {CORES['primario']} 0%, {CORES['fundo_card']} 100%);
        border-radius: 12px;
        padding: 1rem;
        border: 2px solid {CORES['borda_primaria']};
        box-shadow: 0 4px 20px rgba(0, 35, 59, 0.4);
    }}

    /* ==================== EXPANDERS ==================== */
    .streamlit-expanderHeader {{
        background: linear-gradient(135deg, {CORES['secundario']} 0%, #6a8a4a 100%);
        color: {CORES['texto_primario']} !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        padding: 1rem !important;
        border-radius: 8px;
        border: 2px solid {CORES['borda_destaque']};
    }}
    
    .streamlit-expanderContent {{
        background-color: rgba(0, 35, 59, 0.9);
        border: 2px solid {CORES['borda_primaria']};
        border-top: none;
        border-radius: 0 0 8px 8px;
        padding: 1rem;
    }}

    /* ==================== TABS ==================== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: {CORES['fundo_card']};
        color: {CORES['texto_primario']};
        border-radius: 8px 8px 0 0;
        border: 2px solid {CORES['borda_primaria']};
        border-bottom: none;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {CORES['secundario']} !important;
        border-color: {CORES['borda_destaque']} !important;
    }}

    /* ==================== ALERTAS ==================== */
    .stAlert {{
        background: linear-gradient(135deg, {CORES['primario']} 0%, {CORES['fundo_card']} 100%);
        color: {CORES['texto_primario']};
        border: 2px solid {CORES['borda_destaque']};
        border-radius: 8px;
    }}

    /* ==================== SEPARADORES ==================== */
    hr {{
        border-color: {CORES['borda_primaria']};
        margin: 2rem 0 !important;
        opacity: 0.6;
    }}

    /* ==================== SCROLLBAR PERSONALIZADA ==================== */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {CORES['primario']};
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {CORES['secundario']};
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {CORES['destaque']};
    }}

    /* ==================== CARDS DE NAVEGAÇÃO ==================== */
    .nav-card {{
        background: linear-gradient(135deg, {CORES['primario']} 0%, {CORES['fundo_card']} 100%);
        border: 3px solid {CORES['borda_primaria']};
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 35, 59, 0.5);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer;
        text-align: center;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }}
    
    .nav-card:hover {{
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 60px rgba(86, 110, 61, 0.4);
        border-color: {CORES['borda_destaque']};
        background: linear-gradient(135deg, {CORES['secundario']} 0%, #6a8a4a 100%);
    }}
    
    .nav-card h3 {{
        font-size: 1.6rem !important;
        margin-bottom: 1rem;
        color: {CORES['texto_primario']};
    }}
    
    .nav-card p {{
        font-size: 1rem;
        color: {CORES['texto_secundario']};
        margin-bottom: 1.5rem;
        line-height: 1.6;
    }}
    
    .nav-card .icon {{
        font-size: 3.5rem;
        margin-bottom: 1rem;
    }}

    /* ==================== HEADER COM LOGO ==================== */
    .header-container {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 2rem;
        background: linear-gradient(135deg, {CORES['primario']} 0%, {CORES['fundo_card']} 100%);
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 2px solid {CORES['borda_primaria']};
    }}
    
    .header-logo {{
        max-width: 180px;
        height: auto;
    }}
    
    .header-title {{
        color: {CORES['texto_primario']};
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
    }}

    /* ==================== FOOTER ==================== */
    .footer {{
        text-align: center;
        margin-top: 3rem;
        padding: 1.5rem;
        border-top: 2px solid {CORES['borda_primaria']};
        color: {CORES['texto_destaque']};
        font-size: 0.85rem;
    }}
    
    .footer a {{
        color: {CORES['destaque']};
        text-decoration: none;
    }}

    /* ==================== ANIMAÇÕES ==================== */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .fade-in {{
        animation: fadeIn 0.5s ease-out forwards;
    }}

    /* ==================== SLIDER ==================== */
    .stSlider > div > div > div {{
        background-color: {CORES['secundario']} !important;
    }}
    
    .stSlider > div > div > div > div {{
        background-color: {CORES['destaque']} !important;
    }}
    
    /* Slider thumb (bolinha) */
    .stSlider [role="slider"] {{
        background-color: {CORES['destaque']} !important;
        border-color: {CORES['secundario']} !important;
    }}
    
    /* Slider value text */
    .stSlider > div > div > div > div > div {{
        color: {CORES['destaque']} !important;
    }}
    
    /* Sidebar slider overrides */
    section[data-testid="stSidebar"] .stSlider > div > div > div {{
        background-color: {CORES['secundario']} !important;
    }}
    
    section[data-testid="stSidebar"] .stSlider > div > div > div > div {{
        background-color: {CORES['destaque']} !important;
    }}
    
    section[data-testid="stSidebar"] .stSlider [role="slider"] {{
        background-color: {CORES['destaque']} !important;
    }}

    /* ==================== CHECKBOX ==================== */
    .stCheckbox > label > div[data-testid="stCheckbox"] > div {{
        background-color: {CORES['fundo_card']};
        border-color: {CORES['borda_primaria']};
    }}
    
    .stCheckbox > label > div[data-testid="stCheckbox"] > div[aria-checked="true"] {{
        background-color: {CORES['secundario']} !important;
        border-color: {CORES['destaque']} !important;
    }}
    
    /* Sidebar checkbox overrides */
    section[data-testid="stSidebar"] .stCheckbox > label > div[data-testid="stCheckbox"] > div[aria-checked="true"] {{
        background-color: {CORES['secundario']} !important;
        border-color: {CORES['destaque']} !important;
    }}
    
    /* Checkbox SVG check mark */
    .stCheckbox svg {{
        fill: {CORES['texto_primario']} !important;
        stroke: {CORES['texto_primario']} !important;
    }}

    /* ==================== RADIO BUTTONS ==================== */
    /* Override radio button accent color */
    section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {{
        color: {CORES['secundario']} !important;
    }}
    
    .stRadio [role="radiogroup"] label div[data-testid="stMarkdownContainer"] {{
        color: {CORES['texto_primario']} !important;
    }}

    /* ==================== STREAMLIT ACCENT OVERRIDE ==================== */
    /* Force Streamlit primary accent color to palette */
    :root {{
        --primary-color: {CORES['secundario']} !important;
    }}
    
    /* Override any remaining red accent colors */
    .st-emotion-cache-1inwz65 {{
        fill: {CORES['secundario']} !important;
    }}
    
    /* Generic accent override for checked states */
    [data-baseweb="checkbox"] [data-testid="stCheckbox"] {{
        --primaryColor: {CORES['secundario']} !important;
    }}

    /* ==================== DATE INPUT ==================== */
    .stDateInput > div > div {{
        background-color: {CORES['fundo_card']};
        border: 2px solid {CORES['borda_primaria']};
        color: {CORES['texto_primario']};
    }}

    /* ==================== TEXT INPUT ==================== */
    .stTextInput > div > div {{
        background-color: {CORES['fundo_card']};
        border: 2px solid {CORES['borda_primaria']};
        color: {CORES['texto_primario']};
        border-radius: 8px;
    }}
    
    .stTextInput > div > div:focus-within {{
        border-color: {CORES['destaque']};
    }}
    
    .stTextInput input {{
        color: {CORES['texto_primario']} !important;
    }}

    /* ==================== NUMBER INPUT ==================== */
    .stNumberInput > div > div {{
        background-color: {CORES['fundo_card']};
        border: 2px solid {CORES['borda_primaria']};
    }}
    
    .stNumberInput input {{
        color: {CORES['texto_primario']} !important;
    }}

    /* ==================== RADIO BUTTONS ==================== */
    .stRadio > div {{
        background-color: transparent;
    }}
    
    .stRadio label {{
        color: {CORES['texto_primario']} !important;
    }}

    /* ==================== PROGRESS BAR ==================== */
    .stProgress > div > div > div {{
        background-color: {CORES['secundario']};
    }}

    /* ==================== TOAST ==================== */
    .stToast {{
        background-color: {CORES['secundario']} !important;
        color: {CORES['texto_primario']} !important;
    }}

    /* ==================== FILE UPLOADER ==================== */
    .stFileUploader > div {{
        background-color: {CORES['fundo_card']};
        border: 2px dashed {CORES['borda_primaria']};
        border-radius: 12px;
    }}
    
    .stFileUploader > div:hover {{
        border-color: {CORES['destaque']};
    }}

    /* ==================== FILTROS INTERATIVOS - DESIGN REFINADO ==================== */
    /* Selectbox em expanders - fundo escuro, fonte clara */
    .streamlit-expanderContent div[data-testid="stSelectbox"] > div > div {{
        background-color: {CORES['fundo_card']} !important;
        border: 2px solid {CORES['borda_primaria']} !important;
        border-radius: 8px !important;
        color: {CORES['texto_primario']} !important;
        transition: all 0.3s ease !important;
    }}
    
    .streamlit-expanderContent div[data-testid="stSelectbox"] > div > div:hover {{
        border-color: {CORES['destaque']} !important;
        box-shadow: 0 4px 15px rgba(86, 110, 61, 0.3) !important;
    }}
    
    /* Multiselect em expanders */
    .streamlit-expanderContent div[data-testid="stMultiSelect"] > div > div {{
        background-color: {CORES['fundo_card']} !important;
        border: 2px solid {CORES['borda_primaria']} !important;
        border-radius: 8px !important;
        color: {CORES['texto_primario']} !important;
        transition: all 0.3s ease !important;
    }}
    
    .streamlit-expanderContent div[data-testid="stMultiSelect"] > div > div:hover {{
        border-color: {CORES['destaque']} !important;
        box-shadow: 0 4px 15px rgba(86, 110, 61, 0.3) !important;
    }}

    /* Expander com design clean */
    details[data-testid="stExpander"] {{
        border: 2px solid {CORES['borda_primaria']} !important;
        border-radius: 12px !important;
        background: linear-gradient(135deg, {CORES['primario']} 0%, {CORES['fundo_card']} 100%) !important;
        transition: all 0.3s ease !important;
    }}
    
    details[data-testid="stExpander"]:hover {{
        border-color: {CORES['destaque']} !important;
        box-shadow: 0 6px 20px rgba(86, 110, 61, 0.3) !important;
    }}
    
    details[data-testid="stExpander"] summary {{
        background: linear-gradient(135deg, {CORES['secundario']} 0%, #6a8a4a 100%) !important;
        color: {CORES['texto_primario']} !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 1rem !important;
        font-weight: 600 !important;
    }}
    
    details[data-testid="stExpander"][open] summary {{
        border-radius: 10px 10px 0 0 !important;
    }}

    /* Container com scroll para expanders de dados */
    .scrollable-container {{
        max-height: 300px;
        overflow-y: auto;
        padding: 1rem;
        background: rgba(0, 35, 59, 0.5);
        border-radius: 8px;
    }}
    
    /* Scrollbar estilizada */
    .scrollable-container::-webkit-scrollbar {{
        width: 8px;
    }}
    
    .scrollable-container::-webkit-scrollbar-track {{
        background: {CORES['primario']};
        border-radius: 4px;
    }}
    
    .scrollable-container::-webkit-scrollbar-thumb {{
        background: {CORES['secundario']};
        border-radius: 4px;
    }}
    
    .scrollable-container::-webkit-scrollbar-thumb:hover {{
        background: {CORES['destaque']};
    }}
    
    /* Popup modal com scroll */
    .popup-content {{
        max-height: 400px;
        overflow-y: auto;
        padding: 1.5rem;
        background: linear-gradient(135deg, {CORES['primario']} 0%, {CORES['fundo_card']} 100%);
        border-radius: 12px;
        border: 2px solid {CORES['borda_destaque']};
    }}
    
    .popup-content::-webkit-scrollbar {{
        width: 8px;
    }}
    
    .popup-content::-webkit-scrollbar-track {{
        background: {CORES['primario']};
        border-radius: 4px;
    }}
    
    .popup-content::-webkit-scrollbar-thumb {{
        background: {CORES['secundario']};
        border-radius: 4px;
    }}

    /* Sidebar logo maior */
    section[data-testid="stSidebar"] img {{
        max-width: 100% !important;
        margin: 0 auto 1rem auto;
        display: block;
        filter: drop-shadow(0 4px 12px rgba(0,0,0,0.4));
    }}
    
    /* KPI Labels brancos */
    div[data-testid="stMetric"] label {{
        color: {CORES['texto_primario']} !important;
    }}
</style>
"""

# ======================================================================================
# FUNÇÃO PARA APLICAR ESTILOS GLOBAIS
# ======================================================================================
def aplicar_estilos():
    """Aplica os estilos CSS globais na página"""
    st.markdown(get_css_global(), unsafe_allow_html=True)

# ======================================================================================
# FUNÇÃO PARA RENDERIZAR SIDEBAR PADRÃO
# ======================================================================================
def renderizar_sidebar(pagina_atual="Dashboard"):
    """
    Renderiza a sidebar padrão com logo e navegação
    
    Args:
        pagina_atual: Nome da página atual para destacar na navegação
    """
    with st.sidebar:
        # Logo grande no topo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "Imagens", "AE - Logo Hor Principal_2.png")
            if os.path.exists(logo_path):
                st.image(logo_path, use_container_width=True)
            else:
                st.image("Imagens/AE - Logo Hor Principal_2.png", use_container_width=True)
        except Exception:
            st.markdown(f"""
            <div style="text-align: center; padding: 1.5rem; background: {CORES['secundario']}; border-radius: 12px; margin-bottom: 1rem;">
                <h2 style="color: {CORES['texto_primario']}; margin: 0;">AFIRMA E-VIAS</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Título da sidebar
        st.markdown(f"""
        <h3 style="color: {CORES['texto_destaque']}; text-align: center; margin-bottom: 1rem;">AE - Dashboard's</h3>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.caption(f"© 2026 Afirma E-vias")

# ======================================================================================
# FUNÇÃO PARA RENDERIZAR HEADER COM LOGO
# ======================================================================================
def renderizar_header(titulo, subtitulo=""):
    """
    Renderiza o header padrão com logo e título
    
    Args:
        titulo: Título principal da página
        subtitulo: Subtítulo opcional
    """
    col1, col2 = st.columns([1, 4])
    
    with col1:
        try:
            # Selo para o header principal
            logo_path = r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias\Manual Completo\Identidade Visual\Logotipo e Variações\Símbolo e Selos\PNG\Selo\Selo_1.png"
            st.image(logo_path, width=240)
        except Exception:
            pass
    
    with col2:
        st.markdown(f"""
        <div style="padding-left: 1rem;">
            <h1 style="margin: 0; color: {CORES['texto_primario']};">{titulo}</h1>
            {"<p style='color: " + CORES['texto_destaque'] + "; font-size: 1.1rem; margin-top: 0.5rem;'>" + subtitulo + "</p>" if subtitulo else ""}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

# ======================================================================================
# FUNÇÃO PARA RENDERIZAR FOOTER
# ======================================================================================
def renderizar_footer():
    """Renderiza o footer padrão e o rótulo fixo no rodapé"""
    # Footer padrão
    st.markdown(f"""
    <div class="footer">
        <p>© 2026 Afirma E-vias | Laboratório Central | Sistema de Gestão de Ensaios</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Rótulo já injetado globalmente via aplicar_estilos() — sem duplicar aqui

# ======================================================================================
# CONFIGURAÇÃO DE GRÁFICOS PLOTLY - ALTO CONTRASTE
# ======================================================================================
PLOTLY_LAYOUT = {
    'font': {
        'family': 'Poppins, sans-serif',
        'color': '#FFFFFF',
        'size': 14
    },
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'plot_bgcolor': 'rgba(0,0,0,0)',
    
    # CONFIGURAÇÕES GLOBAIS DE INTERATIVIDADE
    'dragmode': False,  # Desabilita arrastar/zoom
    'hovermode': 'closest',  # Tooltip segue o cursor
    'hoverlabel': {
        'bgcolor': '#00233B',
        'bordercolor': '#BFCF99',
        'font': {
            'family': 'Poppins, sans-serif',
            'size': 14,
            'color': '#FFFFFF'
        }
    },
    
    'title': {
        'font': {
            'family': 'Poppins, sans-serif',
            'size': 20,
            'color': CORES['texto_primario']
        },
        'x': 0.5,
        'xanchor': 'center'
    },
    'legend': {
        'bgcolor': 'rgba(0, 35, 59, 0.8)',
        'bordercolor': CORES['borda_primaria'],
        'font': {'color': CORES['texto_primario'], 'size': 12}
    },
    'xaxis': {
        'gridcolor': 'rgba(255,255,255,0.1)',
        'tickcolor': '#BFCF99',
        'tickfont': {'color': '#FFFFFF', 'size': 12},
        'title_font': {'color': '#BFCF99', 'size': 14},
        'fixedrange': True
    },
    'yaxis': {
        'gridcolor': 'rgba(255,255,255,0.1)',
        'tickcolor': '#BFCF99',
        'tickfont': {'color': '#FFFFFF', 'size': 12},
        'title_font': {'color': '#BFCF99', 'size': 14},
        'fixedrange': True
    }
}

# Configuração padrão para st.plotly_chart - USE EM TODOS OS GRÁFICOS
PLOTLY_CONFIG = {
    'displayModeBar': False,
    'scrollZoom': False,
    'doubleClick': False,
    'displaylogo': False,
    'staticPlot': False
}

# Cores para gráficos - paleta corporativa vibrante
CORES_GRAFICOS = [
    '#566E3D',  # Verde Oliva (Principal)
    '#BFCF99',  # Verde Claro
    '#00233B',  # Azul Escuro
    '#EFEBDC',  # Bege Claro
    '#F2F1EF',  # Cinza Acetinado
    '#6a8a4a',  # Verde Médio
    '#7da058',  # Verde Claro 2
    '#0a3d5f',  # Azul Médio
]

# Escala de cores para heatmaps e gradientes
ESCALA_CORES = [
    [0, CORES['destaque']],
    [0.5, CORES['secundario']],
    [1, CORES['primario']]
]
