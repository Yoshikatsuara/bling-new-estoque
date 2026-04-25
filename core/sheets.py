"""
Cliente Google Sheets.
Centraliza abertura de planilha e operações de leitura/escrita.
"""

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from core.config import JSON_CREDENTIALS, get_spreadsheet_id

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_client() -> gspread.Client:
    try:
        info = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file(JSON_CREDENTIALS, scopes=SCOPES)
    return gspread.authorize(creds)


def abrir_planilha() -> gspread.Spreadsheet:
    """Abre a planilha principal do projeto."""
    return _get_client().open_by_key(get_spreadsheet_id())


def get_aba(nome_aba: str, criar_se_nao_existir: bool = False,
            cabecalho: list = None, rows: int = 5000, cols: int = 12) -> gspread.Worksheet:
    """
    Retorna uma aba pelo nome. Opcionalmente cria se não existir.

    Args:
        nome_aba: nome da aba
        criar_se_nao_existir: se True, cria aba vazia
        cabecalho: se criando, adiciona esta linha como cabeçalho
        rows, cols: dimensões ao criar
    """
    sh = abrir_planilha()
    try:
        return sh.worksheet(nome_aba)
    except gspread.exceptions.WorksheetNotFound:
        if not criar_se_nao_existir:
            raise
        aba = sh.add_worksheet(title=nome_aba, rows=rows, cols=cols)
        if cabecalho:
            aba.append_row(cabecalho, value_input_option="RAW")
        return aba


@st.cache_data(ttl=60, show_spinner=False)
def ler_aba_como_df(nome_aba: str) -> pd.DataFrame:
    """Lê uma aba inteira como DataFrame. Cache de 60s."""
    try:
        aba = get_aba(nome_aba)
        dados = aba.get_all_records()
        return pd.DataFrame(dados) if dados else pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()


def append_linhas(nome_aba: str, linhas: list, value_input_option: str = "RAW") -> None:
    """Adiciona linhas em batch na aba."""
    aba = get_aba(nome_aba)
    aba.append_rows(linhas, value_input_option=value_input_option)


def invalidar_cache():
    """Chama quando acabou de gravar algo e quer forçar releitura."""
    ler_aba_como_df.clear()
