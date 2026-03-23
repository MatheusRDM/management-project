"""
_eco_despacho.py — aba Despacho para ECO Rodovias.
Layout MOBILE-FIRST: zero st.columns nos formulários,
tudo empilhado verticalmente, CSS grid responsivo para HTML puro.
"""
import sys, os

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_PAGES_DIR)
if _PAGES_DIR not in sys.path: sys.path.insert(0, _PAGES_DIR)
if _ROOT_DIR  not in sys.path: sys.path.insert(0, _ROOT_DIR)

import streamlit as st
import json
import pandas as pd
from datetime import datetime, date

from _eco_shared import (
    COR_ACCENT, COR_BG, COR_TEXT, COR_MUTED, COR_OK,
    _CACHE_DIR,
)

# ── Constantes ────────────────────────────────────────────────────────────────
_SETORES = {
    "Minas Goiás": [
        "km 0–50 (Uberlândia)",
        "km 50–100 (Araguari)",
        "km 100–150 (Catalão)",
        "km 150–200 (Cumari)",
        "km 200+ (Divisa GO/MG)",
    ],
    "Cerrado": [
        "km 0–50 (Uberlândia Norte)",
        "km 50–100 (Monte Alegre)",
        "km 100–150 (Patrocínio)",
        "km 150–200 (Serra do Salitre)",
        "km 200+ (Patos de Minas)",
    ],
}

_STATUS_OPTIONS = ["OK", "ELB", "N/E", "FALTA"]
_STATUS_COLORS = {
    "OK":    ("#3cb44b", "rgba(60,180,75,0.25)"),
    "ELB":   ("#6ec6ff", "rgba(67,99,216,0.25)"),
    "N/E":   ("#7a90a8", "rgba(58,74,94,0.4)"),
    "FALTA": ("#ff5577", "rgba(230,25,75,0.25)"),
}


# =============================================================================
# I/O
# =============================================================================

def _checklist_path():
    return os.path.join(_CACHE_DIR, "eco_checklist.json")

def _despacho_path(dt):
    return os.path.join(_CACHE_DIR, f"eco_despacho_{dt.isoformat()}.json")

def _carregar_checklist():
    p = _checklist_path()
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}

def _carregar_despacho(dt):
    p = _despacho_path(dt)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}

def _salvar_despacho(dt, data):
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_despacho_path(dt), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _obter_workers_hoje(checklist, dt):
    if not checklist:
        return {}
    med_key = list(checklist.keys())[-1]
    sheets = checklist[med_key].get("sheets", {})
    dt_str = dt.isoformat()
    result = {}
    for sheet_name, workers in sheets.items():
        lista = []
        for w in workers:
            status_dia = w.get("dias", {}).get(dt_str)
            lista.append({
                "colaborador": w["colaborador"],
                "funcao":      w.get("funcao", ""),
                "status":      status_dia if status_dia else None,
            })
        result[sheet_name] = lista
    return result

def _obter_veiculos_logos():
    from _eco_rast_api import _parse_eco
    raw = st.session_state.get("logos_veiculos", [])
    if not raw:
        return []
    return [_parse_eco(v, i) for i, v in enumerate(raw)]


# =============================================================================
# CSS MOBILE-FIRST
# =============================================================================

