"""
=========================================================================
EPR LITORAL PIONEIRO — Dashboard Visual (FORM 022A)
=========================================================================
Layout dinâmico com seções por material, tabelas HTML estilizadas,
badges de status coloridos e mini-cards de progresso.
=========================================================================
"""

import io
import os
import sys
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from styles import CORES, renderizar_footer
from EPR.utils_epr import (
    carregar_dados, sincronizar_epr, calcular_kpis,
    formatar_numero, get_label_grupo, get_icone_grupo,
)

SESSION_PREFIX = "epr_dash_"

# Ordem de prioridade dos status (EM ANDAMENTO aparece primeiro)
_STATUS_ORDEM = {"EM ANDAMENTO": 0, "AGUARDANDO": 1, "CONCLUIDO": 2}

# =============================================================================
# PALETAS E CONFIGURAÇÕES VISUAIS
# =============================================================================

_COR_STATUS = {
    "CONCLUIDO":    {"bg": "#14532d", "txt": "#86efac", "border": "#22c55e"},
    "EM ANDAMENTO": {"bg": "#1e3a5f", "txt": "#93c5fd", "border": "#3b82f6"},
    "AGUARDANDO":   {"bg": "#451a03", "txt": "#fcd34d", "border": "#f59e0b"},
}

_COR_GRUPO = {
    "CP_CONCRETO": {"accent": "#6d8fa0", "light": "rgba(109,143,160,0.12)"},
    "CAUQ_PISTA":  {"accent": "#8a6d3b", "light": "rgba(138,109,59,0.12)"},
    "CAUQ_MASSA":  {"accent": "#7b5ea7", "light": "rgba(123,94,167,0.12)"},
    "OUTROS":      {"accent": "#4a7c59", "light": "rgba(74,124,89,0.12)"},
}

# Colunas por grupo (ordem e conteúdo)
_COLUNAS_GRUPO = {
    "CP_CONCRETO": [
        ("PT",                  "PT",             "50px"),
        ("DATA_RECEBIMENTO",    "Dt. Receb.",      "90px"),
        ("PEDREIRA",            "Procedência",    "160px"),
        ("QUANTIDADE",          "Qtd",             "40px"),
        ("DATA_MOLDAGEM",       "Data Coleta",     "90px"),
        ("LOCALIZACAO",         "Localização",    "180px"),
        ("DATA_ROMPIMENTO_7D",  "Dt. Rupt. 7d",    "90px"),
        ("RESULTADO_7D_MPA",    "Fc7 (MPa)",        "70px"),
        ("DATA_ROMPIMENTO_28D", "Dt. Rupt. 28d",   "90px"),
        ("RESULTADO_28D_MPA",   "Fc28 (MPa)",       "70px"),
        ("STATUS",              "Status",           "120px"),
    ],
    "CAUQ_PISTA": [
        ("PT",               "PT",            "50px"),
        ("DATA_RECEBIMENTO", "Dt. Receb.",     "90px"),
        ("PEDREIRA",         "Procedência",   "140px"),
        ("QUANTIDADE",       "Qtd",            "40px"),
        ("NUMERO_CP",        "Nº CP",          "60px"),
        ("DATA_EXECUCAO",    "Data Execução",  "90px"),
        ("LOCALIZACAO",      "Localização",   "180px"),
        ("TRECHO",           "Trecho/Faixa",  "110px"),
        ("STATUS",           "Status",         "120px"),
    ],
    "CAUQ_MASSA": [
        ("PT",               "PT",            "50px"),
        ("DATA_RECEBIMENTO", "Dt. Receb.",     "90px"),
        ("QUANTIDADE",       "Qtd",            "40px"),
        ("PROJETO_NUM",      "Projeto/PC",     "120px"),
        ("DATA_MOLDAGEM",    "Data Coleta",    "90px"),
        ("LOCALIZACAO",      "Localização",   "220px"),
        ("TIPO_SERVICO",     "Tipo Serviço",  "150px"),
        ("MATERIAL_OBS",     "Material OBS",  "140px"),
        ("STATUS",           "Status",         "120px"),
    ],
    "OUTROS": [
        ("PT",               "PT",            "50px"),
        ("DATA_RECEBIMENTO", "Dt. Receb.",     "90px"),
        ("MATERIAL",         "Material",      "180px"),
        ("QUANTIDADE",       "Qtd",            "40px"),
        ("LOCALIZACAO",      "Localização",   "220px"),
        ("STATUS",           "Status",         "120px"),
    ],
}


