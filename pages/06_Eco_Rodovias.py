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
# LOGOS RASTREAMENTO — API
# =============================================================================
_LOGOS_BASE = "https://rastrear.logosrastreamento.com.br"
_CORES_VEICULOS = [
    "#FF6B35","#4CC9F0","#F7B731","#7BED9F","#FF4757",
    "#A29BFE","#FD79A8","#00CEC9","#FDCB6E","#6C5CE7",
]

def _logos_criar_sessao():
    try:
        usuario = st.secrets["logos_usuario"]
        senha   = st.secrets["logos_senha"]
    except Exception:
        usuario = "matheus.resende@afirmaevias.com.br"
        senha   = "Rfp@39TH"

    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    r = sess.get(f"{_LOGOS_BASE}/home", timeout=20)
    m = _re.search(r'__RequestVerificationToken[^>]+value="([^"]+)"', r.text)
    token = m.group(1) if m else ""
    sess.post(f"{_LOGOS_BASE}/Identity/Account/Login", data={
        "Input.UserName": usuario,
        "Input.Password": senha,
        "__RequestVerificationToken": token,
    }, timeout=20, allow_redirects=True)
    return sess


def _logos_get_idcliente(sess):
    for c in sess.cookies:
        if c.name == "IDCLI":
            return c.value
    r = sess.get(f"{_LOGOS_BASE}/home", timeout=15)
    m = _re.search(r"IDCLI\s*[=:]\s*['\"]?(\d+)", r.text)
    return m.group(1) if m else None


def _logos_veiculos_eco(sess, idcliente):
    try:
        r = sess.post(f"{_LOGOS_BASE}/api/ultimaposicao", json={
            "idcliente": int(idcliente),
            "texto": "", "placa": "", "serial": "",
            "descricao": "", "grupoveiculo": "", "idsVeiculos": [],
        }, timeout=30)
        items = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
        return [v for v in items if "ECO" in str(v.get("descricao", "")).upper()]
    except Exception:
        return []


def _logos_historico(sess, idveiculo, datainicio, datafinal):
    try:
        r = sess.post(f"{_LOGOS_BASE}/api/historicoposicao", json={
            "idveiculo": idveiculo,
            "datainicio": datainicio,
            "datafinal":  datafinal,
        }, timeout=90)
        d = r.json()
        return d if isinstance(d, list) else d.get("data", d.get("posicoes", []))
    except Exception:
        return []


