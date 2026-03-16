"""
=========================================================================
NOVO DASHBOARD - VERSÃO COM SQLITE ROBUSTO
=========================================================================
Dashboard completamente independente do Dashboard de Certificados
Segue o mesmo padrão visual mas com dados e lógica separados
=========================================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from io import BytesIO
import sys
import os

# Adicionar o diretório pai ao path para importar styles
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar estilos globais padronizados
from styles import aplicar_estilos, renderizar_sidebar, renderizar_footer, CORES, PLOTLY_LAYOUT, PLOTLY_CONFIG

# Importar utilitários EXCLUSIVOS deste dashboard (ESTRUTURA FORM 067)
from Mov_cert.utils_novo_dashboard import (
    carregar_dados,
    processar_dados,
    calcular_estatisticas,
    sync_dados,
    formatar_numero,
    formatar_data,
    exportar_csv,
    get_opcoes_unicas,
    carregar_form044,
    carregar_dados_em_execucao,
    buscar_e_extrair_form045,
    calcular_fas_total,
    normalizar_identificacao
)

# Constante para evitar conflito de session_state com Dashboard de Certificados
SESSION_PREFIX = "novo_dash_"


def gerar_excel_bytes(df_input: pd.DataFrame, sheet_name: str = "Dados") -> bytes:
    """Gera um arquivo Excel em memória a partir de um DataFrame."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_input.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer.getvalue()


def abreviar_texto(texto: str, limite: int = 35) -> str:
    texto = str(texto)
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + "..."