# =============================================================================
# GERAÇÃO DE HTML
# =============================================================================

_CSS_TABELA = """
<style>
.epr-table-wrap {
    overflow-x: auto;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 1rem;
}
.epr-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Poppins', sans-serif;
    font-size: 0.82rem;
    color: #e2e8f0;
}
.epr-table thead tr {
    background: rgba(15,20,35,0.9);
    position: sticky;
    top: 0;
    z-index: 10;
}
.epr-table thead th {
    padding: 9px 12px;
    text-align: left;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: #94a3b8;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    white-space: nowrap;
}
.epr-table tbody tr {
    border-bottom: 1px solid rgba(255,255,255,0.05);
    transition: background 0.15s ease;
}
.epr-table tbody tr:hover {
    background: rgba(255,255,255,0.05) !important;
}
.epr-table tbody tr:nth-child(odd) {
    background: rgba(255,255,255,0.02);
}
.epr-table td {
    padding: 8px 12px;
    vertical-align: middle;
    max-width: 260px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.epr-table td.wrap {
    white-space: normal;
    word-break: break-word;
}
.badge-status {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    border: 1px solid;
    white-space: nowrap;
}
.pt-chip {
    display: inline-block;
    background: rgba(191,207,153,0.15);
    color: #BFCF99;
    border: 1px solid rgba(191,207,153,0.3);
    border-radius: 6px;
    padding: 1px 8px;
    font-weight: 700;
    font-size: 0.80rem;
}
.loc-text {
    color: #7dd3fc;
    font-size: 0.78rem;
}
.date-text {
    color: #fde68a;
    font-size: 0.79rem;
    font-weight: 600;
}
.cp-chip {
    display: inline-block;
    background: rgba(139,92,246,0.2);
    color: #c4b5fd;
    border: 1px solid rgba(139,92,246,0.35);
    border-radius: 6px;
    padding: 1px 8px;
    font-size: 0.78rem;
    font-weight: 600;
}
.proj-chip {
    display: inline-block;
    background: rgba(251,146,60,0.15);
    color: #fdba74;
    border: 1px solid rgba(251,146,60,0.3);
    border-radius: 6px;
    padding: 1px 8px;
    font-size: 0.78rem;
    font-weight: 600;
}
.qtd-cell {
    text-align: center;
    font-weight: 700;
    color: #cbd5e1;
}
.mat-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 8px 8px 0 0;
    margin-bottom: 0;
}
.mat-count-badge {
    display: inline-block;
    background: rgba(255,255,255,0.12);
    color: #e2e8f0;
    border-radius: 20px;
    padding: 1px 10px;
    font-size: 0.72rem;
    font-weight: 600;
}
.progresso-wrap {
    background: rgba(0,0,0,0.25);
    border-radius: 0;
    height: 5px;
    margin-bottom: 0;
}
.progresso-bar {
    height: 5px;
    border-radius: 0;
    transition: width 0.4s ease;
}
.secao-material {
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 18px;
    overflow: hidden;
}
</style>
"""

def _badge(status: str) -> str:
    c = _COR_STATUS.get(status, {"bg": "#1e293b", "txt": "#94a3b8", "border": "#475569"})
    return (f'<span class="badge-status" '
            f'style="background:{c["bg"]};color:{c["txt"]};border-color:{c["border"]};">'
            f'{status}</span>')


def _cel(valor, tipo="texto") -> str:
    v = str(valor).strip() if valor and str(valor).strip().lower() not in ("nan", "none", "-", "") else "-"
    if tipo == "pt":
        return f'<td><span class="pt-chip">{v}</span></td>'
    if tipo == "status":
        return f'<td>{_badge(v)}</td>'
    if tipo == "data":
        return f'<td><span class="date-text">{v}</span></td>'
    if tipo == "loc":
        return f'<td class="wrap"><span class="loc-text">{v}</span></td>'
    if tipo == "cp":
        return f'<td><span class="cp-chip">{v}</span></td>'
    if tipo == "proj":
        return f'<td><span class="proj-chip">{v}</span></td>'
    if tipo == "qtd":
        return f'<td class="qtd-cell">{v}</td>'
    if tipo == "fc":
        if v == "-":
            return '<td style="text-align:center;color:#475569;font-size:0.80rem;">—</td>'
        try:
            vf = float(v)
            return (f'<td style="text-align:center;font-weight:700;'
                    f'color:#86efac;font-size:0.85rem;">{vf:.1f}</td>')
        except Exception:
            return f'<td style="text-align:center;">{v}</td>'
    return f'<td title="{v}">{v}</td>'


