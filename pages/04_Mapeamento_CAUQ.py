"""
=========================================================================
MAPEAMENTO DE PROJETOS CAUQ
=========================================================================
Mapa interativo com todos os projetos CAUQ Marshall mapeados por
localização, com filtros por ano, norma, procedência e mais.
Inclui validação por limites de especificação (DER/PR, DNIT, DEINFRA).
=========================================================================
"""
 
import streamlit as st
import sys
import os
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap
from streamlit_folium import st_folium
 
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
from styles import aplicar_estilos, CORES
from page_auth import proteger_pagina
from CAUQ.cauq_scanner import (
    escanear_projetos, anos_disponiveis, geocodificar_pendentes, SPEC_LIMITS,
)
from CAUQ.pedreiras_data import PEDREIRAS_INTEL
 
# ======================================================================================
# CONFIGURACAO DA PAGINA
# ======================================================================================
st.set_page_config(
    page_title="Mapeamento CAUQ | Afirma E-vias",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
aplicar_estilos()
proteger_pagina("Mapeamento de Projetos CAUQ")
 
# ======================================================================================
# CONSTANTES
# ======================================================================================
 
NORMA_CORES_FOLIUM = {
    "DEINFRA": "purple",
    "DER-PR":  "blue",
    "DER":     "blue",
    "DNIT":    "red",
    "OUTRO":   "gray",
}
 
NORMA_HEX = {
    "DEINFRA": "#7B2D8B",
    "DER-PR":  "#1565C0",
    "DER":     "#1565C0",
    "DNIT":    "#C62828",
    "OUTRO":   "#757575",
}
 
# ======================================================================================
# CACHE DE DADOS
# ======================================================================================
 
@st.cache_data(ttl=86400, show_spinner=False)
def carregar_dados(anos_selecionados: tuple[int, ...]) -> pd.DataFrame:
    """Cache persistente por 24h. Só recarrega ao clicar 'Atualizar Dados'."""
    return escanear_projetos(
        anos_filtro=list(anos_selecionados),
        com_geocode=True, com_geocode_api=False,
    )
 
 
# ======================================================================================
# UTILITARIOS
# ======================================================================================
 
def _fmt(val, decimais: int = 2, unidade: str = "") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    try:
        return f"{float(val):.{decimais}f}{' ' + unidade if unidade else ''}"
    except Exception:
        return str(val)
 
 
def _is_valid(val) -> bool:
    return val is not None and not (isinstance(val, float) and pd.isna(val))
 
 
def _check_spec(val, norma: str, campo: str) -> str | None:
    """Retorna cor de status: verde=OK, vermelho=fora, None=sem limite."""
    limits = SPEC_LIMITS.get(norma, {}).get(campo)
    if not limits or not _is_valid(val):
        return None
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    lo = limits.get("min")
    hi = limits.get("max")
    if lo is not None and v < lo:
        return "#E53935"
    if hi is not None and v > hi:
        return "#E53935"
    return "#43A047"
 
 
def _get_norma_fields(norma: str) -> list[str]:
    if norma == "DEINFRA":
        return ["abrasao_la", "indice_forma", "durabilidade_graudo",
                "durabilidade_miudo", "equivalente_areia", "lamelaridade", "adesividade"]
    elif norma == "DER-PR":
        return ["abrasao_la", "indice_forma", "durabilidade_graudo", "durabilidade_miudo",
                "equivalente_areia", "lamelaridade", "adesividade"]
    elif norma == "DNIT":
        return ["abrasao_la", "durabilidade_graudo", "durabilidade_miudo",
                "equivalente_areia", "adesividade"]
    return ["abrasao_la", "durabilidade_graudo", "durabilidade_miudo",
            "equivalente_areia", "adesividade"]
 
 
LABELS = {
    "abrasao_la":           "Abrasao LA (%)",
    "indice_forma":         "Indice de Forma",
    "durabilidade_graudo":  "Durabilidade Graudo (%)",
    "durabilidade_miudo":   "Durabilidade Miudo (%)",
    "equivalente_areia":    "Equivalente de Areia (%)",
    "lamelaridade":         "Lamelaridade (%)",
    "adesividade":          "Adesividade (%)",
    "teor":                 "Teor (%)",
    "volume_vazios":        "Volume de Vazios (%)",
    "rbv":                  "RBV (%)",
    "vam":                  "VAM (%)",
    "rice":                 "RICE (g/cm3)",
    "densidade_aparente":   "Dens. Aparente (g/cm3)",
    "dui":                  "DUI (%)",
    "filler_betume":        "Filler/Betume",
    "deformacao_permanente":"Def. Permanente (mm)",
}
 
 
def _popup_html(row: pd.Series) -> str:
    norma = str(row.get("norma", "OUTRO"))
    cor = NORMA_HEX.get(norma, "#757575")
    campos_agr = _get_norma_fields(norma)
 
    def _val_row(campo, val):
        spec_cor = _check_spec(val, norma, campo)
        dot = ""
        if spec_cor:
            dot = f"<span style='color:{spec_cor};font-size:14px;'>&#9679;</span> "
        return f"<tr><td>{LABELS.get(campo, campo)}</td><td>{dot}<b>{_fmt(val)}</b></td></tr>"
 
    agr_rows = ""
    for campo in campos_agr:
        val = row.get(campo)
        if _is_valid(val):
            agr_rows += _val_row(campo, val)
 
    marshall_rows = ""
    for campo in ["teor", "volume_vazios", "rbv", "vam", "rice",
                  "densidade_aparente", "dui", "filler_betume"]:
        val = row.get(campo)
        if _is_valid(val):
            marshall_rows += _val_row(campo, val)
 
    def_val = row.get("deformacao_permanente")
    def_row = ""
    if _is_valid(def_val):
        spec_cor = _check_spec(def_val, norma, "deformacao_permanente")
        dot = f"<span style='color:{spec_cor};'>&#9679;</span> " if spec_cor else ""
        def_row = (
            f"<tr><td colspan='2' style='padding-top:6px;'>"
            f"<b>Def. Permanente:</b> {dot}{_fmt(def_val)} mm</td></tr>"
        )
 
    html = f"""
    <div style="font-family:Arial,sans-serif;min-width:320px;max-width:400px;">
        <div style="background:{cor};color:#fff;padding:8px 12px;border-radius:6px 6px 0 0;margin-bottom:6px;">
            <b style="font-size:13px;">{row.get('num_projeto','—')}</b><br>
            <span style="font-size:11px;">{row.get('procedencia','—')}</span>
        </div>
        <table style="width:100%;font-size:11px;border-collapse:collapse;">
            <tr><td style="color:#555;">Localizacao</td>
                <td><b>{row.get('localizacao','—')}</b></td></tr>
            <tr><td style="color:#555;">Natureza</td>
                <td><b>{row.get('natureza_mineralogica','—')}</b></td></tr>
            <tr><td style="color:#555;">Ligante</td>
                <td><b>{row.get('ligante','—')}</b></td></tr>
            <tr><td style="color:#555;">Faixa</td>
                <td><b>{row.get('faixa_granulometrica','—')}</b></td></tr>
            <tr><td style="color:#555;">Norma</td>
                <td><b style="color:{cor};">{norma}</b></td></tr>
            <tr><td style="color:#555;">Ano</td>
                <td><b>{int(row.get('ano',0))}</b></td></tr>
        </table>
 
        <div style="margin-top:8px;padding:4px 0;border-top:1px solid #ddd;">
            <b style="font-size:11px;color:#333;">Caracteristicas do Agregado</b>
        </div>
        <table style="width:100%;font-size:11px;border-collapse:collapse;">
            {agr_rows if agr_rows else "<tr><td colspan='2' style='color:#aaa;'>Nao disponivel</td></tr>"}
        </table>
 
        <div style="margin-top:8px;padding:4px 0;border-top:1px solid #ddd;">
            <b style="font-size:11px;color:#333;">Parametros Marshall</b>
        </div>
        <table style="width:100%;font-size:11px;border-collapse:collapse;">
            {marshall_rows if marshall_rows else "<tr><td colspan='2' style='color:#aaa;'>Nao disponivel</td></tr>"}
        </table>
 
        {f'<table style="width:100%;font-size:11px;">{def_row}</table>' if def_row else ''}
        <div style="margin-top:4px;font-size:9px;color:#999;">
            <span style="color:#43A047;">&#9679;</span> Conforme
            <span style="color:#E53935;">&#9679;</span> Fora da especificacao
        </div>
    </div>
    """
    return html
 
 

def _stats_pedreira(df_proj, proc_list) -> dict | None:
    """Calcula estatísticas agregadas dos projetos CAUQ que usaram esta pedreira."""
    if df_proj is None or df_proj.empty or not proc_list:
        return None
    mask = pd.Series(False, index=df_proj.index)
    for p in proc_list:
        mask |= df_proj["procedencia"].astype(str).str.upper().str.contains(
            p.upper(), na=False, regex=False
        )
    sub = df_proj[mask]
    if sub.empty:
        return None
    st_dict: dict = {"n": len(sub)}
    st_dict["anos"] = sorted(sub["ano"].dropna().astype(int).unique().tolist())
    st_dict["normas"] = sorted(sub["norma"].dropna().astype(str).unique().tolist())
    st_dict["locs"] = sorted(sub["localizacao"].dropna().astype(str).unique().tolist())[:4]
    for campo in ("abrasao_la", "teor", "volume_vazios", "rbv", "equivalente_areia"):
        vals = sub[campo].dropna() if campo in sub.columns else pd.Series([], dtype=float)
        if not vals.empty:
            st_dict[campo] = {"mean": float(vals.mean()), "min": float(vals.min()), "max": float(vals.max())}
    return st_dict


def _filtrar_intel_pedreiras(
    intel_list: list,
    nat_sel: str | None = None,
    loc_sel: str | None = None,
    proc_sel: str | None = None,
) -> list:
    """
    Filtra PEDREIRAS_INTEL pelos filtros de Natureza, Localização e Procedência.
    Cada filtro é avaliado como substring parcial (case + accent insensitive).
    """
    import unicodedata as _ud

    def _n(s: str) -> str:
        s2 = _ud.normalize('NFKD', str(s))
        s2 = ''.join(c for c in s2 if not _ud.combining(c))
        return s2.upper().strip()

    result = []
    for ped in intel_list:
        # Filtro Natureza Mineralógica
        if nat_sel:
            if _n(nat_sel) not in _n(ped.get('natureza', '')):
                continue
        # Filtro Localização (por município no campo localizacao da pedreira)
        if loc_sel:
            if _n(loc_sel) not in _n(ped.get('localizacao', '')):
                continue
        # Filtro Procedência (verifica se proc_sel bate com alguma alias da pedreira)
        if proc_sel:
            proc_n = _n(proc_sel)
            matched = any(
                _n(p) in proc_n or proc_n in _n(p)
                for p in ped.get('procedencias', [])
            )
            if not matched:
                continue
        result.append(ped)
    return result


def _combinar_pedreiras_cauq(intel_list: list, df_proj) -> list:
    """
    Retorna PEDREIRAS_INTEL + pedreiras do banco CAUQ sem entrada no intel,
    posicionadas no centróide das localizações dos seus projetos (posição aproximada).
    """
    if df_proj is None or df_proj.empty:
        return intel_list

    # Conjunto de chaves já cobertas pelo intel
    covered: set[str] = set()
    for ped in intel_list:
        for p in ped.get("procedencias", []):
            covered.add(p.upper())

    def _norm(s: str) -> str:
        return " ".join(s.upper().split())
    def _ja_cobre(proc_str: str) -> bool:
        pu = _norm(proc_str)
        return any(_norm(c) in pu or pu in _norm(c) for c in covered)

    df_geo_p = df_proj[df_proj["lat"].notna() & df_proj["lon"].notna()].copy()
    extra: list = []
    for proc, grp in df_geo_p.groupby("procedencia"):
        if not proc or str(proc).upper() in ("", "-", "NAN", "0"):
            continue
        if _ja_cobre(str(proc)):
            continue
        lat_c = float(grp["lat"].mean())
        lon_c = float(grp["lon"].mean())
        loc_vals = grp["localizacao"].dropna()
        loc = str(loc_vals.mode().iloc[0]) if not loc_vals.empty else "—"
        nat_vals = grp["natureza_mineralogica"].dropna() if "natureza_mineralogica" in grp.columns else pd.Series([], dtype=str)
        nat = str(nat_vals.mode().iloc[0]) if not nat_vals.empty else "—"
        estado = loc.split("-")[-1].strip()[:2] if "-" in loc else "BR"
        extra.append({
            "nome": str(proc).upper(),
            "procedencias": [str(proc)],
            "localizacao": loc,
            "natureza": nat,
            "endereco": f"Posição aproximada — centróide de {len(grp)} projetos em {loc}",
            "lat": lat_c,
            "lon": lon_c,
            "estado": estado,
            "_aprox": True,
        })

    return intel_list + extra


def _criar_mapa(grupos_loc: dict, pedreiras: list | None = None, df_projetos=None) -> folium.Map:
    lats = [k[0] for k in grupos_loc] or [-25.4]
    lons = [k[1] for k in grupos_loc] or [-51.5]
    lat_c = sum(lats) / len(lats)
    lon_c = sum(lons) / len(lons)
 
    m = folium.Map(location=[lat_c, lon_c], zoom_start=7, tiles=None)
 
    folium.TileLayer("CartoDB positron",  name="Mapa Claro",    attr="CartoDB").add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="Mapa Escuro", attr="CartoDB").add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap",
                     attr="OpenStreetMap contributors").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satelite (Esri)",
    ).add_to(m)
 
    Fullscreen(position="topleft", title="Tela cheia",
               title_cancel="Sair de tela cheia").add_to(m)
    MiniMap(toggle_display=True, tile_layer="CartoDB positron").add_to(m)
 
    mc_grupos = {
        "DEINFRA": MarkerCluster(name="DEINFRA"),
        "DER-PR":  MarkerCluster(name="DER-PR"),
        "DNIT":    MarkerCluster(name="DNIT"),
        "OUTRO":   MarkerCluster(name="Outras"),
    }
    for g in mc_grupos.values():
        g.add_to(m)
 
    fg_multi = folium.FeatureGroup(name="Multiplos Projetos")
    fg_multi.add_to(m)
 
    for (lat, lon), rows in grupos_loc.items():
        if len(rows) == 1:
            row = rows[0]
            norma = str(row.get("norma", "OUTRO"))
            cor = NORMA_CORES_FOLIUM.get(norma, "gray")
            grupo = mc_grupos.get(norma, mc_grupos["OUTRO"])
 
            popup = folium.Popup(
                folium.IFrame(html=_popup_html(row), width=420, height=440),
                max_width=440,
            )
            tooltip = (
                f"<b>{row.get('num_projeto','—')}</b><br>"
                f"{row.get('procedencia','—')}<br>"
                f"{row.get('localizacao','—')}<br>"
                f"<span style='color:{NORMA_HEX.get(norma,'#555')}'>{norma}</span>"
            )
            folium.Marker(
                location=[lat, lon],
                popup=popup,
                tooltip=folium.Tooltip(tooltip, sticky=True),
                icon=folium.Icon(color=cor, icon="road", prefix="fa"),
            ).add_to(grupo)
 
        else:
            n = len(rows)
            loc_name = rows[0].get("localizacao", "—")
            proc_name = rows[0].get("procedencia", "—")
            normas_presentes = ", ".join(sorted({str(r.get("norma","—")) for r in rows}))
            folium.Marker(
                location=[lat, lon],
                tooltip=folium.Tooltip(
                    f"<b>{n} projetos - {proc_name}</b><br>"
                    f"{loc_name}<br>"
                    f"<span style='color:#BFCF99;'>Normas: {normas_presentes}</span><br>"
                    f"<i>Clique para comparar abaixo do mapa</i>",
                    sticky=True,
                ),
                icon=folium.DivIcon(
                    html=f"""
                    <div style="
                        background:#566E3D;color:#fff;border-radius:50%;
                        width:36px;height:36px;
                        display:flex;align-items:center;justify-content:center;
                        font-size:15px;font-weight:bold;
                        border:3px solid #fff;
                        box-shadow:0 2px 6px rgba(0,0,0,0.45);
                        cursor:pointer;
                    ">{n}</div>""",
                    icon_size=(36, 36),
                    icon_anchor=(18, 18),
                ),
            ).add_to(fg_multi)
 
    # ── Camada de Pedreiras (Intel Geoespacial + Dados CAUQ) ──────────
    if pedreiras:
        NATUREZA_COR = {
            "BASALTO":  "#E65100",
            "GRANITO":  "#6A1B9A",
            "GNAISSE":  "#1A237E",
            "DACITO":   "#558B2F",
            "DIABASIO": "#4E342E",
            "DIABÁSIO": "#4E342E",
            "AREIA":    "#F9A825",
            "RIOLITO":  "#00695C",
        }

        fg_pedreiras = folium.FeatureGroup(name="Pedreiras (Fontes)", show=True)
        fg_pedreiras.add_to(m)

        for ped in pedreiras:
            lat_p = ped.get("lat")
            lon_p = ped.get("lon")
            if lat_p is None or lon_p is None:
                continue

            nat      = str(ped.get("natureza", "")).upper().split("/")[0].strip()
            cor_ped  = NATUREZA_COR.get(nat, "#B71C1C")
            is_aprox = ped.get("_aprox", False)

            # Stats agregados do banco CAUQ
            st_d   = _stats_pedreira(df_projetos, ped.get("procedencias", []))
            n_proj = st_d["n"] if st_d else 0

            stats_rows = ""
            if st_d:
                anos_str   = ", ".join(str(a) for a in st_d.get("anos", []))
                normas_str = ", ".join(st_d.get("normas", []))
                locs_str   = " | ".join(st_d.get("locs", []))
                stats_rows += (
                    "<tr><td colspan='2' style='padding:5px 4px 2px;"
                    "border-top:1px solid #eee;color:#555;font-weight:600;'>"
                    f"Dados CAUQ ({n_proj} projetos)</td></tr>"
                    "<tr><td style='color:#777;padding:1px 4px;'>Anos</td>"
                    f"<td style='padding:1px 4px;'><b>{anos_str}</b></td></tr>"
                    "<tr><td style='color:#777;padding:1px 4px;'>Normas</td>"
                    f"<td style='padding:1px 4px;'><b>{normas_str}</b></td></tr>"
                )
                if locs_str:
                    stats_rows += (
                        "<tr><td style='color:#777;padding:1px 4px;'>Obras em</td>"
                        f"<td style='padding:1px 4px;font-size:10px;'>{locs_str}</td></tr>"
                    )
                for campo, label in [
                    ("abrasao_la",        "Abr. LA (%)"),
                    ("teor",              "Teor (%)"),
                    ("equivalente_areia", "Eq. Areia (%)"),
                    ("volume_vazios",     "Vol. Vazios (%)"),
                    ("rbv",               "RBV (%)"),
                ]:
                    sv = st_d.get(campo)
                    if sv:
                        stats_rows += (
                            "<tr><td style='color:#777;padding:1px 4px;'>"
                            f"{label}</td>"
                            "<td style='padding:1px 4px;'>"
                            f"<b>{sv['mean']:.1f}</b>"
                            "<span style='color:#aaa;font-size:10px;'>"
                            f" ({sv['min']:.1f}–{sv['max']:.1f})</span>"
                            "</td></tr>"
                        )

            loc_exata  = ped.get("loc_exata", False)
            aprox_note = (
                "<tr><td colspan='2' style='color:#F9A825;font-size:9px;padding:3px 4px;'>"
                "⚠ Posicao aproximada (centroide dos projetos)</td></tr>"
            ) if is_aprox else (
                "<tr><td colspan='2' style='color:#43A047;font-size:9px;padding:3px 4px;'>"
                "📍 Coordenada exata (verificada via KMZ/ANM)</td></tr>"
            ) if loc_exata else ""

            badge_tipo = "📍 GPS Exato" if loc_exata else ("⚡ INTEL" if not is_aprox else "~ CAUQ")
            sem_dados  = (
                "<tr><td colspan='2' style='color:#aaa;padding:5px 4px;"
                "border-top:1px solid #eee;'>Sem projetos no periodo filtrado</td></tr>"
            )

            popup_html = (
                f"<div style='font-family:Arial,sans-serif;min-width:280px;max-width:360px;'>"
                f"<div style='background:{cor_ped};color:#fff;padding:8px 12px;"
                f"border-radius:6px 6px 0 0;margin-bottom:6px;'>"
                f"<b style='font-size:13px;'>&#9935; {ped['nome']}</b><br>"
                f"<span style='font-size:10px;opacity:0.85;'>{ped['estado']}"
                f"&nbsp;&nbsp;{badge_tipo}</span></div>"
                f"<table style='width:100%;font-size:11px;border-collapse:collapse;'>"
                f"<tr><td style='color:#555;padding:2px 4px;'>Localizacao</td>"
                f"<td style='padding:2px 4px;'><b>{ped['localizacao']}</b></td></tr>"
                f"<tr><td style='color:#555;padding:2px 4px;'>Natureza</td>"
                f"<td style='padding:2px 4px;'><b style='color:{cor_ped};'>"
                f"{ped['natureza']}</b></td></tr>"
                f"<tr><td style='color:#555;padding:2px 4px;'>Ref.</td>"
                f"<td style='padding:2px 4px;font-size:10px;'>{ped['endereco']}</td></tr>"
                f"<tr><td style='color:#555;padding:2px 4px;'>Coord.</td>"
                f"<td style='padding:2px 4px;font-size:10px;'>{lat_p:.5f}, {lon_p:.5f}</td></tr>"
                f"{aprox_note}"
                f"{stats_rows if stats_rows else sem_dados}"
                f"</table></div>"
            )

            n_label = f" ({n_proj})" if n_proj > 0 else ""
            tooltip_txt = (
                f"<b>&#9935; {ped['nome']}</b>{n_label}<br>"
                f"{ped['natureza']} | {ped['localizacao']}"
            )
            border_col = "#00E676" if loc_exata else ("#fff" if not is_aprox else "#F9A825")
            opacity    = "1.0"  if not is_aprox else "0.75"
            icon_symbol = "📍" if loc_exata else "&#9935;"
            icon_html  = (
                f"<div style='background:{cor_ped};color:#fff;border-radius:4px;"
                f"width:26px;height:26px;display:flex;align-items:center;"
                f"justify-content:center;font-size:{'12' if loc_exata else '14'}px;font-weight:bold;"
                f"border:2px solid {border_col};"
                f"box-shadow:0 2px 6px rgba(0,0,0,0.5);"
                f"opacity:{opacity};'>{icon_symbol}</div>"
            )
            popup_h = 390 if st_d else 220
            folium.Marker(
                location=[lat_p, lon_p],
                popup=folium.Popup(
                    folium.IFrame(html=popup_html, width=390, height=popup_h),
                    max_width=410,
                ),
                tooltip=folium.Tooltip(tooltip_txt, sticky=True),
                icon=folium.DivIcon(
                    html=icon_html, icon_size=(26, 26), icon_anchor=(13, 13),
                ),
            ).add_to(fg_pedreiras)

    folium.LayerControl(collapsed=True).add_to(m)
    return m
 
 
