"""
Página: Registrar Movimentação.
Upload do relatório XLSX do Bling → grava em Controle_Estoque com coluna Tipo e Canal.
Também permite lançamento manual.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from core import sheets
from core.bling_parser import extrair_data_do_nome, parsear_relatorio
from core.config import (
    ABA_CONTROLE_ESTOQUE,
    CABECALHO_CONTROLE_ESTOQUE,
    CANAIS,
    EMBALAGENS_LABELS,
    EMBALAGENS_ORDEM,
    TIPOS_MOVIMENTACAO,
)
from core.dados import carregar_ultimo_relatorio
from core.helpers import agora_br
from core.style import render_header, render_metric
from utils.theme import aplicar_tema

# ==========================================
# SETUP
# ==========================================

st.set_page_config(page_title="Movimentação · Frutifica", page_icon="📋", layout="wide")
aplicar_tema()


# ==========================================
# FUNÇÕES
# ==========================================


def gravar_relatorio(df_rel: pd.DataFrame, data_relatorio, tipo: str, canal: str) -> str:
    """
    Grava relatório na aba Controle_Estoque COM coluna Tipo e Canal.
    Returns: 'success' | 'duplicate' | 'error:...'
    """
    import gspread

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    data_str = data_relatorio.strftime("%d/%m/%Y")

    linhas = []
    for _, row in df_rel.iterrows():
        linhas.append([
            row["Codigo"],
            row.get("Descricao", ""),
            row.get("Unidade", ""),
            0,                       # Preco (R$)
            int(row["Quantidade"]),   # Estoque Fisico
            int(row["Quantidade"]),   # Estoque Virtual
            "Ativo",                 # Situacao
            tipo,                    # Tipo
            canal,                   # Canal  ← NOVO
            data_str,                # Data Relatorio
            agora,                   # Atualizado em
        ])

    try:
        aba = sheets.get_aba(
            ABA_CONTROLE_ESTOQUE,
            criar_se_nao_existir=True,
            cabecalho=CABECALHO_CONTROLE_ESTOQUE,
            rows=5000,
            cols=15,
        )
        existentes = aba.get_all_records()

        # Checa duplicata: mesma data E mesmo tipo
        ja_tem = any(
            str(r.get("Data Relatorio", "")).strip() == data_str
            and str(r.get("Tipo", "")).strip().lower() == tipo.lower()
            for r in existentes
        )
        if ja_tem:
            return "duplicate"

        if not existentes:
            aba.append_row(CABECALHO_CONTROLE_ESTOQUE, value_input_option="RAW")

        aba.append_rows(linhas, value_input_option="RAW")
        sheets.invalidar_cache()
        return "success"

    except Exception as e:
        return f"error:{e}"


def calcular_diferencas(
    df_anterior: pd.DataFrame, df_atual: pd.DataFrame, tipo: str
) -> pd.DataFrame:
    """
    Compara saldo anterior com atual.
    Consumo: Anterior - Atual (queda = consumo)
    Entrada: Atual - Anterior (subida = entrada)
    """
    df_ant = df_anterior.rename(columns={"Estoque Fisico": "Saldo_Anterior"})
    df_atu = df_atual[["Codigo", "Quantidade"]].rename(
        columns={"Quantidade": "Saldo_Atual"}
    )

    merged = pd.merge(df_ant, df_atu, on="Codigo", how="outer").fillna(0)
    merged["Saldo_Anterior"] = merged["Saldo_Anterior"].astype(int)
    merged["Saldo_Atual"] = merged["Saldo_Atual"].astype(int)

    if tipo.lower() == "consumo":
        merged["Movimento"] = merged["Saldo_Anterior"] - merged["Saldo_Atual"]
    else:
        merged["Movimento"] = merged["Saldo_Atual"] - merged["Saldo_Anterior"]

    ordem_map = {c: i for i, c in enumerate(EMBALAGENS_ORDEM)}
    merged["_ordem"] = merged["Codigo"].map(ordem_map).fillna(99)
    merged = merged.sort_values("_ordem").drop(columns=["_ordem"]).reset_index(drop=True)

    return merged


# ==========================================
# INTERFACE
# ==========================================

render_header("📋 Registrar Movimentação", "Upload de relatório Bling · Frutifica")

modo = st.radio(
    "Como deseja registrar?",
    ["📂 Upload de relatório Bling", "✏️ Lançamento manual"],
    horizontal=True,
)

st.divider()

# ==========================================
# MODO 1: UPLOAD DO RELATÓRIO BLING
# ==========================================

if "Upload" in modo:

    tipo_upload = st.radio(
        "Este arquivo deve ser registrado como:",
        TIPOS_MOVIMENTACAO,
        horizontal=True,
        key="tipo_upload",
        help="Consumo = saída de embalagens. Entrada = recebimento.",
    )

    st.divider()

    uploaded = st.file_uploader(
        "Relatório do Bling",
        type=["xlsx", "xls", "csv"],
        help="Arquivo de saldo exportado do Bling (Excel ou CSV)",
    )

    if not uploaded:
        st.markdown(
            "<div class='empty-state'>"
            "<div style='font-size:2.5rem;margin-bottom:12px'>📂</div>"
            "<div style='color:#94a3b8;font-size:0.95rem'>"
            "Escolha Consumo ou Entrada e suba o relatório XLSX do Bling."
            "</div></div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # Parse
    with st.spinner("Parseando relatório..."):
        df_parsed = parsear_relatorio(uploaded)

    if df_parsed.empty:
        st.error("❌ Nenhuma embalagem de interesse encontrada no arquivo.")
        st.stop()

    # Configuração
    st.markdown("<div class='section-title'>Configuração</div>", unsafe_allow_html=True)

    data_detectada = extrair_data_do_nome(uploaded.name)

    col1, col2 = st.columns(2)
    with col1:
        data_relatorio = st.date_input(
            "Data deste relatório",
            value=data_detectada if data_detectada else datetime.today(),
            help=(
                "Detectada do nome do arquivo"
                if data_detectada
                else "Informe a data manualmente"
            ),
        )
        if data_detectada:
            st.caption(
                f"📅 Data detectada do arquivo: {data_detectada.strftime('%d/%m/%Y')}"
            )
    with col2:
        canal_upload = st.selectbox("Canal", options=CANAIS, key="canal_upload")

    st.divider()

    # Preview saldos
    st.markdown(
        "<div class='section-title'>Saldos Importados</div>", unsafe_allow_html=True
    )

    total_saldo = int(df_parsed["Quantidade"].sum())
    c1, c2 = st.columns(2)
    with c1:
        render_metric(len(df_parsed), "Embalagens encontradas")
    with c2:
        render_metric(f"{total_saldo:,}".replace(",", "."), "Saldo total (un.)")

    df_display = df_parsed.copy()
    df_display["Embalagem"] = df_display["Codigo"].map(
        lambda c: EMBALAGENS_LABELS.get(c, c)
    )
    st.dataframe(
        df_display[["Embalagem", "Quantidade"]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # Comparação com anterior (mesmo tipo)
    st.markdown(
        "<div class='section-title'>Comparação com Relatório Anterior</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Buscando último relatório no Sheets..."):
        df_anterior, data_anterior = carregar_ultimo_relatorio()

    if df_anterior.empty or data_anterior is None:
        st.info("ℹ️ Nenhum relatório anterior encontrado. Este será a referência inicial.")

        if st.button("📥 Gravar como Referência Inicial", type="primary"):
            with st.spinner("Gravando..."):
                res = gravar_relatorio(df_parsed, data_relatorio, tipo_upload, canal_upload)
            if res == "success":
                st.markdown(
                    "<div class='success-box'>✅ Relatório gravado como referência!</div>",
                    unsafe_allow_html=True,
                )
            elif res == "duplicate":
                st.markdown(
                    f"<div class='warn-box'>⚠️ Já existe relatório de {tipo_upload} para {data_relatorio.strftime('%d/%m/%Y')}.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='error-box'>⛔ {res}</div>",
                    unsafe_allow_html=True,
                )
        st.stop()

    # Tem anterior → comparar
    st.caption(f"Último relatório: **{data_anterior.strftime('%d/%m/%Y')}**")
    diferencas = calcular_diferencas(df_anterior, df_parsed, tipo_upload)

    movimentos = diferencas[diferencas["Movimento"] > 0].copy()
    ignorados = diferencas[diferencas["Movimento"] <= 0].copy()
    total_movimento = int(movimentos["Movimento"].sum()) if not movimentos.empty else 0

    formula = (
        "Saldo anterior − Saldo atual"
        if tipo_upload.lower() == "consumo"
        else "Saldo atual − Saldo anterior"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric(tipo_upload, "Tipo escolhido")
    with c2:
        render_metric(
            f"{total_movimento:,}".replace(",", "."),
            f"Total {tipo_upload.lower()} (un.)",
        )
    with c3:
        render_metric(len(ignorados), "Sem movimento para este tipo")

    st.caption(f"Regra: **{formula}**. Apenas valores > 0 são relevantes.")

    # Tabela de diferenças
    df_diff = diferencas.copy()
    df_diff["Embalagem"] = df_diff["Codigo"].map(
        lambda c: EMBALAGENS_LABELS.get(c, c)
    )
    df_diff["Status"] = df_diff["Movimento"].apply(
        lambda m: f"✅ {tipo_upload}" if m > 0 else "⚪ Sem movimento"
    )
    st.dataframe(
        df_diff[
            ["Embalagem", "Saldo_Anterior", "Saldo_Atual", "Movimento", "Status"]
        ].rename(
            columns={
                "Saldo_Anterior": "Saldo Anterior",
                "Saldo_Atual": "Saldo Atual",
                "Movimento": f"Qtd {tipo_upload}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # Gravar
    st.caption(
        f"Ao clicar: grava relatório em Controle_Estoque com Tipo = {tipo_upload}, Canal = {canal_upload}"
    )

    if st.button(f"✅ Gravar Relatório ({tipo_upload})", type="primary"):
        with st.spinner("Gravando..."):
            res = gravar_relatorio(df_parsed, data_relatorio, tipo_upload, canal_upload)

        if res == "success":
            st.markdown(
                "<div class='success-box'>✅ Relatório gravado com sucesso!</div>",
                unsafe_allow_html=True,
            )
        elif res == "duplicate":
            st.markdown(
                f"<div class='warn-box'>⚠️ Relatório de {tipo_upload} para {data_relatorio.strftime('%d/%m/%Y')} já existe.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='error-box'>⛔ {res}</div>",
                unsafe_allow_html=True,
            )


# ==========================================
# MODO 2: LANÇAMENTO MANUAL
# ==========================================

elif "manual" in modo:

    col_left, col_center, col_right = st.columns([1, 2.5, 1])

    with col_center:
        tipo = st.radio(
            "Tipo de Movimentação", options=TIPOS_MOVIMENTACAO, horizontal=True
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        data_mov = st.date_input("Data da Movimentação", value=datetime.today())

        canal_manual = st.selectbox("Canal", options=CANAIS, key="canal_manual")

        embalagens_sel = st.multiselect(
            "Embalagem (Produto)",
            options=EMBALAGENS_ORDEM,
            format_func=lambda c: EMBALAGENS_LABELS.get(c, c),
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
            cols = st.columns(min(len(embalagens_sel), 3))
            for i, emb in enumerate(embalagens_sel):
                with cols[i % len(cols)]:
                    quantidades[emb] = st.number_input(
                        EMBALAGENS_LABELS.get(emb, emb).split(":")[0],
                        min_value=1,
                        step=100,
                        value=100,
                        key=f"qty_{emb}",
                    )

        observacoes = st.text_area(
            "Observações (Opcional)",
            placeholder="Ex: contagem física, ajuste, NF...",
            height=90,
        )

        st.divider()

        if st.button("✅ Registrar Movimentação", type="primary"):
            if not embalagens_sel:
                st.warning("Selecione pelo menos uma embalagem.")
            else:
                agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                data_str = data_mov.strftime("%d/%m/%Y")

                linhas = []
                for emb in embalagens_sel:
                    qtd = int(quantidades.get(emb, 1))
                    linhas.append([
                        emb,
                        EMBALAGENS_LABELS.get(emb, emb).split(": ", 1)[-1],
                        "UN",
                        0,              # Preco
                        qtd,            # Estoque Fisico
                        qtd,            # Estoque Virtual
                        "Ativo",        # Situacao
                        tipo,           # Tipo
                        canal_manual,   # Canal  ← NOVO
                        data_str,       # Data Relatorio
                        agora,          # Atualizado em
                    ])

                try:
                    aba = sheets.get_aba(
                        ABA_CONTROLE_ESTOQUE,
                        criar_se_nao_existir=True,
                        cabecalho=CABECALHO_CONTROLE_ESTOQUE,
                        rows=5000,
                        cols=15,
                    )
                    aba.append_rows(linhas, value_input_option="RAW")
                    sheets.invalidar_cache()

                    for emb in embalagens_sel:
                        label = EMBALAGENS_LABELS.get(emb, emb)
                        st.markdown(
                            f"<div class='success-box'>✅ <strong>{label}</strong> — "
                            f"{quantidades[emb]:,} un. registrada como {tipo}!</div>".replace(",", "."),
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.markdown(
                        f"<div class='error-box'>⛔ Erro: {e}</div>",
                        unsafe_allow_html=True,
                    )