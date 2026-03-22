"""
_eco_checklist.py — checklist tab for ECO Rodovias.
"""
import sys
import os

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_PAGES_DIR)
if _PAGES_DIR not in sys.path: sys.path.insert(0, _PAGES_DIR)
if _ROOT_DIR  not in sys.path: sys.path.insert(0, _ROOT_DIR)

import streamlit as st
import json
from datetime import datetime

from _eco_shared import (
    COR_PRIMARY, COR_ACCENT, COR_BG, COR_CARD, COR_BORDER,
    COR_TEXT, COR_MUTED, COR_OK, COR_COBRAR, COR_NE, COR_ELAB,
    PLOTLY_LAYOUT, PLOTLY_CONFIG,
    _BASE_DIR, _CACHE_DIR, _Y_BASE, _IS_CLOUD,
)


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
# ABA CHECKLIST
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
