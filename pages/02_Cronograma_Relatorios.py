import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import sys
import os
from thefuzz import fuzz

# Adicionar o diretório pai ao path para importar styles
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar estilos globais padronizados
from styles import aplicar_estilos, renderizar_sidebar, renderizar_footer, CORES, PLOTLY_LAYOUT, CORES_GRAFICOS
from page_auth import proteger_pagina

# Importar utilitários específicos para certificados
from utils_certificados import (
    sync_all_data,
    carregar_dados_consolidados_sql,
    exportar_dados_csv,
    rastrear_projetos_compasa_completo,
    rastrear_projetos_externos,
    carregar_dados_epr_raw,
    consolidar_fas_totais,
    gerar_quantitativos_empresas,
    carregar_empresa_finalidade_raw,
    escanear_todos_projetos,
    TIPOS_PROJETO_CONFIG,
)

# ======================================================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILO
# ======================================================================================
st.set_page_config(
    page_title="Cronograma | Afirma E-vias",
    page_icon="",
    layout="wide",
    initial_sidebar_state="auto"
)

# Aplicar estilos globais padronizados
aplicar_estilos()
proteger_pagina("Cronograma de Ensaios")

# ======================================================================================
# CORES CORPORATIVAS ADICIONAIS (USADAS EM PAINÉIS ESPECIAIS)
# ======================================================================================
COR_FUNDO_PRINCIPAL = "#00233B"
COR_FUNDO_CARD = "#00121F"
COR_TEXTO_TITULO = "#EFEBDC"
COR_TEXTO_CORPO = "#F2F1EF"
COR_DESTAQUE_VERDE = "#BFCF99"
COR_DESTAQUE_BORDAS = "#566E3D"

# ======================================================================================
# CAMINHO DO ARQUIVO EXCEL COM CLIENTES CADASTRADOS
# ======================================================================================
CAMINHO_FORM_067 = r"G:\.shortcut-targets-by-id\1NUJ7pNAqedohSrLjiwFErFrtVqVZkrjk\006 - Lab. Central\1.0 CONTROLES\00.CERTIFICADOS\FORM 067 - REV 00 - Controle de Certificados(2025).xlsm"

# ======================================================================================
# FUNÇÃO PARA CARREGAR CLIENTES COM CONTRATO CONTÍNUO (CC)
# ======================================================================================
@st.cache_data(ttl=3600)  # Cache por 1 hora
def carregar_clientes_contrato_continuo():
    """
    Carrega a lista de clientes com Contrato Contínuo (CC) do arquivo Excel.
    Aba: CLIENTES CAD
    Coluna K (10): Nome do cliente
    Coluna Q (16): Contrato (se contém 'CC' = Contrato Contínuo)
    
    Returns:
        set: Conjunto de nomes de clientes com contrato contínuo
    """
    try:
        df = pd.read_excel(
            CAMINHO_FORM_067,
            sheet_name='CLIENTES CAD',
            header=None,
            skiprows=1  # Pular cabeçalho
        )
        
        # Coluna K (10) = Nome do Cliente, Coluna Q (16) = Contrato
        df_clientes = df.iloc[:, [10, 16]].copy()
        df_clientes.columns = ['CLIENTE', 'CONTRATO']
        
        # Filtrar clientes com contrato contínuo (CC)
        # CC pode aparecer como "CC", "CC CONSULTORIA", etc.
        mask_cc = df_clientes['CONTRATO'].astype(str).str.upper().str.startswith('CC')
        clientes_cc = set(df_clientes[mask_cc]['CLIENTE'].dropna().str.strip().str.upper().tolist())
        
        return clientes_cc
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar clientes CC: {e}")
        return set()

def verificar_cliente_cc(nome_cliente, clientes_cc):
    """
    Verifica se um cliente está na lista de Contratos Contínuos.
    Usa fuzzy matching para maior flexibilidade.
    """
    if not nome_cliente or pd.isna(nome_cliente):
        return False
    
    nome_upper = str(nome_cliente).upper().strip()
    
    for cliente_cc in clientes_cc:
        # Matching exato ou fuzzy (90% similaridade)
        if nome_upper == cliente_cc or fuzz.ratio(nome_upper, cliente_cc) >= 90:
            return True
    
    return False

# ======================================================================================
# FUNÇÕES AUXILIARES PARA DASHBOARD CC
# ======================================================================================

def calcular_similaridade(texto1, texto2):
    """Calcula similaridade entre dois textos usando fuzz.ratio"""
    if not texto1 or not texto2:
        return 0
    return fuzz.ratio(str(texto1).upper().strip(), str(texto2).upper().strip())

def deve_ignorar_pedreira(texto):
    """Verifica se o texto deve ser ignorado (PEDREIRA e similares com 80%)"""
    if not texto or pd.isna(texto):
        return False
    texto_upper = str(texto).upper().strip()
    termos_ignorar = ['PEDREIRA']
    for termo in termos_ignorar:
        if termo in texto_upper or fuzz.ratio(texto_upper, termo) >= 80:
            return True
    return False

def agrupar_por_similaridade(lista_textos, threshold=70):
    """
    Agrupa textos similares usando threshold de similaridade.
    Retorna dict {grupo_representante: [textos_similares]}
    """
    if not lista_textos:
        return {}
    
    grupos = {}
    textos_processados = set()
    
    for texto in lista_textos:
        if texto in textos_processados or pd.isna(texto):
            continue
        
        texto_upper = str(texto).upper().strip()
        grupo_encontrado = None
        
        # Verificar se pertence a um grupo existente
        for representante in grupos.keys():
            if fuzz.ratio(texto_upper, representante) >= threshold:
                grupo_encontrado = representante
                break
        
        if grupo_encontrado:
            grupos[grupo_encontrado].append(texto)
        else:
            grupos[texto_upper] = [texto]
        
        textos_processados.add(texto)
    
    return grupos

def identificar_tipo_cliente_cc(nome_cliente):
    """
    Identifica o tipo de tratamento para cliente CC.
    Retorna: 'EPR', 'STRATA', 'COMPASA' ou 'PADRAO'
    """
    if not nome_cliente:
        return 'PADRAO'
    
    nome_upper = str(nome_cliente).upper().strip()
    
    if 'EPR LITORAL PIONEIRO' in nome_upper or fuzz.ratio(nome_upper, 'EPR LITORAL PIONEIRO S.A.') >= 85:
        return 'EPR'
    elif 'STRATA ENGENHARIA' in nome_upper or fuzz.ratio(nome_upper, 'STRATA ENGENHARIA LTDA') >= 85:
        return 'STRATA'
    elif 'COMPASA' in nome_upper or fuzz.ratio(nome_upper, 'COMPASA DO BRASIL') >= 80:
        return 'COMPASA'
    else:
        return 'PADRAO'

def criar_quadro_quantitativo_cc(df_cliente, nome_cliente, tipo_cliente):
    """
    Cria quadro quantitativo específico para cliente CC.
    
    Args:
        df_cliente: DataFrame filtrado do cliente
        nome_cliente: Nome do cliente
        tipo_cliente: 'EPR', 'STRATA', 'COMPASA' ou 'PADRAO'
    
    Returns:
        dict com dados para exibição
    """
    resultado = {
        'cliente': nome_cliente,
        'tipo': tipo_cliente,
        'total': len(df_cliente),
        'materiais': {},
        'subgrupos': {}
    }
    
    if tipo_cliente in ['EPR', 'STRATA', 'PADRAO']:
        # Agrupar por MATERIAL (coluna E do FORM 22A)
        if 'MATERIAL' in df_cliente.columns:
            materiais = df_cliente['MATERIAL'].dropna().value_counts()
            # Top 3 materiais
            top_materiais = materiais.head(3)
            resultado['materiais'] = top_materiais.to_dict()
            resultado['outros'] = materiais[3:].sum() if len(materiais) > 3 else 0
    
    elif tipo_cliente == 'COMPASA':
        # Agrupar por LOCAL (coluna M do FORM 22A)
        if 'LOCAL' in df_cliente.columns:
            # Filtrar PEDREIRA
            df_filtrado = df_cliente[~df_cliente['MATERIAL'].apply(deve_ignorar_pedreira)]
            
            # Sub-agrupar por PT
            if 'NUMERO_PROPOSTA' in df_filtrado.columns:
                pts = df_filtrado['NUMERO_PROPOSTA'].dropna().unique()
                
                for pt in pts:
                    df_pt = df_filtrado[df_filtrado['NUMERO_PROPOSTA'] == pt]
                    
                    # Agrupar materiais por similaridade (70%)
                    if 'MATERIAL' in df_pt.columns:
                        materiais_lista = df_pt['MATERIAL'].dropna().tolist()
                        grupos_similares = agrupar_por_similaridade(materiais_lista, threshold=70)
                        
                        resultado['subgrupos'][str(pt)] = {
                            'total': len(df_pt),
                            'grupos_material': {k: len(v) for k, v in grupos_similares.items()}
                        }
            
            # Local como agrupador principal
            locais = df_filtrado['LOCAL'].dropna().value_counts()
            resultado['locais'] = locais.to_dict()
    
    return resultado

# ======================================================================================
# CORES DE STATUS PARA O CRONOGRAMA (Usando cores globais + status específicos)
# ======================================================================================
CORES_STATUS = {
    'finalizado': CORES['sucesso'],
    'em_andamento': CORES['info'],
    'aguardando': CORES['alerta'],
    'urgente': CORES['erro'],
    'vencido': CORES['vencido'],
}

# ======================================================================================
# FUNÇÕES AUXILIARES DE LAYOUT
# ======================================================================================

def render_control_buttons(key_suffix):
    """Renderiza a linha de botões padronizada"""
    col_btn1, col_btn2, col_btn3, col_spacer = st.columns([1, 1, 1, 4])
    with col_btn1:
        btn_exp = st.button("📊 EXPORTAR", key=f"btn_exp_{key_suffix}")
    with col_btn2:
        btn_att = st.button("🔄 ATUALIZAR", key=f"btn_att_{key_suffix}")
    with col_btn3:
        horizontal = st.checkbox("══ HORIZONTAL", value=True, key=f"check_{key_suffix}")
    return btn_exp, btn_att, horizontal

# ======================================================================================
# FUNÇÕES AUXILIARES
# ======================================================================================

def calcular_prazo_entrega(data_aceite, prazo_texto):
    """Calcula a data de entrega baseada na data de aceite e prazo em dias"""
    try:
        if pd.isna(data_aceite) or not prazo_texto:
            return None
        
        # Extrair número de dias do texto (ex: "25 dias úteis")
        import re
        numeros = re.findall(r'\d+', str(prazo_texto))
        if not numeros:
            return None
        
        dias = int(numeros[0])
        
        # Converter data de aceite
        data_aceite_dt = pd.to_datetime(data_aceite, format='%d/%m/%Y', errors='coerce')
        if pd.isna(data_aceite_dt):
            return None
        
        # Adicionar dias úteis, pulando fins de semana
        data_entrega = data_aceite_dt
        dias_adicionados = 0
        while dias_adicionados < dias:
            data_entrega += timedelta(days=1)
            # weekday() -> Segunda-feira = 0, Domingo = 6
            if data_entrega.weekday() < 5: # Ignora Sábado (5) e Domingo (6)
                dias_adicionados += 1
        
        return data_entrega.strftime('%d/%m/%Y')
        
    except Exception:
        return None

def obter_cor_status(status):
    """Retorna a cor baseada no status usando paleta corporativa"""
    cores = {
        'FINALIZADO': '#566E3D',           # Verde oliva
        'EM EXECUÇÃO': '#00233B',          # Azul escuro
        'EM ANDAMENTO': '#00233B',         # Azul escuro
        'AGUARDANDO MATERIAL': '#BFCF99',  # Verde claro
        'AGUARDANDO APROVAÇÃO': '#dc2626', # Vermelho
        'A INICIAR': '#566E3D',            # Verde oliva
        'A DEFINIR': '#f59e0b',            # Amarelo
        'CANCELADO': '#7f1d1d',            # Vermelho escuro
        'VENCIDO': '#dc2626',              # Vermelho
        'URGENTE': '#f59e0b',              # Amarelo
        'NO PRAZO': '#566E3D',             # Verde oliva
        'SEM PRAZO': '#BFCF99',            # Verde claro
    }
    return cores.get(status, '#BFCF99')

def criar_timeline_gantt(df):
    """Cria um gráfico de Gantt para visualização do teste 01"""
    if df.empty:
        return None
    
    # Preparar dados para o Gantt
    timeline_data = []
    
    for _, row in df.iterrows():
        # Data de início (aceite da proposta ou recebimento do material)
        data_inicio = row.get('RECEBIMENTO_MATERIAL') or row.get('ACEITE_PROPOSTA')
        
        if data_inicio:
            # Data de término (entrega ou prazo calculado)
            data_fim = row.get('DATA_ENTREGA')
            
            if not data_fim and row.get('PRAZO_ENTREGA_TEXTO'):
                data_fim = calcular_prazo_entrega(data_inicio, row['PRAZO_ENTREGA_TEXTO'])
            
            if data_fim:
                timeline_data.append({
                    'Relatório': row.get('NUMERO_RELATORIO', 'N/A'),
                    'Cliente': row.get('CLIENTE', 'N/A'),
                    'Ensaio': row.get('ENSAIO', 'N/A'),
                    'Status': row.get('STATUS', 'N/A'),
                    'Início': pd.to_datetime(data_inicio, format='%d/%m/%Y', errors='coerce'),
                    'Fim': pd.to_datetime(data_fim, format='%d/%m/%Y', errors='coerce'),
                    'Cor': obter_cor_status(row.get('STATUS', ''))
                })
    
    if not timeline_data:
        return None
    
    timeline_df = pd.DataFrame(timeline_data)
    timeline_df = timeline_df.dropna(subset=['Início', 'Fim'])
    
    # Criar gráfico de Gantt
    fig = px.timeline(
        timeline_df,
        x_start="Início",
        x_end="Fim",
        y="Relatório",
        color="Cor",
        title="📅 TESTEs",
        hover_data=["Cliente", "Ensaio", "Status"],
        color_discrete_map={
            'FINALIZADO': '#16a34a',
            'EM EXECUÇÃO': '#3b82f6',
            'EM ANDAMENTO': '#f59e0b',
            'AGUARDANDO MATERIAL': '#6b7280',
            'AGUARDANDO APROVAÇÃO': '#dc2626'
        }
    )
    
    fig.update_layout(
        height=max(400, len(timeline_df) * 40),
        font=dict(family="Poppins, sans-serif", color="#ffffff", size=12),
        plot_bgcolor='rgba(0, 35, 59, 0.95)',
        paper_bgcolor='rgba(0, 35, 59, 0.95)',
        showlegend=True,
        legend=dict(
            bgcolor='rgba(0, 35, 59, 0.95)',
            bordercolor='#566E3D',
            font=dict(color='#FFFFFF', size=12)
        ),
        xaxis=dict(
            gridcolor='#566E3D',
            tickcolor='#BFCF99',
            tickfont=dict(color='#FFFFFF', size=10)
        ),
        yaxis=dict(
            gridcolor='#566E3D',
            tickcolor='#BFCF99',
            tickfont=dict(color='#FFFFFF', size=10)
        )
    )
    
    return fig

# ======================================================================================
# UNIDADE_PADRÃO_ATIVIDADES — FUNÇÕES CENTRALIZADAS
# ======================================================================================

def calcular_unidade_padrao(
    df_projetos_externos=None,
    df_fas=None,
    dict_cc_ensaios=None,
    pts_cbb=0,
    pts_asfaltec=0,
):
    """
    Retorna dicionário consolidado de Unidade_Padrão_atividades.

    Chaves esperadas:
        'PROJETOS_EXTERNOS', 'FAS_ENSAIOS', 'CC_<CLIENTE>', 'CBB_ASFALTOS', 'ASFALTEC', '__TOTAL__'
    Cada valor: {'unidades': int, 'label': str, 'descricao': str}
    """
    result = {}

    # Projetos Externos — cada projeto = 1
    n_ext = len(df_projetos_externos) if df_projetos_externos is not None and not df_projetos_externos.empty else 0
    result['PROJETOS_EXTERNOS'] = {
        'unidades': n_ext,
        'label': 'Projetos Externos',
        'descricao': 'Cada projeto na rede = 1 unidade',
    }

    # FAS / Ensaios — cada linha (ensaio) = 1 (ou soma da coluna QUANTIDADE)
    n_fas = 0
    if df_fas is not None and not df_fas.empty:
        if 'QUANTIDADE' in df_fas.columns:
            n_fas = int(pd.to_numeric(df_fas['QUANTIDADE'], errors='coerce').fillna(1).sum())
        else:
            n_fas = len(df_fas)
    result['FAS_ENSAIOS'] = {
        'unidades': n_fas,
        'label': 'FAS — Ensaios',
        'descricao': 'Cada ensaio de cada FAS = 1 unidade',
    }

    # Clientes CC — cada ensaio (Col H/QUANTIDADE) = 1
    cc_map = dict_cc_ensaios or {}
    for cliente_label, qtd in cc_map.items():
        chave = 'CC_' + cliente_label.upper().replace(' ', '_')[:20]
        result[chave] = {
            'unidades': int(qtd),
            'label': cliente_label,
            'descricao': 'CC — cada ensaio (Col H FORM 022A) = 1 unidade',
        }

    # CBB Asfaltos — cada PT distinto = 1
    result['CBB_ASFALTOS'] = {
        'unidades': int(pts_cbb),
        'label': 'CBB Asfaltos',
        'descricao': 'Cada PT distinto = 1 unidade',
    }

    # Asfaltec — cada PT distinto = 1
    result['ASFALTEC'] = {
        'unidades': int(pts_asfaltec),
        'label': 'Asfaltec',
        'descricao': 'Cada PT distinto = 1 unidade',
    }

    # Total geral
    total_geral = sum(v['unidades'] for k, v in result.items())
    result['__TOTAL__'] = {
        'unidades': total_geral,
        'label': 'TOTAL GERAL',
        'descricao': 'Soma de todas as unidades padronizadas',
    }

    return result


def render_banner_unidade_padrao(upa_dict, chave=None, cor_borda='#BFCF99', cor_texto='#BFCF99'):
    """Renderiza banner padrão de Unidade_Padrão_atividades para uma seção."""
    if not upa_dict:
        return
    entry = upa_dict.get(chave) if chave and chave in upa_dict else upa_dict.get('__TOTAL__', {})
    if not entry:
        return
    st.markdown(
        f'<div style="background:#0f2a3f;border-left:4px solid {cor_borda};'
        f'padding:8px 14px;border-radius:4px;margin:4px 0 10px 0;">'
        f'<span style="color:{cor_texto};font-weight:bold;font-size:0.95rem;">'
        f'<span style="color:#adb5bd;font-size:0.82rem;margin-left:12px;">'
        f'{entry.get("descricao","")} | '
        f'<b style="color:{cor_texto}">{entry.get("unidades",0)}</b> unidades'
        f'</span></div>',
        unsafe_allow_html=True
    )


def _soma_quantidade(df_subset) -> int:
    """Soma COL H (QUANTIDADE); fallback para contagem de registros."""
    if df_subset is None or df_subset.empty:
        return 0
    if 'QUANTIDADE' in df_subset.columns:
        return int(pd.to_numeric(df_subset['QUANTIDADE'], errors='coerce').fillna(0).sum())
    return len(df_subset)


def render_banner_unidade_padrao_local(unidades: int, descricao: str, cor_borda='#BFCF99', cor_texto='#BFCF99'):
    """Banner de Unidade_Padrão_atividades baseado em subconjunto filtrado."""
    st.markdown(
        f'<div style="background:#0f2a3f;border-left:4px solid {cor_borda};'
        f'padding:8px 14px;border-radius:4px;margin:4px 0 10px 0;">'
        f'<span style="color:{cor_texto};font-weight:bold;font-size:0.95rem;">'
        f'<span style="color:#adb5bd;font-size:0.82rem;margin-left:12px;">'
        f'{descricao} | '
        f'<b style="color:{cor_texto}">{unidades}</b> unidades'
        f'</span></div>',
        unsafe_allow_html=True
    )

# -------------------------------------------------------------------------
# FUNÇÃO REESCRITA COM ALTURA DINÂMICA
# -------------------------------------------------------------------------
def criar_timeline_avancada(df):
    """Cria timeline interativa avançada com Plotly e altura dinâmica."""
    if df.empty:
        return go.Figure()
    
    colunas_data = ['DATA_ENTREGA', 'DATA_ACEITE', 'DATA_ENTREGA_RELATORIO', 'PRAZO_ENTREGA']
    coluna_data = None
    
    for col in colunas_data:
        if col in df.columns:
            coluna_data = col
            break
    
    if not coluna_data:
        return go.Figure()
    
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    df = df.dropna(subset=[coluna_data])
    
    if df.empty:
        return go.Figure()
    
    df = df.sort_values(coluna_data)
    
    cores_status = {
        'FINALIZADO': '#16a34a', 'EM ANDAMENTO': '#3b82f6', 'EM EXECUÇÃO': '#3b82f6',
        'AGUARDANDO MATERIAL': '#6b7280', 'AGUARDANDO APROVAÇÃO': '#dc2626',
        'A INICIAR': '#8b5cf6', 'A DEFINIR': '#f97316', 'CANCELADO': '#ef4444',
        'SEM STATUS': '#9ca3af'
    }
    
    fig = go.Figure()
    
    # Lógica para contar linhas necessárias no eixo Y
    qtd_linhas_y = 0
    
    if 'TIPO' in df.columns:
        tipos = df['TIPO'].unique()
        for tipo in tipos:
            df_tipo = df[df['TIPO'] == tipo]
            statuses = df_tipo['STATUS'].unique()
            qtd_linhas_y += len(statuses)
            
            for status in statuses:
                df_status = df_tipo[df_tipo['STATUS'] == status]
                if not df_status.empty:
                    fig.add_trace(go.Scatter(
                        x=df_status[coluna_data],
                        y=[f"{tipo} - {status}"] * len(df_status),
                        mode='markers+lines',
                        name=f"{tipo} - {status}",
                        marker=dict(size=14, color=cores_status.get(status, '#6b7280'), line=dict(width=2, color='white'), symbol='circle'),
                        line=dict(width=3, color=cores_status.get(status, '#6b7280')),
                        text=df_status.apply(lambda x: f"🏢 {x.get('CLIENTE', 'N/A')}<br>📄 {x.get('NUMERO_PROPOSTA', 'N/A')}<br>📅 {x[coluna_data].strftime('%d/%m/%Y')}", axis=1),
                        hovertemplate='<b>%{text}</b><extra></extra>',
                        hoverlabel=dict(
            bgcolor="rgba(0, 35, 59, 0.98)",
            font_size=12,
            font_family="Poppins",
            font_color="#FFFFFF",
            bordercolor="#566E3D"
        )
                    ))
    else:
        statuses = df['STATUS'].unique()
        qtd_linhas_y = len(statuses)
        for status in statuses:
            df_status = df[df['STATUS'] == status]
            fig.add_trace(go.Scatter(
                x=df_status[coluna_data],
                y=[f"{status}"] * len(df_status),
                mode='markers+lines',
                name=status,
                marker=dict(size=14, color=cores_status.get(status, '#6b7280'), line=dict(width=2, color='white')),
                line=dict(width=3, color=cores_status.get(status, '#6b7280')),
                text=df_status.apply(lambda x: f"🏢 {x.get('CLIENTE', 'N/A')}<br>📄 {x.get('NUMERO_PROPOSTA', 'N/A')}<br>📅 {x[coluna_data].strftime('%d/%m/%Y')}", axis=1),
                hovertemplate='<b>%{text}</b><extra></extra>',
                hoverlabel=dict(
            bgcolor="rgba(0, 35, 59, 0.98)",
            font_size=12,
            font_family="Poppins",
            font_color="#FFFFFF",
            bordercolor="#566E3D"
        )
            ))
    
    # --- CÁLCULO DINÂMICO DE ALTURA ---
    # 50px por linha de categoria + 200px de base
    altura_dinamica = 200 + (qtd_linhas_y * 50)
    altura_final = max(400, altura_dinamica) # Mínimo de 400px
    # ----------------------------------

    fig.update_layout(
        title={'text': f"📈 TESTE {coluna_data}", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 24, 'color': 'white'}},
        xaxis_title="Data",
        yaxis_title="Tipo e Status",
        
        # APLICAÇÃO DA ALTURA
        height=altura_final,
        
        plot_bgcolor='rgba(0, 35, 59, 0.95)',
        paper_bgcolor='rgba(0, 35, 59, 0.95)',
        font=dict(color='#FFFFFF', size=12, family='Poppins'),
        hovermode='closest',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='#FFFFFF', size=10),
            bgcolor='rgba(0, 35, 59, 0.95)',
            bordercolor='#566E3D'
        ),
        margin=dict(l=20, r=20, t=80, b=20)
    )
    
    fig.update_xaxes(gridcolor='#4a5568', tickcolor='#4a5568', tickfont=dict(color='white', size=11))
    fig.update_yaxes(gridcolor='#4a5568', tickcolor='#4a5568', tickfont=dict(color='white', size=11))
    
    return fig

