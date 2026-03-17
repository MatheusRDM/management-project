"""
=========================================================================
EPR LITORAL PIONEIRO — FORM 022A
=========================================================================
Página dedicada ao acompanhamento de ensaios da EPR Litoral Pioneiro.
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
    page_title="EPR Litoral Pioneiro | Afirma E-vias",
    page_icon="Imagens/AE - Logo Hor Principal_2.png",
    layout="wide",
    initial_sidebar_state="auto"
)

# Aplicar estilos
aplicar_estilos()
proteger_pagina("EPR Litoral Pioneiro")

# ======================================================================================
# CARREGAR DASHBOARD EPR
# ======================================================================================
from EPR.epr_dashboard import main

main()
