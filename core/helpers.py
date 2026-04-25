"""
Utilitários diversos: cálculo de semana, dias úteis, formatações.
"""

from datetime import date, datetime
import pandas as pd

from core.config import FERIADOS_2026

MESES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}


def semana_do_mes(d: date) -> str:
    """'Semana 3' a partir do dia do mês."""
    semana = (d.day - 1) // 7 + 1
    return f"Semana {semana}"


def semana_label(d) -> str:
    """'W3 Abr/2026' — formato usado na planilha de projeção."""
    d = pd.Timestamp(d)
    return f"W{(d.day - 1) // 7 + 1} {MESES_ABREV[d.month]}/{d.year}"


def gerar_dias_uteis(inicio: str = "2026-04-17", fim: str = "2026-12-31", extras: list = None) -> pd.DatetimeIndex:
    """
    Gera DatetimeIndex com dias úteis do período (exclui fins de semana e feriados).

    Args:
        extras: lista de strings 'YYYY-MM-DD' com sábados/domingos trabalhados
    """
    feriados = pd.to_datetime(FERIADOS_2026)
    todos = pd.date_range(start=inicio, end=fim, freq="B")  # B = business days
    uteis = [d for d in todos if d not in feriados]
    if extras:
        uteis = sorted(set(uteis) | set(pd.to_datetime(extras)))
    return pd.DatetimeIndex(uteis)


def formatar_data_br(d) -> str:
    """Converte pra formato brasileiro dd/mm/yyyy."""
    if isinstance(d, str):
        return d
    return d.strftime("%d/%m/%Y")


def agora_br() -> str:
    """Timestamp atual em formato brasileiro."""
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")
