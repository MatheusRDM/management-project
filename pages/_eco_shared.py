"""
_eco_shared.py — shared constants/paths for ECO Rodovias modules.
No streamlit imports here.
"""
import os

# ── Paleta ────────────────────────────────────────────────────────────────────
COR_PRIMARY  = "#566E3D"
COR_ACCENT   = "#BFCF99"
COR_BG       = "#0D1B2A"
COR_CARD     = "rgba(26, 31, 46, 0.85)"
COR_BORDER   = "rgba(86,110,61,0.35)"
COR_TEXT     = "#E8EFD8"
COR_MUTED    = "#8FA882"
COR_OK       = "#3cb44b"
COR_COBRAR   = "#e6194b"
COR_NE       = "#3a4a5e"
COR_ELAB     = "#4363d8"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color=COR_TEXT, size=12),
    margin=dict(l=10, r=10, t=35, b=10),
    hoverlabel=dict(bgcolor=COR_BG, bordercolor=COR_PRIMARY,
                    font=dict(color=COR_TEXT, size=12, family="Poppins")),
    hovermode="closest",
    dragmode=False,
)
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_DIR = os.path.join(_BASE_DIR, "cache_certificados")
_Y_BASE    = "Y:/24-017 ECO 050 e CERRADO - Supervisão de Obras/04. Medição AFIRMA"
_IS_CLOUD  = not os.path.exists(_Y_BASE)
