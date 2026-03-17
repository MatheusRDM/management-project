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
import json
import requests as _requests
import unicodedata
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap
from streamlit_folium import st_folium
 
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
from styles import aplicar_estilos, CORES
from page_auth import proteger_pagina
from CAUQ.cauq_scanner import (
    escanear_projetos, anos_disponiveis, geocodificar_pendentes, SPEC_LIMITS,
    carregar_parquet_cache,
)
from CAUQ.pedreiras_data import PEDREIRAS_INTEL
from cloud_config import get_logo_path
 
# ======================================================================================
# CONFIGURACAO DA PAGINA
# ======================================================================================
st.set_page_config(
    page_title="Mapeamento CAUQ | Afirma E-vias",
    page_icon="Imagens/logo_icon.png",
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
    """Cache persistente por 24h com fallback Parquet instantaneo."""
    # Tenta Parquet primeiro (instantaneo, <100ms)
    df_pq = carregar_parquet_cache()
    if df_pq is not None and not df_pq.empty:
        if anos_selecionados:
            df_pq = df_pq[df_pq["ano"].isin(anos_selecionados)]
        if not df_pq.empty:
            return df_pq
    # Fallback: scan completo (lento, ~15-60s)
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
    import unicodedata as _ud
    def _n(s):
        s2 = _ud.normalize("NFKD", str(s).upper())
        s2 = "".join(c for c in s2 if not _ud.combining(c))
        return " ".join(s2.split())
    if df_proj is None or df_proj.empty or not proc_list:
        return None
    proc_norm = df_proj["procedencia"].astype(str).apply(_n)
    mask = pd.Series(False, index=df_proj.index)
    for p in proc_list:
        mask |= proc_norm.str.contains(_n(p), na=False, regex=False)
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


def _dedup_pedreiras(lista: list, dist_km: float = 8.0) -> list:
    """
    Une marcadores de pedreira com nome similar E proximidade geografica.
    Mantém coords do que tem loc_exata=True. Mescla procedencias.
    """
    from math import radians, cos, sin, asin, sqrt
    import unicodedata as _ud

    def _haver(lat1, lon1, lat2, lon2):
        R = 6371.0
        lat1, lon1, lat2, lon2 = (radians(x) for x in (lat1, lon1, lat2, lon2))
        dlat = lat2 - lat1; dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        return 2 * R * asin(min(1.0, sqrt(a)))

    def _norm_nome(n):
        n2 = _ud.normalize("NFKD", str(n).upper())
        n2 = "".join(c for c in n2 if not _ud.combining(c))
        for rem in ("PEDREIRA ", "PEDREIRAS ", "MINERACAO ", "BRITAGEM ", "USINA "):
            n2 = n2.replace(rem, "")
        return n2.split(" - ")[0].strip()

    def _similares(n1, n2):
        k1 = _norm_nome(n1); k2 = _norm_nome(n2)
        if not k1 or not k2 or len(k1) < 4: return False
        return k1 == k2 or k1 in k2 or k2 in k1

    merged = []; used = set()
    for i, p1 in enumerate(lista):
        if i in used: continue
        if p1.get("lat") is None:
            merged.append(p1); used.add(i); continue
        group = [p1]; used.add(i)
        for j, p2 in enumerate(lista):
            if j <= i or j in used or p2.get("lat") is None: continue
            d = _haver(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
            if d <= dist_km and _similares(p1["nome"], p2["nome"]):
                group.append(p2); used.add(j)
        if len(group) == 1:
            merged.append(p1)
        else:
            base = max(group, key=lambda x: (int(x.get("loc_exata", False)), len(x.get("procedencias", []))))
            combined = dict(base)
            seen = set(); all_procs = []
            for g in group:
                for proc in g.get("procedencias", []):
                    k = proc.strip().upper()
                    if k not in seen: seen.add(k); all_procs.append(proc)
            combined["procedencias"] = all_procs
            combined["nome"] = sorted([g["nome"] for g in group], key=len)[0]
            if any(g.get("loc_exata") for g in group):
                combined["loc_exata"] = True; combined["_aprox"] = False
            merged.append(combined)
    return merged


def _combinar_pedreiras_cauq(intel_list: list, df_proj) -> list:
    """
    Retorna PEDREIRAS_INTEL + pedreiras do banco CAUQ sem entrada no intel,
    posicionadas no centroide das localizacoes. Aplica dedup por nome+proximidade.
    """
    if df_proj is None or df_proj.empty:
        return intel_list

    # Conjunto de chaves já cobertas pelo intel
    import unicodedata as _ud2
    def _norm(s: str) -> str:
        s2 = _ud2.normalize("NFKD", str(s).upper())
        s2 = "".join(c for c in s2 if not _ud2.combining(c))
        return " ".join(s2.split())
    covered: set[str] = set()
    for ped in intel_list:
        for p in ped.get("procedencias", []):
            covered.add(_norm(p))

    def _ja_cobre(proc_str: str) -> bool:
        pu = _norm(proc_str)
        return any(c in pu or pu in c for c in covered)

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

    return _dedup_pedreiras(intel_list + extra)


def _criar_mapa(grupos_loc: dict, pedreiras: list | None = None, df_projetos=None,
                geojson_contorno: dict | None = None, nome_contorno: str = "",
                center_override: tuple | None = None) -> folium.Map:
    import unicodedata as _ud
    def _n(s):
        s2 = _ud.normalize("NFKD", str(s).upper())
        s2 = "".join(c for c in s2 if not _ud.combining(c))
        return " ".join(s2.split())

    # --- Centro do mapa ---
    all_lats = [k[0] for k in grupos_loc] or [-25.4]
    all_lons = [k[1] for k in grupos_loc] or [-51.5]
    if pedreiras:
        for _p in pedreiras:
            if _p.get("lat") is not None:
                all_lats.append(_p["lat"])
                all_lons.append(_p["lon"])
    lat_c = sum(all_lats) / len(all_lats)
    lon_c = sum(all_lons) / len(all_lons)
    zoom_ini = 7

    # Se município selecionado, centraliza e dá zoom nele
    if center_override:
        lat_c, lon_c, zoom_ini = center_override

    m = folium.Map(location=[lat_c, lon_c], zoom_start=zoom_ini, tiles=None)

    folium.TileLayer("CartoDB positron",   name="Mapa Claro",    attr="CartoDB").add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="Mapa Escuro",  attr="CartoDB").add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap",
                     attr="OpenStreetMap contributors").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satelite (Esri)",
    ).add_to(m)

    Fullscreen(position="topleft", title="Tela cheia",
               title_cancel="Sair de tela cheia").add_to(m)
    MiniMap(toggle_display=True, tile_layer="CartoDB positron").add_to(m)

    # ── Contorno do município selecionado (Google-style) ──────────────────
    if geojson_contorno:
        _adicionar_contorno_municipio(m, geojson_contorno, nome_contorno)

    # ══════════════════════════════════════════════════════════════════════
    # MARCADORES UNIFICADOS POR PEDREIRA
    # Cada pedreira = 1 marcador. Contém dados da pedreira + stats CAUQ.
    # ══════════════════════════════════════════════════════════════════════
    NATUREZA_COR = {
        "BASALTO":  "#E65100", "GRANITO":  "#6A1B9A", "GNAISSE":  "#1A237E",
        "DACITO":   "#558B2F", "DIABASIO": "#4E342E", "DIABÁSIO": "#4E342E",
        "AREIA":    "#F9A825", "RIOLITO":  "#00695C", "MIGMATITO": "#5D4037",
    }

    fg_pedreiras = folium.FeatureGroup(name="Pedreiras", show=True)
    fg_pedreiras.add_to(m)

    # Offset co-located quarries so they don't perfectly stack
    _used_locs: dict[str, int] = {}

    if pedreiras:
        for ped in pedreiras:
            lat_p = ped.get("lat")
            lon_p = ped.get("lon")
            if lat_p is None or lon_p is None:
                continue
            loc_key = f"{round(lat_p, 3)},{round(lon_p, 3)}"
            _used_locs[loc_key] = _used_locs.get(loc_key, 0) + 1
            if _used_locs[loc_key] > 1:
                offset = _used_locs[loc_key] * 0.003
                lat_p = lat_p + offset
                lon_p = lon_p + offset * 0.7

            nat      = str(ped.get("natureza", "")).upper().split("/")[0].strip()
            cor_ped  = NATUREZA_COR.get(nat, "#B71C1C")
            is_aprox = ped.get("_aprox", False)
            loc_exata = ped.get("loc_exata", False)

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
                f"<div style='font-family:Arial,sans-serif;min-width:220px;max-width:340px;width:max-content;'>"
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

            # ── Icone: CIRCULO = tem projetos, QUADRADO = sem projetos ──
            border_col = "#00E676" if loc_exata else ("#fff" if not is_aprox else "#F9A825")
            opacity    = "1.0" if not is_aprox else "0.75"

            if n_proj > 0:
                # CÍRCULO com número de projetos dentro
                icon_html = (
                    f"<div style='background:{cor_ped};color:#fff;border-radius:50%;"
                    f"width:32px;height:32px;display:flex;align-items:center;"
                    f"justify-content:center;font-size:13px;font-weight:bold;"
                    f"border:2.5px solid {border_col};"
                    f"box-shadow:0 2px 6px rgba(0,0,0,0.5);"
                    f"opacity:{opacity};'>{n_proj}</div>"
                )
                icon_size = (32, 32)
                icon_anchor = (16, 16)
            else:
                # QUADRADO pequeno sem projetos
                icon_html = (
                    f"<div style='background:{cor_ped};color:#fff;border-radius:3px;"
                    f"width:18px;height:18px;display:flex;align-items:center;"
                    f"justify-content:center;font-size:9px;font-weight:bold;"
                    f"border:2px solid {border_col};"
                    f"box-shadow:0 2px 4px rgba(0,0,0,0.4);"
                    f"opacity:{opacity};'>⛏</div>"
                )
                icon_size = (18, 18)
                icon_anchor = (9, 9)

            n_label = f" ({n_proj})" if n_proj > 0 else ""
            tooltip_txt = (
                f"<b>&#9935; {ped['nome']}</b>{n_label}<br>"
                f"{ped['natureza']} | {ped['localizacao']}"
            )
            if n_proj > 0:
                tooltip_txt += f"<br><i style='color:#BFCF99;'>Clique para ver {n_proj} projetos</i>"

            popup_h = 390 if st_d else 220
            folium.Marker(
                location=[lat_p, lon_p],
                popup=folium.Popup(
                    folium.IFrame(html=popup_html, width=360, height=popup_h),
                    max_width=380,
                ),
                tooltip=folium.Tooltip(tooltip_txt, sticky=True),
                icon=folium.DivIcon(
                    html=icon_html, icon_size=icon_size, icon_anchor=icon_anchor,
                ),
            ).add_to(fg_pedreiras)

    folium.LayerControl(collapsed=True).add_to(m)
    return m
 
 
