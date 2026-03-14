"""
=========================================================================
UTILS NOVO DASHBOARD - MÓDULO ISOLADO (ESTRUTURA FORM 067)
=========================================================================
Este arquivo contém funções exclusivas para o Novo Dashboard.
Usa a MESMA ESTRUTURA de dados do FORM 067 (Certificados).
NÃO importa funções do utils_certificados.py para evitar conflitos.
=========================================================================
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import re
import logging
from datetime import datetime
from contextlib import contextmanager
import glob
import plotly.express as px

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ======================================================================================
# 1. CONFIGURAÇÃO DE ARQUIVOS - FORM 067 (MESMA FONTE DO DASHBOARD DE CERTIFICADOS)
# ======================================================================================

FILES_CONFIG = {
    "certificados_2026": {
        "local_path": r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\00.CERTIFICADOS\FORM 067 - REV 00 - Controle de Certificados(2026)..xlsm",
        "tipo": "certificado", "ano": "2026"
    },
    "certificados_2025": {
        "local_path": r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\00.CERTIFICADOS\FORM 067 - REV 00 - Controle de Certificados(2025).xlsm",
        "tipo": "certificado", "ano": "2025"
    },
    "propostas_comerciais": {
        "local_path": r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\007 - Controle de Propostas\FORM 044 - REV 05 - Controle de Propostas E-VIAS.AFIRMA.xlsx",
        "tipo": "proposta", "ano": "multi-ano"
    },
}

# Caminho base para propostas comerciais
BASE_DIR_PROPOSTAS = r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\000 - Comercial\01 - Propostas Comerciais"

# Nome do banco de dados (mesmo banco, mas tabelas diferentes)
DB_NAME = "lab_central_master.db"

# Nome da tabela específica deste dashboard (diferente de certificados_067)
TABELA_NOVO_DASHBOARD = "novo_dashboard_067"

# ======================================================================================
# 2. GERENCIADOR DE DADOS - ISOLADO
# ======================================================================================

class DataBridgeNovo:
    """
    Gerenciador de dados exclusivo para o Novo Dashboard.
    Usa estrutura do FORM 067 mas tabela separada.
    """
    
    def __init__(self):
        self.is_cloud = False
        
    def get_file_content(self, config_key):
        """Retorna o caminho do arquivo se existir"""
        if config_key not in FILES_CONFIG:
            return None
        config = FILES_CONFIG[config_key]
        local_path = config["local_path"]
        if os.path.exists(local_path):
            return local_path
        return None

    @contextmanager
    def get_db_conn(self):
        """Gerenciador de contexto para conexão com o banco"""
        conn = sqlite3.connect(DB_NAME)
        try:
            yield conn
        finally:
            conn.close()
            
    def init_db(self):
        """
        Inicializa a tabela específica do Novo Dashboard.
        Estrutura baseada no FORM 067 - Aba "FORM 067"
        """
        with self.get_db_conn() as conn:
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {TABELA_NOVO_DASHBOARD} (
                    ID TEXT,
                    PT TEXT,
                    PT_NORMALIZADO TEXT,
                    CLIENTE TEXT,
                    ENSAIO TEXT,
                    NORMA TEXT,
                    QUANTIDADE REAL,
                    ACREDITADO TEXT,
                    FORMULARIO TEXT,
                    DATA TEXT,
                    ANO TEXT,
                    RELATORIO_VINCULADO TEXT,
                    NUM_CERTIFICADO TEXT
                )
            ''')
            conn.commit()
            logger.info(f"Tabela {TABELA_NOVO_DASHBOARD} inicializada")


# Instância global do gerenciador
bridge_novo = DataBridgeNovo()
bridge_novo.init_db()


# ======================================================================================
# FUNÇÕES AUXILIARES (FORM 067)
# ======================================================================================

def normalizar_pt(pt_raw):
    """Normaliza número do PT"""
    if not pt_raw: return None
    pt_str = str(pt_raw).upper().strip()
    match = re.search(r'(\d+)', pt_str)
    return match.group(1) if match else None

# ======================================================================================
# 3. FUNÇÕES DE CARREGAMENTO DE DADOS
# ======================================================================================

def carregar_dados():
    """
    Carrega dados da tabela do Novo Dashboard.
    Estrutura FORM 067: PT, CLIENTE, ENSAIO, NORMA, QUANTIDADE, ACREDITADO, DATA, ANO
    """
    try:
        with bridge_novo.get_db_conn() as conn:
            df = pd.read_sql_query(f"SELECT * FROM {TABELA_NOVO_DASHBOARD}", conn)
            logger.info(f"Dados carregados: {len(df)} registros")
            return df
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()


def carregar_dados_do_excel():
    """
    Carrega dados do FORM 067 (Certificados) diretamente do Excel.
    
    ESTRUTURA FORM 067 - Aba "FORM 067":
    - Cabeçalhos na linha 7 (índice 6)
    - Dados começam na linha 8 (índice 7)
    
    COLUNAS:
    - A (0): ID
    - B (1): CLIENTE
    - C (2): ENSAIO
    - D (3): NORMA
    - E (4): QUANTIDADE
    - F (5): PT
    - G (6): ANO
    - H (7): ACREDITADO ← Se vazio ou "-", NÃO CONTAR
    - I (8): FORMULÁRIO
    - N (13): Nº CERTIFICADO
    - P (15): DATA
    """
    todos = []
    
    for ano_arquivo in ['2026', '2025']:
        key = f'certificados_{ano_arquivo}'
        if key not in FILES_CONFIG:
            continue
            
        path = FILES_CONFIG[key]['local_path']
        if not os.path.exists(path): 
            logger.warning(f"Arquivo não encontrado: {path}")
            continue
            
        try:
            # Ler aba específica "FORM 067"
            df = pd.read_excel(path, sheet_name='FORM 067', header=None, engine='openpyxl')
            logger.info(f"Lendo FORM 067 de {ano_arquivo}: {len(df)} linhas")
            
            # Dados começam na linha 8 (índice 7)
            for i in range(7, len(df)):
                try:
                    row = df.iloc[i]
                    
                    # Coluna L (11): IDENTIFICAÇÃO AMOSTRA
                    # REGRA: Se contiver "Número disponível" ou similar, DESCONSIDERAR
                    id_amostra = str(row.iloc[11]).strip() if pd.notna(row.iloc[11]) else ''
                    id_amostra_upper = id_amostra.upper()
                    if 'NÚMERO DISPONÍVEL' in id_amostra_upper or 'NUMERO DISPONIVEL' in id_amostra_upper or 'NÚMEROS DISPONÍVEIS' in id_amostra_upper or 'NUMEROS DISPONIVEIS' in id_amostra_upper:
                        continue
                    
                    # Coluna C (2): ENSAIO - obrigatório
                    ensaio = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
                    if len(ensaio) < 2 or ensaio.upper() in ['NAN', 'NONE', 'ENSAIO', '']:
                        continue
                    
                    # Coluna B (1): CLIENTE
                    cliente = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    if cliente in ['-', 'nan', 'NaN', 'CLIENTE', ''] or pd.isna(row.iloc[1]):
                        cliente = 'NÃO INFORMADO'
                    
                    # Coluna D (3): NORMA
                    norma = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
                    if norma in ['-', 'nan', 'NaN']:
                        norma = ''
                    
                    # Coluna E (4): QUANTIDADE
                    qtd = 1
                    try:
                        qtd_raw = row.iloc[4]
                        if pd.notna(qtd_raw) and str(qtd_raw).strip() not in ['-', '']:
                            qtd = float(qtd_raw) if float(qtd_raw) > 0 else 1
                    except: 
                        pass
                    
                    # Coluna F (5): PT
                    pt = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ''
                    if pt in ['-', 'nan', 'NaN']:
                        pt = ''
                    
                    # Coluna G (6): ANO
                    ano_valor = str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else ano_arquivo
                    if ano_valor in ['-', 'nan', 'NaN', '']:
                        ano_valor = ano_arquivo
                    # Pegar apenas os 4 primeiros caracteres se for ano composto
                    if len(ano_valor) >= 4:
                        ano_valor = ano_valor[:4]
                    
                    # Coluna H (7): ACREDITADO
                    # REGRA: Se vazio (NaN) ou "-", NÃO CONTAR como acreditado
                    acreditado_raw = row.iloc[7]
                    acreditado = None  # None = não informado/vazio
                    if pd.notna(acreditado_raw):
                        acred_str = str(acreditado_raw).strip().upper()
                        if acred_str in ['SIM', 'S', 'YES', 'Y']:
                            acreditado = 'SIM'
                        elif acred_str in ['NÃO', 'NAO', 'N', 'NO', 'NÃO']:
                            acreditado = 'NÃO'
                        elif acred_str == '-':
                            acreditado = None  # "-" = não contar
                    
                    # Coluna N (13): Nº CERTIFICADO
                    num_cert = str(row.iloc[13]).strip() if pd.notna(row.iloc[13]) else ''
                    if num_cert in ['-', 'nan', 'NaN']:
                        num_cert = ''
                    
                    # Coluna P (15): DATA
                    data_cert = None
                    if pd.notna(row.iloc[15]) and str(row.iloc[15]).strip() not in ['-', '']:
                        data_cert = pd.to_datetime(row.iloc[15], errors='coerce')
                    
                    # Coluna K (10): RELATÓRIO VINCULADO
                    relatorio = str(row.iloc[10]).strip() if pd.notna(row.iloc[10]) else ''
                    if relatorio in ['-', 'nan', 'NaN']:
                        relatorio = ''
                    
                    # Coluna I (8): FORMULÁRIO
                    formulario = str(row.iloc[8]).strip() if pd.notna(row.iloc[8]) else ''
                    
                    # ID (coluna A)
                    id_registro = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    
                    todos.append({
                        'ID': id_registro,
                        'PT': pt,
                        'PT_NORMALIZADO': normalizar_pt(pt),
                        'CLIENTE': cliente,
                        'ENSAIO': ensaio,
                        'NORMA': norma,
                        'QUANTIDADE': qtd,
                        'ACREDITADO': acreditado,  # SIM, NÃO ou None
                        'FORMULARIO': formulario,
                        'DATA': data_cert.strftime('%Y-%m-%d') if data_cert else None,
                        'ANO': ano_valor,
                        'RELATORIO_VINCULADO': relatorio,
                        'NUM_CERTIFICADO': num_cert
                    })
                except Exception as e: 
                    continue
                    
            logger.info(f"FORM 067 {ano_arquivo}: {len([t for t in todos if str(t.get('ANO', '')).startswith(ano_arquivo[:4])])} registros válidos")
            
        except Exception as e:
            logger.error(f"Erro ao ler FORM 067 {ano_arquivo}: {e}")
            continue
    
    if todos:
        df_final = pd.DataFrame(todos)
        df_final = df_final[df_final['ENSAIO'].str.len() > 1]  # Remover ensaios vazios
        logger.info(f"Total de registros carregados: {len(df_final)}")
        return df_final
    
    return pd.DataFrame()

# ======================================================================================
# 4. FUNÇÕES DE PROCESSAMENTO DE DADOS
# ======================================================================================

def processar_dados(df):
    """
    Processa dados do FORM 067.
    Campos: PT, CLIENTE, ENSAIO, NORMA, QUANTIDADE, ACREDITADO, DATA, ANO
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_processado = df.copy()
    
    # Remover duplicatas
    df_processado = df_processado.drop_duplicates()
    
    # Tratar valores nulos em strings
    for col in ['PT', 'CLIENTE', 'ENSAIO', 'NORMA', 'ACREDITADO', 'ANO']:
        if col in df_processado.columns:
            df_processado[col] = df_processado[col].fillna('')
    
    # Converter DATA para datetime
    if 'DATA' in df_processado.columns:
        df_processado['DATA'] = pd.to_datetime(df_processado['DATA'], errors='coerce')
        df_processado['MES'] = df_processado['DATA'].dt.month
    
    # Garantir QUANTIDADE numérica
    if 'QUANTIDADE' in df_processado.columns:
        df_processado['QUANTIDADE'] = pd.to_numeric(df_processado['QUANTIDADE'], errors='coerce').fillna(1)
    
    return df_processado


