"""
Parser de relatórios exportados do Bling (CSV, XLS, XLSX).

Funções principais:
- extrair_data_do_nome(nome_arquivo)
- parsear_relatorio(uploaded_file, codigos_filtro=None)
"""

import re
from datetime import date
from typing import Optional

import pandas as pd

from core.config import EMBALAGENS_CODIGOS


# ==========================================
# CONFIGURAÇÃO
# ==========================================

def _normalizar_lista_codigos(codigos) -> list:
    """
    Aceita lista, tupla, set ou dict e retorna lista de códigos em maiúsculo.
    """
    if codigos is None:
        return []

    if isinstance(codigos, dict):
        codigos = list(codigos.keys())

    return [str(c).strip().upper() for c in codigos if str(c).strip()]


CODIGOS_ALVO = _normalizar_lista_codigos(EMBALAGENS_CODIGOS)


# ==========================================
# DATA DO NOME DO ARQUIVO
# ==========================================

def extrair_data_do_nome(nome_arquivo: str) -> Optional[date]:
    """
    Extrai data do nome do arquivo.

    Aceita exemplos:
        relatorio_22_04_2026.csv
        relatorio_22-04-2026.xlsx
        22_04_2026.csv
        estoque_2026_04_22.xlsx

    Retorna:
        datetime.date ou None
    """

    if not nome_arquivo:
        return None

    nome_arquivo = str(nome_arquivo)

    padroes = [
        r"(\d{2})[_\-](\d{2})[_\-](\d{4})",  # DD_MM_AAAA ou DD-MM-AAAA
        r"(\d{4})[_\-](\d{2})[_\-](\d{2})",  # AAAA_MM_DD ou AAAA-MM-DD
    ]

    for padrao in padroes:
        match = re.search(padrao, nome_arquivo)

        if not match:
            continue

        g1, g2, g3 = match.groups()

        try:
            if len(g1) == 4:
                ano = int(g1)
                mes = int(g2)
                dia = int(g3)
            else:
                dia = int(g1)
                mes = int(g2)
                ano = int(g3)

            return date(ano, mes, dia)

        except ValueError:
            return None

    return None


# ==========================================
# TRATAMENTO DE NÚMEROS
# ==========================================

def parse_quantidade_br(valor) -> int:
    """
    Converte quantidade brasileira para inteiro.

    Exemplos:
        "1.500" -> 1500
        "1.500,00" -> 1500
        "1500" -> 1500
        "" -> 0
    """

    if pd.isna(valor):
        return 0

    s = str(valor).strip().strip('"').strip("'")

    if s in ("", "-", "0", "0,00", "0.00"):
        return 0

    s = re.sub(r"[^\d.,\-]", "", s)

    if not s:
        return 0

    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")

    try:
        return max(0, int(float(s)))
    except ValueError:
        return 0


# ==========================================
# LEITURA DO ARQUIVO
# ==========================================

def _ler_csv(uploaded_file) -> pd.DataFrame:
    """
    Tenta ler CSV do Bling com diferentes encodings e separadores.
    """

    encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
    separadores = [";", ",", "\t"]

    ultimo_erro = None

    for encoding in encodings:
        for sep in separadores:
            try:
                uploaded_file.seek(0)

                df = pd.read_csv(
                    uploaded_file,
                    sep=sep,
                    encoding=encoding,
                    dtype=str,
                    engine="python",
                )

                if df.shape[1] >= 4:
                    return df

            except Exception as e:
                ultimo_erro = e

    try:
        uploaded_file.seek(0)

        return pd.read_csv(
            uploaded_file,
            sep=None,
            encoding="latin1",
            dtype=str,
            engine="python",
        )

    except Exception:
        return pd.DataFrame()


def _ler_excel(uploaded_file) -> pd.DataFrame:
    """
    Lê XLS/XLSX.
    """

    try:
        uploaded_file.seek(0)

        df = pd.read_excel(
            uploaded_file,
            dtype=str,
        )

        return df

    except Exception:
        return pd.DataFrame()


