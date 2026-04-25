"""
Constantes centralizadas do projeto.
Mudou depósito, embalagem, ID de planilha? Muda aqui e propaga pra todas as páginas.
"""

import streamlit as st

# ==========================================
# GOOGLE SHEETS
# ==========================================

SPREADSHEET_ID = "1YznbVsWCjzm9U7j-iGqD17Gj4F-8kFcFhHcGQbcOjXg"
JSON_CREDENTIALS = "credenciais.json"

# Nomes das abas
ABA_CONTROLE_ESTOQUE = "Controle_Estoque"
ABA_MOVIMENTACOES = "Movimentacoes"
ABA_BOM = "BOM"  # Ficha técnica (futuro)

# ==========================================
# BLING API
# ==========================================

TOKEN_FILE = "bling_token.json"
REDIRECT_URI = "http://localhost:8080"

BLING_API_BASE = "https://www.bling.com.br/Api/v3"

# ==========================================
# DEPÓSITOS
# ==========================================

DEPOSITOS = {
    "TODOS": None,
    "EXPEDICAO": 10968231680,
    "ESTOQUE FRUTIFICA": 8443864433,
    "ESTOQUE ARMAZEM": 14886735791,
    "ESTOQUE PLASTICO": 14888296600,
    "COZINHA": 9057073796,
    "ESTOQUE ESCRITORIO": 14886696923,
    "ESTOQUE MANUTENCAO": 14886721328,
    "ESTOQUE MONTAGEM": 14887751954,
}

# ==========================================
# EMBALAGENS
# ==========================================

EMBALAGENS_CODIGOS = [
    "EMB108", "EMB109", "EMB110", "EMB111",
    "EMB112", "EMB113", "EMB114", "EMB115",
    "EMB116", "EMB_ETQ"
]

# Ordem de apresentação (prioridade)
EMBALAGENS_ORDEM = [
    "EMB116", "EMB115", "EMB109", "EMB108", "EMB110",
    "EMB111", "EMB112", "EMB113", "EMB114", "EMB_ETQ"
]

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
# FUNÇÕES DE ACESSO A CREDENCIAIS
# ==========================================

def get_bling_credentials() -> tuple:
    """Retorna (client_id, client_secret) do st.secrets. Falha explicitamente se ausente."""
    try:
        return st.secrets["bling"]["client_id"], st.secrets["bling"]["client_secret"]
    except (KeyError, FileNotFoundError) as e:
        raise RuntimeError(
            "Credenciais do Bling não configuradas. "
            "Defina [bling] client_id e client_secret em .streamlit/secrets.toml"
        ) from e


def get_spreadsheet_id() -> str:
    """Retorna o ID da planilha do st.secrets, com fallback para a constante SPREADSHEET_ID."""
    try:
        return st.secrets["sheets"]["spreadsheet_id"]
    except (KeyError, FileNotFoundError):
        return SPREADSHEET_ID


# ==========================================
# MOVIMENTAÇÃO
# ==========================================

TIPOS_MOVIMENTACAO = ["Consumo", "Entrada"]
CANAIS = ["I9", "Montagem", "Estoque"]


# ==========================================
# CALENDÁRIO 2026
# ==========================================

FERIADOS_2026 = [
    "2026-04-03", "2026-04-21", "2026-05-01", "2026-06-04",
    "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-15",
    "2026-11-20", "2026-12-25",
]

MESES_NUM = {
    "Abril 2026": "04", "Maio 2026": "05", "Junho 2026": "06",
    "Julho 2026": "07", "Agosto 2026": "08", "Setembro 2026