def calcular_estatisticas(df):
    """
    Calcula estatísticas do FORM 067 para exibição no dashboard.
    
    IMPORTANTE para ACREDITADO (Coluna H):
    - Só conta registros onde ACREDITADO não é None/vazio
    - None = não informado, não entra no cálculo de acreditados
    """
    if df is None or df.empty:
        return {
            'total_certificados': 0,
            'total_quantidade': 0,
            'clientes_unicos': 0,
            'ensaios_unicos': 0,
            'acreditados_sim': 0,
            'acreditados_nao': 0,
            'acreditados_nao_informado': 0
        }
    
    total_certificados = len(df)
    total_quantidade = df['QUANTIDADE'].sum() if 'QUANTIDADE' in df.columns else 0
    clientes_unicos = df['CLIENTE'].nunique() if 'CLIENTE' in df.columns else 0
    ensaios_unicos = df['ENSAIO'].nunique() if 'ENSAIO' in df.columns else 0
    
    # Estatísticas de ACREDITADO - Coluna H
    # REGRA: Se vazio (None) ou "-", NÃO CONTAR
    acreditados_sim = 0
    acreditados_nao = 0
    acreditados_nao_informado = 0
    
    if 'ACREDITADO' in df.columns:
        acreditados_sim = len(df[df['ACREDITADO'] == 'SIM'])
        acreditados_nao = len(df[df['ACREDITADO'] == 'NÃO'])
        acreditados_nao_informado = len(df[df['ACREDITADO'].isna() | (df['ACREDITADO'] == '')])
    
    return {
        'total_certificados': total_certificados,
        'total_quantidade': int(total_quantidade),
        'clientes_unicos': clientes_unicos,
        'ensaios_unicos': ensaios_unicos,
        'acreditados_sim': acreditados_sim,
        'acreditados_nao': acreditados_nao,
        'acreditados_nao_informado': acreditados_nao_informado
    }


