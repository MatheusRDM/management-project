"""
utils_performance.py — Dados de Performance de Contratos
Correlaciona: Centro de Custo · Rateio Mensal · Medições
"""

import os
import re
import glob
import pandas as pd

# =============================================================================
# CAMINHOS BASE
# =============================================================================

BASE_CONTROLE = r"Z:\CONTROLE OPERACIONAL\01. Controles"
BASE_RATEIO   = r"Z:\CONTROLE OPERACIONAL\01. Controles\2. RATEIO MENSAL DE PESSOAL"
BASE_MEDICOES = r"Z:\CONTROLE OPERACIONAL\13. Medições"

CENTRO_CUSTO_FILE = os.path.join(BASE_CONTROLE, "centro de custo 2.xlsx")
RESUMO_MEDICOES   = os.path.join(BASE_MEDICOES, "Resumo Medições.xlsx")

MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO",    6: "JUNHO",     7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO",10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}
MESES_ABREV = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR",
    5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
}

# =============================================================================
# CENTRO DE CUSTO
# =============================================================================

def carregar_centro_custo() -> pd.DataFrame:
    """Retorna tabela de centros de custo: COD | Descrição | Código e Nome"""
    if not os.path.exists(CENTRO_CUSTO_FILE):
        return pd.DataFrame(columns=["COD", "Descricao", "Codigo_e_Nome"])
    xf = pd.ExcelFile(CENTRO_CUSTO_FILE)
    sheet = "Cadastro de Plano de Custos" if "Cadastro de Plano de Custos" in xf.sheet_names else xf.sheet_names[0]
    df = pd.read_excel(CENTRO_CUSTO_FILE, sheet_name=sheet, dtype=str)
    df.columns = df.columns.str.strip()
    # normaliza colunas
    rename = {}
    for c in df.columns:
        lc = c.lower()
        if "digo" in lc and "nome" not in lc:
            rename[c] = "COD"
        elif "descri" in lc:
            rename[c] = "Descricao"
        elif "nome" in lc:
            rename[c] = "Codigo_e_Nome"
    df = df.rename(columns=rename)
    df = df.dropna(subset=["COD", "Descricao"])
    df["COD"] = df["COD"].astype(str).str.strip().str.zfill(9)
    df["Descricao"] = df["Descricao"].str.strip()
    return df[["COD", "Descricao", "Codigo_e_Nome"]].reset_index(drop=True)


def dict_cod_nome() -> dict:
    """Retorna {COD: Descrição} para join rápido."""
    df = carregar_centro_custo()
    return dict(zip(df["COD"], df["Descricao"]))


# =============================================================================
# RATEIO MENSAL — descoberta dinâmica de arquivos disponíveis
# =============================================================================

def _meses_disponiveis() -> list[dict]:
    """Varre a pasta de rateio e retorna lista de {ano, mes, label, path}."""
    resultados = []
    if not os.path.isdir(BASE_RATEIO):
        return resultados
    for ano_dir in sorted(os.listdir(BASE_RATEIO), reverse=True):
        ano_path = os.path.join(BASE_RATEIO, ano_dir)
        if not os.path.isdir(ano_path) or not ano_dir.isdigit():
            continue
        ano = int(ano_dir)
        for mes_dir in sorted(os.listdir(ano_path), reverse=True):
            mes_path = os.path.join(ano_path, mes_dir)
            if not os.path.isdir(mes_path):
                continue
            # descobre xlsx dentro da pasta
            xlsx = glob.glob(os.path.join(mes_path, "*.xlsx"))
            xlsx = [f for f in xlsx if not os.path.basename(f).startswith("~$")]
            if not xlsx:
                continue
            # tenta identificar o mês pelo nome da pasta
            mes_num = _detectar_mes(mes_dir)
            label = f"{MESES_ABREV.get(mes_num, mes_dir[:3].upper())}/{ano}"
            resultados.append({
                "ano": ano, "mes": mes_num,
                "label": label,
                "pasta": mes_path,
                "arquivo": xlsx[0],
            })
    return resultados


def _detectar_mes(texto: str) -> int:
    t = texto.upper()
    ordem = [
        (["JAN"], 1), (["FEV","FEB"], 2), (["MAR"], 3), (["ABR","APR"], 4),
        (["MAI","MAY"], 5), (["JUN"], 6), (["JUL"], 7), (["AGO","AUG"], 8),
        (["SET","SEP"], 9), (["OUT","OCT"], 10), (["NOV"], 11), (["DEZ","DEC"], 12),
    ]
    for abrevs, num in ordem:
        if any(a in t for a in abrevs):
            return num
    return 0


def meses_disponiveis_labels() -> list[str]:
    return [m["label"] for m in _meses_disponiveis()]


def _info_por_label(label: str) -> dict | None:
    for m in _meses_disponiveis():
        if m["label"] == label:
            return m
    return None