def _tipo_cel(coluna: str) -> str:
    mapa = {
        "PT": "pt", "STATUS": "status",
        "DATA_RECEBIMENTO": "data", "DATA_MOLDAGEM": "data", "DATA_EXECUCAO": "data",
        "DATA_ROMPIMENTO_7D": "data", "DATA_ROMPIMENTO_28D": "data",
        "LOCALIZACAO": "loc", "TRECHO": "loc",
        "NUMERO_CP": "cp",
        "PROJETO_NUM": "proj",
        "QUANTIDADE": "qtd",
        "RESULTADO_7D_MPA": "fc", "RESULTADO_28D_MPA": "fc",
    }
    return mapa.get(coluna, "texto")


def _gerar_tabela_html(df: pd.DataFrame, grupo: str, busca: str = "") -> str:
    """Gera HTML da tabela estilizada para um grupo/material."""
    colunas = _COLUNAS_GRUPO.get(grupo, _COLUNAS_GRUPO["OUTROS"])
    colunas_disp = [(col, label, w) for col, label, w in colunas if col in df.columns]

    if df.empty or not colunas_disp:
        return "<p style='color:#94a3b8;padding:12px;'>Nenhum registro.</p>"

    # Header
    thead = "".join(
        f'<th style="min-width:{w};max-width:{w};">{label}</th>'
        for col, label, w in colunas_disp
    )

    # Rows
    linhas = []
    for _, row in df.iterrows():
        cels = ""
        for col, _, _ in colunas_disp:
            val = row.get(col, "-")
            cel_html = _cel(val, _tipo_cel(col))
            # Destaque da busca
            if busca and busca.lower() in str(val).lower():
                cel_html = cel_html.replace(
                    str(val),
                    f'<mark style="background:#854d0e;color:#fef08a;border-radius:3px;padding:0 2px;">'
                    f'{str(val)}</mark>',
                    1
                )
            cels += cel_html
        linhas.append(f"<tr>{cels}</tr>")

    tbody = "\n".join(linhas)
    return f"""
<div class="epr-table-wrap">
<table class="epr-table">
  <thead><tr>{thead}</tr></thead>
  <tbody>{tbody}</tbody>
</table>
</div>"""


def _mini_card_material(nome: str, total: int, concluidos: int, cor_accent: str) -> str:
    pct = (concluidos / total * 100) if total > 0 else 0
    return f"""
<div style="background:rgba(15,20,35,0.6);border:1px solid {cor_accent}40;border-radius:10px;
     padding:12px 16px;text-align:center;">
  <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:4px;white-space:nowrap;
       overflow:hidden;text-overflow:ellipsis;">{nome}</div>
  <div style="font-size:1.4rem;font-weight:700;color:#e2e8f0;">{total}</div>
  <div style="font-size:0.70rem;color:{cor_accent};margin-top:2px;">{pct:.0f}% concluído</div>
  <div style="background:rgba(0,0,0,0.3);border-radius:4px;height:4px;margin-top:6px;">
    <div style="width:{min(pct,100):.1f}%;background:{cor_accent};height:4px;border-radius:4px;"></div>
  </div>
</div>"""


# =============================================================================
# RENDERIZAÇÃO DAS SEÇÕES
# =============================================================================