def carregar_form044():
    """
    Carrega dados do FORM 044 (Controle de Propostas).
    Estrutura baseada no arquivo Excel FORM 044.
    """
    try:
        path = FILES_CONFIG['propostas_comerciais']['local_path']
        if not os.path.exists(path):
            logger.warning(f"Arquivo FORM 044 não encontrado: {path}")
            return pd.DataFrame()
        
        # Carregar aba principal (assume "FORM 044" ou primeira aba)
        df = pd.read_excel(path, sheet_name=0, engine='openpyxl')
        logger.info(f"FORM 044 carregado: {len(df)} linhas")
        
        # Processar colunas essenciais
        # Assume colunas: FAS, EMPRESA, STATUS, etc.
        if df.empty:
            return df
        
        # Limpeza básica
        df = df.dropna(how='all')
        
        # Normalizar nomes de colunas
        df.columns = df.columns.str.strip().str.upper()
        
        # Filtrar apenas propostas aprovadas ou similares
        if 'STATUS' in df.columns:
            df = df[df['STATUS'].str.upper().isin(['APROVADA', 'APROVADO', 'APROVADAS']) | df['STATUS'].isna()]
        
        logger.info(f"FORM 044 processado: {len(df)} propostas aprovadas")
        return df
        
    except Exception as e:
        logger.error(f"Erro ao carregar FORM 044: {e}")
        return pd.DataFrame()

