"""
_eco_diario.py — Aba "Diário de Obra" para ECO Rodovias.

Fonte: ensaios_aevias.json (tipo == "Diário de Obra")
Exibe calendário mensal por profissional, agrupado por função.
Hover em cada célula mostra: obra + empreiteira + local + contrato.
"""
import os
import json
import sys
from datetime import datetime, date

import streamlit as st

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_PAGES_DIR)
if _PAGES_DIR not in sys.path: sys.path.insert(0, _PAGES_DIR)
if _ROOT_DIR  not in sys.path: sys.path.insert(0, _ROOT_DIR)

from _eco_shared import _CACHE_DIR
from _eco_funcoes import cargo_para_grupo, header_grupo, ORDEM_GRUPOS, GRUPOS

_ENSAIOS_PATH = os.path.join(_CACHE_DIR, "ensaios_aevias.json")
_BASE44_HOST  = "https://aevias-controle.base44.app"

# Data mínima: 01/03/2026 conforme requisito
_DATA_MIN = date(2026, 3, 1)

_DAY_ABBR = {0:"SEG",1:"TER",2:"QUA",3:"QUI",4:"SEX",5:"SAB",6:"DOM"}

_CSS = """
<style>
.do-wrap{padding:0 2px}
.do-table{border-collapse:collapse;font-size:.68rem;font-family:Inter,sans-serif;width:100%;min-width:600px}
.do-table th{
  background:rgba(86,110,61,.2);color:#BFCF99;padding:4px 3px;
  text-align:center;font-weight:600;border:1px solid rgba(86,110,61,.15);
  font-size:.6rem;white-space:nowrap
}
.do-table td{
  padding:4px 3px;border:1px solid rgba(255,255,255,.04);
  text-align:center;white-space:nowrap;font-size:.62rem
}
.do-table td.do-nome{
  text-align:left;font-weight:600;color:#E8EFD8;padding-left:8px;
  min-width:140px;max-width:180px;overflow:hidden;text-overflow:ellipsis
}
.do-pend{background:rgba(247,183,49,.18);color:#F7B731;border-radius:4px;cursor:help}
.do-ok{background:rgba(60,180,75,.18);color:#3cb44b;border-radius:4px;cursor:help}
.do-rep{background:rgba(230,25,75,.18);color:#e6194b;border-radius:4px;cursor:help}
.do-vazio{color:#2D3748;background:transparent}
.do-hj{outline:2px solid #F7B731 !important;outline-offset:-1px}
.do-badge{
  display:inline-block;font-size:.62rem;font-weight:700;
  padding:2px 5px;border-radius:4px
}
.do-wrap-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
</style>
"""


@st.cache_data(ttl=300, show_spinner=False)
def _carregar_diarios() -> list:
    if not os.path.exists(_ENSAIOS_PATH):
        return []
    with open(_ENSAIOS_PATH, encoding="utf-8") as f:
        dados = json.load(f)
    recs = dados if isinstance(dados, list) else dados.get("registros", dados.get("data", []))
    return [r for r in recs if r.get("tipo", "") == "Diário de Obra"]


