import streamlit as st
import gspread
import pandas as pd
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

from utils.theme import CORES, LAYOUT_PLOTLY, aplicar_tema

# ==========================================
# CONFIGURAÇÕES
# ==========================================

SPREADSHEET_ID = "1YznbVsWCjzm9U7j-iGqD17Gj4F-8kFcFhHcGQbcOjXg"
JSON_CREDENTIALS = "credenciais.json"
NOME_ABA = "Movimentacoes"

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

MESES_NUM = {
    "Abril 2026": "04", "Maio 2026": "05", "Junho 2026": "06",
    "Julho 2026": "07", "Agosto 2026": "08", "Setembro 2026": "09",
    "Outubro 2026": "10", "Novembro 2026": "11", "Dezembro 2026": "12"
}

FERIADOS_2026 = pd.to_datetime([
    "2026-04-03", "2026-04-21", "2026-05-01", "2026-06-04",
    "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-15",
    "2026-11-20", "2026-12-25",
])

# ==========================================
# HELPERS
# ==========================================

def gerar_dias_uteis(extras=[]):
    todos = pd.date_range(start="2026-04-17", end="2026-12-31", freq="B")
    uteis = [d for d in todos if d not in FERIADOS_2026]
    if extras:
        uteis = sorted(set(uteis) | set(pd.to_datetime(extras)))
    return pd.DatetimeIndex(uteis)

def semana_label(d):
    meses = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
             7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
    d = pd.Timestamp(d)
    return f"W{(d.day-1)//7+1} {meses[d.month]}/{d.year}"

# ==========================================
# ESTILO
# ==========================================

st.set_page_config(page_title="Entrada", page_icon="📦", layout="wide")
aplicar_tema()