def carregar_dados_em_execucao():
    """
    Carrega dados de propostas em execução (FORM 022A).
    Usa a mesma lógica do dashboard principal.
    """
    try:
        with bridge_novo.get_db_conn() as conn:
            # Assume tabela de execucao existe ou usar dados do FORM 067 como proxy
            # Para FAS, precisamos de NUMERO_PROPOSTA, CLIENTE
            # Usar dados do FORM 067 como proxy para execucao
            df = pd.read_sql_query("SELECT PT as NUMERO_PROPOSTA, CLIENTE FROM novo_dashboard_067 WHERE PT IS NOT NULL", conn)
            logger.info(f"Dados em execução carregados: {len(df)} registros")
            return df
    except Exception as e:
        logger.error(f"Erro ao carregar dados em execução: {e}")
        return pd.DataFrame(lista_processamento).drop_duplicates(subset=['PC'])

# ======================================================================================
# 6. FUNÇÕES AUXILIARES
# ======================================================================================

def get_opcoes_unicas(df, coluna):
    """
    Retorna uma lista ordenada de valores únicos de uma coluna de um DataFrame.
    Útil para preencher caixas de seleção (selectbox/multiselect).
    """
    if df is None or df.empty or coluna not in df.columns:
        return []
    
    # Extrai valores únicos, remove vazios (NaN) e converte para string
    valores = df[coluna].dropna().unique()
    lista_valores = [str(v).strip() for v in valores if str(v).strip() != '']
    
    return sorted(lista_valores)