# =============================================================================
# CARREGAR RATEIO (CLT + PJ unificados)
# =============================================================================

def carregar_rateio(label: str) -> pd.DataFrame:
    """
    Carrega e unifica as abas CLT e PJ do arquivo de rateio do mês/ano.
    Retorna DataFrame com colunas normalizadas.
    """
    info = _info_por_label(label)
    if info is None:
        return pd.DataFrame()

    arquivo = info["arquivo"]
    try:
        xf = pd.ExcelFile(arquivo)
    except Exception:
        return pd.DataFrame()

    sheets = xf.sheet_names
    ano_s = str(info["ano"])[-2:]  # "26"
    mes_s = MESES_ABREV.get(info["mes"], "").lower()  # "fev"

    # detecta sheets CLT e PJ para o mês correto
    clt_sheet = _encontrar_sheet(sheets, [f"{mes_s}{ano_s}", f"{mes_s} {ano_s}"], ["clt"])
    pj_sheet  = _encontrar_sheet(sheets, [f"{mes_s}{ano_s}", f"{mes_s} {ano_s}"], ["pj"])

    frames = []
    for sheet, tipo in [(clt_sheet, "CLT"), (pj_sheet, "PJ")]:
        if sheet is None:
            continue
        df = pd.read_excel(arquivo, sheet_name=sheet, header=0, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        df = _normalizar_rateio(df, tipo)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out["MES_LABEL"] = label
    return out


def _encontrar_sheet(sheets: list, prefixos: list, sufixos: list) -> str | None:
    """Encontra sheet que contenha qualquer prefixo E qualquer sufixo (case-insensitive)."""
    for s in sheets:
        sl = s.lower().replace(" ", "").replace("-", "")
        for p in prefixos:
            pl = p.lower().replace(" ", "").replace("-", "")
            for sf in sufixos:
                if pl in sl and sf in sl:
                    return s
    # fallback: apenas sufixo
    for s in sheets:
        sl = s.lower()
        if any(sf in sl for sf in sufixos):
            return s
    return None


def _normalizar_rateio(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Mapeia colunas variáveis para esquema padrão."""
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if re.search(r"c[oó]d", cl) and "nome" not in cl and "centro" not in cl:
            col_map[c] = "COD"
        elif "centro" in cl and "custo" in cl:
            col_map[c] = "CENTRO_CUSTO"
        elif "gestor" in cl:
            col_map[c] = "GESTOR"
        elif "colaborador" in cl:
            col_map[c] = "COLABORADOR"
        elif re.search(r"fun[çc][aã]o", cl):
            col_map[c] = "FUNCAO"
        elif "status" in cl or "situac" in cl:
            col_map[c] = "STATUS"
        elif re.search(r"in[íi]cio|inicio", cl):
            col_map[c] = "DATA_INI"
        elif re.search(r"final|fim", cl) and "periodo" in cl:
            col_map[c] = "DATA_FIM"
        elif re.search(r"sal[aá]rio\s*x|utiliza[çc]", cl):
            col_map[c] = "SALARIO_UTILIZADO"
        elif re.search(r"sal[aá]rio", cl):
            col_map[c] = "SALARIO_BASE"
        elif re.search(r"rateio\s*custo|%\s*custo|%custo", cl):
            col_map[c] = "PERC_CUSTO"
        elif re.search(r"produtividade", cl):
            col_map[c] = "PRODUTIVIDADE"

    df = df.rename(columns=col_map)
    df["TIPO"] = tipo

    obrigatorias = ["COD", "CENTRO_CUSTO", "COLABORADOR", "FUNCAO",
                    "STATUS", "PERC_CUSTO", "PRODUTIVIDADE", "TIPO",
                    "GESTOR", "DATA_INI", "DATA_FIM",
                    "SALARIO_BASE", "SALARIO_UTILIZADO"]
    for col in obrigatorias:
        if col not in df.columns:
            df[col] = None

    df = df[obrigatorias].copy()

    # limpa
    df["COLABORADOR"] = df["COLABORADOR"].astype(str).str.strip()
    df = df[df["COLABORADOR"].str.len() > 2]
    df = df[~df["COLABORADOR"].str.lower().isin(["nan", "none", "colaborador", "total", ""])]

    df["COD"] = df["COD"].astype(str).str.strip().str.zfill(9)
    df["CENTRO_CUSTO"] = df["CENTRO_CUSTO"].astype(str).str.strip()
    df["STATUS"] = df["STATUS"].astype(str).str.strip().str.upper()

    for col_num in ["PERC_CUSTO", "PRODUTIVIDADE", "SALARIO_BASE", "SALARIO_UTILIZADO"]:
        df[col_num] = pd.to_numeric(df[col_num], errors="coerce")

    # CLT: SALARIO_UTILIZADO já calculado; para PJ PERC_CUSTO é a proporção (sem salário nominal)
    if tipo == "CLT":
        df["CUSTO_ALOCADO"] = df["SALARIO_UTILIZADO"]
    else:
        df["CUSTO_ALOCADO"] = None  # PJ sem valor nominal no rateio

    return df


# =============================================================================
# RESUMO DE MEDIÇÕES (faturamento por contrato)
# =============================================================================

def carregar_resumo_medicoes(ano: int | None = None) -> pd.DataFrame:
    """
    Lê Resumo Medições.xlsx — aba do ano solicitado.
    Retorna DataFrame: CONTRATANTE | CENTRO_CUSTO | GRUPO | ESCOPO | STATUS | {colunas mensais...}
    """
    if not os.path.exists(RESUMO_MEDICOES):
        return pd.DataFrame()

    try:
        xf = pd.ExcelFile(RESUMO_MEDICOES)
    except Exception:
        return pd.DataFrame()

    sheets = xf.sheet_names
    if ano is None:
        # pega o mais recente
        anos = [int(s) for s in sheets if s.isdigit()]
        if not anos:
            return pd.DataFrame()
        ano = max(anos)

    sheet = str(ano)
    if sheet not in sheets:
        return pd.DataFrame()

    df = pd.read_excel(RESUMO_MEDICOES, sheet_name=sheet, header=0)
    df.columns = [str(c).strip() for c in df.columns]

    # renomeia colunas fixas conhecidas
    rename = {}
    for c in df.columns:
        cl = c.lower()
        if "contratante" in cl:
            rename[c] = "CONTRATANTE"
        elif "centro" in cl and "custo" in cl:
            rename[c] = "CENTRO_CUSTO"
        elif "grupo" in cl:
            rename[c] = "GRUPO"
        elif "escopo" in cl or "tipo" in cl:
            rename[c] = "ESCOPO"
        elif "dia" in cl and "medi" in cl:
            rename[c] = "DIA_MEDICAO"
        elif "status" in cl:
            rename[c] = "STATUS"

    df = df.rename(columns=rename)

    # identifica colunas de valor mensal (float/datetime cabeçalhos)
    colunas_fixas = {"CONTRATANTE", "CENTRO_CUSTO", "GRUPO", "ESCOPO", "DIA_MEDICAO", "STATUS"}
    colunas_mes = [c for c in df.columns if c not in colunas_fixas]

    df = df.dropna(subset=["CENTRO_CUSTO"])
    df["ANO"] = ano
    return df


# =============================================================================
# MEDIÇÕES MENSAIS — detalhe por colaborador (Unificado)
# =============================================================================

def _path_medicoes_mensais(ano: int, mes: int) -> str | None:
    resumo_dir = os.path.join(BASE_MEDICOES, "000-RESUMO", str(ano))
    if not os.path.isdir(resumo_dir):
        return None
    # busca subpasta do mês
    mes_nome = MESES_PT.get(mes, "")
    for d in sorted(os.listdir(resumo_dir)):
        dl = d.upper()
        if str(mes).zfill(2) in d[:3] or mes_nome[:3] in dl:
            pasta = os.path.join(resumo_dir, d)
            if os.path.isdir(pasta):
                xlsx = [f for f in glob.glob(os.path.join(pasta, "*.xlsx"))
                        if not os.path.basename(f).startswith("~$")]
                if xlsx:
                    return xlsx[0]
    return None


def carregar_unificado(ano: int, mes: int) -> pd.DataFrame:
    """
    Lê a aba 'Unificado' do arquivo de medições do mês.
    Retorna DataFrame com colunas: MES | MEDICAO | CONTRATO | OBRA | CLIENTE |
      SERVICO | COLABORADOR | MATRICULA | PRODUTIVIDADE | QTDE | PRECO_UNIT | VALOR_TOTAL
    """
    path = _path_medicoes_mensais(ano, mes)
    if not path or not os.path.exists(path):
        return pd.DataFrame()

    try:
        xf = pd.ExcelFile(path)
    except Exception:
        return pd.DataFrame()

    # encontra aba Unificado (case-insensitive)
    sheet = next((s for s in xf.sheet_names if "unificado" in s.lower()), None)
    if sheet is None:
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name=sheet, header=0)
    df.columns = [str(c).strip() for c in df.columns]

    rename = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl == "mês" or cl == "mes":
            rename[c] = "MES"
        elif "medi" in cl and ("ão" in cl or "ao" in cl or cl == "medição"):
            rename[c] = "MEDICAO"
        elif "cliente" in cl and "contrato" in cl:
            rename[c] = "CONTRATO"
        elif cl == "obra":
            rename[c] = "OBRA"
        elif cl == "cliente":
            rename[c] = "CLIENTE"
        elif "discrimina" in cl or "servi" in cl:
            rename[c] = "SERVICO"
        elif cl == "info":
            rename[c] = "COLABORADOR"
        elif "matri" in cl:
            rename[c] = "MATRICULA"
        elif "produtividade" in cl:
            rename[c] = "PRODUTIVIDADE"
        elif "qtde" in cl or "quantidade" in cl:
            rename[c] = "QTDE"
        elif "pre" in cl and "unit" in cl:
            rename[c] = "PRECO_UNIT"

    df = df.rename(columns=rename)

    for col in ["MES", "MEDICAO", "CONTRATO", "OBRA", "CLIENTE",
                "SERVICO", "COLABORADOR", "MATRICULA", "PRODUTIVIDADE",
                "QTDE", "PRECO_UNIT"]:
        if col not in df.columns:
            df[col] = None

    df["QTDE"] = pd.to_numeric(df["QTDE"], errors="coerce").fillna(0)
    df["PRECO_UNIT"] = pd.to_numeric(df["PRECO_UNIT"], errors="coerce").fillna(0)
    df["PRODUTIVIDADE"] = pd.to_numeric(df["PRODUTIVIDADE"], errors="coerce")
    df["VALOR_TOTAL"] = df["QTDE"] * df["PRECO_UNIT"]
    df["ANO"] = ano
    df["MES_NUM"] = mes

    df = df.dropna(subset=["COLABORADOR"])
    df = df[df["COLABORADOR"].astype(str).str.strip().str.len() > 1]

    return df


# =============================================================================
# CORRELAÇÃO: rateio × medições
# =============================================================================

def correlacionar(df_rateio: pd.DataFrame, df_unif: pd.DataFrame) -> pd.DataFrame:
    """
    Faz fuzzy-join entre COLABORADOR do rateio e COLABORADOR das medições.
    Retorna tabela enriquecida.
    """
    if df_rateio.empty or df_unif.empty:
        return pd.DataFrame()

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", str(s).upper().strip())

    df_rateio = df_rateio.copy()
    df_unif   = df_unif.copy()
    df_rateio["_KEY"] = df_rateio["COLABORADOR"].apply(_norm)
    df_unif["_KEY"]   = df_unif["COLABORADOR"].apply(_norm)

    merged = pd.merge(
        df_unif, df_rateio[["_KEY", "CENTRO_CUSTO", "FUNCAO", "GESTOR",
                             "STATUS", "TIPO", "PERC_CUSTO", "SALARIO_BASE",
                             "CUSTO_ALOCADO", "PRODUTIVIDADE"]],
        on="_KEY", how="left", suffixes=("", "_rateio")
    )
    merged = merged.drop(columns=["_KEY"], errors="ignore")
    return merged


# =============================================================================
# RESUMO EXECUTIVO por colaborador
# =============================================================================

def resumo_por_colaborador(df_rateio: pd.DataFrame) -> pd.DataFrame:
    """Agrega rateio para visão por colaborador."""
    if df_rateio.empty:
        return pd.DataFrame()

    agg = (
        df_rateio.groupby("COLABORADOR", sort=True)
        .agg(
            FUNCAO=("FUNCAO", "first"),
            TIPO=("TIPO", "first"),
            GESTOR=("GESTOR", "first"),
            STATUS=("STATUS", "first"),
            NUM_CONTRATOS=("CENTRO_CUSTO", "nunique"),
            CONTRATOS=("CENTRO_CUSTO", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))),
            PERC_CUSTO_TOTAL=("PERC_CUSTO", "sum"),
            SALARIO_BASE=("SALARIO_BASE", "first"),
            CUSTO_TOTAL=("CUSTO_ALOCADO", "sum"),
            PRODUTIVIDADE_MEDIA=("PRODUTIVIDADE", "mean"),
        )
        .reset_index()
    )
    return agg


# =============================================================================
# RESUMO por contrato
# =============================================================================

def resumo_por_contrato(df_rateio: pd.DataFrame, df_resumo: pd.DataFrame) -> pd.DataFrame:
    """Agrega rateio + faturamento por contrato."""
    agg_pes = (
        df_rateio.groupby("CENTRO_CUSTO")
        .agg(
            NUM_COLABORADORES=("COLABORADOR", "nunique"),
            COLABORADORES=("COLABORADOR", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))),
            CUSTO_PESSOAL=("CUSTO_ALOCADO", "sum"),
        )
        .reset_index()
    )

    if not df_resumo.empty:
        df_resumo = df_resumo.rename(columns={"CENTRO_CUSTO": "CENTRO_CUSTO"})
        out = pd.merge(agg_pes, df_resumo[["CENTRO_CUSTO", "GRUPO", "ESCOPO", "STATUS"]],
                       on="CENTRO_CUSTO", how="left")
    else:
        out = agg_pes

    return out
