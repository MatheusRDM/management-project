"""
_eco_ensaios.py — Ensaios AEVIAS: analytics completo com fonte de dados própria.

FONTE DE DADOS:
  1. Primária  : cache_certificados/ensaios_aevias.json  (sempre disponível, atualizado via sync)
  2. Secundária: ~/Desktop/Ensaios AEVIAS/ensaios_dados.json (máquina local)
  Ambas são geradas por:  Ensaios AEVIAS/baixar_ensaios.py  (Selenium → AEVIAS CONTROLE)

SINCRONIZAR: botão "Sincronizar" executa baixar_ensaios.py e atualiza o cache JSON
             (funciona apenas na máquina local onde o Python + Chrome estão instalados)
"""
import sys, os, json, subprocess, shutil
from datetime import datetime, date, timedelta

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_PAGES_DIR)
if _PAGES_DIR not in sys.path: sys.path.insert(0, _PAGES_DIR)
if _ROOT_DIR  not in sys.path: sys.path.insert(0, _ROOT_DIR)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from _eco_shared import (
    COR_TEXT, COR_MUTED,
    PLOTLY_LAYOUT, PLOTLY_CONFIG,
    _BASE_DIR, _CACHE_DIR, _IS_CLOUD,
)

# =============================================================================
# CONSTANTES
# =============================================================================
_AEVIAS_BASE    = "https://aevias-controle.base44.app"
_JSON_CACHE     = os.path.join(_CACHE_DIR, "ensaios_aevias.json")
_JSON_DESKTOP   = os.path.join(
    os.path.expanduser("~"), "OneDrive", "Área de Trabalho",
    "Ensaios AEVIAS", "ensaios_dados.json"
)
_SCRIPT_SYNC    = os.path.join(
    os.path.expanduser("~"), "OneDrive", "Área de Trabalho",
    "Ensaios AEVIAS", "baixar_ensaios.py"
)

# Paleta de cores por categoria (obra)
_COR_OBRA = {
    "SST":              "#e6194b",
    "Pavimento":        "#3cb44b",
    "TOPOGRAFIA":       "#ffe119",
    "OAE / Terraplenos":"#4363d8",
    "Ampliações":       "#f58231",
    "ESCRITÓRIO":       "#911eb4",
    "Conserva":         "#42d4f4",
}
_COR_TIPO = {
    "Diário de Obra":       "#7BBF6A",
    "Checklist de Usina":   "#4CC9F0",
    "Checklist de Aplicação":"#F7B731",
    "Checklist de MRAF":    "#FF6B6B",
    "Ensaio de CAUQ":       "#A29BFE",
}
_OBRAS_ORDEM = ["SST","Pavimento","TOPOGRAFIA","OAE / Terraplenos",
                "Ampliações","ESCRITÓRIO","Conserva"]

# Paleta gráficos
_C = {
    "bg":    "rgba(0,0,0,0)",
    "grid":  "rgba(255,255,255,0.06)",
    "text":  "#C8D8A8",
    "seq":   ["#7BBF6A","#4CC9F0","#F7B731","#FF6B6B","#A29BFE","#FD79A8","#00CEC9"],
}
_BASE = dict(
    paper_bgcolor=_C["bg"], plot_bgcolor=_C["bg"],
    font=dict(family="Inter, sans-serif", color=_C["text"], size=12),
    margin=dict(l=12, r=12, t=36, b=12),
)
_NI = dict(displayModeBar=False, scrollZoom=False)

# =============================================================================
# CARGA DE DADOS — FONTE PRÓPRIA
# =============================================================================

def _carregar_ensaios(forcar_cache: bool = False) -> list[dict]:
    """
    Carrega dados de ensaios na seguinte ordem de prioridade:
      1. JSON do desktop (máquina local, mais atualizado)
      2. JSON do cache do app (cloud ou máquina sem desktop atualizado)
    Retorna lista de dicts com: data, obra, profissional, tipo, reportUrl
    """
    for caminho in ([_JSON_DESKTOP, _JSON_CACHE] if not forcar_cache
                    else [_JSON_CACHE]):
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                dados = json.load(f)
            return dados
    return []