@st.fragment
def _mostrar_painel_comparacao(projetos: list):
    """Fragment: re-renderiza somente este painel, sem rerun da pagina inteira."""
    import plotly.graph_objects as go
    import random

    n        = len(projetos)
    nome_ped = projetos[0].get("procedencia", "—")
    loc_ped  = projetos[0].get("localizacao",  "—")

    st.markdown(
        f"""
        <div style="background:#0a3d5f;border-radius:10px;padding:0.8rem 1.2rem;
                    border-left:4px solid #BFCF99;margin-bottom:1rem;">
            <b style="color:#BFCF99;font-size:1rem;">
                {n} projetos na mesma pedreira &mdash; Comparacao
            </b>
            <span style="color:#aaa;font-size:0.82rem;margin-left:1rem;">
                {nome_ped} | {loc_ped}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_fichas, tab_grafico = st.tabs([
        f"📋 Fichas ({n} projetos)",
        "📊 Analise Estatistica",
    ])

    # ── ABA FICHAS: grid responsivo (até 4 cols desktop, 2 tablet, 1 mobile) ───
    with tab_fichas:
        COLS_ROW = min(4, max(1, n))
        for row_start in range(0, n, COLS_ROW):
            batch = projetos[row_start : row_start + COLS_ROW]
            cols = st.columns(len(batch))
            for i, row in enumerate(batch):
                norma      = str(row.get("norma", "OUTRO"))
                cor        = NORMA_HEX.get(norma, "#757575")
                campos_agr = _get_norma_fields(norma)

                with cols[i]:
                    st.markdown(
                        f"""
                        <div style="background:#0a3d5f;border-radius:8px;padding:0.7rem 1rem;
                                    border-top:4px solid {cor};margin-bottom:0.6rem;">
                            <b style="color:#fff;font-size:0.9rem;">{row.get("num_projeto","—")}</b><br>
                            <span style="color:#BFCF99;font-size:0.8rem;">{row.get("faixa_granulometrica","—")}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    def _lin(label, val, campo=None, _c=cols[i]):
                        spec = ""
                        if campo:
                            cc = _check_spec(val if _is_valid(val) else None, norma, campo)
                            if cc:
                                spec = f"<span style='color:{cc};'>&#9679;</span> "
                        v_str = _fmt(val) if _is_valid(val) else str(val)
                        _c.markdown(
                            f"<div style='font-size:0.82rem;padding:1px 0;'>"
                            f"<span style='color:#aaa;'>{label}:</span> {spec}<b>{v_str}</b></div>",
                            unsafe_allow_html=True,
                        )

                    _lin("Ligante", row.get("ligante", "—"))
                    _lin("Norma",   norma)
                    _lin("Ano",     int(row.get("ano", 0)))

                    cols[i].markdown(
                        "<div style='margin:6px 0 2px;font-size:0.8rem;color:#BFCF99;'>"
                        "<b>Agregado</b></div>",
                        unsafe_allow_html=True,
                    )
                    for campo in campos_agr:
                        val = row.get(campo)
                        if _is_valid(val):
                            _lin(LABELS[campo], val, campo)

                    cols[i].markdown(
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

            st.markdown(
                "<hr style='border-color:#1a3d5f;margin:0.5rem 0;'>",
                unsafe_allow_html=True,
            )

    # ── ABA GRAFICO: analise estatistica por parametro e ano ────────────────────
    with tab_grafico:
        CAMPOS_GRAF = {
            "deformacao_permanente": "Def. Permanente (mm)",
            "abrasao_la":            "Abrasao LA (%)",
            "volume_vazios":         "Volume de Vazios (%)",
            "rbv":                   "RBV (%)",
            "teor":                  "Teor de Ligante (%)",
            "vam":                   "VAM (%)",
            "rice":                  "RICE (g/cm3)",
            "densidade_aparente":    "Dens. Aparente (g/cm3)",
            "equivalente_areia":     "Equivalente de Areia (%)",
            "durabilidade_graudo":   "Durabilidade Graudo (%)",
            "durabilidade_miudo":    "Durabilidade Miudo (%)",
            "lamelaridade":          "Lamelaridade (%)",
            "adesividade":           "Adesividade (%)",
            "dui":                   "DUI (%)",
            "filler_betume":         "Filler/Betume",
        }

        # Campos que têm pelo menos um valor
        campos_com_dado = [
            k for k in CAMPOS_GRAF
            if any(_is_valid(p.get(k)) for p in projetos)
        ]

        if not campos_com_dado:
            st.info("Nenhum dado numerico disponivel para os projetos desta pedreira.")
        else:
            col_sel, col_norm = st.columns([3, 2])
            with col_sel:
                campo_sel = st.selectbox(
                    "Parametro",
                    options=campos_com_dado,
                    format_func=lambda x: CAMPOS_GRAF[x],
                    key="ped_campo_sel",
                )
            with col_norm:
                normas_disp = sorted(set(str(p.get("norma", "OUTRO")) for p in projetos))
                norma_filtro = st.multiselect(
                    "Especificação:",
                    options=normas_disp,
                    default=normas_disp,
                    key="ped_norma_sel",
                )

            # DataFrame para o gráfico
            df_g = pd.DataFrame([
                {
                    "ano":     int(p.get("ano", 0)),
                    "valor":   p.get(campo_sel),
                    "norma":   str(p.get("norma", "OUTRO")),
                    "projeto": p.get("num_projeto", "—"),
                    "faixa":   p.get("faixa_granulometrica", "—"),
                }
                for p in projetos
                if norma_filtro and str(p.get("norma", "OUTRO")) in norma_filtro
            ])
            df_g = df_g[df_g["valor"].apply(lambda v: _is_valid(v))].copy()
            df_g["valor"] = df_g["valor"].astype(float)

            if df_g.empty:
                st.warning("Nenhum dado disponivel para este parametro/norma.")
            else:
                lbl      = CAMPOS_GRAF[campo_sel]
                anos_ord = sorted(df_g["ano"].unique())

                # Resumo por ano
                resumo = (
                    df_g.groupby("ano")["valor"]
                    .agg(["mean", "min", "max", "count"])
                    .reset_index()
                    .rename(columns={"mean": "Media", "min": "Min",
                                     "max": "Max", "count": "N"})
                )

                NORMA_COLORS_GRAF = {
                    "DEINFRA": "#7B2D8B",
                    "DER-PR":  "#1565C0",
                    "DER":     "#1565C0",
                    "DNIT":    "#C62828",
                    "OUTRO":   "#757575",
                }

                fig = go.Figure()

                # Box por ano (fundo)
                for ano in anos_ord:
                    sub_ano = df_g[df_g["ano"] == ano]
                    fig.add_trace(go.Box(
                        y=sub_ano["valor"],
                        name=str(ano),
                        boxpoints=False,
                        marker_color="#1E88E5",
                        line_color="#1E88E5",
                        fillcolor="rgba(30,136,229,0.12)",
                        showlegend=False,
                        hoverinfo="skip",
                        width=0.4,
                    ))

                # Formato de casas decimais por campo
                _dec = 3 if campo_sel in ("rice", "densidade_aparente") else 2
                _yfmt = f"%.{_dec}f"

                # Scatter pontos por norma
                for nr in sorted(df_g["norma"].unique()):
                    sub_nr = df_g[df_g["norma"] == nr]
                    # Labels de valor nos pontos
                    text_labels = [f"{v:.{_dec}f}" for v in sub_nr["valor"]]
                    hover_texts = sub_nr["projeto"] + "<br>" + sub_nr["faixa"]
                    fig.add_trace(go.Scatter(
                        x=[str(a) for a in sub_nr["ano"]],
                        y=sub_nr["valor"],
                        mode="markers+text",
                        name=nr,
                        marker=dict(
                            color=NORMA_COLORS_GRAF.get(nr, "#757575"),
                            size=11,
                            line=dict(width=1.5, color="white"),
                            opacity=0.92,
                        ),
                        text=text_labels,
                        textposition="top center",
                        textfont=dict(size=10, color="#ddd"),
                        customdata=hover_texts,
                        hovertemplate=(
                            "<b>%{customdata}</b><br>"
                            + lbl + f": <b>%{{y:.{_dec}f}}</b>"
                            "<extra>" + nr + "</extra>"
                        ),
                    ))

                # Linha de média por ano
                fig.add_trace(go.Scatter(
                    x=[str(a) for a in resumo["ano"]],
                    y=resumo["Media"],
                    mode="lines+markers",
                    name="Média",
                    line=dict(color="#BFCF99", width=2, dash="dot"),
                    marker=dict(symbol="diamond", size=9, color="#BFCF99"),
                    hovertemplate=f"Média %{{x}}: <b>%{{y:.{_dec}f}}</b><extra></extra>",
                ))

                # Linhas de limite de especificação
                spec_drawn = set()
                for nr in norma_filtro:
                    if nr in spec_drawn:
                        continue
                    lim = SPEC_LIMITS.get(nr, {}).get(campo_sel, {})
                    if lim.get("min") is not None:
                        fig.add_hline(
                            y=lim["min"], line_dash="dash",
                            line_color="#E53935", line_width=1.5,
                            annotation_text=f"Min {nr}: {lim['min']}",
                            annotation_font_color="#E53935",
                            annotation_position="bottom right",
                        )
                    if lim.get("max") is not None:
                        fig.add_hline(
                            y=lim["max"], line_dash="dash",
                            line_color="#E53935", line_width=1.5,
                            annotation_text=f"Max {nr}: {lim['max']}",
                            annotation_font_color="#E53935",
                            annotation_position="top right",
                        )
                    if lim:
                        spec_drawn.add(nr)

                fig.update_layout(
                    title=dict(
                        text=f"<b>{lbl}</b>  —  {nome_ped}  ({n} projetos)",
                        font=dict(color="#BFCF99", size=15),
                    ),
                    paper_bgcolor="#0a1929",
                    plot_bgcolor="#0d2137",
                    font=dict(color="#ccc", size=12),
                    xaxis=dict(
                        title="Ano",
                        tickfont=dict(color="#aaa"),
                        gridcolor="#1a3d5f",
                        categoryorder="array",
                        categoryarray=[str(a) for a in anos_ord],
                    ),
                    yaxis=dict(
                        title=lbl,
                        tickfont=dict(color="#aaa"),
                        gridcolor="#1a3d5f",
                        zeroline=False,
                    ),
                    legend=dict(
                        bgcolor="rgba(10,25,41,0.85)",
                        bordercolor="#1a3d5f",
                        borderwidth=1,
                        font=dict(color="#ccc"),
                        itemclick="toggle",
                        itemdoubleclick="toggleothers",
                    ),
                    hovermode="x unified",
                    hoverlabel=dict(
                        bgcolor="#0a1929",
                        bordercolor="#1a3d5f",
                        font=dict(color="#fff", size=12),
                    ),
                    dragmode=False,
                    height=480,
                    margin=dict(l=50, r=30, t=55, b=45),
                )

                st.plotly_chart(
                    fig, use_container_width=True,
                    config={
                        "displayModeBar": False,
                        "scrollZoom": False,
                        "doubleClick": False,
                        "staticPlot": False,
                    },
                )

                # Tabela resumo por ano
                st.markdown(
                    "<div style='font-size:0.82rem;color:#BFCF99;"
                    "margin-top:0.4rem;'><b>Resumo por Ano</b></div>",
                    unsafe_allow_html=True,
                )
                tab_r = resumo.copy()
                tab_r["Ano"]   = tab_r["ano"].astype(str)
                tab_r["Media"] = tab_r["Media"].apply(lambda v: f"{v:.{_dec}f}")
                tab_r["Min"]   = tab_r["Min"].apply(lambda v: f"{v:.{_dec}f}")
                tab_r["Max"]   = tab_r["Max"].apply(lambda v: f"{v:.{_dec}f}")
                st.dataframe(
                    tab_r[["Ano", "N", "Min", "Media", "Max"]],
                    use_container_width=True,
                    hide_index=True,
                )


# ======================================================================================
# LOTES PROMAC — KMZ convertido para GeoJSON + info dos vencedores
# ======================================================================================

CORES_LOTES = [
    '#e6194b','#3cb44b','#ffe119','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6',
    '#bfef45','#fabed4','#469990','#dcbeff','#9A6324','#fffac8','#800000','#aaffc3',
    '#808000','#ffd8b1','#000075','#a9a9a9','#FF6B6B','#4ECDC4','#FFE66D','#6B5B95',
    '#FF8C42','#A06CD5','#6EC6FF','#E850A8','#C5E17A','#FFB7C5','#5A9E94','#D4B8FF',
    '#B8860B','#FFFACD','#8B0000','#98FB98','#6B8E23','#FFDAB9','#000080','#C0C0C0',
]


@st.cache_data(ttl=86400, show_spinner=False)
def _carregar_promac_geojson() -> dict | None:
    _path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "cache_certificados", "promac_lotes.geojson",
    )
    if os.path.exists(_path):
        with open(_path, encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def _carregar_promac_info() -> dict:
    """Retorna dict {num_lote: {extensao_km, cnpj, empresa, situacao}}."""
    _path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "cache_certificados", "promac_lotes.json",
    )
    if os.path.exists(_path):
        with open(_path, encoding="utf-8") as f:
            data = json.load(f)
        return {item["lote"]: item for item in data}
    return {}


def _adicionar_lotes_promac(mapa: folium.Map, geojson: dict, info: dict,
                            lote_filtro: str = "Todos") -> None:
    """Adiciona os lotes PROMAC — 1 GeoJson por lote (40 max), sem GeoJsonTooltip."""
    fg = folium.FeatureGroup(name="Lotes PROMAC", show=True)

    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        lote_label = props.get("lote", "")
        if lote_filtro != "Todos" and lote_label != lote_filtro:
            continue

        cor      = props.get("cor", "#aaa")
        empresa  = props.get("empresa", "—")
        cnpj     = props.get("cnpj", "—")
        ext_km   = props.get("ext_km", "—")
        situacao = props.get("situacao", "—")

        popup_html = (
            f'<div style="background:#0a1929;color:#fff;font-family:sans-serif;'
            f'font-size:12px;padding:10px;border-radius:8px;min-width:240px;">'
            f'<div style="background:{cor};color:#fff;font-weight:700;font-size:14px;'
            f'padding:6px 10px;border-radius:6px 6px 0 0;margin:-10px -10px 8px;">'
            f'{lote_label}</div>'
            f'<b>Empresa:</b> {empresa}<br>'
            f'<b>CNPJ:</b> {cnpj}<br>'
            f'<b>Extensão:</b> {ext_km} km<br>'
            f'<b>Situação:</b> {situacao}'
            f'</div>'
        )

        folium.GeoJson(
            feat,
            style_function=lambda _, c=cor: {"color": c, "weight": 4, "opacity": 0.9},
            highlight_function=lambda _: {"color": "#fff", "weight": 7, "opacity": 1},
            tooltip=folium.Tooltip(
                f"<b>{lote_label}</b><br><small>{empresa}</small>",
                style="background:#0a1929;color:#fff;border:1px solid #566E3D;border-radius:4px;",
            ),
            popup=folium.Popup(popup_html, max_width=320),
        ).add_to(fg)

    fg.add_to(mapa)


# ======================================================================================
# BUSCA DE MUNICÍPIO + CONTORNO (IBGE GeoJSON on-demand)
# ======================================================================================

def _normalizar_texto(s: str) -> str:
    s2 = unicodedata.normalize("NFKD", str(s).upper())
    return "".join(c for c in s2 if not unicodedata.combining(c)).strip()


def _geojson_bbox_center(geojson: dict) -> tuple[float, float, float, float] | None:
    """Calcula centro e zoom ideal a partir do bounding box do GeoJSON."""
    lats, lons = [], []

    def _extrair(obj):
        if isinstance(obj, list):
            if obj and isinstance(obj[0], (int, float)):
                lons.append(obj[0])
                lats.append(obj[1])
            else:
                for item in obj:
                    _extrair(item)

    features = geojson.get("features", [geojson])
    for feat in features:
        geom = feat.get("geometry", {}) if isinstance(feat, dict) else {}
        _extrair(geom.get("coordinates", []))

    if not lats:
        return None

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    centro_lat = (lat_min + lat_max) / 2
    centro_lon = (lon_min + lon_max) / 2

    # Calcula zoom baseado na extensão do bbox (municípios BR ~ 0.05° a 3°)
    span = max(lat_max - lat_min, lon_max - lon_min)
    if span < 0.1:
        zoom = 13
    elif span < 0.3:
        zoom = 11
    elif span < 0.8:
        zoom = 10
    elif span < 1.5:
        zoom = 9
    else:
        zoom = 8

    return centro_lat, centro_lon, zoom


@st.cache_data(ttl=86400, show_spinner=False)
def _carregar_index_municipios() -> dict:
    """Carrega índice nome→codIBGE dos 399 municípios do PR."""
    _idx_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "cache_certificados", "pr_municipios_index.json"
    )
    if os.path.exists(_idx_path):
        with open(_idx_path, encoding="utf-8") as f:
            return json.load(f)
    # fallback: busca da API
    try:
        r = _requests.get(
            "https://servicodados.ibge.gov.br/api/v1/localidades/estados/41/municipios",
            timeout=10
        )
        muns = r.json()
        nomes = sorted(m["nome"] for m in muns)
        cod_map = {m["nome"]: str(m["id"]) for m in muns}
        return {"nomes": nomes, "cod_map": cod_map}
    except Exception:
        return {"nomes": [], "cod_map": {}}


