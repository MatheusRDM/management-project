"""
_eco_rastreamento.py — all render functions + _aba_rastreamento fragment for ECO Rodovias.
"""
import sys
import os

_PAGES_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_PAGES_DIR)
if _PAGES_DIR not in sys.path: sys.path.insert(0, _PAGES_DIR)
if _ROOT_DIR  not in sys.path: sys.path.insert(0, _ROOT_DIR)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from datetime import datetime, date

from _eco_shared import (
    COR_PRIMARY, COR_ACCENT, COR_BG, COR_CARD, COR_BORDER,
    COR_TEXT, COR_MUTED, COR_OK, COR_COBRAR, COR_NE, COR_ELAB,
    PLOTLY_LAYOUT, PLOTLY_CONFIG,
    _BASE_DIR, _CACHE_DIR, _Y_BASE, _IS_CLOUD,
)
from _eco_rast_api import (
    _LOGOS_BASE, _CORES_VEICULOS,
    _HIST_ODO_FIELDS, _HIST_LAT_FIELDS, _HIST_LON_FIELDS,
    _HIST_VEL_FIELDS, _HIST_IGN_FIELDS, _HIST_DT_FIELDS,
    _HIST_CID_FIELDS, _HIST_UF_FIELDS,
    _logos_login, _logos_get_eco, _logos_get_rota,
    _pick, _km_from_hist, _normalizar_contrato, _parse_eco,
)


# =============================================================================
# RENDER: MAPA DE POSIÇÃO
# =============================================================================

