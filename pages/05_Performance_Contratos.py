"""
=============================================================================
PERFORMANCE DE CONTRATOS — Visão por Colaborador e Contrato
=============================================================================
Página restrita ao usuário Dev.
Correlaciona: Rateio Mensal · Centro de Custo · Medições de Faturamento
=============================================================================
"""
import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from styles import aplicar_estilos
from page_auth import proteger_pagina

# =============================================================================
st.set_page_config(
    page_title="Performance | Afirma E-vias",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
aplicar_estilos()
proteger_pagina("Performance de Contratos")
# =============================================================================

from performance.utils_performance import (
    carregar_centro_custo,
    meses_disponiveis_labels,
    carregar_rateio,
    carregar_resumo_medicoes,
    carregar_unificado,
    resumo_por_colaborador,
    resumo_por_contrato,
)

# ── paleta ──────────────────────────────────────────────────────────────────
COR_PRIMARY   = "#566E3D"
COR_ACCENT    = "#BFCF99"
COR_BG        = "#0D1B2A"
COR_CARD      = "rgba(26, 31, 46, 0.85)"
COR_BORDER    = "rgba(86,110,61,0.35)"
COR_TEXT      = "#E8EFD8"
COR_MUTED     = "#8FA882"
COR_DANGER    = "#E05C5C"
COR_WARN      = "#E0A85C"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color=COR_TEXT, size=12),
    margin=dict(l=10, r=10, t=35, b=10),
    hoverlabel=dict(bgcolor=COR_BG, bordercolor=COR_PRIMARY,
                    font=dict(color=COR_TEXT, size=12, family="Poppins")),
    hovermode="closest",
    dragmode=False,
)
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}

# ── estilos CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

