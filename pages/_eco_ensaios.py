"""
_eco_ensaios.py — ensaios tab for ECO Rodovias.
"""
import sys
import os

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_PAGES_DIR)
if _PAGES_DIR not in sys.path: sys.path.insert(0, _PAGES_DIR)
if _ROOT_DIR  not in sys.path: sys.path.insert(0, _ROOT_DIR)

import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from _eco_shared import (
    COR_PRIMARY, COR_ACCENT, COR_BG, COR_CARD, COR_BORDER,
    COR_TEXT, COR_MUTED, COR_OK, COR_COBRAR, COR_NE, COR_ELAB,
    PLOTLY_LAYOUT, PLOTLY_CONFIG,
    _BASE_DIR, _CACHE_DIR, _Y_BASE, _IS_CLOUD,
)


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