@st.cache_data(ttl=3600, show_spinner=False)
def _buscar_geojson_municipio(cod: str) -> dict | None:
    """Busca o GeoJSON de contorno de um município pelo código IBGE."""
    try:
        url = f"https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{cod}?formato=application/vnd.geo+json"
        r = _requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _sugestoes_cidade(texto: str, nomes: list[str], max_res: int = 8) -> list[str]:
    """Retorna cidades cujo nome começa com o texto digitado (case-insensitive, sem acento)."""
    if not texto or len(texto) < 2:
        return []
    t = _normalizar_texto(texto)
    resultados = [n for n in nomes if _normalizar_texto(n).startswith(t)]
    if not resultados:
        resultados = [n for n in nomes if t in _normalizar_texto(n)]
    return resultados[:max_res]


def _adicionar_contorno_municipio(mapa: folium.Map, geojson: dict, nome: str) -> None:
    """Adiciona contorno destacado de município ao mapa folium."""
    folium.GeoJson(
        geojson,
        name=f"Contorno — {nome}",
        style_function=lambda _: {
            "fillColor":   "#BFCF99",
            "color":       "#BFCF99",
            "weight":      3.5,
            "fillOpacity": 0.12,
            "dashArray":   "6 4",
        },
        highlight_function=lambda _: {
            "fillColor":   "#BFCF99",
            "color":       "#ffffff",
            "weight":      5,
            "fillOpacity": 0.25,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[],
            aliases=[],
            sticky=False,
            labels=False,
            localize=True,
        ),
    ).add_to(mapa)
    # Tooltip simples com o nome
    folium.Marker(
        location=[0, 0],  # invisível — apenas para mostrar nome
        icon=folium.DivIcon(html="", icon_size=(0, 0)),
    )