def _renderizar_secoes_por_material(df_grupo: pd.DataFrame, grupo: str, busca: str = ""):
    """
    Renderiza seções separadas por tipo de material exato (col MATERIAL).
    Cada seção tem: header colorido + barra de progresso + tabela HTML.
    """
    if df_grupo.empty or "MATERIAL" not in df_grupo.columns:
        st.info("Nenhum registro para exibir.")
        return

    cor_g = _COR_GRUPO.get(grupo, _COR_GRUPO["OUTROS"])
    materiais = df_grupo["MATERIAL"].value_counts().index.tolist()

    # Mini-cards por material
    if len(materiais) > 1:
        cols_cards = st.columns(min(len(materiais), 4))
        for i, mat in enumerate(materiais[:4]):
            df_m = df_grupo[df_grupo["MATERIAL"] == mat]
            total_m = int(df_m["QUANTIDADE"].sum())
            conc_m  = int(df_m[df_m["STATUS"] == "CONCLUIDO"]["QUANTIDADE"].sum())
            with cols_cards[i % len(cols_cards)]:
                st.markdown(
                    _mini_card_material(mat, total_m, conc_m, cor_g["accent"]),
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # Uma seção por material
    for mat in materiais:
        df_m = df_grupo[df_grupo["MATERIAL"] == mat].copy()

        # Ordenar: EM ANDAMENTO → AGUARDANDO → CONCLUIDO
        if "STATUS" in df_m.columns:
            df_m["_ord"] = df_m["STATUS"].map(_STATUS_ORDEM).fillna(99)
            df_m = df_m.sort_values("_ord").drop(columns=["_ord"])

        # Aplicar busca
        if busca.strip():
            mask = df_m.apply(
                lambda r: busca.lower() in " ".join(str(v) for v in r.values).lower(), axis=1
            )
            df_m_filtrado = df_m[mask]
        else:
            df_m_filtrado = df_m

        total_m = len(df_m)
        n_filt  = len(df_m_filtrado)
        conc_m  = int(df_m[df_m["STATUS"] == "CONCLUIDO"]["QUANTIDADE"].sum())
        total_qtd = int(df_m["QUANTIDADE"].sum())
        pct_m   = (conc_m / total_qtd * 100) if total_qtd > 0 else 0

        # Header da seção
        st.markdown(
            f"""<div class="secao-material">
            <div class="mat-header" style="background:{cor_g['light']};border-bottom:1px solid {cor_g['accent']}30;">
                <span style="font-weight:700;color:#e2e8f0;font-size:0.9rem;">{mat}</span>
                <span class="mat-count-badge">{n_filt} de {total_m} registro{'s' if total_m!=1 else ''}</span>
                <span style="margin-left:auto;font-size:0.75rem;color:{cor_g['accent']};">{pct_m:.0f}% concluído</span>
            </div>
            <div class="progresso-wrap">
                <div class="progresso-bar" style="width:{min(pct_m,100):.1f}%;background:{cor_g['accent']};"></div>
            </div>""",
            unsafe_allow_html=True,
        )

        if df_m_filtrado.empty:
            st.markdown(
                "<p style='color:#94a3b8;padding:10px 14px;font-size:0.82rem;'>"
                "Nenhum registro corresponde à busca.</p></div>",
                unsafe_allow_html=True,
            )
        else:
            html_tabela = _gerar_tabela_html(df_m_filtrado, grupo, busca)
            st.markdown(html_tabela + "</div>", unsafe_allow_html=True)

        # OBS completa por material (expander)
        if "OBS_RAW" in df_m_filtrado.columns:
            df_com_obs = df_m_filtrado[
                df_m_filtrado["OBS_RAW"].notna() &
                (df_m_filtrado["OBS_RAW"].astype(str).str.strip() != "") &
                (df_m_filtrado["OBS_RAW"].astype(str).str.lower() != "nan") &
                (df_m_filtrado["OBS_RAW"].astype(str) != "-")
            ]
            if not df_com_obs.empty:
                with st.expander(f"📄 OBS completa — {mat} ({len(df_com_obs)} registros)"):
                    for _, row in df_com_obs.iterrows():
                        obs = str(row.get("OBS_RAW", ""))
                        pt  = str(row.get("PT", "-"))
                        dt  = str(row.get("DATA_RECEBIMENTO", "-"))
                        st.markdown(
                            f"""<div style="background:rgba(15,22,40,0.7);border-left:3px solid {cor_g['accent']};
                            padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;">
                            <div style="display:flex;gap:10px;margin-bottom:5px;align-items:center;">
                                <span class="pt-chip">PT {pt}</span>
                                <span style="color:#94a3b8;font-size:0.78rem;">{dt}</span>
                            </div>
                            <pre style="color:#cbd5e1;font-size:0.79rem;margin:0;
                            white-space:pre-wrap;font-family:'Poppins',monospace;">{obs}</pre>
                            </div>""",
                            unsafe_allow_html=True,
                        )

        # Export por material
        try:
            buf = io.BytesIO()
            cols_exp = [c for c, *_ in _COLUNAS_GRUPO.get(grupo, _COLUNAS_GRUPO["OUTROS"])
                        if c in df_m_filtrado.columns]
            if "OBS_RAW" in df_m_filtrado.columns:
                cols_exp = cols_exp + ["OBS_RAW"]
            df_exp = df_m_filtrado[cols_exp].copy()
            with pd.ExcelWriter(buf, engine="xlsxwriter") as wr:
                df_exp.to_excel(wr, index=False, sheet_name=mat[:31])
            buf.seek(0)
            nome_arquivo = f"EPR_{mat[:30].replace(' ', '_').replace('/', '-')}.xlsx"
            st.download_button(
                f"⬇️ Exportar Excel — {mat[:40]}",
                data=buf.getvalue(),
                file_name=nome_arquivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{SESSION_PREFIX}exp_{grupo}_{mat[:20]}",
            )
        except Exception:
            pass


def _renderizar_materiais_em_tabs(df_grupo: pd.DataFrame, grupo: str):
    """
    Sub-tabs por material: ao clicar, a tabela aparece imediatamente.
    Substitui as seções empilhadas verticalmente.
    """
    if df_grupo.empty or "MATERIAL" not in df_grupo.columns:
        st.info("Nenhum registro para exibir.")
        return

    cor_g = _COR_GRUPO.get(grupo, _COR_GRUPO["OUTROS"])
    materiais = df_grupo["MATERIAL"].value_counts().index.tolist()

    # Labels com contagem de status: "CP Concreto (Cil.)  EM AND.:3 | AGU.:2 | OK:5"
    def _label(mat):
        df_m = df_grupo[df_grupo["MATERIAL"] == mat]
        and_ = len(df_m[df_m["STATUS"] == "EM ANDAMENTO"])
        agu_ = len(df_m[df_m["STATUS"] == "AGUARDANDO"])
        ok_  = len(df_m[df_m["STATUS"] == "CONCLUIDO"])
        partes = []
        if and_: partes.append(f"🔄 {and_}")
        if agu_: partes.append(f"⏳ {agu_}")
        if ok_:  partes.append(f"✅ {ok_}")
        sufixo = "  " + " · ".join(partes) if partes else ""
        return f"{mat[:30]}{sufixo}"

    nomes_subtabs = [_label(m) for m in materiais]
    subtabs = st.tabs(nomes_subtabs)

    for i, mat in enumerate(materiais):
        with subtabs[i]:
            df_m = df_grupo[df_grupo["MATERIAL"] == mat].copy()

            # Ordenar: EM ANDAMENTO → AGUARDANDO → CONCLUIDO
            if "STATUS" in df_m.columns:
                df_m["_ord"] = df_m["STATUS"].map(_STATUS_ORDEM).fillna(99)
                df_m = df_m.sort_values("_ord").drop(columns=["_ord"])

            # KPIs do material
            total_qtd = int(df_m["QUANTIDADE"].sum())
            conc_qtd  = int(df_m[df_m["STATUS"] == "CONCLUIDO"]["QUANTIDADE"].sum())
            and_qtd   = int(df_m[df_m["STATUS"] == "EM ANDAMENTO"]["QUANTIDADE"].sum())
            agu_qtd   = int(df_m[df_m["STATUS"] == "AGUARDANDO"]["QUANTIDADE"].sum())
            pct_m     = (conc_qtd / total_qtd * 100) if total_qtd > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📦 Amostras",     formatar_numero(total_qtd))
            c2.metric("✅ Concluídos",   formatar_numero(conc_qtd))
            c3.metric("🔄 Em Andamento", formatar_numero(and_qtd))
            c4.metric("⏳ Aguardando",   formatar_numero(agu_qtd))

            # Barra de progresso inline
            st.markdown(
                f"""<div style="background:rgba(0,0,0,0.25);border-radius:4px;height:5px;margin:4px 0 4px 0;">
                <div style="width:{min(pct_m,100):.1f}%;background:{cor_g['accent']};height:5px;border-radius:4px;"></div>
                </div>
                <div style="font-size:0.75rem;color:{cor_g['accent']};text-align:right;margin-bottom:10px;">
                {pct_m:.0f}% concluído</div>""",
                unsafe_allow_html=True,
            )

            # Busca + filtro de status
            col_b, col_s = st.columns([3, 1])
            with col_b:
                busca = st.text_input(
                    "🔍 Buscar",
                    key=f"{SESSION_PREFIX}busca_{grupo}_{i}",
                    placeholder="PT, localização, data, KM...",
                )
            with col_s:
                opts_s = ["Todos"] + sorted(df_m["STATUS"].dropna().unique().tolist())
                s_filt = st.selectbox("Status", opts_s,
                                      key=f"{SESSION_PREFIX}sf_{grupo}_{i}")

            # Filtrar
            df_view = df_m.copy()
            if s_filt != "Todos":
                df_view = df_view[df_view["STATUS"] == s_filt]
            if busca.strip():
                mask = df_view.apply(
                    lambda r: busca.lower() in " ".join(str(v) for v in r.values).lower(),
                    axis=1,
                )
                df_view = df_view[mask]

            # Tabela HTML
            if df_view.empty:
                st.info("Nenhum registro corresponde ao filtro.")
            else:
                st.markdown(
                    _gerar_tabela_html(df_view, grupo, busca),
                    unsafe_allow_html=True,
                )

            # OBS completa
            if "OBS_RAW" in df_view.columns:
                df_obs = df_view[
                    df_view["OBS_RAW"].notna() &
                    (df_view["OBS_RAW"].astype(str).str.strip() != "") &
                    (df_view["OBS_RAW"].astype(str).str.lower() != "nan") &
                    (df_view["OBS_RAW"].astype(str) != "-")
                ]
                if not df_obs.empty:
                    with st.expander(f"📄 OBS completa ({len(df_obs)} registros)"):
                        for _, row in df_obs.iterrows():
                            obs = str(row.get("OBS_RAW", ""))
                            pt  = str(row.get("PT", "-"))
                            dt  = str(row.get("DATA_RECEBIMENTO", "-"))
                            st.markdown(
                                f"""<div style="background:rgba(15,22,40,0.7);
                                border-left:3px solid {cor_g['accent']};
                                padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;">
                                <div style="display:flex;gap:10px;margin-bottom:5px;align-items:center;">
                                    <span class="pt-chip">PT {pt}</span>
                                    <span style="color:#94a3b8;font-size:0.78rem;">{dt}</span>
                                </div>
                                <pre style="color:#cbd5e1;font-size:0.79rem;margin:0;
                                white-space:pre-wrap;font-family:'Poppins',monospace;">{obs}</pre>
                                </div>""",
                                unsafe_allow_html=True,
                            )

            # Export por material
            try:
                buf = io.BytesIO()
                cols_exp = [c for c, *_ in _COLUNAS_GRUPO.get(grupo, _COLUNAS_GRUPO["OUTROS"])
                            if c in df_view.columns]
                if "OBS_RAW" in df_view.columns:
                    cols_exp += ["OBS_RAW"]
                df_exp = df_view[cols_exp].copy()
                with pd.ExcelWriter(buf, engine="xlsxwriter") as wr:
                    df_exp.to_excel(wr, index=False, sheet_name=mat[:31])
                buf.seek(0)
                nome_arq = f"EPR_{mat[:30].replace(' ', '_').replace('/', '-')}.xlsx"
                st.download_button(
                    f"⬇️ Exportar Excel — {mat[:40]}",
                    data=buf.getvalue(),
                    file_name=nome_arq,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"{SESSION_PREFIX}exp2_{grupo}_{i}",
                )
            except Exception:
                pass


def _renderizar_tab_grupo(df_grupo: pd.DataFrame, grupo: str):
    """Renderiza uma tab completa para um grupo de material."""
    icone = get_icone_grupo(grupo)
    label = get_label_grupo(grupo)
    cor_g = _COR_GRUPO.get(grupo, _COR_GRUPO["OUTROS"])

    if df_grupo.empty:
        st.info(f"Nenhum registro de **{label}** no período selecionado.")
        return

    # KPIs
    kpis = calcular_kpis(df_grupo)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Amostras",     formatar_numero(kpis["total_amostras"]))
    c2.metric("✅ Concluídos",   formatar_numero(kpis["concluidos"]))
    c3.metric("🔄 Em Andamento", formatar_numero(kpis["em_andamento"]))
    c4.metric("⏳ Aguardando",   formatar_numero(kpis["aguardando"]))

    pct = kpis["pct_concluido"]
    st.progress(min(int(pct), 100),
                text=f"**{icone} {label}: {pct:.1f}% concluído**")

    # Gráfico mensal — colapsado para a tabela aparecer imediatamente
    if "MES_ANO" in df_grupo.columns:
        with st.expander("📊 Ver gráfico de andamento por mês", expanded=False):
            meses = sorted(df_grupo["MES_ANO"].dropna().unique())
            fig = go.Figure()
            for status, c_cfg in [("AGUARDANDO", _COR_STATUS["AGUARDANDO"]),
                                   ("EM ANDAMENTO", _COR_STATUS["EM ANDAMENTO"]),
                                   ("CONCLUIDO", _COR_STATUS["CONCLUIDO"])]:
                df_s = df_grupo[df_grupo["STATUS"] == status]
                if df_s.empty:
                    continue
                qtd = df_s.groupby("MES_ANO")["QUANTIDADE"].sum().reindex(meses, fill_value=0)
                fig.add_trace(go.Bar(
                    name=status, x=meses, y=qtd.values,
                    marker_color=c_cfg["border"],
                    hovertemplate=f"<b>{status}</b><br>Mês: %{{x}}<br>Qtd: %{{y}}<extra></extra>",
                    text=qtd.values, textposition="inside",
                    textfont=dict(color="white", size=11),
                ))
            fig.update_layout(
                title=dict(text=f"Andamento por Mês — {label}", font=dict(size=13, color="#FFFFFF")),
                barmode="stack", dragmode=False, height=270,
                plot_bgcolor="rgba(15,20,35,0.8)", paper_bgcolor="rgba(15,20,35,0.8)",
                font=dict(color="#FFFFFF", size=11),
                legend=dict(orientation="h", xanchor="center", x=0.5, yanchor="top", y=-0.18,
                            bgcolor="rgba(15,20,35,0.6)", font=dict(size=10)),
                margin=dict(l=20, r=20, t=45, b=80),
                xaxis=dict(fixedrange=True, tickangle=-30, tickfont=dict(size=9)),
                yaxis=dict(fixedrange=True, tickfont=dict(size=9)),
            )
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False, "scrollZoom": False})

    st.markdown("---")
    st.markdown(f"#### {icone} Registros por Material")

    # Sub-tabs por material — tabela aparece ao clicar, sem empilhamento vertical
    _renderizar_materiais_em_tabs(df_grupo, grupo)