def _sincronizar_e_copiar():
    """Executa baixar_ensaios.py e copia o JSON resultante para o cache do app."""
    if not os.path.exists(_SCRIPT_SYNC):
        return False, "Script não encontrado em " + _SCRIPT_SYNC
    try:
        result = subprocess.run(
            [sys.executable, _SCRIPT_SYNC],
            capture_output=True, text=True, timeout=300,
            cwd=os.path.dirname(_SCRIPT_SYNC),
        )
        if os.path.exists(_JSON_DESKTOP):
            shutil.copy2(_JSON_DESKTOP, _JSON_CACHE)
            return True, f"Sincronizado! {result.stdout[-500:] if result.stdout else 'OK'}"
        return False, result.stderr[-500:] if result.stderr else "Sem saída"
    except subprocess.TimeoutExpired:
        return False, "Timeout (>5 min) — processo ainda pode estar rodando"
    except Exception as e:
        return False, str(e)


def _df_ensaios(dados: list[dict]) -> pd.DataFrame:
    """Constrói e normaliza o DataFrame de ensaios."""
    if not dados:
        return pd.DataFrame()
    df = pd.DataFrame(dados)
    df["obra"] = df["obra"].str.strip()
    df["tipo"] = df["tipo"].str.strip()
    # Retrocompatibilidade: novo scraper usa 'lab', antigo usava 'profissional'
    if "lab" in df.columns:
        df["profissional"] = df["lab"].fillna("").str.strip()
    elif "profissional" in df.columns:
        df["profissional"] = df["profissional"].fillna("").str.strip()
    else:
        df["profissional"] = "—"
    df["data_dt"]      = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    df["data_iso"]     = df["data_dt"].dt.strftime("%Y-%m-%d")
    df["semana"]       = df["data_dt"].dt.isocalendar().week.astype(str)
    df["dia_semana"]   = df["data_dt"].dt.dayofweek  # 0=Seg
    df["url_completa"] = _AEVIAS_BASE + df["reportUrl"].fillna("")
    return df.sort_values("data_dt", ascending=False).reset_index(drop=True)


# =============================================================================
# SUBCOMPONENTES VISUAIS
# =============================================================================

