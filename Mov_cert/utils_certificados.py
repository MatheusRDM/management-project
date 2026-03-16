import streamlit as st
import pandas as pd
import sqlite3
import os
import io
import sys
import logging
from datetime import datetime
from contextlib import contextmanager
import docx
import re
from thefuzz import fuzz

# Tenta importar bibliotecas do Google (modo nuvem vs local)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ======================================================================================
# 1. CONFIGURAÇÃO DE ARQUIVOS E DIRETÓRIOS
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
    "recebimento_2026": {
        "local_path": r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\03. RECEBIMENTO DE AMOSTRAS\FORM 022 A - REV 00 - Controle de recebimentos e descarte de amostras-AGIR - 2026.xlsm",
        "tipo": "recebimento", "ano": "2026"
    },
    "recebimento_2025": {
        "local_path": r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\03. RECEBIMENTO DE AMOSTRAS\FORM 022 A - REV 00 - Controle de recebimentos e descarte de amostras-AGIR 2025.xlsm",
        "tipo": "recebimento", "ano": "2025"
    },
    "propostas_comerciais": {
        "local_path": r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\007 - Controle de Propostas\FORM 044 - REV 05 - Controle de Propostas E-VIAS.AFIRMA.xlsx",
        "tipo": "proposta", "ano": "multi-ano"
    },
}

LOCAL_PATH_RELATORIOS = r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\0.1 RELATÓRIOS TÉCNICOS\003-PROJETOS"
DIRETORIO_BASE_CAUQ = r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\0.2 PROJETOS CAUQ MARSHALL"
DB_NAME = "lab_central_master.db"