def _inject_css():
    st.markdown("""<style>
    /* ─── KPI grid: 2 col mobile → 3 tablet → 5 desktop ─── */
    .d-kpi-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-bottom: 14px;
    }
    @media(min-width:640px) { .d-kpi-grid { grid-template-columns: repeat(3,1fr); } }
    @media(min-width:960px) { .d-kpi-grid { grid-template-columns: repeat(5,1fr); } }

    .d-kpi {
        background: rgba(26,31,46,0.85);
        border: 1px solid rgba(86,110,61,0.35);
        border-radius: 10px;
        padding: 12px 8px;
        text-align: center;
    }
    .d-kpi .v {
        font-family:'Poppins',sans-serif;
        font-size: 1.5rem; font-weight:700; line-height:1.1;
    }
    .d-kpi .l {
        font-family:'Poppins',sans-serif;
        font-size:.65rem; color:#8FA882;
        text-transform:uppercase; letter-spacing:.04em; margin-top:3px;
    }

    /* ─── Section card ─── */
    .d-sec {
        background: rgba(26,31,46,0.85);
        border: 1px solid rgba(86,110,61,0.35);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .d-sec h3 {
        font-family:'Poppins',sans-serif;
        font-size:.88rem; font-weight:600;
        color:#BFCF99; margin:0 0 8px 0;
    }

    /* ─── Worker card (vertical stack, mobile friendly) ─── */
    .d-wcard {
        background: rgba(13,27,42,0.5);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 6px;
        font-family:'Poppins',sans-serif;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
    }
    .d-wcard .wn {
        font-size:.82rem; font-weight:500; color:#E8EFD8;
        flex: 1 1 100%;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .d-wcard .wf {
        font-size:.68rem; color:#8FA882;
        flex: 1 1 auto;
    }
    .d-badge {
        display:inline-block; padding:3px 12px;
        border-radius:5px; font-family:'Poppins',sans-serif;
        font-size:.72rem; font-weight:600; white-space:nowrap;
        flex-shrink: 0;
    }
    /* desktop: name and badge on same line */
    @media(min-width:640px) {
        .d-wcard .wn { flex: 1 1 auto; }
    }

    /* ─── Frota grid: 1 → 2 → 3 cols ─── */
    .d-frota-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
    }
    @media(min-width:640px) { .d-frota-grid { grid-template-columns: repeat(2,1fr); } }
    @media(min-width:960px) { .d-frota-grid { grid-template-columns: repeat(3,1fr); } }

    .d-fcard {
        background: rgba(26,31,46,0.7);
        border: 1px solid rgba(86,110,61,0.25);
        border-radius: 8px;
        padding: 12px;
        font-family:'Poppins',sans-serif;
    }
    .d-fcard .pl { font-size:.95rem; font-weight:700; color:#BFCF99; }
    .d-fcard .inf { font-size:.72rem; color:#8FA882; margin-top:4px; line-height:1.5; }
    .d-fcard .son { color:#7BBF6A; }
    .d-fcard .sof { color:#FF4757; }

    /* ─── Presença card (label + select empilhados) ─── */
    .d-pcard {
        background: rgba(13,27,42,0.5);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 10px 12px 4px 12px;
        margin-bottom: 2px;
        font-family:'Poppins',sans-serif;
    }
    .d-pcard .pn { font-size:.82rem; font-weight:500; color:#E8EFD8; }
    .d-pcard .pf { font-size:.68rem; color:#8FA882; }

    /* ─── Distribuição card ─── */
    .d-dcard {
        background: rgba(13,27,42,0.5);
        border: 1px solid rgba(86,110,61,0.15);
        border-radius: 8px;
        padding: 10px 12px 4px 12px;
        margin-bottom: 2px;
        font-family:'Poppins',sans-serif;
    }
    .d-dcard .dn { font-size:.84rem; font-weight:600; color:#E8EFD8; }
    .d-dcard .df { font-size:.68rem; color:#8FA882; margin-bottom:4px; }

    /* ─── Contrato divider ─── */
    .d-contrato {
        font-family:'Poppins',sans-serif;
        font-size:.85rem; font-weight:600;
        color:#BFCF99; padding:10px 0 6px 0;
    }

    /* ─── Streamlit overrides for mobile touch ─── */
    .d-pcard + div .stSelectbox,
    .d-dcard + div .stSelectbox {
        margin-bottom: 10px;
    }
    </style>""", unsafe_allow_html=True)


# =============================================================================
# HELPERS
# =============================================================================

