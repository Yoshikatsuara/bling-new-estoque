"""
Configurações centrais do sistema Frutifica.
Fonte única de constantes usadas por todas as páginas.
"""

# ==========================================
# PLANILHA
# ==========================================

import streamlit as st

SPREADSHEET_ID = "1YznbVsWCjzm9U7j-iGqD17Gj4F-8kFcFhHcGQbcOjXg"
JSON_CREDENTIALS = "credenciais.json"

def get_spreadsheet_id():
    return SPREADSHEET_ID

ABA_CONTROLE_ESTOQUE = "Controle_Estoque"
ABA_SALDO_INICIAL = "Saldo_Inicial"

# Cabeçalho padrão do Controle_Estoque (inclui Tipo e Canal)
CABECALHO_CONTROLE_ESTOQUE = [
    "Codigo",
    "Descricao",
    "Unidade",
    "Preco (R$)",
    "Estoque Fisico",
    "Estoque Virtual",
    "Situacao",
    "Tipo",              # "Consumo" ou "Entrada"
    "Canal",             # "I9", "Montagem", "Estoque"
    "Data Relatorio",
    "Atualizado em",
]

CABECALHO_SALDO_INICIAL = ["Codigo", "Saldo_Inicial", "Data_Base", "Data_Definicao"]

# ==========================================
# EMBALAGENS
# ==========================================

EMBALAGENS_ORDEM = [
    "EMB116", "EMB115", "EMB109", "EMB108", "EMB110",
    "EMB111", "EMB112", "EMB113", "EMB114", "EMB_ETQ",
]

EMBALAGENS_CODIGOS = EMBALAGENS_ORDEM  # alias

EMBALAGENS_LABELS = {
    "EMB116": "EMB116: BANDEJA ROSA I9",
    "EMB115": "EMB115: BANDEJA VERDE I9",
    "EMB109": "EMB109: EMB TAMPA ROSA CUPIM NOVO",
    "EMB108": "EMB108: EMB TAMPA ROSA PATINHO MOIDO",
    "EMB110": "EMB110: EMB TAMPA VERDE FEIJOADA NOVA",
    "EMB111": "EMB111: EMB TAMPA VERDE FRANGO PARMEGIANA",
    "EMB112": "EMB112: EMB TAMPA VERDE ESTROGONOFE FRANGO",
    "EMB113": "EMB113: TAMPA LISA VERDE I9",
    "EMB114": "EMB114: TAMPA LISA ROSA I9",
    "EMB_ETQ": "EMB_ETQ: ETIQUETAS LISAS",
}

# ==========================================
# TIPOS E CANAIS
# ==========================================

TIPOS_MOVIMENTACAO = ["Consumo", "Entrada"]

CANAIS = ["I9", "Montagem", "Estoque"]

# ==========================================
# DATAS
# ==========================================

MESES_NUM = {
    "Abril 2026": "04",
    "Maio 2026": "05",
    "Junho 2026": "06",
    "Julho 2026": "07",
    "Agosto 2026": "08",
    "Setembro 2026": "09",
    "Outubro 2026": "10",
    "Novembro 2026": "11",
    "Dezembro 2026": "12",
}

ALERTA_ESTOQUE_BAIXO = 500  # unidades

# ==========================================
# BLING API
# ==========================================

BLING_API_BASE = "https://api.bling.com.br/Api/v3"
REDIRECT_URI = "https://bling-new-estoque.streamlit.app"
TOKEN_FILE = "bling_token.json"

def get_bling_credentials():
    """Retorna (client_id, client_secret) do Bling."""
    try:
        return st.secrets["bling"]["client_id"], st.secrets["bling"]["client_secret"]
    except Exception:
        # Fallback local
        import json
        with open("credenciais.json") as f:
            creds = json.load(f)
        return creds["client_id"], creds["client_secret"]