# ======================================================================================
# 2. GERENCIADOR DE DADOS
# ======================================================================================
class DataBridge:
    def __init__(self):
        from cloud_config import IS_CLOUD
        self.is_cloud = IS_CLOUD

    def get_file_content(self, config_key):
        if config_key not in FILES_CONFIG:
            return None
        config = FILES_CONFIG[config_key]
        local_path = config["local_path"]
        if os.path.exists(local_path):
            return local_path
        return None

    @contextmanager
    def get_db_conn(self):
        conn = sqlite3.connect(DB_NAME)
        try: yield conn
        finally: conn.close()
            
    def init_db(self):
        with self.get_db_conn() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS recebimentos (
                id INTEGER PRIMARY KEY, NUMERO_PROPOSTA TEXT, CLIENTE TEXT, STATUS TEXT, 
                DATA_RECEBIMENTO TEXT, DATA_ENTREGA TEXT, DIAS_VENCIMENTO REAL, 
                STATUS_PRAZO TEXT, MATERIAL TEXT, PEDREIRA TEXT, TEM_MATERIAL INTEGER,
                TIPO_PROPOSTA TEXT, ANO TEXT, PT_COLUNA_A TEXT, FONTE TEXT, 
                DATA_ENTREGA_FAS TEXT, PROJETO_FAS TEXT, E_CONTRATO_CONTINUO INTEGER)''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS certificados_067 (
                id INTEGER PRIMARY KEY, CLIENTE TEXT, ENSAIO TEXT, NORMA TEXT,
                QUANTIDADE REAL, PT TEXT, PT_NORMALIZADO TEXT, ANO_CERT TEXT, 
                RELATORIO_VINCULADO TEXT, NUM_CERTIFICADO TEXT, ENSAIO_CONCLUIDO INTEGER)''')

            conn.execute('''CREATE TABLE IF NOT EXISTS propostas (
                NUMERO_PROPOSTA TEXT, ANO TEXT, CLIENTE TEXT,
                STATUS_PROPOSTA TEXT, DATA_ACEITE_PROPOSTA DATETIME)''')

bridge = DataBridge()
bridge.init_db()

# ======================================================================================
# 3. FUNÇÕES AUXILIARES
# ======================================================================================

def normalizar_pc(pc_raw):
    if not pc_raw: return None
    pc_str = str(pc_raw).upper().strip()
    match = re.search(r'PC\s*(\d+)[\.\-](\d+)', pc_str, re.IGNORECASE)
    if match: return f"PC{match.group(1).zfill(3)}.{match.group(2)[:2]}"
    nums = re.findall(r'\d+\.\d+', pc_str)
    if nums: 
        parts = nums[0].split('.')
        if len(parts) == 2: return f"PC{parts[0].zfill(3)}.{parts[1][:2]}"
    return None

def normalizar_pt(pt_raw):
    if not pt_raw: return None
    pt_str = str(pt_raw).upper().strip()
    match = re.search(r'(\d+)', pt_str)
    return match.group(1) if match else None

def normalizar_pt_busca(texto):
    if not texto: return ""
    match = re.search(r'(\d+)', str(texto))
    return str(int(match.group(1))) if match else ""

def normalizar_status(status_raw):
    if not status_raw: return 'A DEFINIR'
    s = status_raw.upper().strip()
    if any(x in s for x in ['CONCLU', 'FINALIZ', 'ENTREGUE', 'EMITIDO', 'OK', 'ENVIADO', 'PRONTO', 'RELATÓRIO FEITO']):
        return 'FINALIZADO'
    if any(x in s for x in ['ANDAMENTO', 'EXECU', 'INICIAR', 'TESTE', 'ENSAIO']):
        return 'EM ANDAMENTO'
    if 'AGUARDANDO' in s:
        return 'AGUARDANDO MATERIAL'
    return 'A DEFINIR'

def categorizar_material(material_raw):
    if not material_raw: return 'Outros'
    mat = str(material_raw).upper()
    if any(x in mat for x in ['BRITA', 'AREIA', 'PEDRA', 'BGS', 'RACH']): return 'Agregado'
    if any(x in mat for x in ['SOLO', 'TERRA', 'ATERRO']): return 'Solo'
    if any(x in mat for x in ['CONCRETO', 'CIMENTO', 'ARGAMASSA']): return 'Concreto'
    if any(x in mat for x in ['ASFALTO', 'CBUQ', 'CAP']): return 'Asfalto'
    return 'Outros'

# ======================================================================================
# 4. FUNÇÕES ESPECÍFICAS COMPASA (BUSCA INTELIGENTE POR PEDREIRA E PT)
# ======================================================================================

def verificar_existencia_pdf(pasta):
    try:
        if not os.path.exists(pasta): return False
        for f in os.listdir(pasta):
            if f.lower().endswith('.pdf'): return True
        return False
    except: return False

def buscar_pt_dentro_excel(pasta_busca, pt_alvo, celula_verificacao):
    if not os.path.exists(pasta_busca): return None, None
    
    pt_nums = re.findall(r'\d+', str(pt_alvo))
    pt_limpo = pt_nums[0] if pt_nums else str(pt_alvo)

    for f in os.listdir(pasta_busca):
        if f.endswith('.xlsm') or f.endswith('.xlsx'):
            if f.startswith('~$'): continue
            
            caminho_completo = os.path.join(pasta_busca, f)
            try:
                if pt_limpo in f:
                    df = pd.read_excel(caminho_completo, header=None, nrows=50, engine='openpyxl')
                    return caminho_completo, df

                xls = pd.ExcelFile(caminho_completo, engine='openpyxl')
                sheet_names = xls.sheet_names
                
                if celula_verificacao == "L9":
                    for sheet in sheet_names:
                        if "007" in sheet and "E1" in sheet:
                            df = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=40)
                            if len(df) > 8 and len(df.columns) > 11:
                                val = str(df.iloc[8, 11]).strip().upper()
                                if pt_limpo in val:
                                    return caminho_completo, df
                
                df = pd.read_excel(xls, sheet_name=0, header=None, nrows=50)
                mapa = {"I8": (7, 8), "E7": (6, 4), "E27": (26, 4), "L9": (8, 11)}
                if celula_verificacao in mapa:
                    r, c = mapa[celula_verificacao]
                    if len(df) > r and len(df.columns) > c:
                        val = str(df.iloc[r, c]).strip().upper()
                        if pt_limpo in val:
                            return caminho_completo, df
            except:
                continue
                
    return None, None

def extrair_detalhes_tecnicos(df, tipo_fase):
    dados = {}
    try:
        pass
    except: pass
    return dados

def verificar_fase_compasa_detalhada(tipo_fase, pt_alvo, pedreira, ano):
    retorno = {
        'STATUS': 'NAO_INICIADO',
        'ARQUIVO': None,
        'DETALHES': {},
        'TEM_PDF': False
    }

    if not pedreira: return retorno
    
    base = DIRETORIO_BASE_CAUQ
    sub = ""
    if tipo_fase == 'COMPOSICAO': sub = "003-COMPOSIÇÕES"
    elif tipo_fase == 'PIONEIRO': sub = "004-TRAÇOS PIONEIROS"
    elif tipo_fase == 'PROJETO': sub = "006-PROJETOS"
    
    caminho_base = os.path.join(base, sub)
    if not os.path.exists(caminho_base): return retorno

    pasta_ano = None
    for p in os.listdir(caminho_base):
        if str(ano) in p:
            pasta_ano = os.path.join(caminho_base, p)
            break
    if not pasta_ano: return retorno

    pasta_projeto = None
    melhor_score = 0
    nome_pedreira = str(pedreira).upper().replace("PEDREIRA", "").strip()
    
    try:
        for p in os.listdir(pasta_ano):
            path = os.path.join(pasta_ano, p)
            if not os.path.isdir(path): continue
            
            score = fuzz.partial_ratio(nome_pedreira, p.upper())
            if score > 80 and score > melhor_score:
                melhor_score = score
                pasta_projeto = path
            
            pt_nums = re.findall(r'\d+', str(pt_alvo))
            pt_clean = pt_nums[0] if pt_nums else ""
            
            if tipo_fase == 'PROJETO' and pt_clean:
                 if p.startswith(pt_clean) or f" {pt_clean} " in p:
                     pasta_projeto = path
                     break 

    except: return retorno

    if not pasta_projeto: return retorno
    
    dir_busca = pasta_projeto
    if tipo_fase == 'PROJETO':
        sub_ent = os.path.join(pasta_projeto, "005-ENTREGA")
        if os.path.exists(sub_ent): dir_busca = sub_ent

    caminho_excel, df_lido = buscar_pt_dentro_excel(dir_busca, pt_alvo, tipo_fase)
    
    if caminho_excel:
        retorno['ARQUIVO'] = os.path.basename(caminho_excel)
        retorno['TEM_PDF'] = verificar_existencia_pdf(dir_busca)
        retorno['STATUS'] = 'OK' if retorno['TEM_PDF'] else 'ANDAMENTO'
    
    return retorno

@st.cache_data(ttl=300)
def rastrear_projetos_compasa_completo(df_compasa):
    res = []
    processed_pts = set()

    for _, row in df_compasa.iterrows():
        pt = row.get('NUMERO_PROPOSTA')
        
        if pt in processed_pts: continue
        
        ped = row.get('PEDREIRA')
        ano = row.get('ANO')
        
        mat = str(row.get('MATERIAL', '')).upper()
        if 'CAUQ' in mat or 'PROJETO' in mat or ped:
            status_comp = verificar_fase_compasa_detalhada('COMPOSICAO', pt, ped, ano)
            status_pion = verificar_fase_compasa_detalhada('PIONEIRO', pt, ped, ano)
            status_proj = verificar_fase_compasa_detalhada('PROJETO', pt, ped, ano)
            
            if (status_comp['STATUS'] != 'NAO_INICIADO' or 
                status_pion['STATUS'] != 'NAO_INICIADO' or 
                status_proj['STATUS'] != 'NAO_INICIADO'):
                
                res.append({
                    'PT': pt, 'PEDREIRA': ped, 'STATUS_GERAL': row.get('STATUS'),
                    'DADOS_COMPOSICAO': status_comp,
                    'DADOS_PIONEIRO': status_pion,
                    'DADOS_PROJETO': status_proj
                })
                processed_pts.add(pt)
                
    return pd.DataFrame(res)

# ======================================================================================
# 5. SINCRONIZAÇÃO
# ======================================================================================

def get_lista_cc_from_excel():
    cc_names = set()
    path = FILES_CONFIG['certificados_2025']['local_path']
    if os.path.exists(path):
        try:
            df = pd.read_excel(path, sheet_name='CLIENTES CAD', header=None, skiprows=1)
            for i, row in df.iterrows():
                nome = str(row.iloc[10]).strip().upper()
                contrato = str(row.iloc[16]).strip()
                if nome and contrato and contrato.upper() not in ['NAN', 'NONE', '']:
                    cc_names.add(nome)
        except: pass
    return cc_names

def extrair_datas_fas():
    return {}

def carregar_form044():
    return {}

def sync_propostas():
    pass

def sync_certificados_067():
    """Sincroniza dados do FORM 067 (Certificados) - INDEPENDENTE do FORM 022 A"""
    todos = []
    for ano in ['2026', '2025']:
        path = FILES_CONFIG[f'certificados_{ano}']['local_path']
        if not os.path.exists(path): 
            logger.warning(f"Arquivo não encontrado: {path}")
            continue
        try:
            df = pd.read_excel(path, header=None, engine='openpyxl')
            logger.info(f"Lendo FORM 067 de {ano}: {len(df)} linhas")
            
            for i in range(8, len(df)):
                try:
                    row = df.iloc[i]
                    pt = str(row.iloc[5]).strip()
                    if len(pt) < 2 or pt.upper() in ['NAN', 'NONE', '']: continue
                    
                    # Extrair data do certificado (coluna 15 = DATA DE EMISSÃO)
                    data_cert = pd.to_datetime(row.iloc[15], errors='coerce') if pd.notna(row.iloc[15]) else None
                    
                    # Extrair quantidade
                    qtd = 1
                    try:
                        qtd_raw = row.iloc[4]
                        if pd.notna(qtd_raw):
                            qtd = float(qtd_raw) if float(qtd_raw) > 0 else 1
                    except: pass
                    
                    # Extrair cliente (coluna 1)
                    cliente = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    if cliente.upper() in ['NAN', 'NONE', 'CLIENTE', '']: 
                        cliente = 'NÃO INFORMADO'
                    
                    # Extrair norma (coluna 3)
                    norma = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
                    
                    # Extrair acreditado (coluna 6 ou 7)
                    acreditado = 'NÃO'
                    try:
                        acred_raw = str(row.iloc[6]).strip().upper()
                        if acred_raw in ['SIM', 'S', 'YES', 'Y', 'X']:
                            acreditado = 'SIM'
                    except: pass
                    
                    # Verificar se ensaio foi concluído
                    ensaio_concluido = 1 if pd.notna(row.iloc[13]) else 0
                    
                    todos.append({
                        'PT': pt,
                        'PT_NORMALIZADO': normalizar_pt(pt),
                        'CLIENTE': cliente,
                        'ENSAIO': str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else '',
                        'NORMA': norma,
                        'QUANTIDADE': qtd,
                        'ACREDITADO': acreditado,
                        'DATA': data_cert.strftime('%Y-%m-%d') if data_cert else None,
                        'ANO': ano,
                        'ENSAIO_CONCLUIDO': ensaio_concluido,
                        'RELATORIO_VINCULADO': str(row.iloc[10]).strip() if pd.notna(row.iloc[10]) else '',
                        'NUM_CERTIFICADO': str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    })
                except Exception as e: 
                    continue
                    
            logger.info(f"FORM 067 {ano}: {len([t for t in todos if t['ANO']==ano])} registros válidos")
        except Exception as e:
            logger.error(f"Erro ao ler FORM 067 {ano}: {e}")
            
    if todos:
        df_final = pd.DataFrame(todos)
        df_final = df_final[df_final['ENSAIO'].str.len() > 1]  # Remover ensaios vazios
        logger.info(f"Total certificados a salvar: {len(df_final)}")
        
        with bridge.get_db_conn() as conn:
            df_final.to_sql('certificados_067', conn, if_exists='replace', index=False)
        logger.info("Tabela certificados_067 atualizada com sucesso")

def sync_recebimento():
    todos_dados = []
    keys = [k for k in FILES_CONFIG if FILES_CONFIG[k]['tipo'] == 'recebimento']
    cc_list = get_lista_cc_from_excel()
    
    for key in keys:
        source = bridge.get_file_content(key)
        if not source: continue
        try:
            df = pd.read_excel(source, header=None, engine='openpyxl')
            ano = FILES_CONFIG[key]['ano']
            for i in range(6, len(df)):
                try:
                    row = df.iloc[i]
                    empresa = str(row.iloc[1]).strip()
                    if len(empresa)<3 or empresa.upper() in ['EMPRESA','CLIENTE']: continue
                    
                    dt_rec = pd.to_datetime(row.iloc[2], errors='coerce')
                    
                    pt_col_a = str(row.iloc[0]).strip()
                    prop_raw = str(row.iloc[13]).strip()
                    status_raw = str(row.iloc[17]).strip()
                    
                    is_cc = empresa.upper() in cc_list or 'COMPASA' in empresa.upper() or 'EPR' in empresa.upper()
                    tipo = 'CC' if is_cc else 'PC'
                    num_prop = pt_col_a if tipo == 'CC' else prop_raw
                    if 'COMPASA' in empresa.upper(): empresa = 'COMPASA DO BRASIL'
                    
                    status = normalizar_status(status_raw)
                    if status == 'FINALIZADO': tem_mat = True
                    else:
                        tem_mat = True if (pd.notna(dt_rec) or tipo=='CC') else False
                        status = 'EM ANDAMENTO' if tem_mat else 'AGUARDANDO RECEBIMENTO'
                    
                    todos_dados.append({
                        'NUMERO_PROPOSTA': num_prop, 'CLIENTE': empresa,
                        'DATA_RECEBIMENTO': dt_rec, 'STATUS': status,
                        'TIPO_PROPOSTA': tipo, 'TEM_MATERIAL': tem_mat,
                        'MATERIAL': str(row.iloc[3]), 'PEDREIRA': str(row.iloc[4]),
                        'ANO': ano, 'PT_COLUNA_A': pt_col_a
                    })
                except: continue
        except: continue
        
    if todos_dados:
        df_final = pd.DataFrame(todos_dados)
        for c in ['DATA_RECEBIMENTO']:
             df_final[c] = df_final[c].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        
        df_final = df_final.sort_values(['DATA_RECEBIMENTO', 'STATUS'], ascending=[False, True])
        df_final = df_final.drop_duplicates(subset=['NUMERO_PROPOSTA', 'PT_COLUNA_A'], keep='first')
        
        with bridge.get_db_conn() as conn:
            df_final.to_sql('recebimentos', conn, if_exists='replace', index=False)

def sync_all_data():
    """Sincroniza todos os dados - limpa cache e recarrega do Excel"""
    try:
        st.cache_data.clear()
    except: pass
    
    # Deletar banco antigo para forçar recriação
    import os
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            logger.info(f"Banco {DB_NAME} removido para recriação")
        except: pass
    
    # Reinicializar banco
    bridge.init_db()
    
    # Sincronizar dados frescos
    sync_recebimento()
    sync_certificados_067()
    sync_propostas()
    logger.info("Sincronização completa - todos os dados recarregados")

def carregar_dados_consolidados_sql():
    with bridge.get_db_conn() as conn:
        try: return pd.read_sql_query("SELECT * FROM recebimentos", conn)
        except: return pd.DataFrame()

def carregar_dados_certificados_sql():
    """Carrega dados APENAS da tabela certificados_067 (FORM 067) - SEM FORM 022 A"""
    with bridge.get_db_conn() as conn:
        try: 
            df = pd.read_sql_query("SELECT * FROM certificados_067", conn)
            logger.info(f"Certificados carregados do SQLite: {len(df)} registros")
            return df
        except Exception as e:
            logger.error(f"Erro ao carregar certificados: {e}")
            return pd.DataFrame()

def carregar_dados_combinados():
    """Carrega dados de certificados (FORM 067) - DESVINCULADO DO FORM 022 A"""
    return carregar_dados_certificados_sql()

def get_opcoes_filtro(df, coluna):
    """Retorna opções únicas de uma coluna para filtros"""
    if df is None or df.empty or coluna not in df.columns:
        return []
    try:
        valores = df[coluna].dropna().unique().tolist()
        return sorted([str(v) for v in valores if v and str(v).strip()])
    except:
        return []

def get_unique_values_safe(df, coluna):
    """Retorna valores únicos de forma segura"""
    return get_opcoes_filtro(df, coluna)

def get_estatisticas_dashboard(df):
    """Retorna estatísticas para o dashboard"""
    if df is None or df.empty:
        return {
            'total': 0,
            'finalizados': 0,
            'em_andamento': 0,
            'aguardando': 0
        }
    try:
        total = len(df)
        finalizados = len(df[df['STATUS'] == 'FINALIZADO']) if 'STATUS' in df.columns else 0
        em_andamento = len(df[df['STATUS'] == 'EM ANDAMENTO']) if 'STATUS' in df.columns else 0
        aguardando = len(df[df['STATUS'].str.contains('AGUARDANDO', na=False)]) if 'STATUS' in df.columns else 0
        return {
            'total': total,
            'finalizados': finalizados,
            'em_andamento': em_andamento,
            'aguardando': aguardando
        }
    except:
        return {'total': 0, 'finalizados': 0, 'em_andamento': 0, 'aguardando': 0}

def formatar_protocolo(val):
    """Formata número de protocolo"""
    if not val: return ""
    return str(val).strip()

def exportar_dados_csv(df, n): return df.to_csv(index=False).encode('utf-8')
def formatar_numero(val): return str(val)
def formatar_data(val): return str(val)
def extrair_dados_cliente_word(a,b): return "" 

if __name__ == "__main__": pass
