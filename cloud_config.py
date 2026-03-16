r"""
=========================================================================
CLOUD CONFIG - Deteccao de Ambiente e Fallback Inteligente
=========================================================================
Modulo central que detecta se estamos rodando local (com Google Drive)
ou na nuvem (Streamlit Cloud), e fornece funcoes de fallback unificadas.

Local:  Acessa G:\ (Google Drive via Stream) -> atualiza caches
Cloud:  Carrega 100% dos dados de caches estaticos (parquet/json)
=========================================================================
"""

import os
import logging
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# =============================================================================
# DETECÇÃO DE AMBIENTE
# =============================================================================

# Referência: pasta do Google Drive mapeado via Stream
_GDRIVE_PROBE = r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk"

IS_CLOUD = not os.path.isdir(_GDRIVE_PROBE)

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(_PROJECT_ROOT, "cache_certificados")
IMAGENS_DIR = os.path.join(_PROJECT_ROOT, "Imagens")

# =============================================================================
# IMAGENS — Fallback inteligente (local Google Drive → Imagens/)
# =============================================================================

# Logo horizontal principal
LOGO_HORIZONTAL = os.path.join(IMAGENS_DIR, "AE - Logo Hor Principal_2.png")

# Selo (usa logo horizontal como fallback se selo não existir localmente)
_SELO_LOCAL = os.path.join(IMAGENS_DIR, "Selo_1.png")
LOGO_SELO = _SELO_LOCAL if os.path.exists(_SELO_LOCAL) else LOGO_HORIZONTAL

# Padronagem
LOGO_PADRONAGEM = os.path.join(IMAGENS_DIR, "Padronagem_2.png")


def get_logo_path(tipo: str = "horizontal") -> str | None:
    """
    Retorna o caminho da logo, tentando Google Drive primeiro (local)
    e caindo para Imagens/ no cloud.

    tipo: 'horizontal', 'selo', 'padronagem'
    """
    _GDRIVE_LOGOS = {
        "horizontal": (
            r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1"
            r"\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias"
            r"\Manual Completo\Identidade Visual\Logotipo e Variações\Logotipo\PNG"
            r"\AE - Logo Hor Principal_2.png"
        ),
        "selo": (
            r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1"
            r"\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias"
            r"\Manual Completo\Identidade Visual\Logotipo e Variações\Símbolo e Selos\PNG"
            r"\Selo\Selo_1.png"
        ),
        "selo_c_ass": (
            r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1"
            r"\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias"
            r"\Manual Completo\Identidade Visual\Logotipo e Variações\Símbolo e Selos\PNG"
            r"\Selo C Ass\Selo C Ass_4.png"
        ),
    }

    _LOCAL_FALLBACK = {
        "horizontal": LOGO_HORIZONTAL,
        "selo":       LOGO_SELO,
        "selo_c_ass": LOGO_SELO,
        "padronagem": LOGO_PADRONAGEM,
    }

    # Tenta Google Drive primeiro (só funciona local)
    gdrive = _GDRIVE_LOGOS.get(tipo)
    if gdrive and os.path.exists(gdrive):
        return gdrive

    # Fallback para imagem local
    local = _LOCAL_FALLBACK.get(tipo, LOGO_HORIZONTAL)
    if os.path.exists(local):
        return local

    return None


# =============================================================================
# CACHE DE DADOS — Carregamento de parquet estáticos
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def carregar_parquet_cache(nome: str) -> pd.DataFrame:
    """
    Carrega um arquivo parquet do cache estático.

    Nomes disponíveis:
        - 'db_novo_dashboard_067'   → FORM 067 (Dashboard Certificados)
        - 'db_epr_form022a'         → FORM 022A (EPR)
        - 'db_recebimentos'         → Recebimentos
        - 'db_certificados_067'     → Certificados 067
        - 'dados_certificados'      → Dados consolidados certificados
        - 'dados_processados'       → Dados processados
        - 'dados_recebimento'       → Dados recebimento
        - 'relatorios_tecnicos'     → Relatórios técnicos
        - 'cauq_projetos'           → Projetos CAUQ Marshall
    """
    path = os.path.join(CACHE_DIR, f"{nome}.parquet")
    if os.path.exists(path):
        df = pd.read_parquet(path)
        logger.info(f"[cloud_config] Loaded {nome}.parquet: {len(df)} rows")
        return df

    logger.warning(f"[cloud_config] Cache not found: {path}")
    return pd.DataFrame()


# =============================================================================
# CREDENCIAIS — st.secrets com fallback para dev local
# =============================================================================

def get_usuarios() -> dict:
    """
    Retorna o dicionário de usuários.
    Em produção (cloud): usa st.secrets
    Em dev (local): usa fallback hardcoded
    """
    try:
        # Tenta carregar de st.secrets (Streamlit Cloud)
        if hasattr(st, 'secrets') and 'usuarios' in st.secrets:
            return dict(st.secrets['usuarios'])
    except Exception:
        pass

    # Fallback para desenvolvimento local
    return {
        "Gestor": {
            "senha": "Afirmaevias",
            "paginas": ["Dashboard de Certificados", "Cronograma de Ensaios", "Mapeamento de Projetos CAUQ"]
        },
        "Geoloc": {
            "senha": "Afirmaevias",
            "paginas": ["Mapeamento de Projetos CAUQ"]
        },
        "EPR": {
            "senha": "Afirmaevias",
            "paginas": ["EPR Litoral Pioneiro"]
        },
        "Dev": {
            "senha": "Afirmaevias",
            "paginas": ["Dashboard de Certificados", "Cronograma de Ensaios", "EPR Litoral Pioneiro", "Mapeamento de Projetos CAUQ"]
        }
    }


# =============================================================================
# INFO DE AMBIENTE (para debug no sidebar)
# =============================================================================

def mostrar_info_ambiente():
    """Mostra um badge discreto no sidebar indicando o ambiente."""
    modo = "☁️ Cloud" if IS_CLOUD else "💻 Local"
    st.sidebar.caption(f"Ambiente: {modo}")