# =============================================================================
# MAIN
# =============================================================================

def main():
    # CSS global da tabela
    st.markdown(_CSS_TABELA, unsafe_allow_html=True)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""<style>
        div[data-testid="stButton"][key="back_to_menu_epr"] > button {
            background: transparent !important;
            border: 1px solid rgba(191,207,153,0.3) !important;
            color: rgba(191,207,153,0.7) !important;
            font-size: 0.78rem !important;
            padding: 0.2rem 0.6rem !important;
            border-radius: 6px !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stButton"][key="back_to_menu_epr"] > button:hover {
            background: rgba(191,207,153,0.1) !important;
            color: #BFCF99 !important;
        }
        </style>""", unsafe_allow_html=True)

        if st.button("← Menu Principal", key="back_to_menu_epr"):
            st.switch_page("app.py")

        try:
            st.image("Imagens/AE - Logo Hor Principal_2.png", use_container_width=True)
        except Exception:
            st.markdown(f"""<div style="background:{CORES['secundario']};padding:1rem;
            border-radius:8px;text-align:center;">
            <h3 style="color:white;margin:0;">AFIRMA E-VIAS</h3></div>""",
            unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(
            f"<h3 style='color:{CORES['destaque']};text-align:center;font-size:1rem;'>"
            f"🛣️ EPR Litoral Pioneiro</h3>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        if st.button("🔄 Sincronizar FORM 022A", use_container_width=True, key=f"{SESSION_PREFIX}sync"):
            with st.spinner("Lendo FORM 022A e processando..."):
                ok = sincronizar_epr()
            if ok:
                st.success("✅ Dados atualizados!")
                st.rerun()
            else:
                st.warning("⚠️ FORM 022A não encontrado ou sem dados EPR.")

        st.markdown("---")
        df_full = carregar_dados()

        with st.expander("🔍 Filtros Globais", expanded=True):
            df = df_full.copy() if not df_full.empty else pd.DataFrame()

            if not df.empty and "ANO" in df.columns:
                anos = sorted(df["ANO"].dropna().unique(), reverse=True)
                ano_sel = st.selectbox("Ano:", ["Todos"] + list(anos), key=f"{SESSION_PREFIX}ano")
                if ano_sel != "Todos":
                    df = df[df["ANO"] == ano_sel]

            if not df.empty and "MES_ANO" in df.columns:
                meses = sorted(df["MES_ANO"].dropna().unique())
                mes_sel = st.selectbox("Mês (MM/AAAA):", ["Todos"] + meses, key=f"{SESSION_PREFIX}mes")
                if mes_sel != "Todos":
                    df = df[df["MES_ANO"] == mes_sel]

            if not df.empty and "MATERIAL_GRUPO" in df.columns:
                grupos_d = sorted(df["MATERIAL_GRUPO"].dropna().unique())
                labels_g = ["Todos"] + [f"{get_icone_grupo(g)} {get_label_grupo(g)}" for g in grupos_d]
                vals_g   = ["Todos"] + grupos_d
                g_label  = st.selectbox("Tipo de Material:", labels_g, key=f"{SESSION_PREFIX}grupo")
                g_sel    = vals_g[labels_g.index(g_label)]
                if g_sel != "Todos":
                    df = df[df["MATERIAL_GRUPO"] == g_sel]

        st.markdown("---")
        st.caption("© 2026 Afirma E-vias")

    # ── Header ────────────────────────────────────────────────────────────────
    col_logo, col_titulo = st.columns([0.8, 4])
    with col_logo:
        try:
            st.image(
                r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1"
                r"\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias"
                r"\Manual Completo\Identidade Visual\Logotipo e Variações\Símbolo e Selos"
                r"\PNG\Selo C Ass\Selo C Ass_4.png",
                width=110,
            )
        except Exception:
            pass

    with col_titulo:
        st.markdown(f"""
        <div style="padding-left:1rem;">
            <h1 style="margin:0;font-size:1.9rem;">🛣️ EPR Litoral Pioneiro</h1>
            <p style="color:{CORES['destaque']};font-size:1rem;margin-top:0.3rem;">
                Acompanhamento de Ensaios — FORM 022A
            </p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    if df_full.empty:
        st.info("ℹ️ Clique em **🔄 Sincronizar FORM 022A** na sidebar para carregar os dados.")
        renderizar_footer()
        return

    df_filtrado = df if not df.empty else df_full

    # ── KPIs Gerais ───────────────────────────────────────────────────────────
    kpis = calcular_kpis(df_filtrado)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📦 Total Amostras",  formatar_numero(kpis["total_amostras"]))
    k2.metric("✅ Concluídos",      formatar_numero(kpis["concluidos"]),
              delta=f"{kpis['pct_concluido']:.1f}%")
    k3.metric("🔄 Em Andamento",    formatar_numero(kpis["em_andamento"]))
    k4.metric("⏳ Aguardando",      formatar_numero(kpis["aguardando"]))

    st.progress(min(int(kpis["pct_concluido"]), 100),
                text=f"**Progresso Geral: {kpis['pct_concluido']:.1f}% concluído**")

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    grupos_presentes = [
        g for g in ["CP_CONCRETO", "CAUQ_PISTA", "CAUQ_MASSA", "OUTROS"]
        if "MATERIAL_GRUPO" in df_filtrado.columns
        and g in df_filtrado["MATERIAL_GRUPO"].values
    ]
    if not grupos_presentes:
        grupos_presentes = ["CP_CONCRETO", "CAUQ_PISTA", "CAUQ_MASSA"]

    nomes_tabs = [f"{get_icone_grupo(g)} {get_label_grupo(g)}" for g in grupos_presentes]

    tabs = st.tabs(nomes_tabs)
    for i, grupo in enumerate(grupos_presentes):
        with tabs[i]:
            df_g = (df_filtrado[df_filtrado["MATERIAL_GRUPO"] == grupo].copy()
                    if "MATERIAL_GRUPO" in df_filtrado.columns else pd.DataFrame())
            _renderizar_tab_grupo(df_g, grupo)

    renderizar_footer()
