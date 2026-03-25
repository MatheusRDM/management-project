"""
_eco_resumo.py — Resumo diário por profissional.
Combina dados de: Checklist APP + Ensaios AEVIAS + Rastreamento Logos.
Layout Instagram-scroll, mobile-first.
"""
import sys, os, json
from datetime import datetime, date, timedelta
from collections import defaultdict
from calendar import monthrange

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_PAGES_DIR)
if _PAGES_DIR not in sys.path: sys.path.insert(0, _PAGES_DIR)
if _ROOT_DIR  not in sys.path: sys.path.insert(0, _ROOT_DIR)

import streamlit as st

from _eco_shared import (
    COR_TEXT, COR_MUTED,
    _BASE_DIR, _CACHE_DIR, _IS_CLOUD,
)
from _eco_funcoes import cargo_para_grupo, header_grupo, ORDEM_GRUPOS, GRUPOS

_BASE44_URL = "https://aevias-controle.base44.app"

# ─── CSS ────────────────────────────────────────────────────────────────────
_CSS_RESUMO = """
<style>
/* Resumo page — Instagram scroll */
.rs-header{margin-bottom:12px}
.rs-header h2{font-size:1.1rem;font-weight:700;color:#E8EFD8;margin:0}
.rs-header p{font-size:.7rem;color:#6b7f8d;margin:2px 0 0}

/* Person card */
.rs-card{background:rgba(18,25,38,.85);backdrop-filter:blur(12px);
  -webkit-backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.06);
  border-radius:16px;padding:16px;margin-bottom:14px;
  transition:border-color .2s}
.rs-card:hover{border-color:rgba(123,191,106,.2)}

/* Person header */
.rs-phdr{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.rs-avatar{width:44px;height:44px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:.9rem;font-weight:700;color:#fff;flex-shrink:0;
  background:linear-gradient(135deg,#566E3D,#7BBF6A)}
.rs-pname{font-size:.95rem;font-weight:700;color:#E8EFD8;flex:1;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rs-prole{font-size:.62rem;color:#6b7f8d;margin-top:1px}

/* Day section */
.rs-day{background:rgba(0,0,0,.12);border-radius:12px;padding:12px;
  margin-bottom:8px}
.rs-day-hdr{display:flex;align-items:center;justify-content:space-between;
  margin-bottom:8px}
.rs-day-title{font-size:.78rem;font-weight:700;color:#C8D8A8}
.rs-day-date{font-size:.62rem;color:#6b7f8d}

/* Metric row */
.rs-metrics{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));
  gap:6px;margin-bottom:8px}
.rs-metric{background:rgba(255,255,255,.04);border-radius:10px;padding:8px 10px;
  text-align:center}
.rs-metric .mv{font-size:1rem;font-weight:700;line-height:1.2}
.rs-metric .ml{font-size:.55rem;color:#6b7f8d;letter-spacing:.03em;margin-top:2px}

/* Status badges inline */
.rs-badges{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px}
.rs-badge{font-size:.6rem;font-weight:600;padding:3px 9px;border-radius:12px;
  display:inline-flex;align-items:center;gap:3px}
.rs-badge.rb-ok{background:rgba(60,180,75,.15);color:#3cb44b}
.rs-badge.rb-pend{background:rgba(247,183,49,.15);color:#F7B731}
.rs-badge.rb-miss{background:rgba(255,107,107,.12);color:#FF6B6B}
.rs-badge.rb-ne{background:rgba(58,74,94,.4);color:#7a90a8}

/* Diário de obra description */
.rs-diario{background:rgba(76,201,240,.06);border:1px solid rgba(76,201,240,.15);
  border-radius:10px;padding:10px 12px;margin-top:6px;
  font-size:.72rem;color:#C8D8A8;line-height:1.5}
.rs-diario-label{font-size:.6rem;font-weight:700;color:#4CC9F0;
  margin-bottom:4px;letter-spacing:.04em}

/* Ignition status */
.rs-ign{display:inline-flex;align-items:center;gap:4px;
  font-size:.65rem;font-weight:600;padding:3px 10px;border-radius:12px}
.rs-ign.ig-on{background:rgba(123,191,106,.15);color:#7BBF6A;
  border:1px solid rgba(123,191,106,.3)}
.rs-ign.ig-off{background:rgba(255,71,87,.1);color:#FF4757;
  border:1px solid rgba(255,71,87,.2)}

/* Section divider */
.rs-divider{height:1px;background:rgba(255,255,255,.04);margin:6px 0}

/* No data */
.rs-empty{text-align:center;padding:20px;color:#6b7f8d;font-size:.8rem}
</style>
"""