def _kpi(val, label, cor="#BFCF99"):
    return f'<div class="d-kpi"><div class="v" style="color:{cor}">{val}</div><div class="l">{label}</div></div>'

def _badge(s):
    if s:
        su = str(s).upper().strip()
        if su == "OK":
            c, bg = _STATUS_COLORS["OK"]
        elif su in ("ELAB.", "ELAB", "ELB"):
            c, bg = _STATUS_COLORS["ELB"]; su = "ELB"
        elif su in ("N/E", "NE"):
            c, bg = _STATUS_COLORS["N/E"]; su = "N/E"
        else:
            c, bg = _STATUS_COLORS["FALTA"]
        lbl = su[:4]
    else:
        c, bg = "#ff5577", "rgba(230,25,75,0.25)"; lbl = "—"
    return f'<span class="d-badge" style="background:{bg};color:{c}">{lbl}</span>'

def _status_idx(current):
    cu = str(current).upper().strip() if current else ""
    for j, opt in enumerate(_STATUS_OPTIONS):
        if cu.startswith(opt[:2]):
            return j
    return 0


# =============================================================================
# SEÇÕES
# =============================================================================

def _render_visao(workers_hoje, dt):
    total = sum(len(v) for v in workers_hoje.values())
    ok  = sum(1 for ws in workers_hoje.values() for w in ws if w["status"] and str(w["status"]).upper().strip() == "OK")
    elb = sum(1 for ws in workers_hoje.values() for w in ws if w["status"] and str(w["status"]).upper().strip() in ("ELAB.", "ELAB", "ELB"))
    ne  = sum(1 for ws in workers_hoje.values() for w in ws if w["status"] and str(w["status"]).upper().strip() in ("N/E", "NE"))
    falta = total - ok - elb - ne

    h = '<div class="d-kpi-grid">'
    h += _kpi(total, "Total",    COR_ACCENT)
    h += _kpi(ok,    "OK",       COR_OK)
    h += _kpi(elb,   "Elaboração", "#6ec6ff")
    h += _kpi(ne,    "N/E",      COR_MUTED)
    h += _kpi(falta, "Sem Status", "#ff5577")
    h += '</div>'
    st.markdown(h, unsafe_allow_html=True)

    for sn, workers in workers_hoje.items():
        h = f'<div class="d-sec"><h3>🛣️ {sn} — {dt.strftime("%d/%m/%Y")}</h3>'
        for w in workers:
            b = _badge(w["status"])
            h += f'''<div class="d-wcard">
                <span class="wn">{w["colaborador"]}</span>
                {b}
                <span class="wf">{w["funcao"]}</span>
            </div>'''
        h += '</div>'
        st.markdown(h, unsafe_allow_html=True)


def _render_presenca(workers_hoje, dt, despacho):
    st.markdown(f'''<div style="font-family:'Poppins',sans-serif;margin-bottom:8px">
        <span style="font-size:.95rem;font-weight:600;color:#BFCF99">✏️ Presença</span>
        <span style="font-size:.75rem;color:#8FA882"> — {dt.strftime("%d/%m/%Y")}</span>
    </div>''', unsafe_allow_html=True)
    st.caption("Altere o status e salve ao final.")

    presenca = despacho.get("presenca", {})

    for sn, workers in workers_hoje.items():
        st.markdown(f'<div class="d-contrato">🛣️ {sn}</div>', unsafe_allow_html=True)

        for w in workers:
            nome = w["colaborador"]
            current = presenca.get(nome, w["status"] or "")

            # Card com nome + função (HTML puro) → select logo abaixo (Streamlit nativo, full width)
            st.markdown(f'''<div class="d-pcard">
                <div class="pn">{nome}</div>
                <div class="pf">{w["funcao"]}</div>
            </div>''', unsafe_allow_html=True)

            presenca[nome] = st.selectbox(
                nome, _STATUS_OPTIONS, index=_status_idx(current),
                key=f"dp_{sn}_{nome}", label_visibility="collapsed",
            )

    return presenca


