"""
=========================================================================
DASHBOARD DE CERTIFICADOS - FORM 067
=========================================================================
Dashboard baseado na estrutura do FORM 067
=========================================================================
"""

import streamlit as st
import sys
import os

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar estilos globais padronizados
from styles import aplicar_estilos
from page_auth import proteger_pagina

# ======================================================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================================================
st.set_page_config(
    page_title="Certificados | Afirma E-vias",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="auto"
)

# Aplicar estilos
aplicar_estilos()
proteger_pagina("Dashboard de Certificados")

# ======================================================================================
# CARREGAR DASHBOARD FORM 067
# ======================================================================================
from Mov_cert.novo_dashboard import main

main()