def _padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza o relatório do Bling para:
        Codigo, GTIN, Descricao, Unidade, Quantidade
    """

    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    mapa_colunas = {}

    for col in df.columns:
        col_norm = (
            str(col)
            .strip()
            .lower()
            .replace("ó", "o")
            .replace("í", "i")
            .replace("ç", "c")
            .replace("ã", "a")
            .replace("á", "a")
            .replace("é", "e")
        )

        if col_norm in ["codigo", "código", "cod", "sku"]:
            mapa_colunas[col] = "Codigo"

        elif col_norm in ["gtin", "ean", "gtin/ean", "codigo de barras"]:
            mapa_colunas[col] = "GTIN"

        elif col_norm in ["produto", "descricao", "descrição", "nome"]:
            mapa_colunas[col] = "Descricao"

        elif col_norm in ["unidade", "un"]:
            mapa_colunas[col] = "Unidade"

        elif col_norm in ["quantidade", "estoque", "estoque fisico", "saldo"]:
            mapa_colunas[col] = "Quantidade"

    df = df.rename(columns=mapa_colunas)

    colunas_necessarias = ["Codigo", "Descricao", "Unidade", "Quantidade"]

    if all(c in df.columns for c in colunas_necessarias):
        if "GTIN" not in df.columns:
            df["GTIN"] = ""

        return df[["Codigo", "GTIN", "Descricao", "Unidade", "Quantidade"]].copy()

    if df.shape[1] >= 5:
        df = df.iloc[:, :5].copy()
        df.columns = ["Codigo", "GTIN", "Descricao", "Unidade", "Quantidade"]
        return df

    if df.shape[1] >= 4:
        df = df.iloc[:, :4].copy()
        df.columns = ["Codigo", "Descricao", "Unidade", "Quantidade"]
        df["GTIN"] = ""
        return df[["Codigo", "GTIN", "Descricao", "Unidade", "Quantidade"]]

    return pd.DataFrame()


def _ler_arquivo(uploaded_file) -> pd.DataFrame:
    """
    Lê CSV, XLS ou XLSX e retorna DataFrame cru padronizado.
    """

    if uploaded_file is None:
        return pd.DataFrame()

    nome = uploaded_file.name.lower()

    if nome.endswith(".csv"):
        df = _ler_csv(uploaded_file)

    elif nome.endswith((".xls", ".xlsx")):
        df = _ler_excel(uploaded_file)

    else:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    return _padronizar_colunas(df)


# ==========================================
# PARSER PRINCIPAL
# ==========================================

def parsear_relatorio(uploaded_file, codigos_filtro=None) -> pd.DataFrame:
    """
    Lê arquivo exportado do Bling e retorna DataFrame limpo com:

        Codigo
        Descricao
        Unidade
        Quantidade

    Filtra apenas os códigos de embalagem configurados.
    """

    df = _ler_arquivo(uploaded_file)

    if df.empty:
        return pd.DataFrame(
            columns=["Codigo", "Descricao", "Unidade", "Quantidade"]
        )

    df = df.copy()

    df = df[
        ~df["Codigo"]
        .astype(str)
        .str.contains("total", case=False, na=False)
    ].copy()

    df["Codigo"] = (
        df["Codigo"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Descricao"] = (
        df["Descricao"]
        .astype(str)
        .str.strip()
    )

    df["Unidade"] = (
        df["Unidade"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Quantidade"] = df["Quantidade"].apply(parse_quantidade_br)

    codigos_alvo = (
        _normalizar_lista_codigos(codigos_filtro)
        if codigos_filtro is not None
        else CODIGOS_ALVO
    )

    if codigos_alvo:
        df = df[df["Codigo"].isin(codigos_alvo)].copy()

    if df.empty:
        return pd.DataFrame(
            columns=["Codigo", "Descricao", "Unidade", "Quantidade"]
        )

    df = df[["Codigo", "Descricao", "Unidade", "Quantidade"]].copy()

    df = df.sort_values("Codigo").reset_index(drop=True)

    return df


# ==========================================
# ALIAS OPCIONAL PARA COMPATIBILIDADE
# ==========================================

def processar_csv_bling(uploaded_file, codigos_filtro=None) -> pd.DataFrame:
    """
    Alias de compatibilidade caso alguma página antiga chame processar_csv_bling.
    """
    return parsear_relatorio(uploaded_file, codigos_filtro=codigos_filtro)