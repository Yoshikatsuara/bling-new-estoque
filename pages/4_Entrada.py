"""
Página: Entrada de Embalagens.
Pivots diário e semanal + gráficos.

Fonte de dados: core/dados.py → Controle_Estoque (Tipo = Entrada)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import sheets
from core.config import EMBALAGENS_LABELS, EMBALAGENS_ORDEM, MESES_NUM
from core.dados import calcular_movimentacoes, carregar_controle_estoque
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

st.set_page_config(page_title="Entrada · Frutifica", page_icon="📦", layout="wide")
aplicar_tema()

TIPO = "Entrada"
COR_PRINCIPAL = "#38bdf8"
CMAP = "Blues"

# ==========================================
# ESTADO
# ==========================================

if "dias_extras" not in st.session_state:
    st.session_state["dias_extras"] = []

# ==========================================
# SIDEBAR
# ==========================================

render_sidebar_header("📦 Entrada", "Frutifica · I9")

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
    df_estoque = carregar_controle_estoque()
    df_mov = calcular_movimentacoes(df_estoque, TIPO)

DIAS_UTEIS = gerar_dias_uteis(extras=st.session_state["dias_extras"])


# ==========================================
# PIVOTS
# ==========================================


def pivot_diario(df_mov: pd.DataFrame) -> pd.DataFrame:
    if df_mov.empty:
        pivot = pd.DataFrame(0, index=EMBALAGENS_ORDEM, columns=[])
    else:
        df_t = df_mov.copy()
        df_t["Data"] = df_t["Data"].dt.normalize()

        dias_uteis_set = set(pd.DatetimeIndex(DIAS_UTEIS).normalize())
        datas_validas = sorted(
            d for d in df_t["Data"].dropna().unique() if d in dias_uteis_set
        )

        pivot = df_t.pivot_table(
            index="Codigo",
            columns="Data",
            values="Quantidade",
            aggfunc="sum",
            fill_value=0,
        )
        pivot = pivot.reindex(
            index=EMBALAGENS_ORDEM, columns=datas_validas, fill_value=0
        )

    pivot.index = [EMBALAGENS_LABELS.get(e, e) for e in pivot.index]
    pivot.index.name = "Embalagem"
    pivot.columns = [pd.Timestamp(d).strftime("%d/%m") for d in pivot.columns]
    pivot.insert(0, "TOTAL", pivot.sum(axis=1))
    return pivot


def pivot_semanal(df_mov: pd.DataFrame) -> pd.DataFrame:
    semana_map = {d: semana_label(d) for d in DIAS_UTEIS}
    semanas_ord = list(dict.fromkeys(semana_map.values()))

    if df_mov.empty:
        pivot = pd.DataFrame(0, index=EMBALAGENS_ORDEM, columns=semanas_ord)
    else:
        df_t = df_mov.copy()
        df_t["Semana"] = df_t["Data"].map(
            lambda d: semana_label(d) if pd.notna(d) else None
        )
        pivot = df_t.pivot_table(
            index="Codigo",
            columns="Semana",
            values="Quantidade",
            aggfunc="sum",
            fill_value=0,
        )
        pivot = pivot.reindex(
            index=EMBALAGENS_ORDEM, columns=semanas_ord, fill_value=0
        )

    pivot.index = [EMBALAGENS_LABELS.get(e, e) for e in pivot.index]
    pivot.index.name = "Embalagem"
    pivot.insert(0, "TOTAL", pivot.sum(axis=1))
    return pivot


# ==========================================
# CONTEÚDO
# ==========================================

render_header("📦 Entrada de Embalagens", "Diário e semanal · Frutifica · I9")

if df_estoque.empty:
    render_empty_state("📭", "Nenhum dado na aba Controle_Estoque.")
    st.stop()

# ==========================================
# MÉTRICAS
# ==========================================

total = int(df_mov["Quantidade"].sum()) if not df_mov.empty else 0
dias_n = df_mov["Data"].nunique() if not df_mov.empty else 0

emb_top = "—"
if not df_mov.empty:
    top = df_mov.groupby("Codigo")["Quantidade"].sum()
    if not top.empty and top.max() > 0:
        emb_top = EMBALAGENS_LABELS.get(top.idxmax(), "—").split(":")[0]

c1, c2, c3 = st.columns(3)
with c1:
    render_metric(f"{total:,}".replace(",", "."), "Total recebido (un.)")
with c2:
    render_metric(str(dias_n), "Dias com lançamento")
with c3:
    render_metric(emb_top, "Mais recebida")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.divider()

# ==========================================
# ENTRADA DIÁRIA
# ==========================================

st.markdown(
    "<div class='section-title'>Entrada Diária</div>", unsafe_allow_html=True
)

pivot_d = pivot_diario(df_mov)

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
        cmap=CMAP, subset=pivot_d_view.columns[1:], axis=None
    ),
    use_container_width=True,
    height=420,
)

# ==========================================
# ENTRADA SEMANAL
# ==========================================

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-title'>Entrada Semanal</div>", unsafe_allow_html=True
)

pivot_s = pivot_semanal(df_mov)

st.dataframe(
    pivot_s.style.format("{:,.0f}").background_gradient(
        cmap=CMAP, subset=pivot_s.columns[1:], axis=None
    ),
    use_container_width=True,
    height=420,
)

# ==========================================
# GRÁFICOS
# ==========================================

st.divider()
st.markdown(
    "<div class='section-title'>Visualizações</div>", unsafe_allow_html=True
)

# Gráfico 1 — Barras empilhadas semanais
pivot_s_plot = pivot_semanal(df_mov).drop(columns=["TOTAL"])
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
        title="Entrada Semanal por Embalagem",
        height=400,
    )
    st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2 — Total por embalagem horizontal
if not df_mov.empty:
    totais = df_mov.groupby("Codigo")["Quantidade"].sum()
    totais = totais.reindex(EMBALAGENS_ORDEM, fill_value=0)
    totais.index = [EMBALAGENS_LABELS.get(e, e).split(":")[0] for e in totais.index]
    totais = totais[totais > 0].sort_values()

    if not totais.empty:
        fig2 = go.Figure(
            go.Bar(
                x=totais.values,
                y=totais.index,
                orientation="h",
                marker_color=COR_PRINCIPAL,
                text=[f"{v:,}".replace(",", ".") for v in totais.values],
                textposition="outside",
                textfont=dict(color="#94a3b8", size=11),
            )
        )
        fig2.update_layout(
            **LAYOUT_PLOTLY,
            title="Total Recebido por Embalagem",
            height=380,
            margin=dict(l=20, r=80, t=40, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

# Gráfico 3 — Linha temporal diária
if not df_mov.empty:
    linha = df_mov.groupby("Data")["Quantidade"].sum().reset_index()
    linha.columns = ["Data", "Entrada"]

    fig3 = go.Figure(
        go.Scatter(
            x=linha["Data"],
            y=linha["Entrada"],
            mode="lines+markers",
            line=dict(color=COR_PRINCIPAL, width=2),
            marker=dict(size=6, color=COR_PRINCIPAL),
            fill="tozeroy",
            fillcolor="rgba(56,189,248,0.08)",
        )
    )
    fig3.update_layout(
        **LAYOUT_PLOTLY,
        title="Entrada Diária Total",
        height=350,
    )
    st.plotly_chart(fig3, use_container_width=True)