def _cards_resumo(df: pd.DataFrame, ultima_sync: str):
    total    = len(df)
    obras_n  = df["obra"].nunique()
    profs_n  = df["profissional"].nunique()
    dias_n   = df["data_dt"].nunique()
    d_ini    = df["data_dt"].min().strftime("%d/%m") if not df.empty else "—"
    d_fim    = df["data_dt"].max().strftime("%d/%m") if not df.empty else "—"
    st.markdown(f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px">
      <div style="flex:1;min-width:100px;background:rgba(123,191,106,0.12);border:1px solid #7BBF6A55;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.7rem;font-weight:700;color:#7BBF6A">{total}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Total registros</div></div>
      <div style="flex:1;min-width:100px;background:rgba(76,201,240,0.12);border:1px solid #4CC9F055;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.7rem;font-weight:700;color:#4CC9F0">{dias_n}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Dias com registro<br>{d_ini} → {d_fim}</div></div>
      <div style="flex:1;min-width:100px;background:rgba(247,183,49,0.12);border:1px solid #F7B73155;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.7rem;font-weight:700;color:#F7B731">{profs_n}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Profissionais/Projetos</div></div>
      <div style="flex:1;min-width:100px;background:rgba(255,107,107,0.12);border:1px solid #FF6B6B55;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.7rem;font-weight:700;color:#FF6B6B">{obras_n}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Categorias de obra</div></div>
      <div style="flex:1;min-width:100px;background:rgba(162,155,254,0.12);border:1px solid #A29BFE55;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:.85rem;font-weight:700;color:#A29BFE">{ultima_sync}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Última sincronização</div></div>
    </div>""", unsafe_allow_html=True)


def _grafico_timeline(df: pd.DataFrame):
    st.markdown("### 📅 Timeline — Produção Diária por Categoria")
    df_t = df.dropna(subset=["data_dt"]).copy()
    timeline = df_t.groupby(["data_iso","obra"]).size().reset_index(name="qtd")
    todas_datas = sorted(df_t["data_iso"].unique())
    todas_obras = list(_COR_OBRA.keys())

    fig = go.Figure()
    for obra in todas_obras:
        sub = timeline[timeline["obra"] == obra]
        fig.add_trace(go.Bar(
            x=sub["data_iso"], y=sub["qtd"],
            name=obra,
            marker_color=_COR_OBRA.get(obra, "#888"),
            hovertemplate=f"<b>{obra}</b><br>%{{x}}: %{{y}} reg<extra></extra>",
        ))
    fig.update_layout(
        **_BASE,
        height=280, barmode="stack",
        xaxis=dict(gridcolor=_C["grid"], tickangle=-45, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=_C["grid"], title="Registros"),
        legend=dict(orientation="h", y=-0.3, x=0, font=dict(size=10)),
        title=dict(text="Registros por dia (empilhado por categoria)",
                   font=dict(size=12), x=0),
    )
    st.plotly_chart(fig, use_container_width=True, config=_NI)


def _heatmap_profissional(df: pd.DataFrame):
    st.markdown("### 🗓️ Heatmap — Quem Trabalhou Cada Dia")
    df_t = df.dropna(subset=["data_dt"]).copy()
    profs = sorted(df_t["profissional"].unique())
    datas = sorted(df_t["data_iso"].unique())

    pivot = (df_t.groupby(["profissional","data_iso"]).size()
                  .unstack(fill_value=0)
                  .reindex(index=profs, columns=datas, fill_value=0))

    # Texto com contagem
    text_vals = [[str(v) if v > 0 else "" for v in row] for row in pivot.values]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[d[5:] for d in datas],   # MM-DD
        y=profs,
        text=text_vals,
        texttemplate="%{text}",
        colorscale=[[0,"#0D1B2A"],[0.01,"#1a3a1a"],[0.3,"#3cb44b"],[1,"#7BBF6A"]],
        showscale=False,
        hovertemplate="<b>%{y}</b> · %{x}: %{z} registros<extra></extra>",
        xgap=2, ygap=2,
    ))
    fig.update_layout(
        **_BASE,
        height=max(220, len(profs) * 38 + 60),
        xaxis=dict(tickfont=dict(size=9), side="top"),
        yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
        title=dict(text="Registros por profissional/dia (verde = ativo, escuro = sem registro)",
                   font=dict(size=11), x=0),
    )
    st.plotly_chart(fig, use_container_width=True, config=_NI)


def _pivot_quem_fez_o_que(df: pd.DataFrame):
    st.markdown("### 📋 Pivot: Profissional × Dia × Tipo")
    df_t = df.dropna(subset=["data_dt"]).copy()
    datas = sorted(df_t["data_iso"].unique())
    profs = sorted(df_t["profissional"].unique())

    # Para cada célula: string com iniciais dos tipos
    _TIPO_SIGLA = {
        "Diário de Obra":        "DO",
        "Checklist de Usina":    "CU",
        "Checklist de Aplicação":"CA",
        "Checklist de MRAF":     "MR",
        "Ensaio de CAUQ":        "CAUQ",
    }

    rows = []
    for prof in profs:
        row = {"Profissional": prof}
        for d in datas:
            sub = df_t[(df_t["profissional"] == prof) & (df_t["data_iso"] == d)]
            if sub.empty:
                row[d[5:]] = ""
            else:
                siglas = sorted(set(_TIPO_SIGLA.get(t, t[:2]) for t in sub["tipo"]))
                row[d[5:]] = " · ".join(siglas)
        rows.append(row)

    df_pivot = pd.DataFrame(rows).set_index("Profissional")
    st.dataframe(df_pivot, use_container_width=True, height=max(200, len(profs)*35+50))
    st.caption("DO=Diário de Obra · CU=Checklist Usina · CA=Checklist Aplicação · "
               "MR=MRAF · CAUQ=Ensaio CAUQ")


def _grafico_por_profissional(df: pd.DataFrame):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 👤 Registros por Profissional")
        cnt = (df.groupby(["profissional","tipo"]).size()
                  .reset_index(name="n"))
        profs_sorted = (df.groupby("profissional").size()
                           .sort_values().index.tolist())
        fig = go.Figure()
        for tipo, cor in _COR_TIPO.items():
            sub = cnt[cnt["tipo"] == tipo]
            sub = sub.set_index("profissional").reindex(profs_sorted, fill_value=0).reset_index()
            fig.add_trace(go.Bar(
                y=sub["profissional"], x=sub["n"],
                name=tipo, orientation="h",
                marker_color=cor,
                hovertemplate=f"<b>{tipo}</b><br>%{{y}}: %{{x}}<extra></extra>",
            ))
        fig.update_layout(
            **_BASE, barmode="stack",
            height=max(280, len(profs_sorted)*28+60),
            xaxis=dict(gridcolor=_C["grid"], title="Registros"),
            yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=10)),
            legend=dict(orientation="h", y=-0.25, font=dict(size=9)),
            title=dict(text="Total por profissional (empilhado por tipo)",
                       font=dict(size=12), x=0),
        )
        st.plotly_chart(fig, use_container_width=True, config=_NI)

    with col2:
        st.markdown("### 🏗️ Registros por Categoria de Obra")
        cnt2 = (df.groupby(["obra","tipo"]).size()
                   .reset_index(name="n"))
        obras_sorted = (df.groupby("obra").size()
                           .sort_values().index.tolist())
        fig2 = go.Figure()
        for tipo, cor in _COR_TIPO.items():
            sub = cnt2[cnt2["tipo"] == tipo]
            sub = sub.set_index("obra").reindex(obras_sorted, fill_value=0).reset_index()
            fig2.add_trace(go.Bar(
                y=sub["obra"], x=sub["n"],
                name=tipo, orientation="h",
                marker_color=cor,
                hovertemplate=f"<b>{tipo}</b><br>%{{y}}: %{{x}}<extra></extra>",
            ))
        fig2.update_layout(
            **_BASE, barmode="stack",
            height=max(280, len(obras_sorted)*28+60),
            xaxis=dict(gridcolor=_C["grid"], title="Registros"),
            yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=10)),
            legend=dict(orientation="h", y=-0.25, font=dict(size=9)),
            title=dict(text="Total por categoria (empilhado por tipo)",
                       font=dict(size=12), x=0),
        )
        st.plotly_chart(fig2, use_container_width=True, config=_NI)


def _dias_sem_registro(df: pd.DataFrame):
    st.markdown("### ⚠️ Dias Úteis SEM Registro por Profissional")
    if df.empty or df["data_dt"].isna().all():
        st.info("Sem dados.")
        return

    d_ini  = df["data_dt"].min().date()
    d_fim  = df["data_dt"].max().date()
    # Gera todos os dias úteis (seg-sex) no período
    todos  = pd.date_range(d_ini, d_fim, freq="B")  # B = business days
    datas_uteis = set(d.strftime("%Y-%m-%d") for d in todos)
    profs  = sorted(df["profissional"].unique())

    ausencias = []
    for prof in profs:
        datas_prof = set(df[df["profissional"] == prof]["data_iso"].unique())
        faltando   = sorted(datas_uteis - datas_prof)
        for d in faltando:
            ausencias.append({"Profissional": prof, "Data": d})

    if not ausencias:
        st.success("Nenhum dia útil sem registro no período!")
        return

    df_aus = pd.DataFrame(ausencias).sort_values(["Profissional","Data"])
    df_aus["Data"] = pd.to_datetime(df_aus["Data"]).dt.strftime("%d/%m/%Y")

    # Contagem por profissional
    cnt_aus = df_aus.groupby("Profissional").size().reset_index(name="Dias faltando")
    cnt_aus = cnt_aus.sort_values("Dias faltando", ascending=True)

    col_a, col_b = st.columns([1, 2])
    with col_a:
        fig_aus = go.Figure(go.Bar(
            x=cnt_aus["Dias faltando"], y=cnt_aus["Profissional"],
            orientation="h",
            marker=dict(
                color=cnt_aus["Dias faltando"],
                colorscale=[[0,"#1a3a1a"],[0.5,"#F7B731"],[1,"#FF6B6B"]],
                line_width=0,
            ),
            text=cnt_aus["Dias faltando"].astype(str) + " dias",
            textposition="outside",
            textfont=dict(size=10, color=_C["text"]),
            hovertemplate="<b>%{y}</b>: %{x} dias sem registro<extra></extra>",
        ))
        fig_aus.update_layout(
            **_BASE,
            title=dict(text="Dias úteis faltando", font=dict(size=12), x=0),
            height=max(220, len(cnt_aus)*30+60),
            xaxis=dict(gridcolor=_C["grid"], zeroline=False),
            yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=10)),
        )
        st.plotly_chart(fig_aus, use_container_width=True, config=_NI)

    with col_b:
        st.dataframe(
            df_aus.rename(columns={"Profissional":"Profissional","Data":"Data ausente"}),
            use_container_width=True, hide_index=True,
            height=min(400, len(df_aus)*35+50),
        )


def _tabela_com_links(df: pd.DataFrame):
    st.markdown("### 🔗 Tabela Completa com Links")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        f_obra = st.multiselect("Categoria:", sorted(df["obra"].unique()), key="ens_obra")
    with f2:
        f_tipo = st.multiselect("Tipo:", sorted(df["tipo"].unique()), key="ens_tipo")
    with f3:
        f_prof = st.multiselect("Profissional:", sorted(df["profissional"].unique()), key="ens_prof")
    with f4:
        datas_disp = sorted(df["data_dt"].dropna().dt.date.unique(), reverse=True)
        f_data = st.date_input("De:", value=datas_disp[-1] if datas_disp else date.today(),
                               key="ens_dini")

    dv = df.copy()
    if f_obra: dv = dv[dv["obra"].isin(f_obra)]
    if f_tipo: dv = dv[dv["tipo"].isin(f_tipo)]
    if f_prof: dv = dv[dv["profissional"].isin(f_prof)]
    if f_data: dv = dv[dv["data_dt"].dt.date >= f_data]

    dv_show = dv[["data","profissional","tipo","obra","url_completa"]].copy()
    dv_show.columns = ["Data","Profissional","Tipo","Categoria","Link"]
    dv_show = dv_show.reset_index(drop=True)

    st.dataframe(
        dv_show,
        use_container_width=True,
        hide_index=True,
        height=min(600, len(dv_show)*35+60),
        column_config={
            "Link": st.column_config.LinkColumn("Abrir relatório", display_text="↗ Abrir"),
        },
    )
    st.caption(f"{len(dv_show)} registro(s) de {len(df)} total")


# =============================================================================
# ENTRADA PRINCIPAL
# =============================================================================

def _aba_ensaios():
    # ── Cabeçalho + sincronização ──────────────────────────────────────────────
    c_titulo, c_btn = st.columns([6, 1])
    with c_titulo:
        st.markdown("## 📊 Ensaios AEVIAS — Dashboard de Produção")
        st.caption(
            "Dados extraídos automaticamente de "
            f"[aevias-controle.base44.app]({_AEVIAS_BASE}) "
            "via Selenium. Clique em **Sincronizar** para baixar registros novos."
        )

    # Informação da última atualização do cache
    _mtime = ""
    for _p in [_JSON_DESKTOP, _JSON_CACHE]:
        if os.path.exists(_p):
            _t = os.path.getmtime(_p)
            _mtime = datetime.fromtimestamp(_t).strftime("%d/%m %H:%M")
            break

    with c_btn:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Sincronizar", key="ens_sync", use_container_width=True,
                     disabled=_IS_CLOUD,
                     help="Executa baixar_ensaios.py (apenas máquina local)"):
            with st.spinner("Sincronizando com AEVIAS CONTROLE..."):
                ok, msg = _sincronizar_e_copiar()
            if ok:
                st.success(f"✅ {msg}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    if _IS_CLOUD:
        st.info(
            "ℹ️ App em cloud — sincronização automática desabilitada. "
            "Execute `baixar_ensaios.py` localmente e comite o `cache_certificados/ensaios_aevias.json`."
        )

    # ── Carga dos dados ────────────────────────────────────────────────────────
    dados = _carregar_ensaios()
    if not dados:
        st.warning("Nenhum dado encontrado. Execute a sincronização ou verifique o cache.")
        st.code(f"Cache esperado em:\n  {_JSON_CACHE}\n\nOu desktop:\n  {_JSON_DESKTOP}")
        return

    df = _df_ensaios(dados)

    # ── Filtro global de período ───────────────────────────────────────────────
    with st.expander("🗓️ Filtrar período global", expanded=False):
        dts = df["data_dt"].dropna()
        col_ini, col_fim = st.columns(2)
        with col_ini:
            d_ini_g = st.date_input("Início:", value=dts.min().date(),
                                    key="ens_g_ini")
        with col_fim:
            d_fim_g = st.date_input("Fim:", value=dts.max().date(),
                                    key="ens_g_fim")
        if d_ini_g and d_fim_g:
            df = df[(df["data_dt"].dt.date >= d_ini_g) &
                    (df["data_dt"].dt.date <= d_fim_g)]

    # ── Cards de resumo ────────────────────────────────────────────────────────
    _cards_resumo(df, _mtime or "—")

    # ── Seções analíticas ──────────────────────────────────────────────────────
    st.markdown("---")
    _grafico_timeline(df)

    st.markdown("---")
    _heatmap_profissional(df)

    st.markdown("---")
    _grafico_por_profissional(df)

    st.markdown("---")
    _pivot_quem_fez_o_que(df)

    st.markdown("---")
    _dias_sem_registro(df)

    st.markdown("---")
    _tabela_com_links(df)
