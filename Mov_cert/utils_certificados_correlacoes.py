"""
=========================================================================
UTILITÁRIOS CERTIFICADOS - VERSÃO COM CORRELAÇÕES E SQLITE ROBUSTO
=========================================================================
Mantém as correlações corretas do Excel mas usa o sistema SQLite robusto
=========================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import logging

# Importar sistema robusto SQLite
from utils_certificados import (
    carregar_dados_combinados,
    get_opcoes_filtro,
    get_unique_values_safe,
    get_estatisticas_dashboard,
    exportar_dados_csv,
    formatar_numero,
    formatar_data,
    formatar_protocolo
)

# Re-exportar para uso no dashboard
__all__ = [
    'carregar_dados_combinados',
    'get_opcoes_filtro', 
    'get_unique_values_safe',
    'get_estatisticas_dashboard',
    'exportar_dados_csv',
    'formatar_numero',
    'formatar_data',
    'formatar_protocolo'
]

# Configurar logging
logger = logging.getLogger(__name__)

# ======================================================================================
# CONSTANTES ESPECÍFICAS PARA CERTIFICADOS (MANTIDAS DO ORIGINAL)
# ======================================================================================

# Constantes específicas para certificados
ARQUIVOS_CERTIFICADOS = [
    r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\00.CERTIFICADOS\FORM 067 - REV 00 - Controle de Certificados(2026)..xlsm",
    r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\00.CERTIFICADOS\FORM 067 - REV 00 - Controle de Certificados(2025).xlsm"
]

# Constantes para relatórios técnicos
PASTA_RELATORIOS = r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\0.1 RELATÓRIOS TÉCNICOS\003-PROJETOS"

# Constantes para controle de recebimento de amostras FORM 022 A
ARQUIVOS_RECEBIMENTO = [
    r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\03. RECEBIMENTO DE AMOSTRAS\FORM 022 A - REV 00 - Controle de recebimentos e descarte de amostras-AGIR - 2026.xlsm",
    r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\03. RECEBIMENTO DE AMOSTRAS\FORM 022 A - REV 00 - Controle de recebimentos e descarte de amostras-AGIR 2025.xlsm"
]

# ======================================================================================
# FUNÇÕES DE CARREGAMENTO E PROCESSAMENTO (VERSÃO SQLITE ROBUSTA)
# ======================================================================================

@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_dados_certificados():
    """
    Carrega dados EXCLUSIVAMENTE do FORM 067 (Certificados)
    DESVINCULADO DO FORM 022 A (Recebimento de Amostras)
    """
    try:
        # Carregar dados apenas da tabela certificados_067
        df = carregar_dados_combinados()
        
        if df.empty:
            logger.warning("Nenhum dado de certificado encontrado")
            return pd.DataFrame()
        
        # Os dados já vêm com as colunas corretas do FORM 067:
        # PT, CLIENTE, ENSAIO, NORMA, QUANTIDADE, ACREDITADO, DATA, ANO, etc.
        
        # Garantir colunas essenciais existam
        colunas_essenciais = ['CLIENTE', 'ENSAIO', 'QUANTIDADE', 'ANO', 'DATA']
        for coluna in colunas_essenciais:
            if coluna not in df.columns:
                if coluna == 'QUANTIDADE':
                    df[coluna] = 1
                elif coluna == 'ANO':
                    df[coluna] = str(datetime.now().year)
                else:
                    df[coluna] = ''
        
        logger.info(f"Certificados FORM 067 carregados: {len(df)} registros")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados certificados: {e}")
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def processar_dados_certificados(df):
    """Processa dados mantendo compatibilidade com o Dashboard original"""
    if df.empty:
        return df
    
    try:
        # Limpar dados
        df = df.dropna(subset=['CLIENTE', 'ENSAIO'], how='all')
        
        # Converter tipos de dados
        if 'QUANTIDADE' in df.columns:
            df['QUANTIDADE'] = pd.to_numeric(df['QUANTIDADE'], errors='coerce').fillna(0)
        
        # Converter colunas de data
        colunas_data = ['ACEITE_PROPOSTA', 'DATA_ENTREGA', 'DATA']
        for coluna in colunas_data:
            if coluna in df.columns:
                df[coluna] = pd.to_datetime(df[coluna], errors='coerce')
        
        # Limpar dados textuais
        colunas_texto = ['CLIENTE', 'ENSAIO', 'NORMA', 'STATUS', 'ACREDITADO']
        for coluna in colunas_texto:
            if coluna in df.columns:
                df[coluna] = df[coluna].astype(str).str.strip()
                df[coluna] = df[coluna].replace('', 'N/A')
        
        logger.info(f"Dados processados: {len(df)} registros")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao processar dados: {e}")
        return df

@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_relatorios_tecnicos():
    """Carrega relatórios técnicos usando SQLite robusto"""
    try:
        # Carregar dados do SQLite robusto filtrando apenas relatórios técnicos
        df = carregar_dados_combinados({'tipos': ['RELATÓRIO TÉCNICO']})
        
        if df.empty:
            return pd.DataFrame()
        
        # Mapear colunas para compatibilidade
        mapeamento_colunas = {
            'tipo': 'TIPO',
            'numero_relatorio': 'NUMERO_RELATORIO',
            'ensaio': 'ENSAIO',
            'norma': 'NORMA',
            'quantidade': 'QUANTIDADE',
            'prazo_entrega': 'PRAZO_ENTREGA_TEXTO',
            'acreditado': 'ACREDITADO',
            'data_aceite': 'ACEITE_PROPOSTA',
            'data_entrega_relatorio': 'DATA_ENTREGA',
            'status': 'STATUS',
            'numero_proposta': 'NUMERO_PROPOSTA',
            'cliente': 'CLIENTE',
            'cnpj': 'CNPJ',
            'ano': 'ANO',
            'tem_pasta_fas': 'TEM_PASTA_FAS',
            'PT': 'PT'
        }
        
        df_renomeado = df.rename(columns=mapeamento_colunas)
        
        logger.info(f"Relatórios técnicos carregados: {len(df_renomeado)} registros")
        return df_renomeado
        
    except Exception as e:
        logger.error(f"Erro ao carregar relatórios técnicos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_dados_recebimento():
    """Carrega dados de recebimento usando SQLite robusto"""
    try:
        # Carregar dados do SQLite robusto filtrando apenas recebimentos
        df = carregar_dados_combinados({'tipos': ['RECEBIMENTO AMOSTRA']})
        
        if df.empty:
            return pd.DataFrame()
        
        # Mapear colunas para compatibilidade
        mapeamento_colunas = {
            'tipo': 'TIPO',
            'numero_relatorio': 'NUMERO_RELATORIO',
            'ensaio': 'ENSAIO',
            'norma': 'NORMA',
            'quantidade': 'QUANTIDADE',
            'prazo_entrega': 'PRAZO_ENTREGA_TEXTO',
            'acreditado': 'ACREDITADO',
            'data_aceite': 'ACEITE_PROPOSTA',
            'data_entrega_relatorio': 'DATA_ENTREGA',
            'status': 'STATUS',
            'numero_proposta': 'NUMERO_PROPOSTA',
            'cliente': 'CLIENTE',
            'cnpj': 'CNPJ',
            'tipo_proposta': 'TIPO_PROPOSTA',
            'ano': 'ANO',
            'tem_pasta_fas': 'TEM_PASTA_FAS',
            'PT': 'PT'
        }
        
        df_renomeado = df.rename(columns=mapeamento_colunas)
        
        logger.info(f"Dados recebimento carregados: {len(df_renomeado)} registros")
        return df_renomeado
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados recebimento: {e}")
        return pd.DataFrame()

def carregar_correlacao_normas_ensaios():
    """Carrega correlação normas-ensaios dos arquivos Excel originais"""
    try:
        correlacao_normas = pd.DataFrame()
        
        # Tentar carregar dos arquivos Excel originais
        for arquivo in ARQUIVOS_CERTIFICADOS:
            try:
                if os.path.exists(arquivo):
                    # Ler aba "AUX_ENS" para correlação normas-ensaios
                    df_aux_ens = pd.read_excel(arquivo, sheet_name="AUX_ENS", header=0)
                    
                    # Criar correlação única entre coluna D (ensaios) e E (normas)
                    correlacao = df_aux_ens[['Unnamed: 3', 'Unnamed: 4']].dropna()
                    correlacao.columns = ['ENSAIO', 'NORMA']
                    correlacao = correlacao.drop_duplicates()
                    
                    if not correlacao.empty:
                        correlacao_normas = pd.concat([correlacao_normas, correlacao], ignore_index=True)
                        logger.info(f"Correlação carregada de {arquivo}: {len(correlacao)} itens")
                    
            except Exception as e:
                logger.warning(f"Erro ao ler correlação de {arquivo}: {e}")
                continue
        
        # Remover duplicatas finais
        if not correlacao_normas.empty:
            correlacao_normas = correlacao_normas.drop_duplicates()
            correlacao_normas = correlacao_normas.dropna()
            
            # Limpar dados
            correlacao_normas['ENSAIO'] = correlacao_normas['ENSAIO'].astype(str).str.strip()
            correlacao_normas['NORMA'] = correlacao_normas['NORMA'].astype(str).str.strip()
            
            # Remover linhas vazias
            correlacao_normas = correlacao_normas[
                (correlacao_normas['ENSAIO'] != '') & 
                (correlacao_normas['NORMA'] != '')
            ]
            
            logger.info(f"Correlação normas-ensaios final: {len(correlacao_normas)} itens")
        
        # Salvar no session state para uso no Dashboard
        st.session_state['Correlacao_normas-ensaios'] = correlacao_normas
        
        return correlacao_normas
        
    except Exception as e:
        logger.error(f"Erro ao carregar correlação normas-ensaios: {e}")
        return pd.DataFrame()

def carregar_dados_completos():
    """Carrega e combina dados de certificados e relatórios técnicos"""
    # Carregar certificados
    df_certificados = carregar_dados_certificados()
    if not df_certificados.empty:
        df_certificados = processar_dados_certificados(df_certificados)
        # Adicionar coluna TIPO se não existir
        if 'TIPO' not in df_certificados.columns:
            df_certificados['TIPO'] = 'CERTIFICADO'
    
    # Carregar relatórios técnicos
    df_relatorios = carregar_relatorios_tecnicos()
    
    # Combinar dados
    if not df_certificados.empty and not df_relatorios.empty:
        df_completo = pd.concat([df_certificados, df_relatorios], ignore_index=True)
    elif not df_certificados.empty:
        df_completo = df_certificados
    elif not df_relatorios.empty:
        df_completo = df_relatorios
    else:
        df_completo = pd.DataFrame()
    
    return df_completo

# ======================================================================================
# FUNÇÕES DE ESTATÍSTICAS (VERSÃO SQLITE ROBUSTA)
# ======================================================================================

def calcular_estatisticas_certificados(df):
    """Calcula estatísticas usando SQLite robusto mas mantendo estrutura"""
    try:
        # Usar estatísticas do SQLite robusto
        stats_sqlite = get_estatisticas_dashboard()
        
        # Mapear para estrutura esperada pelo Dashboard
        stats = {
            'total_certificados': stats_sqlite.get('total_registros', 0),
            'total_amostras': stats_sqlite.get('total_quantidade', 0),
            'clientes_unicos': stats_sqlite.get('clientes_unicos', 0),
            'ensaios_unicos': stats_sqlite.get('ensaios_unicos', 0),
            'normas_unicas': stats_sqlite.get('normas_unicas', 0),
        }
        
        # Estatísticas por ano (se disponível nos dados)
        if not df.empty and 'ANO' in df.columns:
            stats['por_ano'] = df.groupby('ANO').size().to_dict()
        
        # Estatísticas por acreditado (se disponível nos dados)
        if not df.empty and 'ACREDITADO' in df.columns:
            stats['por_acreditado'] = df['ACREDITADO'].value_counts().to_dict()
        
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas: {e}")
        return {}

# ======================================================================================
# FUNÇÕES DE EXPORTAÇÃO (MANTIDAS DO ORIGINAL)
# ======================================================================================

def exportar_dados_csv(df, nome_arquivo="certificados_exportados"):
    """Exporta dados para CSV usando função do SQLite robusto"""
    try:
        return exportar_dados_csv(df, nome_arquivo)
    except Exception as e:
        logger.error(f"Erro ao exportar CSV: {e}")
        return False

def exportar_dados_excel(df, nome_arquivo="certificados_exportados"):
    """Exporta dados para Excel"""
    try:
        if df.empty:
            st.warning("Não há dados para exportar")
            return False
        
        # Criar arquivo Excel em memória
        from io import BytesIO
        buffer = BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Certificados')
        
        buffer.seek(0)
        
        st.download_button(
            label="📥 Baixar Excel",
            data=buffer.getvalue(),
            file_name=f"{nome_arquivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao exportar Excel: {e}")
        return False

# ======================================================================================
# FUNÇÕES DE FORMATAÇÃO (MANTIDAS DO ORIGINAL)
# ======================================================================================

def formatar_numero(numero, decimal_places=0):
    """Formata número para exibição"""
    if pd.isna(numero):
        return "0"
    
    if decimal_places == 0:
        return f"{int(numero):,}".replace(",", ".")
    else:
        return f"{numero:,.{decimal_places}f}".replace(",", ".")

def formatar_data(data):
    """Formata data para exibição"""
    if pd.isna(data):
        return "-"
    if isinstance(data, str):
        return data
    return data.strftime('%d/%m/%Y')

def formatar_protocolo(pt):
    """Formata protocolo para exibição"""
    if pd.isna(pt):
        return "-"
    return str(pt).strip()

# ======================================================================================
# FUNÇÕES DE FILTRO AVANÇADO (VERSÃO SQLITE ROBUSTA)
# ======================================================================================

def filtrar_dados_avancado(df, filtros):
    """Aplica filtros avançados usando SQLite robusto"""
    try:
        if df.empty:
            return df
        
        df_filtrado = df.copy()
        
        # Filtro por período de data
        if 'ACEITE_PROPOSTA' in df.columns and 'periodo_data' in filtros:
            data_inicio = filtros['periodo_data'].get('inicio')
            data_fim = filtros['periodo_data'].get('fim')
            
            if data_inicio:
                df_filtrado['ACEITE_PROPOSTA'] = pd.to_datetime(df_filtrado['ACEITE_PROPOSTA'], errors='coerce')
                df_filtrado = df_filtrado[df_filtrado['ACEITE_PROPOSTA'] >= data_inicio]
            if data_fim:
                df_filtrado['ACEITE_PROPOSTA'] = pd.to_datetime(df_filtrado['ACEITE_PROPOSTA'], errors='coerce')
                df_filtrado = df_filtrado[df_filtrado['ACEITE_PROPOSTA'] <= data_fim]
        
        # Filtro por quantidade mínima
        if 'QUANTIDADE' in df.columns and 'quantidade_minima' in filtros:
            qtd_min = filtros['quantidade_minima']
            if qtd_min and qtd_min > 0:
                df_filtrado = df_filtrado[df_filtrado['QUANTIDADE'] >= qtd_min]
        
        # Filtro por texto (busca em múltiplas colunas)
        if 'texto_busca' in filtros and filtros['texto_busca']:
            texto = filtros['texto_busca'].upper()
            colunas_texto = ['CLIENTE', 'ENSAIO', 'NORMA', 'NUMERO_RELATORIO']
            
            mascara = pd.Series(False, index=df_filtrado.index)
            for coluna in colunas_texto:
                if coluna in df_filtrado.columns:
                    mascara |= df_filtrado[coluna].astype(str).str.contains(texto, na=False)
            
            df_filtrado = df_filtrado[mascara]
        
        return df_filtrado
        
    except Exception as e:
        logger.error(f"Erro ao aplicar filtros avançados: {e}")
        return df

# ======================================================================================
# FUNÇÕES DE VALIDAÇÃO (MANTIDAS DO ORIGINAL)
# ======================================================================================

def validar_dados_certificados(df):
    """Valida a qualidade dos dados dos certificados"""
    if df.empty:
        return False, "DataFrame vazio"
    
    # Verificar colunas essenciais
    colunas_essenciais = ['CLIENTE', 'ENSAIO']
    for coluna in colunas_essenciais:
        if coluna not in df.columns:
            return False, f"Coluna essencial '{coluna}' não encontrada"
    
    # Verificar se há dados válidos
    if df['CLIENTE'].isna().all() and df['ENSAIO'].isna().all():
        return False, "Não há dados válidos de CLIENTE ou ENSAIO"
    
    return True, "Dados válidos"

def limpar_texto(texto):
    """Limpa e normaliza texto"""
    if pd.isna(texto):
        return ""
    return str(texto).strip().upper()

# ======================================================================================
# INICIALIZAÇÃO AUTOMÁTICA DA CORRELAÇÃO
# ======================================================================================

def inicializar_correlacoes():
    """Inicializa correlações normas-ensaios automaticamente"""
    try:
        # Verificar se já existe no session state
        if 'Correlacao_normas-ensaios' not in st.session_state:
            carregar_correlacao_normas_ensaios()
        
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar correlações: {e}")
        return False
