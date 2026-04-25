"""
Página: Registrar Movimentação.
Lança consumo ou entrada manual de embalagens no Google Sheets.
Em fases futuras: dispara baixa no Bling via API.
"""

from datetime import datetime

import streamlit as st

from core import sheets
from core.config import (
    ABA_MOVIMENTACOES,
    CANAIS,
    EMBALAGENS_CODIGOS,
    TIPOS_MOVIMENTACAO,
)
from core.helpers import agora_br, semana_do_mes
from core.style import render_header
from utils.theme import aplicar_tema

# ==========================================
# SETUP
# ==========================================

st.set_page_config(page_title="Movimentação · Frutifica", page_icon="📋", layout="wide")
aplicar_tema()

CABECALHO_MOVIMENTACOES = [
    "Carimbo de data/hora",
    "Data da Movimentação",
    "Tipo de Movimentação",
    "Embalagem (Produto)",
    "Quantidade Movimentada (Unidades)",
    "Conversor Quantidade (Número)",
    "Canal",
    "Semana do Mês",
    "Observações",
]

# ==========================================
# FUNÇÕES
# ==========================================

def checar_duplicata(registros: list, data_str: str, embalagem: str, tipo: str) -> bool:
    for r in registros:
        if (
            str(r.get("Data da Movimentação", "")).strip() == data_str
            and str(r.get("Embalagem (Produto)", "")).strip() == embalagem
            and str(r.get("Tipo de Movimentação", "")).strip() == tipo
        ):
            return True
    return False


def registrar_movimentacoes(linhas: list) -> dict:
    try:
        aba = sheets.get_aba(
            ABA_MOVIMENTACOES,
            criar_se_nao_existir=True,
            cabecalho=CABECALHO_MOVIMENTACOES,
        )
        registros = aba.get_all_records()
        resultados = []

        for dados in linhas:
            duplicata = checar_duplicata(
                registros,
                dados["data_movimentacao"],
                dados["embalagem"],
                dados["tipo"],
            )
            if duplicata:
                resultados.append({"embalagem": dados["embalagem"], "status": "duplicata"})
                continue

            linha = [
                dados["carimbo"],
                dados["data_movimentacao"],
                dados["tipo"],
                dados["embalagem"],
                dados["quantidade"],
                dados["quantidade"],  # Conversor Quantidade = mesmo valor por enquanto
                dados["canal"],
                dados["semana"],
                dados["observacoes"],
            ]
            aba.append_row(linha, value_input_option="RAW")
            resultados.append({"embalagem": dados["embalagem"], "status": "ok"})

        sheets.invalidar_cache()
        return {"sucesso": True, "resultados": resultados}

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


# ==========================================
# INTERFACE
# ==========================================

render_header("📋 Registrar Movimentação", "Consumo e entrada manual de embalagens · Frutifica")

col_left, col_center, col_right = st.columns([1, 2.5, 1])

with col_center:
    # Tipo
    tipo = st.radio("Tipo de Movimentação", options=TIPOS_MOVIMENTACAO, horizontal=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Data
    data_mov = st.date_input("Data da Movimentação", value=datetime.today())

    # Embalagens (multiselect)
    embalagens_sel = st.multiselect(
        "Embalagem (Produto)",
        options=EMBALAGENS_CODIGOS,
        placeholder="Selecione uma ou mais embalagens...",
    )

    # Quantidades por embalagem
    quantidades = {}
    if embalagens_sel:
        st.markdown(
            "<div style='font-size:0.75rem;color:#6b7280;text-transform:uppercase;"
            "letter-spacing:0.08em;margin-top:8px;margin-bottom:4px'>"
            "Quantidade por Embalagem</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(min(len(embalagens_sel), 5))
        for i, emb in enumerate(embalagens_sel):
            with cols[i % 5]:
                quantidades[emb] = st.number_input(
                    emb,
                    min_value=1,
                    step=1,
                    value=1,
                    key=f"qty_{emb}",
                )

    with st.form("form_movimentacao", clear_on_submit=False):
        # Canal
        canal = st.selectbox("Canal", options=CANAIS)

        # Observações
        observacoes = st.text_area(
            "Observações (Opcional)",
            placeholder="Ex: NF 00123, OS referência, ajuste de inventário...",
            height=90,
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.divider()

        submitted = st.form_submit_button("✅ Registrar Movimentação", type="primary")

    # --- Feedback ---
    if submitted:
        if not embalagens_sel:
            st.markdown(
                "<div class='warn-box'>⚠️ Selecione pelo menos uma embalagem.</div>",
                unsafe_allow_html=True,
            )
        else:
            semana = semana_do_mes(data_mov)
            carimbo = agora_br()

            linhas = [
                {
                    "carimbo": carimbo,
                    "data_movimentacao": data_mov.strftime("%d/%m/%Y"),
                    "tipo": tipo,
                    "embalagem": emb,
                    "quantidade": int(quantidades[emb]),
                    "canal": canal,
                    "semana": semana,
                    "observacoes": observacoes.strip() if observacoes else "",
                }
                for emb in embalagens_sel
            ]

            with st.spinner("Registrando na planilha..."):
                resultado = registrar_movimentacoes(linhas)

            if not resultado["sucesso"]:
                st.markdown(
                    f"""
                <div class='error-box'>
                    ⛔ Erro de conexão com o Sheets.<br>
                    <span style='font-size:0.75rem;opacity:0.7'>{resultado.get('erro')}</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                for r in resultado["resultados"]:
                    if r["status"] == "ok":
                        qty = quantidades[r["embalagem"]]
                        st.markdown(
                            f"""
                        <div class='success-box'>
                            ✅ <strong>{r['embalagem']}</strong> — {int(qty)} un. registrada!
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"""
                        <div class='warn-box'>
                            ⚠️ <strong>{r['embalagem']}</strong> já registrada para essa data e tipo. Pulada.
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