def _carregar_ensaios_resumo():
    """Carrega ensaios do cache."""
    p = os.path.join(_CACHE_DIR, "ensaios_aevias.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []


def _carregar_checklist_resumo():
    """Carrega checklist do cache."""
    p = os.path.join(_CACHE_DIR, "eco_checklist.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _get_rastreamento_data():
    """Obtém dados de rastreamento do session_state."""
    veiculos = st.session_state.get("logos_veiculos", [])
    if not veiculos:
        return []
    try:
        from _eco_rast_api import _parse_eco
        return [_parse_eco(v, i) for i, v in enumerate(veiculos)]
    except Exception:
        return []


def _aba_resumo():
    """Aba Resumo — análise diária por profissional."""

    st.markdown(_CSS_RESUMO, unsafe_allow_html=True)
    st.markdown(
        '<div class="rs-header">'
        '<h2>Resumo Diário por Profissional</h2>'
        '<p>Checklist + Ensaios + Rastreamento combinados</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    DAY_NAMES = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta",
                 4: "Sexta", 5: "Sábado", 6: "Domingo"}

    # ── Load all data sources ──────────────────────────────────────────────
    ensaios_raw = _carregar_ensaios_resumo()
    checklist_cache = _carregar_checklist_resumo()
    rastr_itens = _get_rastreamento_data()

    # ── Build ensaios index: profissional → date → list of records ─────────
    ens_by_prof: dict = defaultdict(lambda: defaultdict(list))
    for e in ensaios_raw:
        prof = (e.get("lab") or e.get("profissional") or "").strip()
        if not prof:
            continue
        try:
            d = datetime.strptime(e["data"], "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            continue
        ens_by_prof[prof][d].append(e)

    # ── Build checklist index: colaborador → date → status ─────────────────
    ck_by_person: dict = defaultdict(dict)
    # Use most recent medição
    if checklist_cache:
        meds = sorted(checklist_cache.keys())
        latest_med = meds[-1] if meds else None
        if latest_med:
            entry = checklist_cache[latest_med]
            for sheet_name, people in entry.get("sheets", {}).items():
                for p in people:
                    nome = p.get("colaborador", "").strip()
                    if not nome:
                        continue
                    for d, v in p.get("dias", {}).items():
                        ck_by_person[nome][d] = v

    # ── Build rastreamento index: motorista → data (com fuzzy match) ─────────
    rastr_by_motorista: dict[str, dict] = {}
    for it in rastr_itens:
        m = it.get("motorista", "").strip()
        if m:
            rastr_by_motorista[m] = it

    def _normalizar(nome: str) -> set[str]:
        """Retorna set de tokens longos (>=4 chars) do nome em minúsculas."""
        import unicodedata
        s = unicodedata.normalize("NFD", nome.lower())
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return {t for t in s.split() if len(t) >= 4}

    # Pré-computa tokens dos motoristas
    _rastr_tokens: list[tuple[set, dict]] = [
        (_normalizar(m), it) for m, it in rastr_by_motorista.items()
    ]

    def _buscar_rastr(nome_pessoa: str) -> dict | None:
        """Tenta localizar o veículo do colaborador por sobreposição de tokens."""
        tokens_p = _normalizar(nome_pessoa)
        if not tokens_p:
            return None
        melhor, melhor_n = None, 0
        for tokens_m, it in _rastr_tokens:
            n = len(tokens_p & tokens_m)
            if n > melhor_n:
                melhor_n, melhor = n, it
        return melhor if melhor_n >= 1 else None

    # Compatibilidade: mantém rastr_by_person para lookup direto
    rastr_by_person: dict[str, dict] = rastr_by_motorista

    # ── Collect all unique person names ────────────────────────────────────
    all_people = set()
    all_people.update(ens_by_prof.keys())
    all_people.update(ck_by_person.keys())
    all_people.update(rastr_by_person.keys())

    if not all_people:
        st.markdown('<div class="rs-empty">Nenhum dado encontrado. Carregue Checklist, Ensaios ou Rastreamento.</div>',
                    unsafe_allow_html=True)
        return

    # ── DATA MÍNIMA: 01/03/2026 ────────────────────────────────────────────
    _DATA_MIN = date(2026, 3, 1)

    # ── Filtro 1: Mês ──────────────────────────────────────────────────────
    _PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
           7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
    # Meses disponíveis: de 03/2026 até hoje
    meses_disp = []
    cur = _DATA_MIN.replace(day=1)
    while cur <= today.replace(day=1):
        meses_disp.append((cur.year, cur.month))
        m2 = cur.month + 1
        cur = cur.replace(year=cur.year + (1 if m2 > 12 else 0),
                          month=(m2 - 1) % 12 + 1)
    meses_disp.reverse()
    opcoes_mes = {f"{_PT[m]}/{y}": (y, m) for y, m in meses_disp}

    col_mes, col_dia, col_obra, col_prof = st.columns([2, 2, 2, 2])
    with col_mes:
        mes_lbl = st.selectbox("Mes:", list(opcoes_mes.keys()), key="rs_mes")
    ano_sel, mes_sel = opcoes_mes[mes_lbl]

    # ── Filtro 2: Dia do mês ───────────────────────────────────────────────
    _, ultimo_dia = monthrange(ano_sel, mes_sel)
    dias_disp = list(range(1, min(ultimo_dia, today.day if (ano_sel == today.year and mes_sel == today.month) else ultimo_dia) + 1))
    opcoes_dia = {str(d): d for d in reversed(dias_disp)}
    opcoes_dia = {"Todos os dias": 0, **opcoes_dia}
    with col_dia:
        dia_lbl = st.selectbox("Dia:", list(opcoes_dia.keys()), key="rs_dia")
    dia_sel = opcoes_dia[dia_lbl]

    # Calcula dates_range
    if dia_sel == 0:
        d_ini = max(date(ano_sel, mes_sel, 1), _DATA_MIN)
        d_fim = date(ano_sel, mes_sel, min(ultimo_dia, today.day if (ano_sel == today.year and mes_sel == today.month) else ultimo_dia))
        dates_range = [(d_ini + timedelta(days=i)).strftime("%Y-%m-%d")
                       for i in range((d_fim - d_ini).days + 1)]
    else:
        d_sel = date(ano_sel, mes_sel, dia_sel)
        dates_range = [d_sel.strftime("%Y-%m-%d")]
    dates_range = [d for d in dates_range if d >= _DATA_MIN.strftime("%Y-%m-%d")]

    # ── Filtro 3: Tipo de Obra ─────────────────────────────────────────────
    obras_todas = sorted({
        e.get("obra","") for e in ensaios_raw
        if e.get("obra") and e.get("tipo") != "Diário de Obra"
    })
    with col_obra:
        obra_sel = st.selectbox("Tipo de Obra:", ["Todas"] + obras_todas, key="rs_obra")

    # ── Filtro 4: Profissional ─────────────────────────────────────────────
    people_sorted = sorted(all_people)
    with col_prof:
        prof_sel = st.selectbox("Profissional:", ["Todos"] + people_sorted, key="rs_prof")
    if prof_sel != "Todos":
        people_sorted = [prof_sel]

    # Filtra ensaios por obra selecionada
    if obra_sel != "Todas":
        ens_by_prof_filtrado = defaultdict(lambda: defaultdict(list))
        for prof, dias in ens_by_prof.items():
            for d, recs in dias.items():
                recs_f = [r for r in recs if r.get("obra") == obra_sel]
                if recs_f:
                    ens_by_prof_filtrado[prof][d] = recs_f
    else:
        ens_by_prof_filtrado = ens_by_prof

    # ── Agrupa pessoas por grupo de trabalho ──────────────────────────────
    funcao_por_pessoa: dict[str, str] = {}
    for med in checklist_cache.values():
        for pessoas in med.get("sheets", {}).values():
            for p in pessoas:
                nome = p.get("colaborador","").strip()
                func = p.get("funcao","")
                if nome and func:
                    funcao_por_pessoa[nome] = func

    por_grupo_rs = defaultdict(list)
    for person in people_sorted:
        func = funcao_por_pessoa.get(person, "")
        g = cargo_para_grupo(func)
        por_grupo_rs[g].append(person)

    grupos_rs = [g for g in ORDEM_GRUPOS if por_grupo_rs.get(g)]

    # ── Render cards por grupo (expander por grupo + expander por pessoa) ─────
    for grupo_rs in grupos_rs:
        g_info = GRUPOS[grupo_rs]
        n_grupo = len(por_grupo_rs[grupo_rs])

        with st.expander(f"{g_info['label']}  ({n_grupo} pessoas)", expanded=True):
            st.markdown(header_grupo(grupo_rs), unsafe_allow_html=True)

            for person in por_grupo_rs[grupo_rs]:
                ens_data = ens_by_prof_filtrado.get(person, {})
                ck_data  = ck_by_person.get(person, {})
                rastr    = _buscar_rastr(person)   # fuzzy match por tokens

                has_data = any(d in ens_data or d in ck_data for d in dates_range) or bool(rastr)
                if not has_data:
                    continue

                role = funcao_por_pessoa.get(person, "")
                initials = "".join(w[0] for w in person.split()[:2]).upper() if person else "?"

                # Status ignição para label do expander
                ign_label = ""
                if rastr:
                    if rastr.get("ignicao"):
                        v = rastr.get("velocidade", 0)
                        ign_label = f" · {int(v)} km/h" if v > 3 else " · Ligado"
                    else:
                        ign_label = " · Desligado"

                with st.expander(f"{person}{ign_label}  —  {role}", expanded=False):

                    # ── Rastreamento (veículo) ─────────────────────────────
                    if rastr:
                        st.markdown(
                            '<div style="font-size:.65rem;font-weight:700;color:#4CC9F0;'
                            'letter-spacing:.06em;margin-bottom:4px">VEICULO / RASTREAMENTO</div>',
                            unsafe_allow_html=True,
                        )
                        h_dir  = rastr.get("tempo_dir_h", 0)
                        h_par  = rastr.get("tempo_par_min", 0)
                        km_odo = rastr.get("odometro", 0)
                        cidade = rastr.get("cidade", "—")
                        uf     = rastr.get("uf", "")
                        placa  = rastr.get("placa", "")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Dirigindo",  f"{h_dir:.1f}h")
                        c2.metric("Parado",     f"{h_par:.0f}min")
                        c3.metric("Hodometro",  f"{km_odo:,} km")
                        c4.metric("Local",      f"{cidade} {uf}")
                        st.caption(f"Placa: {placa}")
                        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

                    # ── Checklist + Diário + Ensaios por dia ───────────────
                    for d in reversed(dates_range):
                        try:
                            dt_obj = datetime.strptime(d, "%Y-%m-%d")
                        except Exception:
                            continue
                        day_all   = ens_data.get(d, [])
                        ck_val    = ck_data.get(d)
                        day_ck    = [e for e in day_all if str(e.get("tipo","")).lower().startswith("checklist")]
                        day_do    = [e for e in day_all if "diário" in str(e.get("tipo","")).lower()
                                     or "diario" in str(e.get("tipo","")).lower()]
                        day_ens_r = [e for e in day_all if e not in day_ck and e not in day_do]

                        if not day_all and not ck_val:
                            continue

                        day_name  = DAY_NAMES.get(dt_obj.weekday(), "")
                        day_label = f"{day_name} {dt_obj.day:02d}/{dt_obj.month:02d}"
                        parts = [
                            f'<div class="rs-day">'
                            f'<div class="rs-day-hdr">'
                            f'<span class="rs-day-title">{day_label}</span>'
                            f'<span class="rs-day-date">{d}</span>'
                            f'</div>'
                        ]

                        def _dot_row(e):
                            tipo   = e.get("tipo","—")
                            obra   = e.get("obra","")
                            status = e.get("status","")
                            url    = e.get("reportUrl","")
                            s_l    = status.lower()
                            dot_c  = ("#3cb44b" if "aprovado" in s_l else
                                      "#F7B731" if "pendente" in s_l else
                                      "#FF6B6B" if "reprovado" in s_l else "#6b7f8d")
                            link = (f'<a href="{_BASE44_URL}{url}" target="_blank" '
                                    f'style="color:#4CC9F0;font-size:.6rem;margin-left:4px">Ver</a>'
                                    if url else "")
                            return (
                                f'<div style="display:flex;align-items:center;gap:5px;padding:2px 0">'
                                f'<span style="width:6px;height:6px;border-radius:50%;background:{dot_c};flex-shrink:0"></span>'
                                f'<span style="font-size:.68rem;color:#C8D8A8">{tipo}</span>'
                                f'<span style="font-size:.58rem;color:#6b7f8d">{obra}</span>'
                                f'<span style="font-size:.58rem;color:{dot_c};font-weight:600">{status}</span>'
                                f'{link}</div>'
                            )

                        # Bloco CHECKLIST
                        if ck_val or day_ck:
                            vu = str(ck_val or "").upper().strip()
                            ck_cor = ("#3cb44b" if vu=="OK" else
                                      "#e6194b" if vu in ("COBRAR","COBRE") else
                                      "#7a90a8" if vu in ("N/E","NE") else "#566E3D")
                            ck_lbl = {"OK":"OK", "COBRAR":"Pendente","COBRE":"Pendente",
                                      "N/E":"N/E","NE":"N/E"}.get(vu, vu or "—")
                            parts.append(
                                f'<div style="margin:4px 0 2px;font-size:.6rem;font-weight:700;'
                                f'color:#BFCF99;letter-spacing:.04em">CHECKLIST</div>'
                                f'<div style="display:flex;align-items:center;gap:6px;padding:2px 0">'
                                f'<span style="background:{ck_cor}22;color:{ck_cor};font-size:.62rem;'
                                f'font-weight:700;border-radius:4px;padding:1px 6px">{ck_lbl}</span>'
                                + "".join(_dot_row(e) for e in day_ck)
                                + '</div>'
                            )

                        # Bloco DIÁRIO DE OBRA
                        if day_do:
                            parts.append(
                                f'<div style="margin:4px 0 2px;font-size:.6rem;font-weight:700;'
                                f'color:#4CC9F0;letter-spacing:.04em">DIARIO DE OBRA</div>'
                            )
                            parts.extend(_dot_row(e) for e in day_do)

                        # Bloco ENSAIOS
                        if day_ens_r:
                            parts.append(
                                f'<div style="margin:4px 0 2px;font-size:.6rem;font-weight:700;'
                                f'color:#7BBF6A;letter-spacing:.04em">ENSAIOS</div>'
                            )
                            parts.extend(_dot_row(e) for e in day_ens_r)

                        parts.append('</div>')  # close rs-day
                        st.markdown("".join(parts), unsafe_allow_html=True)