# Overrides locais: identidade azul da página Entrada
st.markdown("""
<style>
.metric-value { color: #38bdf8 !important; }
.stButton > button { background: #38bdf8 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ESTADO: dias extras
# ==========================================

if "dias_extras" not in st.session_state:
    st.session_state["dias_extras"] = []

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:
    st.markdown("""
    <div style='padding: 8px 0 20px 0'>
        <div style='font-size:1.1rem;font-weight:600;color:#f1f5f9'>📦 Entrada</div>
        <div style='font-size:0.75rem;color:#4b5563;margin-top:4px'>Frutifica · I9</div>
    </div>
    """, unsafe_allow_html=True)

    atualizar = st.button("🔄 Atualizar dados", use_container_width=True)

    st.divider()
    st.markdown("**Filtrar por mês**")
    mes_sel = st.multiselect(
        "Meses",
        options=list(MESES_NUM.keys()),
        default=["Abril 2026"],
        label_visibility="collapsed"
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

@st.cache_data(ttl=300)
def carregar_movimentacoes():
    creds = Credentials.from_service_account_file(
        JSON_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    try:
        aba = sh.worksheet(NOME_ABA)
        dados = aba.get_all_records()
    except Exception:
        return pd.DataFrame()

    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados)
    df["Data da Movimentação"] = pd.to_datetime(
        df["Data da Movimentação"], dayfirst=True, errors="coerce"
    )
    df["Quantidade Movimentada (Unidades)"] = pd.to_numeric(
        df["Quantidade Movimentada (Unidades)"], errors="coerce"
    ).fillna(0)
    df["Codigo"] = df["Embalagem (Produto)"].str.extract(r"^(EMB[^\s:]+)")
    return df

if atualizar:
    st.cache_data.clear()

with st.spinner("Carregando..."):
    df = carregar_movimentacoes()

DIAS_UTEIS = gerar_dias_uteis(st.session_state["dias_extras"])

# ==========================================
# PIVOTS
# ==========================================

def pivot_diario(df, tipo="Entrada"):
    df_t = df[df["Tipo de Movimentação"] == tipo].copy()
    if df_t.empty:
        pivot = pd.DataFrame(0, index=EMBALAGENS_ORDEM, columns=DIAS_UTEIS)
    else:
        pivot = df_t.pivot_table(
            index="Codigo", columns="Data da Movimentação",
            values="Quantidade Movimentada (Unidades)",
            aggfunc="sum", fill_value=0
        )
        pivot = pivot.reindex(index=EMBALAGENS_ORDEM, columns=DIAS_UTEIS, fill_value=0)

    pivot.index = [EMBALAGENS_LABELS.get(e, e) for e in pivot.index]
    pivot.index.name = "Embalagem"
    pivot.columns = [d.strftime("%d/%m") for d in pivot.columns]
    pivot.insert(0, "TOTAL", pivot.sum(axis=1))
    return pivot

def pivot_semanal(df, tipo="Entrada"):
    semana_map = {d: semana_label(d) for d in DIAS_UTEIS}
    semanas_ord = list(dict.fromkeys(semana_map.values()))

    df_t = df[df["Tipo de Movimentação"] == tipo].copy()
    if df_t.empty:
        pivot = pd.DataFrame(0, index=EMBALAGENS_ORDEM, columns=semanas_ord)
    else:
        df_t["Semana"] = df_t["Data da Movimentação"].map(
            lambda d: semana_label(d) if pd.notna(d) else None
        )
        pivot = df_t.pivot_table(
            index="Codigo", columns="Semana",
            values="Quantidade Movimentada (Unidades)",
            aggfunc="sum", fill_value=0
        )
        pivot = pivot.reindex(index=EMBALAGENS_ORDEM, columns=semanas_ord, fill_value=0)

    pivot.index = [EMBALAGENS_LABELS.get(e, e) for e in pivot.index]
    pivot.index.name = "Embalagem"
    pivot.insert(0, "TOTAL", pivot.sum(axis=1))
    return pivot

# ==========================================
# INTERFACE
# ==========================================

st.markdown("""
<div class='header-title'>📦 Entrada de Embalagens</div>
<div class='header-sub'>Diário e semanal · Frutifica · I9</div>
""", unsafe_allow_html=True)

if df.empty:
    st.markdown("""
    <div style='background:#161b27;border:1px solid #1e2535;border-radius:12px;
    padding:40px;text-align:center;margin-top:40px'>
        <div style='font-size:2rem;margin-bottom:12px'>📭</div>
        <div style='color:#94a3b8'>Nenhum dado na aba Movimentacoes.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

df_entrada = df[df["Tipo de Movimentação"] == "Entrada"]

# — Métricas —
total = int(df_entrada["Quantidade Movimentada (Unidades)"].sum())
dias_n = df_entrada["Data da Movimentação"].nunique()
emb_top_cod = df_entrada.groupby("Codigo")["Quantidade Movimentada (Unidades)"].sum()
emb_top = EMBALAGENS_LABELS.get(emb_top_cod.idxmax(), "—").split(":")[0] if not emb_top_cod.empty else "—"

c1, c2, c3 = st.columns(3)
for col, val, label in [
    (c1, f"{total:,}", "Total recebido (un.)"),
    (c2, str(dias_n), "Dias com lançamento"),
    (c3, emb_top, "Mais recebida"),
]:
    col.markdown(f"""<div class='metric-card'>
        <div class='metric-value' style='font-size:{"1.6rem" if len(str(val))<8 else "1.1rem"}'>{val}</div>
        <div class='metric-label'>{label}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.divider()

# — Entrada Diária —
st.markdown("<div class='section-title'>Entrada Diária</div>", unsafe_allow_html=True)

pivot_d = pivot_diario(df)

if mes_sel:
    meses_filtro = [MESES_NUM[m] for m in mes_sel]
    cols_vis = ["TOTAL"] + [c for c in pivot_d.columns if c != "TOTAL" and c[3:5] in meses_filtro]
    pivot_d_view = pivot_d[cols_vis]
else:
    pivot_d_view = pivot_d

st.dataframe(
    pivot_d_view.style.format("{:,.0f}").background_gradient(
        cmap="Blues", subset=pivot_d_view.columns[1:], axis=None
    ),
    use_container_width=True,
    height=420
)

# — Entrada Semanal —
st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Entrada Semanal</div>", unsafe_allow_html=True)

pivot_s = pivot_semanal(df)

st.dataframe(
    pivot_s.style.format("{:,.0f}").background_gradient(
        cmap="Blues", subset=pivot_s.columns[1:], axis=None
    ),
    use_container_width=True,
    height=420
)

# ==========================================
# GRÁFICOS
# ==========================================

st.divider()
st.markdown("<div class='section-title'>Visualizações</div>", unsafe_allow_html=True)

# Gráfico 1 — Barras empilhadas semanais
pivot_s_plot = pivot_semanal(df).drop(columns=["TOTAL"])
pivot_s_plot = pivot_s_plot.loc[:, (pivot_s_plot != 0).any(axis=0)]

fig1 = go.Figure()
for i, emb in enumerate(pivot_s_plot.index):
    fig1.add_trace(go.Bar(
        name=emb.split(":")[0],
        x=pivot_s_plot.columns.tolist(),
        y=pivot_s_plot.loc[emb].tolist(),
        marker_color=CORES[i % len(CORES)],
    ))
fig1.update_layout(**LAYOUT_PLOTLY, barmode="stack",
    title="Entrada Semanal por Embalagem", height=400)
st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2 — Total por embalagem (horizontal)
totais = df_entrada.groupby("Codigo")["Quantidade Movimentada (Unidades)"].sum()
totais = totais.reindex(EMBALAGENS_ORDEM, fill_value=0)
totais.index = [EMBALAGENS_LABELS.get(e, e).split(":")[0] for e in totais.index]
totais = totais[totais > 0].sort_values()

fig2 = go.Figure(go.Bar(
    x=totais.values, y=totais.index, orientation="h",
    marker_color="#38bdf8",
    text=[f"{v:,}" for v in totais.values],
    textposition="outside", textfont=dict(color="#94a3b8", size=11),
))
fig2.update_layout(**LAYOUT_PLOTLY,
    title="Total Recebido por Embalagem", height=380,
    margin=dict(l=20, r=80, t=40, b=20))
st.plotly_chart(fig2, use_container_width=True)

# Gráfico 3 — Linha temporal diária
if not df_entrada.empty:
    linha = df_entrada.groupby("Data da Movimentação")["Quantidade Movimentada (Unidades)"].sum().reset_index()
    linha.columns = ["Data", "Entrada"]
    fig3 = go.Figure(go.Scatter(
        x=linha["Data"], y=linha["Entrada"],
        mode="lines+markers",
        line=dict(color="#38bdf8", width=2),
        marker=dict(size=6, color="#38bdf8"),
        fill="tozeroy", fillcolor="rgba(56,189,248,0.08)",
    ))
    fig3.update_layout(**LAYOUT_PLOTLY,
        title="Entrada Diária Total", height=350)
    st.plotly_chart(fig3, use_container_width=True)
