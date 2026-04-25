"""
Identidade visual do projeto: paleta, layout Plotly e CSS global.
Qualquer página importa daqui — mudou cor/layout base, propaga pra todas.
"""

import streamlit as st

# Paleta consistente pra gráficos Plotly (10 cores)
CORES = [
    "#4ade80", "#38bdf8", "#f472b6", "#fb923c", "#a78bfa",
    "#facc15", "#34d399", "#60a5fa", "#f87171", "#94a3b8",
]

# Configuração padrão de layout dos gráficos Plotly
LAYOUT_PLOTLY = dict(
    paper_bgcolor="#0f1117",
    plot_bgcolor="#0f1117",
    font=dict(family="DM Sans", color="#94a3b8"),
    xaxis=dict(gridcolor="#1e2535"),
    yaxis=dict(gridcolor="#1e2535"),
    legend=dict(bgcolor="#161b27", bordercolor="#1e2535", borderwidth=1),
)

CSS_GLOBAL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0f1117; }
[data-testid="stSidebar"] { background: #161b27 !important; border-right: 1px solid #1e2535; }

/* Cards e métricas */
.metric-card {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
}
.metric-value { font-family: 'DM Mono', monospace; font-size: 2rem; font-weight: 500; color: #4ade80; line-height: 1; }
.metric-label { font-size: 0.78rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 6px; }

/* Headers */
.header-title { font-size: 1.6rem; font-weight: 600; color: #f1f5f9; letter-spacing: -0.02em; }
.header-sub { font-size: 0.85rem; color: #4b5563; margin-bottom: 28px; }
.section-title { font-size: 0.78rem; font-weight: 600; color: #6b7280; text-transform: uppercase;
    letter-spacing: 0.08em; margin: 24px 0 10px 0; }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
    background: #0f1117 !important;
    border-color: #1e2535 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
}
.stNumberInput input {
    background: #0f1117 !important;
    border-color: #1e2535 !important;
    color: #f1f5f9 !important;
}

/* Labels de inputs */
.stSelectbox label, .stNumberInput label, .stTextArea label,
.stDateInput label, .stRadio label, .stMultiSelect label, .stCheckbox label {
    color: #94a3b8 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
.stCheckbox label { font-size: 0.88rem !important; text-transform: none !important; letter-spacing: 0 !important; }

/* Radio buttons como pílulas */
.stRadio > div { gap: 12px; }
.stRadio > div label {
    background: #1e2535;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 8px 18px !important;
    color: #94a3b8 !important;
    font-size: 0.9rem !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    cursor: pointer;
    transition: all 0.15s;
}
.stRadio > div label:has(input:checked) {
    border-color: #4ade80 !important;
    color: #4ade80 !important;
    background: #0f2318 !important;
}

/* Botões */
.stButton > button {
    background: #4ade80 !important;
    color: #0f1117 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.4rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stDownloadButton > button {
    background: #1e2535 !important;
    color: #94a3b8 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
}

/* Boxes de feedback */
.success-box {
    background: #0f2318;
    border: 1px solid #4ade80;
    border-radius: 10px;
    padding: 16px 20px;
    color: #4ade80;
    font-size: 0.9rem;
    text-align: center;
    margin-top: 12px;
}
.error-box {
    background: #2a0f0f;
    border: 1px solid #ef4444;
    border-radius: 10px;
    padding: 16px 20px;
    color: #ef4444;
    font-size: 0.9rem;
    text-align: center;
    margin-top: 12px;
}
.warn-box {
    background: #1a1500;
    border: 1px solid #facc15;
    border-radius: 10px;
    padding: 16px 20px;
    color: #facc15;
    font-size: 0.9rem;
    text-align: center;
    margin-top: 12px;
}

/* Empty state */
.empty-state {
    background: #161b27;
    border: 1px solid #1e2535;
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    margin-top: 40px;
}

hr { border-color: #1e2535 !important; }

/* Sidebar header */
.sidebar-header {
    padding: 8px 0 20px 0;
}
.sidebar-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #f1f5f9;
}
.sidebar-sub {
    font-size: 0.75rem;
    color: #4b5563;
    margin-top: 4px;
}
</style>
"""


def aplicar_tema():
    """Injeta o CSS global no topo da página."""
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)
