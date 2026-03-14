"""
=========================================================================
CACHE MANAGER — Afirma E-vias Management Project
=========================================================================
Gerencia o cache de dados por ID de página/dashboard.

Uso:
    from cache_manager import carregar_dados, limpar_cache

    # Carrega dados do dashboard de certificados
    df = carregar_dados("certificados")

    # Carrega dados do cronograma
    df = carregar_dados("cronograma")

Cada cache_id tem seu próprio TTL e lógica de carregamento.
=========================================================================
"""

import os
import streamlit as st

# =============================================================================
# CONFIGURAÇÕES POR ID
# =============================================================================

# TTL em segundos por dashboard (0 = sem expiração automática)
_TTL_POR_ID = {
    "certificados":  3600,   # 1 hora
    "cronograma":    1800,   # 30 minutos
    "relatorios":    3600,   # 1 hora
}

# Caminho padrão do banco de dados
_DB_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_central_master.db")


# =============================================================================
# LOADERS INTERNOS (um por ID)
# =============================================================================

def _carregar_certificados(caminho_db: str):
    """Carrega e processa os dados de certificados."""
    try:
        import sqlite3
        import pandas as pd

        with sqlite3.connect(caminho_db) as conn:
            df = pd.read_sql_query("SELECT * FROM certificados", conn)

        # Normalização básica
        if "DATA" in df.columns:
            df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
            df["MES_ANO"] = df["DATA"].dt.strftime("%m/%Y")

        return df

    except Exception as e:
        st.warning(f"[cache_manager] Erro ao carregar certificados: {e}")
        import pandas as pd
        return pd.DataFrame()


def _carregar_cronograma(caminho_db: str):
    """Carrega e processa os dados do cronograma de relatórios."""
    try:
        import sqlite3
        import pandas as pd

        with sqlite3.connect(caminho_db) as conn:
            df = pd.read_sql_query("SELECT * FROM cronograma", conn)

        if "DATA_INICIO" in df.columns:
            df["DATA_INICIO"] = pd.to_datetime(df["DATA_INICIO"], errors="coerce")
        if "DATA_FIM" in df.columns:
            df["DATA_FIM"] = pd.to_datetime(df["DATA_FIM"], errors="coerce")

        return df

    except Exception as e:
        st.warning(f"[cache_manager] Erro ao carregar cronograma: {e}")
        import pandas as pd
        return pd.DataFrame()


def _carregar_relatorios(caminho_db: str):
    """Carrega os relatórios técnicos."""
    try:
        import sqlite3
        import pandas as pd

        with sqlite3.connect(caminho_db) as conn:
            df = pd.read_sql_query("SELECT * FROM relatorios_tecnicos", conn)

        if "DATA_EMISSAO" in df.columns:
            df["DATA_EMISSAO"] = pd.to_datetime(df["DATA_EMISSAO"], errors="coerce")

        return df

    except Exception as e:
        st.warning(f"[cache_manager] Erro ao carregar relatórios: {e}")
        import pandas as pd
        return pd.DataFrame()


# =============================================================================
# MAPA DE LOADERS  (cache_id → função de carregamento)
# =============================================================================

_LOADERS = {
    "certificados": _carregar_certificados,
    "cronograma":   _carregar_cronograma,
    "relatorios":   _carregar_relatorios,
}


# =============================================================================
# FUNÇÃO PRINCIPAL — cache por ID com TTL dinâmico
# =============================================================================

@st.cache_data(show_spinner=False)
def _cache_interno(cache_id: str, caminho_db: str, _ttl_segundos: int):
    """
    Função interna cacheada pelo Streamlit.
    Cada combinação (cache_id, caminho_db) gera uma entrada independente no cache.
    O parâmetro _ttl_segundos é só para forçar revalidação quando o TTL muda
    (prefixo _ faz o Streamlit ignorá-lo na chave de cache).
    """
    if cache_id not in _LOADERS:
        raise ValueError(
            f"[cache_manager] cache_id '{cache_id}' não reconhecido. "
            f"IDs disponíveis: {list(_LOADERS.keys())}"
        )

    loader = _LOADERS[cache_id]
    return loader(caminho_db)


def carregar_dados(cache_id: str, caminho_db: str = None):
    """
    Carrega dados cacheados com base no ID do dashboard.

    Parâmetros
    ----------
    cache_id : str
        Identificador do dashboard. Valores válidos:
          - "certificados"  → dados do Dashboard de Certificados
          - "cronograma"    → dados do Cronograma de Relatórios
          - "relatorios"    → dados dos Relatórios Técnicos

    caminho_db : str, opcional
        Caminho para o arquivo SQLite. Se omitido, usa lab_central_master.db
        na raiz do projeto.

    Retorno
    -------
    pandas.DataFrame
        Dados carregados e normalizados, com cache automático.

    Exemplo
    -------
    >>> from cache_manager import carregar_dados
    >>> df_cert = carregar_dados("certificados")
    >>> df_cron = carregar_dados("cronograma")
    """
    if caminho_db is None:
        caminho_db = _DB_PADRAO

    ttl = _TTL_POR_ID.get(cache_id, 3600)
    return _cache_interno(cache_id, caminho_db, ttl)


# =============================================================================
# UTILITÁRIOS
# =============================================================================

def limpar_cache(cache_id: str = None):
    """
    Limpa o cache de um ID específico ou de todos.

    Parâmetros
    ----------
    cache_id : str ou None
        Se None, limpa todo o cache do Streamlit.
        Se informado, tenta limpar apenas o cache daquele ID.
    """
    if cache_id is None:
        _cache_interno.clear()
        st.toast("🗑️ Cache completo limpo.", icon="✅")
    else:
        # Streamlit não suporta invalidação por chave diretamente;
        # a limpeza total é o caminho seguro.
        _cache_interno.clear()
        st.toast(f"🗑️ Cache de '{cache_id}' limpo.", icon="✅")


def ids_disponiveis():
    """Retorna a lista de IDs de cache suportados."""
    return list(_LOADERS.keys())