def _thread_buscar_logos(data_ini_str, data_fim_str):
    try:

        sess  = _logos_criar_sessao()
        idcli = _logos_get_idcliente(sess)
        if not idcli:
            st.session_state["_logos_error"]   = "Falha no login. Verifique as credenciais."
            st.session_state["_logos_loading"] = False
            return

        veiculos = _logos_veiculos_eco(sess, idcli)
        if not veiculos:
            st.session_state["_logos_error"]   = "Nenhum veículo ECO encontrado."
            st.session_state["_logos_loading"] = False
            return

        resultado = []
        for v in veiculos:
            vid  = v.get("idveiculo") or v.get("id")
            hist = _logos_historico(sess, vid, data_ini_str, data_fim_str) if vid else []
            resultado.append({"veiculo": v, "historico": hist})

        st.session_state["logos_dados"]              = resultado
        st.session_state["logos_ultima_atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        st.session_state["_logos_loading"]           = False
    except Exception as e:
        st.session_state["_logos_error"]   = str(e)
        st.session_state["_logos_loading"] = False


# ─── Status bar — re-renderiza a cada 2s enquanto carrega ────────────────────
@st.fragment(run_every=2)
def _logos_status_bar():
    loading = st.session_state.get("_logos_loading", False)
    error   = st.session_state.get("_logos_error")
    atu     = st.session_state.get("logos_ultima_atualizacao")
    inicio  = st.session_state.get("_logos_inicio_ts")

    if loading:
        elapsed = ""
        if inicio:
            secs = int((datetime.now() - inicio).total_seconds())
            elapsed = f" — {secs}s"
        st.markdown(f"""
        <div style="background:rgba(86,110,61,0.25);border:1px solid #566E3D;border-radius:8px;
                    padding:14px 20px;display:flex;align-items:center;gap:12px;margin:8px 0;">
            <span style="font-size:1.4rem">⏳</span>
            <span style="color:#BFCF99;font-weight:600;font-size:1rem">
                Autenticando e buscando veículos ECO no Logos Rastreamento{elapsed}...
            </span>
        </div>""", unsafe_allow_html=True)
    elif error:
        st.error(f"❌ {error}")
    elif atu:
        n = len(st.session_state.get("logos_dados", []))
        st.success(f"✅ {n} veículo(s) ECO carregados · Atualizado: {atu}")
    else:
        st.caption("Clique em **🔄 Atualizar** para buscar os veículos ECO do Logos Rastreamento.")


def _aba_rastreamento():
    # ── Controles ─────────────────────────────────────────────────────────────
    loading = bool(st.session_state.get("_logos_loading", False))

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        d_ini = st.date_input("Data início:", value=date.today().replace(day=1), key="logos_d_ini")
    with c2:
        d_fim = st.date_input("Data fim:",    value=date.today(),                key="logos_d_fim")
    with c3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="logos_btn",
                     use_container_width=True,
                     disabled=loading,
                     help="Busca apenas veículos com ECO no nome"):
            if not st.session_state.get("_logos_loading"):
                st.session_state["_logos_loading"]  = True
                st.session_state["_logos_error"]    = None
                st.session_state["_logos_inicio_ts"] = datetime.now()
                threading.Thread(
                    target=_thread_buscar_logos,
                    args=(d_ini.strftime("%d/%m/%Y 00:00"),
                          d_fim.strftime("%d/%m/%Y 23:59")),
                    daemon=True
                ).start()
            st.rerun()

    _logos_status_bar()

    dados = st.session_state.get("logos_dados")
    if not dados:
        return

    # ── Mapa de rotas ─────────────────────────────────────────────────────────
    st.markdown("#### 🗺️ Rotas dos Veículos ECO")
    mapa   = folium.Map(location=[-18.5, -47.5], zoom_start=7, tiles="CartoDB dark_matter")
    bounds = []

    for i, item in enumerate(dados):
        v    = item["veiculo"]
        hist = item["historico"]
        cor  = _CORES_VEICULOS[i % len(_CORES_VEICULOS)]
        desc = v.get("descricao", f"Veículo {i+1}")
        placa = v.get("placa", "")

        coords = []
        for p in hist:
            lat = p.get("latitude") or p.get("lat") or p.get("Latitude")
            lon = p.get("longitude") or p.get("lon") or p.get("lng") or p.get("Longitude")
            if lat and lon:
                try:
                    coords.append([float(lat), float(lon)])
                except Exception:
                    pass

        if len(coords) > 1:
            folium.PolyLine(coords, color=cor, weight=3, opacity=0.85,
                            tooltip=f"{desc} ({placa})").add_to(mapa)
            folium.CircleMarker(coords[-1], radius=6, color=cor, fill=True,
                                fill_color=cor, fill_opacity=1.0,
                                tooltip=f"📍 Última posição: {desc}").add_to(mapa)
            bounds.extend(coords)

    if bounds:
        lats = [c[0] for c in bounds]
        lons = [c[1] for c in bounds]
        mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    st_folium(mapa, width="100%", height=520, key="logos_mapa", returned_objects=[])

    # ── Tabela resumo ─────────────────────────────────────────────────────────
    st.markdown("#### 📊 Resumo por Veículo")
    rows = []
    for item in dados:
        v    = item["veiculo"]
        hist = item["historico"]
        rows.append({
            "Veículo":           v.get("descricao", "—"),
            "Placa":             v.get("placa", "—"),
            "Última posição":    v.get("datahoraposicao", v.get("datahora", "—")),
            "Velocidade km/h":   v.get("velocidade", "—"),
            "Hodômetro km":      v.get("hodometro", "—"),
            "Ignição":           "✅" if v.get("ignicao") else "⭕",
            "Registros rota":    len(hist),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
