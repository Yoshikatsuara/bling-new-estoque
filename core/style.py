"""
Helpers de renderização (header, métricas, empty state) compartilhados.
O CSS, paleta e layout Plotly vivem em utils.theme — aqui só reexportamos
aliases pra manter compatibilidade com código que ainda chama os nomes antigos.
"""

import streamlit as st

from utils.theme import CORES, CSS_GLOBAL, LAYOUT_PLOTLY, aplicar_tema

# Aliases de compatibilidade
CORES_GRAFICOS = CORES
LAYOUT_PLOTLY_BASE = LAYOUT_PLOTLY
aplicar_css = aplicar_tema


def render_header(titulo: str, subtitulo: str = ""):
    """Renderiza o header padrão de cada página."""
    st.markdown(f"""
    <div class='header-title'>{titulo}</div>
    <div class='header-sub'>{subtitulo}</div>
    """, unsafe_allow_html=True)


def render_sidebar_header(titulo: str, subtitulo: str = ""):
    """Header padrão da sidebar."""
    st.sidebar.markdown(f"""
    <div class='sidebar-header'>
        <div class='sidebar-title'>{titulo}</div>
        <div class='sidebar-sub'>{subtitulo}</div>
    </div>
    """, unsafe_allow_html=True)


def render_metric(valor, label: str, cor: str = "#4ade80"):
    """Renderiza um card de métrica."""
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-value' style='color:{cor}'>{valor}</div>
        <div class='metric-label'>{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_empty_state(icone: str, mensagem: str):
    """Estado vazio quando não tem dados."""
    st.markdown(f"""
    <div class='empty-state'>
        <div style='font-size:2.5rem;margin-bottom:12px'>{icone}</div>
        <div style='color:#94a3b8;font-size:0.95rem'>{mensagem}</div>
    </div>
    """, unsafe_allow_html=True)
