"""
Home do sistema. Resumo rápido + navegação.
"""

import streamlit as st

from core.style import aplicar_css, render_header

st.set_page_config(
    page_title="Controle Embalagens · Frutifica",
    page_icon="📦",
    layout="wide"
)

aplicar_css()

# ==========================================
# HEADER
# ==========================================

render_header(
    "📦 Controle de Embalagens",
    "Sistema integrado · Frutifica · I9"
)

# ==========================================
# CARDS DE NAVEGAÇÃO
# ==========================================

st.markdown("<div class='section-title'>O que você quer fazer?</div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class='metric-card' style='padding:24px'>
        <div style='font-size:1.8rem;margin-bottom:8px'>📦</div>
        <div style='font-size:1.1rem;font-weight:600;color:#f1f5f9;margin-bottom:6px'>
            Consultar Estoque
        </div>
        <div style='font-size:0.85rem;color:#94a3b8;line-height:1.5'>
            Saldo atual das embalagens em tempo real.<br>
            Filtros por depósito e embalagem.
        </div>
        <div style='margin-top:14px;font-size:0.78rem;color:#4ade80;font-family:DM Mono'>
            → página "Estoque"
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='metric-card' style='padding:24px'>
        <div style='font-size:1.8rem;margin-bottom:8px'>📉</div>
        <div style='font-size:1.1rem;font-weight:600;color:#f1f5f9;margin-bottom:6px'>
            Analisar Consumo
        </div>
        <div style='font-size:0.85rem;color:#94a3b8;line-height:1.5'>
            Consumo diário e semanal.<br>
            Gráficos e tendências.
        </div>
        <div style='margin-top:14px;font-size:0.78rem;color:#4ade80;font-family:DM Mono'>
            → página "Consumo"
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class='metric-card' style='padding:24px'>
        <div style='font-size:1.8rem;margin-bottom:8px'>📋</div>
        <div style='font-size:1.1rem;font-weight:600;color:#f1f5f9;margin-bottom:6px'>
            Registrar Movimentação
        </div>
        <div style='font-size:0.85rem;color:#94a3b8;line-height:1.5'>
            Lançar consumo ou entrada de embalagens.<br>
            Por canal e por embalagem.
        </div>
        <div style='margin-top:14px;font-size:0.78rem;color:#4ade80;font-family:DM Mono'>
            → página "Movimentacao"
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='metric-card' style='padding:24px;opacity:0.5'>
        <div style='font-size:1.8rem;margin-bottom:8px'>🎯</div>
        <div style='font-size:1.1rem;font-weight:600;color:#f1f5f9;margin-bottom:6px'>
            Projeção e Ruptura
        </div>
        <div style='font-size:0.85rem;color:#94a3b8;line-height:1.5'>
            Cobertura em dias e data de ruptura.<br>
            <em>Em construção</em>
        </div>
        <div style='margin-top:14px;font-size:0.78rem;color:#6b7280;font-family:DM Mono'>
            em breve
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# RODAPÉ
# ==========================================

st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
st.divider()
st.markdown("""
<div style='text-align:center;color:#4b5563;font-size:0.78rem;padding:16px 0'>
    Dados consultados em tempo real via Bling API v3<br>
    Histórico armazenado em Google Sheets
</div>
""", unsafe_allow_html=True)