def _render_distribuicao(workers_hoje, dt, despacho):
    st.markdown('''<div style="font-family:'Poppins',sans-serif;margin-bottom:8px">
        <span style="font-size:.95rem;font-weight:600;color:#BFCF99">🗺️ Distribuição</span>
    </div>''', unsafe_allow_html=True)
    st.caption("Atribua veículo e setor para cada colaborador ativo.")

    veiculos = _obter_veiculos_logos()
    placas = (["(sem veículo)"] + [f"{v['placa']} — {v['motorista']}" for v in veiculos]) if veiculos else ["(sem veículo)"]

    distribuicao = despacho.get("distribuicao", {})

    for sn, workers in workers_hoje.items():
        ativos = [w for w in workers
                  if str(despacho.get("presenca", {}).get(w["colaborador"], w["status"] or "")).upper().strip()
                  in ("OK", "ELB", "ELAB.", "ELAB")]
        if not ativos:
            st.info(f"Nenhum colaborador ativo em **{sn}** hoje.")
            continue

        st.markdown(f'<div class="d-contrato">🛣️ {sn}</div>', unsafe_allow_html=True)
        setores_opts = ["(não atribuído)"] + _SETORES.get(sn, ["Setor A", "Setor B", "Setor C"])

        for w in ativos:
            nome = w["colaborador"]
            dist_w = distribuicao.get(nome, {})

            # Card header
            st.markdown(f'''<div class="d-dcard">
                <div class="dn">{nome}</div>
                <div class="df">{w["funcao"]}</div>
            </div>''', unsafe_allow_html=True)

            # Veículo select (full width, stacked)
            vei_idx = 0
            old_vei = dist_w.get("veiculo", "")
            for j, p in enumerate(placas):
                if old_vei and old_vei in p:
                    vei_idx = j; break
            veiculo_sel = st.selectbox(
                "🚗 Veículo", placas, index=vei_idx,
                key=f"dv_{sn}_{nome}",
            )

            # Setor select (full width, stacked)
            set_idx = 0
            old_set = dist_w.get("setor", "")
            for j, s in enumerate(setores_opts):
                if old_set and old_set in s:
                    set_idx = j; break
            setor_sel = st.selectbox(
                "📍 Setor/km", setores_opts, index=set_idx,
                key=f"ds_{sn}_{nome}",
            )

            distribuicao[nome] = {
                "veiculo": veiculo_sel if veiculo_sel != "(sem veículo)" else "",
                "setor":   setor_sel if setor_sel != "(não atribuído)" else "",
            }

        st.markdown("---")

    return distribuicao


def _render_frota(veiculos):
    st.markdown('''<div style="font-family:'Poppins',sans-serif;margin-bottom:8px">
        <span style="font-size:.95rem;font-weight:600;color:#BFCF99">🚗 Frota</span>
    </div>''', unsafe_allow_html=True)

    if not veiculos:
        st.info("Acesse a aba **🛰️ Rastreamento** e clique **🔄 Atualizar** para carregar a frota.")
        return

    on  = [v for v in veiculos if v.get("ignicao")]
    off = [v for v in veiculos if not v.get("ignicao")]

    kh = '<div class="d-kpi-grid" style="grid-template-columns:repeat(3,1fr)">'
    kh += _kpi(len(veiculos), "Total", COR_ACCENT)
    kh += _kpi(len(on),  "ON",  "#7BBF6A")
    kh += _kpi(len(off), "OFF", "#FF4757")
    kh += '</div>'
    st.markdown(kh, unsafe_allow_html=True)

    cards = '<div class="d-frota-grid">'
    for v in veiculos:
        ic = "son" if v.get("ignicao") else "sof"
        il = "🟢 ON" if v.get("ignicao") else "🔴 OFF"
        vel = v.get("velocidade", 0)
        vs = f"{int(vel)} km/h" if vel and vel > 0 else "Parado"
        cu = f"{v.get('cidade','—')}/{v.get('uf','—')}"
        cards += f'''<div class="d-fcard">
            <div class="pl">🚗 {v.get("placa","—")}</div>
            <div class="inf">
                {v.get("motorista","—")}<br>
                {v.get("contrato","—")}<br>
                <span class="{ic}">{il}</span> · {vs}<br>
                📍 {cu}
            </div>
        </div>'''
    cards += '</div>'
    st.markdown(cards, unsafe_allow_html=True)