def formatar_numero(valor, decimais=0):
    """Formata número com separador de milhares"""
    try:
        if decimais == 0:
            return f"{int(valor):,}".replace(",", ".")
        return f"{float(valor):,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)


def formatar_data(valor, formato="%d/%m/%Y"):
    """Formata data para exibição"""
    try:
        if pd.isna(valor):
            return ""
        if isinstance(valor, str):
            valor = pd.to_datetime(valor)
        return valor.strftime(formato)
    except:
        return str(valor)


def exportar_csv(df, nome_arquivo="dados_exportados"):
    """
    Prepara dados para download em CSV.
    
    Args:
        df: DataFrame para exportar
        nome_arquivo: nome base do arquivo
        
    Returns:
        bytes do CSV
    """
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# ======================================================================================
# 7. SINCRONIZAÇÃO DE DADOS
# ======================================================================================

def sync_dados():
    """
    Sincroniza dados do Excel para o SQLite.
    Se as fontes reais não existirem, cria dados de demonstração.
    """
    try:
        # Limpar cache do Streamlit
        st.cache_data.clear()
        
        # Carregar dados frescos do Excel
        df = carregar_dados_do_excel()
        
        # Se não houver dados reais, criar dados de demonstração
        if df.empty:
            logger.info("Fontes reais não encontradas. Criando dados de demonstração...")
            df = criar_dados_demonstracao()
        
        if df.empty:
            logger.warning("Nenhum dado disponível")
            return False
        
        # Processar dados
        df_processado = processar_dados(df)
        
        # Salvar no SQLite
        with bridge_novo.get_db_conn() as conn:
            df_processado.to_sql(
                TABELA_NOVO_DASHBOARD, 
                conn, 
                if_exists='replace', 
                index=False
            )
        
        logger.info(f"Sincronização completa: {len(df_processado)} registros")
        return True
        
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        return False