# ======================================================================================
# LAYOUT PRINCIPAL
# ======================================================================================

def main():
    # ── Header ──────────────────────────────────────────────────────────────────────
    col_logo, col_titulo = st.columns([1, 5])
    with col_logo:
        _logo = get_logo_path("selo_c_ass")
        if _logo:
            try:
                st.image(_logo, use_container_width=True)
            except Exception:
                _logo = None
        if not _logo:
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
                <h1 style="margin:0;font-size:clamp(1.3rem, 4vw, 2.2rem) !important;">Mapeamento de Projetos CAUQ</h1>
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
            norma_sel  = st.selectbox("Especificação:", norma_opts, key="f_norma")
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
                "⛏ Pedreiras - Sem projeto",
                value=True,
                key="show_pedreiras_sem_projeto",
                help="Exibe no mapa as pedreiras que NÃO possuem projetos vinculados no período filtrado",
            )

            st.divider()
            st.checkbox(
                "🛣️ Lotes PROMAC",
                value=False,
                key="show_lotes_promac",
                help="Exibe os 40 lotes de manutenção rodoviária (DER/PR) no mapa",
            )
            if st.session_state.get("show_lotes_promac"):
                _promac_info = _carregar_promac_info()
                _lote_opts = ["Todos"] + [f"LOTE {n:02d}" for n in sorted(_promac_info.keys())]
                st.selectbox("Filtrar Lote:", _lote_opts, key="f_lote_promac")

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
            <div style="background:#0a3d5f;border-radius:8px;padding:0.5rem 0.6rem;
                        border-left:3px solid {cor};text-align:center;min-width:0;">
                <div style="color:{cor};font-size:0.65rem;text-transform:uppercase;
                            letter-spacing:0.04em;white-space:nowrap;overflow:hidden;
                            text-overflow:ellipsis;">{label}</div>
                <div style="color:#fff;font-size:1.15rem;font-weight:700;">{value}</div>
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
        <div style="display:flex;gap:1rem;margin-bottom:0.8rem;flex-wrap:wrap;align-items:center;">
            <span style="background:#E65100;color:#fff;border-radius:50%;padding:3px 8px;
                         font-size:0.78rem;font-weight:700;">N</span><span style="font-size:0.8rem;color:#ccc;">Basalto</span>
            <span style="background:#6A1B9A;color:#fff;border-radius:50%;padding:3px 8px;
                         font-size:0.78rem;font-weight:700;">N</span><span style="font-size:0.8rem;color:#ccc;">Granito</span>
            <span style="background:#F9A825;color:#1a1a1a;border-radius:50%;padding:3px 8px;
                         font-size:0.78rem;font-weight:700;">N</span><span style="font-size:0.8rem;color:#ccc;">Areia</span>
            <span style="background:#1A237E;color:#fff;border-radius:50%;padding:3px 8px;
                         font-size:0.78rem;font-weight:700;">N</span><span style="font-size:0.8rem;color:#ccc;">Gnaisse</span>
            <span style="color:#666;font-size:0.82rem;">&nbsp;|&nbsp;</span>
            <span style="background:#4E342E;color:#fff;border-radius:3px;padding:2px 6px;
                         font-size:0.72rem;">&#9935;</span><span style="font-size:0.8rem;color:#999;"> = sem projetos</span>
            <span style="color:#666;font-size:0.82rem;">&nbsp;|&nbsp;</span>
            <span style="color:#00E676;font-weight:600;font-size:0.8rem;">&#9679; Borda verde = GPS exato</span>
            <span style="color:#BFCF99;font-size:0.82rem;">&nbsp;| Clique no circulo para comparar projetos</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
 
    # ── Agrupar por localizacao ──────────────────────────────────────────────────────
    grupos_loc: dict = {}
    for _, row in df_geo.iterrows():
        key = (round(float(row["lat"]), 4), round(float(row["lon"]), 4))
        grupos_loc.setdefault(key, []).append(row)
 
 
    # ── Mapa (com cache de pedreiras por hash de filtros) ────────────────────────
    if df_geo.empty and mostrar_projetos:
        st.warning(
            "Nenhum projeto com localizacao geocodificada nos filtros selecionados."
        )
    else:
        import hashlib as _hl
        _show_sem_proj = st.session_state.get("show_pedreiras_sem_projeto", True)
        _filter_key = _hl.md5(
            f"{len(df)}_{nat_sel}_{loc_sel}_{proc_sel}_{_show_sem_proj}".encode()
        ).hexdigest()

        # Cache pedreiras layer — só recalcula quando filtros mudam
        if st.session_state.get("_ped_hash") != _filter_key:
            _intel = _filtrar_intel_pedreiras(
                PEDREIRAS_INTEL,
                nat_sel  if nat_sel  != "Todas" else None,
                loc_sel  if loc_sel  != "Todas" else None,
                proc_sel if proc_sel != "Todas" else None,
            )
            pedreiras_layer = _combinar_pedreiras_cauq(_intel, df)

            # Se o toggle "Sem projeto" está desmarcado, remove pedreiras sem projetos
            if not _show_sem_proj and pedreiras_layer:
                pedreiras_layer = [
                    p for p in pedreiras_layer
                    if (_stats_pedreira(df, p.get("procedencias", [])) or {}).get("n", 0) > 0
                ]

            st.session_state["_ped_cache"] = pedreiras_layer
            st.session_state["_ped_hash"] = _filter_key
        else:
            pedreiras_layer = st.session_state.get("_ped_cache")

        # ── BUSCA DE CIDADE — acima do mapa ──────────────────────────────────────
        _idx       = _carregar_index_municipios()
        _nomes_mun = _idx.get("nomes", [])
        _cod_map   = _idx.get("cod_map", {})

        _cidade_sel = st.selectbox(
            "Buscar cidade:",
            options=[""] + _nomes_mun,
            index=0,
            key="cidade_selectbox",
            format_func=lambda x: "Digite para buscar..." if x == "" else x,
            help="Digite o nome para filtrar. Ao selecionar, a região é contornada no mapa.",
        )

        _geojson_contorno = None
        _center_override  = None
        _nome_contorno = _cidade_sel or ""
        _cod_contorno  = _cod_map.get(_cidade_sel, "") if _cidade_sel else ""
        if _cod_contorno:
            with st.spinner(f"Carregando contorno de {_cidade_sel}..."):
                _geojson_contorno = _buscar_geojson_municipio(_cod_contorno)
            if _geojson_contorno:
                _center_override = _geojson_bbox_center(_geojson_contorno)

        mapa = _criar_mapa(
            grupos_loc, pedreiras=pedreiras_layer, df_projetos=df,
            geojson_contorno=_geojson_contorno, nome_contorno=_nome_contorno,
            center_override=_center_override,
        )

        # Lotes PROMAC
        _show_promac = st.session_state.get("show_lotes_promac", False)
        _lote_filtro = st.session_state.get("f_lote_promac", "Todos") if _show_promac else "Todos"
        if _show_promac:
            _promac_geo = _carregar_promac_geojson()
            _promac_inf = _carregar_promac_info()
            if _promac_geo:
                _adicionar_lotes_promac(mapa, _promac_geo, _promac_inf, _lote_filtro)

        # key dinâmica força re-render ao mudar toggle/filtro PROMAC
        import hashlib as _hlm
        _map_key = "cauq_map_" + _hlm.md5(
            f"{_filter_key}_{_show_promac}_{_lote_filtro}_{_nome_contorno}".encode()
        ).hexdigest()[:8]

        map_data = st_folium(
            mapa, width="100%", height=560,
            returned_objects=["last_object_clicked"], key=_map_key,
        )
 
        clk = (map_data or {}).get("last_object_clicked")
        if clk:
            import unicodedata as _ud_c
            def _nc(s):
                s2 = _ud_c.normalize("NFKD", str(s).upper())
                s2 = "".join(c for c in s2 if not _ud_c.combining(c))
                return " ".join(s2.split())

            lat_c = float(clk.get("lat", 0))
            lon_c = float(clk.get("lng", 0))

            # Encontrar a pedreira clicada pela coordenada
            matched_ped = None
            if pedreiras_layer:
                for _p in pedreiras_layer:
                    _pla = _p.get("lat"); _plo = _p.get("lon")
                    if _pla is not None and abs(_pla - lat_c) < 0.003 and abs(_plo - lon_c) < 0.003:
                        matched_ped = _p
                        break

            if matched_ped and not df.empty:
                proc_list = matched_ped.get("procedencias", [])
                proc_norm_col = df["procedencia"].astype(str).apply(_nc)
                mask = pd.Series(False, index=df.index)
                for p in proc_list:
                    mask |= proc_norm_col.str.contains(_nc(p), na=False, regex=False)
                sub = df[mask]
                if not sub.empty:
                    st.session_state["cauq_compare"] = [row.to_dict() for _, row in sub.iterrows()]
                else:
                    st.session_state.pop("cauq_compare", None)
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
            st.bar_chart(df_ano.set_index("ano"), height=220)
        with col_b:
            st.markdown("**Norma por Ano**")
            ct = pd.crosstab(df["ano"], df["norma"])
            st.bar_chart(ct, height=220)
 
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
                st.bar_chart(nat_df.set_index("Natureza"), height=260)
 
        with col_m2:
            st.markdown("**Ligante Asfaltico**")
            lig_counts = df["ligante"].dropna()
            lig_counts = lig_counts[~lig_counts.isin(["", "-", "nan", "0"])]
            if not lig_counts.empty:
                lig_df = lig_counts.value_counts().reset_index()
                lig_df.columns = ["Ligante", "Projetos"]
                st.bar_chart(lig_df.set_index("Ligante"), height=260)
 
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