def _mostrar_painel_comparacao(projetos: list):
    n = len(projetos)
    st.markdown(
        f"""
        <div style="background:#0a3d5f;border-radius:10px;padding:0.8rem 1.2rem;
                    border-left:4px solid #BFCF99;margin-bottom:1rem;">
            <b style="color:#BFCF99;font-size:1rem;">
                {n} projetos na mesma pedreira - Comparacao
            </b>
            <span style="color:#aaa;font-size:0.82rem;margin-left:1rem;">
                {projetos[0].get('procedencia','—')} | {projetos[0].get('localizacao','—')}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    max_cols = min(n, 4)
    cols = st.columns(max_cols)
    for i, row in enumerate(projetos[:max_cols]):
        norma = str(row.get("norma", "OUTRO"))
        cor = NORMA_HEX.get(norma, "#757575")
        campos_agr = _get_norma_fields(norma)
 
        with cols[i]:
            st.markdown(
                f"""
                <div style="background:#0a3d5f;border-radius:8px;padding:0.7rem 1rem;
                            border-top:4px solid {cor};margin-bottom:0.6rem;">
                    <b style="color:#fff;font-size:0.9rem;">{row.get('num_projeto','—')}</b><br>
                    <span style="color:#BFCF99;font-size:0.8rem;">{row.get('faixa_granulometrica','—')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
 
            def _lin(label, val, campo=None):
                spec = ""
                if campo:
                    c = _check_spec(val if _is_valid(val) else None, norma, campo)
                    if c:
                        spec = f"<span style='color:{c};'>&#9679;</span> "
                v_str = _fmt(val) if _is_valid(val) else str(val)
                cols[i].markdown(
                    f"<div style='font-size:0.82rem;padding:1px 0;'>"
                    f"<span style='color:#aaa;'>{label}:</span> {spec}<b>{v_str}</b></div>",
                    unsafe_allow_html=True,
                )
 
            _lin("Ligante",  row.get("ligante", "—"))
            _lin("Norma",    norma)
            _lin("Ano",      int(row.get("ano", 0)))
 
            st.markdown(
                "<div style='margin:6px 0 2px;font-size:0.8rem;color:#BFCF99;'>"
                "<b>Agregado</b></div>",
                unsafe_allow_html=True,
            )
            for campo in campos_agr:
                val = row.get(campo)
                if _is_valid(val):
                    _lin(LABELS[campo], val, campo)
 
            st.markdown(
                "<div style='margin:6px 0 2px;font-size:0.8rem;color:#BFCF99;'>"
                "<b>Marshall</b></div>",
                unsafe_allow_html=True,
            )
            for campo in ["teor", "volume_vazios", "rbv", "vam", "rice",
                          "densidade_aparente", "dui", "filler_betume"]:
                val = row.get(campo)
                if _is_valid(val):
                    _lin(LABELS[campo], val, campo)
 
            def_val = row.get("deformacao_permanente")
            if _is_valid(def_val):
                _lin("Def. Perm.", f"{_fmt(def_val)} mm", "deformacao_permanente")
 
    if n > max_cols:
        st.caption(f"Mostrando {max_cols} de {n} projetos")
 
 
# ======================================================================================
# LAYOUT PRINCIPAL
# ======================================================================================
 
def main():
    # ── Header ──────────────────────────────────────────────────────────────────────
    col_logo, col_titulo = st.columns([0.8, 4])
    with col_logo:
        try:
            logo_path = r"G:\.shortcut-targets-by-id\1JbWwLDR6PaShh0-_xJZLFAvEXQKn65V1\008 - Comercial\010 - Marketing\00 - Identidade Visual Afirma Evias\Manual Completo\Identidade Visual\Logotipo e Variações\Símbolo e Selos\PNG\Selo C Ass\Selo C Ass_4.png"
            st.image(logo_path, width=160)
        except Exception:
            st.markdown(
                f'<div style="background:{CORES["secundario"]};padding:1rem;'
                f'border-radius:8px;text-align:center;">'
                f'<h3 style="color:white;margin:0;">AFIRMA E-VIAS</h3></div>',
                unsafe_allow_html=True,
            )
 
    with col_titulo:
        st.markdown(
            f"""
            <div style="padding-left:1rem;">
                <h1 style="margin:0;font-size:2.2rem !important;">Mapeamento de Projetos CAUQ</h1>
                <p style="color:{CORES['destaque']};font-size:1.1rem;margin-top:0.4rem;">
                    Distribuicao Geografica | Projetos Marshall | Ensaios de Agregados
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
 
    st.markdown("---")
 
    # ── Sidebar ─────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""<style>
        div[data-testid="stButton"][key="back_to_menu_cauq"] > button {
            background: transparent !important;
            border: 1px solid rgba(191,207,153,0.3) !important;
            color: rgba(191,207,153,0.7) !important;
            font-size: 0.78rem !important;
            padding: 0.2rem 0.6rem !important;
            border-radius: 6px !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stButton"][key="back_to_menu_cauq"] > button:hover {
            background: rgba(191,207,153,0.1) !important;
            color: #BFCF99 !important;
        }
        </style>""", unsafe_allow_html=True)
 
        if st.button("< Menu Principal", key="back_to_menu_cauq"):
            st.switch_page("app.py")
 
        try:
            st.image("Imagens/AE - Logo Hor Principal_2.png", use_container_width=True)
        except Exception:
            st.markdown(
                f'<div style="background:{CORES["secundario"]};padding:1rem;'
                f'border-radius:8px;text-align:center;">'
                f'<h3 style="color:white;margin:0;">AFIRMA E-VIAS</h3></div>',
                unsafe_allow_html=True,
            )
 
        st.markdown("---")
 
        # ── Carregar dados ──────────────────────────────────────────────────────────
        anos_disp = anos_disponiveis()
        if not anos_disp:
            st.error("Nenhum diretorio encontrado.")
            st.stop()
 
        if st.button("Atualizar Dados", key="forcar_atualizacao_cauq",
                     help="Re-escaneia arquivos modificados e atualiza o cache"):
            carregar_dados.clear()
            st.rerun()
 
        with st.spinner("Carregando projetos..."):
            df_raw = carregar_dados(tuple(sorted(anos_disp)))
 
        if df_raw.empty:
            st.error("Nenhum projeto encontrado.")
            st.stop()
 
        df = df_raw.copy()
 
        def _opts(series) -> list[str]:
            vals = series.dropna().astype(str).unique().tolist()
            return sorted([v for v in vals if v and v not in ("-", "", "nan", "0")])
 
        # ════════════════════════════════════════════════════════════════════════════
        # FILTROS EM UM ÚNICO EXPANDER (layout padronizado)
        # ════════════════════════════════════════════════════════════════════════════

        with st.expander("▸ Filtros", expanded=True):

            ano_opts = ["Todos"] + [str(a) for a in anos_disp]
            ano_sel  = st.selectbox("Ano:", ano_opts, key="f_ano")
            if ano_sel != "Todos":
                df = df[df["ano"] == int(ano_sel)]

            norma_opts = ["Todas"] + _opts(df["norma"])
            norma_sel  = st.selectbox("Norma:", norma_opts, key="f_norma")
            if norma_sel != "Todas":
                df = df[df["norma"].astype(str) == norma_sel]

            nat_opts = ["Todas"] + _opts(df["natureza_mineralogica"])
            nat_sel  = st.selectbox("Natureza Mineral.:", nat_opts, key="f_nat")
            if nat_sel != "Todas":
                df = df[df["natureza_mineralogica"].astype(str) == nat_sel]

            lig_opts = ["Todos"] + _opts(df["ligante"])
            lig_sel  = st.selectbox("Ligante:", lig_opts, key="f_lig")
            if lig_sel != "Todos":
                df = df[df["ligante"].astype(str) == lig_sel]

            faixa_opts = ["Todas"] + _opts(df["faixa_granulometrica"])
            faixa_sel  = st.selectbox("Faixa Granulomet.:", faixa_opts, key="f_faixa")
            if faixa_sel != "Todas":
                df = df[df["faixa_granulometrica"].astype(str) == faixa_sel]

            loc_opts = ["Todas"] + _opts(df["localizacao"])
            loc_sel  = st.selectbox("Localização:", loc_opts, key="f_loc")
            if loc_sel != "Todas":
                df = df[df["localizacao"].astype(str) == loc_sel]

            proc_opts = ["Todas"] + _opts(df["procedencia"])
            proc_sel  = st.selectbox("Procedência:", proc_opts, key="f_proc")
            if proc_sel != "Todas":
                df = df[df["procedencia"].astype(str) == proc_sel]

            st.divider()
            st.checkbox(
                "⛏ Pedreiras (Fontes)",
                value=True,
                key="show_pedreiras",
                help="Exibe no mapa as pedreiras e minerações fornecedoras de agregados",
            )

        mostrar_projetos = True
        # (modo_vis alias: sempre todos visíveis — toggle pedreiras via checkbox)

        

        # ── Resumo e acoes ──────────────────────────────────────────────────────────
        st.markdown("---")
        total = len(df_raw)
        filtrado = len(df)
        sem_geo = int(df["lat"].isna().sum())
        st.caption(f"Projetos: {filtrado} / {total}")
        if sem_geo > 0:
            st.caption(f"  {sem_geo} sem coordenadas")
            if st.button(f"Geocodificar ({sem_geo})", key="btn_geocode",
                         help="Consulta OpenStreetMap para obter coordenadas pendentes"):
                with st.spinner(f"Geocodificando {sem_geo} localizacoes..."):
                    df_atualizado, n_novos = geocodificar_pendentes(df_raw.copy())
                if n_novos > 0:
                    carregar_dados.clear()
                    st.success(f"{n_novos} localizacao(oes) geocodificada(s)!")
                    st.rerun()
                else:
                    st.warning("Nenhuma localizacao nova encontrada.")
        st.markdown("---")
        st.caption("2026 Afirma E-vias")
 
    # ── KPIs ─────────────────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)
 
    def _kpi(col, label, value, cor="#BFCF99"):
        col.markdown(
            f"""
            <div style="background:#0a3d5f;border-radius:10px;padding:0.7rem 0.8rem;
                        border-left:4px solid {cor};text-align:center;">
                <div style="color:{cor};font-size:0.7rem;text-transform:uppercase;
                            letter-spacing:0.05em;">{label}</div>
                <div style="color:#fff;font-size:1.3rem;font-weight:700;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
 
    df_geo = df[df["lat"].notna() & df["lon"].notna()] if mostrar_projetos else df.iloc[0:0]
 
    _kpi(col1, "Projetos", len(df))
    _kpi(col2, "Mapeados", len(df_geo))
    _kpi(col3, "DER-PR", len(df[df["norma"] == "DER-PR"]), "#1565C0")
    _kpi(col4, "DNIT", len(df[df["norma"] == "DNIT"]), "#C62828")
    _kpi(col5, "DEINFRA", len(df[df["norma"] == "DEINFRA"]), "#7B2D8B")
    # Pedreiras unicas no banco + inteligencia geoespacial
    n_ped = df["procedencia"].dropna().nunique()
    n_intel = len(PEDREIRAS_INTEL)
    _kpi(col6, f"Pedreiras", f"{n_ped} / {n_intel}", "#E65100")
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    # ── Legenda ──────────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="display:flex;gap:1.5rem;margin-bottom:0.8rem;flex-wrap:wrap;align-items:center;">
            <span style="color:{NORMA_HEX['DER-PR']};font-weight:600;">&#9679; DER-PR</span>
            <span style="color:{NORMA_HEX['DNIT']};font-weight:600;">&#9679; DNIT</span>
            <span style="color:{NORMA_HEX['DEINFRA']};font-weight:600;">&#9679; DEINFRA-SC</span>
            <span style="color:{NORMA_HEX['OUTRO']};font-weight:600;">&#9679; Outras</span>
            <span style="color:#888;font-size:0.85rem;">&nbsp;| Badge verde = multiplos projetos</span>
            <span style="background:#E65100;color:#fff;border-radius:4px;padding:2px 7px;
                         font-size:0.8rem;font-weight:600;">&#9935; Pedreiras</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ── Agrupar por localizacao ──────────────────────────────────────────────────────
    grupos_loc: dict = {}
    for _, row in df_geo.iterrows():
        key = (round(float(row["lat"]), 4), round(float(row["lon"]), 4))
        grupos_loc.setdefault(key, []).append(row)
 
    multi_locs = {k: v for k, v in grupos_loc.items() if len(v) > 1}
 
    # ── Mapa ─────────────────────────────────────────────────────────────────────────
    if df_geo.empty and mostrar_projetos:
        st.warning(
            "Nenhum projeto com localizacao geocodificada nos filtros selecionados."
        )
    else:
        with st.spinner("Renderizando mapa..."):
            _intel = _filtrar_intel_pedreiras(
                PEDREIRAS_INTEL,
                nat_sel  if nat_sel  != "Todas" else None,
                loc_sel  if loc_sel  != "Todas" else None,
                proc_sel if proc_sel != "Todas" else None,
            )
            pedreiras_layer = (
                _combinar_pedreiras_cauq(_intel, df)
                if st.session_state.get("show_pedreiras", True)
                else None
            )
            mapa = _criar_mapa(grupos_loc, pedreiras=pedreiras_layer, df_projetos=df)
            map_data = st_folium(
                mapa, width="100%", height=560,
                returned_objects=["last_object_clicked"], key="cauq_map",
            )
 
        clk = (map_data or {}).get("last_object_clicked")
        if clk:
            lat_c = float(clk.get("lat", 0))
            lon_c = float(clk.get("lng", 0))
            matched = None
            for (la, lo), rows in multi_locs.items():
                if abs(la - lat_c) < 0.002 and abs(lo - lon_c) < 0.002:
                    matched = rows
                    break
            if matched:
                st.session_state["cauq_compare"] = matched
            else:
                st.session_state.pop("cauq_compare", None)
 
    if st.session_state.get("cauq_compare"):
        _mostrar_painel_comparacao(st.session_state["cauq_compare"])
 
    st.markdown("---")
 
    # ── Abas de Analise ──────────────────────────────────────────────────────────────
    tab_tabela, tab_stats, tab_specs, tab_mineralogia = st.tabs([
        "Tabela de Dados", "Estatisticas", "Conformidade", "Mineralogia",
    ])
 
    # ── Tabela de Dados ───────────────────────────────────────────────────────────
    with tab_tabela:
        colunas_exibir = {
            "ano":                   "Ano",
            "num_projeto":           "N Projeto",
            "procedencia":           "Procedencia",
            "localizacao":           "Localizacao",
            "natureza_mineralogica": "Natureza",
            "faixa_granulometrica":  "Faixa",
            "norma":                 "Norma",
            "ligante":               "Ligante",
            "teor":                  "Teor (%)",
            "volume_vazios":         "Vol. Vazios (%)",
            "rbv":                   "RBV (%)",
            "vam":                   "VAM (%)",
            "rice":                  "RICE",
            "densidade_aparente":    "Dens. Ap.",
            "dui":                   "DUI (%)",
            "filler_betume":         "Filler/Bet.",
            "abrasao_la":            "Abr. LA (%)",
            "durabilidade_graudo":   "Dur. Gr. (%)",
            "durabilidade_miudo":    "Dur. Mi. (%)",
            "equivalente_areia":     "Eq. Areia (%)",
            "lamelaridade":          "Lamelar. (%)",
            "adesividade":           "Adesiv. (%)",
            "deformacao_permanente": "Def. Perm. (mm)",
        }
 
        cols_existentes = [c for c in colunas_exibir if c in df.columns]
        df_tab = df[cols_existentes].rename(columns=colunas_exibir)
 
        float_cols = [
            v for k, v in colunas_exibir.items()
            if k in df.columns and df[k].dtype in ["float64", "float32"]
        ]
        for col in float_cols:
            if col in df_tab.columns:
                df_tab[col] = df_tab[col].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "—"
                )
 
        st.dataframe(df_tab, use_container_width=True, hide_index=True)
 
        csv = df_tab.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
        st.download_button(
            label="Baixar CSV",
            data=csv.encode("utf-8-sig"),
            file_name=f"cauq_projetos_{'_'.join(str(a) for a in sorted(df['ano'].unique()))}.csv",
            mime="text/csv",
        )
 
    # ── Estatisticas ──────────────────────────────────────────────────────────────
    with tab_stats:
        st.markdown(
            f"<h4 style='color:{CORES['destaque']};'>Estatisticas por Norma</h4>",
            unsafe_allow_html=True,
        )
        metricas_num = [
            "teor", "volume_vazios", "rbv", "vam", "abrasao_la",
            "equivalente_areia", "durabilidade_graudo", "durabilidade_miudo",
            "lamelaridade", "dui", "rice", "densidade_aparente",
            "deformacao_permanente",
        ]
        metricas_existentes = [m for m in metricas_num if m in df.columns]
 
        if metricas_existentes:
            df_stat = df.groupby("norma")[metricas_existentes].agg(["mean", "min", "max", "count"])
            df_stat.columns = [f"{LABELS.get(m, m)} ({stat})"
                               for m, stat in df_stat.columns]
            st.dataframe(df_stat.round(2), use_container_width=True)
 
        st.markdown(
            f"<h4 style='color:{CORES['destaque']};margin-top:1rem;'>Evolucao por Ano</h4>",
            unsafe_allow_html=True,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Projetos por Ano**")
            df_ano = df.groupby("ano").size().reset_index(name="Projetos")
            st.bar_chart(df_ano.set_index("ano"), height=250)
        with col_b:
            st.markdown("**Norma por Ano**")
            ct = pd.crosstab(df["ano"], df["norma"])
            st.bar_chart(ct, height=250)
 
    # ── Conformidade com Especificacoes ──────────────────────────────────────────
    with tab_specs:
        st.markdown(
            f"<h4 style='color:{CORES['destaque']};'>Conformidade com Especificacoes</h4>"
            f"<p style='color:#aaa;font-size:0.85rem;'>"
            f"DER/PR ES-PA 15/23 e 21/23 | DNIT 031/2006-ES | DEINFRA-SC ES-P 05/16"
            f"</p>",
            unsafe_allow_html=True,
        )
 
        campos_check = [
            "abrasao_la", "equivalente_areia", "durabilidade_graudo",
            "durabilidade_miudo", "volume_vazios", "rbv", "vam", "dui",
        ]
 
        for norma_key in ["DER-PR", "DNIT", "DEINFRA"]:
            df_norma = df[df["norma"] == norma_key]
            if df_norma.empty:
                continue
 
            cor = NORMA_HEX.get(norma_key, "#757575")
            specs = SPEC_LIMITS.get(norma_key, {})
 
            st.markdown(
                f"<div style='margin-top:1rem;padding:0.5rem 1rem;background:#0a3d5f;"
                f"border-left:4px solid {cor};border-radius:6px;'>"
                f"<b style='color:{cor};font-size:1rem;'>{norma_key}</b>"
                f" <span style='color:#aaa;'>({len(df_norma)} projetos)</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
 
            rows_html = []
            for campo in campos_check:
                if campo not in specs:
                    continue
                lim = specs[campo]
                vals = df_norma[campo].dropna()
                if vals.empty:
                    continue
 
                lo = lim.get("min", "—")
                hi = lim.get("max", "—")
                lim_str = f"{lo} - {hi}" if lo != "—" and hi != "—" else (
                    f"min {lo}" if hi == "—" else f"max {hi}"
                )
 
                n_ok = 0
                for v in vals:
                    ok = True
                    if isinstance(lo, (int, float)) and v < lo:
                        ok = False
                    if isinstance(hi, (int, float)) and v > hi:
                        ok = False
                    if ok:
                        n_ok += 1
 
                n_total = len(vals)
                pct = 100 * n_ok / n_total if n_total > 0 else 0
                cor_pct = "#43A047" if pct >= 90 else "#FFA726" if pct >= 70 else "#E53935"
 
                rows_html.append(
                    f"<tr>"
                    f"<td style='padding:4px 8px;'>{LABELS.get(campo, campo)}</td>"
                    f"<td style='padding:4px 8px;text-align:center;'>{lim_str}</td>"
                    f"<td style='padding:4px 8px;text-align:center;'>{vals.mean():.1f}</td>"
                    f"<td style='padding:4px 8px;text-align:center;'>{vals.min():.1f} - {vals.max():.1f}</td>"
                    f"<td style='padding:4px 8px;text-align:center;color:{cor_pct};font-weight:bold;'>"
                    f"{n_ok}/{n_total} ({pct:.0f}%)</td>"
                    f"</tr>"
                )
 
            if rows_html:
                st.markdown(
                    f"""
                    <table style="width:100%;font-size:0.85rem;border-collapse:collapse;margin-top:0.5rem;">
                        <thead>
                            <tr style="background:#0d4a6f;color:#BFCF99;">
                                <th style="padding:6px 8px;text-align:left;">Parametro</th>
                                <th style="padding:6px 8px;text-align:center;">Limite</th>
                                <th style="padding:6px 8px;text-align:center;">Media</th>
                                <th style="padding:6px 8px;text-align:center;">Min - Max</th>
                                <th style="padding:6px 8px;text-align:center;">Conforme</th>
                            </tr>
                        </thead>
                        <tbody>{''.join(rows_html)}</tbody>
                    </table>
                    """,
                    unsafe_allow_html=True,
                )
 
    # ── Mineralogia ──────────────────────────────────────────────────────────────
    with tab_mineralogia:
        st.markdown(
            f"<h4 style='color:{CORES['destaque']};'>Distribuicao Mineralogica</h4>",
            unsafe_allow_html=True,
        )
 
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("**Natureza Mineralogica**")
            nat_counts = df["natureza_mineralogica"].dropna()
            nat_counts = nat_counts[~nat_counts.isin(["", "-", "nan", "0"])]
            if not nat_counts.empty:
                nat_df = nat_counts.value_counts().reset_index()
                nat_df.columns = ["Natureza", "Projetos"]
                st.bar_chart(nat_df.set_index("Natureza"), height=300)
 
        with col_m2:
            st.markdown("**Ligante Asfaltico**")
            lig_counts = df["ligante"].dropna()
            lig_counts = lig_counts[~lig_counts.isin(["", "-", "nan", "0"])]
            if not lig_counts.empty:
                lig_df = lig_counts.value_counts().reset_index()
                lig_df.columns = ["Ligante", "Projetos"]
                st.bar_chart(lig_df.set_index("Ligante"), height=300)
 
        st.markdown(
            f"<h4 style='color:{CORES['destaque']};margin-top:1rem;'>"
            f"Propriedades por Natureza Mineralogica</h4>",
            unsafe_allow_html=True,
        )
        props_por_nat = ["abrasao_la", "durabilidade_graudo", "equivalente_areia"]
        nat_valid = df[df["natureza_mineralogica"].notna() &
                       ~df["natureza_mineralogica"].isin(["", "-", "nan", "0"])]
        if not nat_valid.empty:
            for prop in props_por_nat:
                if prop in nat_valid.columns:
                    vals = nat_valid.groupby("natureza_mineralogica")[prop].agg(
                        ["mean", "min", "max", "count"]
                    ).round(2)
                    vals = vals[vals["count"] >= 2]
                    if not vals.empty:
                        vals.columns = ["Media", "Min", "Max", "N"]
                        st.markdown(f"**{LABELS.get(prop, prop)}**")
                        st.dataframe(vals, use_container_width=True)
 
 
main()