# -------------------------------------------------------------------------
# FUNÇÃO REESCRITA COM ALTURA DINÂMICA
# -------------------------------------------------------------------------
def criar_gantt_avancado(df):
    """
    Cria gráfico de Gantt avançado com Plotly e altura dinâmica.
    AGRUPADO APENAS POR CLIENTE para reduzir dados e melhorar visualização.
    """
    if df.empty:
        return go.Figure()
    
    colunas_data = ['DATA_ENTREGA', 'DATA_ACEITE', 'DATA_ENTREGA_RELATORIO', 'PRAZO_ENTREGA']
    coluna_data = None
    
    for col in colunas_data:
        if col in df.columns:
            coluna_data = col
            break
    
    if not coluna_data:
        return go.Figure()
    
    df = df.copy()
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    df = df.dropna(subset=[coluna_data])
    
    if df.empty:
        return go.Figure()
    
    # Criar coluna de agrupamento: CLIENTE
    if 'CLIENTE' not in df.columns:
        df['CLIENTE'] = 'Sem Cliente'
    
    # Agrupar dados por CLIENTE (apenas cliente, sem subdivisão)
    clientes_unicos = df['CLIENTE'].dropna().unique()
    
    fig = go.Figure()
    
    cores_status = {
        'FINALIZADO': '#566E3D',           # Verde oliva
        'EM ANDAMENTO': '#00233B',         # Azul escuro
        'EM EXECUÇÃO': '#003d5c',          # Azul médio
        'AGUARDANDO MATERIAL': '#BFCF99',  # Verde claro
        'AGUARDANDO APROVAÇÃO': '#dc2626', # Vermelho
        'A INICIAR': '#566E3D',            # Verde oliva
        'A DEFINIR': '#f59e0b',            # Amarelo
        'CANCELADO': '#7f1d1d',            # Vermelho escuro
        'SEM STATUS': '#6b7280'            # Cinza
    }
    
    y_labels = []
    
    # Iterar por cada cliente (UMA LINHA POR CLIENTE)
    for cliente in sorted(clientes_unicos):
        df_cliente = df[df['CLIENTE'] == cliente].copy()
        
        if df_cliente.empty:
            continue
        
        # Pegar a primeira e última data para criar a barra DO CLIENTE
        data_min = df_cliente[coluna_data].min()
        data_max = df_cliente[coluna_data].max()
        
        # Calcular duração em dias
        duracao = max(1, (data_max - data_min).days)
        if duracao == 0:
            duracao = 5  # Mínimo de 5 dias para visualização
        
        # Status predominante (mais frequente) do cliente
        status_predominante = df_cliente['STATUS'].mode().iloc[0] if 'STATUS' in df_cliente.columns and not df_cliente['STATUS'].mode().empty else 'SEM STATUS'
        
        cor = cores_status.get(status_predominante, '#6b7280')
        
        # Criar label: apenas CLIENTE
        cliente_abrev = str(cliente)[:50] if len(str(cliente)) > 50 else str(cliente)
        label_y = cliente_abrev
        y_labels.append(label_y)
        
        # Contagem de atividades do cliente
        qtd_atividades = len(df_cliente)
        qtd_propostas = df_cliente['NUMERO_PROPOSTA'].nunique() if 'NUMERO_PROPOSTA' in df_cliente.columns else 0
        
        # Texto do hover com detalhes agregados
        texto_hover = f"""
        <b>🏢 {cliente}</b><br>
        📊 Status principal: {status_predominante}<br>
        📅 Início: {data_min.strftime('%d/%m/%Y')}<br>
        📅 Fim: {data_max.strftime('%d/%m/%Y')}<br>
        📋 Total Atividades: {qtd_atividades}<br>
        📄 Propostas: {qtd_propostas}
        """
        
        fig.add_trace(go.Bar(
            x=[duracao],
            y=[label_y],
            orientation='h',
            name=status_predominante,
            marker=dict(
                color=cor,
                line=dict(color='white', width=1)
            ),
            base=data_min,
            text=f"{qtd_atividades} ativ.",
            textposition='inside',
            textfont=dict(color='white', size=11),
            hovertemplate=texto_hover + '<extra></extra>',
            hoverlabel=dict(
                bgcolor="rgba(0, 35, 59, 0.98)",
                font_size=15,
                font_family="Poppins",
                font_color="#FFFFFF",
                bordercolor="#566E3D",
                align="left"
            )
        ))
    
    # --- CÁLCULO DINÂMICO DE ALTURA ---
    qtd_itens = len(y_labels)
    pixels_por_barra = 35
    altura_dinamica = 180 + (qtd_itens * pixels_por_barra)
    altura_dinamica = max(400, min(altura_dinamica, 2000))  # Mín 400, Máx 2000
    # ----------------------------------

    fig.update_layout(
        title={
            'text': f"📊 Gráfico de Gantt Avançado - {coluna_data}",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': 'white'}
        },
        xaxis_title="Período de Tempo",
        yaxis_title=None,
        height=altura_dinamica,
        plot_bgcolor='rgba(0, 35, 59, 0.95)',
        paper_bgcolor='rgba(0, 35, 59, 0.95)',
        font=dict(color='#FFFFFF', size=11, family='Poppins'),
        showlegend=False,
        barmode='stack',
        margin=dict(l=20, r=20, t=80, b=50),
        yaxis=dict(
            automargin=True,
            gridcolor='#566E3D',
            tickcolor='#BFCF99',
            tickfont=dict(color='#FFFFFF', size=10)
        )
    )
    
    fig.update_xaxes(
        type='date',
        gridcolor='#566E3D',
        tickcolor='#BFCF99',
        tickfont=dict(color='white', size=11)
    )
    fig.update_yaxes(
        gridcolor='#566E3D',
        tickcolor='#BFCF99',
        tickfont=dict(color='white', size=10),
        autorange="reversed"
    )
    
    # Linha vertical para data atual
    hoje = datetime.now()
    fig.add_vline(
        x=hoje,
        line_dash="dash",
        line_color="#dc2626",
        line_width=2,
    )
    fig.add_annotation(
        x=hoje,
        y=1.02,
        xref="x",
        yref="paper",
        text="📍 HOJE",
        showarrow=False,
        font=dict(color="#dc2626", size=12),
        xanchor="left",
        bgcolor="rgba(0, 35, 59, 0.8)",
        bordercolor="#dc2626",
        borderwidth=1,
        borderpad=3,
    )
    
    return fig

def criar_quadro_kanban(df):
    """Cria quadro Kanban para visualização de status"""
    if df.empty or 'STATUS' not in df.columns:
        return pd.DataFrame()
    
    # Definir ordem das colunas Kanban
    ordem_kanban = [
        'A INICIAR',
        'AGUARDANDO MATERIAL',
        'AGUARDANDO APROVAÇÃO',
        'EM ANDAMENTO',
        'EM EXECUÇÃO',
        'A DEFINIR',
        'FINALIZADO',
        'CANCELADO'
    ]
    
    # Filtrar apenas status que existem nos dados
    status_existentes = [status for status in ordem_kanban if status in df['STATUS'].unique()]
    
    # Adicionar outros status não mapeados
    outros_status = [status for status in df['STATUS'].unique() if status not in ordem_kanban]
    status_existentes.extend(outros_status)
    
    # Criar dados para o Kanban
    dados_kanban = []
    
    for status in status_existentes:
        df_status = df[df['STATUS'] == status].head(10)  # Limitar para performance
        
        for _, row in df_status.iterrows():
            dados_kanban.append({
                'Status': status,
                'Cliente': row.get('CLIENTE', 'N/A'),
                'Proposta': row.get('NUMERO_PROPOSTA', 'N/A'),
                'Tipo': row.get('TIPO', 'N/A'),
                'Data': row.get('DATA_ENTREGA', 'N/A'),
                'Prioridade': '🔴 Alta' if status in ['A INICIAR', 'AGUARDANDO MATERIAL'] else '🟡 Média' if status in ['EM ANDAMENTO', 'EM EXECUÇÃO'] else '🟢 Baixa'
            })
    
    return pd.DataFrame(dados_kanban)

def criar_gauge_conclusao(df):
    """Cria gráfico de velocimetro para taxa de conclusão"""
    if df.empty or 'STATUS' not in df.columns:
        return go.Figure()
    
    total = len(df)
    finalizados = len(df[df['STATUS'] == 'FINALIZADO'])
    taxa_conclusao = (finalizados / total) * 100 if total > 0 else 0
    
    # Definir cores baseadas na taxa de conclusão
    if taxa_conclusao >= 75:
        cor = '#566E3D'  # Verde oliva
    elif taxa_conclusao >= 50:
        cor = '#BFCF99'  # Verde claro
    elif taxa_conclusao >= 25:
        cor = '#f59e0b'  # Amarelo
    else:
        cor = '#dc2626'  # Vermelho
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=taxa_conclusao,
        domain={'x': [0, 1], 'y': [0, 1]},
        delta={'reference': 75, 'increasing': {'color': '#566E3D'}},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': '#FFFFFF',
                'tickfont': {'size': 12, 'color': '#FFFFFF'}
            },
            'bar': {'color': cor},
            'bgcolor': 'rgba(0, 35, 59, 0.95)',
            'borderwidth': 2,
            'bordercolor': '#BFCF99',
            'steps': [
                {'range': [0, 25], 'color': 'rgba(220, 38, 38, 0.2)'},
                {'range': [25, 50], 'color': 'rgba(245, 158, 11, 0.2)'},
                {'range': [50, 75], 'color': 'rgba(191, 207, 153, 0.2)'},
                {'range': [75, 100], 'color': 'rgba(86, 110, 61, 0.2)'}
            ],
            'threshold': {
                'line': {'color': '#FFFFFF', 'width': 4},
                'thickness': 0.75,
                'value': 75
            }
        },
        title={
            'text': "Taxa de Conclusão",
            'font': {'size': 24, 'color': '#FFFFFF', 'family': 'Poppins'}
        },
        number={
            'font': {'size': 48, 'color': '#FFFFFF', 'family': 'Poppins'},
            'suffix': '%'
        }
    ))
    
    fig.update_layout(
        height=400,
        plot_bgcolor='rgba(0, 35, 59, 0.95)',
        paper_bgcolor='rgba(0, 35, 59, 0.95)',
        margin=dict(l=40, r=40, t=100, b=40)
    )
    
    return fig

def criar_panorama_geral(df):
    """Cria gráfico de panorama geral com todos os status - ESTILO POWER BI"""
    if df.empty or 'STATUS' not in df.columns:
        return go.Figure()
    
    # Contagem por status
    status_counts = df['STATUS'].value_counts()
    
    # Cores por status - cores mais vibrantes e visíveis
    cores_status = {
        'FINALIZADO': '#566E3D',           # Verde oliva
        'EM ANDAMENTO': '#00233B',         # Azul escuro
        'EM EXECUÇÃO': '#003d5c',          # Azul médio
        'AGUARDANDO MATERIAL': '#BFCF99',  # Verde claro
        'AGUARDANDO APROVAÇÃO': '#dc2626', # Vermelho
        'A INICIAR': '#566E3D',            # Verde oliva
        'A DEFINIR': '#f59e0b',            # Amarelo
        'CANCELADO': '#7f1d1d',            # Vermelho escuro
        'SEM STATUS': '#6b7280'            # Cinza
    }
    
    # Criar cores para cada status
    colors = [cores_status.get(status, '#BFCF99') for status in status_counts.index]
    
    # Calcular percentuais
    total = status_counts.sum()
    percentuais = [(count/total)*100 for count in status_counts.values]
    
    # Criar figura
    fig = go.Figure()
    
    # Adicionar barras com informações detalhadas e animação
    fig.add_trace(go.Bar(
        x=status_counts.index,
        y=status_counts.values,
        marker=dict(
            color=colors,
            line=dict(color='rgba(255, 255, 255, 0.8)', width=2),
            opacity=0.95
        ),
        text=[f'<b>{val}</b><br>({perc:.1f}%)' for val, perc in zip(status_counts.values, percentuais)],
        textposition='outside',
        textfont=dict(color='white', size=14, family='Poppins', weight='bold'),
        hovertemplate='<b style="font-size:16px">%{x}</b><br><br>' +
                      '<b>Quantidade:</b> %{y}<br>' +
                      '<b>Percentual:</b> %{customdata:.1f}%<br>' +
                      '<b>Total Geral:</b> ' + str(total) + '<br>' +
                      '<extra></extra>',
        customdata=percentuais,
        hoverlabel=dict(
            bgcolor="rgba(0, 35, 59, 0.98)",
            font_size=15,
            font_family="Poppins",
            font_color="white",
            bordercolor="rgba(255, 255, 255, 0.5)",
            align="left"
        )
    ))
    
    fig.update_layout(
        title={
            'text': '📊 PANORAMA GERAL - STATUS DE TODAS AS ATIVIDADES',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 26, 'color': '#FFFFFF', 'family': 'Poppins', 'weight': 'bold'}
        },
        xaxis_title="<b>Status das Atividades</b>",
        yaxis_title="<b>Quantidade de Atividades</b>",
        height=580,
        plot_bgcolor='rgba(0, 35, 59, 0.95)',
        paper_bgcolor='rgba(0, 35, 59, 0.95)',
        font=dict(color='#FFFFFF', size=14, family='Poppins'),
        showlegend=False,
        margin=dict(l=60, r=60, t=100, b=120),
        hovermode='x unified',
        hoverdistance=100,
        transition={'duration': 500}
    )
    
    fig.update_xaxes(
        gridcolor='rgba(86, 110, 61, 0.2)',
        tickcolor='#BFCF99',
        tickfont=dict(color='#FFFFFF', size=13, family='Poppins'),
        title_font=dict(color='#BFCF99', size=15, family='Poppins'),
        tickangle=-45,
        showgrid=False,
        zeroline=False,
        fixedrange=True
    )
    
    fig.update_yaxes(
        gridcolor='rgba(86, 110, 61, 0.25)',
        tickcolor='#BFCF99',
        tickfont=dict(color='#FFFFFF', size=13, family='Poppins'),
        title_font=dict(color='#BFCF99', size=15, family='Poppins'),
        showgrid=True,
        zeroline=True,
        fixedrange=True
    )
    
    return fig

# -------------------------------------------------------------------------
# FUNÇÃO REESCRITA COM ALTURA DINÂMICA
# -------------------------------------------------------------------------
def criar_gantt_atividades_criticas(df):
    """
    Cria gráfico de Gantt para atividades críticas usando dados do FORM 022 A.
    Utiliza DATA_RECEBIMENTO como início e DATA_ENTREGA como fim.
    COM ALTURA DINÂMICA.
    """
    if df.empty or 'STATUS' not in df.columns:
        return go.Figure()
    
    # Filtrar atividades não finalizadas
    status_ativos = ['AGUARDANDO MATERIAL', 'AGUARDANDO APROVAÇÃO', 'A INICIAR', 'A DEFINIR', 'EM ANDAMENTO', 'EM EXECUÇÃO']
    df_criticas = df[df['STATUS'].isin(status_ativos)].copy()
    
    if df_criticas.empty:
        # Se não há atividades críticas, mostrar todas as atividades
        df_criticas = df.copy()
    
    if df_criticas.empty:
        return go.Figure()
    
    # Preparar datas
    hoje = datetime.now()
    
    # Usar DATA_RECEBIMENTO como início e DATA_ENTREGA como fim
    if 'DATA_RECEBIMENTO' in df_criticas.columns:
        df_criticas['DATA_RECEBIMENTO'] = pd.to_datetime(df_criticas['DATA_RECEBIMENTO'], errors='coerce')
    else:
        df_criticas['DATA_RECEBIMENTO'] = hoje - timedelta(days=7)
    
    if 'DATA_ENTREGA' in df_criticas.columns:
        df_criticas['DATA_ENTREGA'] = pd.to_datetime(df_criticas['DATA_ENTREGA'], errors='coerce')
    else:
        df_criticas['DATA_ENTREGA'] = hoje + timedelta(days=14)
    
    # Preencher datas vazias
    df_criticas['DATA_RECEBIMENTO'] = df_criticas['DATA_RECEBIMENTO'].fillna(hoje - timedelta(days=7))
    df_criticas['DATA_ENTREGA'] = df_criticas['DATA_ENTREGA'].fillna(hoje + timedelta(days=14))
    
    # Calcular duração em dias
    df_criticas['DURACAO'] = (df_criticas['DATA_ENTREGA'] - df_criticas['DATA_RECEBIMENTO']).dt.days
    df_criticas['DURACAO'] = df_criticas['DURACAO'].apply(lambda x: max(1, x) if pd.notna(x) else 7)
    
    # Ordenar por data de entrega
    df_criticas = df_criticas.sort_values('DATA_ENTREGA', ascending=True)
    
    # Limitar para melhor visualização
    df_display = df_criticas.head(50) if len(df_criticas) > 50 else df_criticas
    
    # --- CÁLCULO DINÂMICO DE ALTURA ---
    qtd_itens = len(df_display)
    pixels_por_barra = 50  # Altura confortável para cada barra + espaço
    altura_cabecalho = 180 # Espaço para título, legendas e eixo X
    altura_dinamica = altura_cabecalho + (qtd_itens * pixels_por_barra)
    # ----------------------------------

    # Criar figura com Plotly Timeline
    fig = go.Figure()
    
    # Cores por status usando paleta corporativa
    cores_status = {
        'FINALIZADO': '#566E3D',           # Verde oliva
        'EM EXECUÇÃO': '#00233B',          # Azul escuro
        'EM ANDAMENTO': '#00233B',         # Azul escuro
        'AGUARDANDO MATERIAL': '#BFCF99',  # Verde claro
        'AGUARDANDO APROVAÇÃO': '#dc2626', # Vermelho
        'A INICIAR': '#566E3D',            # Verde oliva
        'A DEFINIR': '#f59e0b',            # Amarelo
        'CANCELADO': '#7f1d1d',            # Vermelho escuro
    }
    
    for idx, row in df_display.iterrows():
        status = row.get('STATUS', 'A DEFINIR')
        cor = cores_status.get(status, '#BFCF99')
        
        # Verificar se está vencido
        data_entrega = row['DATA_ENTREGA']
        is_vencido = data_entrega < hoje if pd.notna(data_entrega) else False
        
        if is_vencido and status != 'FINALIZADO':
            cor = '#dc2626'  # Vermelho para vencidos
            status_display = f"⚠️ {status} (VENCIDO)"
        else:
            status_display = status
        
        # Criar label para eixo Y usando apenas o nome da empresa
        cliente = str(row.get('CLIENTE', 'N/A')).strip()[:60]
        label_y = cliente if cliente else "EMPRESA NAO INFORMADA"

        # Texto do hover
        material = row.get('MATERIAL', 'N/A') if pd.notna(row.get('MATERIAL')) else 'N/A'
        dias_restantes = row.get('DIAS_VENCIMENTO', 'N/A')

        hover_text = f"""
        <b>🏢 {row.get('CLIENTE', 'N/A')}</b><br>
        📄 Proposta: {row.get('NUMERO_PROPOSTA', 'N/A')}<br>
        📊 Status: {status_display}<br>
        🧪 Material: {material}<br>
        📅 Recebimento: {row['DATA_RECEBIMENTO'].strftime('%d/%m/%Y') if pd.notna(row['DATA_RECEBIMENTO']) else 'N/A'}<br>
        📅 Entrega: {row['DATA_ENTREGA'].strftime('%d/%m/%Y') if pd.notna(row['DATA_ENTREGA']) else 'N/A'}<br>
        ⏰ Dias restantes: {dias_restantes}
        """
        
        fig.add_trace(go.Bar(
            x=[row['DURACAO']],
            y=[label_y],
            orientation='h',
            name=status,
            marker=dict(
                color=cor,
                line=dict(color='#FFFFFF', width=1),
                pattern_shape="/" if is_vencido else None
            ),
            base=row['DATA_RECEBIMENTO'],
            text=status_display,
            textposition='inside',
            textfont=dict(color='white', size=10),
            hovertemplate=hover_text + '<extra></extra>',
            hoverlabel=dict(bgcolor="#00233B", font_size=12, font_color="white")
        ))
    
    # Layout com cores corporativas e ALTURA DINÂMICA
    fig.update_layout(
        title={
            'text': '📊 GANTT DE ATIVIDADES - CRONOGRAMA DE ENTREGAS',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': '#FFFFFF', 'family': 'Poppins'}
        },
        xaxis_title="Período de Execução",
        yaxis_title=None,
        
        # AQUI A MÁGICA ACONTECE
        height=altura_dinamica,
        
        plot_bgcolor='rgba(0, 35, 59, 0.9)',
        paper_bgcolor='rgba(0, 35, 59, 0.9)',
        font=dict(color='#FFFFFF', size=11, family='Poppins'),
        showlegend=False,
        barmode='stack',
        margin=dict(l=20, r=20, t=80, b=50),
        yaxis=dict(automargin=True)
    )
    
    fig.update_xaxes(
        type='date',
        gridcolor='#566E3D',
        tickcolor='#BFCF99',
        tickfont=dict(color='#FFFFFF', size=11),
        title_font=dict(color='#BFCF99', size=14)
    )
    
    fig.update_yaxes(
        gridcolor='#566E3D',
        tickcolor='#BFCF99',
        tickfont=dict(color='#FFFFFF', size=12),
        autorange="reversed"
    )
    
    # Linha vertical para data atual
    fig.add_vline(
        x=hoje,
        line_dash="dash",
        line_color="#dc2626",
        line_width=3,
    )

    fig.add_annotation(
        x=hoje,
        y=1.02,
        xref="x",
        yref="paper",
        text="📍 HOJE",
        showarrow=False,
        font=dict(color="#dc2626", size=14, family="Poppins"),
        xanchor="left",
        bgcolor="rgba(0, 35, 59, 0.8)",
        bordercolor="#dc2626",
        borderwidth=1,
        borderpad=4,
    )
    
    return fig

