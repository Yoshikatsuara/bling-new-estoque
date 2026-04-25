"""
Página: Consulta de Estoque.
Upload do relatório Bling (CSV/XLSX) como fonte de verdade.
Data extraída automaticamente do nome do arquivo.
"""

import re
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st

from core import sheets
from core.config import ABA_CONTROLE_ESTOQUE, EMBALAGENS_CODIGOS
from core.style import (
    aplicar_css,
    render_empty_state,
    render_header,
    render_metric,
    render_sidebar_header,
)

st.set_page_config(page_title="Estoque · Frutifica", page_icon="📦", layout="wide")
aplicar_css()

EMBALAGENS_DEFAULT = [f"EMB{i}" for i in range(108, 117)]


# ==========================================
# HELPERS
# ==========================================

def extrair_data_do_nome(nome_arquivo: str):
    match = re.search(r"(\d{2})[_-](\d{2})[_-](\d{4})", nome_arquivo)
    if not match:
        return None
    try:
        dia, mes, ano = match.groups()
        return datetime(int(ano), int(mes), int(dia)).date()
    except ValueError:
        return None


def parse_numero_br(valor) -> float:
    if pd.isna(valor):
        return 0.0

    s = str(valor).strip().replace(".", "").replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return 0.0


def processar_csv_bling(arquivo, codigos_filtro: list) -> list:
    nome = arquivo.name.lower()

    # --- leitura por tipo ---
    if nome.endswith(".csv"):
        try:
            df = pd.read_csv(
                arquivo,
                sep=None,
                engine="python",
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            arquivo.seek(0)
            df = pd.read_csv(
                arquivo,
                sep=None,
                engine="python",
                encoding="latin1"
            )

    elif nome.endswith(".xlsx") or nome.endswith(".xls"):
        df = pd.read_excel(arquivo)

    else:
        raise ValueError("Formato de arquivo não suportado. Use CSV, XLSX ou XLS.")

    # --- normalizar colunas ---
    df.columns = df.columns.str.strip()

    # --- padronizar nomes ---
    mapa = {
        "Código": "Código",
        "Codigo": "Código",
        "Produto": "Produto",
        "Descrição": "Produto",
        "Descricao": "Produto",
        "Unidade": "Unidade",
        "Quantidade": "Quantidade",
        "Saldo": "Quantidade",
        "Qtd": "Quantidade",
    }

    df.rename(columns={c: mapa.get(c, c) for c in df.columns}, inplace=True)

    # --- validação ---
    obrigatorias = ["Código", "Produto", "Unidade", "Quantidade"]

    for col in obrigatorias:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória não encontrada: {col}")

    # --- limpeza ---
    df["Código"] = df["Código"].astype(str).str.strip()
    df["Quantidade"] = df["Quantidade"].apply(parse_numero_br)

    # --- filtro ---
    df = df[df["Código"].isin(codigos_filtro)].copy()

    return df[["Código", "Produto", "Unidade", "Quantidade"]].to_dict("records")


def montar_linhas(registros: list, data_relatorio) -> list:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    linhas = []

    for r in registros:
        linhas.append({
            "Codigo": r.get("Código", ""),
            "Descricao": r.get("Produto", ""),
            "Unidade": r.get("Unidade", ""),
            "Saldo": r.get("Quantidade", 0),
            "Data Relatorio": data_relatorio.strftime("%d/%m/%Y"),
            "Atualizado em": agora,
        })

    return linhas


CAMPOS_COMPARACAO = ["Codigo", "Descricao", "Saldo", "Data Relatorio"]


def _normalizar(linha: dict) -> tuple:
    return tuple(str(linha.get(c, "")).strip() for c in CAMPOS_COMPARACAO)


def exportar_sheets(linhas: list, data_relatorio_str: str) -> str:
    try:
        aba = sheets.get_aba(ABA_CONTROLE_ESTOQUE)
        dados_existentes = aba.get_all_records()

    except gspread.exceptions.WorksheetNotFound:
        aba = sheets.get_aba(
            ABA_CONTROLE_ESTOQUE,
            criar_se_nao_existir=True,
            cabecalho=list(linhas[0].keys()),
            rows=5000,
            cols=15,
        )
        dados_existentes = []

    registros_da_data = [
        row for row in dados_existentes
        if str(row.get("Data Relatorio", "")).strip() == data_relatorio_str
    ]

    if registros_da_data:
        existentes_norm = sorted(_normalizar(r) for r in registros_da_data)
        novas_norm = sorted(_normalizar(r) for r in linhas)

        if existentes_norm == novas_norm:
            return "duplicate"

        return "date_conflict"

    if not dados_existentes:
        aba.append_row(list(linhas[0].keys()), value_input_option="RAW")

    aba.append_rows([list(l.values()) for l in linhas], value_input_option="RAW")
    sheets.invalidar_cache()

    return "success"


def formatar_numero(n) -> str:
    if isinstance(n, float) and n != int(n):
        return f"{n:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{int(n):,}".replace(",", ".")


# ==========================================
# SIDEBAR
# ==========================================

render_sidebar_header("📦 Consulta de Estoque", "Frutifica · Relatório Bling")

with st.sidebar:
    st.markdown("**Relatório Bling (CSV/XLSX)**")

    arquivo_csv = st.file_uploader(
        "Upload",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed",
    )

    st.markdown("**Embalagens**")

    embalagens_sel = st.multiselect(
        "Selecione",
        options=EMBALAGENS_CODIGOS,
        default=EMBALAGENS_DEFAULT,
        placeholder="Digite para buscar",
        label_visibility="collapsed"
    )

    st.divider()

    salvar_historico = st.checkbox("Salvar histórico no Sheets", value=True)


# ==========================================
# MAIN
# ==========================================

render_header(
    "Relatório de Saldos em Estoque",
    "Fonte: Relatório oficial Bling"
)

if not arquivo_csv:
    render_empty_state("📥", "Faça upload do relatório na sidebar")
    st.stop()

if not embalagens_sel:
    st.warning("Selecione pelo menos uma embalagem.")
    st.stop()

data_relatorio = extrair_data_do_nome(arquivo_csv.name)

if not data_relatorio:
    st.error(f"❌ Nome do arquivo inválido: {arquivo_csv.name}")
    st.stop()

# --- processamento ---
try:
    registros = processar_csv_bling(arquivo_csv, embalagens_sel)

except Exception as e:
    st.error(f"❌ Erro ao ler arquivo: {e}")
    st.stop()

if not registros:
    st.warning("Nenhum código encontrado no arquivo.")
    st.stop()

linhas = montar_linhas(registros, data_relatorio)

st.caption(
    f"📄 {arquivo_csv.name} · {data_relatorio.strftime('%d/%m/%Y')}"
)

# --- métricas ---
total_saldo = sum(l.get("Saldo", 0) for l in linhas)
zerados = sum(1 for l in linhas if l.get("Saldo", 0) == 0)

c1, c2, c3 = st.columns(3)

with c1:
    render_metric(len(linhas), "Produtos")

with c2:
    render_metric(formatar_numero(total_saldo), "Saldo Total")

with c3:
    cor = "#ef4444" if zerados > 0 else "#4ade80"
    render_metric(zerados, "Zerados", cor=cor)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# --- tabela ---
HEADERS_EXIBICAO = {
    "Data Relatorio": "Data do Relatório",
    "Atualizado em": "Atualizado em",
}

linhas_exibicao = [
    {HEADERS_EXIBICAO.get(k, k): v for k, v in l.items()} for l in linhas
]

st.dataframe(linhas_exibicao, use_container_width=True, height=420)

# --- sheets ---
if salvar_historico:
    data_str = data_relatorio.strftime("%d/%m/%Y")

    with st.spinner("Salvando no histórico..."):
        try:
            resultado = exportar_sheets(linhas, data_str)

        except Exception as e:
            st.error(f"❌ Erro ao salvar no Sheets: {e}")
            resultado = None

    if resultado == "success":
        st.success(f"✅ Histórico salvo — aba `{ABA_CONTROLE_ESTOQUE}`")

    elif resultado == "duplicate":
        st.info(f"ℹ️ Dados já existem para {data_str}")

    elif resultado == "date_conflict":
        st.warning(f"⚠️ Conflito de dados para {data_str}")