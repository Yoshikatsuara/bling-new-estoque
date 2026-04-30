"""
Página: Controle de Saldo.

Regra: Saldo Atual = Saldo Inicial - Σ Consumo + Σ Entrada
Layout:
  - Pivot de saldo diário (acumulado) no topo
  - Tabela resumo por embalagem
  - Extrato de movimentações
  - Configuração de saldo inicial no rodapé
"""

from datetime import date, datetime

import pandas as pd
import streamlit as st

from core import sheets
from core.config import (
    ALERTA_ESTOQUE_BAIXO,
    CANAIS,
    EMBALAGENS_LABELS,
    EMBALAGENS_ORDEM,
)
from core.dados import (
    calcular_saldo_atual,
    calcular_saldo_diario,
    carregar_controle_estoque,
    carregar_saldos_iniciais,
    gerar_extrato,
    salvar_saldos_iniciais,
)
from core.style import (
    aplicar_css,
    render_empty_state,
    render_header,
    render_metric,
    render_sidebar_header,
)

# ==========================================
# SETUP
# ==========================================

st.set_page_config(page_title="Saldo · Frutifica", page_icon="💰", layout="wide")
aplicar_css()

# ==========================================
# SIDEBAR
# ==========================================

render_sidebar_header("💰 Controle de Saldo", "Frutifica · Embalagens")

with st.sidebar:
    atualizar = st.button("🔄 Atualizar dados", use_container_width=True)

    st.divider()

    st.markdown("**Canal**")
    canal_sel = st.selectbox(
        "Canal",
        options=["Todos"] + CANAIS,
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("**Alerta estoque baixo**")
    alerta_limite = st.number_input(
        "Limite (un.)",
        min_value=0,
        value=ALERTA_ESTOQUE_BAIXO,
        step=100,
        label_visibility="collapsed",
    )

if atualizar:
    sheets.invalidar_cache()
    st.cache_data.clear()

# Filtro de canal (None = todos)
filtro_canal = canal_sel if canal_sel != "Todos" else None

# ==========================================
# DADOS
# ==========================================

with st.spinner("Carregando..."):
    df_ini = carregar_saldos_iniciais()
    df_estoque = carregar_controle_estoque()

# ==========================================
# HEADER
# ==========================================

render_header(
    "💰 Controle de Saldo",
    "Saldo Inicial − Consumo + Entradas = Saldo Atual",
)

if df_ini.empty or df_ini["Saldo_Inicial"].sum() == 0:
    render_empty_state(
        "⚙️",
        "Nenhum saldo inicial definido. Role até o final da página para configurar.",
    )
else:
    # ==========================================
    # CÁLCULOS
    # ==========================================

    df_saldo = calcular_saldo_atual(df_estoque, filtro_canal)

    total_atual = int(df_saldo["Saldo_Atual"].sum())
    total_consumo = int(df_saldo["Total_Consumo"].sum())
    total_entrada = int(df_saldo["Total_Entrada"].sum())
    em_alerta = int((df_saldo["Saldo_Atual"] < alerta_limite).sum())

    # ==========================================
    # MÉTRICAS
    # ==========================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_metric(
            f"{total_atual:,}".replace(",", "."), "Saldo Atual Total"
        )
    with c2:
        render_metric(
            f"{total_consumo:,}".replace(",", "."),
            "Total Consumido",
            cor="#ef4444",
        )
    with c3:
        render_metric(
            f"{total_entrada:,}".replace(",", "."),
            "Total Entradas",
            cor="#38bdf8",
        )
    with c4:
        cor_alerta = "#ef4444" if em_alerta > 0 else "#4ade80"
        render_metric(em_alerta, "Em alerta", cor=cor_alerta)

    if canal_sel != "Todos":
        st.caption(f"📌 Filtrando por canal: **{canal_sel}**")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ==========================================
    # SALDO DIÁRIO (pivot acumulado)
    # ==========================================

    st.markdown(
        "<div class='section-title'>Saldo Diário por Embalagem</div>",
        unsafe_allow_html=True,
    )

    pivot_diario = calcular_saldo_diario(df_estoque, filtro_canal)

    if pivot_diario.empty:
        st.info("Nenhuma movimentação registrada para gerar saldo diário.")
    else:
        # Adicionar coluna de saldo inicial no início
        saldos_ini_map = dict(
            zip(df_ini["Codigo"], df_ini["Saldo_Inicial"])
        )
        col_ini = [
            int(saldos_ini_map.get(cod, 0)) for cod in EMBALAGENS_ORDEM
        ]
        pivot_diario.insert(0, "Saldo Ini.", col_ini)

        st.dataframe(
            pivot_diario.style.format("{:,.0f}").background_gradient(
                cmap="RdYlGn",
                axis=None,
                subset=pivot_diario.columns[1:],
            ),
            use_container_width=True,
            height=440,
        )

    st.divider()

    # ==========================================
    # TABELA RESUMO
    # ==========================================

    st.markdown(
        "<div class='section-title'>Resumo por Embalagem</div>",
        unsafe_allow_html=True,
    )

    df_view = df_saldo.copy()
    df_view["Embalagem"] = df_view["Codigo"].map(
        lambda c: EMBALAGENS_LABELS.get(c, c)
    )
    df_view["Status"] = df_view["Saldo_Atual"].apply(
        lambda s: "🔴 BAIXO" if s < alerta_limite else "🟢 OK"
    )
    df_view = df_view[
        [
            "Embalagem",
            "Saldo_Inicial",
            "Total_Consumo",
            "Total_Entrada",
            "Saldo_Atual",
            "Status",
        ]
    ]
    df_view.columns = [
        "Embalagem",
        "Saldo Inicial",
        "Consumo",
        "Entradas",
        "Saldo Atual",
        "Status",
    ]

    st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True,
        height=440,
    )

    # ==========================================
    # EXTRATO
    # ==========================================

    if not df_estoque.empty:
        with st.expander("📋 Extrato de Movimentações"):
            df_extrato = gerar_extrato(df_estoque, filtro_canal)

            if df_extrato.empty:
                st.info("Nenhuma movimentação registrada.")
            else:
                emb_filtro = st.selectbox(
                    "Filtrar por embalagem",
                    options=["Todas"] + EMBALAGENS_ORDEM,
                    format_func=lambda c: (
                        "Todas"
                        if c == "Todas"
                        else EMBALAGENS_LABELS.get(c, c)
                    ),
                )

                if emb_filtro != "Todas":
                    df_extrato = df_extrato[
                        df_extrato["Codigo"] == emb_filtro
                    ]

                df_ext_view = df_extrato.copy()
                df_ext_view["Data"] = df_ext_view["Data"].dt.strftime(
                    "%d/%m/%Y"
                )
                df_ext_view["Impacto"] = df_ext_view.apply(
                    lambda r: (
                        f"🔴 -{r['Quantidade']:,}".replace(",", ".")
                        if r["Tipo"].lower() == "consumo"
                        else f"🔵 +{r['Quantidade']:,}".replace(",", ".")
                    ),
                    axis=1,
                )

                st.dataframe(
                    df_ext_view[
                        [
                            "Data",
                            "Embalagem",
                            "Tipo",
                            "Canal",
                            "Impacto",
                            "Saldo_Acumulado",
                        ]
                    ].rename(columns={"Saldo_Acumulado": "Saldo Após"}),
                    use_container_width=True,
                    hide_index=True,
                    height=400,
                )

    # ==========================================
    # ALERTAS
    # ==========================================

    if em_alerta > 0:
        st.markdown(
            "<div class='section-title'>⚠️ Embalagens em Alerta</div>",
            unsafe_allow_html=True,
        )

        alertas = df_saldo[df_saldo["Saldo_Atual"] < alerta_limite]
        cols = st.columns(min(len(alertas), 4))

        for i, (_, row) in enumerate(alertas.iterrows()):
            with cols[i % len(cols)]:
                label = EMBALAGENS_LABELS.get(
                    row["Codigo"], row["Codigo"]
                ).split(":")[0]
                render_metric(
                    f"{int(row['Saldo_Atual']):,}".replace(",", "."),
                    label,
                    cor="#ef4444",
                )


