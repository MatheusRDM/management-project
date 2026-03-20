"""
=============================================================================
ECO RODOVIAS — Gestão de Contrato 6771
=============================================================================
BR-050 (Eco Minas Goiás) + BR-365 (Eco Cerrado)
Checklist APP + Ensaios AEVIAS
=============================================================================
"""
import streamlit as st
import sys
import os
import json
import re as _re
import threading
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from styles import aplicar_estilos
from page_auth import proteger_pagina

# =============================================================================
st.set_page_config(
    page_title="Eco Rodovias | Afirma E-vias",
    page_icon="Imagens/logo_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
aplicar_estilos()
proteger_pagina("Eco Rodovias")
# =============================================================================

# ── Paleta ────────────────────────────────────────────────────────────────────
COR_PRIMARY  = "#566E3D"
COR_ACCENT   = "#BFCF99"
COR_BG       = "#0D1B2A"
COR_CARD     = "rgba(26, 31, 46, 0.85)"
COR_BORDER   = "rgba(86,110,61,0.35)"
COR_TEXT     = "#E8EFD8"
COR_MUTED    = "#8FA882"
COR_OK       = "#3cb44b"
COR_COBRAR   = "#e6194b"
COR_NE       = "#3a4a5e"
COR_ELAB     = "#4363d8"

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

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

.eco-header {
    padding: 18px 0 8px 0;
    border-bottom: 2px solid rgba(86,110,61,0.4);
    margin-bottom: 24px;
}
.eco-header h1 {
    font-family: 'Poppins', sans-serif;
    font-size: 1.55rem;
    font-weight: 700;
    color: #BFCF99;
    margin: 0;
}
.eco-header p {
    font-family: 'Poppins', sans-serif;
    font-size: 0.82rem;
    color: #8FA882;
    margin: 4px 0 0 0;
}
.eco-kpi {
    background: rgba(26,31,46,0.85);
    border: 1px solid rgba(86,110,61,0.35);
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
    margin-bottom: 10px;
}
.eco-kpi .val {
    font-family: 'Poppins', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}
.eco-kpi .lbl {
    font-family: 'Poppins', sans-serif;
    font-size: 0.72rem;
    color: #8FA882;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.cal-wrap { overflow-x: auto; width: 100%; }
.cal-table {
    border-collapse: collapse;
    font-family: 'Poppins', sans-serif;
    font-size: 0.68rem;
    width: 100%;
    min-width: 900px;
}
.cal-table th {
    background: rgba(86,110,61,0.25);
    color: #BFCF99;
    padding: 5px 3px;
    text-align: center;
    font-weight: 600;
    border: 1px solid rgba(86,110,61,0.2);
    white-space: nowrap;
    font-size: 0.62rem;
}
.cal-table td {
    padding: 5px 4px;
    border: 1px solid rgba(255,255,255,0.05);
    text-align: center;
    white-space: nowrap;
}
.cal-table td.colab {
    text-align: left;
    font-weight: 500;
    color: #E8EFD8;
    padding-left: 8px;
    min-width: 160px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cal-table td.funcao {
    text-align: left;
    color: #8FA882;
    font-size: 0.60rem;
    min-width: 120px;
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
}
.status-ok    { background: rgba(60,180,75,0.25);  color: #3cb44b; font-weight:600; border-radius:3px; }
.status-cobrar{ background: rgba(230,25,75,0.25);  color: #ff5577; font-weight:600; border-radius:3px; }
.status-ne    { background: rgba(58,74,94,0.4);    color: #7a90a8; }
.status-elab  { background: rgba(67,99,216,0.25);  color: #6ec6ff; font-weight:600; border-radius:3px; }
.status-vazio { background: transparent; color: #3a4a5e; }
.legend-item { display:inline-flex; align-items:center; gap:6px; margin-right:14px; font-size:0.75rem; font-family:'Poppins',sans-serif; color:#E8EFD8; }
.legend-dot { width:12px; height:12px; border-radius:3px; display:inline-block; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CAMINHOS
# =============================================================================
_BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_DIR  = os.path.join(_BASE_DIR, "cache_certificados")
_Y_BASE     = "Y:/24-017 ECO 050 e CERRADO - Supervisão de Obras/04. Medição AFIRMA"
_IS_CLOUD   = not os.path.exists(_Y_BASE)

# =============================================================================
# CARREGAMENTO DE DADOS
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def _carregar_checklist_cache() -> dict:
    p = os.path.join(_CACHE_DIR, "eco_checklist.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _carregar_checklist_y(med_folder: str) -> dict | None:
    """Lê o xlsx de controle diretamente do Y:."""
    import openpyxl
    from glob import glob
    folder = os.path.join(_Y_BASE, med_folder)
    if not os.path.exists(folder):
        return None
    # Busca arquivo xlsx com "controle" e "app" no nome
    hits = [f for f in os.listdir(folder)
            if f.lower().endswith(".xlsx")
            and "controle" in f.lower()
            and not f.startswith("~")]
    if not hits:
        return None
    path = os.path.join(folder, hits[0])
    wb = openpyxl.load_workbook(path)
    result = {}
    for sn in wb.sheetnames:
        ws = wb[sn]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 3:
            continue
        header = rows[0]
        dates = []
        for v in header[2:]:
            if isinstance(v, datetime):
                dates.append(v.strftime("%Y-%m-%d"))
            else:
                dates.append(None)
        people = []
        for row in rows[2:]:
            if not row[0]:
                continue
            entry = {
                "colaborador": str(row[0]),
                "funcao": str(row[1]) if row[1] else "",
                "dias": {},
            }
            for i, d in enumerate(dates):
                if d and (i + 2) < len(row):
                    v = row[i + 2]
                    entry["dias"][d] = str(v) if v else None
            people.append(entry)
        result[sn] = people
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def _listar_meds() -> list[str]:
    cache = _carregar_checklist_cache()
    local_meds = list(cache.keys())
    if not _IS_CLOUD and os.path.exists(_Y_BASE):
        y_meds = [d for d in sorted(os.listdir(_Y_BASE)) if d.startswith("MED")]
        # Merge, mantendo cache + novos do Y
        all_meds = sorted(set(local_meds + y_meds))
        return all_meds
    return local_meds


@st.cache_data(ttl=3600, show_spinner=False)
def _carregar_ensaios() -> list[dict]:
    # 1. Tenta Y / desktop local
    local = os.path.join(
        os.path.expanduser("~"),
        "OneDrive", "Área de Trabalho", "Ensaios AEVIAS", "ensaios_dados.json"
    )
    for p in [local, os.path.join(_CACHE_DIR, "eco_ensaios.json")]:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return []


# =============================================================================
# COMPONENTES VISUAIS
# =============================================================================

def _kpi_card(val, label, cor="#BFCF99"):
    return f"""
    <div class="eco-kpi">
        <div class="val" style="color:{cor}">{val}</div>
        <div class="lbl">{label}</div>
    </div>"""


def _status_class(v):
    if v is None or v == "":
        return "status-vazio", "·"
    vu = str(v).upper().strip()
    if vu == "OK":
        return "status-ok", "OK"
    if vu in ("COBRAR", "COBRE"):
        return "status-cobrar", "COB"
    if vu in ("N/E", "NE"):
        return "status-ne", "N/E"
    if vu in ("ELAB.", "ELAB"):
        return "status-elab", "ELB"
    return "status-vazio", v[:3] if v else "·"


def _renderizar_calendario(people: list[dict], mes_ref: str):
    """Renderiza tabela HTML de calendário."""
    if not people:
        st.warning("Nenhum colaborador encontrado.")
        return

    # Coleta todas as datas disponíveis
    datas = set()
    for p in people:
        datas.update(p.get("dias", {}).keys())
    datas = sorted(d for d in datas if d)

    if not datas:
        st.info("Sem datas registradas.")
        return

    # Monta cabeçalho de datas
    DAY_ABBR = {0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SÁB", 6: "DOM"}
    html = ['<div class="cal-wrap"><table class="cal-table">']
    # Linha 1: números dos dias
    html.append("<thead><tr>")
    html.append('<th>Colaborador</th><th>Função</th>')
    for d in datas:
        dt = datetime.strptime(d, "%Y-%m-%d")
        html.append(f'<th>{dt.day:02d}</th>')
    html.append('<th>OK</th><th>COB</th></tr>')
    # Linha 2: siglas dos dias da semana
    html.append("<tr>")
    html.append('<th></th><th></th>')
    for d in datas:
        dt = datetime.strptime(d, "%Y-%m-%d")
        html.append(f'<th style="font-size:0.55rem;color:#8FA882">{DAY_ABBR[dt.weekday()]}</th>')
    html.append('<th></th><th></th></tr></thead>')

    # Linhas por colaborador
    html.append("<tbody>")
    for p in people:
        dias = p.get("dias", {})
        ok_count  = sum(1 for v in dias.values() if v and str(v).upper().strip() == "OK")
        cob_count = sum(1 for v in dias.values() if v and str(v).upper().strip() in ("COBRAR", "COBRE"))
        html.append("<tr>")
        html.append(f'<td class="colab" title="{p["colaborador"]}">{p["colaborador"]}</td>')
        html.append(f'<td class="funcao" title="{p["funcao"]}">{p["funcao"]}</td>')
        for d in datas:
            v = dias.get(d)
            cls, txt = _status_class(v)
            html.append(f'<td class="{cls}">{txt}</td>')
        cor_ok  = "#3cb44b" if ok_count  > 0 else "#7a90a8"
        cor_cob = "#ff5577" if cob_count > 0 else "#7a90a8"
        html.append(f'<td style="color:{cor_ok};font-weight:700">{ok_count}</td>')
        html.append(f'<td style="color:{cor_cob};font-weight:700">{cob_count if cob_count else "—"}</td>')
        html.append("</tr>")
    html.append("</tbody></table></div>")

    # Legenda
    html.append("""
    <div style="margin-top:10px">
        <span class="legend-item"><span class="legend-dot" style="background:rgba(60,180,75,0.35)"></span>OK — Checklist enviado</span>
        <span class="legend-item"><span class="legend-dot" style="background:rgba(230,25,75,0.35)"></span>COBRAR — Pendente</span>
        <span class="legend-item"><span class="legend-dot" style="background:rgba(58,74,94,0.6)"></span>N/E — Não estava em campo</span>
        <span class="legend-item"><span class="legend-dot" style="background:rgba(67,99,216,0.35)"></span>ELAB. — Em elaboração</span>
    </div>""")

    st.markdown("".join(html), unsafe_allow_html=True)


# =============================================================================
# ABAS DE CONTEÚDO
# =============================================================================

def _aba_checklist():
    meds = _listar_meds()
    if not meds:
        st.info("Nenhuma medição encontrada. Verifique o acesso ao servidor Y:")
        return

    med_labels = {m: m for m in reversed(meds)}  # mais recente primeiro
    meds_reversed = list(reversed(meds))

    col_sel, col_info = st.columns([2, 4])
    with col_sel:
        med_escolhida = st.selectbox(
            "📅 Medição:",
            options=meds_reversed,
            format_func=lambda x: x,
            key="eco_med_sel",
        )

    # Carrega dados da medição selecionada
    with st.spinner("Carregando checklist..."):
        sheets = None
        if not _IS_CLOUD:
            sheets = _carregar_checklist_y(med_escolhida)
        if sheets is None:
            cache = _carregar_checklist_cache()
            entry = cache.get(med_escolhida, {})
            sheets = entry.get("sheets", {})

    if not sheets:
        st.warning(f"Nenhum arquivo de controle encontrado para **{med_escolhida}**.")
        return

    # KPIs globais
    total_ok = total_cob = total_ne = 0
    for plist in sheets.values():
        for p in plist:
            for v in p.get("dias", {}).values():
                vu = str(v).upper().strip() if v else ""
                if vu == "OK":
                    total_ok += 1
                elif vu in ("COBRAR", "COBRE"):
                    total_cob += 1
                elif vu in ("N/E", "NE"):
                    total_ne += 1

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_kpi_card(total_ok,  "Checklists OK",     COR_OK),    unsafe_allow_html=True)
    c2.markdown(_kpi_card(total_cob, "A Cobrar",          COR_COBRAR), unsafe_allow_html=True)
    c3.markdown(_kpi_card(total_ne,  "Não em Campo (N/E)", COR_MUTED), unsafe_allow_html=True)
    pct = f"{100*total_ok/(total_ok+total_cob):.0f}%" if (total_ok+total_cob) > 0 else "—"
    c4.markdown(_kpi_card(pct, "Taxa de Conformidade", COR_ACCENT), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Sub-abas por contrato
    sheet_names = list(sheets.keys())
    tab_labels = [f"🛣️ {s}" for s in sheet_names]
    tabs = st.tabs(tab_labels)

    for tab, sn in zip(tabs, sheet_names):
        with tab:
            people = sheets[sn]
            if not people:
                st.info("Nenhum colaborador.")
                continue

            # KPIs por contrato
            ok_c = sum(
                1 for p in people for v in p.get("dias", {}).values()
                if v and str(v).upper().strip() == "OK"
            )
            cob_c = sum(
                1 for p in people for v in p.get("dias", {}).values()
                if v and str(v).upper().strip() in ("COBRAR", "COBRE")
            )
            colab_cob = [
                p["colaborador"].split()[0]
                for p in people
                if any(str(v).upper().strip() in ("COBRAR", "COBRE")
                       for v in p.get("dias", {}).values() if v)
            ]

            if cob_c > 0:
                st.error(
                    f"⚠️ **{cob_c} checklist(s) pendente(s)** — Colaboradores: "
                    + ", ".join(colab_cob[:6])
                    + ("..." if len(colab_cob) > 6 else "")
                )
            else:
                st.success(f"✅ Todos os checklists enviados neste contrato — {ok_c} registros OK")

            _renderizar_calendario(people, med_escolhida)


def _aba_ensaios():
    data = _carregar_ensaios()
    if not data:
        st.info("Nenhum dado de ensaios encontrado. Execute a automação de download.")
        return

    df = pd.DataFrame(data)
    # Normalizar encoding
    df["obra"]         = df["obra"].str.strip()
    df["tipo"]         = df["tipo"].str.strip()
    df["profissional"] = df["profissional"].str.strip()
    df["data_dt"]      = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")

    # Ordem das obras
    OBRAS_ORDEM = ["SST", "Pavimento", "TOPOGRAFIA", "OAE / Terraplenos",
                   "Ampliações", "ESCRITÓRIO", "Conserva"]
    OBRAS_CORES = {
        "SST":              "#e6194b",
        "Pavimento":        "#3cb44b",
        "TOPOGRAFIA":       "#ffe119",
        "OAE / Terraplenos":"#4363d8",
        "Ampliações":       "#f58231",
        "ESCRITÓRIO":       "#911eb4",
        "Conserva":         "#42d4f4",
    }

    # KPIs por categoria
    st.markdown("#### Ensaios por Categoria")
    cols = st.columns(len(OBRAS_ORDEM))
    for col, obra in zip(cols, OBRAS_ORDEM):
        cnt = len(df[df["obra"] == obra])
        cor = OBRAS_CORES.get(obra, COR_ACCENT)
        col.markdown(
            f'<div class="eco-kpi"><div class="val" style="color:{cor}">{cnt}</div>'
            f'<div class="lbl">{obra}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráficos
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Distribuição por Categoria")
        obras_count = df.groupby("obra").size().reset_index(name="qtd")
        obras_count = obras_count.sort_values("qtd", ascending=False)
        cores_list = [OBRAS_CORES.get(o, COR_MUTED) for o in obras_count["obra"]]
        fig = go.Figure(go.Pie(
            labels=obras_count["obra"],
            values=obras_count["qtd"],
            marker_colors=cores_list,
            hole=0.52,
            textinfo="label+value",
            textfont_size=12,
        ))
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, height=320)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with col_b:
        st.markdown("#### Distribuição por Tipo de Documento")
        tipos_count = df.groupby("tipo").size().reset_index(name="qtd")
        tipos_count = tipos_count.sort_values("qtd", ascending=True)
        fig2 = go.Figure(go.Bar(
            x=tipos_count["qtd"],
            y=tipos_count["tipo"],
            orientation="h",
            marker_color=COR_PRIMARY,
            text=tipos_count["qtd"],
            textposition="outside",
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=320,
                           xaxis=dict(showgrid=False, visible=False),
                           yaxis=dict(showgrid=False, tickfont=dict(size=11)))
        st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

    # Timeline
    if df["data_dt"].notna().any():
        st.markdown("#### Timeline de Ensaios")
        df_time = df.dropna(subset=["data_dt"]).copy()
        df_time["data_str"] = df_time["data_dt"].dt.strftime("%Y-%m-%d")
        timeline = df_time.groupby(["data_str", "obra"]).size().reset_index(name="qtd")
        fig3 = px.bar(
            timeline, x="data_str", y="qtd", color="obra",
            color_discrete_map=OBRAS_CORES,
            labels={"data_str": "Data", "qtd": "Qtd", "obra": "Categoria"},
        )
        fig3.update_layout(**PLOTLY_LAYOUT, height=280,
                           bargap=0.1, showlegend=True,
                           legend=dict(orientation="h", y=-0.18, x=0))
        st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CONFIG)

    # Filtros e tabela
    st.markdown("#### Tabela de Ensaios")
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        f_obra = st.multiselect("Categoria:", sorted(df["obra"].unique()), key="eco_f_obra")
    with f_col2:
        f_tipo = st.multiselect("Tipo:", sorted(df["tipo"].unique()), key="eco_f_tipo")
    with f_col3:
        f_prof = st.multiselect("Profissional/Projeto:", sorted(df["profissional"].unique()), key="eco_f_prof")

    df_view = df.copy()
    if f_obra: df_view = df_view[df_view["obra"].isin(f_obra)]
    if f_tipo: df_view = df_view[df_view["tipo"].isin(f_tipo)]
    if f_prof: df_view = df_view[df_view["profissional"].isin(f_prof)]

    _sort_col = "data_dt" if "data_dt" in df_view.columns else "data"
    df_display = df_view.sort_values(_sort_col, ascending=False)[["data", "obra", "tipo", "profissional"]]
    df_display.columns = ["Data", "Categoria", "Tipo", "Profissional/Projeto"]
    st.dataframe(df_display, use_container_width=True, hide_index=True, height=300)
    st.caption(f"{len(df_display)} registro(s) exibido(s) de {len(df)} total")


# =============================================================================
# SIDEBAR
# =============================================================================

def _sidebar():
    with st.sidebar:
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] { background: #0D1B2A !important; }
        .eco-sidebar-title {
            font-family:'Poppins',sans-serif; font-size:0.78rem;
            color:#8FA882; text-transform:uppercase; letter-spacing:.06em;
            margin: 8px 0 4px 0;
        }
        div[data-testid="stButton"] button {
            background: rgba(86,110,61,0.15) !important;
            border: 1px solid rgba(86,110,61,0.4) !important;
            color: #BFCF99 !important;
            font-family:'Poppins',sans-serif !important;
            font-size:0.78rem !important;
            padding:0.2rem 0.6rem !important;
            border-radius:6px !important;
            margin-bottom:0.5rem !important;
        }
        </style>""", unsafe_allow_html=True)

        if st.button("< Menu Principal", key="back_menu_eco"):
            st.switch_page("app.py")

        try:
            st.image("Imagens/AE - Logo Hor Principal_2.png", use_container_width=True)
        except Exception:
            st.markdown('<h3 style="color:white;text-align:center">AFIRMA E-VIAS</h3>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="eco-sidebar-title">Contrato</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-family:'Poppins',sans-serif; font-size:0.80rem; color:#E8EFD8; line-height:1.6">
            <b style="color:#BFCF99">ECO RODOVIAS 6771</b><br>
            🛣️ BR-050 — Eco Minas Goiás<br>
            🛣️ BR-365 — Eco Cerrado<br>
            <span style="color:#8FA882; font-size:0.72rem">Supervisão de Obras</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="eco-sidebar-title">Acesso ao Servidor</div>', unsafe_allow_html=True)
        if _IS_CLOUD:
            st.warning("🌐 Modo Cloud — dados do cache", icon=None)
        else:
            st.success("✅ Servidor Y: conectado", icon=None)


# =============================================================================
# MAIN
# =============================================================================

# =============================================================================
# LOGOS RASTREAMENTO — API (síncrono, via @st.fragment)
# =============================================================================
_LOGOS_BASE = "https://rastrear.logosrastreamento.com.br"
_CORES_VEICULOS = [
    "#FF6B35","#4CC9F0","#F7B731","#7BED9F","#FF4757",
    "#A29BFE","#FD79A8","#00CEC9","#FDCB6E","#6C5CE7",
]


def _logos_login():
    """Autentica no Logos e retorna (sess, idcli)."""
    try:
        usuario = st.secrets["logos_usuario"]
        senha   = st.secrets["logos_senha"]
    except Exception:
        usuario = "matheus.resende@afirmaevias.com.br"
        senha   = "19072019Joaquim*"

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    })
    r = sess.get(f"{_LOGOS_BASE}/Identity/Account/Login", timeout=15)
    m = _re.search(r'name="__RequestVerificationToken"[^>]+value="([^"]+)"', r.text)
    token = m.group(1) if m else ""
    sess.post(f"{_LOGOS_BASE}/Identity/Account/Login", data={
        "Input.UserName": usuario,
        "Input.Password": senha,
        "__RequestVerificationToken": token,
    }, timeout=15, allow_redirects=True)
    idcli = next((c.value for c in sess.cookies if c.name == "IDCLI"), None)
    if not idcli:
        raise ValueError("Login falhou — credenciais inválidas ou sessão expirada.")
    return sess, idcli


def _logos_get_eco(sess, idcli):
    """Retorna lista de veículos com ECO no nome (última posição)."""
    r = sess.post(f"{_LOGOS_BASE}/api/ultimaposicao", json={
        "idcliente": int(idcli), "texto": "", "placa": "", "serial": "",
        "descricao": "", "grupoveiculo": "", "idsVeiculos": [],
    }, timeout=20)
    items = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
    return [v for v in items if "ECO" in str(v.get("descricaovel", "")).upper()]


def _logos_get_rota(sess, idveiculo, d_ini, d_fim):
    """Retorna histórico de posições. d_ini/d_fim: 'YYYY-MM-DD HH:MM'"""
    r = sess.post(f"{_LOGOS_BASE}/api/historicoposicao", json={
        "idveiculo": idveiculo, "datainicio": d_ini, "datafinal": d_fim,
    }, timeout=60)
    d = r.json()
    return d if isinstance(d, list) else d.get("data", [])


@st.fragment
def _aba_rastreamento():
    # ── Controles ─────────────────────────────────────────────────────────────
    atu = st.session_state.get("logos_ultima_atualizacao")
    c1, c2 = st.columns([5, 1])
    with c1:
        if atu:
            st.caption(f"✅ {len(st.session_state.get('logos_veiculos',[]))} veículos ECO · Atualizado: {atu}")
    with c2:
        atualizar = st.button("🔄 Atualizar", key="logos_btn", use_container_width=True)

    if atualizar:
        with st.spinner("Conectando ao Logos e buscando veículos ECO..."):
            try:
                sess, idcli = _logos_login()
                veiculos = _logos_get_eco(sess, idcli)
                if not veiculos:
                    st.warning("Nenhum veículo com 'ECO' no nome encontrado.")
                    return
                st.session_state["logos_veiculos"]           = veiculos
                st.session_state["logos_ultima_atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                st.session_state.pop("logos_rota", None)
            except Exception as e:
                st.error(f"❌ {e}")
                return

    veiculos = st.session_state.get("logos_veiculos", [])
    if not veiculos:
        st.info("Clique em **🔄 Atualizar** para buscar os veículos ECO do Logos Rastreamento.")
        return

    # ── Mapa: última posição ──────────────────────────────────────────────────
    mapa   = folium.Map(location=[-18.5, -47.5], zoom_start=6, tiles="CartoDB dark_matter")
    bounds = []
    for i, v in enumerate(veiculos):
        cor   = _CORES_VEICULOS[i % len(_CORES_VEICULOS)]
        desc  = v.get("descricaovel", f"Veículo {i+1}")
        placa = v.get("placavel", "")
        lat   = v.get("pos_coordenada_latitude")
        lon   = v.get("pos_coordenada_longitude")
        ign   = "🟢" if v.get("pos_ignicao") else "🔴"
        vel   = v.get("pos_velocidade", 0)
        loc   = v.get("localizacao", "")
        if lat and lon:
            try:
                lt, ln = float(lat), float(lon)
                popup_html = (f"<b style='color:{cor}'>{desc}</b><br>"
                              f"Placa: {placa}<br>Ignição: {ign}<br>"
                              f"Velocidade: {vel} km/h<br>{loc}")
                folium.CircleMarker(
                    [lt, ln], radius=8, color=cor, fill=True,
                    fill_color=cor, fill_opacity=0.9,
                    tooltip=f"{ign} {desc} — {vel} km/h",
                    popup=folium.Popup(popup_html, max_width=260),
                ).add_to(mapa)
                bounds.append([lt, ln])
            except Exception:
                pass

    if bounds:
        lats = [c[0] for c in bounds]; lons = [c[1] for c in bounds]
        mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    st_folium(mapa, width="100%", height=430, key="logos_mapa_pos", returned_objects=[])

    # ── Tabela veículos ───────────────────────────────────────────────────────
    rows = [{
        "Veículo":        v.get("descricaovel", "—"),
        "Placa":          v.get("placavel", "—"),
        "Última posição": str(v.get("pos_dt_posicao", "—"))[:16].replace("T", " "),
        "Vel. km/h":      v.get("pos_velocidade", "—"),
        "Hodômetro km":   v.get("pos_odometro", "—"),
        "Ignição":        "🟢 Ligado" if v.get("pos_ignicao") else "🔴 Desligado",
        "Localização":    v.get("localizacao", "—"),
    } for v in veiculos]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=260)

    # ── Rota detalhada ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Rota detalhada — selecione um veículo**")
    # Monta label com última data conhecida para guiar o usuário
    def _label(v, i):
        dt = str(v.get("pos_dt_posicao", ""))[:10]
        return f"{v.get('descricaovel', f'V{i}')}  [{dt}]"
    opcoes = {_label(v, i): v for i, v in enumerate(veiculos)}

    r1, r2, r3, r4 = st.columns([3, 2, 2, 1])
    with r1:
        sel = st.selectbox("Veículo [última data]:", list(opcoes.keys()), key="logos_sel_v")
    with r2:
        # Sugere data baseada na última posição do veículo selecionado
        v_sel_data = opcoes[sel]
        ultima_dt  = str(v_sel_data.get("pos_dt_posicao", ""))[:10]
        try:
            from datetime import date as _date
            sugest = _date.fromisoformat(ultima_dt) if ultima_dt else date.today()
        except Exception:
            sugest = date.today()
        d_ini = st.date_input("De:", value=sugest, key="logos_r_ini")
    with r3:
        d_fim = st.date_input("Até:", value=sugest, key="logos_r_fim")
    with r4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        ver_rota = st.button("🗺️ Ver Rota", key="logos_btn_rota", use_container_width=True)

    if ver_rota:
        vid = opcoes[sel].get("pos_idvei")
        with st.spinner(f"Buscando rota..."):
            try:
                sess2, _ = _logos_login()
                hist = _logos_get_rota(
                    sess2, vid,
                    d_ini.strftime("%Y-%m-%d 00:00"),
                    d_fim.strftime("%Y-%m-%d 23:59"),
                )
                if not hist:
                    st.warning(f"Nenhuma posição encontrada para {d_ini} – {d_fim}. Tente outras datas.")
                    return
                st.session_state["logos_rota"]     = hist
                st.session_state["logos_rota_sel"] = sel
                st.session_state["logos_rota_idx"] = list(opcoes.keys()).index(sel)
            except Exception as e:
                st.error(f"❌ {e}")
                return

    hist = st.session_state.get("logos_rota", [])
    if not hist:
        return

    coords = []
    for p in hist:
        lt = p.get("pos_coordenada_latitude") or p.get("latitude")
        ln = p.get("pos_coordenada_longitude") or p.get("longitude")
        if lt and ln:
            try:
                coords.append([float(lt), float(ln)])
            except Exception:
                pass

    if coords:
        idx_sel   = st.session_state.get("logos_rota_idx", 0)
        cor_rota  = _CORES_VEICULOS[idx_sel % len(_CORES_VEICULOS)]
        desc_rota = st.session_state.get("logos_rota_sel", sel)

        mapa_r = folium.Map(tiles="CartoDB dark_matter")
        folium.PolyLine(coords, color=cor_rota, weight=4, opacity=0.9,
                        tooltip=desc_rota).add_to(mapa_r)
        folium.CircleMarker(coords[0],  radius=7, color="#00FF00", fill=True,
                            fill_color="#00FF00", tooltip="▶ Início").add_to(mapa_r)
        folium.CircleMarker(coords[-1], radius=7, color="#FF4757", fill=True,
                            fill_color="#FF4757", tooltip="⏹ Fim").add_to(mapa_r)
        lats = [c[0] for c in coords]; lons = [c[1] for c in coords]
        mapa_r.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
        st_folium(mapa_r, width="100%", height=480, key="logos_mapa_rota", returned_objects=[])
        st.caption(f"📍 {len(coords)} posições registradas · {desc_rota}")


# =============================================================================
def main():
    _sidebar()

    st.markdown("""
    <div class="eco-header">
        <h1>🛣️ Eco Rodovias — Contrato 6771</h1>
        <p>BR-050 (Eco Minas Goiás) · BR-365 (Eco Cerrado) · Supervisão de Obras AFIRMA E-VIAS</p>
    </div>""", unsafe_allow_html=True)

    tab_checklist, tab_ensaios, tab_rastr = st.tabs([
        "📋 Checklist APP",
        "🔬 Ensaios AEVIAS",
        "🛰️ Rastreamento",
    ])

    with tab_checklist:
        _aba_checklist()

    with tab_ensaios:
        _aba_ensaios()

    with tab_rastr:
        _aba_rastreamento()


if __name__ == "__main__" or True:
    main()