.perf-header {
    padding: 18px 0 8px 0;
    border-bottom: 2px solid rgba(86,110,61,0.4);
    margin-bottom: 24px;
}
.perf-header h1 {
    font-family: 'Poppins', sans-serif;
    font-size: 1.55rem;
    font-weight: 700;
    color: #BFCF99;
    margin: 0;
}
.perf-header p {
    font-family: 'Poppins', sans-serif;
    font-size: 0.82rem;
    color: #8FA882;
    margin: 4px 0 0 0;
}
.kpi-card {
    background: rgba(26, 31, 46, 0.85);
    border: 1px solid rgba(86,110,61,0.35);
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
}
.kpi-label {
    font-family: 'Poppins', sans-serif;
    font-size: 0.72rem;
    color: #8FA882;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.kpi-value {
    font-family: 'Poppins', sans-serif;
    font-size: 1.65rem;
    font-weight: 700;
    color: #BFCF99;
}
.kpi-sub {
    font-family: 'Poppins', sans-serif;
    font-size: 0.72rem;
    color: #566E3D;
    margin-top: 4px;
}
.section-title {
    font-family: 'Poppins', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: #BFCF99;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-left: 3px solid #566E3D;
    padding-left: 10px;
    margin: 24px 0 12px 0;
}
.badge-ativo   { background:#1A3A2A; color:#6FCF97; border:1px solid #27AE60; border-radius:20px; padding:2px 10px; font-size:0.72rem; }
.badge-inativo { background:#3A1A1A; color:#EB5757; border:1px solid #E05C5C; border-radius:20px; padding:2px 10px; font-size:0.72rem; }
.badge-clt     { background:#1A2A3A; color:#56B4D3; border:1px solid #2D9CDB; border-radius:20px; padding:2px 8px; font-size:0.7rem; }
.badge-pj      { background:#2A2A1A; color:#F2C94C; border:1px solid #E0A85C; border-radius:20px; padding:2px 8px; font-size:0.7rem; }
.table-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid rgba(86,110,61,0.25); }
table.perf-table { width: 100%; border-collapse: collapse; font-family: 'Poppins', sans-serif; font-size: 0.8rem; }
table.perf-table th {
    background: rgba(86,110,61,0.25);
    color: #BFCF99;
    padding: 9px 12px;
    text-align: left;
    font-weight: 600;
    white-space: nowrap;
    border-bottom: 1px solid rgba(86,110,61,0.3);
}
table.perf-table td {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: #C8D5B0;
    vertical-align: middle;
}
table.perf-table tr:hover td { background: rgba(86,110,61,0.08); }
.progress-bar-wrap { background: rgba(255,255,255,0.08); border-radius: 20px; height: 7px; width: 100%; }
.progress-bar-fill { background: #566E3D; border-radius: 20px; height: 7px; }
.no-data-box {
    background: rgba(26,31,46,0.7);
    border: 1px dashed rgba(86,110,61,0.4);
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    color: #8FA882;
    font-family: 'Poppins', sans-serif;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)


# ─── helpers ────────────────────────────────────────────────────────────────
def _fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

def _fmt_pct(v, casas=1):
    try:
        return f"{float(v)*100:.{casas}f}%"
    except Exception:
        return "—"

def _badge(texto, classe):
    return f'<span class="{classe}">{texto}</span>'

def _progbar(v, max_v=1.0, cor=COR_PRIMARY):
    pct = min(100, max(0, float(v or 0) / max(float(max_v), 0.001) * 100))
    return (f'<div class="progress-bar-wrap">'
            f'<div class="progress-bar-fill" style="width:{pct:.1f}%;background:{cor}"></div>'
            f'</div>')


# ─── header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="perf-header">
  <h1>📊 Performance de Contratos</h1>
  <p>Rateio de pessoal · Alocação por centro de custo · Correlação com medições</p>
</div>
""", unsafe_allow_html=True)


# ─── sidebar — filtros ───────────────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("Imagens/AE - Logo Hor Principal_2.png", use_container_width=True)
    except Exception:
        st.markdown("**Afirma E-vias**")

    st.markdown("---")
    st.markdown("### 🔎 Filtros")

    meses = meses_disponiveis_labels()
    if not meses:
        st.warning("Pasta de rateio não encontrada.\nVerifique: Z:\\CONTROLE OPERACIONAL")
        st.stop()

    mes_sel = st.selectbox("Período", meses, index=0)

    tipo_sel = st.selectbox("Tipo de vínculo", ["Todos", "CLT", "PJ"])
    status_sel = st.selectbox("Status", ["Todos", "ATUAL", "AFASTADO"])

    st.markdown("---")
    collab_filtro = st.text_input("🔍 Buscar colaborador", placeholder="Nome parcial...")

    st.markdown("---")
    mostrar_inativos = st.checkbox("Mostrar contratos inativos", value=False)


# ─── carregamento ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _load(mes_label: str):
    df_r   = carregar_rateio(mes_label)
    df_cc  = carregar_centro_custo()
    # descobre ano/mes do label  (ex: "FEV/2026")
    try:
        partes = mes_label.split("/")
        ano = int(partes[1])
        mes_abrev = partes[0]
        mes_map = {"JAN":1,"FEV":2,"MAR":3,"ABR":4,"MAI":5,"JUN":6,
                   "JUL":7,"AGO":8,"SET":9,"OUT":10,"NOV":11,"DEZ":12}
        mes = mes_map.get(mes_abrev.upper(), 0)
    except Exception:
        ano, mes = 0, 0

    df_unif  = carregar_unificado(ano, mes) if mes else pd.DataFrame()
    df_resum = carregar_resumo_medicoes(ano)
    return df_r, df_cc, df_unif, df_resum


with st.spinner("Carregando dados..."):
    df_rateio, df_cc, df_unif, df_resumo = _load(mes_sel)

if df_rateio.empty:
    st.markdown(f"""
    <div class="no-data-box">
      ⚠️ Nenhum dado de rateio encontrado para <b>{mes_sel}</b>.<br>
      Verifique se o arquivo Excel do período está na pasta de rateio.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── aplicar filtros ─────────────────────────────────────────────────────────
df_f = df_rateio.copy()
if tipo_sel != "Todos":
    df_f = df_f[df_f["TIPO"] == tipo_sel]
if status_sel != "Todos":
    df_f = df_f[df_f["STATUS"] == status_sel]
if collab_filtro:
    df_f = df_f[df_f["COLABORADOR"].str.upper().str.contains(collab_filtro.upper(), na=False)]


# ─── KPI cards ───────────────────────────────────────────────────────────────
n_colab    = df_f["COLABORADOR"].nunique()
n_contratos = df_f["CENTRO_CUSTO"].nunique()
custo_total = df_f["CUSTO_ALOCADO"].sum()
prod_media  = df_f["PRODUTIVIDADE"].mean()

c1, c2, c3, c4 = st.columns(4)
for col, lbl, val, sub in [
    (c1, "Colaboradores", str(n_colab), f"no período {mes_sel}"),
    (c2, "Contratos ativos", str(n_contratos), "centros de custo"),
    (c3, "Custo CLT alocado", _fmt_brl(custo_total) if custo_total > 0 else "—", "salário × % utilização"),
    (c4, "Produtividade média", _fmt_pct(prod_media) if pd.notna(prod_media) else "—", "medida no período"),
]:
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{lbl}</div>
      <div class="kpi-value">{val}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─── tabs ────────────────────────────────────────────────────────────────────
tab_colab, tab_contrato, tab_matriz, tab_unif = st.tabs([
    "👤 Por Colaborador",
    "🏗️ Por Contrato",
    "🔲 Mapa de Alocação",
    "📋 Medições — Detalhe",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — POR COLABORADOR
# ════════════════════════════════════════════════════════════════════════════
with tab_colab:
    df_res = resumo_por_colaborador(df_f)

    # ── gráfico produtividade ──
    if not df_res.empty:
        top20 = df_res.nlargest(20, "PERC_CUSTO_TOTAL").copy()
        top20["PROD_PCT"] = top20["PRODUTIVIDADE_MEDIA"].fillna(0) * 100

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=top20["PERC_CUSTO_TOTAL"] * 100,
            y=top20["COLABORADOR"],
            orientation="h",
            name="% Custo alocado",
            marker=dict(color=COR_PRIMARY, line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>% Custo total: %{x:.1f}%<extra></extra>",
            text=[f"{v:.0f}%" for v in top20["PERC_CUSTO_TOTAL"]*100],
            textposition="outside",
            textfont=dict(color=COR_MUTED, size=11),
        ))
        fig.add_trace(go.Scatter(
            x=top20["PROD_PCT"],
            y=top20["COLABORADOR"],
            mode="markers+text",
            name="Produtividade medida",
            marker=dict(color=COR_ACCENT, size=8, symbol="diamond"),
            hovertemplate="<b>%{y}</b><br>Produtividade: %{x:.1f}%<extra></extra>",
            text=[f"{v:.0f}%" for v in top20["PROD_PCT"]],
            textposition="middle right",
            textfont=dict(color=COR_ACCENT, size=10),
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            height=max(380, len(top20)*32),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(title="% alocação", gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(orientation="h", x=0, y=1.04),
            title=dict(text=f"Alocação de custo por colaborador — {mes_sel}",
                       font=dict(size=13, color=COR_ACCENT), x=0),
            barmode="overlay",
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    # ── tabela detalhada ──
    st.markdown('<div class="section-title">Detalhamento por colaborador</div>', unsafe_allow_html=True)

    if df_res.empty:
        st.markdown('<div class="no-data-box">Nenhum colaborador encontrado para os filtros selecionados.</div>',
                    unsafe_allow_html=True)
    else:
        rows = []
        for _, r in df_res.iterrows():
            b_tipo   = _badge(r["TIPO"],   "badge-clt" if r["TIPO"] == "CLT" else "badge-pj")
            b_status = _badge(r["STATUS"], "badge-ativo" if r["STATUS"] == "ATUAL" else "badge-inativo")
            prod_bar = _progbar(r["PRODUTIVIDADE_MEDIA"])
            custo_str = _fmt_brl(r["CUSTO_TOTAL"]) if pd.notna(r["CUSTO_TOTAL"]) and r["CUSTO_TOTAL"] > 0 else "—"
            salario   = _fmt_brl(r["SALARIO_BASE"]) if pd.notna(r["SALARIO_BASE"]) and float(r["SALARIO_BASE"] or 0) > 0 else "—"
            rows.append(f"""
            <tr>
              <td><b>{r['COLABORADOR']}</b></td>
              <td>{r['FUNCAO'] or '—'}</td>
              <td>{b_tipo}</td>
              <td>{b_status}</td>
              <td>{r['GESTOR'] or '—'}</td>
              <td>{r['NUM_CONTRATOS']}</td>
              <td style="font-size:0.72rem;max-width:220px;white-space:normal">{r['CONTRATOS']}</td>
              <td>{_fmt_pct(r['PERC_CUSTO_TOTAL'])}</td>
              <td>{salario}</td>
              <td>{custo_str}</td>
              <td>{prod_bar}<div style="font-size:0.7rem;color:{COR_MUTED};text-align:center;margin-top:2px">{_fmt_pct(r['PRODUTIVIDADE_MEDIA'])}</div></td>
            </tr>""")

        html = f"""
        <div class="table-wrap">
        <table class="perf-table">
        <thead><tr>
          <th>Colaborador</th><th>Função</th><th>Tipo</th><th>Status</th>
          <th>Gestor</th><th>Nº Contratos</th><th>Contratos</th>
          <th>% Custo total</th><th>Salário base</th><th>Custo alocado</th>
          <th>Produtividade</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
        </table></div>"""
        st.markdown(html, unsafe_allow_html=True)

        # export
        st.markdown("<br>", unsafe_allow_html=True)
        csv = df_res.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", csv, f"colaboradores_{mes_sel.replace('/','-')}.csv",
                           "text/csv", use_container_width=False)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — POR CONTRATO
# ════════════════════════════════════════════════════════════════════════════
with tab_contrato:
    df_cont = resumo_por_contrato(df_f, df_resumo)

    if not mostrar_inativos and "STATUS" in df_cont.columns:
        df_cont = df_cont[df_cont["STATUS"].astype(str).str.upper() != "INATIVO"]

    # ── gráfico colaboradores por contrato ──
    if not df_cont.empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_cont["CENTRO_CUSTO"],
            y=df_cont["NUM_COLABORADORES"],
            marker=dict(color=COR_PRIMARY, line=dict(width=0)),
            name="Colaboradores",
            hovertemplate="<b>%{x}</b><br>%{y} colaboradores<extra></extra>",
            text=df_cont["NUM_COLABORADORES"],
            textposition="outside",
            textfont=dict(color=COR_MUTED, size=10),
        ))
        if "CUSTO_PESSOAL" in df_cont.columns:
            fig2.add_trace(go.Scatter(
                x=df_cont["CENTRO_CUSTO"],
                y=df_cont["CUSTO_PESSOAL"],
                mode="markers",
                name="Custo pessoal (R$)",
                yaxis="y2",
                marker=dict(color=COR_ACCENT, size=9, symbol="circle"),
                hovertemplate="<b>%{x}</b><br>Custo: R$ %{y:,.2f}<extra></extra>",
            ))
            fig2.update_layout(yaxis2=dict(overlaying="y", side="right",
                                           title="Custo pessoal (R$)",
                                           gridcolor="rgba(0,0,0,0)"))

        fig2.update_layout(
            **PLOTLY_LAYOUT,
            height=400,
            xaxis=dict(tickangle=-40, tickfont=dict(size=10)),
            yaxis=dict(title="Nº colaboradores", gridcolor="rgba(255,255,255,0.05)"),
            legend=dict(orientation="h", x=0, y=1.04),
            title=dict(text=f"Colaboradores e custo por contrato — {mes_sel}",
                       font=dict(size=13, color=COR_ACCENT), x=0),
        )
        st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

    # ── tabela ──
    st.markdown('<div class="section-title">Detalhamento por contrato</div>', unsafe_allow_html=True)

    if df_cont.empty:
        st.markdown('<div class="no-data-box">Nenhum dado de contrato disponível.</div>', unsafe_allow_html=True)
    else:
        rows2 = []
        for _, r in df_cont.iterrows():
            grupo  = r.get("GRUPO", "—") or "—"
            escopo = r.get("ESCOPO", "—") or "—"
            st_val = str(r.get("STATUS", "—") or "—").upper()
            b_st   = _badge(st_val, "badge-ativo" if st_val == "ATIVO" else "badge-inativo")
            custo  = _fmt_brl(r.get("CUSTO_PESSOAL")) if pd.notna(r.get("CUSTO_PESSOAL", None)) else "—"
            nomes  = str(r.get("COLABORADORES","—") or "—")
            nomes_trunc = (nomes[:80] + "…") if len(nomes) > 80 else nomes
            rows2.append(f"""
            <tr>
              <td><b style="font-size:0.78rem">{r['CENTRO_CUSTO']}</b></td>
              <td>{grupo}</td>
              <td style="font-size:0.72rem">{escopo}</td>
              <td>{b_st}</td>
              <td style="text-align:center">{r['NUM_COLABORADORES']}</td>
              <td>{custo}</td>
              <td style="font-size:0.72rem;max-width:200px;white-space:normal">{nomes_trunc}</td>
            </tr>""")

        html2 = f"""
        <div class="table-wrap">
        <table class="perf-table">
        <thead><tr>
          <th>Centro de Custo</th><th>Grupo</th><th>Escopo</th><th>Status</th>
          <th>Colaboradores</th><th>Custo pessoal (CLT)</th><th>Equipe</th>
        </tr></thead>
        <tbody>{''.join(rows2)}</tbody>
        </table></div>"""
        st.markdown(html2, unsafe_allow_html=True)

        csv2 = df_cont.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", csv2, f"contratos_{mes_sel.replace('/','-')}.csv",
                           "text/csv", use_container_width=False)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — MAPA DE ALOCAÇÃO (colaborador × contrato)
# ════════════════════════════════════════════════════════════════════════════
with tab_matriz:
    st.markdown('<div class="section-title">Mapa de alocação: Colaborador × Contrato</div>',
                unsafe_allow_html=True)

    if df_f.empty:
        st.markdown('<div class="no-data-box">Sem dados para o mapa.</div>', unsafe_allow_html=True)
    else:
        # pivot: linhas=colaborador, colunas=contrato, valores=PERC_CUSTO
        pivot = (
            df_f.dropna(subset=["COLABORADOR", "CENTRO_CUSTO", "PERC_CUSTO"])
            .groupby(["COLABORADOR", "CENTRO_CUSTO"])["PERC_CUSTO"]
            .sum()
            .reset_index()
            .pivot(index="COLABORADOR", columns="CENTRO_CUSTO", values="PERC_CUSTO")
            .fillna(0)
        )

        # limita a 40 colaboradores mais alocados para não travar
        top40 = (
            df_f.groupby("COLABORADOR")["PERC_CUSTO"].sum()
            .nlargest(40).index.tolist()
        )
        pivot_view = pivot.loc[pivot.index.isin(top40)]

        z     = pivot_view.values * 100
        texto = [[f"{v:.0f}%" if v > 0 else "" for v in row] for row in z]

        fig3 = go.Figure(go.Heatmap(
            z=z,
            x=pivot_view.columns.tolist(),
            y=pivot_view.index.tolist(),
            text=texto,
            texttemplate="%{text}",
            textfont=dict(size=9, color="white"),
            colorscale=[[0,"#0D1B2A"], [0.01,"#1A3A1A"],
                        [0.4, COR_PRIMARY], [1.0, COR_ACCENT]],
            zmin=0, zmax=100,
            hovertemplate="<b>%{y}</b><br>%{x}<br>%{z:.1f}%<extra></extra>",
            showscale=True,
            colorbar=dict(title="% alocado", ticksuffix="%",
                          tickfont=dict(color=COR_TEXT, size=10)),
        ))
        fig3.update_layout(
            **PLOTLY_LAYOUT,
            height=max(450, len(pivot_view)*22 + 80),
            xaxis=dict(tickangle=-45, tickfont=dict(size=9), side="bottom"),
            yaxis=dict(tickfont=dict(size=9)),
            title=dict(text=f"Heatmap de alocação — {mes_sel} (top {len(pivot_view)} colaboradores)",
                       font=dict(size=13, color=COR_ACCENT), x=0),
        )
        st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CONFIG)

        if len(pivot.index) > 40:
            st.caption(f"⚠️ Exibindo os 40 colaboradores mais alocados. Total no período: {len(pivot.index)}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — MEDIÇÕES DETALHE (Unificado)
# ════════════════════════════════════════════════════════════════════════════
with tab_unif:
    st.markdown('<div class="section-title">Detalhe de medições — Aba Unificado</div>',
                unsafe_allow_html=True)

    if df_unif.empty:
        st.markdown("""
        <div class="no-data-box">
          Arquivo de medições mensais não encontrado.<br>
          <small>Z:\\CONTROLE OPERACIONAL\\13. Medições\\000-RESUMO\\{ano}\\{mês}\\</small>
        </div>""", unsafe_allow_html=True)
    else:
        # filtros rápidos
        col_f1, col_f2, col_f3 = st.columns(3)
        clientes_uniq = sorted(df_unif["CLIENTE"].dropna().astype(str).unique())
        cli_sel = col_f1.selectbox("Cliente", ["Todos"] + clientes_uniq)
        colab_uniq = sorted(df_unif["COLABORADOR"].dropna().astype(str).unique())
        col_sel = col_f2.selectbox("Colaborador", ["Todos"] + colab_uniq)
        serv_uniq = sorted(df_unif["SERVICO"].dropna().astype(str).unique())
        serv_sel = col_f3.selectbox("Serviço", ["Todos"] + serv_uniq)

        du = df_unif.copy()
        if cli_sel != "Todos":
            du = du[du["CLIENTE"].astype(str) == cli_sel]
        if col_sel != "Todos":
            du = du[du["COLABORADOR"].astype(str) == col_sel]
        if serv_sel != "Todos":
            du = du[du["SERVICO"].astype(str) == serv_sel]

        # KPIs rápidos da medição
        total_valor = du["VALOR_TOTAL"].sum()
        n_colab_u   = du["COLABORADOR"].nunique()
        n_cli_u     = du["CLIENTE"].nunique()

        cm1, cm2, cm3 = st.columns(3)
        for col, lbl, val in [
            (cm1, "Total faturado", _fmt_brl(total_valor)),
            (cm2, "Colaboradores", str(n_colab_u)),
            (cm3, "Clientes", str(n_cli_u)),
        ]:
            col.markdown(f"""
            <div class="kpi-card">
              <div class="kpi-label">{lbl}</div>
              <div class="kpi-value" style="font-size:1.2rem">{val}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── gráfico faturamento por cliente ──
        fat_cli = du.groupby("CLIENTE")["VALOR_TOTAL"].sum().sort_values(ascending=False).head(15)
        if not fat_cli.empty:
            fig4 = go.Figure(go.Bar(
                x=fat_cli.index.tolist(),
                y=fat_cli.values,
                marker=dict(color=COR_PRIMARY, line=dict(width=0)),
                text=[_fmt_brl(v) for v in fat_cli.values],
                textposition="outside",
                textfont=dict(color=COR_MUTED, size=10),
                hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>",
            ))
            fig4.update_layout(
                **PLOTLY_LAYOUT,
                height=350,
                xaxis=dict(tickangle=-35, tickfont=dict(size=10)),
                yaxis=dict(title="R$", gridcolor="rgba(255,255,255,0.05)"),
                title=dict(text="Faturamento por cliente — medição atual",
                           font=dict(size=13, color=COR_ACCENT), x=0),
            )
            st.plotly_chart(fig4, use_container_width=True, config=PLOTLY_CONFIG)

        # ── tabela detalhe ──
        cols_show = ["COLABORADOR", "CLIENTE", "CONTRATO", "OBRA", "SERVICO",
                     "PRODUTIVIDADE", "QTDE", "PRECO_UNIT", "VALOR_TOTAL"]
        du_show = du[[c for c in cols_show if c in du.columns]].copy()
        du_show["PRODUTIVIDADE"] = du_show["PRODUTIVIDADE"].apply(
            lambda v: _fmt_pct(v) if pd.notna(v) else "—"
        )
        du_show["PRECO_UNIT"]  = du_show["PRECO_UNIT"].apply(_fmt_brl)
        du_show["VALOR_TOTAL"] = du_show["VALOR_TOTAL"].apply(_fmt_brl)

        st.dataframe(
            du_show.rename(columns={
                "COLABORADOR":"Colaborador","CLIENTE":"Cliente","CONTRATO":"Contrato",
                "OBRA":"Obra","SERVICO":"Serviço","PRODUTIVIDADE":"Produtividade",
                "QTDE":"Qtde","PRECO_UNIT":"Preço Unit.","VALOR_TOTAL":"Valor Total",
            }),
            use_container_width=True,
            hide_index=True,
        )

        csv3 = du.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", csv3,
                           f"medicoes_detalhe_{mes_sel.replace('/','-')}.csv",
                           "text/csv", use_container_width=False)