def _render_mapa_posicao(itens, map_key="logos_mapa_pos", height=560):
    """Mapa de posição atual com estilo melhorado. Retorna o componente st_folium."""
    from folium.plugins import MarkerCluster
    mapa = folium.Map(
        location=[-18.5, -47.5], zoom_start=6,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    # Legenda flutuante
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
                background:rgba(13,27,42,0.92);border:1px solid rgba(86,110,61,0.5);
                border-radius:10px;padding:12px 16px;font-family:Inter,sans-serif;
                font-size:12px;color:#C8D8A8;min-width:160px;box-shadow:0 4px 16px rgba(0,0,0,0.5)">
      <b style="color:#BFCF99;font-size:13px">ECO Rodovias</b><br><br>
      <span style="color:#7BBF6A">●</span> Ignição ON<br>
      <span style="color:#FF4757">●</span> Ignição OFF<br>
      <span style="color:#F7B731">●</span> Em movimento
    </div>"""
    mapa.get_root().html.add_child(folium.Element(legend_html))

    bounds = []
    for it in itens:
        if it.get("lat") and it.get("lon"):
            try:
                lt, ln = float(it["lat"]), float(it["lon"])
                em_movimento = it.get("velocidade", 0) > 3
                if em_movimento:
                    cor_pin = "#F7B731"
                elif it["ignicao"]:
                    cor_pin = "#7BBF6A"
                else:
                    cor_pin = "#FF4757"

                # Ícone personalizado com número da velocidade
                vel_str = f"{int(it.get('velocidade',0))} km/h" if em_movimento else "Parado"
                icon_html = f"""
                <div style="background:{cor_pin};border:2px solid rgba(255,255,255,0.3);
                            border-radius:50%;width:32px;height:32px;
                            display:flex;align-items:center;justify-content:center;
                            font-size:9px;font-weight:700;color:#0D1B2A;
                            box-shadow:0 2px 8px rgba(0,0,0,0.6)">
                  {"▶" if em_movimento else "■"}
                </div>"""
                icon = folium.DivIcon(
                    html=icon_html,
                    icon_size=(32, 32),
                    icon_anchor=(16, 16),
                )

                popup_html = f"""
                <div style="font-family:Inter,sans-serif;font-size:13px;
                            background:#0D1B2A;color:#E8EFD8;
                            border-radius:8px;padding:12px;min-width:220px">
                  <b style="color:{cor_pin};font-size:14px">{it['desc']}</b><br>
                  <span style="color:#8FA882">Placa:</span> {it['placa']}<br>
                  <span style="color:#8FA882">Status:</span>
                  {'Em movimento — ' + vel_str if em_movimento else ('Ligado parado' if it['ignicao'] else 'Desligado')}<br>
                  <span style="color:#8FA882">Odômetro:</span> {it['odometro']:,} km<br>
                  <span style="color:#8FA882">Local:</span> {it.get('cidade','—')} / {it.get('uf','—')}<br>
                  <span style="color:#8FA882">Atualizado:</span> {it.get('dt_posicao','—')}
                </div>"""

                folium.Marker(
                    [lt, ln],
                    icon=icon,
                    tooltip=folium.Tooltip(
                        f"<b>{it['motorista']}</b><br>{vel_str}",
                        style="background:#0D1B2A;color:#E8EFD8;border:1px solid #566E3D;"
                              "font-family:Inter;font-size:12px;border-radius:6px;"
                    ),
                    popup=folium.Popup(popup_html, max_width=300),
                ).add_to(mapa)
                bounds.append([lt, ln])
            except Exception:
                pass

    if bounds:
        lats = [c[0] for c in bounds]
        lons = [c[1] for c in bounds]
        mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    st_folium(mapa, width="100%", height=height, key=map_key, returned_objects=[])


# =============================================================================
# RENDER: ESTATÍSTICAS
# =============================================================================

def _render_estatisticas(itens):
    """Estatísticas — análise individual por motorista com scroll infinito."""

    # ── CSS for stats cards ──────────────────────────────────────────────────
    st.markdown("""
    <style>
    .st-card{background:rgba(18,25,38,.85);backdrop-filter:blur(12px);
      -webkit-backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.06);
      border-radius:16px;padding:16px;margin-bottom:12px;transition:border-color .2s}
    .st-card:hover{border-color:rgba(123,191,106,.2)}
    .st-hdr{display:flex;align-items:center;gap:10px;margin-bottom:10px}
    .st-av{width:44px;height:44px;border-radius:50%;display:flex;
      align-items:center;justify-content:center;font-size:.9rem;
      font-weight:700;color:#fff;flex-shrink:0}
    .st-name{font-size:.92rem;font-weight:700;color:#E8EFD8;flex:1;min-width:0;
      overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .st-ign{font-size:.62rem;font-weight:700;padding:3px 10px;border-radius:12px;
      display:inline-flex;align-items:center;gap:4px}
    .st-ign.on{background:rgba(123,191,106,.15);color:#7BBF6A;border:1px solid rgba(123,191,106,.3)}
    .st-ign.mov{background:rgba(247,183,49,.15);color:#F7B731;border:1px solid rgba(247,183,49,.3)}
    .st-ign.off{background:rgba(255,71,87,.1);color:#FF4757;border:1px solid rgba(255,71,87,.2)}
    .st-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:6px;margin-bottom:8px}
    .st-met{background:rgba(255,255,255,.04);border-radius:10px;padding:8px;text-align:center}
    .st-met .v{font-size:.95rem;font-weight:700;line-height:1.2}
    .st-met .l{font-size:.52rem;color:#6b7f8d;letter-spacing:.03em;margin-top:2px}
    .st-loc{font-size:.7rem;color:#8FA882;padding:6px 0;
      border-top:1px solid rgba(255,255,255,.04);margin-top:4px}
    .st-placa{font-size:.6rem;color:#6b7f8d;background:rgba(255,255,255,.04);
      padding:2px 8px;border-radius:8px;display:inline-block}
    .st-filter-row{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
    .st-fbtn{background:rgba(255,255,255,.06);backdrop-filter:blur(8px);
      border:1px solid rgba(255,255,255,.08);border-radius:20px;
      padding:8px 16px;display:flex;align-items:center;gap:6px;cursor:pointer;
      transition:all .15s;flex-shrink:0}
    .st-fbtn:hover{background:rgba(255,255,255,.1)}
    .st-fbtn .fv{font-size:1rem;font-weight:700;line-height:1}
    .st-fbtn .fl{font-size:.6rem;color:#8FA882}
    </style>""", unsafe_allow_html=True)

    df = pd.DataFrame(itens)
    ligados    = int(df["ignicao"].sum())
    deslig     = len(df) - ligados
    em_mov     = int((df["velocidade"] > 3).sum())
    h_dir_total = round(df["tempo_dir_h"].sum(), 1)

    # ── Interactive KPI filter buttons ────────────────────────────────────────
    filtro = st.radio(
        "Filtrar por:",
        options=["Todos", "🟢 Ligados", "🟡 Em Movimento", "🔴 Desligados"],
        index=0,
        horizontal=True,
        key="stats_filtro",
    )

    # KPI chips with counts
    st.markdown(f"""
    <div class="st-filter-row">
      <div class="st-fbtn"><span class="fv" style="color:#7BBF6A">{len(df)}</span>
        <span class="fl">veículos</span></div>
      <div class="st-fbtn"><span class="fv" style="color:#4CC9F0">{ligados}</span>
        <span class="fl">ligados</span></div>
      <div class="st-fbtn"><span class="fv" style="color:#F7B731">{em_mov}</span>
        <span class="fl">andando</span></div>
      <div class="st-fbtn"><span class="fv" style="color:#FF6B6B">{deslig}</span>
        <span class="fl">desligados</span></div>
      <div class="st-fbtn"><span class="fv" style="color:#A29BFE">{h_dir_total:.0f}h</span>
        <span class="fl">dirigindo</span></div>
    </div>""", unsafe_allow_html=True)

    # Apply filter
    if filtro == "🟢 Ligados":
        df_show = df[df["ignicao"] == True]
    elif filtro == "🟡 Em Movimento":
        df_show = df[(df["ignicao"] == True) & (df["velocidade"] > 3)]
    elif filtro == "🔴 Desligados":
        df_show = df[df["ignicao"] == False]
    else:
        df_show = df

    if df_show.empty:
        st.info("Nenhum veículo nesta categoria.")
        return

    # ── Sort: moving first, then ON-stopped, then OFF ────────────────────────
    def _sort_key(row):
        if row["velocidade"] > 3:
            return (0, -row["velocidade"])
        if row["ignicao"]:
            return (1, 0)
        return (2, 0)

    df_sorted = df_show.copy()
    df_sorted["_sort"] = df_sorted.apply(_sort_key, axis=1)
    df_sorted = df_sorted.sort_values("_sort")

    # ── Individual cards — infinite scroll ────────────────────────────────────
    _SEQ = ["#7BBF6A","#4CC9F0","#F7B731","#FF6B6B","#A29BFE","#FD79A8","#00CEC9"]

    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        initials = "".join(w[0] for w in row["motorista"].split()[:2]).upper()
        vel = row.get("velocidade", 0)
        em_movimento = vel > 3
        cor_av = _SEQ[idx % len(_SEQ)]

        # Ignition badge
        if em_movimento:
            ign_cls = "mov"
            ign_txt = f"🟡 {int(vel)} km/h"
        elif row["ignicao"]:
            ign_cls = "on"
            ign_txt = "🟢 Ligado"
        else:
            ign_cls = "off"
            ign_txt = "🔴 Desligado"

        # Metrics
        odo = row.get("odometro", 0)
        h_dir = row.get("tempo_dir_h", 0)
        h_par = row.get("tempo_par_min", 0)
        horim = row.get("horimetro", 0)
        bat = row.get("bateria", "")
        cidade = row.get("cidade", "—")
        uf = row.get("uf", "")
        placa = row.get("placa", "")
        contrato = row.get("contrato", "")
        dt_pos = row.get("dt_posicao", "—")

        # Try to extract hour from dt_posicao for "ligou às" info
        hora_lig = ""
        if dt_pos and dt_pos != "—":
            try:
                hora_lig = dt_pos.split(" ")[1] if " " in dt_pos else ""
            except Exception:
                pass

        card_html = f"""
        <div class="st-card">
          <div class="st-hdr">
            <div class="st-av" style="background:linear-gradient(135deg,{cor_av},{cor_av}88)">{initials}</div>
            <div style="flex:1;min-width:0">
              <div class="st-name">{row['motorista']}</div>
              <div style="display:flex;gap:4px;align-items:center;margin-top:2px">
                <span class="st-placa">{placa}</span>
                <span style="font-size:.58rem;color:#6b7f8d">{contrato}</span>
              </div>
            </div>
            <span class="st-ign {ign_cls}">{ign_txt}</span>
          </div>
          <div class="st-grid">
            <div class="st-met"><div class="v" style="color:#7BBF6A">{h_dir:.1f}h</div>
              <div class="l">Dirigindo</div></div>
            <div class="st-met"><div class="v" style="color:#F7B731">{h_par:.0f}min</div>
              <div class="l">Parado lig.</div></div>
            <div class="st-met"><div class="v" style="color:#4CC9F0">{odo:,}</div>
              <div class="l">Hodômetro km</div></div>
            <div class="st-met"><div class="v" style="color:#A29BFE">{int(vel)}</div>
              <div class="l">km/h agora</div></div>
            {"<div class='st-met'><div class='v' style=color:#00CEC9>" + str(horim) + "</div><div class='l'>Horímetro</div></div>" if horim else ""}
          </div>
          <div class="st-loc">
            📍 {cidade}{(' · ' + uf) if uf else ''} · Atualizado: {dt_pos}
            {(' · Última atividade: ' + hora_lig) if hora_lig else ''}
          </div>
        </div>"""

        st.markdown(card_html, unsafe_allow_html=True)


# =============================================================================
# RENDER: ROTA INDIVIDUAL
# =============================================================================

def _render_rota_individual(itens):
    st.markdown("**Selecione o veículo e o período:**")
    opcoes = {f"{it['motorista']}  [{it['ultima_data']}]": it for it in itens}
    r1, r2, r3, r4 = st.columns([3, 2, 2, 1])
    with r1:
        sel = st.selectbox("Motorista [última data]:", list(opcoes.keys()), key="logos_sel_v")
    it_sel = opcoes[sel]
    with r2:
        d_ini = st.date_input("De:", value=it_sel["ultima_data"], key="logos_r_ini")
    with r3:
        d_fim = st.date_input("Até:", value=it_sel["ultima_data"], key="logos_r_fim")
    with r4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        ver_rota = st.button("Ver Rota", key="logos_btn_rota", use_container_width=True)

    if ver_rota:
        with st.spinner("Buscando rota..."):
            try:
                sess2, _ = _logos_login()
                hist = _logos_get_rota(
                    sess2, it_sel["idvei"],
                    d_ini.strftime("%Y-%m-%d 00:00"),
                    d_fim.strftime("%Y-%m-%d 23:59"),
                )
                if not hist:
                    st.warning(f"Nenhuma posição para {d_ini} – {d_fim}. Tente outras datas.")
                    return
                st.session_state["logos_rota"]     = hist
                st.session_state["logos_rota_sel"] = sel
                st.session_state["logos_rota_cor"] = it_sel["cor"]
            except Exception as e:
                st.error(f"{e}")
                return

    hist = st.session_state.get("logos_rota", [])
    if not hist:
        return

    coords = []
    cidades_rota = []
    for p in hist:
        lt = p.get("pos_coordenada_latitude")
        ln = p.get("pos_coordenada_longitude")
        if lt and ln:
            try:
                coords.append([float(lt), float(ln)])
            except Exception:
                pass
        cidade = p.get("pos_end_cidade", "")
        if cidade and (not cidades_rota or cidades_rota[-1] != cidade):
            cidades_rota.append(cidade)

    if not coords:
        st.warning("Sem coordenadas válidas neste período.")
        return

    cor_rota  = st.session_state.get("logos_rota_cor", "#4CC9F0")
    desc_rota = st.session_state.get("logos_rota_sel", sel)

    # Cards da rota
    km_rota = _km_from_hist(hist)
    c1, c2, c3 = st.columns(3)
    c1.metric("Posições GPS", len(coords))
    c2.metric("Km percorridos", f"{km_rota:,} km")
    c3.metric("Cidades passadas", len(set(cidades_rota)))

    if cidades_rota:
        st.caption("Rota: " + " → ".join(dict.fromkeys(cidades_rota)))

    mapa_r = folium.Map(tiles="CartoDB dark_matter")
    folium.PolyLine(coords, color=cor_rota, weight=4, opacity=0.9,
                    tooltip=desc_rota).add_to(mapa_r)
    folium.CircleMarker(coords[0],  radius=8, color="#00FF00", fill=True,
                        fill_color="#00FF00", tooltip="▶ Início").add_to(mapa_r)
    folium.CircleMarker(coords[-1], radius=8, color="#FF4757", fill=True,
                        fill_color="#FF4757", tooltip="⏹ Fim").add_to(mapa_r)
    lats = [c[0] for c in coords]; lons = [c[1] for c in coords]
    mapa_r.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    st_folium(mapa_r, width="100%", height=500, key="logos_mapa_rota", returned_objects=[])


# =============================================================================
# RENDER: ANÁLISE DE PERÍODO
# =============================================================================

def _render_analise_periodo(itens):
    _C = {
        "bg":      "rgba(0,0,0,0)",
        "grid":    "rgba(255,255,255,0.06)",
        "text":    "#C8D8A8",
        "eco135":  "#7BBF6A",
        "cerrado": "#4CC9F0",
        "acc1":    "#F7B731",
        "acc2":    "#FF6B6B",
        "seq":     ["#7BBF6A","#4CC9F0","#F7B731","#FF6B6B","#A29BFE","#FD79A8","#00CEC9"],
    }
    _NO_INTERACT = dict(displayModeBar=False, scrollZoom=False)
    _BASE = dict(
        paper_bgcolor=_C["bg"], plot_bgcolor=_C["bg"],
        font=dict(family="Inter, sans-serif", color=_C["text"], size=12),
        margin=dict(l=12, r=12, t=36, b=12),
        dragmode=False,
    )

    # Padrão fixo: 01/03/2026 → hoje (conforme solicitado)
    _d_min = date(2026, 3, 1)
    _d_max = date.today()

    st.markdown(
        "Histórico consolidado de toda a frota ECO. "
        f"**Período padrão: 01/03/2026 → {_d_max.strftime('%d/%m/%Y')}**"
    )
    p1, p2, p3 = st.columns([2, 2, 1])
    with p1:
        pd_ini = st.date_input("Data início:", value=_d_min, key="logos_p_ini")
    with p2:
        pd_fim = st.date_input("Data fim:", value=_d_max, key="logos_p_fim")
    with p3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        carregar = st.button(" Carregar Período", key="logos_btn_periodo", use_container_width=True)

    if carregar:
        resultados = []
        all_pontos = []
        _raw_sample = None   # primeiro ponto bruto para diagnóstico de campos
        prog = st.progress(0, text="Iniciando...")
        with st.spinner("Buscando histórico de todos os veículos ECO..."):
            try:
                sess3, _ = _logos_login()
                for idx, it in enumerate(itens):
                    prog.progress((idx + 1) / len(itens),
                                  text=f"Buscando {it['motorista']} ({idx+1}/{len(itens)})...")
                    try:
                        hist = _logos_get_rota(
                            sess3, it["idvei"],
                            pd_ini.strftime("%Y-%m-%d 00:00"),
                            pd_fim.strftime("%Y-%m-%d 23:59"),
                        )
                    except Exception:
                        hist = []

                    if hist:
                        if _raw_sample is None:
                            _raw_sample = hist[0]  # guarda primeiro ponto para debug
                        km = _km_from_hist(hist)
                        cidades = list(dict.fromkeys(
                            str(_pick(p, _HIST_CID_FIELDS) or "") for p in hist
                            if _pick(p, _HIST_CID_FIELDS)
                        ))
                        ufs = list(dict.fromkeys(
                            str(_pick(p, _HIST_UF_FIELDS) or "") for p in hist
                            if _pick(p, _HIST_UF_FIELDS)
                        ))
                        # Coleta pontos temporais (com detecção automática de campos)
                        for p in hist:
                            dt_str = str(_pick(p, _HIST_DT_FIELDS, ""))
                            try:
                                dt  = pd.to_datetime(dt_str)
                                vel = float(_pick(p, _HIST_VEL_FIELDS) or 0)
                                odo = int(float(_pick(p, _HIST_ODO_FIELDS) or 0))
                                all_pontos.append({
                                    "motorista":  it["motorista"],
                                    "contrato":   it["contrato"],
                                    "dt":         dt.isoformat(),   # timestamp completo
                                    "hora":       dt.hour,
                                    "dia_semana": dt.dayofweek,
                                    "data":       dt.date(),
                                    "odometro":   odo,
                                    "velocidade": vel,
                                    # idle = PARADO (vel ≤ 3 km/h), independente de ignição
                                    "idle":       vel <= 3,
                                    "cidade":     str(_pick(p, _HIST_CID_FIELDS) or ""),
                                    "uf":         str(_pick(p, _HIST_UF_FIELDS) or ""),
                                })
                            except Exception:
                                pass
                    else:
                        km = 0; cidades = []; ufs = []

                    resultados.append({
                        "contrato":    it["contrato"],
                        "motorista":   it["motorista"],
                        "placa":       it["placa"],
                        "km_periodo":  km,
                        "registros":   len(hist),
                        "cidades":     len(set(cidades)),
                        "estados":     ", ".join(ufs[:3]),
                        "rota_resumo": " → ".join(list(dict.fromkeys(cidades))[:5]),
                    })
                prog.empty()
                st.session_state["logos_periodo_result"] = resultados
                st.session_state["logos_periodo_pontos"] = all_pontos
                st.session_state["logos_periodo_label"]  = f"{pd_ini} a {pd_fim}"
                st.session_state["logos_hist_sample"] = _raw_sample
            except Exception as e:
                st.error(f" {e}")
                return

    res = st.session_state.get("logos_periodo_result", [])
    if not res:
        return

    label_periodo = st.session_state.get("logos_periodo_label", "")
    st.markdown(f"#### Resultados: {label_periodo}")

    df_p  = pd.DataFrame(res)
    pontos = st.session_state.get("logos_periodo_pontos", [])
    df_pt  = pd.DataFrame(pontos) if pontos else pd.DataFrame()

    total_km = df_p["km_periodo"].sum()

    if total_km == 0 and df_pt.empty:
        st.warning(
            "️ Nenhum dado encontrado para este período. "
            "Verifique se as datas selecionadas têm dados disponíveis — "
            f"a última posição conhecida dos veículos é **{_d_max.strftime('%d/%m/%Y')}**."
        )
        return

    # Se tem pontos GPS mas km=0, mostrar aviso útil
    if total_km == 0 and not df_pt.empty:
        total_regs = df_p["registros"].sum()
        st.warning(
            f"️ {total_regs} registros GPS encontrados, mas km calculado = 0. "
            f"Isso pode significar que o campo odômetro está zerado na API. "
            f"Usando velocidade × tempo como método alternativo..."
        )

    # ── Métricas base ──────────────────────────────────────────────────────────
    # ── Debug: campos reais do historicoposicao ────────────────────────────────
    _sample = st.session_state.get("logos_hist_sample")
    if _sample:
        total_km_check = sum(r.get("km_periodo", 0) for r in res)
        if total_km_check == 0:
            st.error("️ Km = 0 para todos os veículos. Exibindo campos reais da API para diagnóstico:")
            with st.expander(" Campos retornados pelo historicoposicao (clique para ver)", expanded=True):
                st.json({k: v for k, v in _sample.items()})
                st.caption("Os campos acima são os REAIS retornados. Se 'pos_odometro' não aparecer, "
                            "o nome correto está nessa lista.")
        else:
            with st.expander(" Debug: campos da API (opcional)"):
                st.json({k: v for k, v in _sample.items()})

    CUSTO_KM       = 0.62   # R$/km — gasolina ~11 km/L × R$6,82/L (mar/2026)
    CUSTO_IDLE_H   = 6.82   # R$/h idle — 1L gasolina/h × R$6,82/L (mar/2026)
    LIMIAR_IDLE_OK = 5      # % idle aceitável (Geotab: alvo ≤5%)
    LIMIAR_IDLE_AL = 10     # % idle alarme (Geotab: >10% = crítico)
    LIMIAR_KM_WA   = 300    # km/dia atenção
    LIMIAR_KM_AL   = 500    # km/dia alarme
    dias_nome      = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]

    ativos   = (df_p["registros"] > 0).sum()
    inativos = len(df_p) - ativos
    n_dias   = max(1, (pd.to_datetime(label_periodo.split(" a ")[-1]) -
                       pd.to_datetime(label_periodo.split(" a ")[0])).days + 1) if " a " in label_periodo else 1

    # ── Diagnóstico automático de campos ──────────────────────────────────────
    vel_detectada = (not df_pt.empty and "velocidade" in df_pt.columns
                     and float(df_pt["velocidade"].max()) > 0)
    odo_detectado = (not df_pt.empty and "odometro" in df_pt.columns
                     and int(df_pt["odometro"].max()) > 0)
    dt_detectado  = "dt" in df_pt.columns if not df_pt.empty else False

    _diag_msgs = []
    if not vel_detectada:
        _diag_msgs.append("️ **Velocidade** não detectada nos dados — eficiência e idle calculados por estimativa")
    if not odo_detectado:
        _diag_msgs.append("️ **Odômetro** zerado — km calculados por velocidade × tempo ou GPS")
    if _diag_msgs:
        with st.expander(" Diagnóstico de dados da API", expanded=True):
            for m in _diag_msgs: st.markdown(m)
            _sample = st.session_state.get("logos_hist_sample")
            if _sample:
                st.caption("Campos reais retornados pelo historicoposicao:")
                st.json({k: v for k, v in list(_sample.items())[:25]})

    # ── Agrega KPIs por motorista usando timestamps reais ─────────────────────
    # Usa intervalos reais entre GPS points para calcular horas (sem MINS_POR_PONTO)
    # idle = vel ≤ 3 km/h (parado com motor ligado ou desligado)
    if not df_pt.empty:
        agg = {}
        for mot, grp in df_pt.groupby("motorista"):
            n_total = len(grp)
            n_fds   = int((grp["dia_semana"] >= 5).sum())

            # ── Tempo: usa timestamps reais (cap 30 min entre pontos) ─────────
            if dt_detectado and n_total >= 2:
                grp_s = grp.sort_values("dt")
                times = pd.to_datetime(grp_s["dt"])
                # intervalo entre pontos consecutivos (horas), gap máx = 0.5h
                deltas_h = (times.diff().dt.total_seconds()
                                  .div(3600).fillna(0).clip(lower=0, upper=0.5))
                h_rastreio = float(deltas_h.sum())
                # h_mov = soma dos intervalos em que a velocidade do ponto ANTERIOR era > 3
                if vel_detectada:
                    vel_vals   = grp_s["velocidade"].values
                    mask_prev  = vel_vals[:-1] > 3        # vel do ponto i (prev)
                    h_mov      = float(deltas_h.values[1:][mask_prev].sum())
                else:
                    h_mov      = h_rastreio * 0.6          # estimativa 60%
            else:
                # Fallback: contagem de pontos × 3 min
                h_rastreio = n_total * 3 / 60
                if vel_detectada:
                    n_mov  = int((grp["velocidade"] > 3).sum())
                    h_mov  = n_mov * 3 / 60
                else:
                    h_mov  = h_rastreio * 0.6

            h_idle   = max(0.0, h_rastreio - h_mov)
            idle_pct = round(h_idle / max(0.01, h_rastreio) * 100, 1)
            fds_pct  = round(n_fds / max(1, n_total) * 100, 1)

            # ── Km: usa km_periodo calculado pelo historico ───────────────────
            km       = float(df_p.loc[df_p["motorista"] == mot, "km_periodo"].values[0]) \
                       if mot in df_p["motorista"].values else 0.0

            # ── Eficiência: km / h_mov (sanity cap 130 km/h) ─────────────────
            eff_raw  = km / max(0.1, h_mov)
            # Se eficiência calculada > 130, dado insuficiente
            eff      = round(min(eff_raw, 130.0), 1) if eff_raw <= 130 else None

            # ── Custos ────────────────────────────────────────────────────────
            custo_cb   = round(km * CUSTO_KM, 2)
            custo_id   = round(h_idle * CUSTO_IDLE_H, 2)

            # ── Velocidade máxima ─────────────────────────────────────────────
            vel_max = float(grp["velocidade"].max()) if vel_detectada else 0.0

            # ── Local onde mais ficou parado ──────────────────────────────────
            grp_idle = grp[(grp["velocidade"] <= 3) & (grp["cidade"] != "")]
            if not grp_idle.empty:
                local_cnt = grp_idle.groupby(["cidade","uf"]).size()
                _idx = local_cnt.idxmax()
                # Tempo estimado no local: intervalos de tempo no grupo idle
                if dt_detectado:
                    _g2 = grp_s[grp_s["cidade"] == _idx[0]] if "grp_s" in dir() else grp_idle
                    _times2 = pd.to_datetime(_g2["dt"])
                    idle_local_min = int(_times2.diff().dt.total_seconds()
                                         .fillna(0).clip(upper=1800).sum() / 60)
                else:
                    idle_local_min = int(local_cnt.max() * 3)
                idle_local = f"{_idx[0]} / {_idx[1]}"
            else:
                idle_local, idle_local_min = "—", 0

            agg[mot] = {
                "motorista":      mot,
                "km_periodo":     km,
                "h_rastreio":     round(h_rastreio, 1),
                "h_mov":          round(h_mov, 1),
                "h_idle":         round(h_idle, 1),
                "idle_pct":       idle_pct,
                "fds_pct":        fds_pct,
                "n_fds":          n_fds,
                "efficiency":     eff,          # None = dado insuficiente
                "custo_cb":       custo_cb,
                "custo_idle":     custo_id,
                "custo_total":    round(custo_cb + custo_id, 2),
                "vel_max":        round(vel_max, 0),
                "idle_local":     idle_local,
                "idle_local_min": idle_local_min,
            }
        df_mot = pd.DataFrame(list(agg.values()))
    else:
        df_mot = pd.DataFrame()

    total_custo_cb   = df_mot["custo_cb"].sum()   if not df_mot.empty else 0
    total_custo_idle = df_mot["custo_idle"].sum()  if not df_mot.empty else 0
    total_custo      = df_mot["custo_total"].sum() if not df_mot.empty else 0
    km_dia           = total_km / n_dias

    # ═══════════════════════════════════════════════════════════════════════════
    # CARDS RESUMO
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px">
      <div style="flex:1;min-width:110px;background:rgba(123,191,106,0.12);border:1px solid #7BBF6A55;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#7BBF6A">{total_km:,.0f} km</div>
        <div style="color:#C8D8A8;font-size:.75rem">Total rodado</div></div>
      <div style="flex:1;min-width:110px;background:rgba(76,201,240,0.12);border:1px solid #4CC9F055;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#4CC9F0">{km_dia:,.0f} km</div>
        <div style="color:#C8D8A8;font-size:.75rem">Média km/dia</div></div>
      <div style="flex:1;min-width:110px;background:rgba(247,183,49,0.12);border:1px solid #F7B73155;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#F7B731">R$ {total_custo_cb:,.0f}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Custo combustível est.</div></div>
      <div style="flex:1;min-width:110px;background:rgba(255,107,107,0.12);border:1px solid #FF6B6B55;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#FF6B6B">R$ {total_custo_idle:,.0f}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Custo idle est.</div></div>
      <div style="flex:1;min-width:110px;background:rgba(162,155,254,0.12);border:1px solid #A29BFE55;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#A29BFE">R$ {total_custo:,.0f}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Custo total estimado</div></div>
      <div style="flex:1;min-width:110px;background:rgba(123,191,106,0.12);border:1px solid #7BBF6A55;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#7BBF6A">{ativos}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Veículos ativos</div></div>
      <div style="flex:1;min-width:110px;background:rgba(255,107,107,0.08);border:1px solid #FF6B6B33;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#FF6B6B">{inativos}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Sem dados</div></div>
      <div style="flex:1;min-width:110px;background:rgba(247,183,49,0.08);border:1px solid #F7B73133;
                  border-radius:10px;padding:14px;text-align:center">
        <div style="font-size:1.6rem;font-weight:700;color:#F7B731">{n_dias}</div>
        <div style="color:#C8D8A8;font-size:.75rem">Dias analisados</div></div>
    </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 1 — ️ ALERTAS CRÍTICOS (nomes específicos)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## ️ Alertas Críticos — Pessoas e Quantidades")
    st.caption("Baseado em: Geotab Fleet KPIs · Lei 13.103/2015 · CTB Art. 61 · gasolina R$6,82/L (preço médio BR mar/2026)")

    if not df_mot.empty:
        a1, a2, a3 = st.columns(3)

        # Alerta 1: Idle > limiar
        with a1:
            df_idle_al = df_mot[df_mot["idle_pct"] > LIMIAR_IDLE_AL].sort_values("idle_pct", ascending=False)
            st.markdown(f"""
            <div style="background:rgba(255,70,70,0.12);border:1px solid #FF6B6B88;border-radius:10px;
                        padding:14px;margin-bottom:12px">
              <div style="color:#FF6B6B;font-weight:700;font-size:1rem">
                 Motor Ocioso &gt;{LIMIAR_IDLE_AL}% — {len(df_idle_al)} motorista(s)
              </div>
              <div style="color:#C8D8A8;font-size:.75rem">Benchmark Geotab: alvo ≤5%, alarme &gt;10%<br>
              Custo: ~R$5,09/hora parado</div>
            </div>""", unsafe_allow_html=True)
            if not df_idle_al.empty:
                tab_idle = df_idle_al[["motorista","idle_pct","h_idle","custo_idle"]].copy()
                tab_idle.columns = ["Motorista","Idle %","Horas idle","Custo idle (R$)"]
                st.dataframe(tab_idle, use_container_width=True, hide_index=True)
            else:
                st.success("Nenhum motorista acima do limite.")
            df_idle_wa = df_mot[(df_mot["idle_pct"] > LIMIAR_IDLE_OK) & (df_mot["idle_pct"] <= LIMIAR_IDLE_AL)]
            if not df_idle_wa.empty:
                st.markdown(f" **Atenção ({LIMIAR_IDLE_OK}–{LIMIAR_IDLE_AL}%):** {', '.join(df_idle_wa['motorista'].tolist())}")

        # Alerta 2: Km/dia excessivo
        with a2:
            if not df_pt.empty and "data" in df_pt.columns and "odometro" in df_pt.columns:
                _dfo = df_pt[df_pt["odometro"] > 0]
                df_daily_v = (_dfo.groupby(["motorista","data"])["odometro"]
                                    .agg(["max","min"]).reset_index())
                df_daily_v["km_dia"] = (df_daily_v["max"] - df_daily_v["min"]).clip(lower=0, upper=1500)
                dias_alarme = df_daily_v[df_daily_v["km_dia"] > LIMIAR_KM_AL].sort_values("km_dia", ascending=False)
                dias_atencao = df_daily_v[(df_daily_v["km_dia"] > LIMIAR_KM_WA) &
                                          (df_daily_v["km_dia"] <= LIMIAR_KM_AL)]
                st.markdown(f"""
                <div style="background:rgba(255,70,70,0.12);border:1px solid #FF6B6B88;border-radius:10px;
                            padding:14px;margin-bottom:12px">
                  <div style="color:#FF6B6B;font-weight:700;font-size:1rem">
                     Km/dia &gt;{LIMIAR_KM_AL} — {len(dias_alarme)} ocorrência(s)
                  </div>
                  <div style="color:#C8D8A8;font-size:.75rem">Alarme: &gt;500 km/dia ≈ risco Lei 13.103<br>
                  {len(dias_atencao)} ocorrências em zona atenção ({LIMIAR_KM_WA}–{LIMIAR_KM_AL} km)</div>
                </div>""", unsafe_allow_html=True)
                if not dias_alarme.empty:
                    tab_al = dias_alarme[["motorista","data","km_dia"]].copy()
                    tab_al.columns = ["Motorista","Data","Km no dia"]
                    st.dataframe(tab_al, use_container_width=True, hide_index=True)
                else:
                    st.success("Nenhum dia com >500 km.")

        # Alerta 3: Fim de semana
        with a3:
            if not df_mot.empty and "n_fds" in df_mot.columns:
                df_fds_al = df_mot[df_mot["n_fds"] > 0].sort_values("fds_pct", ascending=False)
                st.markdown(f"""
                <div style="background:rgba(255,183,49,0.12);border:1px solid #F7B73188;border-radius:10px;
                            padding:14px;margin-bottom:12px">
                  <div style="color:#F7B731;font-weight:700;font-size:1rem">
                     Ativos no Fim de Semana — {len(df_fds_al)} motorista(s)
                  </div>
                  <div style="color:#C8D8A8;font-size:.75rem">Qualquer trip FDS sem OS aprovada = custo não justificado<br>
                  Benchmark: 0% FDS sem autorização</div>
                </div>""", unsafe_allow_html=True)
                if not df_fds_al.empty:
                    tab_fds = df_fds_al[["motorista","n_fds","fds_pct","km_periodo"]].copy()
                    tab_fds.columns = ["Motorista","Reg. FDS","% do total","Km total"]
                    st.dataframe(tab_fds, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 2 —  ANÁLISE DE CUSTO POR MOTORISTA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Custo Estimado por Motorista")
    st.caption("Combustível: R$0,62/km · Idle: R$6,82/h (1L gasolina/h × R$6,82/L — preço médio BR mar/2026)")

    if not df_mot.empty:
        df_custo = df_mot[df_mot["km_periodo"] > 0].sort_values("custo_total", ascending=True)

        fig_custo = go.Figure()
        fig_custo.add_trace(go.Bar(
            x=df_custo["custo_cb"], y=df_custo["motorista"], orientation="h",
            name="Combustível (R$)", marker_color="#7BBF6A", marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>Combustível: R$ %{x:,.0f}<extra></extra>",
        ))
        fig_custo.add_trace(go.Bar(
            x=df_custo["custo_idle"], y=df_custo["motorista"], orientation="h",
            name="Idle (R$)", marker_color="#FF6B6B", marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>Idle: R$ %{x:,.0f}<extra></extra>",
        ))
        fig_custo.update_layout(
            **_BASE,
            title=dict(text=" Custo estimado: combustível + idle por motorista",
                       font=dict(size=14, color=_C["text"]), x=0),
            barmode="stack",
            height=max(400, len(df_custo) * 22),
            xaxis=dict(tickprefix="R$", tickformat=",", gridcolor=_C["grid"], zeroline=False),
            yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
            legend=dict(orientation="h", y=1.04, x=0),
            bargap=0.2,
        )
        st.plotly_chart(fig_custo, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 3 —  SCORE DE EFICIÊNCIA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Score de Eficiência — km por hora em movimento")
    st.caption("km / horas com vel >3 km/h (cap 120 km/h). Baixo = viagens curtas · Alto = rodovia contínua.")

    if not df_mot.empty:
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            df_eff = df_mot[df_mot["km_periodo"] > 0].sort_values("efficiency", ascending=True)
            media_eff = df_eff["efficiency"].mean()
            cores_eff = [_C["acc2"] if v < media_eff * 0.7
                         else (_C["acc1"] if v < media_eff else _C["eco135"])
                         for v in df_eff["efficiency"]]
            fig_eff = go.Figure(go.Bar(
                x=df_eff["efficiency"], y=df_eff["motorista"], orientation="h",
                marker_color=cores_eff, marker_line_width=0,
                text=[f"{v:.1f} km/h" for v in df_eff["efficiency"]],
                textposition="outside",
                textfont=dict(size=10, color=_C["text"]),
                hovertemplate="<b>%{y}</b>: %{x:.1f} km/h em movimento<extra></extra>",
            ))
            fig_eff.add_vline(x=media_eff, line_dash="dash", line_color=_C["acc1"],
                              annotation_text=f"Média: {media_eff:.1f}",
                              annotation_font_color=_C["acc1"])
            fig_eff.update_layout(
                **_BASE,
                title=dict(text=" Eficiência: km por hora em movimento",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=max(400, len(df_eff) * 22),
                xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
            )
            st.plotly_chart(fig_eff, use_container_width=True, config=_NO_INTERACT)

        with col_e2:
            # Scatter: km_total vs horas_idle — vilões ficam no canto direito-baixo
            df_sc = df_mot[df_mot["km_periodo"] > 0].copy()
            df_sc["tamanho"] = (df_sc["km_periodo"] / df_sc["km_periodo"].max() * 30 + 8).clip(8, 40)
            df_sc["cor"] = df_sc["idle_pct"].apply(
                lambda x: "#FF6B6B" if x > LIMIAR_IDLE_AL else ("#F7B731" if x > LIMIAR_IDLE_OK else "#7BBF6A")
            )
            fig_sc = go.Figure()
            for label, color, mask in [
                (f"Idle OK (≤{LIMIAR_IDLE_OK}%)", "#7BBF6A", df_sc["idle_pct"] <= LIMIAR_IDLE_OK),
                (f"Atenção ({LIMIAR_IDLE_OK}–{LIMIAR_IDLE_AL}%)", "#F7B731",
                 (df_sc["idle_pct"] > LIMIAR_IDLE_OK) & (df_sc["idle_pct"] <= LIMIAR_IDLE_AL)),
                (f"Alarme (>{LIMIAR_IDLE_AL}%)", "#FF6B6B", df_sc["idle_pct"] > LIMIAR_IDLE_AL),
            ]:
                sub = df_sc[mask]
                if not sub.empty:
                    fig_sc.add_trace(go.Scatter(
                        x=sub["h_idle"], y=sub["km_periodo"],
                        mode="markers+text",
                        name=label,
                        marker=dict(color=color, size=sub["tamanho"], opacity=0.85,
                                    line=dict(color="#0D1B2A", width=1)),
                        text=sub["motorista"].str.split().str[0],
                        textposition="top center",
                        textfont=dict(size=9, color=_C["text"]),
                        hovertemplate="<b>%{text}</b><br>Idle: %{x:.1f}h · Km: %{y:,.0f}<extra></extra>",
                        customdata=sub[["motorista","idle_pct"]].values,
                    ))
            fig_sc.update_layout(
                **_BASE,
                title=dict(text=" Km rodado vs Horas idle (tamanho = km total)",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=420,
                xaxis=dict(title="Horas idle", gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(title="Km rodado", gridcolor=_C["grid"], zeroline=False, tickformat=","),
                legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10)),
            )
            st.plotly_chart(fig_sc, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 4 — ⏱️ IDLE TIME DETALHADO
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## ⏱️ Tempo Ocioso — Quem mais desperdiça combustível")

    if not df_mot.empty:
        col_i1, col_i2 = st.columns(2)

        with col_i1:
            df_idle_r = df_mot[df_mot["h_rastreio"] > 0].sort_values("idle_pct", ascending=True)
            cores_idle = [
                _C["eco135"] if v <= LIMIAR_IDLE_OK
                else (_C["acc1"] if v <= LIMIAR_IDLE_AL else _C["acc2"])
                for v in df_idle_r["idle_pct"]
            ]
            fig_idle_pct = go.Figure(go.Bar(
                x=df_idle_r["idle_pct"], y=df_idle_r["motorista"], orientation="h",
                marker_color=cores_idle, marker_line_width=0,
                text=[f"{v:.1f}%" for v in df_idle_r["idle_pct"]],
                textposition="outside",
                textfont=dict(size=10, color=_C["text"]),
                hovertemplate="<b>%{y}</b>: %{x:.1f}% idle<extra></extra>",
            ))
            fig_idle_pct.add_vline(x=LIMIAR_IDLE_OK, line_dash="dot", line_color=_C["acc1"],
                                   annotation_text="Alvo 5%", annotation_font_color=_C["acc1"])
            fig_idle_pct.add_vline(x=LIMIAR_IDLE_AL, line_dash="dash", line_color=_C["acc2"],
                                   annotation_text="Alarme 10%", annotation_font_color=_C["acc2"])
            fig_idle_pct.update_layout(
                **_BASE,
                title=dict(text=" % de Idle por Motorista (verde ≤5% · amarelo 5–10% · vermelho >10%)",
                           font=dict(size=12, color=_C["text"]), x=0),
                height=max(400, len(df_idle_r) * 22),
                xaxis=dict(ticksuffix="%", gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
            )
            st.plotly_chart(fig_idle_pct, use_container_width=True, config=_NO_INTERACT)

        with col_i2:
            df_idle_h = df_mot[df_mot["h_idle"] > 0].sort_values("h_idle", ascending=True)
            fig_idle_h = go.Figure(go.Bar(
                x=df_idle_h["h_idle"], y=df_idle_h["motorista"], orientation="h",
                marker=dict(
                    color=df_idle_h["h_idle"],
                    colorscale=[[0,"#1a1a2a"],[0.5,"#8B2020"],[1,"#FF6B6B"]],
                    line_width=0,
                ),
                text=[f"{h:.1f}h · R${c:.0f}" for h, c in zip(df_idle_h["h_idle"], df_idle_h["custo_idle"])],
                textposition="outside",
                textfont=dict(size=10, color=_C["text"]),
                hovertemplate="<b>%{y}</b>: %{x:.1f}h idle<extra></extra>",
            ))
            fig_idle_h.update_layout(
                **_BASE,
                title=dict(text="⏱️ Horas idle absolutas (h · custo est.)",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=max(400, len(df_idle_h) * 22),
                xaxis=dict(ticksuffix="h", gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
            )
            st.plotly_chart(fig_idle_h, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 4.5 —  COMPORTAMENTO DETALHADO: VEL MAX · IDLE · LOCAL
    # ═══════════════════════════════════════════════════════════════════════════
    if not df_mot.empty:
        st.markdown("---")
        st.markdown("##  Comportamento Detalhado — Velocidade · Idle · Onde Ficou Parado")
        st.caption("Velocidade máxima atingida · horas ligado parado · local de maior permanência")

        # ── Gráfico: velocidade máxima por motorista ──────────────────────────
        col_vm1, col_vm2 = st.columns(2)

        with col_vm1:
            df_vel_max = df_mot[["motorista","vel_max"]].sort_values("vel_max", ascending=True)
            cores_vmax = [
                _C["acc2"] if v > 110 else (_C["acc1"] if v > 90 else _C["eco135"])
                for v in df_vel_max["vel_max"]
            ]
            fig_vmax = go.Figure(go.Bar(
                x=df_vel_max["vel_max"], y=df_vel_max["motorista"], orientation="h",
                marker_color=cores_vmax, marker_line_width=0,
                text=[f"{v:.0f} km/h" for v in df_vel_max["vel_max"]],
                textposition="outside",
                textfont=dict(size=9, color=_C["text"]),
                hovertemplate="<b>%{y}</b>: máx %{x:.0f} km/h<extra></extra>",
            ))
            fig_vmax.add_vline(x=110, line_dash="dash", line_color=_C["acc2"],
                               annotation_text="110 km/h limite", annotation_font_color=_C["acc2"],
                               annotation_position="top right")
            fig_vmax.add_vline(x=90, line_dash="dot", line_color=_C["acc1"],
                               annotation_text="90 km/h recomendado", annotation_font_color=_C["acc1"],
                               annotation_position="top right")
            fig_vmax.update_layout(
                **_BASE,
                title=dict(text=" Velocidade Máxima Atingida por Motorista",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=max(400, len(df_vel_max) * 24),
                xaxis=dict(ticksuffix=" km/h", gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
            )
            st.plotly_chart(fig_vmax, use_container_width=True, config=_NO_INTERACT)

        with col_vm2:
            # Horas ligado parado (idle) por motorista
            df_idle_h2 = df_mot[df_mot["h_idle"] > 0].sort_values("h_idle", ascending=True)
            fig_idle_abs = go.Figure(go.Bar(
                x=df_idle_h2["h_idle"], y=df_idle_h2["motorista"], orientation="h",
                marker=dict(
                    color=df_idle_h2["h_idle"],
                    colorscale=[[0,"#0D2010"],[0.4,"#7B4000"],[1,"#FF6B6B"]],
                    line_width=0,
                    colorbar=dict(title="h idle", thickness=10,
                                  tickfont=dict(color=_C["text"]),
                                  title_font=dict(color=_C["text"])),
                ),
                text=[f"{h:.1f}h parado · R${c:.0f}" for h, c in
                      zip(df_idle_h2["h_idle"], df_idle_h2["custo_idle"])],
                textposition="outside",
                textfont=dict(size=9, color=_C["text"]),
                hovertemplate="<b>%{y}</b>: %{x:.1f}h ligado parado<extra></extra>",
            ))
            fig_idle_abs.update_layout(
                **_BASE,
                title=dict(text="⏸️ Horas Ligado e Parado (idle absoluto)",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=max(400, len(df_idle_h2) * 24),
                xaxis=dict(ticksuffix="h", gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
            )
            st.plotly_chart(fig_idle_abs, use_container_width=True, config=_NO_INTERACT)

        # ── Tabela: local onde mais ficou parado + vel_max + idle ─────────────
        st.markdown("#####  Onde Cada Motorista Mais Ficou Parado")
        df_local = df_mot[["motorista","vel_max","h_idle","idle_pct","idle_local","idle_local_min"]].copy()
        df_local["h_idle_str"]     = df_local["h_idle"].apply(lambda h: f"{h:.1f}h")
        df_local["idle_pct_str"]   = df_local["idle_pct"].apply(lambda p: f"{p:.1f}%")
        df_local["vel_max_str"]    = df_local["vel_max"].apply(lambda v: f"{v:.0f} km/h")
        df_local["idle_local_str"] = df_local.apply(
            lambda r: f"{r['idle_local']} ({r['idle_local_min']} min)" if r["idle_local"] != "—" else "—",
            axis=1
        )
        df_display_local = df_local[["motorista","vel_max_str","h_idle_str","idle_pct_str","idle_local_str"]].copy()
        df_display_local.columns = ["Motorista","Vel. Máxima","H. Ligado Parado","% Idle","Onde Mais Ficou"]
        df_display_local = df_display_local.sort_values("H. Ligado Parado", ascending=False)
        st.dataframe(df_display_local, use_container_width=True, hide_index=True)

        # ── Destaque: top 3 maiores velocidades ───────────────────────────────
        st.markdown("##### ️ Top 5 — Maiores Velocidades Registradas")
        top_vel = df_mot.sort_values("vel_max", ascending=False).head(5)
        cols_tv = st.columns(5)
        for i, (_, row) in enumerate(top_vel.iterrows()):
            with cols_tv[i]:
                cor = _C["acc2"] if row["vel_max"] > 110 else (_C["acc1"] if row["vel_max"] > 90 else _C["eco135"])
                alerta = "" if row["vel_max"] > 110 else ("️" if row["vel_max"] > 90 else "")
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.2);border:1px solid {cor}55;
                            border-radius:10px;padding:12px;text-align:center">
                  <div style="font-size:1.4rem;font-weight:700;color:{cor}">{alerta}</div>
                  <div style="font-size:1.2rem;font-weight:700;color:{cor}">{row['vel_max']:.0f} km/h</div>
                  <div style="font-size:.75rem;color:#C8D8A8;margin-top:4px">
                    {row['motorista'].split()[0]}</div>
                </div>""", unsafe_allow_html=True)

        # ── Destaque: top 3 maior idle ────────────────────────────────────────
        st.markdown("##### ⏸️ Top 5 — Mais Tempo Ligado e Parado")
        top_idle = df_mot.sort_values("h_idle", ascending=False).head(5)
        cols_ti = st.columns(5)
        for i, (_, row) in enumerate(top_idle.iterrows()):
            with cols_ti[i]:
                cor = _C["acc2"] if row["idle_pct"] > LIMIAR_IDLE_AL else (
                      _C["acc1"] if row["idle_pct"] > LIMIAR_IDLE_OK else _C["eco135"])
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.2);border:1px solid {cor}55;
                            border-radius:10px;padding:12px;text-align:center">
                  <div style="font-size:1.2rem;font-weight:700;color:{cor}">{row['h_idle']:.1f}h</div>
                  <div style="font-size:.85rem;color:#F7B731">{row['idle_pct']:.0f}% idle</div>
                  <div style="font-size:.75rem;color:#C8D8A8;margin-top:4px">
                    {row['motorista'].split()[0]}</div>
                  <div style="font-size:.7rem;color:#8FA882">{row['idle_local']}</div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 5 —  RANKING KM + MÉDIA KM/DIA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Quem Mais Rodou no Período")

    col_k1, col_k2 = st.columns(2)

    with col_k1:
        if not df_p.empty:
            cores_c = {c: _C["seq"][i % len(_C["seq"])]
                       for i, c in enumerate(df_p["contrato"].unique())}
            df_km_r = df_p.sort_values("km_periodo", ascending=True)
            fig_km = go.Figure()
            for contrato, grp in df_km_r.groupby("contrato"):
                fig_km.add_trace(go.Bar(
                    x=grp["km_periodo"], y=grp["motorista"], orientation="h",
                    name=contrato, marker_color=cores_c[contrato], marker_line_width=0,
                    text=[f"{v:,.0f} km" for v in grp["km_periodo"]],
                    textposition="outside",
                    textfont=dict(size=10, color=_C["text"]),
                    hovertemplate="<b>%{y}</b><br>%{x:,.0f} km<extra></extra>",
                ))
            fig_km.update_layout(
                **_BASE,
                title=dict(text="Km total por motorista no período",
                           font=dict(size=13, color=_C["text"]), x=0),
                barmode="group", height=max(400, len(df_p) * 22),
                xaxis=dict(tickformat=",", gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
                legend=dict(orientation="h", y=1.04, x=0),
                bargap=0.25,
            )
            st.plotly_chart(fig_km, use_container_width=True, config=_NO_INTERACT)

    with col_k2:
        if not df_pt.empty and "data" in df_pt.columns:
            # Tenta odômetro primeiro; fallback: estima km via velocidade
            _dfo2 = df_pt[df_pt["odometro"] > 0] if "odometro" in df_pt.columns else pd.DataFrame()
            if not _dfo2.empty:
                df_mv = (_dfo2.groupby(["motorista","data"])["odometro"]
                              .agg(["max","min"]).reset_index())
                df_mv["km_d"] = (df_mv["max"] - df_mv["min"]).clip(lower=0, upper=1500)
            else:
                # Fallback: vel × intervalo (≈3 min por ponto)
                df_mv = df_pt.copy()
                df_mv["km_est"] = df_mv["velocidade"] * (MINS_POR_PONTO / 60.0)
                df_mv = (df_mv.groupby(["motorista","data"])["km_est"]
                              .sum().reset_index())
                df_mv = df_mv.rename(columns={"km_est":"km_d"})
                df_mv["km_d"] = df_mv["km_d"].clip(lower=0, upper=1500)
            df_media = (df_mv.groupby("motorista")["km_d"].mean().reset_index()
                              .sort_values("km_d", ascending=True))
            cores_kmdia = [
                _C["acc2"] if v > LIMIAR_KM_AL
                else (_C["acc1"] if v > LIMIAR_KM_WA else _C["eco135"])
                for v in df_media["km_d"]
            ]
            fig_med = go.Figure(go.Bar(
                x=df_media["km_d"], y=df_media["motorista"], orientation="h",
                marker_color=cores_kmdia, marker_line_width=0,
                text=[f"{v:.0f} km/dia" for v in df_media["km_d"]],
                textposition="outside",
                textfont=dict(size=10, color=_C["text"]),
                hovertemplate="<b>%{y}</b>: %{x:.0f} km/dia médio<extra></extra>",
            ))
            fig_med.add_vline(x=LIMIAR_KM_WA, line_dash="dot", line_color=_C["acc1"],
                              annotation_text=f"Atenção {LIMIAR_KM_WA}km",
                              annotation_font_color=_C["acc1"])
            fig_med.add_vline(x=LIMIAR_KM_AL, line_dash="dash", line_color=_C["acc2"],
                              annotation_text=f"Alarme {LIMIAR_KM_AL}km",
                              annotation_font_color=_C["acc2"])
            fig_med.update_layout(
                **_BASE,
                title=dict(text=" Média km/dia (verde OK · amarelo >300 · vermelho >500)",
                           font=dict(size=12, color=_C["text"]), x=0),
                height=max(400, len(df_media) * 22),
                xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
            )
            st.plotly_chart(fig_med, use_container_width=True, config=_NO_INTERACT)

    # ── Km por dia — linha temporal ────────────────────────────────────────────
    if not df_pt.empty and "data" in df_pt.columns:
        _dfo3 = df_pt[df_pt["odometro"] > 0] if "odometro" in df_pt.columns else pd.DataFrame()
        if not _dfo3.empty:
            df_daily2 = (_dfo3.groupby(["data","motorista"])["odometro"]
                              .agg(["max","min"]).reset_index())
            df_daily2["km_d"] = (df_daily2["max"] - df_daily2["min"]).clip(lower=0, upper=1500)
        else:
            df_daily2 = df_pt.copy()
            df_daily2["km_d"] = df_daily2["velocidade"] * (MINS_POR_PONTO / 60.0)
            df_daily2 = (df_daily2.groupby(["data","motorista"])["km_d"]
                                  .sum().reset_index())
            df_daily2["km_d"] = df_daily2["km_d"].clip(lower=0, upper=1500)
        df_agg2 = df_daily2.groupby("data")["km_d"].sum().reset_index().sort_values("data")
        fig_kmd = go.Figure(go.Scatter(
            x=df_agg2["data"].astype(str), y=df_agg2["km_d"],
            mode="lines+markers",
            line=dict(color=_C["acc1"], width=2),
            marker=dict(color=_C["acc1"], size=5),
            fill="tozeroy", fillcolor="rgba(247,183,49,0.10)",
            hovertemplate="<b>%{x}</b>: %{y:,.0f} km (frota)<extra></extra>",
        ))
        fig_kmd.update_layout(
            **_BASE,
            title=dict(text=" Km percorrido por dia — frota total",
                       font=dict(size=13, color=_C["text"]), x=0),
            height=280,
            xaxis=dict(gridcolor=_C["grid"], zeroline=False, tickangle=-35, tickfont=dict(size=9)),
            yaxis=dict(gridcolor=_C["grid"], zeroline=False, tickformat=","),
        )
        st.plotly_chart(fig_kmd, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 6 —  FIM DE SEMANA — QUEM TRABALHOU + KM POR ODÔMETRO
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Fim de Semana — Quem Trabalhou e Quantos Km")
    st.caption(
        "Km calculados por **odômetro**: max − min por motorista por dia · "
        "fallback: velocidade × tempo quando odômetro=0"
    )

    if not df_pt.empty and "dia_semana" in df_pt.columns:
        dias_nome_pt = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
        df_fds = df_pt[df_pt["dia_semana"] >= 5].copy()

        # ── Km FDS por odômetro (max−min por motorista×dia) ──────────────────
        km_fds_por_mot = pd.Series(dtype=float)
        dias_fds_por_mot = pd.Series(dtype=int)

        if not df_fds.empty:
            # Método 1: odômetro
            df_odo_fds = df_fds[df_fds["odometro"] > 0]
            if not df_odo_fds.empty:
                daily_fds = (df_odo_fds.groupby(["motorista","data"])["odometro"]
                                        .agg(odo_max="max", odo_min="min").reset_index())
                daily_fds["km_dia"] = (daily_fds["odo_max"] - daily_fds["odo_min"]).clip(lower=0, upper=1500)
                km_fds_por_mot = daily_fds.groupby("motorista")["km_dia"].sum()
                dias_fds_por_mot = daily_fds[daily_fds["km_dia"] > 0].groupby("motorista")["data"].nunique()

            # Método 2 (fallback): velocidade × tempo para pontos sem odômetro
            df_vel_fds = df_fds[df_fds["odometro"] == 0].copy()
            if not df_vel_fds.empty:
                df_vel_fds["km_pont"] = df_vel_fds["velocidade"] * (MINS_POR_PONTO / 60)
                km_vel_fb = df_vel_fds.groupby("motorista")["km_pont"].sum()
                # Soma ao odômetro (onde já tem) ou adiciona (onde só tem fallback)
                km_fds_por_mot = km_fds_por_mot.add(km_vel_fb, fill_value=0)

            km_fds_por_mot = km_fds_por_mot.round(0)
            if dias_fds_por_mot.empty:
                dias_fds_por_mot = df_fds.groupby("motorista")["data"].nunique()

            # Total de registros FDS por motorista (para %FDS)
            reg_fds = df_fds.groupby("motorista").size()
            reg_tot = df_pt.groupby("motorista").size()

            # DataFrame consolidado
            df_fds_summary = (km_fds_por_mot.reset_index()
                               .rename(columns={0:"km_fds","odometro":"km_fds"}))
            df_fds_summary.columns = ["motorista","km_fds"]
            df_fds_summary["dias_fds"] = (dias_fds_por_mot
                                           .reindex(df_fds_summary["motorista"]).fillna(0).values.astype(int))
            df_fds_summary["reg_fds"]  = (reg_fds
                                           .reindex(df_fds_summary["motorista"]).fillna(0).values.astype(int))
            df_fds_summary["pct_fds"]  = (df_fds_summary["reg_fds"] /
                                           reg_tot.reindex(df_fds_summary["motorista"]).fillna(1).values * 100).round(1)
            df_fds_summary = df_fds_summary.sort_values("km_fds", ascending=False)

            # ── KPIs resumo FDS ───────────────────────────────────────────────
            total_km_fds  = df_fds_summary["km_fds"].sum()
            n_trab_fds    = (df_fds_summary["km_fds"] > 0).sum()
            media_km_fds  = df_fds_summary[df_fds_summary["km_fds"]>0]["km_fds"].mean()
            maior_km_fds  = df_fds_summary.iloc[0]["motorista"] if not df_fds_summary.empty else "—"
            maior_km_val  = df_fds_summary.iloc[0]["km_fds"] if not df_fds_summary.empty else 0

            st.markdown(f"""
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px">
              <div style="flex:1;min-width:120px;background:rgba(255,107,107,0.12);border:1px solid #FF6B6B55;
                          border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:1.6rem;font-weight:700;color:#FF6B6B">{n_trab_fds}</div>
                <div style="color:#C8D8A8;font-size:.75rem">Motoristas no FDS</div></div>
              <div style="flex:1;min-width:120px;background:rgba(247,183,49,0.12);border:1px solid #F7B73155;
                          border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:1.6rem;font-weight:700;color:#F7B731">{total_km_fds:,.0f} km</div>
                <div style="color:#C8D8A8;font-size:.75rem">Km total no FDS</div></div>
              <div style="flex:1;min-width:120px;background:rgba(76,201,240,0.12);border:1px solid #4CC9F055;
                          border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:1.6rem;font-weight:700;color:#4CC9F0">{media_km_fds:,.0f} km</div>
                <div style="color:#C8D8A8;font-size:.75rem">Média km/motorista FDS</div></div>
              <div style="flex:1;min-width:140px;background:rgba(162,155,254,0.12);border:1px solid #A29BFE55;
                          border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:1.1rem;font-weight:700;color:#A29BFE">{maior_km_fds.split()[0] if maior_km_fds != '—' else '—'}</div>
                <div style="font-size:.9rem;color:#F7B731">{maior_km_val:,.0f} km</div>
                <div style="color:#C8D8A8;font-size:.75rem">Mais rodou no FDS</div></div>
            </div>""", unsafe_allow_html=True)

            col_f1, col_f2 = st.columns(2)

            with col_f1:
                # Km por motorista no FDS — ordenado por km
                df_km_plot = df_fds_summary[df_fds_summary["km_fds"] > 0].sort_values("km_fds", ascending=True)
                if not df_km_plot.empty:
                    fig_km_fds = go.Figure(go.Bar(
                        x=df_km_plot["km_fds"],
                        y=df_km_plot["motorista"],
                        orientation="h",
                        marker=dict(
                            color=df_km_plot["km_fds"],
                            colorscale=[[0,"#3a1020"],[0.4,"#A0304A"],[1,"#FF6B6B"]],
                            line_width=0,
                        ),
                        text=[f"{k:,.0f} km · {d}d" for k, d in
                              zip(df_km_plot["km_fds"], df_km_plot["dias_fds"])],
                        textposition="outside",
                        textfont=dict(size=9, color=_C["text"]),
                        hovertemplate="<b>%{y}</b>: %{x:,.0f} km no FDS<extra></extra>",
                    ))
                    fig_km_fds.update_layout(
                        **_BASE,
                        title=dict(text=" Km rodados no Fim de Semana (por odômetro)",
                                   font=dict(size=13, color=_C["text"]), x=0),
                        height=max(380, len(df_km_plot) * 26),
                        xaxis=dict(ticksuffix=" km", gridcolor=_C["grid"], zeroline=False),
                        yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
                    )
                    st.plotly_chart(fig_km_fds, use_container_width=True, config=_NO_INTERACT)

            with col_f2:
                # Distribuição Sábado vs Domingo
                df_fds["dia_label"] = df_fds["dia_semana"].map({5:"Sábado",6:"Domingo"})
                sab_dom = df_fds.groupby(["motorista","dia_label"]).size().unstack(fill_value=0)
                sab_dom = sab_dom.reindex(columns=["Sábado","Domingo"], fill_value=0)
                sab_dom = sab_dom.loc[sab_dom.sum(axis=1).sort_values(ascending=True).index]

                fig_sd = go.Figure()
                fig_sd.add_trace(go.Bar(
                    x=sab_dom["Sábado"], y=sab_dom.index, orientation="h",
                    name="Sábado", marker_color="#F7B731", marker_line_width=0,
                    hovertemplate="<b>%{y}</b> · Sábado: %{x} reg<extra></extra>",
                ))
                fig_sd.add_trace(go.Bar(
                    x=sab_dom["Domingo"], y=sab_dom.index, orientation="h",
                    name="Domingo", marker_color="#FF6B6B", marker_line_width=0,
                    hovertemplate="<b>%{y}</b> · Domingo: %{x} reg<extra></extra>",
                ))
                fig_sd.update_layout(
                    **_BASE, barmode="stack",
                    title=dict(text=" Sábado vs Domingo — registros por motorista",
                               font=dict(size=13, color=_C["text"]), x=0),
                    height=max(380, len(sab_dom) * 26),
                    xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                    yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
                    legend=dict(orientation="h", y=1.04, x=0,
                                font=dict(color=_C["text"], size=10)),
                )
                st.plotly_chart(fig_sd, use_container_width=True, config=_NO_INTERACT)

            # Atividade por dia da semana (toda a frota)
            dia_cnt = (df_pt.groupby("dia_semana").size()
                            .reindex(range(7), fill_value=0).reset_index())
            dia_cnt.columns = ["dia_semana","n"]
            fds_pct_tot = int(dia_cnt[dia_cnt["dia_semana"] >= 5]["n"].sum() /
                              max(1, dia_cnt["n"].sum()) * 100)
            fig_dia = go.Figure(go.Bar(
                x=[dias_nome_pt[d] for d in dia_cnt["dia_semana"]],
                y=dia_cnt["n"],
                marker_color=[_C["acc2"] if d >= 5 else _C["cerrado"] for d in dia_cnt["dia_semana"]],
                marker_line_width=0,
                text=dia_cnt["n"],
                textposition="outside",
                textfont=dict(size=11, color=_C["text"]),
                hovertemplate="<b>%{x}</b>: %{y} registros<extra></extra>",
            ))
            fig_dia.update_layout(
                **_BASE,
                title=dict(text=f" Registros por dia — {fds_pct_tot}% são Sáb/Dom",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=280,
                xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], zeroline=False),
                bargap=0.2,
            )
            st.plotly_chart(fig_dia, use_container_width=True, config=_NO_INTERACT)

            # Tabela detalhada FDS
            st.markdown("#####  Tabela completa — Fim de Semana")
            tab_fds_full = df_fds_summary.copy()
            tab_fds_full["km_fds"] = tab_fds_full["km_fds"].round(0).astype(int)
            tab_fds_full["pct_fds"] = tab_fds_full["pct_fds"].astype(str) + "%"
            tab_fds_full = tab_fds_full.rename(columns={
                "motorista":"Motorista","km_fds":"Km no FDS",
                "dias_fds":"Dias com atividade","reg_fds":"Registros GPS",
                "pct_fds":"% do total de reg.",
            })
            st.dataframe(tab_fds_full, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro de fim de semana no período selecionado.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 7 —  HORÁRIOS + HEATMAPS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Quando Trabalham — Horários e Padrões")

    if not df_pt.empty and "hora" in df_pt.columns:
        col_h1, col_h2 = st.columns(2)

        with col_h1:
            hora_cnt = (df_pt.groupby("hora").size()
                             .reindex(range(24), fill_value=0).reset_index())
            hora_cnt.columns = ["hora","n"]
            pico = int(hora_cnt.loc[hora_cnt["n"].idxmax(), "hora"])
            fig_hora = go.Figure(go.Bar(
                x=hora_cnt["hora"], y=hora_cnt["n"],
                marker_color=[_C["acc1"] if h == pico else _C["eco135"] for h in hora_cnt["hora"]],
                marker_line_width=0,
                hovertemplate="<b>%{x}h</b>: %{y} registros<extra></extra>",
            ))
            fig_hora.update_layout(
                **_BASE,
                title=dict(text=f" Horários — pico às {pico}h",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=280,
                xaxis=dict(tickmode="array", tickvals=list(range(0,24,2)),
                           ticktext=[f"{h}h" for h in range(0,24,2)],
                           gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(gridcolor=_C["grid"], zeroline=False),
                bargap=0.1,
            )
            st.plotly_chart(fig_hora, use_container_width=True, config=_NO_INTERACT)

        with col_h2:
            # Heatmap: hora × dia_semana (toda frota)
            heatmap_data = (df_pt.groupby(["dia_semana","hora"]).size()
                                  .unstack(fill_value=0))
            z_mat = heatmap_data.reindex(range(7)).fillna(0).values.tolist()
            fig_hm = go.Figure(go.Heatmap(
                z=z_mat,
                x=[f"{h}h" for h in range(24)],
                y=dias_nome,
                colorscale=[[0,"#0D1B2A"],[0.3,"#1E4D3A"],[0.7,"#4A8A5A"],[1,"#7BBF6A"]],
                hovertemplate="<b>%{y} %{x}</b>: %{z} registros<extra></extra>",
                showscale=True,
                colorbar=dict(title="Registros", thickness=12,
                              tickfont=dict(color=_C["text"]),
                              title_font=dict(color=_C["text"])),
            ))
            fig_hm.update_layout(
                **_BASE,
                title=dict(text="Heatmap: hora x dia (intensidade = atividade)",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=280,
                xaxis=dict(tickfont=dict(size=9)),
                yaxis=dict(tickfont=dict(size=10)),
            )
            fig_hm.update_layout(margin=dict(l=60, r=12, t=36, b=12))
            st.plotly_chart(fig_hm, use_container_width=True, config=_NO_INTERACT)

        # Heatmap: motorista × hora do dia (quem trabalha quando)
        top_mots = (df_pt.groupby("motorista").size().sort_values(ascending=False)
                         .head(20).index.tolist())
        df_top = df_pt[df_pt["motorista"].isin(top_mots)]
        hm2 = (df_top.groupby(["motorista","hora"]).size()
                      .unstack(fill_value=0)
                      .reindex(columns=range(24), fill_value=0))
        fig_hm2 = go.Figure(go.Heatmap(
            z=hm2.values.tolist(),
            x=[f"{h}h" for h in range(24)],
            y=[m.split()[0] if m else m for m in hm2.index.tolist()],
            colorscale=[[0,"#0D1B2A"],[0.3,"#132840"],[0.7,"#1E6B9E"],[1,"#4CC9F0"]],
            hovertemplate="<b>%{y} %{x}</b>: %{z} registros<extra></extra>",
            showscale=True,
            colorbar=dict(title="Reg.", thickness=12,
                          tickfont=dict(color=_C["text"]),
                          title_font=dict(color=_C["text"])),
        ))
        fig_hm2.update_layout(
            **_BASE,
            title=dict(text="Quando cada motorista trabalha (top 20)",
                       font=dict(size=13, color=_C["text"]), x=0),
            height=max(380, len(top_mots) * 22),
            xaxis=dict(tickfont=dict(size=9)),
            yaxis=dict(tickfont=dict(size=9)),
        )
        fig_hm2.update_layout(margin=dict(l=120, r=12, t=36, b=12))
        st.plotly_chart(fig_hm2, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 7B — 🚗 HORÁRIO DE PARTIDA (Ignição + Movimento)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 🚗 Horário de Partida — Quando Ligam e Começam a Andar")
    st.caption(
        "Análise do primeiro registro diário de cada motorista: "
        "hora da primeira ignição (vel ≥ 0) e hora do primeiro movimento (vel > 3 km/h)."
    )

    if not df_pt.empty and dt_detectado and vel_detectada:
        df_start = df_pt.copy()
        df_start["dt_parsed"] = pd.to_datetime(df_start["dt"])
        df_start["hora_decimal"] = (df_start["dt_parsed"].dt.hour
                                     + df_start["dt_parsed"].dt.minute / 60)

        # Primeira atividade do dia (qualquer registro = carro ligou)
        first_on = (df_start.sort_values("dt_parsed")
                            .groupby(["motorista", "data"])
                            .first()
                            .reset_index())
        first_on["hora_lig"] = first_on["hora_decimal"]

        # Primeiro movimento do dia (vel > 3)
        df_mov = df_start[df_start["velocidade"] > 3]
        first_mov = (df_mov.sort_values("dt_parsed")
                           .groupby(["motorista", "data"])
                           .first()
                           .reset_index())
        first_mov["hora_mov"] = first_mov["hora_decimal"]

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            # Distribution of first ignition times (fleet-wide)
            fig_lig = go.Figure()
            if not first_on.empty:
                bins_lig = first_on["hora_lig"].dropna()
                fig_lig.add_trace(go.Histogram(
                    x=bins_lig,
                    nbinsx=24,
                    marker_color="#7BBF6A",
                    marker_line_width=0,
                    opacity=0.85,
                    hovertemplate="<b>%{x:.0f}h</b>: %{y} ocorrências<extra></extra>",
                ))
                media_lig = bins_lig.mean()
                fig_lig.add_vline(x=media_lig, line_dash="dash", line_color="#F7B731",
                                  annotation_text=f"Média: {int(media_lig)}:{int((media_lig%1)*60):02d}",
                                  annotation_font_color="#F7B731",
                                  annotation_font_size=11)
            fig_lig.update_layout(
                **_BASE,
                title=dict(text="🔑 Primeira Ignição do Dia (frota)",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=300,
                xaxis=dict(tickmode="array", tickvals=list(range(0,24,2)),
                           ticktext=[f"{h}h" for h in range(0,24,2)],
                           gridcolor=_C["grid"], zeroline=False, range=[4,22]),
                yaxis=dict(title="Dias", gridcolor=_C["grid"], zeroline=False),
                bargap=0.08,
            )
            st.plotly_chart(fig_lig, use_container_width=True, config=_NO_INTERACT)

        with col_s2:
            # Distribution of first movement times
            fig_mov = go.Figure()
            if not first_mov.empty:
                bins_mov = first_mov["hora_mov"].dropna()
                fig_mov.add_trace(go.Histogram(
                    x=bins_mov,
                    nbinsx=24,
                    marker_color="#4CC9F0",
                    marker_line_width=0,
                    opacity=0.85,
                    hovertemplate="<b>%{x:.0f}h</b>: %{y} ocorrências<extra></extra>",
                ))
                media_mov = bins_mov.mean()
                fig_mov.add_vline(x=media_mov, line_dash="dash", line_color="#F7B731",
                                  annotation_text=f"Média: {int(media_mov)}:{int((media_mov%1)*60):02d}",
                                  annotation_font_color="#F7B731",
                                  annotation_font_size=11)
            fig_mov.update_layout(
                **_BASE,
                title=dict(text="🏎️ Primeiro Movimento do Dia (vel > 3 km/h)",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=300,
                xaxis=dict(tickmode="array", tickvals=list(range(0,24,2)),
                           ticktext=[f"{h}h" for h in range(0,24,2)],
                           gridcolor=_C["grid"], zeroline=False, range=[4,22]),
                yaxis=dict(title="Dias", gridcolor=_C["grid"], zeroline=False),
                bargap=0.08,
            )
            st.plotly_chart(fig_mov, use_container_width=True, config=_NO_INTERACT)

        # ── Individual start time cards (scroll infinito) ──────────────────────
        st.markdown("### 👤 Padrão Individual de Partida")
        st.caption("Horário médio de ignição e movimento por motorista, com consistência (desvio-padrão).")

        _SEQ_S = ["#7BBF6A","#4CC9F0","#F7B731","#FF6B6B","#A29BFE","#FD79A8","#00CEC9"]

        # Aggregate per driver
        agg_lig = (first_on.groupby("motorista")["hora_lig"]
                           .agg(["mean","std","count"])
                           .rename(columns={"mean":"media_lig","std":"std_lig","count":"dias_lig"}))
        agg_mov = (first_mov.groupby("motorista")["hora_mov"]
                            .agg(["mean","std","count"])
                            .rename(columns={"mean":"media_mov","std":"std_mov","count":"dias_mov"}))
        agg_start = agg_lig.join(agg_mov, how="outer").fillna(0).sort_values("media_lig")

        for idx, (mot, row_s) in enumerate(agg_start.iterrows()):
            initials = "".join(w[0] for w in mot.split()[:2]).upper()
            cor_av = _SEQ_S[idx % len(_SEQ_S)]

            m_lig = row_s["media_lig"]
            s_lig = row_s["std_lig"]
            d_lig = int(row_s["dias_lig"])
            m_mov = row_s["media_mov"]
            s_mov = row_s["std_mov"]
            d_mov = int(row_s["dias_mov"])

            h_lig = f"{int(m_lig)}:{int((m_lig%1)*60):02d}" if d_lig > 0 else "—"
            h_mov = f"{int(m_mov)}:{int((m_mov%1)*60):02d}" if d_mov > 0 else "—"

            # Consistency label
            if s_lig <= 0.5:
                consist = "Muito consistente"
                consist_cor = "#7BBF6A"
            elif s_lig <= 1.0:
                consist = "Consistente"
                consist_cor = "#4CC9F0"
            elif s_lig <= 2.0:
                consist = "Variável"
                consist_cor = "#F7B731"
            else:
                consist = "Irregular"
                consist_cor = "#FF6B6B"

            # Delta between ignition and movement
            delta_min = int((m_mov - m_lig) * 60) if d_mov > 0 and d_lig > 0 else 0
            delta_txt = f"{delta_min} min" if delta_min > 0 else "—"

            card = f"""
            <div class="st-card">
              <div class="st-hdr">
                <div class="st-av" style="background:linear-gradient(135deg,{cor_av},{cor_av}88)">{initials}</div>
                <div style="flex:1;min-width:0">
                  <div class="st-name">{mot}</div>
                  <span style="font-size:.58rem;color:{consist_cor};background:rgba(255,255,255,.05);
                        padding:2px 8px;border-radius:8px">{consist}</span>
                </div>
              </div>
              <div class="st-grid">
                <div class="st-met"><div class="v" style="color:#7BBF6A">{h_lig}</div>
                  <div class="l">Liga carro</div></div>
                <div class="st-met"><div class="v" style="color:#4CC9F0">{h_mov}</div>
                  <div class="l">Começa andar</div></div>
                <div class="st-met"><div class="v" style="color:#F7B731">{delta_txt}</div>
                  <div class="l">Aquecimento</div></div>
                <div class="st-met"><div class="v" style="color:#A29BFE">{d_lig}</div>
                  <div class="l">Dias ativos</div></div>
              </div>
            </div>"""
            st.markdown(card, unsafe_allow_html=True)

    else:
        st.info("Carregue dados do período acima para ver a análise de horários de partida.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 8 —  ONDE ANDAM
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Onde Andam — Cidades e Regiões")

    if not df_pt.empty and "cidade" in df_pt.columns:
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            cnt_cid = (df_pt[df_pt["cidade"] != ""]
                       .groupby(["cidade","uf"]).size()
                       .reset_index(name="n")
                       .sort_values("n", ascending=False)
                       .head(15))
            if not cnt_cid.empty:
                cnt_cid["label"] = cnt_cid["cidade"] + " · " + cnt_cid["uf"]
                fig_cid = go.Figure(go.Bar(
                    x=cnt_cid["n"].iloc[::-1], y=cnt_cid["label"].iloc[::-1],
                    orientation="h",
                    marker=dict(
                        color=cnt_cid["n"].iloc[::-1],
                        colorscale=[[0,"#132840"],[0.5,"#1E6B9E"],[1,"#4CC9F0"]],
                        line_width=0,
                    ),
                    text=cnt_cid["n"].iloc[::-1], textposition="outside",
                    textfont=dict(size=10, color=_C["text"]),
                    hovertemplate="<b>%{y}</b>: %{x} registros<extra></extra>",
                ))
                fig_cid.update_layout(
                    **_BASE,
                    title=dict(text=" Top 15 cidades mais frequentes",
                               font=dict(size=13, color=_C["text"]), x=0),
                    height=380,
                    xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=9)),
                )
                st.plotly_chart(fig_cid, use_container_width=True, config=_NO_INTERACT)

        with col_c2:
            # Por estado
            cnt_uf = (df_pt[df_pt["uf"] != ""].groupby("uf").size()
                           .reset_index(name="n").sort_values("n", ascending=True))
            if not cnt_uf.empty:
                fig_uf = go.Figure(go.Bar(
                    x=cnt_uf["n"], y=cnt_uf["uf"], orientation="h",
                    marker=dict(
                        color=cnt_uf["n"],
                        colorscale=[[0,"#1a3a2a"],[0.5,"#4A8A5A"],[1,"#7BBF6A"]],
                        line_width=0,
                    ),
                    text=cnt_uf["n"], textposition="outside",
                    textfont=dict(size=11, color=_C["text"]),
                    hovertemplate="<b>%{y}</b>: %{x} registros<extra></extra>",
                ))
                fig_uf.update_layout(
                    **_BASE,
                    title=dict(text="️ Distribuição por Estado (UF)",
                               font=dict(size=13, color=_C["text"]), x=0),
                    height=300,
                    xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11)),
                )
                st.plotly_chart(fig_uf, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 9 — ️ TABELAS COMPLETAS
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Tabelas Detalhadas")

    tab_t1, tab_t2, tab_t3 = st.tabs(["Resumo por Motorista", "Rotas", "Dias com Excesso de Km"])

    with tab_t1:
        if not df_mot.empty:
            df_tab_mot = df_mot.sort_values("custo_total", ascending=False).copy()
            df_tab_mot["idle_pct"] = df_tab_mot["idle_pct"].apply(lambda x: f"{x:.1f}%")
            df_tab_mot["fds_pct"]  = df_tab_mot["fds_pct"].apply(lambda x: f"{x:.1f}%")
            df_tab_mot = df_tab_mot.rename(columns={
                "motorista":"Motorista","km_periodo":"Km total",
                "h_rastreio":"H rastreio","h_mov":"H movimento","h_idle":"H idle",
                "idle_pct":"Idle %","fds_pct":"FDS %",
                "n_fds":"Reg FDS","efficiency":"km/h mov",
                "custo_cb":"Custo CB (R$)","custo_idle":"Custo Idle (R$)","custo_total":"Custo Total (R$)",
            })
            st.dataframe(df_tab_mot, use_container_width=True, hide_index=True)

    with tab_t2:
        df_rotas = df_p[df_p["rota_resumo"] != ""].sort_values("km_periodo", ascending=False)[
            ["motorista","placa","km_periodo","rota_resumo","estados","cidades"]
        ].rename(columns={
            "motorista":"Motorista","placa":"Placa","km_periodo":"Km",
            "rota_resumo":"Rota (resumo)","estados":"UFs","cidades":"N° Cidades",
        })
        st.dataframe(df_rotas, use_container_width=True, hide_index=True)

    with tab_t3:
        if not df_pt.empty and "data" in df_pt.columns:
            _dfo4 = df_pt[df_pt["odometro"] > 0] if "odometro" in df_pt.columns else pd.DataFrame()
            if not _dfo4.empty:
                df_dv = (_dfo4.groupby(["motorista","data"])["odometro"]
                              .agg(["max","min"]).reset_index())
                df_dv["km_dia"] = (df_dv["max"] - df_dv["min"]).clip(lower=0, upper=1500)
            else:
                df_dv = df_pt.copy()
                df_dv["km_dia"] = df_dv["velocidade"] * (MINS_POR_PONTO / 60.0)
                df_dv = (df_dv.groupby(["motorista","data"])["km_dia"]
                              .sum().reset_index())
                df_dv["km_dia"] = df_dv["km_dia"].clip(lower=0, upper=1500)
            df_exc = df_dv[df_dv["km_dia"] > LIMIAR_KM_WA].sort_values("km_dia", ascending=False).copy()
            df_exc["status"] = df_exc["km_dia"].apply(
                lambda x: " ALARME >500km" if x > LIMIAR_KM_AL else " ATENÇÃO >300km"
            )
            df_exc = df_exc[["motorista","data","km_dia","status"]].rename(columns={
                "motorista":"Motorista","data":"Data","km_dia":"Km no dia","status":"Status",
            })
            st.dataframe(df_exc, use_container_width=True, hide_index=True)
        else:
            st.info("Dados diários insuficientes.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 10 —  VELOCIDADE: quem dirige rápido demais
    # ═══════════════════════════════════════════════════════════════════════════
    if not df_pt.empty and "velocidade" in df_pt.columns:
        st.markdown("---")
        st.markdown("##  Velocidade — Quem Corre Mais")
        st.caption("CTB Art. 61: limite 110 km/h pista dupla · 100 km/h pista simples · >120 km/h infração grave/gravíssima")

        df_vel = df_pt[df_pt["velocidade"] > 0]
        if not df_vel.empty:
            col_v1, col_v2 = st.columns(2)

            with col_v1:
                # Velocidade média por motorista
                vel_media = (df_vel.groupby("motorista")["velocidade"].mean()
                                    .reset_index().sort_values("velocidade", ascending=True))
                vel_media["velocidade"] = vel_media["velocidade"].round(1)
                cores_vel = [
                    _C["acc2"] if v > 110 else (_C["acc1"] if v > 90 else _C["eco135"])
                    for v in vel_media["velocidade"]
                ]
                fig_vel = go.Figure(go.Bar(
                    x=vel_media["velocidade"], y=vel_media["motorista"], orientation="h",
                    marker_color=cores_vel, marker_line_width=0,
                    text=[f"{v:.0f} km/h" for v in vel_media["velocidade"]],
                    textposition="outside",
                    textfont=dict(size=10, color=_C["text"]),
                    hovertemplate="<b>%{y}</b>: %{x:.1f} km/h média<extra></extra>",
                ))
                fig_vel.add_vline(x=110, line_dash="dash", line_color=_C["acc2"],
                                  annotation_text="110 km/h (pista dupla)",
                                  annotation_font_color=_C["acc2"])
                fig_vel.update_layout(
                    **_BASE,
                    title=dict(text="Velocidade Média por Motorista",
                               font=dict(size=13, color=_C["text"]), x=0),
                    height=max(400, len(vel_media) * 22),
                    xaxis=dict(gridcolor=_C["grid"], zeroline=False, ticksuffix=" km/h"),
                    yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
                )
                st.plotly_chart(fig_vel, use_container_width=True, config=_NO_INTERACT)

            with col_v2:
                # Registros acima de 110 km/h por motorista
                df_exc_vel = df_vel[df_vel["velocidade"] > 110]
                if not df_exc_vel.empty:
                    exc_cnt = (df_exc_vel.groupby("motorista")
                                         .agg(n=("velocidade","size"), vel_max=("velocidade","max"))
                                         .reset_index().sort_values("n", ascending=True))
                    exc_cnt["vel_max"] = exc_cnt["vel_max"].round(0).astype(int)
                    fig_exc = go.Figure(go.Bar(
                        x=exc_cnt["n"], y=exc_cnt["motorista"], orientation="h",
                        marker=dict(
                            color=exc_cnt["vel_max"],
                            colorscale=[[0,"#F7B731"],[0.5,"#FF6B6B"],[1,"#FF0000"]],
                            line_width=0,
                            colorbar=dict(title="Vel máx", thickness=10,
                                          tickfont=dict(color=_C["text"]),
                                          title_font=dict(color=_C["text"])),
                        ),
                        text=[f"{n}x · máx {m} km/h" for n, m in zip(exc_cnt["n"], exc_cnt["vel_max"])],
                        textposition="outside",
                        textfont=dict(size=9, color=_C["text"]),
                        hovertemplate="<b>%{y}</b>: %{x} reg >110 km/h<extra></extra>",
                    ))
                    fig_exc.update_layout(
                        **_BASE,
                        title=dict(text=f" Excesso >110 km/h — {len(df_exc_vel)} registros total",
                                   font=dict(size=13, color=_C["text"]), x=0),
                        height=max(320, len(exc_cnt) * 24),
                        xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                        yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
                    )
                    st.plotly_chart(fig_exc, use_container_width=True, config=_NO_INTERACT)
                else:
                    st.success("Nenhum registro acima de 110 km/h no período.")

            # Histograma de velocidade da frota
            fig_hist_vel = go.Figure(go.Histogram(
                x=df_vel["velocidade"],
                nbinsx=50,
                marker_color=_C["cerrado"],
                marker_line_width=0,
                hovertemplate="%{x:.0f} km/h: %{y} registros<extra></extra>",
            ))
            fig_hist_vel.add_vline(x=110, line_dash="dash", line_color=_C["acc2"],
                                   annotation_text="Limite 110", annotation_font_color=_C["acc2"])
            fig_hist_vel.add_vline(x=80, line_dash="dot", line_color=_C["eco135"],
                                   annotation_text="Econômico 80", annotation_font_color=_C["eco135"])
            fig_hist_vel.update_layout(
                **_BASE,
                title=dict(text=" Distribuição de velocidade (toda frota)",
                           font=dict(size=13, color=_C["text"]), x=0),
                height=260,
                xaxis=dict(title="km/h", gridcolor=_C["grid"], zeroline=False),
                yaxis=dict(title="Registros", gridcolor=_C["grid"], zeroline=False),
            )
            st.plotly_chart(fig_hist_vel, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 11 —  FORA DO HORÁRIO COMERCIAL (22h–6h)
    # ═══════════════════════════════════════════════════════════════════════════
    if not df_pt.empty and "hora" in df_pt.columns:
        df_noturno = df_pt[(df_pt["hora"] >= 22) | (df_pt["hora"] < 6)]
        if not df_noturno.empty:
            st.markdown("---")
            st.markdown("##  Atividade Noturna (22h–6h)")
            st.caption("Registros com ignição fora do horário comercial — possível uso não autorizado")

            col_n1, col_n2 = st.columns(2)

            with col_n1:
                not_mot = (df_noturno.groupby("motorista").size()
                                      .reset_index(name="reg_noturno")
                                      .sort_values("reg_noturno", ascending=True))
                tot_tot = df_pt.groupby("motorista").size()
                not_mot["pct_noturno"] = (not_mot["reg_noturno"].values /
                                          tot_tot.reindex(not_mot["motorista"]).fillna(1).values * 100).round(1)
                fig_not = go.Figure(go.Bar(
                    x=not_mot["reg_noturno"], y=not_mot["motorista"], orientation="h",
                    marker=dict(
                        color=not_mot["pct_noturno"],
                        colorscale=[[0,"#1a1a3a"],[0.5,"#4A3A8A"],[1,"#A29BFE"]],
                        line_width=0,
                        colorbar=dict(title="%", thickness=10,
                                      tickfont=dict(color=_C["text"]),
                                      title_font=dict(color=_C["text"])),
                    ),
                    text=[f"{n} reg · {p:.0f}%" for n, p in zip(not_mot["reg_noturno"], not_mot["pct_noturno"])],
                    textposition="outside",
                    textfont=dict(size=9, color=_C["text"]),
                    hovertemplate="<b>%{y}</b>: %{x} reg noturno<extra></extra>",
                ))
                fig_not.update_layout(
                    **_BASE,
                    title=dict(text=f" Ranking atividade noturna — {len(df_noturno)} reg total",
                               font=dict(size=13, color=_C["text"]), x=0),
                    height=max(320, len(not_mot) * 22),
                    xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                    yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=9)),
                )
                st.plotly_chart(fig_not, use_container_width=True, config=_NO_INTERACT)

            with col_n2:
                # Distribuição horária do uso noturno
                hora_not = (df_noturno.groupby("hora").size()
                                       .reindex(list(range(22,24))+list(range(0,6)), fill_value=0)
                                       .reset_index())
                hora_not.columns = ["hora","n"]
                fig_hnot = go.Figure(go.Bar(
                    x=[f"{h}h" for h in hora_not["hora"]], y=hora_not["n"],
                    marker_color="#A29BFE", marker_line_width=0,
                    hovertemplate="<b>%{x}</b>: %{y} reg<extra></extra>",
                ))
                fig_hnot.update_layout(
                    **_BASE,
                    title=dict(text=" Distribuição horária noturna",
                               font=dict(size=13, color=_C["text"]), x=0),
                    height=260,
                    xaxis=dict(gridcolor=_C["grid"], zeroline=False),
                    yaxis=dict(gridcolor=_C["grid"], zeroline=False),
                    bargap=0.15,
                )
                st.plotly_chart(fig_hnot, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 12 — ️ IDLE POR CIDADE: onde ficam parados com motor ligado
    # ═══════════════════════════════════════════════════════════════════════════
    if not df_pt.empty and "idle" in df_pt.columns and "cidade" in df_pt.columns:
        df_idle_cid = df_pt[(df_pt["idle"] == True) & (df_pt["cidade"] != "")]
        if not df_idle_cid.empty:
            st.markdown("---")
            st.markdown("## ️ Onde Ficam Parados com Motor Ligado")
            st.caption("Pontos GPS com ignição ON + velocidade ≤3 km/h — cada ponto ≈3 min de idle")

            col_ic1, col_ic2 = st.columns(2)

            with col_ic1:
                idle_cid = (df_idle_cid.groupby(["cidade","uf"]).size()
                                        .reset_index(name="idle_pontos")
                                        .sort_values("idle_pontos", ascending=False)
                                        .head(15))
                idle_cid["horas_idle"] = (idle_cid["idle_pontos"] * MINS_POR_PONTO / 60).round(1)
                idle_cid["custo"] = (idle_cid["horas_idle"] * CUSTO_IDLE_H).round(0).astype(int)
                idle_cid["label"] = idle_cid["cidade"] + " · " + idle_cid["uf"]
                fig_icid = go.Figure(go.Bar(
                    x=idle_cid["horas_idle"].iloc[::-1],
                    y=idle_cid["label"].iloc[::-1],
                    orientation="h",
                    marker=dict(
                        color=idle_cid["horas_idle"].iloc[::-1],
                        colorscale=[[0,"#1a1a2a"],[0.5,"#8B2020"],[1,"#FF6B6B"]],
                        line_width=0,
                    ),
                    text=[f"{h:.0f}h · R${c}" for h, c in zip(
                        idle_cid["horas_idle"].iloc[::-1], idle_cid["custo"].iloc[::-1])],
                    textposition="outside",
                    textfont=dict(size=9, color=_C["text"]),
                    hovertemplate="<b>%{y}</b>: %{x:.1f}h idle<extra></extra>",
                ))
                fig_icid.update_layout(
                    **_BASE,
                    title=dict(text="️ Top 15 cidades com mais idle (horas · custo est.)",
                               font=dict(size=12, color=_C["text"]), x=0),
                    height=380,
                    xaxis=dict(ticksuffix="h", gridcolor=_C["grid"], zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=9)),
                )
                st.plotly_chart(fig_icid, use_container_width=True, config=_NO_INTERACT)

            with col_ic2:
                # Idle por motorista × cidade (quem fica parado onde)
                idle_mc = (df_idle_cid.groupby(["motorista","cidade"]).size()
                                       .reset_index(name="n")
                                       .sort_values("n", ascending=False)
                                       .head(20))
                idle_mc["horas"] = (idle_mc["n"] * MINS_POR_PONTO / 60).round(1)
                idle_mc["label"] = idle_mc["motorista"].str.split().str[0] + " — " + idle_mc["cidade"]
                fig_imc = go.Figure(go.Bar(
                    x=idle_mc["horas"].iloc[::-1],
                    y=idle_mc["label"].iloc[::-1],
                    orientation="h",
                    marker=dict(
                        color=idle_mc["horas"].iloc[::-1],
                        colorscale=[[0,"#132840"],[0.5,"#8B4020"],[1,"#FF6B6B"]],
                        line_width=0,
                    ),
                    text=[f"{h:.1f}h" for h in idle_mc["horas"].iloc[::-1]],
                    textposition="outside",
                    textfont=dict(size=9, color=_C["text"]),
                    hovertemplate="<b>%{y}</b>: %{x:.1f}h idle<extra></extra>",
                ))
                fig_imc.update_layout(
                    **_BASE,
                    title=dict(text="️ Motorista × Cidade com mais idle (Top 20)",
                               font=dict(size=12, color=_C["text"]), x=0),
                    height=max(380, len(idle_mc) * 22),
                    xaxis=dict(ticksuffix="h", gridcolor=_C["grid"], zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=8)),
                )
                st.plotly_chart(fig_imc, use_container_width=True, config=_NO_INTERACT)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO 13 —  RANKING FINAL: TOP 10 MOTORISTAS PROBLEMÁTICOS
    # ═══════════════════════════════════════════════════════════════════════════
    if not df_mot.empty:
        st.markdown("---")
        st.markdown("##  Ranking Final — Motoristas que Precisam de Atenção")
        st.caption(
            "Score de risco composto: (idle% × 3) + (fds% × 2) + (1 se km/dia > 300) + (excesso velocidade). "
            "Quanto maior o score, mais urgente a intervenção."
        )

        # Compute risk score
        df_risk = df_mot.copy()
        # idle peso 3
        df_risk["risk_idle"] = df_risk["idle_pct"].clip(upper=100) * 3
        # fds peso 2
        df_risk["risk_fds"]  = df_risk["fds_pct"] * 2
        # km excesso
        if not df_pt.empty and "data" in df_pt.columns:
            _dfoR = df_pt[df_pt["odometro"] > 0] if "odometro" in df_pt.columns else pd.DataFrame()
            if not _dfoR.empty:
                _dailyR = (_dfoR.groupby(["motorista","data"])["odometro"]
                                 .agg(["max","min"]).reset_index())
                _dailyR["km_d"] = (_dailyR["max"] - _dailyR["min"]).clip(lower=0, upper=1500)
            else:
                # Fallback velocidade×tempo
                _dailyR = df_pt.copy()
                _dailyR["km_d"] = _dailyR["velocidade"] * (MINS_POR_PONTO / 60.0)
                _dailyR = (_dailyR.groupby(["motorista","data"])["km_d"]
                                   .sum().reset_index())
                _dailyR["km_d"] = _dailyR["km_d"].clip(lower=0, upper=1500)
            _avgR = _dailyR.groupby("motorista")["km_d"].mean().reset_index()
            _avgR.columns = ["motorista","km_dia_avg"]
            df_risk = df_risk.merge(_avgR, on="motorista", how="left")
            df_risk["km_dia_avg"] = df_risk["km_dia_avg"].fillna(0)
            df_risk["risk_km"] = (df_risk["km_dia_avg"] > LIMIAR_KM_WA).astype(float) * 50
        else:
            df_risk["km_dia_avg"] = 0.0
            df_risk["risk_km"]    = 0.0

        # velocidade excesso
        if not df_pt.empty and "velocidade" in df_pt.columns:
            _velR = (df_pt[df_pt["velocidade"] > 110]
                          .groupby("motorista").size()
                          .reset_index(name="n_excesso_vel"))
            df_risk = df_risk.merge(_velR, on="motorista", how="left")
            df_risk["n_excesso_vel"] = df_risk["n_excesso_vel"].fillna(0)
            df_risk["risk_vel"] = df_risk["n_excesso_vel"].clip(upper=50) * 2
        else:
            df_risk["n_excesso_vel"] = 0
            df_risk["risk_vel"]      = 0.0

        # noturno
        if not df_pt.empty and "hora" in df_pt.columns:
            _notR = (df_pt[(df_pt["hora"] >= 22) | (df_pt["hora"] < 6)]
                          .groupby("motorista").size()
                          .reset_index(name="n_noturno"))
            df_risk = df_risk.merge(_notR, on="motorista", how="left")
            df_risk["n_noturno"] = df_risk["n_noturno"].fillna(0)
            df_risk["risk_not"] = df_risk["n_noturno"].clip(upper=50)
        else:
            df_risk["n_noturno"] = 0
            df_risk["risk_not"]  = 0.0

        df_risk["risk_score"] = (df_risk["risk_idle"] + df_risk["risk_fds"]
                                 + df_risk["risk_km"] + df_risk["risk_vel"]
                                 + df_risk["risk_not"])
        df_risk = df_risk.sort_values("risk_score", ascending=False)

        # Top 10
        top10 = df_risk.head(10).copy()
        fig_risk = go.Figure(go.Bar(
            x=top10["risk_score"].iloc[::-1],
            y=top10["motorista"].iloc[::-1],
            orientation="h",
            marker=dict(
                color=top10["risk_score"].iloc[::-1],
                colorscale=[[0,"#1a3a2a"],[0.3,"#F7B731"],[0.6,"#FF6B6B"],[1,"#FF0000"]],
                line_width=0,
            ),
            hovertemplate="<b>%{y}</b>: score %{x:.0f}<extra></extra>",
        ))
        fig_risk.update_layout(
            **_BASE,
            title=dict(text=" Top 10 — Score de Risco Composto",
                       font=dict(size=14, color=_C["text"]), x=0),
            height=max(350, len(top10) * 30),
            xaxis=dict(title="Score de risco", gridcolor=_C["grid"], zeroline=False),
            yaxis=dict(gridcolor=_C["grid"], tickfont=dict(size=10)),
        )
        st.plotly_chart(fig_risk, use_container_width=True, config=_NO_INTERACT)

        # Detalhes dos top 10
        st.markdown("##### Detalhamento Top 10")
        tab_risk = top10[[
            "motorista","risk_score","km_periodo","idle_pct","h_idle",
            "fds_pct","n_fds","km_dia_avg","n_excesso_vel","n_noturno",
            "custo_total"
        ]].copy()
        tab_risk = tab_risk.rename(columns={
            "motorista":"Motorista","risk_score":"Score","km_periodo":"Km total",
            "idle_pct":"Idle %","h_idle":"H idle","fds_pct":"FDS %",
            "n_fds":"Reg FDS","km_dia_avg":"Km/dia médio",
            "n_excesso_vel":"Reg >110km/h","n_noturno":"Reg noturno",
            "custo_total":"Custo Est. (R$)",
        })
        tab_risk["Km/dia médio"] = tab_risk["Km/dia médio"].round(0)
        tab_risk["Score"] = tab_risk["Score"].round(0)
        st.dataframe(tab_risk, use_container_width=True, hide_index=True)

        # Cards dos 3 piores
        st.markdown("##### Os 3 que mais precisam de atenção:")
        worst3 = top10.head(3)
        cols_w = st.columns(3)
        for i, (_, row) in enumerate(worst3.iterrows()):
            with cols_w[i]:
                problemas = []
                if row["idle_pct"] > LIMIAR_IDLE_AL:
                    problemas.append(f" Idle {row['idle_pct']:.0f}%")
                if row["fds_pct"] > 0:
                    problemas.append(f" FDS {row['fds_pct']:.0f}%")
                if row.get("km_dia_avg", 0) > LIMIAR_KM_WA:
                    problemas.append(f" {row['km_dia_avg']:.0f} km/dia")
                if row.get("n_excesso_vel", 0) > 0:
                    problemas.append(f" {int(row['n_excesso_vel'])}× >110km/h")
                if row.get("n_noturno", 0) > 0:
                    problemas.append(f" {int(row['n_noturno'])} reg noturno")
                prob_html = "<br>".join(problemas) if problemas else "Sem infrações graves"
                medal = ["","",""][i]
                st.markdown(f"""
                <div style="background:rgba(255,70,70,0.10);border:1px solid #FF6B6B55;
                            border-radius:10px;padding:14px;min-height:180px">
                  <div style="font-size:1.1rem;font-weight:700;color:#FF6B6B">
                    {medal} {row['motorista']}</div>
                  <div style="font-size:.85rem;color:#F7B731;margin:4px 0">
                    Score: {row['risk_score']:.0f} · Custo: R$ {row['custo_total']:,.0f}</div>
                  <div style="font-size:.8rem;color:#C8D8A8;line-height:1.5">{prob_html}</div>
                </div>""", unsafe_allow_html=True)


# =============================================================================
# RENDER: FROTA NO DIA — todas as rotas + paradas
# =============================================================================

_CORES_FROTA = [
    "#4CC9F0","#7BBF6A","#F7B731","#FF6B6B","#A29BFE",
    "#FD79A8","#00CEC9","#FDCB6E","#55EFC4","#74B9FF",
    "#E17055","#81ECEC","#B2BEC3","#6C5CE7","#FAB1A0",
]


def _detectar_paradas(pontos, vel_thresh=3, min_min=4):
    """Detecta paradas: blocos de pontos com vel <= thresh por >= min_min minutos."""
    paradas = []
    i = 0
    while i < len(pontos):
        vel = pontos[i].get("velocidade", 0) or 0
        if vel <= vel_thresh:
            bloco = [pontos[i]]
            j = i + 1
            while j < len(pontos) and (pontos[j].get("velocidade", 0) or 0) <= vel_thresh:
                bloco.append(pontos[j])
                j += 1
            # Calcula duração
            try:
                t0 = datetime.fromisoformat(bloco[0].get("dt","").replace("Z",""))
                t1 = datetime.fromisoformat(bloco[-1].get("dt","").replace("Z",""))
                dur_min = max((t1 - t0).total_seconds() / 60, len(bloco) * 3)
            except Exception:
                dur_min = len(bloco) * 3
            if dur_min >= min_min:
                lt = bloco[0].get("pos_coordenada_latitude") or bloco[0].get("lat")
                ln = bloco[0].get("pos_coordenada_longitude") or bloco[0].get("lon")
                try:
                    lt, ln = float(lt), float(ln)
                    h_ini = bloco[0].get("dt","")[-8:-3] if bloco[0].get("dt","") else "—"
                    h_fim = bloco[-1].get("dt","")[-8:-3] if bloco[-1].get("dt","") else "—"
                except Exception:
                    lt = ln = None
                cidade = bloco[0].get("pos_end_cidade","") or bloco[0].get("cidade","")
                if lt and ln:
                    paradas.append({
                        "lat": lt, "lon": ln,
                        "dur_min": round(dur_min),
                        "cidade": cidade or "—",
                        "h_ini": h_ini, "h_fim": h_fim,
                    })
            i = j
        else:
            i += 1
    return paradas


def _render_frota_dia(itens):
    """Seleciona uma data e exibe rota de TODOS os veículos + paradas em scroll infinito."""
    st.markdown("### Frota no Dia — Todas as Rotas")

    c_date, c_btn, _ = st.columns([2, 1, 3])
    with c_date:
        dia_sel = st.date_input("Data:", value=date.today(), key="fd_data")
    with c_btn:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        carregar = st.button("Carregar Frota", key="fd_btn", use_container_width=True)

    if carregar:
        resultados = {}
        prog = st.progress(0, text="Buscando rotas...")
        try:
            sess, _ = _logos_login()
            for idx, it in enumerate(itens):
                prog.progress((idx + 1) / len(itens),
                              text=f"Buscando {it['motorista']} ({idx+1}/{len(itens)})...")
                try:
                    hist = _logos_get_rota(
                        sess, it["idvei"],
                        dia_sel.strftime("%Y-%m-%d 00:00"),
                        dia_sel.strftime("%Y-%m-%d 23:59"),
                    )
                except Exception:
                    hist = []
                if hist:
                    resultados[it["motorista"]] = {
                        "hist": hist, "cor": it["cor"],
                        "placa": it["placa"], "contrato": it.get("contrato",""),
                    }
        except Exception as e:
            st.error(f"Erro ao conectar: {e}")
            return
        finally:
            prog.empty()
        st.session_state["fd_resultados"] = resultados
        st.session_state["fd_data_carregada"] = str(dia_sel)

    resultados = st.session_state.get("fd_resultados", {})
    if not resultados:
        st.info("Selecione a data e clique em Carregar Frota.")
        return

    data_lbl = st.session_state.get("fd_data_carregada", str(dia_sel))
    st.caption(f"Dados de {data_lbl} — {len(resultados)} veiculos com historico")

    # ── Mapa unificado ────────────────────────────────────────────────────────
    mapa = folium.Map(location=[-18.5, -47.5], zoom_start=6,
                      tiles="CartoDB dark_matter", prefer_canvas=True)
    all_lats, all_lons = [], []

    for idx, (motorista, dados) in enumerate(resultados.items()):
        cor = dados["cor"] if dados["cor"] else _CORES_FROTA[idx % len(_CORES_FROTA)]
        coords = []
        for p in dados["hist"]:
            lt = p.get("pos_coordenada_latitude") or p.get("lat")
            ln = p.get("pos_coordenada_longitude") or p.get("lon")
            try:
                lt, ln = float(lt), float(ln)
                coords.append([lt, ln])
                all_lats.append(lt); all_lons.append(ln)
            except Exception:
                pass

        if len(coords) >= 2:
            km = _km_from_hist(dados["hist"])
            folium.PolyLine(
                coords, color=cor, weight=3, opacity=0.85,
                tooltip=folium.Tooltip(
                    f"<b style='color:{cor}'>{motorista}</b><br>"
                    f"{dados['placa']} — {km:,} km",
                    style="background:#0D1B2A;color:#E8EFD8;border:1px solid #566E3D;"
                          "font-family:Inter;font-size:12px;border-radius:6px;",
                ),
            ).add_to(mapa)
            # Marcador inicio (verde pequeno)
            folium.CircleMarker(
                coords[0], radius=5, color="#00FF88", fill=True,
                fill_color="#00FF88", fill_opacity=0.9,
                tooltip=f"Inicio: {motorista}",
            ).add_to(mapa)

        # Paradas: circulos azuis com hover
        paradas = _detectar_paradas(dados["hist"])
        for par in paradas:
            dur_txt = (f"{par['dur_min']//60}h {par['dur_min']%60}min"
                       if par["dur_min"] >= 60 else f"{par['dur_min']} min")
            folium.CircleMarker(
                [par["lat"], par["lon"]],
                radius=7 + min(par["dur_min"] // 20, 10),
                color="#4CC9F0", fill=True,
                fill_color="#4CC9F0", fill_opacity=0.55,
                weight=2,
                tooltip=folium.Tooltip(
                    f"<b>{motorista}</b><br>"
                    f"Parada: {dur_txt}<br>"
                    f"{par['h_ini']} - {par['h_fim']}<br>"
                    f"{par['cidade']}",
                    style="background:#0D1B2A;color:#E8EFD8;border:1px solid #4CC9F0;"
                          "font-family:Inter;font-size:12px;border-radius:6px;",
                ),
            ).add_to(mapa)

    if all_lats:
        mapa.fit_bounds([[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]])

    st_folium(mapa, width="100%", height=560, key="fd_mapa", returned_objects=[])

    # ── Scroll infinito: cards por motorista ─────────────────────────────────
    st.markdown("---")
    st.markdown("#### Detalhamento por Motorista")
    for idx, (motorista, dados) in enumerate(sorted(resultados.items())):
        cor = dados["cor"] if dados["cor"] else _CORES_FROTA[idx % len(_CORES_FROTA)]
        km   = _km_from_hist(dados["hist"])
        n_pts = len(dados["hist"])
        paradas = _detectar_paradas(dados["hist"])
        total_parada_min = sum(p["dur_min"] for p in paradas)

        st.markdown(
            f'<div style="border-left:3px solid {cor};padding:4px 0 4px 12px;'
            f'margin-bottom:4px">'
            f'<span style="font-weight:700;color:{cor};font-size:.95rem">{motorista}</span>'
            f' <span style="color:#8FA882;font-size:.78rem">{dados["placa"]} · {dados["contrato"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Km percorridos", f"{km:,} km")
        c2.metric("Posicoes GPS", n_pts)
        c3.metric("Paradas detectadas", len(paradas))
        c4.metric("Tempo parado", f"{total_parada_min} min" if total_parada_min < 60
                  else f"{total_parada_min//60}h{total_parada_min%60}min")

        if paradas:
            rows_html = "".join(
                f'<tr>'
                f'<td style="padding:4px 8px;color:#E8EFD8">{p["h_ini"]} - {p["h_fim"]}</td>'
                f'<td style="padding:4px 8px;color:#4CC9F0;font-weight:600">'
                f'{p["dur_min"]//60}h {p["dur_min"]%60}min' if p["dur_min"]>=60
                else f'<td style="padding:4px 8px;color:#4CC9F0;font-weight:600">{p["dur_min"]} min'
                f'</td>'
                f'<td style="padding:4px 8px;color:#8FA882">{p["cidade"]}</td>'
                f'</tr>'
                for p in paradas
            )
            st.markdown(
                f'<div style="overflow-x:auto;margin:6px 0 16px 0">'
                f'<table style="border-collapse:collapse;font-family:Inter,sans-serif;'
                f'font-size:.75rem;width:100%">'
                f'<thead><tr>'
                f'<th style="padding:4px 8px;color:#BFCF99;text-align:left;border-bottom:1px solid #566E3D">Horario</th>'
                f'<th style="padding:4px 8px;color:#BFCF99;text-align:left;border-bottom:1px solid #566E3D">Duracao</th>'
                f'<th style="padding:4px 8px;color:#BFCF99;text-align:left;border-bottom:1px solid #566E3D">Local</th>'
                f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Nenhuma parada significativa detectada neste dia.")
        st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:8px 0">', unsafe_allow_html=True)


# =============================================================================
# ABA RASTREAMENTO (fragment)
# =============================================================================

@st.fragment
def _aba_rastreamento():
    atu = st.session_state.get("logos_ultima_atualizacao")
    c1, c2 = st.columns([5, 1])
    with c1:
        if atu:
            n = len(st.session_state.get("logos_veiculos", []))
            st.caption(f" {n} veículos ECO · Atualizado: {atu}")
    with c2:
        atualizar = st.button(" Atualizar", key="logos_btn", use_container_width=True)

    if atualizar:
        with st.spinner("Conectando ao Logos..."):
            try:
                sess, idcli = _logos_login()
                veiculos = _logos_get_eco(sess, idcli)
                if not veiculos:
                    st.warning("Nenhum veículo ECO encontrado.")
                    return
                st.session_state["logos_veiculos"]           = veiculos
                st.session_state["logos_ultima_atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                st.session_state.pop("logos_rota", None)
                st.session_state.pop("logos_periodo_result", None)
            except Exception as e:
                st.error(f" {e}")
                return

    veiculos = st.session_state.get("logos_veiculos", [])
    if not veiculos:
        st.info("Clique em ** Atualizar** para buscar os veículos ECO do Logos Rastreamento.")
        return

    itens = [_parse_eco(v, i) for i, v in enumerate(veiculos)]

    tab_frota, tab_mapa_periodo, tab_stats, tab_rota = st.tabs([
        "Frota no Dia",
        "Mapa & Periodo",
        "Estatisticas",
        "Rota Individual",
    ])
    with tab_frota:
        _render_frota_dia(itens)
    with tab_mapa_periodo:
        st.markdown("### Posicao Atual da Frota")
        _render_mapa_posicao(itens, map_key="logos_mapa_pos", height=580)
        st.markdown("---")
        _render_analise_periodo(itens)
    with tab_stats:
        _render_estatisticas(itens)
    with tab_rota:
        _render_rota_individual(itens)
