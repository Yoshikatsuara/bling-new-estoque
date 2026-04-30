"""
Funções auxiliares compartilhadas entre páginas.
"""

from datetime import datetime

import pandas as pd

# ==========================================
# FERIADOS
# ==========================================

FERIADOS_2026 = pd.to_datetime([
    "2026-04-03", "2026-04-21", "2026-05-01", "2026-06-04",
    "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-15",
    "2026-11-20", "2026-12-25",
])

# ==========================================
# FUNÇÕES
# ==========================================


def agora_br() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def semana_do_mes(data) -> str:
    d = pd.Timestamp(data)
    return f"S{(d.day - 1) // 7 + 1}"


def semana_label(d) -> str:
    meses = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }
    d = pd.Timestamp(d)
    return f"W{(d.day - 1) // 7 + 1} {meses[d.month]}/{d.year}"


def gerar_dias_uteis(extras=None):
    todos = pd.date_range(start="2026-04-17", end="2026-12-31", freq="B")
    uteis = [d for d in todos if d not in FERIADOS_2026]
    if extras:
        uteis = sorted(set(uteis) | set(pd.to_datetime(extras)))
    return pd.DatetimeIndex(uteis)