def _render_relatorio(workers_hoje, despacho, dt):
    st.markdown(f'''<div style="font-family:'Poppins',sans-serif;margin-bottom:8px">
        <span style="font-size:.95rem;font-weight:600;color:#BFCF99">📄 Relatório</span>
        <span style="font-size:.75rem;color:#8FA882"> — {dt.strftime("%d/%m/%Y")}</span>
    </div>''', unsafe_allow_html=True)

    presenca = despacho.get("presenca", {})
    distribuicao = despacho.get("distribuicao", {})

    rows = []
    for sn, workers in workers_hoje.items():
        for w in workers:
            nome = w["colaborador"]
            status = presenca.get(nome, w["status"] or "—")
            dist = distribuicao.get(nome, {})
            rows.append({
                "Contrato":    sn,
                "Colaborador": nome,
                "Função":      w["funcao"],
                "Status":      status,
                "Veículo":     dist.get("veiculo", "—"),
                "Setor":       dist.get("setor", "—"),
            })

    if not rows:
        st.info("Nenhum dado para o relatório.")
        return

    df = pd.DataFrame(rows)

    resumo = df.groupby("Status").size().reset_index(name="Qtd")
    st.dataframe(resumo, use_container_width=True, hide_index=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exportar CSV", data=csv,
        file_name=f"despacho_eco_{dt.isoformat()}.csv",
        mime="text/csv", use_container_width=True,
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

def render_aba_despacho():
    _inject_css()

    # Data — full width (mobile ok)
    dt_sel = st.date_input("📅 Data do despacho", value=date.today(), key="desp_data")
    st.caption("Gerencie presença e distribuição da equipe ECO para o dia selecionado.")

    checklist    = _carregar_checklist()
    workers_hoje = _obter_workers_hoje(checklist, dt_sel)
    despacho     = _carregar_despacho(dt_sel)

    if not workers_hoje:
        st.warning("Nenhum dado de colaboradores encontrado no checklist.")
        return

    # Sub-tabs com nomes curtos (cabe em mobile)
    tab_v, tab_p, tab_d, tab_f, tab_r = st.tabs([
        "👁️ Visão",
        "✏️ Presença",
        "🗺️ Equipes",
        "🚗 Frota",
        "📄 Relatório",
    ])

    with tab_v:
        _render_visao(workers_hoje, dt_sel)

    with tab_p:
        presenca = _render_presenca(workers_hoje, dt_sel, despacho)
        despacho["presenca"] = presenca
        if st.button("💾 Salvar Presença", key="dp_save", type="primary", use_container_width=True):
            despacho["ultima_atualizacao"] = datetime.now().isoformat()
            _salvar_despacho(dt_sel, despacho)
            st.success("✅ Presença salva!")
            st.rerun()

    with tab_d:
        distribuicao = _render_distribuicao(workers_hoje, dt_sel, despacho)
        despacho["distribuicao"] = distribuicao
        if st.button("💾 Salvar Distribuição", key="dd_save", type="primary", use_container_width=True):
            despacho["ultima_atualizacao"] = datetime.now().isoformat()
            _salvar_despacho(dt_sel, despacho)
            st.success("✅ Distribuição salva!")
            st.rerun()

    with tab_f:
        _render_frota(_obter_veiculos_logos())

    with tab_r:
        _render_relatorio(workers_hoje, despacho, dt_sel)