# ==========================================
# RODAPÉ: CONFIGURAÇÃO DE SALDO INICIAL
# ==========================================

st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
st.divider()

with st.expander("⚙️ Reconfigurar Saldo Inicial", expanded=False):
    st.caption(
        "Defina o saldo inicial de referência e a data base. "
        "Todas as movimentações do Controle_Estoque serão calculadas "
        "a partir desse valor."
    )

    df_ini_config = carregar_saldos_iniciais()

    saldos_atuais = (
        dict(zip(df_ini_config["Codigo"], df_ini_config["Saldo_Inicial"]))
        if not df_ini_config.empty
        else {}
    )

    # Data base atual
    datas_base_validas = (
        df_ini_config["Data_Base"].dropna()
        if not df_ini_config.empty and "Data_Base" in df_ini_config.columns
        else pd.Series(dtype="datetime64[ns]")
    )

    if not datas_base_validas.empty:
        data_base_default = datas_base_validas.max().date()
    else:
        data_base_default = date(2026, 4, 17)

    data_base = st.date_input(
        "📅 Data do saldo inicial",
        value=data_base_default,
        format="DD/MM/YYYY",
    )
    st.caption(
        "Data de referência do saldo (ex: data do inventário ou início do controle)."
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.form("form_saldo_inicial"):
        saldos_novos = {}
        cols = st.columns(2)

        for i, codigo in enumerate(EMBALAGENS_ORDEM):
            label = EMBALAGENS_LABELS.get(codigo, codigo)
            with cols[i % 2]:
                saldos_novos[codigo] = st.number_input(
                    label,
                    min_value=0,
                    value=int(saldos_atuais.get(codigo, 0)),
                    step=100,
                    key=f"si_{codigo}",
                )

        st.markdown(
            "<div style='height:8px'></div>", unsafe_allow_html=True
        )
        st.divider()

        submitted = st.form_submit_button(
            "💾 Salvar Saldo Inicial", type="primary"
        )

    if submitted:
        with st.spinner("Salvando na aba Saldo_Inicial..."):
            resultado = salvar_saldos_iniciais(
                saldos=saldos_novos, data_base=data_base
            )

        if resultado == "success":
            st.markdown(
                "<div class='success-box'>✅ Saldo inicial salvo!</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='error-box'>⛔ {resultado}</div>",
                unsafe_allow_html=True,
            )