def criar_dados_demonstracao():
    """
    Cria dados de demonstração com estrutura do FORM 067.
    
    ESTRUTURA:
    - ID, PT, CLIENTE, ENSAIO, NORMA, QUANTIDADE, ACREDITADO, FORMULARIO, DATA, ANO
    
    REGRA ACREDITADO (Coluna H):
    - None = não informado (não conta)
    - 'SIM' = acreditado
    - 'NÃO' = não acreditado
    """
    import random
    from datetime import datetime, timedelta
    
    dados = []
    
    # Opções baseadas no FORM 067 real (2025)
    clientes = [
        'EPR LITORAL PIONEIRO S.A.',
        'COMPASA DO BRASIL DISTRIBUIDORA DE ASFALTOS LTDA',
        'STRATA ENGENHARIA LTDA',
        'ELLENCO CONSTRUÇÕES',
        'BESIX-ECB LTDA',
        'PATRIA INVESTIMENTOS LTDA',
        'ETHOS ENGENHARIA E INFRAESTRUTURA S/A',
        'NÃO INFORMADO'
    ]
    
    ensaios = [
        'Granulometria',
        'Teor de Pulverulentos',
        'Durabilidade - Graúdo',
        'Densidade e Absorção - Graúdo',
        'Equivalente de Areia',
        'Abrasão Los Angeles',
        'Resistência à Compressão Simples - Concreto',
        'Teor de Ligante - Rotarex',
        'Densidade RICE',
        'Módulo de Resiliência - CAUQ (Cliente)',
        'Densidade e Absorção - Miúdo',
        'Índice de Forma - Crivo'
    ]
    
    normas = [
        'DNIT 450/2024 - ME',
        'DNIT 135/2018 - ME',
        'DNIT 180/2018 - ME',
        'ABNT NBR 15617:2015',
        'DNIT 164/2013 - ME',
        'DNIT 054/2004 - ME'
    ]
    
    formularios = ['FORM 052 G', 'FORM 091 B', 'CDM', 'FORM 045']
    
    # ACREDITADO: None (60%), 'Não' (30%), 'Sim' (10%) - reflete dados reais
    acreditados_opcoes = [None, None, None, None, None, None, 'NÃO', 'NÃO', 'NÃO', 'SIM']
    
    data_base = datetime(2025, 1, 1)
    
    for i in range(200):
        dias_aleatorios = random.randint(0, 400)
        data_registro = data_base + timedelta(days=dias_aleatorios)
        ano = str(data_registro.year)
        
        # Cliente: 60% tem cliente, 40% não informado
        cliente = random.choice(clientes) if random.random() > 0.4 else 'NÃO INFORMADO'
        
        dados.append({
            'ID': str(random.randint(1, 2000)),
            'PT': f'PT-{random.randint(1, 500):04d}' if random.random() > 0.3 else '',
            'PT_NORMALIZADO': str(random.randint(1, 500)) if random.random() > 0.3 else None,
            'CLIENTE': cliente,
            'ENSAIO': random.choice(ensaios),
            'NORMA': random.choice(normas),
            'QUANTIDADE': random.randint(1, 10),
            'ACREDITADO': random.choice(acreditados_opcoes),  # None, 'SIM' ou 'NÃO'
            'FORMULARIO': random.choice(formularios),
            'DATA': data_registro.strftime('%Y-%m-%d') if random.random() > 0.3 else None,
            'ANO': ano,
            'RELATORIO_VINCULADO': f'RT-{random.randint(100, 999)}/{ano}' if random.random() > 0.5 else '',
            'NUM_CERTIFICADO': f'CE.{random.randint(1, 200):03d}.{random.randint(1,12):02d}.{ano}.R00'
        })
    
    logger.info(f"Dados de demonstração FORM 067 criados: {len(dados)} registros")
    return pd.DataFrame(dados)


# ======================================================================================
# 8. CACHE PARA PERFORMANCE
# ======================================================================================

@st.cache_data(ttl=300)  # Cache de 5 minutos
def carregar_dados_cached():
    """
    Versão com cache da função carregar_dados.
    Use esta para melhor performance no dashboard.
    """
    return carregar_dados()


@st.cache_data(ttl=300)
def get_estatisticas_cached(df_hash):
    """
    Calcula estatísticas com cache.
    O parâmetro df_hash é usado para invalidar cache quando dados mudam.
    """
    df = carregar_dados_cached()
    return calcular_estatisticas(df)


# ======================================================================================
# FUNÇÕES PARA FAS TOTAL - EXTRAÇÃO DE FORM 045
# ======================================================================================

def normalizar_identificacao(identificacao):
    """Normaliza identificadores (FAS, PT, PC) para comparação."""
    if pd.isna(identificacao):
        return None
    s = str(identificacao).upper().strip()
    s = s.replace('PC ', '').replace('PC', '').replace('FAS ', '').replace('FAS', '').replace('/', '.').strip()
    return s