def _parse_data(s: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def _status_cls(s: str) -> str:
    s = (s or "").lower()
    if "aprovado" in s: return "do-ok"
    if "reprovado" in s: return "do-rep"
    return "do-pend"


def _lookup_funcao(lab: str, checklist_cache: dict) -> str:
    """Busca a funcao do colaborador pelo nome no cache de checklist."""
    nome_norm = lab.strip().lower()
    for med in checklist_cache.values():
        sheets = med.get("sheets", {})
        for pessoas in sheets.values():
            for p in pessoas:
                if p.get("colaborador", "").strip().lower() in nome_norm or \
                   nome_norm in p.get("colaborador", "").strip().lower():
                    return p.get("funcao", "")
    return ""


@st.cache_data(ttl=3600, show_spinner=False)
def _checklist_cache() -> dict:
    p = os.path.join(_CACHE_DIR, "eco_checklist.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _aba_diario():
    """Aba Diário de Obra — calendário mensal por profissional, agrupado por grupo."""
    diarios = _carregar_diarios()
    if not diarios:
        st.info("Nenhum Diário de Obra encontrado em ensaios_aevias.json.")
        return

    chk_cache = _checklist_cache()

    # ── Enriquece cada registro com data e funcao ───────────────────────────
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    for r in diarios:
        r["_data"] = _parse_data(r.get("data", ""))
        r["_dstr"] = r["_data"].strftime("%Y-%m-%d") if r["_data"] else ""
        r["_funcao"] = _lookup_funcao(r.get("lab", ""), chk_cache)
        r["_grupo"] = cargo_para_grupo(r["_funcao"]) if r["_funcao"] else \
                      _grupo_por_obra(r.get("obra", ""))

    # ── Filtra: a partir de 01/03 e sem dias futuros ────────────────────────
    diarios = [r for r in diarios
               if r["_data"] and r["_data"] >= _DATA_MIN and r["_data"] <= today]

    if not diarios:
        st.info("Sem Diários de Obra a partir de 01/03/2026.")
        return

    # ── Filtro de mês ───────────────────────────────────────────────────────
    meses_disp = sorted(
        {(r["_data"].year, r["_data"].month) for r in diarios}, reverse=True
    )
    _PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
           7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
    opcoes = {f"{_PT[m]}/{y}": (y, m) for y, m in meses_disp}
    c_mes, _ = st.columns([2, 4])
    with c_mes:
        mes_lbl = st.selectbox("Mes:", list(opcoes.keys()), key="do_mes_sel")
    ano_sel, mes_sel = opcoes[mes_lbl]

    diarios_mes = [
        r for r in diarios
        if r["_data"].year == ano_sel and r["_data"].month == mes_sel
    ]
    if not diarios_mes:
        st.info(f"Sem Diários em {mes_lbl}.")
        return

    # Datas únicas no mês (sem futuro, sem antes de 01/03)
    datas_mes = sorted({r["_dstr"] for r in diarios_mes if r["_dstr"] <= today_str})

    # ── Agrupa por profissional ─────────────────────────────────────────────
    from collections import defaultdict
    por_lab = defaultdict(lambda: {"registros": defaultdict(list), "funcao": "", "grupo": "Pavimento"})
    for r in diarios_mes:
        lab = r.get("lab", "—")
        por_lab[lab]["registros"][r["_dstr"]].append(r)
        if not por_lab[lab]["funcao"] and r["_funcao"]:
            por_lab[lab]["funcao"] = r["_funcao"]
        if not por_lab[lab]["grupo"]:
            por_lab[lab]["grupo"] = r["_grupo"]

    # Resolve grupo para todos
    for lab, info in por_lab.items():
        if not info["funcao"]:
            # Tenta pela obra dos registros
            obras = [rr.get("obra","") for regs in info["registros"].values() for rr in regs]
            info["grupo"] = _grupo_por_obra(obras[0]) if obras else "Pavimento"
        else:
            info["grupo"] = cargo_para_grupo(info["funcao"])

    # KPIs
    total = len(diarios_mes)
    aprovados = sum(1 for r in diarios_mes if "aprovado" in (r.get("status","")).lower())
    pendentes  = total - aprovados
    c1, c2, c3, _ = st.columns([1, 1, 1, 3])
    c1.metric("Total no mes",  total)
    c2.metric("Aprovados",     aprovados)
    c3.metric("Pendentes",     pendentes)

    st.markdown(f"<div style='font-size:.72rem;color:#8FA882;margin-bottom:8px'>"
                f"Periodo: 01/{mes_sel:02d}/{ano_sel} ate {today.strftime('%d/%m/%Y')} "
                f"· {len(datas_mes)} dias com registros</div>",
                unsafe_allow_html=True)

    # ── Renderiza por grupo ─────────────────────────────────────────────────
    por_grupo = defaultdict(list)
    for lab, info in por_lab.items():
        por_grupo[info["grupo"]].append((lab, info))

    grupos_presentes = [g for g in ORDEM_GRUPOS if por_grupo.get(g)]

    st.markdown(_CSS, unsafe_allow_html=True)

    for grupo in grupos_presentes:
        st.markdown(header_grupo(grupo), unsafe_allow_html=True)
        labs_grupo = sorted(por_grupo[grupo], key=lambda x: x[0])

        # Monta tabela HTML
        html = ['<div class="do-wrap-scroll"><table class="do-table">']
        # Cabeçalho datas
        html.append('<thead><tr><th>Profissional</th>')
        for d in datas_mes:
            dt = datetime.strptime(d, "%Y-%m-%d")
            is_hj = (d == today_str)
            sty = "color:#F7B731;font-weight:700" if is_hj else ""
            lbl = "HOJE" if is_hj else f"{dt.day:02d}"
            sub = _DAY_ABBR[dt.weekday()]
            html.append(f'<th style="{sty}">{lbl}<br>{sub}</th>')
        html.append('<th>Total</th></tr></thead><tbody>')

        for lab, info in labs_grupo:
            regs_por_dia = info["registros"]
            total_lab = sum(len(v) for v in regs_por_dia.values())
            funcao_td = info.get("funcao", "")
            html.append(f'<tr><td class="do-nome" title="{funcao_td}">{lab}</td>')
            for d in datas_mes:
                is_hj = (d == today_str)
                recs_dia = regs_por_dia.get(d, [])
                hj_cls = " do-hj" if is_hj else ""
                if not recs_dia:
                    html.append(f'<td class="do-vazio{hj_cls}">—</td>')
                else:
                    # Tooltip com detalhes
                    tooltip = " | ".join(
                        f"{r.get('obra','?')} · {r.get('empreiteira','?')} · {r.get('local','?')}"
                        for r in recs_dia
                    )
                    pior = ("do-rep" if any("reprovado" in (r.get("status","")).lower() for r in recs_dia)
                            else "do-pend" if any("aprovado" not in (r.get("status","")).lower() for r in recs_dia)
                            else "do-ok")
                    n = len(recs_dia)
                    lbl_cel = f"{n}" if n > 1 else "OK" if pior == "do-ok" else "PND"
                    html.append(
                        f'<td class="{hj_cls}" title="{tooltip}">'
                        f'<span class="do-badge {pior}">{lbl_cel}</span></td>'
                    )
            html.append(f'<td style="color:#8FA882;font-weight:600">{total_lab}</td></tr>')

        html.append('</tbody></table></div>')
        st.markdown("".join(html), unsafe_allow_html=True)

        # Links dos relatórios do grupo (expander)
        with st.expander(f"Relatorios — {GRUPOS[grupo]['label']} ({len(labs_grupo)} pessoas)", expanded=False):
            for lab, info in labs_grupo:
                st.markdown(f"**{lab}**", help=info.get("funcao",""))
                links = []
                for d in datas_mes:
                    for r in info["registros"].get(d, []):
                        url = r.get("reportUrl","")
                        if url:
                            full_url = url if url.startswith("http") else f"{_BASE44_HOST}{url}"
                            data_fmt = r["_data"].strftime("%d/%m") if r["_data"] else d
                            links.append(f"[{data_fmt} — {r.get('obra','?')} ({r.get('status','?')})]({full_url})")
                if links:
                    st.markdown("  \n".join(links))
                else:
                    st.caption("Sem links disponíveis.")


def _grupo_por_obra(obra: str) -> str:
    """Fallback: infere grupo pela obra quando não há funcao."""
    o = (obra or "").lower()
    if "sst" in o or "segurança" in o or "seguranca" in o:
        return "SST"
    if "topografia" in o:
        return "Topografia"
    if "escritório" in o or "escritorio" in o:
        return "Escritório"
    return "Pavimento"