def criar_estatisticas_criticas(df):
    """Cria estatísticas específicas para atividades críticas"""
    if df.empty or 'STATUS' not in df.columns:
        return {}
    
    # Status críticos
    status_criticos = {
        'AGUARDANDO MATERIAL': '🔴 Crítico',
        'AGUARDANDO APROVAÇÃO': '🔴 Crítico',
        'A INICIAR': '🟡 Urgente',
        'A DEFINIR': '🟡 Urgente',
        'EM ANDAMENTO': '🔵 Em Progresso',
        'EM EXECUÇÃO': '🔵 Em Progresso'
    }
    
    estatisticas = {}
    
    # Contar atividades críticas
    df_criticas = df[df['STATUS'].isin(status_criticos.keys())]
    estatisticas['total_criticas'] = len(df_criticas)
    
    # Por nível de criticidade
    criticidade_counts = {}
    for status, nivel in status_criticos.items():
        count = len(df[df['STATUS'] == status])
        if count > 0:
            if nivel not in criticidade_counts:
                criticidade_counts[nivel] = 0
            criticidade_counts[nivel] += count
    
    estatisticas['por_criticidade'] = criticidade_counts
    
    # Por status específico
    estatisticas['por_status_critico'] = {}
    for status in status_criticos.keys():
        count = len(df[df['STATUS'] == status])
        if count > 0:
            estatisticas['por_status_critico'][status] = count
    
    return estatisticas

def criar_grafico_entregas_fas(df):
    """Cria gráfico de timeline com datas de entrega extraídas da FAS"""
    if df.empty:
        return go.Figure()
    
    # Verificar se tem coluna de data de entrega
    if 'DATA_ENTREGA_FAS' not in df.columns and 'DATA_ENTREGA' not in df.columns:
        return go.Figure()
    
    # Usar DATA_ENTREGA_FAS ou DATA_ENTREGA
    coluna_data = 'DATA_ENTREGA_FAS' if 'DATA_ENTREGA_FAS' in df.columns else 'DATA_ENTREGA'
    
    # Filtrar apenas registros com data válida
    df_entregas = df.copy()
    df_entregas[coluna_data] = pd.to_datetime(df_entregas[coluna_data], dayfirst=True, errors='coerce')
    df_entregas = df_entregas.dropna(subset=[coluna_data])
    
    if df_entregas.empty:
        return go.Figure()
    
    # Ordenar por data
    df_entregas = df_entregas.sort_values(coluna_data)
    
    # Cores por status
    cores_status = {
        'FINALIZADO': '#566E3D',           # Verde oliva
        'EM ANDAMENTO': '#00233B',         # Azul escuro
        'EM EXECUÇÃO': '#003d5c',          # Azul médio
        'AGUARDANDO MATERIAL': '#BFCF99',  # Verde claro
        'AGUARDANDO APROVAÇÃO': '#dc2626', # Vermelho
        'A INICIAR': '#566E3D',            # Verde oliva
        'A DEFINIR': '#f59e0b',            # Amarelo
        'CANCELADO': '#7f1d1d',            # Vermelho escuro
        'SEM STATUS': '#6b7280'            # Cinza
    }
    
    fig = go.Figure()
    
    # Adicionar marcadores para cada entrega
    for status in df_entregas['STATUS'].unique():
        df_status = df_entregas[df_entregas['STATUS'] == status]
        cor = cores_status.get(status, '#6b7280')
        
        fig.add_trace(go.Scatter(
            x=df_status[coluna_data],
            y=df_status['CLIENTE'].astype(str).str[:30],
            mode='markers+text',
            name=status,
            marker=dict(
                size=16,
                color=cor,
                line=dict(width=2, color='white'),
                symbol='diamond'
            ),
            text=df_status['NUMERO_PROPOSTA'],
            textposition='top center',
            textfont=dict(color='white', size=10),
            hovertemplate='<b>%{text}</b><br>Cliente: %{y}<br>Entrega: %{x|%d/%m/%Y}<br>Status: ' + status + '<extra></extra>',
            hoverlabel=dict(
            bgcolor="rgba(0, 35, 59, 0.98)",
            font_size=12,
            font_family="Poppins",
            font_color="#FFFFFF",
            bordercolor="#566E3D"
        )
        ))
    
    # Adicionar linha vertical para data atual
    hoje = pd.Timestamp.now()
    fig.add_shape(
        type="line",
        x0=hoje, x1=hoje,
        y0=0, y1=1,
        yref="paper",
        line=dict(color="red", width=2, dash="dash")
    )
    fig.add_annotation(
        x=hoje,
        y=1.02,
        yref="paper",
        text="HOJE",
        showarrow=False,
        font=dict(color="red", size=12)
    )
    
    fig.update_layout(
        title={
            'text': '📅 CRONOGRAMA DE ENTREGAS (FAS)',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': 'white'}
        },
        xaxis_title="Data de Entrega do Relatório",
        yaxis_title="Cliente",
        height=max(500, len(df_entregas) * 30),
        plot_bgcolor='rgba(26, 31, 46, 0.9)',
        paper_bgcolor='rgba(26, 31, 46, 0.9)',
        font=dict(color='white', size=12),
        hovermode='closest',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='white', size=11),
            bgcolor='rgba(26, 31, 46, 0.8)'
        ),
        margin=dict(l=20, r=20, t=80, b=20)
    )
    
    fig.update_xaxes(
        gridcolor='#4a5568',
        tickcolor='#4a5568',
        tickfont=dict(color='white', size=11),
        title_font=dict(color='white', size=14)
    )
    
    fig.update_yaxes(
        gridcolor='#4a5568',
        tickcolor='#4a5568',
        tickfont=dict(color='white', size=10),
        title_font=dict(color='white', size=14)
    )
    
    return fig

def criar_grafico_cbb_asfaltec(df_raw):
    """
    Gráfico comparativo CBB ASFALTOS x ASFALTEC.
    Unidade principal (Unidade_Padrão_atividades): PTs distintos agrupados por empresa.
    Cada grupo de PTs CBB ou ASFALTEC = 1 unidade de medida padronizada.
    """
    if df_raw is None or df_raw.empty:
        return go.Figure()

    col_cliente = 'CLIENTE' if 'CLIENTE' in df_raw.columns else 'EMPRESA'
    df_target = df_raw[df_raw[col_cliente].str.contains('CBB|ASFALTEC', na=False, case=False)].copy()

    if df_target.empty:
        return go.Figure()

    def _grupo(c):
        c = str(c).upper()
        if 'ASFALTEC' in c: return 'ASFALTEC'
        if 'CBB' in c:      return 'CBB ASFALTOS'
        return None

    df_target['GRUPO'] = df_target[col_cliente].apply(_grupo)
    df_target = df_target.dropna(subset=['GRUPO'])

    col_pt = 'NUMERO_PROPOSTA' if 'NUMERO_PROPOSTA' in df_target.columns else 'PT_COLUNA_A'
    df_target['QTD_NUM'] = pd.to_numeric(df_target.get('QUANTIDADE', 1), errors='coerce').fillna(1)

    pts_por_grupo      = df_target.groupby('GRUPO')[col_pt].nunique().to_dict()
    amostras_por_grupo = df_target.groupby('GRUPO')['QTD_NUM'].sum().to_dict()

    grupos_ordenados = ['CBB ASFALTOS', 'ASFALTEC']
    grupos   = [g for g in grupos_ordenados if g in pts_por_grupo]
    pts      = [int(pts_por_grupo.get(g, 0))      for g in grupos]
    amostras = [int(amostras_por_grupo.get(g, 0))  for g in grupos]

    CORES_GRUPO = {
        'CBB ASFALTOS': '#1e6091',
        'ASFALTEC':     '#566E3D',
    }
    cores = [CORES_GRUPO.get(g, '#BFCF99') for g in grupos]

    hover_texts = [
        f'<b style="font-size:16px">{g}</b><br>'
        f'<b>PTs Distintos (Unidade_Padrão):</b> {p}<br>'
        f'<b>Amostras (total):</b> {a}'
        for g, p, a in zip(grupos, pts, amostras)
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='PTs',
        x=grupos,
        y=pts,
        marker=dict(color=cores, line=dict(color='white', width=2), opacity=0.95),
        text=[f'<b>{v}</b>' for v in pts],
        textposition='outside',
        textfont=dict(color='white', size=20, family='Poppins'),
        hovertext=hover_texts,
        hovertemplate='%{hovertext}<extra></extra>',
        hoverlabel=dict(
            bgcolor='rgba(0, 35, 59, 0.98)',
            font_size=14, font_family='Poppins', font_color='white',
            bordercolor='#BFCF99', align='left'
        ),
    ))

    fig.update_layout(
        title={
            'text': '🏗️ CBB ASFALTOS & ASFALTEC — PTs por Empresa (Unidade_Padrão_atividades)',
            'x': 0.5, 'xanchor': 'center',
            'font': {'size': 18, 'color': '#FFFFFF', 'family': 'Poppins'}
        },
        barmode='group', height=360,
        dragmode=False,
        plot_bgcolor='rgba(0, 35, 59, 0.95)',
        paper_bgcolor='rgba(0, 35, 59, 0.95)',
        font=dict(color='#FFFFFF', size=13, family='Poppins'),
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50),
        yaxis_title='PTs (Unidade_Padrão_atividades)',
    )
    fig.update_xaxes(
        tickfont=dict(color='white', size=15, family='Poppins'),
        showgrid=False, zeroline=False,
        fixedrange=True
    )
    fig.update_yaxes(
        gridcolor='rgba(86, 110, 61, 0.25)',
        tickfont=dict(color='white', size=12),
        rangemode='tozero',
        fixedrange=True
    )
    return fig


def criar_grafico_entregas_mensal(df):
    """Cria gráfico de barras com entregas agrupadas por mês"""
    if df.empty:
        return go.Figure()
    
    # Usar DATA_ENTREGA_FAS ou DATA_ENTREGA
    coluna_data = 'DATA_ENTREGA_FAS' if 'DATA_ENTREGA_FAS' in df.columns else 'DATA_ENTREGA'
    
    if coluna_data not in df.columns:
        return go.Figure()
    
    df_entregas = df.copy()
    df_entregas[coluna_data] = pd.to_datetime(df_entregas[coluna_data], dayfirst=True, errors='coerce')
    df_entregas = df_entregas.dropna(subset=[coluna_data])
    
    if df_entregas.empty:
        return go.Figure()
    
    # Agrupar por mês/ano
    df_entregas['MES_ANO'] = df_entregas[coluna_data].dt.strftime('%m/%Y')
    entregas_por_mes = df_entregas.groupby('MES_ANO').size().reset_index(name='QUANTIDADE')
    
    # Ordenar por data
    entregas_por_mes['DATA_ORDEM'] = pd.to_datetime(entregas_por_mes['MES_ANO'], format='%m/%Y')
    entregas_por_mes = entregas_por_mes.sort_values('DATA_ORDEM')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=entregas_por_mes['MES_ANO'],
        y=entregas_por_mes['QUANTIDADE'],
        marker_color='#3b82f6',
        text=entregas_por_mes['QUANTIDADE'],
        textposition='auto',
        textfont=dict(color='white', size=14),
        hovertemplate='<b>%{x}</b><br>Entregas: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': '📊 ENTREGAS POR MÊS',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': 'white'}
        },
        xaxis_title="Mês/Ano",
        yaxis_title="Quantidade de Entregas",
        height=400,
        plot_bgcolor='rgba(26, 31, 46, 0.9)',
        paper_bgcolor='rgba(26, 31, 46, 0.9)',
        font=dict(color='white', size=12),
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    fig.update_xaxes(
        gridcolor='#4a5568',
        tickcolor='#4a5568',
        tickfont=dict(color='white', size=11),
        tickangle=45
    )
    
    fig.update_yaxes(
        gridcolor='#4a5568',
        tickcolor='#4a5568',
        tickfont=dict(color='white', size=11)
    )
    
    return fig

# ======================================================================================
# LÓGICA PRINCIPAL DO CRONOGRAMA
# ======================================================================================

