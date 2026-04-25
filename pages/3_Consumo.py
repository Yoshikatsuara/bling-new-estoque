"""
Página: Análise de Consumo.
Tabelas pivot diária e semanal + gráficos de tendência.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import sheets
from core.config import (
    ABA_MOVIMENTACOES,
    EMBALAGENS_LABELS,
    EMBALAGENS_ORDEM,
    MESES_NUM,
)
from core.helpers import gerar_dias_uteis, semana_label
from core.style import (
    render_empty_state,
    render_header,
    render_metric,
    render_sidebar_header,
)
from utils.theme import CORES, LAYOUT_PLOTLY, aplicar_tema

# ==========================================
# SETUP
# ==========================================

st.set_page_config(page_title="Consumo · Frutifica", page_icon="📉", layout="wide")
aplicar_tema()

# ==========================================
# ESTADO
# ==========================================

if "dias_extras" not in st.session_state:
    st.session_state["dias_extras"] = []

# ==========================================
# SIDEBAR
# ==========================================

render_sidebar_header("📉 Consumo", "Frutifica · I9")

with st.sidebar:
    atualizar = st.button("🔄 Atualizar dados", use_container_width=True)

    st.divider()
    st.markdown("**Filtrar por mês**")
    mes_sel = st.multiselect(
        "Meses",
        options=list(MESES_NUM.keys()),
        default=["Abril 2026"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Dias extras de reposição**")
    st.caption("Sábados/domingos trabalhados")
    dia_extra = st.date_input("Data", value=None, label_visibility="collapsed")
    if st.button("➕ Adicionar dia", use_container_width=True):
        if dia_extra and str(dia_extra) not in st.session_state["dias_extras"]:
            st.session_state["dias_extras"].append(str(dia_extra))
            st.success(f"{dia_extra.strftime('%d/%m/%Y')} adicionado!")

    if st.session_state["dias_extras"]:
        st.caption("Dias adicionados:")
        for d in st.session_state["dias_extras"]:
            st.caption(f"• {d}")

# ==========================================
# DADOS
# ==========================================

if atualizar:
    sheets.invalidar_cache()

with st.spinner("Carregando..."):
    df = sheets.ler_aba_como_df(ABA_MOVIMENTACOES)

# Preparação do DataFrame
if not df.empty:
    df["Data da Movimentação"] = pd.to_datetime(
        df["Data da Movimentação"], dayfirst=True, errors="coerce"
    )
    df["Quantidade Movimentada (Unidades)"] = pd.to_numeric(
        df["Quantidade Movimentada (Unidades)"], errors="coerce"
    ).fillna(0)
    df["Codigo"] = df["Embalagem (Produto)"].str.extract(r"^(EMB[^\s:]+)")

DIAS_UTEIS = gerar_dias_uteis(extras=st.session_state["dias_extras"])

# ==========================================
# PIVOTS
# ==========================================

def pivot_diario(df: pd.DataFrame, tipo: str = "Consumo") -> pd.DataFrame:
    df_t = df[df["Tipo de Movimentação"] == tipo].copy() if not df.empty else pd.DataFrame()
    if df_t.empty:
        pivot = pd.DataFrame(0, index=EMBALAGENS_ORDEM, columns=DIAS_UTEIS)
    else:
        pivot = df_t.pivot_table(
            index="Codigo",
            columns="Data da Movimentação",
            values="Quantidade Movimentada (Unidades)",
            aggfunc="sum",
            fill_value=0,
        )
        pivot = pivot.reindex(index=EMBALAGENS_ORDEM, columns=DIAS_UTEIS, fill_value=0)

    pivot.index = [EMBALAGENS_LABELS.get(e, e) for e in pivot.index]
    pivot.index.name = "Embalagem"
    pivot.columns = [d.strftime("%d/%m") for d in pivot.columns]
    pivot.insert(0, "TOTAL", pivot.sum(axis=1))
    return pivot


def pivot_semanal(df: pd.DataFrame, tipo: str = "Consumo") -> pd.DataFrame:
    semana_map = {d: semana_label(d) for d in DIAS_UTEIS}
    semanas_ord = list(dict.fromkeys(semana_map.values()))

    df_t = df[df["Tipo de Movimentação"] == tipo].copy() if not df.empty else pd.DataFrame()
    if df_t.empty:
        pivot = pd.DataFrame(0, index=EMBALAGENS_ORDEM, columns=semanas_ord)
    else:
        df_t["Semana"] = df_t["Data da Movimentação"].map(
            lambda d: semana_label(d) if pd.notna(d) else None
        )
        pivot = df_t.pivot_table(
            index="Codigo",
            columns="Semana",
            values="Quantidade Movimentada (Unidades)",
            aggfunc="sum",
            fill_value=0,
        )
        pivot = pivot.reindex(index=EMBALAGENS_ORDEM, columns=semanas_ord, fill_value=0)

    pivot.index = [EMBALAGENS_LABELS.get(e, e) for e in pivot.index]
    pivot.index.name = "Embalagem"
    pivot.insert(0, "TOTAL", pivot.sum(axis=1))
    return pivot


# ==========================================
# CONTEÚDO
# ==========================================

render_header("📉 Consumo de Embalagens", "Diário e semanal · Frutifica · I9")

if df.empty:
    render_empty_state("📭", "Nenhum dado na aba Movimentacoes.")
    st.stop()

df_consumo = df[df["Tipo de Movimentação"] == "Consumo"]

# --- Métricas ---
total = int(df_consumo["Quantidade Movimentada (Unidades)"].sum())
dias_n = df_consumo["Data da Movimentação"].nunique()
emb_top_cod = df_consumo.groupby("Codigo")["Quantidade Movimentada (Unidades)"].sum()
emb_top = (
    EMBALAGENS_LABELS.get(emb_top_cod.idxmax(), "—").split(":")[0]
    if not emb_top_cod.empty
    else "—"
)

c1, c2, c3 = st.columns(3)
with c1:
    render_metric(f"{total:,}".replace(",", "."), "Total consumido (un.)")
with c2:
    render_metric(str(dias_n), "Dias com lançamento")
with c3:
    render_metric(emb_top, "Mais consumida")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.divider()

# --- Consumo Diário ---
st.markdown("<div class='section-title'>Consumo Diário</div>", unsafe_allow_html=True)

pivot_d = pivot_diario(df)

if mes_sel:
    meses_filtro = [MESES_NUM[m] for m in mes_sel]
    cols_vis = ["TOTAL"] + [
        c for c in pivot_d.columns if c != "TOTAL" and c[3:5] in meses_filtro
    ]
    pivot_d_view = pivot_d[cols_vis]
else:
    pivot_d_view = pivot_d

st.dataframe(
    pivot_d_view.style.format("{:,.0f}").background_gradient(
        cmap="Greens", subset=pivot_d_view.columns[1:], axis=None
    ),
    use_container_width=True,
    height=420,
)

# --- Consumo Semanal ---
st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Consumo Semanal</div>", unsafe_allow_html=True)

pivot_s = pivot_semanal(df)

st.dataframe(
    pivot_s.style.format("{:,.0f}").background_gradient(
        cmap="Greens", subset=pivot_s.columns[1:], axis=None
    ),
    use_container_width=True,
    height=420,
)

# ==========================================
# GRÁFICOS
# ==========================================

st.divider()
st.markdown("<div class='section-title'>Visualizações</div>", unsafe_allow_html=True)

# Gráfico 1 — Barras empilhadas semanais
pivot_s_plot = pivot_semanal(df).drop(columns=["TOTAL"])
pivot_s_plot = pivot_s_plot.loc[:, (pivot_s_plot != 0).any(axis=0)]

if not pivot_s_plot.empty and pivot_s_plot.shape[1] > 0:
    fig1 = go.Figure()
    for i, emb in enumerate(pivot_s_plot.index):
        fig1.add_trace(
            go.Bar(
                name=emb.split(":")[0],
                x=pivot_s_plot.columns.tolist(),
                y=pivot_s_plot.loc[emb].tolist(),
                marker_color=CORES[i % len(CORES)],
            )
        )
    fig1.update_layout(
        **LAYOUT_PLOTLY,
        barmode="stack",
        title="Consumo Semanal por Embalagem",
        height=400,
    )
    st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2 — Total por embalagem (horizontal)
totais = df_consumo.groupby("Codigo")["Quantidade Movimentada (Unidades)"].sum()
totais = totais.reindex(EMBALAGENS_ORDEM, fill_value=0)
totais.index = [EMBALAGENS_LABELS.get(e, e).split(":")[0] for e in totais.index]
totais = totais[totais > 0].sort_values()

if not totais.empty:
    fig2 = go.Figure(
        go.Bar(
            x=totais.values,
            y=totais.index,
            orientation="h",
            marker_color="#4ade80",
            text=[f"{v:,}".replace(",", ".") for v in totais.values],
            textposition="outside",
            textfont=dict(color="#94a3b8", size=11),
        )
    )
    fig2.update_layout(
        **LAYOUT_PLOTLY,
        title="Total Consumido por Embalagem",
        height=380,
        margin=dict(l=20, r=80, t=40, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)

# Gráfico 3 — Linha temporal diária
if not df_consumo.empty:
    linha = (
        df_consumo.groupby("Data da Movimentação")["Quantidade Movimentada (Unidades)"]
        .sum()
        .reset_index()
    )
    linha.columns = ["Data", "Consumo"]
    fig3 = go.Figure(
        go.Scatter(
            x=linha["Data"],
            y=linha["Consumo"],
            mode="lines+markers",
            line=dict(color="#4ade80", width=2),
            marker=dict(size=6, color="#4ade80"),
            fill="tozeroy",
            fillcolor="rgba(74,222,128,0.08)",
        )
    )
    fig3.update_layout(**LAYOUT_PLOTLY, title="Consumo Diário Total", height=350)
    st.plotly_chart(fig3, use_container_width=True)