def buscar_e_extrair_form045(pc_numero, empresa_nome=""):
    """
    Busca o arquivo FORM 045 no diretório comercial com base no ano da PC
    e extrai os serviços e quantidades (E20:G42).
    """
    # 1. Normalização do número da PC (Ex: 041/25 -> 041.25)
    pc_original = str(pc_numero).strip().upper()
    pc_clean = pc_original.replace('/', '.')
    
    # 2. Identificação do Ano para a pasta correta
    ano = "2025" if ".25" in pc_clean else "2026" if ".26" in pc_clean else ""
    if not ano: return pd.DataFrame()
    
    caminho_ano = os.path.join(BASE_DIR_PROPOSTAS, ano)
    if not os.path.exists(caminho_ano): return pd.DataFrame()
    
    # 3. Localizar a pasta da PC (Busca parcial pelo código da PC)
    pastas = [p for p in os.listdir(caminho_ano) if os.path.isdir(os.path.join(caminho_ano, p))]
    caminho_pc = ""
    for p in pastas:
        if pc_clean in p:
            caminho_pc = os.path.join(caminho_ano, p)
            break
            
    if not caminho_pc: return pd.DataFrame()
    
    # 4. Localizar o arquivo Excel FORM 045
    arquivos = glob.glob(os.path.join(caminho_pc, "*.xls*"))
    arquivo_alvo = ""
    for f in arquivos:
        nome_f = os.path.basename(f).upper()
        if "FORM 045" in nome_f:
            arquivo_alvo = f
            break
            
    if not arquivo_alvo: return pd.DataFrame()
    
    # 5. Extração dos Dados (Range E20:G42)
    try:
        # skiprows=19 (pula até a linha 20), usecols="E:G"
        df_temp = pd.read_excel(arquivo_alvo, skiprows=19, nrows=23, usecols="E:G", header=None)
        df_temp.columns = ['Servico', 'Norma', 'Quantidade']
        
        # Limpeza: Remove linhas vazias ou com quantidade zero
        df_temp = df_temp.dropna(subset=['Servico', 'Quantidade'])
        df_temp['Quantidade'] = pd.to_numeric(df_temp['Quantidade'], errors='coerce').fillna(0)
        df_temp = df_temp[df_temp['Quantidade'] > 0]
        
        # Adiciona colunas de identificação
        df_temp['PC_FAS'] = pc_original
        df_temp['EMPRESA'] = empresa_nome
        df_temp['EMPRESA_PC'] = f"{empresa_nome} - {pc_original}"
        
        return df_temp
    except Exception as e:
        return pd.DataFrame()

def calcular_fas_total(df_aprovadas, df_em_execucao):
    """
    Compara PCs Aprovadas vs Em Execução para gerar a lista FAS TOTAL.
    Normaliza e retira duplicatas.
    """
    # Normalizar IDs para comparação
    pcs_aprovadas = set(df_aprovadas['FAS'].apply(normalizar_identificacao).unique()) if not df_aprovadas.empty else set()
    pcs_execucao = set(df_em_execucao['NUMERO_PROPOSTA'].apply(normalizar_identificacao).unique()) if not df_em_execucao.empty else set()
    
    # Se houver diferença (Fas aprovadas que ainda não entraram em execução)
    diferenca = pcs_aprovadas - pcs_execucao
    
    # Unir tudo para o FAS TOTAL (Aprovadas + Em Execução)
    total_set = pcs_aprovadas.union(pcs_execucao)
    
    # Recuperar os nomes originais e empresas das PCs para o processamento
    lista_processamento = []
    
    # Pegar dados de origem (priorizando 044 por ser a entrada oficial)
    for pc in total_set:
        row = df_aprovadas[df_aprovadas['FAS'].apply(normalizar_identificacao) == pc]
        if not row.empty:
            lista_processamento.append({
                'PC': row.iloc[0]['FAS'],
                'EMPRESA': row.iloc[0]['EMPRESA']
            })
        else:
            row_ex = df_em_execucao[df_em_execucao['NUMERO_PROPOSTA'].apply(normalizar_identificacao) == pc]
            if not row_ex.empty:
                lista_processamento.append({
                    'PC': row_ex.iloc[0]['NUMERO_PROPOSTA'],
                    'EMPRESA': row_ex.iloc[0]['CLIENTE']
                })
                
    return pd.DataFrame(lista_processamento).drop_duplicates(subset=['PC'])

# ======================================================================================
# EXECUÇÃO DIRETA (para testes)
# ======================================================================================

if __name__ == "__main__":
    print("=== Teste do Utils Novo Dashboard ===")
    print(f"Tabela: {TABELA_NOVO_DASHBOARD}")
    print(f"Banco: {DB_NAME}")
    
    # Testar carregamento
    df = carregar_dados()
    print(f"Registros carregados: {len(df)}")
    
    # Testar estatísticas
    stats = calcular_estatisticas(df)
    print(f"Estatísticas: {stats}")