def main():
    
    # Sidebar com logo e ações
    # Variáveis dos filtros para reutilizar em outras seções
    _filtro_cliente_sel = "Todos"
    _filtro_mes_num = None
    _filtro_ano_num = None

    with st.sidebar:
        # Botão Menu Principal
        st.markdown("""<style>
        div[data-testid="stButton"][key="back_to_menu_cronograma"] > button {
            background: transparent !important;
            border: 1px solid rgba(191,207,153,0.3) !important;
            color: rgba(191,207,153,0.7) !important;
            font-size: 0.78rem !important;
            padding: 0.2rem 0.6rem !important;
            border-radius: 6px !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stButton"][key="back_to_menu_cronograma"] > button:hover {
            background: rgba(191,207,153,0.1) !important;
            color: #BFCF99 !important;
        }
        </style>""", unsafe_allow_html=True)
        if st.button("< Menu Principal", key="back_to_menu_cronograma"):
            st.switch_page("app.py")

        # Logo grande na sidebar
        logo_sidebar = "Imagens/AE - Logo Hor Principal_2.png"
        if os.path.exists(logo_sidebar):
            st.image(logo_sidebar, use_container_width=True)
        else:
            st.markdown(f"""
            <div style="background: {CORES['secundario']}; padding: 1.5rem; border-radius: 12px; text-align: center; margin-bottom: 1rem;">
                <h2 style="color: white; margin: 0;">AFIRMA E-VIAS</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(f"<h3 style='color: {CORES['destaque']}; text-align: center;'>AE - Dashboard's</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Ações rápidas
        st.markdown(f"<h4 style='color: {CORES['destaque']};'>Ações</h4>", unsafe_allow_html=True)
        col_sync, col_clear = st.columns(2)
        with col_sync:
            if st.button("Sincronizar", use_container_width=True):
                sync_all_data()
                # Limpa todos os caches para refletir os dados recém-sincronizados
                st.cache_data.clear()
                for _k in ['df_sql_cache', 'df_fas_cache', 'df_raw_cbb_cache']:
                    st.session_state.pop(_k, None)
                st.success("Dados sincronizados!")
                st.rerun()
        with col_clear:
            if st.button("Limpar Filtros", use_container_width=True):
                for key in st.session_state.keys():
                    if key.startswith("filtro_") or key in ["ano_sel", "status_sel", "tipo_proposta_sel", "cliente_sel", "proposta_sel", "filtro_rapido_data"]:
                        del st.session_state[key]
                st.rerun()
    
    # Header com Logo na área principal - Selo + título próximos
    col_logo, col_titulo = st.columns([0.8, 4])
    with col_logo:
        try:
            logo_path = r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias\Manual Completo\Identidade Visual\Logotipo e Variações\Símbolo e Selos\PNG\Selo C Ass\Selo C Ass_4.png"
            if os.path.exists(logo_path):
                st.image(logo_path, use_container_width=True)
            else:
                st.markdown("## 📅")
        except Exception:
            st.markdown("## 📅")
    
    with col_titulo:
        st.markdown(f"""
        <div style="padding-left: 1rem;">
            <h1 style="margin: 0;">Quantitativo de Atividades</h1>
            <p style="color: {CORES['destaque']}; font-size: 1.1rem;">Sistema de Acompanhamento de Prazos, Status e Materiais | FORM 022 A</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==========================================================================
    # CARREGAMENTO OTIMIZADO - APENAS SQLite (SEM PROCESSAMENTO WORD LENTO)
    # ==========================================================================
    # Os dados já foram extraídos do FORM 022 A e salvos no SQLite
    # Isso elimina o processamento lento de arquivos Word a cada reload
    
    # Carrega dados do SQLite com dupla camada de cache:
    # 1ª: session_state → zero overhead em reruns dentro da mesma sessão
    # 2ª: @st.cache_data(ttl=300) → compartilhado entre sessões por até 5 min
    if 'df_sql_cache' not in st.session_state:
        with st.spinner("⚡ Carregando dados do SQLite..."):
            st.session_state['df_sql_cache'] = carregar_dados_consolidados_sql()
    df = st.session_state['df_sql_cache']

    # Se o dataframe estiver vazio, tenta sincronizar e recarregar
    if df.empty:
        st.warning("📦 Banco de dados vazio. Iniciando sincronização...")
        with st.spinner("🔄 Sincronizando FORM 022 A... (isso é feito apenas 1x)"):
            sync_all_data()
        st.cache_data.clear()
        for _k in ['df_sql_cache', 'df_fas_cache', 'df_raw_cbb_cache']:
            st.session_state.pop(_k, None)
        st.success("✅ Sincronização concluída!")
        st.rerun()
    
    # ==========================================================================
    # PRÉ-PROCESSAMENTO E LIMPEZA DE DADOS
    # ==========================================================================
    
    # 1. Garantir coluna TEM_MATERIAL
    if 'TEM_MATERIAL' not in df.columns:
        df['TEM_MATERIAL'] = df['DATA_RECEBIMENTO'].notna()
        
    # 2. FORÇAR LIMPEZA: Se STATUS contém "FINALIZADO" ou "CONCLUÍDO", 
    # ele NÃO pode aparecer como "Sem Material" ou "Vencido"
    mask_finalizado = df['STATUS'].str.upper().str.contains('FINALIZADO|CONCLU', na=False)
    
    # Corrige inconsistências visuais
    df.loc[mask_finalizado, 'TEM_MATERIAL'] = True
    df.loc[mask_finalizado, 'STATUS_PRAZO'] = 'FINALIZADO'
    df.loc[mask_finalizado, 'STATUS'] = 'FINALIZADO'

    # 3. Calcular Métricas
    total = len(df)
    
    # Finalizados Reais
    finalizados_real = len(df[mask_finalizado])
    
    # Aguardando Material (Lógica Estrita)
    # Só conta se TEM_MATERIAL é False (0) E o status NÃO é finalizado
    aguardando_df = df[
        (df['TEM_MATERIAL'] == 0) & 
        (~mask_finalizado) & 
        (df['STATUS'] != 'EM ANDAMENTO') # Garante que CCs em andamento não caiam aqui
    ]
    aguardando_real = len(aguardando_df)
    
    # Vencidos (Lógica Estrita)
    # Só conta se o prazo expirou E não está finalizado
    if 'STATUS_PRAZO' in df.columns:
        vencidos_df = df[
            (df['STATUS_PRAZO'] == 'VENCIDO') & 
            (~mask_finalizado)
        ]
        vencidos_real = len(vencidos_df)
    else:
        vencidos_df = pd.DataFrame()
        vencidos_real = 0
        
    # Em Execução (O restante)
    # Tudo que não é finalizado e não é aguardando material
    em_execucao_real = total - finalizados_real - aguardando_real
    
    # ==========================================================================
    # IDENTIFICAR CONTRATOS CONTÍNUOS (CC) - PELO TIPO_PROPOSTA DO FORM 022 A
    # ==========================================================================
    # CC é identificado diretamente pelo campo TIPO_PROPOSTA (quando não tem PC, é CC)
    # OU pelo NUMERO_PROPOSTA que começa com "CC"
    if 'TIPO_PROPOSTA' in df.columns:
        df['E_CONTRATO_CONTINUO'] = df['TIPO_PROPOSTA'] == 'CC'
    elif 'NUMERO_PROPOSTA' in df.columns:
        df['E_CONTRATO_CONTINUO'] = df['NUMERO_PROPOSTA'].astype(str).str.upper().str.startswith('CC')
    else:
        df['E_CONTRATO_CONTINUO'] = False
    
    # Carregar lista adicional de clientes CC do FORM 067 para complementar
    clientes_cc = carregar_clientes_contrato_continuo()
    
    # Complementar: marcar também se o cliente está na lista do FORM 067
    if 'CLIENTE' in df.columns and clientes_cc:
        df['E_CONTRATO_CONTINUO'] = df.apply(
            lambda row: row['E_CONTRATO_CONTINUO'] or verificar_cliente_cc(row.get('CLIENTE'), clientes_cc),
            axis=1
        )
    
    # Converter colunas de data para datetime (otimizado)
    if 'DATA_ENTREGA' in df.columns:
        df['DATA_ENTREGA'] = pd.to_datetime(df['DATA_ENTREGA'], errors='coerce')
    if 'DATA_RECEBIMENTO' in df.columns:
        df['DATA_RECEBIMENTO'] = pd.to_datetime(df['DATA_RECEBIMENTO'], errors='coerce')
    
    # Recalcular dias de vencimento em tempo real (rápido)
    if 'DATA_ENTREGA' in df.columns:
        hoje = pd.Timestamp.now()
        
        # Função para cálculo de prazo - RESPEITA STATUS FINALIZADO e CONTRATO_CONTINUO
        def calcular_status_prazo(row):
            # REGRA 1: Se STATUS já é FINALIZADO, manter FINALIZADO
            if row.get('STATUS') == 'FINALIZADO':
                return 'FINALIZADO', 0
            
            # REGRA 2: Se é Contrato Contínuo, não calcular prazo
            if row.get('STATUS_PRAZO') == 'CONTRATO_CONTINUO' or row.get('E_CONTRATO_CONTINUO') == True:
                return 'CONTRATO_CONTINUO', 0
            
            data_entrega = row['DATA_ENTREGA']
            if pd.isna(data_entrega):
                return 'SEM PRAZO', 0
            
            dias_corridos = (data_entrega - hoje).days
            
            status = 'NO PRAZO'
            if dias_corridos < 0:
                status = 'VENCIDO'
            elif dias_corridos <= 7:
                status = 'URGENTE'
            elif dias_corridos <= 30:
                status = 'ATENÇÃO'
            
            return status, dias_corridos

        # Aplicar lógica de prazo
        prazos_calculados = df.apply(calcular_status_prazo, axis=1)
        df['STATUS_PRAZO'] = [p[0] for p in prazos_calculados]
        df['DIAS_VENCIMENTO'] = [p[1] for p in prazos_calculados]
    
    if df.empty:
        st.error("⚠️ Não foi possível carregar os dados.")
        st.info("💡 Clique em 'Sincronizar Dados' na sidebar para importar do FORM 022 A.")
        st.stop()

    # Consolidado de FAS disponível para múltiplas seções — carregado com df completo (pré-filtro)
    if 'df_fas_cache' not in st.session_state:
        st.session_state['df_fas_cache'] = consolidar_fas_totais(df)
    df_fas = st.session_state.get('df_fas_cache', pd.DataFrame())

    # Carregar raw CC (global) uma vez
    if 'df_raw_cbb_cache' in st.session_state:
        _df_raw_upa = st.session_state['df_raw_cbb_cache']
    else:
        _df_raw_upa = carregar_dados_epr_raw(cliente_filtro=None)
        if not _df_raw_upa.empty:
            st.session_state['df_raw_cbb_cache'] = _df_raw_upa

    # ==================================================================================
    # FILTROS DA SIDEBAR — aplicados ANTES de todo conteúdo para que TODOS os gráficos
    # respondam aos filtros corretamente
    # ==================================================================================
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"<h3 style='color: {CORES['destaque']};'>Filtros Avançados</h3>", unsafe_allow_html=True)

        # Filtro de Ano
        st.markdown("**Ano:**")
        if 'ANO' in df.columns:
            anos = sorted(df['ANO'].dropna().unique(), reverse=True)
            ano_sel = st.selectbox("Ano", ["Todos"] + list(anos), index=0,
                                   key="ano_sel", label_visibility="collapsed")
            if ano_sel != "Todos":
                df = df[df['ANO'] == ano_sel]

        # Filtro de Cliente
        st.markdown("**Cliente:**")
        if 'CLIENTE' in df.columns:
            clientes = sorted(df['CLIENTE'].dropna().astype(str).unique())
            cliente_sel = st.selectbox("Cliente", ["Todos"] + list(clientes), index=0,
                                       key="cliente_sel", label_visibility="collapsed")
            _filtro_cliente_sel = cliente_sel
            if cliente_sel != "Todos":
                df = df[df['CLIENTE'] == cliente_sel]

        # Filtro de Mês — usa DATA_RECEBIMENTO
        st.markdown("**Mês (Data Recebimento)**")
        coluna_principal = 'DATA_RECEBIMENTO'
        if coluna_principal not in df.columns:
            st.info("ℹ️ A coluna DATA_RECEBIMENTO não está disponível para filtro.")
        else:
            datas_recebimento = pd.to_datetime(df[coluna_principal], dayfirst=True, errors='coerce')
            datas_validas = datas_recebimento.dropna()

            if datas_validas.empty:
                st.warning("⚠️ Nenhuma data válida encontrada em DATA_RECEBIMENTO.")
            else:
                _meses_disp = sorted(datas_validas.dt.to_period('M').unique(), reverse=True)
                nomes_meses = {
                    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
                }
                opcoes_mes = ["Todos"] + [
                    f"{nomes_meses[p.month]}/{p.year}" for p in _meses_disp
                ]
                selecao_mes = st.selectbox(
                    "Mês/Ano", opcoes_mes,
                    key="filtro_mes_data_recebimento",
                    label_visibility="collapsed"
                )

                if selecao_mes != "Todos":
                    # Parse "Janeiro/2026" → month=1, year=2026
                    _nome_mes, _ano_mes = selecao_mes.rsplit("/", 1)
                    _filtro_mes_num = [n for n, nome in nomes_meses.items() if nome == _nome_mes][0]
                    _filtro_ano_num = int(_ano_mes)
                    filtro_mes = (datas_recebimento.dt.month == _filtro_mes_num) & (datas_recebimento.dt.year == _filtro_ano_num)
                    df = df[filtro_mes]
                    st.success(f"✅ {selecao_mes}")

        # Botão de Reset
        if st.button("Resetar Filtros", use_container_width=True):
            st.rerun()
        
        # Contador de registros após filtros
        st.markdown("---")
        st.markdown(f"""
        <div style="background: rgba(86, 110, 61, 0.2); padding: 1rem; border-radius: 8px; border-left: 4px solid #566E3D;">
            <h4 style="color: white; margin: 0 0 0.5rem 0;">Registros Filtrados</h4>
            <p style="color: #BFCF99; margin: 0; font-size: 1.1rem;">
                <strong>{len(df)}</strong> registros
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

    # Aplicar ordenação padrão por DATA_ENTREGA (mais recente primeiro)
    if "DATA_ENTREGA" in df.columns:
        df = df.sort_values("DATA_ENTREGA", ascending=False)

    # ==================================================================================
    # RECALCULAR UPA COM FILTROS APLICADOS
    # ==================================================================================
    # Filtrar df_fas com os filtros globais de sidebar (cliente / mês)
    df_fas_sidebar = df_fas.copy()
    if not df_fas_sidebar.empty:
        if _filtro_cliente_sel != "Todos" and 'CLIENTE' in df_fas_sidebar.columns:
            df_fas_sidebar = df_fas_sidebar[
                df_fas_sidebar['CLIENTE'].astype(str).str.upper().str.contains(_filtro_cliente_sel.upper(), na=False)
            ]
        if _filtro_mes_num is not None and 'DATA_RECEBIMENTO' in df_fas_sidebar.columns:
            df_fas_sidebar['DATA_RECEBIMENTO'] = pd.to_datetime(df_fas_sidebar['DATA_RECEBIMENTO'], errors='coerce')
            df_fas_sidebar = df_fas_sidebar[
                (df_fas_sidebar['DATA_RECEBIMENTO'].dt.month == _filtro_mes_num) &
                (df_fas_sidebar['DATA_RECEBIMENTO'].dt.year  == _filtro_ano_num)
            ]

    # Calcular métricas de CC a partir do raw global, respeitando o filtro de cliente se aplicável
    def _qtd_cc(busca):
        if _df_raw_upa is None or _df_raw_upa.empty or 'CLIENTE' not in _df_raw_upa.columns:
            return 0
        df_c = _df_raw_upa[_df_raw_upa['CLIENTE'].astype(str).str.upper().str.contains(busca.upper(), na=False)]
        if _filtro_mes_num is not None and 'DATA_RECEBIMENTO' in df_c.columns:
            df_c = df_c.copy()
            df_c['DATA_RECEBIMENTO'] = pd.to_datetime(df_c['DATA_RECEBIMENTO'], errors='coerce')
            df_c = df_c[
                (df_c['DATA_RECEBIMENTO'].dt.month == _filtro_mes_num) &
                (df_c['DATA_RECEBIMENTO'].dt.year  == _filtro_ano_num)
            ]
        return int(pd.to_numeric(df_c.get('QUANTIDADE', pd.Series([1])), errors='coerce').fillna(1).sum()) if not df_c.empty else 0

    _dict_cc_upa = {
        'EIXO SP':              _qtd_cc('EIXO SP'),
        'EPR IGUAÇU':           _qtd_cc('EPR IGUA'),
        'EPR LITORAL PIONEIRO': _qtd_cc('EPR LITORAL'),
        'EPR VIAS DO CAFÉ':     _qtd_cc('EPR VIAS DO CAF'),
        'STRATA ENGENHARIA LTDA': _qtd_cc('STRATA ENGENHARIA'),
    }

    # CBB/ASF com filtro de mês, se selecionado
    _col_cli_upa = 'CLIENTE' if 'CLIENTE' in _df_raw_upa.columns else 'EMPRESA'
    _col_pt_upa  = 'NUMERO_PROPOSTA' if 'NUMERO_PROPOSTA' in _df_raw_upa.columns else 'PT_COLUNA_A'
    df_cbb_upa = _df_raw_upa.copy()
    if _filtro_mes_num is not None and 'DATA_RECEBIMENTO' in df_cbb_upa.columns:
        df_cbb_upa['DATA_RECEBIMENTO'] = pd.to_datetime(df_cbb_upa['DATA_RECEBIMENTO'], errors='coerce')
        df_cbb_upa = df_cbb_upa[
            (df_cbb_upa['DATA_RECEBIMENTO'].dt.month == _filtro_mes_num) &
            (df_cbb_upa['DATA_RECEBIMENTO'].dt.year  == _filtro_ano_num)
        ]
    _pts_cbb_upa = int(df_cbb_upa[
        df_cbb_upa[_col_cli_upa].str.contains('CBB', na=False, case=False)
    ][_col_pt_upa].nunique()) if not df_cbb_upa.empty else 0
    _pts_asf_upa = int(df_cbb_upa[
        df_cbb_upa[_col_cli_upa].str.contains('ASFALTEC', na=False, case=False)
    ][_col_pt_upa].nunique()) if not df_cbb_upa.empty else 0

    UPA = calcular_unidade_padrao(
        df_projetos_externos=None,  # atualizado após varredura de projetos externos
        df_fas=df_fas_sidebar,
        dict_cc_ensaios=_dict_cc_upa,
        pts_cbb=_pts_cbb_upa,
        pts_asfaltec=_pts_asf_upa,
    )
    st.session_state['UPA'] = UPA

    # ==================================================================================
    # DASHBOARD INTERATIVO - VISÃO GERAL DE MATERIAIS E PRAZOS
    # ==================================================================================
    
    # Mostrar período de dados disponíveis
    datas_info = []
    if 'DATA_RECEBIMENTO' in df.columns:
        dr = df['DATA_RECEBIMENTO'].dropna()
        if not dr.empty:
            datas_info.append(f"**Recebimento:** {dr.min().strftime('%d/%m/%Y')} a {dr.max().strftime('%d/%m/%Y')}")
    if 'DATA_ENTREGA' in df.columns:
        de = df['DATA_ENTREGA'].dropna()
        if not de.empty:
            datas_info.append(f"**Entrega:** {de.min().strftime('%d/%m/%Y')} a {de.max().strftime('%d/%m/%Y')}")
    
    if datas_info:
        st.info(f"📅 Período dos dados: {' | '.join(datas_info)}")
    
    # Usar métricas já calculadas no pré-processamento
    total_registros = total
    finalizados = finalizados_real
    aguardando = aguardando_real
    vencidos = vencidos_real
    em_execucao = em_execucao_real
    
    # Calcular métricas adicionais
    if 'TEM_MATERIAL' in df.columns:
        com_material = len(df[(df['TEM_MATERIAL'] == True)])
        sem_material = aguardando  # Usar o aguardando já calculado
    else:
        com_material = sem_material = 0
    
    # Status de prazo adicionais
    if 'STATUS_PRAZO' in df.columns:
        urgentes = len(df[(df['STATUS_PRAZO'] == 'URGENTE') & (~mask_finalizado)])
        atencao = len(df[(df['STATUS_PRAZO'] == 'ATENÇÃO') & (~mask_finalizado)])
        no_prazo = len(df[(df['STATUS_PRAZO'] == 'NO PRAZO') & (~mask_finalizado)])
    else:
        urgentes = atencao = no_prazo = 0
    
    # ==================================================================================
    # DISTRIBUIÇÃO DE QUANTITATIVOS POR EMPRESA (via UPA)
    # ==================================================================================
    UPA = st.session_state.get('UPA', {})
    st.markdown("## Quantitativos por Empresa")
    

    _labels_upa = [v['label'] for k, v in UPA.items() if k != '__TOTAL__' and v.get('unidades', 0) > 0]
    _values_upa = [v['unidades'] for k, v in UPA.items() if k != '__TOTAL__' and v.get('unidades', 0) > 0]

    if _labels_upa:
        _total_upa = UPA.get('__TOTAL__', {}).get('unidades', 0)

        # Seletor de empresa — controla o valor exibido no centro do gráfico
        _opcoes_sel = ["Todos (Total Geral)"] + _labels_upa
        _empresa_sel = st.selectbox(
            "Filtros:",
            options=_opcoes_sel,
            key="rosca_empresa_sel"
        )

        # Calcular valor e percentual do grupo selecionado
        if _empresa_sel == "Todos (Total Geral)":
            _val_centro = _total_upa
            _txt_centro = f"<b>{_val_centro}</b>"
            _info_banner = None
        else:
            _idx_sel = _labels_upa.index(_empresa_sel)
            _val_centro = _values_upa[_idx_sel]
            _pct_sel = (_val_centro / _total_upa * 100) if _total_upa > 0 else 0
            _txt_centro = f"<b>{_val_centro}</b>"
            _info_banner = (_empresa_sel, _val_centro, _pct_sel)

        fig_rosca_upa = go.Figure(data=[go.Pie(
            labels=_labels_upa,
            values=_values_upa,
            hole=0.55,
            textinfo='percent+value',
            pull=[0.08 if l == _empresa_sel else 0 for l in _labels_upa],
            hovertemplate='<b>%{label}</b><br>Unidades: %{value}<br>%{percent}<extra></extra>',
        )])
        fig_rosca_upa.update_traces(textfont=dict(color='white', size=12))

        altura_base = 420
        altura_extra = max(0, len(_labels_upa) - 10) * 12
        altura_final = min(900, altura_base + altura_extra)

        fig_rosca_upa.update_layout(
            height=altura_final,
            dragmode=False,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.05,
                xanchor="center",
                x=0.5,
                font=dict(color='white', size=11),
                bgcolor='rgba(0,35,59,0.6)',
                itemwidth=30
            ),
            margin=dict(l=20, r=20, t=60, b=140),
            title={'text': 'Unidades Padrão por Empresa', 'x': 0.5,
                   'font': {'color': 'white', 'size': 18, 'family': 'Poppins'}},
            plot_bgcolor='rgba(0,35,59,0.9)',
            paper_bgcolor='rgba(0,35,59,0.9)',
            font=dict(color='white'),
            annotations=[dict(
                text=_txt_centro,
                x=0.5, y=0.5,
                font=dict(size=30, color='white', family='Poppins'),
                showarrow=False,
                xanchor='center', yanchor='middle',
            )]
        )
        st.plotly_chart(fig_rosca_upa, use_container_width=True, config={'displayModeBar': False})

        # Banner de detalhe da seleção
        if _info_banner:
            _lb, _vl, _pc = _info_banner
            st.markdown(
                f'<div style="background:#0f2a3f;border-left:4px solid #BFCF99;'
                f'padding:10px 18px;border-radius:6px;margin:4px 0 12px 0;">'
                f'<b style="color:#BFCF99;">{_lb}</b>: '
                f'<b style="color:white;font-size:1.15rem;">{_vl}</b> unidades'
                f'<span style="color:#adb5bd;margin-left:12px;">({_pc:.1f}% do total)</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        with st.expander("Detalhes do banco de dados", expanded=False):
            _df_upa_tab = pd.DataFrame([
                {'Empresa / Grupo': v['label'],
                 'Unidades Padrão': v['unidades'],
                 'Critério de contagem': v['descricao']}
                for k, v in UPA.items() if k != '__TOTAL__' and v.get('unidades', 0) > 0
            ]).sort_values('Unidades Padrão', ascending=False).reset_index(drop=True)
            if '__TOTAL__' in UPA:
                _df_upa_tab.loc[len(_df_upa_tab)] = {
                    'Empresa / Grupo': '► TOTAL GERAL',
                    'Unidades Padrão': UPA['__TOTAL__']['unidades'],
                    'Critério de contagem': UPA['__TOTAL__']['descricao'],
                }
            st.dataframe(_df_upa_tab, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum quantitativo consolidado disponível.")

    st.markdown("---")

    # ==========================================================================
    # CARDS DE MÉTRICAS EXPANSÍVEIS - CLIQUE PARA VER DETALHES
    # ==========================================================================
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.expander(f"FINALIZADOS: {finalizados}", expanded=False):
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #566E3D 0%, #6a8a4a 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h3 style="color: #FFFFFF; margin: 0;">Atividades Concluídas</h3>
                <p style="color: #BFCF99;">{finalizados} de {total_registros} ({(finalizados/total_registros*100) if total_registros > 0 else 0:.1f}%)</p>
            </div>
            """, unsafe_allow_html=True)
            if finalizados > 0 and 'STATUS' in df.columns:
                df_fin = df[df['STATUS'] == 'FINALIZADO']
                # AGRUPAR POR CLIENTE - mostrar total por cliente
                if 'CLIENTE' in df_fin.columns:
                    agrupado = df_fin.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>• <strong>{str(cliente)[:40]}</strong> | {qtd} atividades</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    with col2:
        with st.expander(f"EM EXECUÇÃO: {em_execucao}", expanded=False):
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #00233B 0%, #0a4d6f 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h3 style="color: #FFFFFF; margin: 0;">Atividades em Andamento</h3>
                <p style="color: #BFCF99;">{em_execucao} atividades ativas</p>
            </div>
            """, unsafe_allow_html=True)
            if em_execucao > 0 and 'STATUS' in df.columns:
                df_exec = df[df['STATUS'].isin(['EM ANDAMENTO', 'EM EXECUÇÃO'])]
                # AGRUPAR POR CLIENTE - mostrar total por cliente
                if 'CLIENTE' in df_exec.columns:
                    agrupado = df_exec.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>• <strong>{str(cliente)[:40]}</strong> | {qtd} atividades</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    with col3:
        with st.expander(f"AGUARDANDO REC.: {aguardando}", expanded=False):
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #713f12 0%, #854d0e 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h3 style="color: #fef08a; margin: 0;">Aguardando Recebimento</h3>
                <p style="color: #fef08a;">{aguardando} pendentes</p>
            </div>
            """, unsafe_allow_html=True)
            if aguardando > 0 and not aguardando_df.empty:
                # AGRUPAR POR CLIENTE - mostrar total por cliente
                if 'CLIENTE' in aguardando_df.columns:
                    agrupado = aguardando_df.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>• <strong>{str(cliente)[:40]}</strong> | {qtd} pendências</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    with col4:
        cor_vencido = '#dc2626' if vencidos > 0 else '#374151'
        with st.expander(f"VENCIDOS: {vencidos}", expanded=vencidos > 0):
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {cor_vencido} 0%, #991b1b 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h3 style="color: #fecaca; margin: 0;">Ação Urgente Necessária!</h3>
                <p style="color: #fecaca;">{vencidos} atividades vencidas</p>
            </div>
            """, unsafe_allow_html=True)
            if vencidos > 0 and not vencidos_df.empty:
                # AGRUPAR POR CLIENTE - mostrar total por cliente
                if 'CLIENTE' in vencidos_df.columns:
                    agrupado = vencidos_df.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>🔴 <strong>{str(cliente)[:40]}</strong> | {qtd} vencidos</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Segunda linha de métricas EXPANSÍVEIS
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        with st.expander(f"URGENTES: {urgentes}", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h4 style="color: #FFFFFF; margin: 0;">Prazo: Próximos 7 dias</h4>
            </div>
            """, unsafe_allow_html=True)
            if urgentes > 0 and 'STATUS_PRAZO' in df.columns:
                df_urg = df[df['STATUS_PRAZO'] == 'URGENTE']
                # AGRUPAR POR CLIENTE
                if 'CLIENTE' in df_urg.columns:
                    agrupado = df_urg.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>• <strong>{str(cliente)[:40]}</strong> | ⏰ {qtd} urgentes</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    with col6:
        with st.expander(f"ATENÇÃO: {atencao}", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, #00233B 0%, #0a3d5f 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h4 style="color: #BFCF99; margin: 0;">Prazo: Próximos 30 dias</h4>
            </div>
            """, unsafe_allow_html=True)
            if atencao > 0 and 'STATUS_PRAZO' in df.columns:
                df_atenc = df[df['STATUS_PRAZO'] == 'ATENÇÃO']
                # AGRUPAR POR CLIENTE
                if 'CLIENTE' in df_atenc.columns:
                    agrupado = df_atenc.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>• <strong>{str(cliente)[:40]}</strong> | ⏰ {qtd} atenção</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    with col7:
        with st.expander(f"COM MATERIAL: {com_material}", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, #566E3D 0%, #6a8a4a 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h4 style="color: #FFFFFF; margin: 0;">Material Recebido</h4>
            </div>
            """, unsafe_allow_html=True)
            if com_material > 0 and 'TEM_MATERIAL' in df.columns:
                df_mat = df[df['TEM_MATERIAL'] == True]
                # AGRUPAR POR CLIENTE
                if 'CLIENTE' in df_mat.columns:
                    agrupado = df_mat.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>• <strong>{str(cliente)[:40]}</strong> | 🧪 {qtd} materiais</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    with col8:
        with st.expander(f"📭 SEM MATERIAL: {sem_material}", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, #BFCF99 0%, #a8c080 100%); padding: 1rem; border-radius: 8px; margin-bottom: 10px;">
                <h4 style="color: #00233B; margin: 0;">Aguardando Recebimento</h4>
            </div>
            """, unsafe_allow_html=True)
            if sem_material > 0 and 'TEM_MATERIAL' in df.columns:
                df_sem = df[(df['TEM_MATERIAL'] == False) & (df['STATUS'] != 'FINALIZADO')]
                # AGRUPAR POR CLIENTE
                if 'CLIENTE' in df_sem.columns:
                    agrupado = df_sem.groupby('CLIENTE').size().sort_values(ascending=False)
                    scroll_html = '<div style="max-height: 300px; overflow-y: auto; padding: 10px; background: rgba(0,35,59,0.5); border-radius: 8px;">'
                    for cliente, qtd in agrupado.items():
                        scroll_html += f"<p style='margin: 5px 0; color: #FFFFFF;'>• <strong>{str(cliente)[:40]}</strong> | 📭 {qtd} pendentes</p>"
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Seção de Alertas Dinâmicos
    if vencidos > 0 or urgentes > 0:
        with st.expander("🚨 ALERTAS CRÍTICOS - CLIQUE PARA VER DETALHES", expanded=True):
            
            if vencidos > 0 and 'STATUS_PRAZO' in df.columns:
                st.markdown("### ⚠️ Atividades VENCIDAS (Ação Imediata Necessária)")
                df_vencidos = df[df['STATUS_PRAZO'] == 'VENCIDO']
                
                # AGRUPAR POR CLIENTE
                if 'CLIENTE' in df_vencidos.columns:
                    agrupado = df_vencidos.groupby('CLIENTE').agg({
                        'DIAS_VENCIMENTO': 'min'  # Pior caso (mais dias de atraso)
                    }).reset_index()
                    agrupado['QTD'] = df_vencidos.groupby('CLIENTE').size().values
                    agrupado = agrupado.sort_values('DIAS_VENCIMENTO').head(10)
                    
                    for _, row in agrupado.iterrows():
                        cliente = str(row['CLIENTE'])[:45]
                        qtd = row['QTD']
                        dias = abs(row['DIAS_VENCIMENTO']) if pd.notna(row['DIAS_VENCIMENTO']) else 0
                        
                        st.markdown(f"""
                        <div style="background: rgba(220,38,38,0.2); padding: 0.8rem; margin: 0.5rem 0; 
                                    border-radius: 8px; border-left: 4px solid #dc2626;">
                            <strong style="color: #dc2626;">🏢 {cliente}</strong> | 
                            <span style="color: #FFFFFF;">📋 {qtd} atividades</span> | 
                            <span style="color: #f59e0b;">⏰ Até {dias:.0f} dias de atraso</span>
                        </div>
                        """, unsafe_allow_html=True)
            
            if urgentes > 0 and 'STATUS_PRAZO' in df.columns:
                st.markdown("### 🔥 Atividades URGENTES (Próximos 7 dias)")
                df_urgentes = df[df['STATUS_PRAZO'] == 'URGENTE']
                
                # AGRUPAR POR CLIENTE
                if 'CLIENTE' in df_urgentes.columns:
                    agrupado = df_urgentes.groupby('CLIENTE').agg({
                        'DIAS_VENCIMENTO': 'min'  # Menor prazo
                    }).reset_index()
                    agrupado['QTD'] = df_urgentes.groupby('CLIENTE').size().values
                    agrupado = agrupado.sort_values('DIAS_VENCIMENTO').head(10)
                    
                    for _, row in agrupado.iterrows():
                        cliente = str(row['CLIENTE'])[:45]
                        qtd = row['QTD']
                        dias = row['DIAS_VENCIMENTO'] if pd.notna(row['DIAS_VENCIMENTO']) else 0
                        
                        st.markdown(f"""
                        <div style="background: rgba(245,158,11,0.2); padding: 0.8rem; margin: 0.5rem 0; 
                                    border-radius: 8px; border-left: 4px solid #f59e0b;">
                            <strong style="color: #f59e0b;">🏢 {cliente}</strong> | 
                            <span style="color: #FFFFFF;">📋 {qtd} atividades</span> | 
                            <span style="color: #BFCF99;">⏰ Até {dias:.0f} dias restantes</span>
                        </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================================================================================
    # 🏗️  SEÇÃO PROJETOS — VERSÃO ROBUSTA
    # ==================================================================================
    # FLUXO:
    #   1ª ETAPA → Varredura dos 6 diretórios de rede (fonte primária)
    #   2ª ETAPA → FORM 022A Coluna M (enriquecimento + A_INICIAR)
    #   3ª ETAPA → Concatenação: pasta existe → fases reais | só no FORM → 🔲 A INICIAR
    #
    # Caminhos dos diretórios:
    #   0.2 PROJETOS CAUQ MARSHALL | 0.3 PROJETOS CAUQ SUPERPAVE
    #   0.4 PROJETOS MRAF          | 0.5 PROJETOS SOLO CIMENTO
    #   0.6 PROJETOS CAMADAS GRANULARES | 0.7 PROJETOS BGS
    #
    # Mapeamento Coluna M → Tipo:
    #   "PROJETO CAUQ"     → CAUQ_MARSHALL  (CAUQ = Marshall)
    #   "PROJETO MARSHALL" → CAUQ_MARSHALL
    #   "PROJETO BGS"      → BGS
    #   "PROJETO MRAF"     → MRAF
    # ==================================================================================

    # ── Filtro Compasa do banco para cruzamento de PTs ───────────────────────────────
    df_compasa_db = df[df['CLIENTE'].str.contains('COMPASA', na=False, case=False)]

    # ── Varredura única robusta — cobre os 6 tipos e os 2 painéis ────────────────────
    if 'df_todos_proj_cache' in st.session_state:
        df_todos_proj = st.session_state['df_todos_proj_cache']
    else:
        with st.spinner("🔍 Varrendo diretórios de projetos na rede e cruzando com FORM 022A..."):
            df_todos_proj = escanear_todos_projetos(df_compasa_db)
        st.session_state['df_todos_proj_cache'] = df_todos_proj

    # ── Separação por seção ───────────────────────────────────────────────────────────
    df_proj_externos = df_todos_proj[df_todos_proj['CLASSIFICACAO'] != 'COMPASA']  if not df_todos_proj.empty else pd.DataFrame()

    # Atualizar UPA com projetos externos reais
    UPA = st.session_state.get('UPA', {})
    if 'PROJETOS_EXTERNOS' in UPA:
        UPA['PROJETOS_EXTERNOS']['unidades'] = len(df_proj_externos) if not df_proj_externos.empty else 0
        UPA['__TOTAL__']['unidades'] = sum(v['unidades'] for k, v in UPA.items() if k != '__TOTAL__')
        st.session_state['UPA'] = UPA

    # Ordem das abas e config de cada tipo
    _TIPOS_ABAS = [
        ('CAUQ_MARSHALL',      'Marshall'),
        ('CAUQ_SUPERPAVE',     'Superpave'),
        ('BGS',                'BGS'),
        ('MRAF',               'MRAF'),
        ('CAMADAS_GRANULARES', 'Cam. Granulares'),
        ('SOLO_CIMENTO',       'Solo Cimento'),
    ]

    # ── Helper: renderiza os cards de uma aba ────────────────────────────────────────
    def _render_cards_projetos(df_tipo, tipo_key, is_compasa=True):
        """
        Renderiza os cards de projeto para um tipo específico.

        STATUS possíveis:
          OK          → projeto concluído (tem PDF)
          ANDAMENTO   → em execução (tem Excel, sem PDF)
          AGUARDANDO  → aguardando amostras
          VAZIO       → pasta existe mas sem arquivos
          A_INICIAR   → FORM 022A registrou projeto, mas PASTA NÃO EXISTE na rede
        """
        if df_tipo.empty:
            st.info("Nenhum projeto localizado para este tipo.")
            return

        tem_pioneiro = TIPOS_PROJETO_CONFIG.get(tipo_key, {}).get('tem_pioneiro', True)

        # ── Separar A_INICIAR dos demais para exibição diferenciada ──────────
        df_iniciados  = df_tipo[df_tipo['STATUS'] != 'A_INICIAR']
        df_a_iniciar  = df_tipo[df_tipo['STATUS'] == 'A_INICIAR']

        # ── 1. Cards normais (projetos com pasta na rede) ─────────────────────
        for _, row in df_iniciados.iterrows():
            _status = row.get('STATUS', 'VAZIO')

            # Ícone e cores por status
            if _status == 'OK':
                _ic, _bg, _tx = "✅", "#dcfce7", "#166534"
            elif _status == 'ANDAMENTO':
                _ic, _bg, _tx = "⏳", "#fef9c3", "#854d0e"
            elif _status == 'AGUARDANDO':
                _ic, _bg, _tx = "🟡", "#fff7ed", "#9a3412"
            else:
                _ic, _bg, _tx = "📁", "#f3f4f6", "#6b7280"

            _cli     = row.get('CLIENTE') or ('COMPASA DO BRASIL' if is_compasa else '—')
            _ped     = row.get('PEDREIRA') or '—'
            _classif_badge = {'COMPASA': '🏗️ COMPASA', 'CC': '🔁 CC', 'EXTERNO': '🌐 EXTERNO'}.get(
                row.get('CLASSIFICACAO', 'EXTERNO'), '🌐 EXTERNO'
            )
            _n_mat       = row.get('N_MATERIAIS', 0)
            _st_form     = row.get('STATUS_FORM', '')
            _st_form_label = {
                'CONCLUIDO': '✅ Lab concluído',
                'ANDAMENTO': '⏳ Lab em andamento',
                'AGUARDANDO': '🟡 Aguardando amostras',
            }.get(_st_form, _st_form)

            _titulo_exp = (
                f"{_ic} PT {row.get('CODIGO', '—')} — {str(_cli)[:30]} | {str(_ped)[:25]} "
                f"| {_n_mat} mat. | {_st_form_label}"
            )

            with st.expander(_titulo_exp, expanded=False):
                # ── Fases ────────────────────────────────────────────────────
                if tem_pioneiro:
                    _fases = [('COMP', 'Composição'), ('PION', 'Pioneiro'), ('PROJ', 'Projeto')]
                else:
                    _fases = [('COMP', 'Composição'), ('PROJ', 'Projeto')]

                _fases_exib = [(fk, fl) for fk, fl in _fases if row.get(f'STATUS_{fk}') != 'NAO_APLICAVEL']
                if _fases_exib:
                    _cols_fase = st.columns(len(_fases_exib))
                    for idx_f, (fk, fl) in enumerate(_fases_exib):
                        st_f = row.get(f'STATUS_{fk}', 'VAZIO')
                        if st_f == 'OK':
                            ic_f, bg_f, tx_f, lbl_f = "✅", "#dcfce7", "#166534", "Concluído"
                        elif st_f == 'ANDAMENTO':
                            ic_f, bg_f, tx_f, lbl_f = "⏳", "#fef9c3", "#854d0e", "Em andamento"
                        elif st_f == 'AGUARDANDO':
                            ic_f, bg_f, tx_f, lbl_f = "🟡", "#fff7ed", "#9a3412", "Aguardando"
                        else:
                            ic_f, bg_f, tx_f, lbl_f = "⬜", "#f3f4f6", "#64748b", "Sem arquivo"
                        with _cols_fase[idx_f]:
                            st.markdown(
                                f'<div style="background:{bg_f};padding:8px;border-radius:5px;'
                                f'text-align:center;border:1px solid {tx_f};">'
                                f'<div style="font-size:18px;">{ic_f}</div>'
                                f'<div style="color:{tx_f};font-weight:bold;font-size:0.8rem;">{fl.upper()}</div>'
                                f'<div style="color:{tx_f};font-size:0.7rem;">{lbl_f}</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                st.markdown("")

                # ── Duas colunas ──────────────────────────────────────────────
                _col_m1, _col_m2 = st.columns(2)
                with _col_m1:
                    st.markdown("**📋 Dados do Projeto**")
                    st.markdown(f"**PT/Protocolo:** `{row.get('CODIGO', '—')}`")
                    st.markdown(f"**Cliente:** {_cli}")
                    st.markdown(f"**Pedreira:** {_ped}")
                    if row.get('MISTURA'):
                        st.markdown(f"**Mistura:** {row['MISTURA']}")
                    if row.get('CODIGO_OBS'):
                        st.markdown(f"**Cód. Projeto:** `{row['CODIGO_OBS']}`")
                    st.markdown(f"**Classificação:** {_classif_badge}")

                with _col_m2:
                    st.markdown("**🔬 Dados do FORM 022A**")
                    st.markdown(f"**Finalidade (Col M):** {row.get('FINALIDADE_RAW') or '—'}")
                    st.markdown(f"**Status Lab:** {_st_form_label}")
                    st.markdown(f"**Materiais ({_n_mat}):**")
                    if row.get('MATERIAIS'):
                        for mat in str(row['MATERIAIS']).split(', '):
                            if mat.strip() and mat.strip().lower() not in ('nan', ''):
                                st.caption(f"  • {mat.strip()}")
                    if row.get('OBS') and str(row['OBS']) not in ('-', 'N.I', 'nan', ''):
                        st.markdown(f"**OBS:** {row['OBS']}")
                    if pd.notna(row.get('DATA_RECEBIMENTO')):
                        try:
                            dt_str = pd.Timestamp(row['DATA_RECEBIMENTO']).strftime('%d/%m/%Y')
                            st.markdown(f"**Recebimento:** {dt_str}")
                        except Exception:
                            pass

                # ── Arquivos nas pastas ──────────────────────────────────────
                arqs_str = []
                for fk, fl in [('COMP', 'Comp'), ('PION', 'Pion'), ('PROJ', 'Proj')]:
                    arq = row.get(f'ARQUIVO_{fk}')
                    if arq:
                        arqs_str.append(f"📁 {fl}: {arq}")
                if arqs_str:
                    st.caption(' | '.join(arqs_str))
                st.markdown(f"**PDF:** {'📄 Disponível ✅' if row.get('TEM_PDF') else '📝 Não gerado ainda'}")

        # ── 2. Bloco A_INICIAR — projetos solicitados mas sem pasta na rede ──
        if not df_a_iniciar.empty:
            st.markdown("")
            st.markdown(
                f'<div style="background:#f1f5f9;border-left:4px solid #64748b;'
                f'padding:8px 12px;border-radius:4px;margin:8px 0;">'
                f'<span style="color:#475569;font-weight:bold;">🔲 A INICIAR ({len(df_a_iniciar)})</span>'
                f'<span style="color:#64748b;font-size:0.82rem;margin-left:8px;">'
                f'Projetos registrados no FORM 022A mas sem pasta criada na rede</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            for _, row in df_a_iniciar.iterrows():
                _cli = row.get('CLIENTE') or ('COMPASA DO BRASIL' if is_compasa else '—')
                _ped = row.get('PEDREIRA') or '—'
                _n_mat = row.get('N_MATERIAIS', 0)
                _titulo_ai = (
                    f"🔲 PT {row.get('CODIGO', '—')} — {str(_cli)[:30]} | {str(_ped)[:25]} "
                    f"| {_n_mat} mat. | A INICIAR"
                )
                with st.expander(_titulo_ai, expanded=False):
                    st.info(
                        "📂 **Pasta não encontrada na rede.**\n\n"
                        "O FORM 022A indica que este projeto foi solicitado, "
                        "mas ainda **não possui diretório criado** na rede. "
                        "Assim que a pasta for criada e os arquivos forem salvos, "
                        "o status será atualizado automaticamente.",
                        icon="🔲"
                    )

                    # Fases → todas A INICIAR
                    if tem_pioneiro:
                        _fases_ai = [('COMP', 'Composição'), ('PION', 'Pioneiro'), ('PROJ', 'Projeto')]
                    else:
                        _fases_ai = [('COMP', 'Composição'), ('PROJ', 'Projeto')]
                    _cols_ai = st.columns(len(_fases_ai))
                    for idx_ai, (_, fl_ai) in enumerate(_fases_ai):
                        with _cols_ai[idx_ai]:
                            st.markdown(
                                f'<div style="background:#f1f5f9;padding:8px;border-radius:5px;'
                                f'text-align:center;border:1px solid #94a3b8;">'
                                f'<div style="font-size:18px;">🔲</div>'
                                f'<div style="color:#475569;font-weight:bold;font-size:0.8rem;">{fl_ai.upper()}</div>'
                                f'<div style="color:#94a3b8;font-size:0.7rem;">A iniciar</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                    st.markdown("")
                    _col_ai1, _col_ai2 = st.columns(2)
                    with _col_ai1:
                        st.markdown("**📋 Dados do Projeto**")
                        st.markdown(f"**PT/Protocolo:** `{row.get('CODIGO', '—')}`")
                        st.markdown(f"**Cliente:** {_cli}")
                        st.markdown(f"**Pedreira:** {_ped}")
                    with _col_ai2:
                        st.markdown("**🔬 Dados do FORM 022A**")
                        st.markdown(f"**Finalidade (Col M):** {row.get('FINALIDADE_RAW') or '—'}")
                        st.markdown(f"**Materiais ({_n_mat}):**")
                        if row.get('MATERIAIS'):
                            for mat in str(row['MATERIAIS']).split(', '):
                                if mat.strip() and mat.strip().lower() not in ('nan', ''):
                                    st.caption(f"  • {mat.strip()}")
                        if pd.notna(row.get('DATA_RECEBIMENTO')):
                            try:
                                dt_str = pd.Timestamp(row['DATA_RECEBIMENTO']).strftime('%d/%m/%Y')
                                st.markdown(f"**Recebimento:** {dt_str}")
                            except Exception:
                                pass

    # ==================================================================================
    # 📌 PAINEL CONFERÊNCIA — PIONEIROS SEM COMPOSIÇÃO OU COM PDF 'PROJ'
    # ==================================================================================
    if not df_todos_proj.empty and 'FLAG_CONFERENCIA' not in df_todos_proj.columns:
        df_todos_proj['FLAG_CONFERENCIA'] = False
    df_conferencia = df_todos_proj[df_todos_proj['FLAG_CONFERENCIA'] == True] if not df_todos_proj.empty else pd.DataFrame()
    if not df_conferencia.empty:
        st.markdown("## 📌 Conferência (Pioneiro)")
        st.caption("Pioneiros sem composição associada ou com PDF contendo 'PROJ'.")
        st.metric("Projetos em conferência", len(df_conferencia))

        cols_conf = [c for c in ['CODIGO', 'PEDREIRA', 'TIPO_PROJETO', 'STATUS', 'TEM_PDF', 'PASTA'] if c in df_conferencia.columns]
        if cols_conf:
            st.dataframe(df_conferencia[cols_conf].reset_index(drop=True), use_container_width=True, hide_index=True)
    else:
        st.caption("Nenhum item em conferência encontrado.")

    st.markdown("---")

    # ==================================================================================
    # 🌐 PAINEL B — PROJETOS EXTERNOS (EMPRESA ≠ COMPASA)
    # CC = EPR, CBB, Asfaltec, Strata, Eixo SP → contratos contínuos internos
    # EXTERNO = DER, DNIT, construtoras, outros
    # ==================================================================================
    st.markdown("## Projetos")
    st.caption(
        "Projetos rastreados nas pastas da rede. "
    )

    if df_proj_externos.empty:
        st.info("Nenhum projeto externo localizado. Verifique a conexão com a rede.")
    else:
        # ── Unidade_Padrão_atividades: cada projeto = 1 unidade ──────────────
        _upa_ext = len(df_proj_externos)
        st.markdown(
            f'<div style="background:#0f2a3f;border-left:4px solid #566E3D;'
            f'padding:8px 14px;border-radius:4px;margin:4px 0 10px 0;">'
            f'<span style="color:#adb5bd;font-size:0.82rem;margin-left:12px;">'
            f'Cada projeto = 1 unidade | Total: <b style="color:#BFCF99">{_upa_ext}</b></span>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Métricas gerais Externos
        _ext_puro  = len(df_proj_externos[df_proj_externos['CLASSIFICACAO'] == 'EXTERNO'])
        _cc_count  = len(df_proj_externos[df_proj_externos['CLASSIFICACAO'] == 'CC'])
        _ok_ext    = len(df_proj_externos[df_proj_externos['STATUS'] == 'OK'])
        _and_ext   = len(df_proj_externos[df_proj_externos['STATUS'] == 'ANDAMENTO'])
        _ai_ext    = len(df_proj_externos[df_proj_externos['STATUS'] == 'A_INICIAR'])

        _e1, _e2, _e3, _e4, _e5, _e6 = st.columns(6)
        _e1.metric("Total Externos",    len(df_proj_externos))
        _e2.metric("Externos puros", _ext_puro)
        _e3.metric("CC (internos)",  _cc_count)
        _e4.metric("Concluídos",     _ok_ext)
        _e5.metric("Em andamento",   _and_ext)
        _e6.metric("A iniciar",      _ai_ext)

        # Filtro EXTERNO / CC / Todos
        _filtro_ext = st.radio(
            "Filtrar por:", ["Todos", "Somente Externos", "Somente CC"],
            horizontal=True, key="filtro_ext_painel"
        )
        if _filtro_ext == "Somente Externos":
            df_ext_exib = df_proj_externos[df_proj_externos['CLASSIFICACAO'] == 'EXTERNO']
        elif _filtro_ext == "Somente CC":
            df_ext_exib = df_proj_externos[df_proj_externos['CLASSIFICACAO'] == 'CC']
        else:
            df_ext_exib = df_proj_externos.copy()

        # Abas por tipo
        _nomes_abas_ext = [label for _, label in _TIPOS_ABAS]
        _tabs_ext = st.tabs(_nomes_abas_ext)

        for idx_t, (tipo_key, _) in enumerate(_TIPOS_ABAS):
            with _tabs_ext[idx_t]:
                _df_tipo_ext = df_ext_exib[df_ext_exib['TIPO_PROJETO'] == tipo_key]
                _render_cards_projetos(_df_tipo_ext, tipo_key, is_compasa=False)

        # Tabela completa expansível
        with st.expander("Detalhes do banco de dados de Projetos", expanded=False):
            _cols_ext = ['CODIGO', 'CLIENTE', 'PEDREIRA', 'MISTURA', 'ANO_PASTA',
                         'TIPO_LABEL', 'STATUS', 'TEM_PDF', 'CLASSIFICACAO']
            st.dataframe(
                df_ext_exib[[c for c in _cols_ext if c in df_ext_exib.columns]],
                use_container_width=True, hide_index=True
            )

    st.markdown("---")

    # ==================================================================================
    #  GRÁFICO DE ATIVIDADES POR CLIENTE (HORIZONTAL + EXPANDER + DINÂMICO)
    # ==================================================================================
    st.markdown("## ATIVIDADES POR CLIENTE")

    # Filtra apenas atividades ativas (não finalizadas/canceladas)
    df_ativos = df[~df['STATUS'].isin(['FINALIZADO', 'CANCELADO', 'CONCLUÍDO'])]

    # Banner local: soma QUANTIDADE (Col H) ou contagem de registros do subconjunto
    _upa_ativos_top = _soma_quantidade(df_ativos)
    render_banner_unidade_padrao_local(
        _upa_ativos_top,
        "Atividades em andamento — soma COL H (QUANTIDADE FORM 022A)",
        cor_borda='#BFCF99',
        cor_texto='#BFCF99',
    )

    if not df_ativos.empty:
        # Agrupamento — usa soma de QUANTIDADE (Col H FORM 022A) como Unidade Padrão,
        # com fallback para contagem de registros quando a coluna não existe
        if 'QUANTIDADE' in df_ativos.columns:
            df_counts = (
                df_ativos.groupby('CLIENTE')['QUANTIDADE']
                .apply(lambda x: pd.to_numeric(x, errors='coerce').fillna(0).sum())
                .reset_index(name='QTD')
            )
            _eixo_x_label = "Unidade Padrão (soma QUANTIDADE FORM 022A)"
        else:
            df_counts = df_ativos['CLIENTE'].value_counts().reset_index()
            df_counts.columns = ['CLIENTE', 'QTD']
            _eixo_x_label = "Contagem de registros"

        # ── Correção UPA: alinhar QTD dos clientes CC com "Quantitativos por Empresa" ──
        # Proporção ativa (não-finalizado) do SQLite é aplicada ao total UPA (raw Excel),
        # garantindo consistência com o gráfico de rosca.
        _UPA_h = st.session_state.get('UPA', {})
        _upa_cc_h = {
            v['label']: v['unidades']
            for k, v in _UPA_h.items()
            if k.startswith('CC_') and v.get('unidades', 0) > 0
        }
        if _upa_cc_h and not df_counts.empty and 'QUANTIDADE' in df.columns:
            # Total QUANTIDADE por cliente no SQLite (todos os status, incluindo finalizados)
            _sql_total_cli = (
                df.groupby('CLIENTE')['QUANTIDADE']
                .apply(lambda x: pd.to_numeric(x, errors='coerce').fillna(0).sum())
                .to_dict()
            )
            for _cc_lbl_h, _cc_upa_h in _upa_cc_h.items():
                _bkw_h = _cc_lbl_h[:12].strip().upper()
                _msk_h = df_counts['CLIENTE'].astype(str).str.upper().str.contains(
                    _bkw_h, na=False, regex=False
                )
                if not _msk_h.any():
                    continue
                for _ih in df_counts[_msk_h].index:
                    _cli_h = df_counts.at[_ih, 'CLIENTE']
                    _total_sql_h = float(_sql_total_cli.get(_cli_h, 0))
                    _ativo_sql_h = float(df_counts.at[_ih, 'QTD'])
                    if _total_sql_h > 0:
                        # Proporção ativa × total UPA raw = QTD corrigida
                        df_counts.at[_ih, 'QTD'] = round(_cc_upa_h * (_ativo_sql_h / _total_sql_h))

        df_counts = df_counts.sort_values('QTD', ascending=True)

        with st.expander(" Ver Gráfico de Atividades em Andamento", expanded=True):
            # Altura dinâmica: Mínimo 200px + 30px por cliente
            altura_grafico = 200 + (len(df_counts) * 30)

            fig_barras = px.bar(
                df_counts,
                x='QTD',
                y='CLIENTE',
                orientation='h',
                text='QTD',
                color='QTD',
                color_continuous_scale=['#3b82f6', '#1d4ed8']
            )

            fig_barras.update_layout(
                height=altura_grafico,
                dragmode=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                xaxis=dict(showgrid=True, gridcolor='#334155', title=_eixo_x_label, fixedrange=True),
                yaxis=dict(title=None, fixedrange=True),
                margin=dict(l=0, r=0, t=30, b=0)
            )

            st.plotly_chart(fig_barras, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Nenhuma atividade em andamento no momento.")

    st.markdown("---")
    
    # ==================================================================================
    # SIDEBAR (FILTROS AVANÇADOS) - Continuação
    # ==================================================================================
    
    # ==================================================================================
    # MÉTRICAS PRINCIPAIS
    # ==================================================================================
    st.markdown("## Propostas Comerciais - FAS")
    st.markdown("PC FAS - Diretório e FORM 045")

    # Usar df_fas_sidebar (filtrado pelos filtros globais) para que responda à sidebar
    if df_fas_sidebar.empty:
        st.warning("Não há FAS registradas para os filtros atuais.")
    else:
        fas_total      = len(df_fas_sidebar['PC'].unique())
        servicos_total = len(df_fas_sidebar)
        fas_finalizadas = df_fas_sidebar[df_fas_sidebar['STATUS_FAS'] == 'FINALIZADO']['PC'].nunique()

        # ── Unidade_Padrão_atividades: cada ensaio de uma FAS = 1 unidade ────
        _upa_fas = int(df_fas_sidebar['QUANTIDADE'].sum()) if 'QUANTIDADE' in df_fas_sidebar.columns else servicos_total
        st.markdown(
            f'<div style="background:#0f2a3f;border-left:4px solid #3b82f6;'
            f'padding:8px 14px;border-radius:4px;margin:4px 0 10px 0;">'
            f'<span style="color:#adb5bd;font-size:0.82rem;margin-left:12px;">'
            f'Total ensaios: '
            f'<b style="color:#93c5fd">{_upa_fas}</b> | FAS: {fas_total}'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        col_info, col_export = st.columns([3,1])
        with col_info:
            col_metrics = st.columns(3)
            with col_metrics[0]:
                st.metric("Total de FAS", fas_total)
            with col_metrics[1]:
                st.metric("Serviços catalogados", servicos_total)
            with col_metrics[2]:
                st.metric("FAS Finalizadas", fas_finalizadas)
        with col_export:
            if st.button("📥 Exportar FAS Consolidada", key="export_fas"):
                st.download_button(
                    "Baixar CSV", df_fas.to_csv(index=False).encode('utf-8'),
                    "fas_consolidadas.csv", key="fas_csv"
                )

        filtros_fas = st.columns(4)
        with filtros_fas[0]:
            status_sel = st.multiselect(
                "Status FAS", sorted(df_fas['STATUS_FAS'].dropna().unique()),
                default=sorted(df_fas['STATUS_FAS'].dropna().unique())
            )
        with filtros_fas[1]:
            cliente_sel = st.multiselect(
                "Clientes", sorted(df_fas['CLIENTE'].dropna().astype(str).unique())
            )
        with filtros_fas[2]:
            servicos_sel = st.multiselect(
                "Serviços", sorted(df_fas['SERVICO'].dropna().astype(str).unique())
            )
        with filtros_fas[3]:
            origem_sel = st.multiselect(
                "Origem", sorted(df_fas['ORIGEM'].dropna().unique()),
                default=sorted(df_fas['ORIGEM'].dropna().unique())
            )

        df_fas_filtrado = df_fas_sidebar.copy()
        if status_sel:
            df_fas_filtrado = df_fas_filtrado[df_fas_filtrado['STATUS_FAS'].isin(status_sel)]
        if cliente_sel:
            df_fas_filtrado = df_fas_filtrado[df_fas_filtrado['CLIENTE'].isin(cliente_sel)]
        if servicos_sel:
            df_fas_filtrado = df_fas_filtrado[df_fas_filtrado['SERVICO'].isin(servicos_sel)]
        if origem_sel:
            df_fas_filtrado = df_fas_filtrado[df_fas_filtrado['ORIGEM'].isin(origem_sel)]

        status_prioridade = {
            'EM ANDAMENTO': 0,
            'EM EXECUÇÃO': 0,
            'AGUARDANDO MATERIAL': 1,
            'AGUARDANDO APROVAÇÃO': 2,
            'URGENTE': 3,
            'NO PRAZO': 3,
            'VENCIDO': 4,
            'FINALIZADO': 99
        }
        df_fas_filtrado['STATUS_ORDER'] = df_fas_filtrado['STATUS_FAS'].apply(
            lambda s: status_prioridade.get(str(s).upper(), 50)
        )

        st.markdown("---")
        dist_status = (
            df_fas_filtrado.groupby('STATUS_FAS')['PC']
            .nunique()
            .reset_index(name='TOTAL_FAS')
            .sort_values('STATUS_FAS')
        )
        if not dist_status.empty:
            fig_fas = px.pie(
                dist_status,
                values='TOTAL_FAS',
                names='STATUS_FAS',
                hole=0.55,
                title='Distribuição de FAS por Status'
            )
            fig_fas.update_traces(textinfo='value+percent', hovertemplate='%{label}: %{value} FAS<extra></extra>')
            fig_fas.update_layout(showlegend=True, margin=dict(t=60, b=10, l=10, r=10))
            st.plotly_chart(fig_fas, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")
        agrupamento = (
            df_fas_filtrado.groupby(['STATUS_FAS']).size().reset_index(name='TOTAL')
            .assign(ORDER=lambda d: d['STATUS_FAS'].apply(lambda s: status_prioridade.get(str(s).upper(), 50)))
            .sort_values('ORDER')
        )
        if not agrupamento.empty:
            st.write("Resumo por status")
            st.dataframe(agrupamento[['STATUS_FAS', 'TOTAL']], use_container_width=True, hide_index=True)

        st.markdown("---")
        pcs_ordenados = sorted(
            df_fas_filtrado['PC'].unique(),
            key=lambda pc: df_fas_filtrado[df_fas_filtrado['PC'] == pc]['STATUS_ORDER'].min()
        )

        for pc in pcs_ordenados:
            grupo = df_fas_filtrado[df_fas_filtrado['PC'] == pc]
            status_pc = grupo.iloc[0]['STATUS_FAS']
            cliente_pc = grupo.iloc[0]['CLIENTE']
            data_aceite_pc = grupo.iloc[0]['DATA_ACEITE']
            data_receb_pc = grupo.iloc[0]['DATA_RECEBIMENTO']
            data_entrega_pc = grupo.iloc[0]['DATA_ENTREGA']
            obs_pc = grupo.iloc[0]['OBS_RECEBIMENTO']

            header = f"**{pc}** - {cliente_pc or 'Cliente não informado'} | Status: **{status_pc}**"
            if pd.notna(data_entrega_pc):
                header += f" | Entrega: {pd.to_datetime(data_entrega_pc).strftime('%d/%m/%Y')}"

            with st.expander(header):
                col_left, col_right = st.columns([2,1])
                with col_left:
                    st.markdown("#### Serviços / Ensaios")
                    st.dataframe(
                        grupo[['SERVICO', 'NORMA', 'QUANTIDADE']].reset_index(drop=True),
                        use_container_width=True
                    )
                with col_right:
                    st.markdown("#### Datas e Observações")
                    if pd.notna(data_aceite_pc):
                        st.markdown(f"**Aceite:** {pd.to_datetime(data_aceite_pc).strftime('%d/%m/%Y')}")
                    if pd.notna(data_receb_pc):
                        st.markdown(f"**Recebimento (022A):** {pd.to_datetime(data_receb_pc).strftime('%d/%m/%Y')}")
                    if pd.notna(data_entrega_pc):
                        st.markdown(f"**Entrega (FAS):** {pd.to_datetime(data_entrega_pc).strftime('%d/%m/%Y')}")
                    if obs_pc:
                        st.info(f"Observações: {obs_pc}")

                if grupo.iloc[0]['MATERIAL_022A']:
                    st.markdown(f"**Materiais registrados no FORM 022A:** {grupo.iloc[0]['MATERIAL_022A']}")

    
    # --- DASHBOARD DE ATIVIDADES POR CLIENTE ---
    st.subheader("Atividades por Cliente")
    st.caption("Status das atividades separadas por cliente com análise detalhada")

    # Subconjunto ativo: remove finalizados/cancelados
    df_ativos = df[~df['STATUS'].isin(['FINALIZADO', 'CANCELADO', 'CONCLUÍDO'])] if 'STATUS' in df.columns else df.copy()

    # Unidade_Padrão local: soma QUANTIDADE (Col H) ou contagem
    if not df_ativos.empty and 'QUANTIDADE' in df_ativos.columns:
        _upa_ativos = int(pd.to_numeric(df_ativos['QUANTIDADE'], errors='coerce').fillna(0).sum())
        _desc_ativos = "Atividades em andamento — soma COL H (QUANTIDADE FORM 022A)"
    else:
        _upa_ativos = len(df_ativos)
        _desc_ativos = "Atividades em andamento — contagem de registros ativos"

    render_banner_unidade_padrao_local(_upa_ativos, _desc_ativos, cor_borda='#BFCF99', cor_texto='#BFCF99')

    col_qc1, col_qc2, col_qc3, col_qc4, col_qc5 = st.columns(5)
    
    with col_qc1:
        if st.button("Todos Clientes", key="btn_todos_cliente", use_container_width=True):
            st.session_state.filtro_cliente_selecionado = "Todos"
    with col_qc2:
        if st.button("Ativos", key="btn_ativos_cliente", use_container_width=True):
            st.session_state.mostrar_finalizados_cliente = False
    with col_qc3:
        if st.button("Finalizados", key="btn_finalizados_cliente", use_container_width=True):
            st.session_state.mostrar_finalizados_cliente = True
    with col_qc4:
        if st.button("10", key="btn_top10_cliente", use_container_width=True):
            st.session_state.limite_clientes = 10
    with col_qc5:
        if st.button("🔄 Limpar", key="btn_limpar_cliente", use_container_width=True):
            st.session_state.filtro_cliente_selecionado = "Todos"
            st.session_state.mostrar_finalizados_cliente = False
    
    # Filtros Avançados
    with st.expander("🔍 Filtros Avançados de Cliente", expanded=False):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if 'CLIENTE' in df.columns:
                clientes_disponiveis = sorted(df['CLIENTE'].dropna().unique())
                cliente_selecionado = st.selectbox(
                    "Selecione o Cliente:",
                    options=["Todos"] + clientes_disponiveis,
                    key="filtro_cliente_dashboard"
                )
            else:
                cliente_selecionado = "Todos"
        with col_f2:
            mostrar_finalizados = st.checkbox("Incluir Finalizados", value=False, key="mostrar_finalizados_cliente")
    
    # Filtrar dados por cliente
    df_cliente = df.copy()
    if cliente_selecionado != "Todos" and 'CLIENTE' in df_cliente.columns:
        df_cliente = df_cliente[df_cliente['CLIENTE'] == cliente_selecionado]
    
    if not mostrar_finalizados and 'STATUS' in df_cliente.columns:
        df_cliente = df_cliente[df_cliente['STATUS'] != 'FINALIZADO']
    
    if not df_cliente.empty:
        # Agrupar por cliente e status
        if 'CLIENTE' in df_cliente.columns and 'STATUS' in df_cliente.columns:
            # Se existir COL H (QUANTIDADE), usar soma para Unidade_Padrão_atividades; senão, contar registros
            _usa_quantidade = 'QUANTIDADE' in df_cliente.columns
            if _usa_quantidade:
                cliente_status = (
                    df_cliente.groupby(['CLIENTE', 'STATUS'])['QUANTIDADE']
                    .sum(min_count=1)
                    .reset_index(name='QUANTIDADE')
                )
                _upa_ylabel = "Unidade Padrao (soma QUANTIDADE FORM 022A)"
            else:
                cliente_status = df_cliente.groupby(['CLIENTE', 'STATUS']).size().reset_index(name='QUANTIDADE')
                _upa_ylabel = "Contagem de registros"

            # ── Correção UPA: alinhar QUANTIDADE dos clientes CC com "Quantitativos por Empresa" ──
            # O SQLite usa deduplicação por PT (1 linha/PT) enquanto o UPA usa dados brutos
            # (todos os ensaios por PT). Aqui redistribuímos proporcionalmente pelo STATUS,
            # garantindo que o total por cliente CC seja o mesmo que no gráfico de rosca.
            _UPA_local = st.session_state.get('UPA', {})
            _upa_cc_totais = {
                v['label']: v['unidades']
                for k, v in _UPA_local.items()
                if k.startswith('CC_') and v.get('unidades', 0) > 0
            }
            if _upa_cc_totais and not cliente_status.empty:
                for _cc_label, _cc_upa_total in _upa_cc_totais.items():
                    # Primeiros 12 chars do label como palavra-chave de busca (ex: 'EPR LITORAL')
                    _busca_kw = _cc_label[:12].strip().upper()
                    _cc_mask = cliente_status['CLIENTE'].astype(str).str.upper().str.contains(
                        _busca_kw, na=False, regex=False
                    )
                    if not _cc_mask.any():
                        continue
                    _atual = float(cliente_status.loc[_cc_mask, 'QUANTIDADE'].sum())
                    if _atual <= 0 or _atual == _cc_upa_total:
                        continue
                    # Redistribuição proporcional garantindo total exato
                    _idxs = cliente_status[_cc_mask].index.tolist()
                    _scale = _cc_upa_total / _atual
                    _restante = _cc_upa_total
                    for _idx in _idxs[:-1]:
                        _nv = round(float(cliente_status.at[_idx, 'QUANTIDADE']) * _scale)
                        cliente_status.at[_idx, 'QUANTIDADE'] = _nv
                        _restante -= _nv
                    cliente_status.at[_idxs[-1], 'QUANTIDADE'] = max(0, _restante)

            cores_status_cliente = {
                'FINALIZADO': '#22c55e', 'EM ANDAMENTO': '#3b82f6', 'EM EXECUÇÃO': '#60a5fa',
                'AGUARDANDO MATERIAL': '#f59e0b', 'AGUARDANDO APROVAÇÃO': '#ef4444',
                'A INICIAR': '#8b5cf6', 'A DEFINIR': '#f97316', 'CANCELADO': '#6b7280'
            }
            
            fig_cliente = px.bar(
                cliente_status.head(50),
                x='CLIENTE',
                y='QUANTIDADE',
                color='STATUS',
                color_discrete_map=cores_status_cliente,
                title=' ATIVIDADES POR CLIENTE E STATUS',
                barmode='group',
                text='QUANTIDADE'
            )
            
            fig_cliente.update_traces(
                texttemplate='<b>%{text}</b>',
                textposition='outside',
                textfont=dict(size=14, color=COR_TEXTO_TITULO),
                hovertemplate='<b style="font-size:16px">%{x}</b><br><br>' +
                              '<b>Status:</b> %{fullData.name}<br>' +
                              '<b>Quantidade:</b> %{y}<br>' +
                              '<extra></extra>',
                marker=dict(line=dict(color='rgba(255, 255, 255, 0.8)', width=2))
            )
            
            fig_cliente.update_layout(
                height=580,
                dragmode=False,
                plot_bgcolor=COR_FUNDO_CARD,
                paper_bgcolor=COR_FUNDO_CARD,
                font=dict(color=COR_TEXTO_CORPO),
                showlegend=True,
                margin=dict(t=100, b=80, l=40, r=40),
                title={
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 22, 'color': COR_TEXTO_TITULO, 'family': 'Poppins', 'weight': 'bold'}
                },
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(color='white', size=13),
                    bgcolor='rgba(0, 35, 59, 0.9)',
                    bordercolor='rgba(255, 255, 255, 0.5)',
                    borderwidth=2
                ),
                hovermode='x unified',
                hoverlabel=dict(
                    bgcolor="rgba(0, 35, 59, 0.98)",
                    font_size=15,
                    font_family="Poppins",
                    font_color="white",
                    bordercolor="rgba(255, 255, 255, 0.5)",
                    align="left"
                ),
                transition={'duration': 500}
            )
            fig_cliente.update_xaxes(
                tickfont=dict(color='white', size=11),
                tickangle=-45,
                showgrid=False,
                gridcolor='rgba(86, 110, 61, 0.2)',
                fixedrange=True
            )
            fig_cliente.update_yaxes(
                tickfont=dict(color='white', size=12),
                title_text=_upa_ylabel,
                fixedrange=True
            )

            # Configurar opções do gráfico
            st.plotly_chart(fig_cliente, use_container_width=True, config={
                'displayModeBar': False,
                'displaylogo': False,
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'atividades_cliente_status',
                    'height': 1000,
                    'width': 1600,
                    'scale': 3
                }
            })
            
            # Tabela detalhada de atividades do cliente
            if cliente_selecionado != "Todos":
                st.markdown(f"### 📋 Detalhes das Atividades - {cliente_selecionado}")
                
                colunas_exibir = ['NUMERO_PROPOSTA', 'STATUS', 'DATA_ENTREGA', 'MATERIAL', 'ENSAIO', 'DIAS_VENCIMENTO']
                colunas_disponiveis = [c for c in colunas_exibir if c in df_cliente.columns]
                
                if colunas_disponiveis:
                    df_exibir = df_cliente[colunas_disponiveis].copy()
                    
                    # Formatar data
                    if 'DATA_ENTREGA' in df_exibir.columns:
                        df_exibir['DATA_ENTREGA'] = pd.to_datetime(df_exibir['DATA_ENTREGA'], errors='coerce').dt.strftime('%d/%m/%Y')
                    
                    st.dataframe(df_exibir, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma atividade encontrada para os filtros selecionados.")
    
    st.markdown("---")
    

    # ==========================================================================
    # QUADROS ESPECÍFICOS PARA CLIENTES CC - AGRUPADOS POR TIPO DE MATERIAL
    # FONTE: df_raw_cbb_cache (FORM 022A SEM deduplicação) → soma real da COL H
    # O df_mensal vem do SQLite deduplicated (1 linha/PT), portanto NÃO pode ser
    # usado para somar QUANTIDADE — daria apenas contagem de PTs.
    # ==========================================================================
    st.markdown("---")
    st.markdown("### Quantitativo de Ensaios - Contratos Contínuos")

    # ── Obter raw SEM deduplicação, aplicando mesmo filtro de mês da sidebar ──
    df_raw_det = st.session_state.get('df_raw_cbb_cache', pd.DataFrame()).copy()

    # Se cache vazio, tentar carregar agora
    if df_raw_det.empty:
        df_raw_det = carregar_dados_epr_raw()
        if not df_raw_det.empty:
            st.session_state['df_raw_cbb_cache'] = df_raw_det

    # Aplicar filtro de mês (DATA_RECEBIMENTO) — só se sidebar selecionou mês específico
    if not df_raw_det.empty and 'DATA_RECEBIMENTO' in df_raw_det.columns:
        df_raw_det['DATA_RECEBIMENTO'] = pd.to_datetime(df_raw_det['DATA_RECEBIMENTO'], errors='coerce')
        _mes_sidebar = st.session_state.get('filtro_mes_data_recebimento', 'Todos')
        if _mes_sidebar and _mes_sidebar != 'Todos':
            # Parse "Janeiro/2026" → period
            try:
                _nomes_m = {
                    'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4,
                    'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8,
                    'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
                }
                _nm, _an = _mes_sidebar.rsplit('/', 1)
                _period_alvo = pd.Period(f"{int(_an)}-{_nomes_m[_nm]:02d}", freq='M')
                df_raw_det = df_raw_det[
                    df_raw_det['DATA_RECEBIMENTO'].dt.to_period('M') == _period_alvo
                ]
            except Exception:
                pass  # filtro inválido → mostra todos

    # Filtro de cliente da sidebar aplicado ao raw (se selecionado)
    if cliente_sel != "Todos" and not df_raw_det.empty and 'CLIENTE' in df_raw_det.columns:
        # cliente_sel pode ser string (selectbox) ou lista (multiselect em outra seção)
        if isinstance(cliente_sel, list):
            _clientes_filtro = [str(c).upper() for c in cliente_sel if pd.notna(c)]
        elif isinstance(cliente_sel, str):
            _clientes_filtro = [cliente_sel.upper()] if cliente_sel else []
        else:
            _clientes_filtro = [str(cliente_sel).upper()]

        if _clientes_filtro:
            df_raw_det = df_raw_det[
                df_raw_det['CLIENTE'].astype(str).str.upper().apply(
                    lambda nome: any(filtro in nome for filtro in _clientes_filtro)
                )
            ]

        # ── Funções de classificação de material ───────────────────────────────
        def eh_material_prioritario(texto):
            if not isinstance(texto, str):
                return False
            t = texto.upper()
            return (
                ("CAUQ" in t and "PISTA" in t) or
                ("CONCRETO" in t and "CIL" in t) or
                ("CAUQ" in t and "MASSA" in t)
            )

        def bucket_material_prioritario(texto):
            if not isinstance(texto, str):
                return texto
            t = texto.upper()
            if "CAUQ" in t and "PISTA" in t:
                return "CP - CAUQ (Pista)"
            if "CONCRETO" in t and "CIL" in t:
                return "CP - Concreto (Cilíndrico)"
            if "CAUQ" in t and "MASSA" in t:
                return "CAUQ (Massa Usinada)"
            return texto

        # ── Clientes com regra de material ────────────────────────────────────
        # STRATA / EPR LITORAL → filtrar só materiais prioritários, somar QUANTIDADE
        # EIXO SP / EPR VIAS   → sem filtro de material, somar toda QUANTIDADE
        _clientes_com_filtro_mat = ['EPR LITORAL PIONEIRO', 'EPR LITORAL PIONEIRO S.A.', 'STRATA']
        _clientes_sem_filtro_mat = ['EIXO SP', 'EPR VIAS DO CAF']  # contém match parcial

        def _soma_det(df_raw, cliente_nome, filtrar_mat=True):
            """Soma QUANTIDADE do raw para um cliente. Se filtrar_mat=True, aplica filtro de material."""
            if df_raw.empty or 'CLIENTE' not in df_raw.columns:
                return pd.Series(dtype=int), 0
            df_cli = df_raw[df_raw['CLIENTE'].astype(str).str.upper().str.contains(
                cliente_nome.upper(), na=False
            )].copy()
            if df_cli.empty:
                return pd.Series(dtype=int), 0
            df_cli['QUANTIDADE_INT'] = pd.to_numeric(df_cli['QUANTIDADE'], errors='coerce').fillna(0).astype(int)
            if filtrar_mat and 'MATERIAL' in df_cli.columns:
                df_cli = df_cli[df_cli['MATERIAL'].apply(eh_material_prioritario)].copy()
            if df_cli.empty:
                return pd.Series(dtype=int), 0
            total = int(df_cli['QUANTIDADE_INT'].sum())
            if filtrar_mat and 'MATERIAL' in df_cli.columns:
                df_cli['MATERIAL_BUCKET'] = df_cli['MATERIAL'].apply(bucket_material_prioritario)
                por_bucket = df_cli.groupby('MATERIAL_BUCKET')['QUANTIDADE_INT'].sum().sort_values(ascending=False)
            else:
                por_bucket = pd.Series({'Todas as amostras': total})
            return por_bucket, total

        # ── Cards de resumo por cliente-alvo ───────────────────────────────────
        # Unidade_Padrão_atividades para CC (EPR, STRATA, EIXO SP):
        #   = quantidade de ensaios (soma COL H do FORM 022A)
        #   Cada ensaio individual = 1 unidade padronizada
        clientes_alvo = {
            "EPR LITORAL PIONEIRO": ("EPR LITORAL PIONEIRO", True),
            "EPR VIAS DO CAFÉ":     ("EPR VIAS DO CAF",     False),
            "EPR IGUAÇU":           ("EPR IGUA",             True),
            "EIXO SP":              ("EIXO SP",              False),
            "STRATA":               ("STRATA",               True),
        }

        if not df_raw_det.empty:
            # Calcular Unidade_Padrão_atividades para cada CC
            _unidades_cc = {}
            for label, (busca, usa_filtro_mat) in clientes_alvo.items():
                _, total_card = _soma_det(df_raw_det, busca, filtrar_mat=usa_filtro_mat)
                _unidades_cc[label] = total_card

            # Total geral CC (excluindo CBB/ASFALTEC que têm painel próprio)
            _total_cc_geral = sum(_unidades_cc.values())

            # Banner da variável Unidade_Padrão_atividades
            st.markdown(
                f'<div style="background:#0f2a3f;border-left:4px solid #BFCF99;'
                f'padding:10px 14px;border-radius:4px;margin:8px 0 12px 0;">'
                f'<span style="color:#BFCF99;font-weight:bold;font-size:0.95rem;">'
                f'<span style="color:#adb5bd;font-size:0.82rem;margin-left:12px;">'
                f'Total de Ensaios: <b style="color:#BFCF99">'
                f'{_total_cc_geral}</b></span>'
                f'</div>',
                unsafe_allow_html=True
            )

            cols_cards = st.columns(len(clientes_alvo))
            for col_card, (label, _) in zip(cols_cards, clientes_alvo.items()):
                total_card = _unidades_cc[label]
                with col_card:
                    st.metric(
                        label,
                        f"{total_card} ensaios",
                        help=f"Unidade_Padrão_atividades = {total_card}"
                    )

        # ── Expanders por cliente (raw, sem dedup) ─────────────────────────────
        if not df_raw_det.empty and 'CLIENTE' in df_raw_det.columns:
            clientes_det_unicos = sorted(df_raw_det['CLIENTE'].dropna().unique())
            for cliente_nome in clientes_det_unicos:
                tipo_cliente = identificar_tipo_cliente_cc(cliente_nome)
                # Definir se usa filtro de material para este cliente
                _nome_up = cliente_nome.upper()
                usa_filtro = not any(x in _nome_up for x in ['EIXO SP', 'EPR VIAS'])

                por_bucket, total_cli = _soma_det(df_raw_det, cliente_nome, filtrar_mat=usa_filtro)

                if total_cli == 0:
                    continue

                with st.expander(f"{cliente_nome[:60]} ({total_cli} ensaios)", expanded=False):
                    if not por_bucket.empty:
                        col_info, col_graf = st.columns([1, 2])
                        with col_info:
                            lbl = "Materiais (priorizados):" if usa_filtro else "Total de amostras:"
                            st.write(lbl)
                            for material, qtd in por_bucket.items():
                                st.write(f"- {str(material)[:45]}: **{qtd}**")

                        top_buckets = por_bucket.head(3)
                        with col_graf:
                            cores_graf = ['#566E3D', '#6a8a4a', '#7fa35d'][:len(top_buckets)]
                            fig_mat = go.Figure(data=[go.Bar(
                                y=[str(m)[:35] for m in top_buckets.index],
                                x=top_buckets.values,
                                orientation='h',
                                marker_color=cores_graf,
                                text=top_buckets.values,
                                textposition='outside',
                                textfont=dict(color='white', size=12)
                            )])
                            _altura_mat = max(160, len(top_buckets) * 60 + 70)
                            fig_mat.update_layout(
                                title={'text': 'Materiais (soma COL H)', 'font': {'color': 'white', 'size': 13}},
                                height=_altura_mat,
                                dragmode=False,
                                plot_bgcolor='rgba(0, 35, 59, 0.9)',
                                paper_bgcolor='rgba(0, 35, 59, 0.9)',
                                font=dict(color='white', size=10),
                                xaxis=dict(gridcolor='#4a5568', fixedrange=True),
                                yaxis=dict(autorange='reversed', fixedrange=True, automargin=True),
                                margin=dict(l=10, r=55, t=36, b=16)
                            )
                            st.plotly_chart(fig_mat, use_container_width=True, config={'displayModeBar': False})

                    # Tabela detalhada do raw
                    with st.expander("Ver todos os registros (raw)", expanded=False):
                        df_cli_raw = df_raw_det[
                            df_raw_det['CLIENTE'].astype(str).str.upper().str.contains(cliente_nome.upper(), na=False)
                        ].copy()
                        cols_exib = [c for c in ['PT_COLUNA_A', 'MATERIAL', 'QUANTIDADE', 'DATA_RECEBIMENTO'] if c in df_cli_raw.columns]
                        if cols_exib:
                            df_cli_raw['DATA_RECEBIMENTO'] = pd.to_datetime(
                                df_cli_raw.get('DATA_RECEBIMENTO'), errors='coerce'
                            ).dt.strftime('%d/%m/%Y')
                            st.dataframe(df_cli_raw[cols_exib].reset_index(drop=True), use_container_width=True, hide_index=True)
                    
        if df_raw_det.empty:
            st.info("Nenhum cliente CC encontrado no período selecionado.")
    else:
        st.info("Nao ha dados disponiveis para o dashboard mensal.")

    # ==================================================================================
    # 📊 CBB ASFALTOS & ASFALTEC — Unidade_Padrão_atividades = PTs agrupados
    # ==================================================================================
    # Regra de unidade: cada GRUPO DE PTs (por empresa) = 1 medida padronizada.
    # CBB ASFALTOS  → conta PTs distintos (ex: 7 PTs = 7 unidades)
    # CC ASFALTEC   → conta PTs distintos (ex: 3 PTs = 3 unidades)
    # Amostras são informação complementar, NÃO a unidade principal.
    # ==================================================================================
    st.markdown("---")
    st.markdown("## CBB & Asfaltec")
    st.caption("Unidade_Padrão_atividades: cada agrupamento de PTs por empresa = 1 unidade | pós 01/12/2025")

    with st.spinner("Carregando dados CBB / Asfaltec..."):
        df_raw_cbb = carregar_dados_epr_raw(cliente_filtro=None)

    if df_raw_cbb.empty:
        st.info("Nenhum dado CBB / Asfaltec encontrado para o período.")
    else:
        # Aplicar filtro de mês da sidebar (DATA_RECEBIMENTO)
        if 'DATA_RECEBIMENTO' in df_raw_cbb.columns:
            df_raw_cbb['DATA_RECEBIMENTO'] = pd.to_datetime(df_raw_cbb['DATA_RECEBIMENTO'], errors='coerce')
            _mes_cbb = st.session_state.get('filtro_mes_data_recebimento', 'Todos')
            if _mes_cbb and _mes_cbb != 'Todos':
                try:
                    _nomes_m_cbb = {
                        'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4,
                        'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8,
                        'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
                    }
                    _nm_c, _an_c = _mes_cbb.rsplit('/', 1)
                    _p_cbb = pd.Period(f"{int(_an_c)}-{_nomes_m_cbb[_nm_c]:02d}", freq='M')
                    df_raw_cbb = df_raw_cbb[
                        df_raw_cbb['DATA_RECEBIMENTO'].dt.to_period('M') == _p_cbb
                    ]
                except Exception:
                    pass

        col_cli_cbb = 'CLIENTE' if 'CLIENTE' in df_raw_cbb.columns else 'EMPRESA'
        col_pt_cbb  = 'NUMERO_PROPOSTA' if 'NUMERO_PROPOSTA' in df_raw_cbb.columns else 'PT_COLUNA_A'

        df_cbb_only = df_raw_cbb[df_raw_cbb[col_cli_cbb].str.contains('CBB',      na=False, case=False)].copy()
        df_asf_only = df_raw_cbb[df_raw_cbb[col_cli_cbb].str.contains('ASFALTEC', na=False, case=False)].copy()

        # ── Unidade_Padrão_atividades: PTs distintos por empresa ──────────────
        pts_cbb = int(df_cbb_only[col_pt_cbb].nunique())
        pts_asf = int(df_asf_only[col_pt_cbb].nunique())
        am_cbb  = int(pd.to_numeric(df_cbb_only.get('QUANTIDADE', pd.Series([1])), errors='coerce').fillna(1).sum())
        am_asf  = int(pd.to_numeric(df_asf_only.get('QUANTIDADE', pd.Series([1])), errors='coerce').fillna(1).sum())

        # Cálculo da variável Unidade_Padrão_atividades para CBB+ASFALTEC
        Unidade_Padrão_atividades_CBB      = pts_cbb   # PTs CBB distintos
        Unidade_Padrão_atividades_ASFALTEC = pts_asf   # PTs ASFALTEC distintos
        Unidade_Padrão_atividades_CBB_ASF  = pts_cbb + pts_asf  # total agrupado

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric(
                " CBB ASFALTOS",
                f"{Unidade_Padrão_atividades_CBB} PTs",
                help=f"Unidade_Padrão_atividades = {Unidade_Padrão_atividades_CBB} | Amostras: {am_cbb}"
            )
        with col_m2:
            st.metric(
                " ASFALTEC",
                f"{Unidade_Padrão_atividades_ASFALTEC} PTs",
                help=f"Unidade_Padrão_atividades = {Unidade_Padrão_atividades_ASFALTEC} | Amostras: {am_asf}"
            )
        with col_m3:
            st.metric(
                "Total CBB + ASFALTEC",
                f"{Unidade_Padrão_atividades_CBB_ASF} PTs",
                help="Unidade_Padrão_atividades total do grupo"
            )

        # ── Gráfico ───────────────────────────────────────────────────────────
        fig_cbb = criar_grafico_cbb_asfaltec(df_raw_cbb)
        st.plotly_chart(fig_cbb, use_container_width=True, config={'displayModeBar': False})

        # ── Expanders detalhados por empresa ──────────────────────────────────
        st.markdown("#### Detalhes do Banco de Dados")
        col_exp1, col_exp2 = st.columns(2)

        def _formatar_tabela_cbb(df_empresa, col_pt):
            """Formata e agrupa tabela de PTs para CBB ou ASFALTEC."""
            cols_det = [c for c in [col_pt, 'MATERIAL', 'QUANTIDADE', 'DATA_RECEBIMENTO'] if c in df_empresa.columns]
            df_det = df_empresa[cols_det].copy().sort_values(col_pt).reset_index(drop=True)
            if 'DATA_RECEBIMENTO' in df_det.columns:
                df_det['DATA_RECEBIMENTO'] = pd.to_datetime(
                    df_det['DATA_RECEBIMENTO'], errors='coerce'
                ).dt.strftime('%d/%m/%Y')
            rename_map = {
                col_pt:             'PT / Proposta',
                'MATERIAL':         'Material',
                'QUANTIDADE':       'Qtd',
                'DATA_RECEBIMENTO': 'Recebimento',
            }
            return df_det.rename(columns={k: v for k, v in rename_map.items() if k in df_det.columns})

        with col_exp1:
            with st.expander(
                f"CBB ASFALTOS — {pts_cbb} Ensaios) | {am_cbb} amostras",
                expanded=False
            ):
                if df_cbb_only.empty:
                    st.info("Sem registros CBB no período.")
                else:
                    st.caption(f"Unidade_Padrão_atividades = **{pts_cbb}** (PTs distintos agrupados)")
                    df_tab_cbb = _formatar_tabela_cbb(df_cbb_only, col_pt_cbb)
                    st.dataframe(df_tab_cbb, use_container_width=True, hide_index=True)
                    if 'MATERIAL' in df_cbb_only.columns:
                        st.markdown("**Distribuição por Material:**")
                        mat_cbb = df_cbb_only['MATERIAL'].value_counts().reset_index()
                        mat_cbb.columns = ['Material', 'Registros']
                        st.dataframe(mat_cbb, use_container_width=True, hide_index=True)

        with col_exp2:
            with st.expander(
                f"ASFALTEC — {pts_asf} Ensaios | {am_asf} amostras",
                expanded=False
            ):
                if df_asf_only.empty:
                    st.info("Sem registros Asfaltec no período.")
                else:
                    st.caption(f"Unidade_Padrão_atividades = **{pts_asf}** (PTs distintos agrupados)")
                    df_tab_asf = _formatar_tabela_cbb(df_asf_only, col_pt_cbb)
                    st.dataframe(df_tab_asf, use_container_width=True, hide_index=True)
                    if 'MATERIAL' in df_asf_only.columns:
                        st.markdown("**Distribuição por Material:**")
                        mat_asf = df_asf_only['MATERIAL'].value_counts().reset_index()
                        mat_asf.columns = ['Material', 'Registros']
                        st.dataframe(mat_asf, use_container_width=True, hide_index=True)


    # ==================================================================================
    # QUANTITATIVO POR EMPRESA x FINALIDADE (COL B x COL M do FORM 022A)
    # Cada célula de FINALIDADE pode conter múltiplos ensaios separados por "," ou "+"
    # Ex: "GRAU DE COMPACTAÇÃO,RTCD,MR" → 3 barras distintas para a mesma amostra
    # ==================================================================================
    st.markdown("## Quantitativo por Empresa × Finalidade")
    st.caption("COL B (Empresa) × COL M (Finalidade) — ensaios compostos são contados individualmente")

    # ── Carregar dados (cache em session_state para evitar releitura) ────────────
    if 'df_empresa_finalidade_cache' not in st.session_state:
        with st.spinner("Carregando dados de Empresa × Finalidade..."):
            st.session_state['df_empresa_finalidade_cache'] = carregar_empresa_finalidade_raw()
    df_ef = st.session_state['df_empresa_finalidade_cache'].copy()

    # ── Lista canônica de finalidades (usada para deambiguação do split) ─────────
    # ── Lista de ENSAIOS SIMPLES (não devem ser divididos mesmo com vírgula/+) ────
    # Finalidades que existem como um único ensaio indivisível
    ENSAIOS_SIMPLES = {
        'ROMPIMENTOS', 'ROMPIMENTO',
        'GRAU DE COMPACTAÇÃO',
        'ENSAIO DE RAA',
        'TEOR, GRANULOMETRIA E RICE',   # a vírgula faz parte do nome — não dividir
        'TEOR E GRANULOMETRIA',
        'DPH', 'DEFORMAÇÃO PERMANENTE',
        'MR',
        'RTCD', 'RT',
        'CARACTERIZAÇÃO CAUQ', 'CARACTERIZAÇÃO',
        'PROJETO MRAF', 'PROJETO DE RECICLAGEM',
        'PROJETO SUPERPAVE', 'PROJETO CAUQ', 'PROJETO BGS',
        'RESÍDUO DA EMULSÃO',
        'IDEAL CT',
        'ADESIVIDADE',
        'ABRASÃO LOS ANGELES',
        'DUI',
        'RECICLAGEM',
        'WHEEL TRACK',
    }
    SIMPLES_UPPER = {s.upper().strip() for s in ENSAIOS_SIMPLES}

    # ── Mapeamento canônico de nomes para exibição uniforme ──────────────────────
    NOME_CANONICO = {
        'DEFORMAÇÃO PERMANENTE': 'DPH',
        'DPH': 'DPH',
        'RTCD': 'RTCD',
        'RT': 'RT',
        'MR': 'MR',
        'DUI': 'DUI',
        'ADESIVIDADE': 'ADESIVIDADE',
        'GRAU DE COMPACTAÇÃO': 'GRAU DE COMPACTAÇÃO',
        'GC': 'GRAU DE COMPACTAÇÃO',
        'ROMPIMENTO': 'ROMPIMENTO',
        'CARACT. CAUQ' : 'CARACATERIZAÇÃO CAUQ',
        'ROMPIMENTOS': 'ROMPIMENTO',
    }

    # ── Função de split: divide composto em ensaios individuais ─────────────────
    # Regra: se o texto inteiro é um ensaio simples → retorna [texto]
    #         caso contrário → divide por "+" e "," e normaliza cada parte
    import re as _re

    def _normalizar_ensaio(txt):
        """Normaliza variações de grafia para nome canônico."""
        t = txt.upper().strip()
        # Espaços múltiplos
        t = _re.sub(r'\s+', ' ', t)
        return NOME_CANONICO.get(t, t)

    def _split_finalidade(texto):
        """
        Quebra finalidade composta em lista de ensaios individuais.
        Ex: 'DUI + ADESIVIDADE'       → ['DUI', 'ADESIVIDADE']
            'MR + DPH'                → ['MR', 'DPH']
            'GRAU DE COMPACTAÇÃO,RT,MR' → ['GRAU DE COMPACTAÇÃO', 'RT', 'MR']
            'TEOR, GRANULOMETRIA E RICE' → ['TEOR, GRANULOMETRIA E RICE']  (simples)
            'DPH'                     → ['DPH']
            'DPH E AZM' → ['DPH', 'AZM']
            'MR; VISC BROK; E REC. ELAST' → ['MR', 'VISC BROK', 'REC. ELAST']
        """
        if not isinstance(texto, str) or not texto.strip():
            return []
        txt = texto.strip()
        t_upper = txt.upper().strip()

        # 1. É um ensaio simples exato → retorna inteiro
        if t_upper in SIMPLES_UPPER:
            return [_normalizar_ensaio(txt)]

        # 2. Dividir por "+" primeiro (separador mais forte)
        partes_plus = [p.strip() for p in _re.split(r'\+', txt)]
        resultado = []
        for parte in partes_plus:
            p_upper = parte.upper().strip()
            if p_upper in SIMPLES_UPPER:
                resultado.append(_normalizar_ensaio(parte))
            else:
                # Dividir por "," dentro desta parte
                sub_partes = [s.strip() for s in parte.split(',')]
                for sub in sub_partes:
                    s_upper = sub.upper().strip()
                    if len(s_upper) >= 2:
                        resultado.append(_normalizar_ensaio(sub))

        # 3. Se nada foi encontrado, retorna o texto inteiro normalizado
        return resultado if resultado else [_normalizar_ensaio(txt)]

    if not df_ef.empty and 'FINALIDADE' in df_ef.columns and 'EMPRESA' in df_ef.columns:

        # Aplicar filtro de mês da sidebar usando variáveis já parseadas
        if not df_ef.empty and 'DATA_RECEBIMENTO' in df_ef.columns and _filtro_mes_num is not None:
            df_ef['DATA_RECEBIMENTO'] = pd.to_datetime(df_ef['DATA_RECEBIMENTO'], errors='coerce')
            df_ef = df_ef[
                (df_ef['DATA_RECEBIMENTO'].dt.month == _filtro_mes_num) &
                (df_ef['DATA_RECEBIMENTO'].dt.year  == _filtro_ano_num)
            ]

        # Filtro rápido de empresa
        _empresas_ef = sorted(df_ef['EMPRESA'].dropna().unique())
        with st.expander("Filtros do gráfico", expanded=False):
            _col_ef1, _col_ef2 = st.columns(2)
            with _col_ef1:
                _emp_sel = st.multiselect(
                    "Empresas:", options=_empresas_ef, default=[],
                    key="filtro_empresa_ef"
                )
            with _col_ef2:
                _top_n_ef = st.slider("Top N finalidades:", 5, 40, 20, key="top_n_ef")
            _orientacao_ef = st.radio(
                "Orientação:", ["Horizontal", "Vertical"],
                horizontal=True, key="orientacao_ef"
            )

        if _emp_sel:
            df_ef = df_ef[df_ef['EMPRESA'].isin(_emp_sel)]

        # Filtro de cliente da sidebar para Empresa (quando não é "Todos")
        if _filtro_cliente_sel != "Todos" and not df_ef.empty and 'EMPRESA' in df_ef.columns:
            _clientes_filtro = [str(_filtro_cliente_sel).upper()] if isinstance(_filtro_cliente_sel, str) else []
            if _clientes_filtro:
                df_ef = df_ef[
                    df_ef['EMPRESA'].astype(str).str.upper().apply(
                        lambda nome: any(filtro in nome for filtro in _clientes_filtro)
                    )
                ]

        # ── Explodir finalidades compostas ────────────────────────────────────────
        rows_exp = []
        for _, row_ef in df_ef.iterrows():
            ensaios_lista = _split_finalidade(row_ef['FINALIDADE'])
            for ensaio in ensaios_lista:
                rows_exp.append({
                    'EMPRESA': str(row_ef['EMPRESA'])[:40],
                    'ENSAIO': ensaio,
                })
        df_exploded = pd.DataFrame(rows_exp) if rows_exp else pd.DataFrame(columns=['EMPRESA', 'ENSAIO'])

        if not df_exploded.empty:
            # Agregação: contar ocorrências EMPRESA × ENSAIO
            df_agg = (
                df_exploded.groupby(['EMPRESA', 'ENSAIO'])
                .size()
                .reset_index(name='QTD')
                .sort_values('QTD', ascending=False)
            )

            # Top N ensaios mais frequentes
            top_ensaios = (
                df_agg.groupby('ENSAIO')['QTD'].sum()
                .sort_values(ascending=False)
                .head(_top_n_ef)
                .index.tolist()
            )
            df_agg = df_agg[df_agg['ENSAIO'].isin(top_ensaios)]

            # Ordenar empresas por total decrescente
            ordem_empresas = (
                df_agg.groupby('EMPRESA')['QTD'].sum()
                .sort_values(ascending=True)
                .index.tolist()
            )

            # Paleta de cores distintas para ensaios
            PALETA = [
                '#566E3D', '#BFCF99', '#00233B', '#003d5c', '#0a4d6f',
                '#dc2626', '#f59e0b', '#7f1d1d', '#6b7280', '#1e40af',
                '#059669', '#7c3aed', '#db2777', '#0891b2', '#65a30d',
                '#ea580c', '#4f46e5', '#0f766e', '#b45309', '#6d28d9',
                '#be123c', '#0369a1', '#15803d', '#c2410c', '#7e22ce',
            ]
            ensaios_ordenados = sorted(top_ensaios)
            cores_map = {e: PALETA[i % len(PALETA)] for i, e in enumerate(ensaios_ordenados)}

            fig_ef = go.Figure()

            for ensaio in ensaios_ordenados:
                df_e = df_agg[df_agg['ENSAIO'] == ensaio].set_index('EMPRESA')['QTD']
                df_e = df_e.reindex(ordem_empresas, fill_value=0)

                if _orientacao_ef == "Horizontal":
                    fig_ef.add_trace(go.Bar(
                        name=ensaio,
                        y=ordem_empresas,
                        x=df_e.values,
                        orientation='h',
                        marker_color=cores_map[ensaio],
                        text=[str(v) if v > 0 else '' for v in df_e.values],
                        textposition='inside',
                        textfont=dict(color='white', size=10),
                        hovertemplate=f'<b>{ensaio}</b><br>Empresa: %{{y}}<br>Qtd: %{{x}}<extra></extra>',
                        hoverlabel=dict(bgcolor='rgba(0,35,59,0.98)', font_color='white', font_size=13)
                    ))
                else:
                    fig_ef.add_trace(go.Bar(
                        name=ensaio,
                        x=ordem_empresas,
                        y=df_e.values,
                        marker_color=cores_map[ensaio],
                        text=[str(v) if v > 0 else '' for v in df_e.values],
                        textposition='inside',
                        textfont=dict(color='white', size=10),
                        hovertemplate=f'<b>{ensaio}</b><br>Empresa: %{{x}}<br>Qtd: %{{y}}<extra></extra>',
                        hoverlabel=dict(bgcolor='rgba(0,35,59,0.98)', font_color='white', font_size=13)
                    ))

            # Altura dinâmica
            _h_ef = max(500, len(ordem_empresas) * 40 + 150) if _orientacao_ef == "Horizontal" else 580

            fig_ef.update_layout(
                barmode='stack',
                dragmode=False,
                title={
                    'text': '📊 Quantitativo de Ensaios por Empresa × Finalidade',
                    'x': 0.5, 'xanchor': 'center',
                    'font': {'size': 18, 'color': '#FFFFFF', 'family': 'Poppins'}
                },
                height=_h_ef,
                plot_bgcolor='rgba(0, 35, 59, 0.95)',
                paper_bgcolor='rgba(0, 35, 59, 0.95)',
                font=dict(color='#FFFFFF', size=11, family='Poppins'),
                legend=dict(
                    orientation='h',
                    xanchor='center', x=0.5,
                    yanchor='top', y=-0.02,
                    bgcolor='rgba(0,35,59,0.9)',
                    bordercolor='#566E3D',
                    font=dict(color='white', size=10),
                    itemwidth=30
                ),
                margin=dict(l=20, r=20, t=80, b=220),
                xaxis=dict(gridcolor='#566E3D', tickcolor='#BFCF99', tickfont=dict(color='white', size=11), fixedrange=True),
                yaxis=dict(gridcolor='#566E3D', tickcolor='#BFCF99', tickfont=dict(color='white', size=11), automargin=True, fixedrange=True),
            )

            # Métricas rápidas acima do gráfico
            _total_ensaios_ef = int(df_agg['QTD'].sum())
            _total_empresas_ef = df_agg['EMPRESA'].nunique()
            _total_tipos_ef = df_agg['ENSAIO'].nunique()
            _col_m1, _col_m2, _col_m3, _col_toggle = st.columns([1, 1, 1, 1])
            _col_m1.metric("Total de ensaios", _total_ensaios_ef)
            _col_m2.metric("Empresas", _total_empresas_ef)
            _col_m3.metric("Tipos de finalidade", _total_tipos_ef)
            with _col_toggle:
                st.markdown("<div style='padding-top:1.6rem;'></div>", unsafe_allow_html=True)
                _ocultar_ef = st.toggle("Ocultar gráfico", value=False, key="ocultar_fig_ef")

            if not _ocultar_ef:
                st.plotly_chart(fig_ef, use_container_width=True, config={
                    'displayModeBar': 'hover', 'displaylogo': False,
                    'modeBarButtonsToAdd': ['toImage'],
                    'toImageButtonOptions': {
                        'format': 'png', 'filename': 'quantitativo_empresa_finalidade',
                        'height': 1200, 'width': 2000, 'scale': 2
                    }
                })

            # Tabela resumo expandível
            with st.expander("Ver tabela resumo por Empresa × Finalidade", expanded=False):
                df_pivot = df_agg.pivot_table(
                    index='EMPRESA', columns='ENSAIO', values='QTD',
                    aggfunc='sum', fill_value=0
                )
                df_pivot['TOTAL'] = df_pivot.sum(axis=1)
                df_pivot = df_pivot.sort_values('TOTAL', ascending=False)
                st.dataframe(df_pivot, use_container_width=True)
        else:
            st.info("Nenhum dado de Finalidade encontrado. Execute **Sincronizar** para atualizar o banco de dados.")
    else:
        st.info("Dados de Empresa × Finalidade não disponíveis. Execute **Sincronizar** para importar.")

    st.markdown("---")

    st.markdown("## Previsão Data de Entrega")
    st.markdown("**Datas de Entrega de Relatórios**")
    
    # Filtros do Gráfico de Entregas
    with st.expander("Filtros do Cronograma de Entregas", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            if 'STATUS' in df.columns:
                status_entregas = st.multiselect(
                    "Status:",
                    options=sorted(df['STATUS'].dropna().unique()),
                    default=sorted(df['STATUS'].dropna().unique()),
                    key="filtro_status_entregas"
                )
            else:
                status_entregas = []
        with col_f2:
            if 'CLIENTE' in df.columns:
                clientes_entregas = st.multiselect(
                    "Clientes:",
                    options=sorted(df['CLIENTE'].dropna().unique())[:30],
                    default=[],
                    key="filtro_cliente_entregas"
                )
            else:
                clientes_entregas = []
        with col_f3:
            if 'TIPO_PROPOSTA' in df.columns:
                tipos_entregas = st.multiselect(
                    "Tipo Proposta:",
                    options=sorted(df['TIPO_PROPOSTA'].dropna().unique()),
                    default=sorted(df['TIPO_PROPOSTA'].dropna().unique()),
                    key="filtro_tipo_entregas"
                )
            else:
                tipos_entregas = []
        with col_f4:
            limite_entregas = st.slider("Limite de registros:", 5, 100, 50, key="limite_entregas")
    
    # Aplicar filtros
    df_entregas_filtrado = df.copy()
    if status_entregas and 'STATUS' in df_entregas_filtrado.columns:
        df_entregas_filtrado = df_entregas_filtrado[df_entregas_filtrado['STATUS'].isin(status_entregas)]
    if clientes_entregas and 'CLIENTE' in df_entregas_filtrado.columns:
        df_entregas_filtrado = df_entregas_filtrado[df_entregas_filtrado['CLIENTE'].isin(clientes_entregas)]
    if tipos_entregas and 'TIPO_PROPOSTA' in df_entregas_filtrado.columns:
        df_entregas_filtrado = df_entregas_filtrado[df_entregas_filtrado['TIPO_PROPOSTA'].isin(tipos_entregas)]
    df_entregas_filtrado = df_entregas_filtrado.head(limite_entregas)
    
    # Verificar se há dados de entrega da FAS
    if 'DATA_ENTREGA_FAS' in df_entregas_filtrado.columns or 'DATA_ENTREGA' in df_entregas_filtrado.columns:
        col_graf1, col_graf2 = st.columns([2, 1])
        
        with col_graf1:
            fig_entregas_fas = criar_grafico_entregas_fas(df_entregas_filtrado)
            if fig_entregas_fas.data:
                st.plotly_chart(fig_entregas_fas, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("📅 Não há datas de entrega disponíveis nos arquivos FAS.")
        
        with col_graf2:
            fig_entregas_mensal = criar_grafico_entregas_mensal(df)
            if fig_entregas_mensal.data:
                st.plotly_chart(fig_entregas_mensal, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("📊 Não há dados suficientes para o gráfico mensal.")
            
            # Estatísticas de entregas
            coluna_data = 'DATA_ENTREGA_FAS' if 'DATA_ENTREGA_FAS' in df.columns else 'DATA_ENTREGA'
            df_temp = df.copy()
            df_temp[coluna_data] = pd.to_datetime(df_temp[coluna_data], dayfirst=True, errors='coerce')
            df_com_data = df_temp.dropna(subset=[coluna_data])
            
            if not df_com_data.empty:
                hoje = datetime.now()
                entregas_futuras = len(df_com_data[df_com_data[coluna_data] > hoje])
                entregas_passadas = len(df_com_data[df_com_data[coluna_data] <= hoje])
                
                st.markdown("### 📈 Resumo de Entregas")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.metric("📅 Entregas Futuras", entregas_futuras)
                with col_e2:
                    st.metric("✅ Entregas Passadas", entregas_passadas)
                
                # Próximas entregas
                proximas = df_com_data[df_com_data[coluna_data] > hoje].nsmallest(5, coluna_data)
                if not proximas.empty:
                    st.markdown("**🔜 Próximas Entregas:**")
                    for _, row in proximas.iterrows():
                        data_str = row[coluna_data].strftime('%d/%m/%Y')
                        st.markdown(f"- **{data_str}**: {row.get('CLIENTE', 'N/A')[:25]}...")
    else:
        st.info("📅 Não há dados de entrega disponíveis. Sincronize os dados da FAS.")
    
    st.markdown("---")
    
    # ==================================================================================
    # GRÁFICOS INTERATIVOS ADICIONAIS
    # ==================================================================================
    
    # Contagem por acreditado
    acreditado_counts = df['ACREDITADO'].value_counts() if 'ACREDITADO' in df.columns else pd.Series()
    acreditados_sim = acreditado_counts.get('SIM', 0)
    acreditados_nao = acreditado_counts.get('NÃO', 0)
    
    # Calcular valores corretos
    total_registros = len(df)
    finalizados = len(df[df['STATUS'] == 'FINALIZADO']) if 'STATUS' in df.columns else 0
    em_execucao = len(df[df['STATUS'] == 'EM EXECUÇÃO']) if 'STATUS' in df.columns else 0
    em_andamento = len(df[df['STATUS'] == 'EM ANDAMENTO']) if 'STATUS' in df.columns else 0
    aguardando = len(df[df['STATUS'].isin(['AGUARDANDO MATERIAL', 'AGUARDANDO APROVAÇÃO', 'A DEFINIR'])]) if 'STATUS' in df.columns else 0
    
    render_banner_unidade_padrao(
        st.session_state.get('UPA', {}),
        chave='__TOTAL__',
        cor_borda='#566E3D',
        cor_texto='#BFCF99',
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Registros", total_registros)
    k2.metric("Finalizados", finalizados)
    k3.metric("Em Execução", em_execucao + em_andamento)
    k4.metric("Aguardando", aguardando)
    
    # Segunda linha de KPIs
    st.markdown("---")
    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Acreditados", acreditados_sim)
    k6.metric("Não Acreditados", acreditados_nao)
    
    # Taxa de conclusão
    if total_registros > 0:
        taxa_conclusao = (finalizados / total_registros * 100)
        k7.metric("Taxa de Conclusão", f"{taxa_conclusao:.1f}%")
    
    # Clientes únicos
    clientes_unicos = df['CLIENTE'].nunique() if 'CLIENTE' in df.columns else 0
    k8.metric("Clientes Únicos", clientes_unicos)
    
    st.markdown("---")
    
    # --- 2. GRÁFICOS ---
    
    # Gráfico de Status
    mostrar_estatisticas = st.checkbox("Exibir estatísticas detalhadas", value=True, key="mostrar_estatisticas")
    if mostrar_estatisticas and 'STATUS' in df.columns:
        st.subheader("Distribuição por Status")
        render_banner_unidade_padrao(
            st.session_state.get('UPA', {}),
            chave='__TOTAL__',
            cor_borda='#BFCF99',
            cor_texto='#BFCF99',
        )
        
        # Filtros do Gráfico de Status
        with st.expander("Filtros da Distribuição por Status", expanded=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                if 'ANO' in df.columns:
                    anos_status = st.multiselect(
                        "Anos:",
                        options=sorted(df['ANO'].dropna().unique(), reverse=True),
                        default=sorted(df['ANO'].dropna().unique(), reverse=True),
                        key="filtro_ano_status"
                    )
                else:
                    anos_status = []
            with col_f2:
                if 'TIPO_PROPOSTA' in df.columns:
                    tipos_status = st.multiselect(
                        "Tipo Proposta:",
                        options=sorted(df['TIPO_PROPOSTA'].dropna().unique()),
                        default=sorted(df['TIPO_PROPOSTA'].dropna().unique()),
                        key="filtro_tipo_status"
                    )
                else:
                    tipos_status = []
        
        # Aplicar filtros
        df_status_filtrado = df.copy()
        if anos_status and 'ANO' in df_status_filtrado.columns:
            df_status_filtrado = df_status_filtrado[df_status_filtrado['ANO'].isin(anos_status)]
        if tipos_status and 'TIPO_PROPOSTA' in df_status_filtrado.columns:
            df_status_filtrado = df_status_filtrado[df_status_filtrado['TIPO_PROPOSTA'].isin(tipos_status)]
        
        # Calcular contagem de status
        status_counts = df_status_filtrado['STATUS'].value_counts()
        
        # Gráfico de pizza
        fig_pizza = px.pie(
            names=status_counts.index,
            values=status_counts.values,
            hole=0.6,
            color_discrete_map={
                'FINALIZADO': '#16a34a',
                'EM EXECUÇÃO': '#3b82f6',
                'EM ANDAMENTO': '#f59e0b',
                'AGUARDANDO MATERIAL': '#6b7280',
                'AGUARDANDO APROVAÇÃO': '#dc2626'
            }
        )
        fig_pizza.update_traces(textposition='outside', textinfo='percent+label', textfont=dict(color='#ffffff', size=14))
        fig_pizza.update_layout(
            height=400,
            showlegend=True,
            font=dict(family="Poppins, sans-serif", color="#ffffff", size=16),
            paper_bgcolor='rgba(45, 55, 72, 0.8)',
            legend=dict(
                bgcolor='rgba(45, 55, 72, 0.8)',
                bordercolor='#4a5568',
                font=dict(color='#ffffff', size=14)
            )
        )
        st.plotly_chart(fig_pizza, use_container_width=True, config={'displayModeBar': False})
        
    
    # --- 3. ESTATÍSTICAS DETALHADAS ---
    if mostrar_estatisticas:
        st.subheader("📈 Estatísticas Detalhadas")
        render_banner_unidade_padrao(
            st.session_state.get('UPA', {}),
            chave='__TOTAL__',
            cor_borda='#BFCF99',
            cor_texto='#BFCF99',
        )
        
        # Filtros das Estatísticas
        with st.expander("🎛️ Filtros das Estatísticas", expanded=False):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                if 'ANO' in df.columns:
                    anos_stats = st.multiselect(
                        "Anos:",
                        options=sorted(df['ANO'].dropna().unique(), reverse=True),
                        default=sorted(df['ANO'].dropna().unique(), reverse=True),
                        key="filtro_ano_stats"
                    )
                else:
                    anos_stats = []
            with col_f2:
                if 'STATUS' in df.columns:
                    status_stats = st.multiselect(
                        "Status:",
                        options=sorted(df['STATUS'].dropna().unique()),
                        default=sorted(df['STATUS'].dropna().unique()),
                        key="filtro_status_stats"
                    )
                else:
                    status_stats = []
            with col_f3:
                if 'TIPO_PROPOSTA' in df.columns:
                    tipos_stats = st.multiselect(
                        "Tipo Proposta:",
                        options=sorted(df['TIPO_PROPOSTA'].dropna().unique()),
                        default=sorted(df['TIPO_PROPOSTA'].dropna().unique()),
                        key="filtro_tipo_stats"
                    )
                else:
                    tipos_stats = []
        
        # Aplicar filtros
        df_stats_filtrado = df.copy()
        if anos_stats and 'ANO' in df_stats_filtrado.columns:
            df_stats_filtrado = df_stats_filtrado[df_stats_filtrado['ANO'].isin(anos_stats)]
        if status_stats and 'STATUS' in df_stats_filtrado.columns:
            df_stats_filtrado = df_stats_filtrado[df_stats_filtrado['STATUS'].isin(status_stats)]
        if tipos_stats and 'TIPO_PROPOSTA' in df_stats_filtrado.columns:
            df_stats_filtrado = df_stats_filtrado[df_stats_filtrado['TIPO_PROPOSTA'].isin(tipos_stats)]
        
        # Usar estatísticas críticas que já existem
        estatisticas = criar_estatisticas_criticas(df_stats_filtrado)
        
        if estatisticas:
            render_banner_unidade_padrao(
                st.session_state.get('UPA', {}),
                chave='__TOTAL__',
                cor_borda='#566E3D',
                cor_texto='#BFCF99',
            )
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f'''
                <div class="kpi-card">
                    <p class="kpi-card-title">TOTAL REGISTROS</p>
                    <h1 class="kpi-card-value">{len(df_stats_filtrado)}</h1>
                </div>
                ''', unsafe_allow_html=True)
            
            with col2:
                em_andamento = len(df_stats_filtrado[df_stats_filtrado['STATUS'].isin(['EM ANDAMENTO', 'EM EXECUÇÃO', 'A INICIAR'])]) if 'STATUS' in df_stats_filtrado.columns else 0
                st.markdown(f'''
                <div class="kpi-card kpi-card-blue">
                    <p class="kpi-card-title">EM ANDAMENTO</p>
                    <h1 class="kpi-card-value">{em_andamento}</h1>
                </div>
                ''', unsafe_allow_html=True)
            
            with col3:
                finalizados = len(df_stats_filtrado[df_stats_filtrado['STATUS'] == 'FINALIZADO']) if 'STATUS' in df_stats_filtrado.columns else 0
                st.markdown(f'''
                <div class="kpi-card">
                    <p class="kpi-card-title">FINALIZADOS</p>
                    <h1 class="kpi-card-value">{finalizados}</h1>
                </div>
                ''', unsafe_allow_html=True)
            
            with col4:
                if 'TIPO' in df_stats_filtrado.columns:
                    tipos_count = len(df_stats_filtrado['TIPO'].unique())
                    st.markdown(f'''
                    <div class="kpi-card kpi-card-blue">
                        <p class="kpi-card-title">TIPOS DE DADOS</p>
                        <h1 class="kpi-card-value">{tipos_count}</h1>
                    </div>
                    ''', unsafe_allow_html=True)
            
            # Adicionar o gráfico de velocímetro
            st.markdown("<br>", unsafe_allow_html=True)
            col_gauge1, col_gauge2 = st.columns([2, 1])
            with col_gauge1:
                # Controles padronizados
                btn_exp, btn_att, _ = render_control_buttons("gauge_chart")
                if btn_att:
                    st.rerun()
                
                # Gráfico de velocímetro
                fig_gauge = criar_gauge_conclusao(df_stats_filtrado)
                st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
            
            # Gráficos de estatísticas
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 Distribuição por Status**")
                if 'STATUS' in df_stats_filtrado.columns:
                    status_df = pd.DataFrame(df_stats_filtrado['STATUS'].value_counts().reset_index())
                    status_df.columns = ['Status', 'Quantidade']
                    fig_status = px.bar(status_df, x='Status', y='Quantidade', 
                                        color='Status', height=400)
                    fig_status.update_layout(
                        plot_bgcolor='rgba(26, 31, 46, 0.9)',
                        paper_bgcolor='rgba(26, 31, 46, 0.9)',
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_status, use_container_width=True, config={'displayModeBar': False})
            
            with col2:
                if 'TIPO' in df_stats_filtrado.columns:
                    st.markdown("**📈 Distribuição por Tipo**")
                    tipo_df = pd.DataFrame(df_stats_filtrado['TIPO'].value_counts().reset_index())
                    tipo_df.columns = ['Tipo', 'Quantidade']
                    fig_tipo = px.pie(tipo_df, values='Quantidade', names='Tipo', 
                                      height=400, hole=0.6)
                    fig_tipo.update_layout(
                        plot_bgcolor='rgba(26, 31, 46, 0.9)',
                        paper_bgcolor='rgba(26, 31, 46, 0.9)',
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_tipo, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("---")
    
    # --- 4. TABELA DETALHADA ---
    mostrar_tabela = st.checkbox("Exibir tabela detalhada", value=True, key="mostrar_tabela")
    if mostrar_tabela:
        st.subheader("📋 Tabela Detalhada de Relatórios")
        
        # Selecionar colunas para exibir
        colunas_exibir = [
            'NUMERO_RELATORIO', 'CLIENTE', 'ENSAIO', 'NORMA', 
            'STATUS', 'ACREDITADO', 'QUANTIDADE', 
            'ACEITE_PROPOSTA', 'RECEBIMENTO_MATERIAL', 'DATA_ENTREGA'
        ]
        
        # Filtrar apenas colunas que existem
        colunas_disponiveis = [col for col in colunas_exibir if col in df.columns]
        
        if colunas_disponiveis:
            # Renomear colunas para melhor visualização
            df_exibir = df[colunas_disponiveis].copy()
            df_exibir.columns = [
                'Relatório', 'Cliente', 'Ensaio', 'Norma', 
                'Status', 'Acreditado', 'Quantidade', 
                'Aceite', 'Recebimento', 'Entrega'
            ][:len(colunas_disponiveis)]
            
            # Destacar linhas por status
            def destacar_status(val):
                cores = {
                    'FINALIZADO': 'background-color: #14532d',
                    'EM EXECUÇÃO': 'background-color: #1e293b',
                    'EM ANDAMENTO': 'background-color: #365314',
                    'AGUARDANDO MATERIAL': 'background-color: #374151',
                    'AGUARDANDO APROVAÇÃO': 'background-color: #7f1d1d'
                }
                return cores.get(val, '')
            
            # Aplicar estilo na coluna Status
            if 'Status' in df_exibir.columns:
                styled_df = df_exibir.style.applymap(
                    lambda x: destacar_status(x) if x in ['FINALIZADO', 'EM EXECUÇÃO', 'EM ANDAMENTO', 'AGUARDANDO MATERIAL', 'AGUARDANDO APROVAÇÃO'] else '',
                    subset=['Status']
                )
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.dataframe(df_exibir, use_container_width=True)
        else:
            st.warning("⚠️ Não há colunas disponíveis para exibir.")
    
    st.markdown("---")
    
    # --- 5. EXPORTAÇÃO ---
    st.subheader("📥 Exportar Dados")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Exportar CSV"):
            exportar_dados_csv(df, "cronograma_relatorios")
    
    with col2:
        if st.button("🔄 Atualizar Dados"):
            st.rerun()
    
    # Footer padronizado
    renderizar_footer()

if __name__ == "__main__":
    main()