def montar_label_com_ensaio(df_base: pd.DataFrame, coluna_referencia: str, valor: str, prefixo_todos: str) -> str:
    if valor == "Todos":
        return prefixo_todos

    texto_base = abreviar_texto(valor)
    if 'ENSAIO' not in df_base.columns:
        return texto_base

    ensaios_relacionados = (
        df_base.loc[df_base[coluna_referencia] == valor, 'ENSAIO']
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if not ensaios_relacionados:
        return texto_base

    ensaio_principal = abreviar_texto(ensaios_relacionados[0], limite=45)
    sufixo = "" if len(ensaios_relacionados) == 1 else " (+)"
    return f"{texto_base} • Ensaio: {ensaio_principal}{sufixo}"

# ======================================================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILO (CSS - BRAND MANUAL AFIRMA E-VIAS)
# ======================================================================================
# Nota: A configuração da página é feita pelo app.py quando chamado via navegação
# Se executado diretamente, configura aqui

# ======================================================================================
# LÓGICA PRINCIPAL DO DASHBOARD
# ======================================================================================

def main():
    # Carregar dados primeiro
    with st.spinner("Carregando dados..."):
        df_raw = carregar_dados()
    
    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado. Clique em 'Sincronizar Dados' na sidebar.")
        df = pd.DataFrame()
    else:
        # Processar dados
        df = processar_dados(df_raw)
    
    # Sidebar com logo e filtros
    with st.sidebar:
        # Seta discreta para voltar ao menu principal
        st.markdown("""
        <style>
        div[data-testid="stButton"][key="back_to_menu_cert"] > button {
            background: transparent !important;
            border: 1px solid rgba(191,207,153,0.3) !important;
            color: rgba(191,207,153,0.7) !important;
            font-size: 0.78rem !important;
            padding: 0.2rem 0.6rem !important;
            border-radius: 6px !important;
            margin-bottom: 4px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stButton"][key="back_to_menu_cert"] > button:hover {
            background: rgba(191,207,153,0.1) !important;
            color: #BFCF99 !important;
            border-color: #BFCF99 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("← Menu Principal", key="back_to_menu_cert", use_container_width=False):
            st.switch_page("app.py")

        # Logo grande na sidebar
        try:
            st.image("Imagens/AE - Logo Hor Principal_2.png", use_container_width=True)
        except Exception:
            st.markdown(f"""
            <div style="background: {CORES['secundario']}; padding: 1.5rem; border-radius: 12px; text-align: center; margin-bottom: 1rem;">
                <h2 style="color: white; margin: 0;">AFIRMA E-VIAS</h2>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"<h3 style='color: {CORES['destaque']}; text-align: center;'>AE - Dashboard's</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Botão de sincronização
        if st.button("🔄 Sincronizar Dados", use_container_width=True, key=f"{SESSION_PREFIX}sync"):
            with st.spinner("Sincronizando dados..."):
                if sync_dados():
                    st.success("✅ Dados atualizados!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("⚠️ Nenhum dado encontrado nas fontes.")
        
        st.markdown("---")
        
        # Filtros em expander - ESTRUTURA FORM 067
        with st.expander("Filtros", expanded=True):
            # Filtro de Ano - SEM restrição de data fixa (carrega histórico completo)
            if not df.empty and 'ANO' in df.columns:
                anos = get_opcoes_unicas(df, 'ANO')
                if anos:
                    anos = sorted(anos, reverse=True)
                    ano_sel = st.selectbox("Ano:", ["Todos"] + list(anos), key=f"{SESSION_PREFIX}ano")
                    if ano_sel != "Todos":
                        df = df[df['ANO'] == ano_sel]
            
            # Filtro de Mês
            if not df.empty and 'MES' in df.columns:
                meses_dict = {
                    1: 'Janeiro',
                    2: 'Fevereiro',
                    3: 'Março',
                    4: 'Abril',
                    5: 'Maio',
                    6: 'Junho',
                    7: 'Julho',
                    8: 'Agosto',
                    9: 'Setembro',
                    10: 'Outubro',
                    11: 'Novembro',
                    12: 'Dezembro'
                }
                meses = sorted(df['MES'].dropna().unique())
                meses_nomes = [meses_dict.get(int(m), str(m)) for m in meses]
                mes_sel = st.selectbox("Mês:", ["Todos"] + meses_nomes, key=f"{SESSION_PREFIX}mes")
                if mes_sel != "Todos":
                    mes_num = [k for k, v in meses_dict.items() if v == mes_sel][0]
                    df = df[df['MES'] == mes_num]
            if not df.empty and 'CLIENTE' in df.columns:
                clientes = sorted(df['CLIENTE'].dropna().astype(str).unique())
                cliente_sel = st.selectbox("Cliente:", ["Todos"] + clientes, key=f"{SESSION_PREFIX}cliente")
                if cliente_sel != "Todos":
                    df = df[df['CLIENTE'] == cliente_sel]
            
            # Filtro de Ensaio
            if not df.empty and 'ENSAIO' in df.columns:
                ensaios = sorted(df['ENSAIO'].dropna().astype(str).unique())
                ensaio_sel = st.selectbox("Ensaio:", ["Todos"] + ensaios, key=f"{SESSION_PREFIX}ensaio")
                if ensaio_sel != "Todos":
                    df = df[df['ENSAIO'] == ensaio_sel]
            
            # Filtro de Acreditado
            if not df.empty and 'ACREDITADO' in df.columns:
                acreditados = sorted(df['ACREDITADO'].dropna().astype(str).unique())
                acreditado_sel = st.selectbox("Acreditado:", ["Todos"] + acreditados, key=f"{SESSION_PREFIX}acreditado")
                if acreditado_sel != "Todos":
                    df = df[df['ACREDITADO'] == acreditado_sel]
        
        st.markdown("---")
        st.caption("© 2026 Afirma E-vias")
    
    # Header com Logo na área principal - Selo + título próximos
    col_logo, col_titulo = st.columns([0.8, 4])
    with col_logo:
        try:
            from cloud_config import get_logo_path
            _selo = get_logo_path("selo_c_ass")
            if _selo:
                st.image(_selo, use_container_width=True)
        except Exception:
            pass
    
    with col_titulo:
        st.markdown(f"""
        <div style="padding-left: 1rem;">
            <h1 style="margin: 0;">Dashboard de Certificados</h1>
            <p style="color: {CORES['destaque']}; font-size: 1.1rem;">Análise de Dados - Certificados Formulário 067</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================================================================================
    # ÁREA PRINCIPAL
    # ==================================================================================
    
    if df.empty:
        st.info("Clique em 'Sincronizar Dados' na sidebar para carregar dados do FORM 067.")
        renderizar_footer()
        return
    
    # Cabeçalho com informações
    st.markdown(f"**Total de Certificados:** {len(df)} registros")
    st.markdown("---")
    
    # --- 1. CARDS DE KPI INTERATIVOS (FORM 067) ---
    stats = calcular_estatisticas(df)
    total_certificados = stats['total_certificados']
    total_quantidade = stats['total_quantidade']
    clientes_unicos = stats['clientes_unicos']
    ensaios_unicos = stats['ensaios_unicos']
    acreditados_sim = stats['acreditados_sim']
    acreditados_nao = stats['acreditados_nao']
    acreditados_nao_informado = stats['acreditados_nao_informado']
    
    k1, k2, k3, k4 = st.columns([1, 1, 1, 1], gap="small")
    
    with k1:
        st.metric("Total Certificados", formatar_numero(total_certificados))
        with st.expander("Ver Detalhes"):
            st.markdown('<div class="scrollable-container">', unsafe_allow_html=True)
            st.write(f"**Registros totais:** {total_certificados}")
            if 'ANO' in df.columns:
                por_ano = df['ANO'].value_counts().sort_index(ascending=False)
                for ano, qtd in por_ano.items():
                    st.write(f"• {ano}: {qtd} certificados")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with k2:
        st.metric("Total Amostras", formatar_numero(total_quantidade))
        with st.expander("Ver Detalhes"):
            if 'ENSAIO' in df.columns and 'QUANTIDADE' in df.columns:
                # Mostrar quantidade por ensaio
                amostras_por_ensaio = df.groupby('ENSAIO')['QUANTIDADE'].sum().sort_values(ascending=False)
                container_amostras = st.container(height=250)
                with container_amostras:
                    for ensaio, qtd in amostras_por_ensaio.items():
                        st.write(f"• {ensaio}: {qtd:,.0f}")
    
    with k3:
        st.metric("Clientes Únicos", formatar_numero(clientes_unicos))
        with st.expander("Ver Detalhes"):
            if 'CLIENTE' in df.columns:
                clientes_lista = df['CLIENTE'].value_counts()
                # Usar container com altura fixa e rolagem
                container_clientes = st.container(height=250)
                with container_clientes:
                    for cliente, qtd in clientes_lista.items():
                        st.write(f"• {cliente}: {qtd}")
    
    with k4:
        st.metric("Ensaios", formatar_numero(ensaios_unicos))
        with st.expander("Ver Detalhes"):
            if 'ENSAIO' in df.columns:
                ensaios_lista = df['ENSAIO'].value_counts()
                # Usar container com altura fixa e rolagem
                container_ensaios = st.container(height=250)
                with container_ensaios:
                    for ensaio, qtd in ensaios_lista.items():
                        st.write(f"• {ensaio}: {qtd}")
    
    # Segunda linha de KPIs - Acreditados (apenas SIM e NÃO - Coluna H vazia é desconsiderada)
    st.markdown("")
    k5, k6, _, _ = st.columns([1, 1, 1, 1], gap="small")
    
    with k5:
        st.metric("Acreditados (Sim)", formatar_numero(acreditados_sim))
        with st.expander("Ver Detalhes"):
            if 'ACREDITADO' in df.columns:
                df_sim = df[df['ACREDITADO'].str.upper() == 'SIM']
                if len(df_sim) > 0:
                    container_sim = st.container(height=250)
                    with container_sim:
                        st.write("**Ensaios:**")
                        ensaios_sim = df_sim['ENSAIO'].value_counts()
                        for ensaio, qtd in ensaios_sim.items():
                            st.write(f"• {ensaio}: {qtd}")
                        st.write("**Empresas:**")
                        empresas_sim = df_sim['CLIENTE'].value_counts()
                        for empresa, qtd in empresas_sim.items():
                            st.write(f"• {empresa}: {qtd}")
    
    with k6:
        st.metric("Acreditados (Não)", formatar_numero(acreditados_nao))
        with st.expander("Ver Detalhes"):
            if 'ACREDITADO' in df.columns:
                df_nao = df[df['ACREDITADO'].str.upper().isin(['NÃO', 'NAO'])]
                if len(df_nao) > 0:
                    container_nao = st.container(height=250)
                    with container_nao:
                        st.write("**Ensaios:**")
                        ensaios_nao = df_nao['ENSAIO'].value_counts()
                        for ensaio, qtd in ensaios_nao.items():
                            st.write(f"• {ensaio}: {qtd}")
                        st.write("**Empresas:**")
                        empresas_nao = df_nao['CLIENTE'].value_counts()
                        for empresa, qtd in empresas_nao.items():
                            st.write(f"• {empresa}: {qtd}")
    
    st.markdown("---")
    
    # --- 2. GRÁFICOS (LARGURA COMPLETA) - FORM 067 ---
    
    # Gráfico 1: Quantitativo por Ensaio
    st.subheader("Quantitativo por Ensaio")
    
    # Filtro único de ensaios
    if 'ENSAIO' in df.columns:
        todos_ensaios_lista = sorted(df['ENSAIO'].dropna().unique().tolist())
        ensaios_selecionados = st.multiselect(
            "Filtrar Ensaios:",
            options=todos_ensaios_lista,
            default=[],
            placeholder="Selecione ensaios específicos ou deixe vazio para todos",
            key=f"{SESSION_PREFIX}filtro_ensaios_graf"
        )
    
    if 'ENSAIO' in df.columns and 'QUANTIDADE' in df.columns:
        # Aplicar filtro se houver seleção
        if ensaios_selecionados:
            df_filtrado = df[df['ENSAIO'].isin(ensaios_selecionados)]
        else:
            df_filtrado = df
        
        top_ensaios = df_filtrado.groupby('ENSAIO')['QUANTIDADE'].sum().sort_values(ascending=True)
        
        # Calcular porcentagens
        total_geral = top_ensaios.sum()
        porcentagens = (top_ensaios / total_geral * 100).round(1)
        
        # Criar gráfico com traces individuais para interatividade (clicar para esconder)
        # Legenda em ordem Z-A (reversed)
        cores_ensaios = ['#566E3D', '#6a8a4a', '#7da058', '#BFCF99', '#89a26c', '#a8c78a', '#c5d9a8', '#d4e4bc', '#e3efd0', '#EFEBDC']
        
        fig = go.Figure()
        # Adicionar traces - ordem normal das barras
        ensaios_lista = list(top_ensaios.items())
        for i, (ensaio, valor) in enumerate(ensaios_lista):
            pct = porcentagens[ensaio]
            cor = cores_ensaios[i % len(cores_ensaios)]
            fig.add_trace(go.Bar(
                y=[ensaio],
                x=[valor],
                name=ensaio,
                orientation='h',
                text=f'{valor:,.0f} ({pct}%)',
                textposition='inside',
                textfont=dict(color='#FFFFFF', size=14),
                marker_color=cor,
                legendgroup=ensaio,
                showlegend=True,
                hovertemplate='<b>%{y}</b><br>Quantidade: %{x:,.0f}<extra></extra>'
            ))
        
        # Altura dinâmica baseada no número de ensaios
        altura_grafico = max(500, len(top_ensaios) * 35)
        
        fig.update_layout(
            xaxis_title="Quantidade Total",
            yaxis_title="Ensaio",
            height=altura_grafico,
            barmode='stack',
            showlegend=True,
            hovermode='closest',
            dragmode=False,
            hoverlabel=dict(
                bgcolor='#00233B',
                bordercolor='#566E3D',
                font=dict(color='#FFFFFF', size=13, family='Poppins, sans-serif')
            ),
            legend=dict(
                title=dict(text="Clique para esconder/mostrar", font=dict(size=11)),
                bgcolor='rgba(26, 31, 46, 0.8)',
                bordercolor='#566E3D',
                font=dict(color='#FFFFFF', size=11),
                orientation='h',
                yanchor='top',
                y=-0.05,
                xanchor='center',
                x=0.5,
                traceorder='reversed',
                itemwidth=30
            ),
            font=dict(family="Poppins, sans-serif", color="#FFFFFF", size=13),
            paper_bgcolor='rgba(26, 31, 46, 0.8)',
            plot_bgcolor='rgba(26, 31, 46, 0.8)',
            margin=dict(l=15, r=15, t=35, b=100),
            xaxis=dict(gridcolor='#566E3D', tickcolor='#566E3D', tickfont=dict(size=12), fixedrange=True),
            yaxis=dict(gridcolor='#566E3D', tickcolor='#566E3D', tickfont=dict(size=12), fixedrange=True)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
    
    st.markdown("---")
    
    # Gráfico 2: Ensaios por Cliente
    st.subheader("Ensaios por Cliente")
    if 'CLIENTE' in df.columns:
        top_clientes = df['CLIENTE'].value_counts().head(10)
        
        fig = px.pie(
            names=top_clientes.index,
            values=top_clientes.values,
            hole=0.6,
            color_discrete_sequence=['#566E3D', '#6a8a4a', '#7da058', '#BFCF99', '#89a26c', '#a8c78a', '#c5d9a8', '#d4e4bc', '#e3efd0', '#EFEBDC']
        )
        fig.update_traces(
            textposition='outside',
            textinfo='percent+label',
            textfont=dict(color='#FFFFFF', size=13),
            hovertemplate='<b>%{label}</b><br>Quantidade: %{value}<br>%{percent}<extra></extra>'
        )
        fig.update_layout(
            height=700,
            showlegend=True,
            dragmode=False,
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='#00233B',
                bordercolor='#566E3D',
                font=dict(color='#FFFFFF', size=13, family='Poppins, sans-serif')
            ),
            font=dict(family="Poppins, sans-serif", color="#FFFFFF", size=13),
            paper_bgcolor='rgba(26, 31, 46, 0.8)',
            margin=dict(l=80, r=80, t=40, b=120),
            legend=dict(
                orientation='h',
                xanchor='center', x=0.5,
                yanchor='top', y=-0.08,
                bgcolor='rgba(26, 31, 46, 0.8)',
                bordercolor='#566E3D',
                font=dict(color='#FFFFFF', size=11),
                itemwidth=30,
                traceorder='normal'
            )
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
    
    st.markdown("---")
    
    # Gráfico 3: Estatísticas por Ano
    st.subheader("Estatísticas por Ano")
    if 'ANO' in df.columns and 'QUANTIDADE' in df.columns:
        stats_ano = df.groupby('ANO').agg({
            'QUANTIDADE': 'sum',
            'CLIENTE': 'nunique',
            'ENSAIO': 'nunique'
        }).round(2)
        stats_ano.columns = ['Total Amostras', 'Clientes Únicos', 'Ensaios']
        
        # Gráfico com traces individuais para interatividade
        cores_anos = ['#566E3D', '#6a8a4a', '#7da058', '#BFCF99', '#89a26c']
        fig = go.Figure()
        for i, (ano, row) in enumerate(stats_ano.iterrows()):
            cor = cores_anos[i % len(cores_anos)]
            fig.add_trace(go.Bar(
                x=[ano],
                y=[row['Total Amostras']],
                name=f"{ano}",
                text=f"{row['Total Amostras']:,.0f}",
                textposition='outside',
                textfont=dict(color='#FFFFFF', size=14),
                marker_color=cor,
                showlegend=True,
                hovertemplate='<b>Ano: %{x}</b><br>Total: %{y:,.0f}<extra></extra>'
            ))
        
        fig.update_layout(
            title=dict(text="Total de Amostras por Ano", font=dict(size=15, color='#FFFFFF')),
            height=380,
            barmode='group',
            showlegend=True,
            hovermode='closest',
            dragmode=False,
            hoverlabel=dict(
                bgcolor='#00233B',
                bordercolor='#566E3D',
                font=dict(color='#FFFFFF', size=13, family='Poppins, sans-serif')
            ),
            legend=dict(
                title=dict(text="Clique para esconder", font=dict(size=10)),
                bgcolor='rgba(26, 31, 46, 0.8)',
                bordercolor='#566E3D',
                font=dict(color='#FFFFFF', size=11),
                orientation='h',
                xanchor='center', x=0.5,
                yanchor='top', y=-0.08
            ),
            font=dict(family="Poppins, sans-serif", color="#FFFFFF", size=13),
            paper_bgcolor='rgba(26, 31, 46, 0.8)',
            plot_bgcolor='rgba(26, 31, 46, 0.8)',
            margin=dict(l=20, r=20, t=50, b=80),
            xaxis=dict(gridcolor='#566E3D', tickcolor='#566E3D', tickfont=dict(size=12), fixedrange=True),
            yaxis=dict(gridcolor='#566E3D', tickcolor='#566E3D', tickfont=dict(size=12), fixedrange=True)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
        
        # Tabela de estatísticas
        st.dataframe(stats_ano, use_container_width=True)
    
    st.markdown("---")
    
    # Gráfico 4: Ensaios Acreditados (Coluna H)
    # REGRA: Só conta registros onde ACREDITADO não é None/vazio
    st.subheader("Ensaios Acreditados (Coluna H)")
    if 'ACREDITADO' in df.columns:
        # Filtrar apenas registros com ACREDITADO informado (não None, não vazio)
        df_acreditado_informado = df[df['ACREDITADO'].notna() & (df['ACREDITADO'] != '')]
        
        if len(df_acreditado_informado) > 0:
            stats_acreditado = df_acreditado_informado['ACREDITADO'].value_counts()
            
            fig = px.pie(
                names=stats_acreditado.index,
                values=stats_acreditado.values,
                hole=0.6,
                color_discrete_map={'SIM': '#566E3D', 'NÃO': '#00233B', 'NAO': '#00233B'}
            )
            fig.update_traces(
                textposition='outside', 
                textinfo='percent+label', 
                textfont=dict(color='#FFFFFF', size=16),
                hovertemplate='<b>%{label}</b><br>Quantidade: %{value}<br>%{percent}<extra></extra>'
            )
            fig.update_layout(
                title=f'<span style="color: #BFCF99; font-size:14px;">Total Informado: {len(df_acreditado_informado)} de {len(df)} registros</span>',
                height=380,
                showlegend=True,
                dragmode=False,
                hovermode='closest',
                hoverlabel=dict(
                    bgcolor='#00233B',
                    bordercolor='#566E3D',
                    font=dict(color='#FFFFFF', size=13, family='Poppins, sans-serif')
                ),
                font=dict(family="Poppins, sans-serif", color="#FFFFFF", size=13),
                paper_bgcolor='rgba(26, 31, 46, 0.8)',
                margin=dict(l=20, r=20, t=50, b=100),
                legend=dict(
                    orientation='h',
                    xanchor='center', x=0.5,
                    yanchor='top', y=-0.05,
                    bgcolor='rgba(26, 31, 46, 0.8)',
                    bordercolor='#566E3D',
                    font=dict(color='#FFFFFF', size=12),
                    itemwidth=30
                )
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
        else:
            st.info("Nenhum registro com informação de acreditação (Coluna H) preenchida.")

    # ==================================================================================
    # SEÇÃO QUANTITATIVA - ANÁLISE TEMPORAL (FORM 067)
    # ==================================================================================
    st.markdown("---")
    
    # Criar coluna MES_ANO a partir do campo DATA do FORM 067
    if 'DATA' in df.columns:
        df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
        df['MES_ANO'] = df['DATA'].dt.strftime('%m/%Y')
        df['ANO_FILTRO'] = df['DATA'].dt.year

    # ==================================================================================
    # 📈 ANÁLISE QUANTITATIVA TEMPORAL (COM FILTROS EM CASCATA)
    # ==================================================================================
    if 'MES_ANO' in df.columns and not df['MES_ANO'].isna().all():
        with st.container():
            st.markdown('<h2 style="color: #BFCF99; margin-bottom: 30px;">Análise Quantitativa Temporal</h2>', unsafe_allow_html=True)

            def criar_filtro_cascata(df_input, key_prefix):
                anos_disponiveis = sorted(df_input['ANO_FILTRO'].dropna().unique())
                ano_opcoes = ["Todos"] + [str(int(a)) for a in anos_disponiveis]
                ano_sel = st.selectbox(
                    "Ano",
                    options=ano_opcoes,
                    index=0,
                    key=f"{SESSION_PREFIX}ano_{key_prefix}",
                    label_visibility="collapsed"
                )
                if ano_sel == "Todos":
                    return df_input.copy()
                return df_input[df_input['ANO_FILTRO'] == int(ano_sel)]

            # Gráfico 1 - Total por mês
            st.markdown("---")
            st.markdown('<h3 style="color: #BFCF99; margin-bottom: 25px;">Total de Ensaios por Mês</h3>', unsafe_allow_html=True)
            df_linhas_filtrado = df.copy()
            with st.expander("Filtros", expanded=False):
                df_linhas_filtrado = criar_filtro_cascata(df, 'c1')
            ensaios_por_mes = df_linhas_filtrado.groupby('MES_ANO').size().reset_index(name='TOTAL_ENSAIOS')
            ensaios_por_mes = ensaios_por_mes.sort_values('MES_ANO')
            fig_ensaios = go.Figure()
            fig_ensaios.add_trace(go.Scatter(
                x=ensaios_por_mes['MES_ANO'],
                y=ensaios_por_mes['TOTAL_ENSAIOS'],
                mode='lines+markers+text',
                line=dict(color='#566E3D', width=3),
                marker=dict(size=15, color='#BFCF99'),
                name='Total de Ensaios',
                text=ensaios_por_mes['TOTAL_ENSAIOS'],
                textposition='top center',
                textfont=dict(color='#FFFFFF', size=17)
            ))
            total_geral = ensaios_por_mes['TOTAL_ENSAIOS'].sum()
            fig_ensaios.update_layout(
                title=f'<span style="color: #FFFFFF; font-size: 15px;">Total Geral: {total_geral:,} ensaios</span>',
                xaxis_title="Mês/Ano",
                yaxis_title="Número de Ensaios",
                height=420,
                hovermode='x unified',
                dragmode=False,
                hoverlabel=dict(bgcolor='#00233B', bordercolor='#566E3D', font=dict(color='#FFFFFF', size=13)),
                plot_bgcolor='rgba(26, 31, 46, 0.8)',
                paper_bgcolor='rgba(26, 31, 46, 0.8)',
                font=dict(color="#FFFFFF", size=12),
                margin=dict(l=20, r=20, t=50, b=50),
                xaxis=dict(tickfont=dict(size=11), tickangle=-45, fixedrange=True),
                yaxis=dict(tickfont=dict(size=11), fixedrange=True)
            )
            st.plotly_chart(fig_ensaios, use_container_width=True, config={'displayModeBar': False})

            # Gráfico 2 - Top clientes
            if 'CLIENTE' in df.columns:
                st.markdown("---")
                st.markdown('<h3 style="color: #BFCF99; margin-bottom: 30px;">Clientes por Ensaios - Análise Temporal</h3>', unsafe_allow_html=True)
                df_clientes_filtrado = df.copy()
                with st.expander("Filtros", expanded=False):
                    df_clientes_filtrado = criar_filtro_cascata(df, 'c2')

                clientes_mes = df_clientes_filtrado.groupby(['MES_ANO', 'CLIENTE']).size().reset_index(name='QTD_ENSAIOS')
                top_clientes_por_mes = (
                    clientes_mes
                    .sort_values(['MES_ANO', 'QTD_ENSAIOS'], ascending=[True, False])
                    .groupby('MES_ANO')
                    .head(3)
                    .copy()
                )

                if not top_clientes_por_mes.empty:
                    top_clientes_por_mes['PORCENTAGEM'] = top_clientes_por_mes.groupby('MES_ANO')['QTD_ENSAIOS'].transform(
                        lambda x: (x / x.sum() * 100).round(1)
                    )
                    fig_clientes = go.Figure()
                    cores_clientes = ['#566E3D', '#7a9a52', '#BFCF99']
                    top_clientes_por_mes['RANK'] = top_clientes_por_mes.groupby('MES_ANO').cumcount()

                    for rank in range(3):
                        dados_rank = top_clientes_por_mes[top_clientes_por_mes['RANK'] == rank]
                        if not dados_rank.empty:
                            fig_clientes.add_trace(go.Bar(
                                y=dados_rank['MES_ANO'],
                                x=dados_rank['QTD_ENSAIOS'],
                                orientation='h',
                                name=f'{rank+1}º Lugar',
                                text=[f"{row['CLIENTE']} ({row['PORCENTAGEM']}%)" for _, row in dados_rank.iterrows()],
                                textposition='auto',
                                textfont=dict(color='#FFFFFF', size=14),
                                marker_color=cores_clientes[rank],
                                showlegend=False,
                                customdata=dados_rank['CLIENTE'],
                                hovertemplate="<b>%{y}</b><br>Cliente: %{customdata}<br>Qtd: %{x}<extra></extra>"
                            ))

                    qtd_total_barras = len(top_clientes_por_mes)
                    altura_dinamica = max(500, 200 + (qtd_total_barras * 60))
                    fig_clientes.update_layout(
                        title=dict(text='Participação dos Maiores Clientes por Mês', font=dict(size=14, color='#FFFFFF')),
                        xaxis_title="Quantidade de Ensaios",
                        yaxis_title=None,
                        height=altura_dinamica,
                        hovermode='closest',
                        dragmode=False,
                        hoverlabel=dict(
                            bgcolor='#00233B',
                            bordercolor='#566E3D',
                            font=dict(color='#FFFFFF', size=13, family='Poppins, sans-serif')
                        ),
                        plot_bgcolor='rgba(26, 31, 46, 0.8)',
                        paper_bgcolor='rgba(26, 31, 46, 0.8)',
                        font=dict(color="#FFFFFF", size=12),
                        barmode='group',
                        bargap=0.15,
                        bargroupgap=0.02,
                        margin=dict(l=20, r=20, t=50, b=20),
                        xaxis=dict(tickfont=dict(size=11), fixedrange=True),
                        yaxis=dict(autorange="reversed", tickfont=dict(size=11), fixedrange=True)
                    )
                    st.plotly_chart(fig_clientes, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

            # ==============================================================================
            # GRÁFICO 3: TOP 3 ENSAIOS POR MÊS (BARRAS DINÂMICAS)
            # ==============================================================================
            if 'ENSAIO' in df.columns:
                st.markdown("---")
                st.markdown('<h3 style="color: #BFCF99; margin-bottom: 20px;">Ensaios - Análise Quantitativa Temporal</h3>', unsafe_allow_html=True)
                df_ensaios_filtrado = df.copy()
                with st.expander("Filtros", expanded=False):
                    df_ensaios_filtrado = criar_filtro_cascata(df, 'c3')

                ensaios_mes = df_ensaios_filtrado.groupby(['MES_ANO', 'ENSAIO']).size().reset_index(name='QTD_ENSAIOS')
                top_ensaios_por_mes = (
                    ensaios_mes
                    .sort_values(['MES_ANO', 'QTD_ENSAIOS'], ascending=[True, False])
                    .groupby('MES_ANO')
                    .head(3)
                    .copy()
                )

                if not top_ensaios_por_mes.empty:
                    top_ensaios_por_mes['PORCENTAGEM'] = top_ensaios_por_mes.groupby('MES_ANO')['QTD_ENSAIOS'].transform(
                        lambda x: (x / x.sum() * 100).round(1)
                    )
                    fig_ensaios_top = go.Figure()
                    cores_ensaios = ['#566E3D', '#7a9a52', '#BFCF99']
                    top_ensaios_por_mes['RANK'] = top_ensaios_por_mes.groupby('MES_ANO').cumcount()

                    for rank in range(3):
                        dados_rank = top_ensaios_por_mes[top_ensaios_por_mes['RANK'] == rank]
                        if not dados_rank.empty:
                            fig_ensaios_top.add_trace(go.Bar(
                                y=dados_rank['MES_ANO'],
                                x=dados_rank['QTD_ENSAIOS'],
                                orientation='h',
                                name=f'{rank+1}º Lugar',
                                text=[f"{row['ENSAIO']} ({row['PORCENTAGEM']}%)" for _, row in dados_rank.iterrows()],
                                textposition='auto',
                                textfont=dict(color='#FFFFFF', size=11),
                                marker_color=cores_ensaios[rank],
                                showlegend=False,
                                customdata=dados_rank['ENSAIO'],
                                hovertemplate="<b>%{y}</b><br>Ensaio: %{customdata}<br>Qtd: %{x}<extra></extra>"
                            ))

                    qtd_total_barras = len(top_ensaios_por_mes)
                    altura_dinamica = max(500, 200 + (qtd_total_barras * 40))
                    fig_ensaios_top.update_layout(
                        title=dict(text='Rank de Ensaios por Mês', font=dict(size=14, color='#FFFFFF')),
                        xaxis_title="Quantidade de Ensaios",
                        yaxis_title=None,
                        height=altura_dinamica,
                        hovermode='closest',
                        dragmode=False,
                        hoverlabel=dict(
                            bgcolor='#00233B',
                            bordercolor='#566E3D',
                            font=dict(color='#FFFFFF', size=13, family='Poppins, sans-serif')
                        ),
                        plot_bgcolor='rgba(26, 31, 46, 0.8)',
                        paper_bgcolor='rgba(26, 31, 46, 0.8)',
                        font=dict(color="#FFFFFF", size=11),
                        barmode='group',
                        bargap=0.15,
                        bargroupgap=0.02,
                        margin=dict(l=10, r=20, t=50, b=15),
                        xaxis=dict(fixedrange=True, tickfont=dict(size=11)),
                        yaxis=dict(autorange="reversed", fixedrange=True, tickfont=dict(size=11))
                    )
                    st.plotly_chart(fig_ensaios_top, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

            # ==============================================================================
            # DASHBOARDS POR NORMA/MÊS E FORMULÁRIO/MÊS
            # ==============================================================================
            if ('NORMA' in df.columns or 'FORMULARIO' in df.columns) and 'MES_ANO' in df.columns:
                st.markdown("---")
                st.markdown('<h3 style="color: #BFCF99;">Dashboards por Norma e Formulário</h3>', unsafe_allow_html=True)
                tab_normas, tab_formularios = st.tabs(["Normas por Mês", "Formulários por Mês"])

                with tab_normas:
                    if 'NORMA' not in df.columns:
                        st.info("Nenhuma coluna de Norma encontrada nos dados.")
                    else:
                        normas_raw = get_opcoes_unicas(df, 'NORMA')
                        normas_opcoes = ["Todos"] + normas_raw
                        meses_opcoes = ["Todos"] + sorted(df['MES_ANO'].dropna().unique().tolist())
                        col_norma, col_mes = st.columns(2)
                        with col_norma:
                            labels_normas = [
                                montar_label_com_ensaio(df, 'NORMA', opc, "Todas as Normas")
                                for opc in normas_opcoes
                            ]
                            norma_sel = st.selectbox(
                                "Norma",
                                options=normas_opcoes,
                                format_func=lambda x: labels_normas[normas_opcoes.index(x)],
                                key=f"{SESSION_PREFIX}norma_mes"
                            )
                        with col_mes:
                            mes_sel = st.selectbox("Mês (MM/AAAA)", meses_opcoes, key=f"{SESSION_PREFIX}mes_norma")

                        df_normas = df.copy()
                        if norma_sel != "Todos":
                            df_normas = df_normas[df_normas['NORMA'] == norma_sel]
                        if mes_sel != "Todos":
                            df_normas = df_normas[df_normas['MES_ANO'] == mes_sel]

                        if df_normas.empty:
                            st.warning("Sem registros para os filtros selecionados.")
                        else:
                            total_registros_norma = len(df_normas)
                            total_amostras_norma = int(df_normas['QUANTIDADE'].sum()) if 'QUANTIDADE' in df_normas.columns else total_registros_norma
                            c1, c2 = st.columns(2)
                            with c1:
                                st.metric("Registros Filtrados", formatar_numero(total_registros_norma))
                            with c2:
                                st.metric("Total de Amostras", formatar_numero(total_amostras_norma))

                            agrupado_norma = df_normas.groupby('MES_ANO').size().reset_index(name='total_registros')
                            has_quantidade = 'QUANTIDADE' in df_normas.columns
                            if has_quantidade:
                                total_amostras_por_mes = (
                                    df_normas.groupby('MES_ANO')['QUANTIDADE'].sum().reset_index(name='total_amostras')
                                )
                                agrupado_norma = agrupado_norma.merge(total_amostras_por_mes, on='MES_ANO', how='left')
                            else:
                                agrupado_norma['total_amostras'] = agrupado_norma['total_registros']

                            agrupado_norma['ORDENADOR'] = pd.to_datetime('01/' + agrupado_norma['MES_ANO'], format='%d/%m/%Y', errors='coerce')
                            agrupado_norma = agrupado_norma.sort_values('ORDENADOR')

                            fig_normas = go.Figure()
                            fig_normas.add_trace(go.Bar(
                                x=agrupado_norma['MES_ANO'],
                                y=agrupado_norma['total_registros'],
                                name='Certificados',
                                marker_color='#566E3D',
                                hovertemplate='<b>%{x}</b><br>Registros: %{y}<extra></extra>'
                            ))

                            if has_quantidade:
                                fig_normas.add_trace(go.Scatter(
                                    x=agrupado_norma['MES_ANO'],
                                    y=agrupado_norma['total_amostras'],
                                    name='Amostras',
                                    mode='lines+markers',
                                    line=dict(color='#BFCF99', width=3),
                                    marker=dict(size=10, color='#BFCF99'),
                                    hovertemplate='<b>%{x}</b><br>Amostras: %{y:,.0f}<extra></extra>'
                                ))

                            fig_normas.update_layout(
                                height=380,
                                plot_bgcolor='rgba(26, 31, 46, 0.8)',
                                paper_bgcolor='rgba(26, 31, 46, 0.8)',
                                font=dict(color='#FFFFFF', size=11),
                                xaxis_title='Mês/Ano',
                                yaxis_title='Volume',
                                hovermode='x unified',
                                dragmode=False,
                                legend=dict(
                                    orientation='h', xanchor='center', x=0.5,
                                    yanchor='top', y=-0.12,
                                    bgcolor='rgba(26, 31, 46, 0.8)',
                                    font=dict(size=11)
                                ),
                                margin=dict(l=20, r=20, t=40, b=80),
                                xaxis=dict(fixedrange=True, tickangle=-45, tickfont=dict(size=10)),
                                yaxis=dict(fixedrange=True, tickfont=dict(size=10))
                            )
                            st.plotly_chart(fig_normas, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

                            # Gráfico adicional com quantitativo por Norma (sem porcentagens)
                            st.markdown("#### Distribuição por Norma (Quantitativos)")
                            df_normas_plot = df_normas.copy()
                            df_normas_plot['NORMA_PLOT'] = df_normas_plot['NORMA'].replace('', 'Não informado')

                            if has_quantidade:
                                resumo_norma = (
                                    df_normas_plot
                                    .groupby('NORMA_PLOT')
                                    .agg(total_registros=('NORMA', 'size'), total_amostras=('QUANTIDADE', 'sum'))
                                    .reset_index()
                                )
                            else:
                                resumo_norma = (
                                    df_normas_plot
                                    .groupby('NORMA_PLOT')
                                    .size()
                                    .reset_index(name='total_registros')
                                )
                                resumo_norma['total_amostras'] = resumo_norma['total_registros']

                            resumo_norma = resumo_norma.sort_values('total_registros', ascending=True)

                            fig_normas_quant = go.Figure()
                            fig_normas_quant.add_trace(go.Bar(
                                y=resumo_norma['NORMA_PLOT'],
                                x=resumo_norma['total_registros'],
                                orientation='h',
                                name='Registros',
                                marker_color='#6a8a4a',
                                text=[f"{val:,.0f}" for val in resumo_norma['total_registros']],
                                textposition='outside',
                                textfont=dict(color='#FFFFFF', size=11),
                                hovertemplate='<b>%{y}</b><br>Registros: %{x:,.0f}<extra></extra>'
                            ))

                            if has_quantidade:
                                fig_normas_quant.add_trace(go.Bar(
                                    y=resumo_norma['NORMA_PLOT'],
                                    x=resumo_norma['total_amostras'],
                                    orientation='h',
                                    name='Amostras',
                                    marker_color='#BFCF99',
                                    text=[f"{val:,.0f}" for val in resumo_norma['total_amostras']],
                                    textposition='inside',
                                    textfont=dict(color='#1A1F2E', size=11),
                                    hovertemplate='<b>%{y}</b><br>Amostras: %{x:,.0f}<extra></extra>'
                                ))

                            altura_quant = max(300, 44 * len(resumo_norma))
                            fig_normas_quant.update_layout(
                                height=altura_quant,
                                plot_bgcolor='rgba(26, 31, 46, 0.8)',
                                paper_bgcolor='rgba(26, 31, 46, 0.8)',
                                font=dict(color='#FFFFFF', size=11),
                                showlegend=has_quantidade,
                                xaxis_title='Quantidade',
                                yaxis_title=None,
                                barmode='group',
                                hovermode='closest',
                                dragmode=False,
                                margin=dict(l=10, r=55, t=30, b=15),
                                xaxis=dict(fixedrange=True, tickfont=dict(size=10)),
                                yaxis=dict(fixedrange=True, automargin=True, tickfont=dict(size=10))
                            )
                            st.plotly_chart(fig_normas_quant, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

                            colunas_normas = (
                                ['MES_ANO', 'NORMA', 'CLIENTE', 'ENSAIO', 'QUANTIDADE']
                                if 'QUANTIDADE' in df_normas.columns
                                else ['MES_ANO', 'NORMA', 'CLIENTE', 'ENSAIO']
                            )
                            df_normas_view = df_normas[colunas_normas].reset_index(drop=True)
                            st.dataframe(df_normas_view, use_container_width=True)
                            st.download_button(
                                label="⬇️ Exportar Excel (Normas)",
                                data=gerar_excel_bytes(df_normas_view, sheet_name="Normas"),
                                file_name=f"normas_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"{SESSION_PREFIX}excel_normas"
                            )

                with tab_formularios:
                    if 'FORMULARIO' not in df.columns:
                        st.info("Nenhuma coluna de Formulário encontrada nos dados.")
                    else:
                        formularios_raw = get_opcoes_unicas(df, 'FORMULARIO')
                        formularios_opcoes = ["Todos"] + formularios_raw
                        meses_opcoes = ["Todos"] + sorted(df['MES_ANO'].dropna().unique().tolist())
                        col_form, col_mes = st.columns(2)
                        with col_form:
                            labels_formularios = [
                                montar_label_com_ensaio(df, 'FORMULARIO', opc, "Todos os Formulários")
                                for opc in formularios_opcoes
                            ]
                            formulario_sel = st.selectbox(
                                "Formulário",
                                options=formularios_opcoes,
                                format_func=lambda x: labels_formularios[formularios_opcoes.index(x)],
                                key=f"{SESSION_PREFIX}form_mes"
                            )
                        with col_mes:
                            mes_form_sel = st.selectbox("Mês (MM/AAAA)", meses_opcoes, key=f"{SESSION_PREFIX}mes_form")

                        df_form = df.copy()
                        if formulario_sel != "Todos":
                            df_form = df_form[df_form['FORMULARIO'] == formulario_sel]
                        if mes_form_sel != "Todos":
                            df_form = df_form[df_form['MES_ANO'] == mes_form_sel]

                        if df_form.empty:
                            st.warning("Sem registros para os filtros selecionados.")
                        else:
                            total_registros_form = len(df_form)
                            total_amostras_form = int(df_form['QUANTIDADE'].sum()) if 'QUANTIDADE' in df_form.columns else total_registros_form
                            c3, c4 = st.columns(2)
                            with c3:
                                st.metric("Registros Filtrados", formatar_numero(total_registros_form))
                            with c4:
                                st.metric("Total de Amostras", formatar_numero(total_amostras_form))

                            agrupado_form = df_form.groupby('MES_ANO').size().reset_index(name='total_registros')
                            has_quantidade_form = 'QUANTIDADE' in df_form.columns
                            if has_quantidade_form:
                                total_amostras_por_mes = (
                                    df_form.groupby('MES_ANO')['QUANTIDADE'].sum().reset_index(name='total_amostras')
                                )
                                agrupado_form = agrupado_form.merge(total_amostras_por_mes, on='MES_ANO', how='left')
                            else:
                                agrupado_form['total_amostras'] = agrupado_form['total_registros']

                            agrupado_form['ORDENADOR'] = pd.to_datetime('01/' + agrupado_form['MES_ANO'], format='%d/%m/%Y', errors='coerce')
                            agrupado_form = agrupado_form.sort_values('ORDENADOR')

                            fig_forms = go.Figure()
                            fig_forms.add_trace(go.Bar(
                                x=agrupado_form['MES_ANO'],
                                y=agrupado_form['total_registros'],
                                name='Certificados',
                                marker_color='#6a8a4a',
                                hovertemplate='<b>%{x}</b><br>Certificados: %{y}<extra></extra>'
                            ))

                            if has_quantidade_form:
                                fig_forms.add_trace(go.Scatter(
                                    x=agrupado_form['MES_ANO'],
                                    y=agrupado_form['total_amostras'],
                                    name='Amostras',
                                    mode='lines+markers',
                                    line=dict(color='#BFCF99', width=3),
                                    marker=dict(size=10, color='#BFCF99'),
                                    hovertemplate='<b>%{x}</b><br>Amostras: %{y:,.0f}<extra></extra>'
                                ))

                            fig_forms.update_layout(
                                height=370,
                                plot_bgcolor='rgba(26, 31, 46, 0.8)',
                                paper_bgcolor='rgba(26, 31, 46, 0.8)',
                                font=dict(color='#FFFFFF', size=11),
                                xaxis_title='Mês/Ano',
                                yaxis_title='Volume',
                                hovermode='x unified',
                                dragmode=False,
                                legend=dict(
                                    orientation='h', xanchor='center', x=0.5,
                                    yanchor='top', y=-0.12,
                                    bgcolor='rgba(26, 31, 46, 0.8)',
                                    font=dict(size=11)
                                ),
                                margin=dict(l=20, r=20, t=40, b=80),
                                xaxis=dict(fixedrange=True, tickangle=-45, tickfont=dict(size=10)),
                                yaxis=dict(fixedrange=True, tickfont=dict(size=10))
                            )
                            st.plotly_chart(fig_forms, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

                            colunas_form = (
                                ['MES_ANO', 'FORMULARIO', 'CLIENTE', 'ENSAIO', 'QUANTIDADE']
                                if 'QUANTIDADE' in df_form.columns
                                else ['MES_ANO', 'FORMULARIO', 'CLIENTE', 'ENSAIO']
                            )
                            df_form_view = df_form[colunas_form].reset_index(drop=True)
                            st.dataframe(df_form_view, use_container_width=True)
                            st.download_button(
                                label="⬇️ Exportar Excel (Formulários)",
                                data=gerar_excel_bytes(df_form_view, sheet_name="Formulários"),
                                file_name=f"formularios_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"{SESSION_PREFIX}excel_forms"
                            )
        # ==================================================================================
        # TABELA DE DADOS
        # ==================================================================================
    st.markdown("---")
    st.subheader("📋 Dados Detalhados")

    col_export, col_table = st.columns([1, 5])
    with col_export:
        csv_data = exportar_csv(df)
        st.download_button(
            label="📥 Exportar CSV",
            data=csv_data,
            file_name=f"dados_novo_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    with col_table:
        st.caption("Pré-visualização do dataset filtrado")
    st.dataframe(
        df.reset_index(drop=True),
        use_container_width=True,
        hide_index=True
    )

    # Footer padronizado
    renderizar_footer()

    # Rótulo fixo discreto no rodapé da página
    st.markdown(f"""
<style>
    .fixed-footer-label {{
        position: fixed;
        bottom: 10px;
        right: 15px;
        font-size: 13px;
        color: {CORES['texto_primario']};
        font-family: 'Poppins', sans-serif;
        font-weight: 400;
        opacity: 0.6;
        z-index: 9999;
        letter-spacing: 0.5px;
        transition: opacity 0.3s ease;
    }}
    .fixed-footer-label:hover {{
        opacity: 1;
        color: {CORES['destaque']};
    }}
</style>
<div class="fixed-footer-label">Developed By: Matheus Resende</div>
""", unsafe_allow_html=True)


# ======================================================================================
# FUNÇÃO PARA CHAMADA EXTERNA (pelo app.py)
# ======================================================================================

def render_novo_dashboard():
    """
    Função wrapper para ser chamada pelo app.py
    Aplica estilos e chama a função main()
    """
    aplicar_estilos()
    main()


# ======================================================================================
# EXECUÇÃO DIRETA (para testes)
# ======================================================================================

if __name__ == "__main__":
    st.set_page_config(
        page_title="Novo Dashboard | Afirma E-vias",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    aplicar_estilos()
    main()
