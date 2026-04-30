"""
Módulo de dados centralizado.
Toda leitura de Controle_Estoque e Saldo_Inicial passa por aqui.

Modelo:
  - Controle_Estoque: cada linha = 1 movimentação com Tipo, Canal e quantidade bruta
  - Saldo_Inicial: referência configurada uma vez (com Data_Base)
  - Saldo Atual = Saldo_Inicial - Σ Consumo + Σ Entrada
"""

from datetime import date, datetime

import pandas as pd

from core import sheets
from core.config import (
    ABA_CONTROLE_ESTOQUE,
    ABA_SALDO_INICIAL,
    CABECALHO_SALDO_INICIAL,
    EMBALAGENS_LABELS,
    EMBALAGENS_ORDEM,
)


# ==========================================
# CONTROLE DE ESTOQUE
# ==========================================


def carregar_controle_estoque() -> pd.DataFrame:
    """
    Lê aba Controle_Estoque e retorna DataFrame limpo.
    """
    df = sheets.ler_aba_como_df(ABA_CONTROLE_ESTOQUE)
    if df.empty:
        return pd.DataFrame()

    df["Codigo"] = df["Codigo"].astype(str).str.strip().str.upper()
    df["Tipo"] = df["Tipo"].astype(str).str.strip()

    if "Canal" in df.columns:
        df["Canal"] = df["Canal"].astype(str).str.strip()
    else:
        df["Canal"] = ""

    df["Data Relatorio"] = pd.to_datetime(
        df["Data Relatorio"], dayfirst=True, errors="coerce"
    )

    df["Estoque Fisico"] = (
        df["Estoque Fisico"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Estoque Fisico"] = (
        pd.to_numeric(df["Estoque Fisico"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    df = df[df["Codigo"].isin(EMBALAGENS_ORDEM)].copy()
    df = df.dropna(subset=["Data Relatorio"])
    df = df.sort_values(["Codigo", "Data Relatorio"]).reset_index(drop=True)

    return df


def calcular_movimentacoes(
    df: pd.DataFrame,
    tipo: str,
    canal: str | None = None,
) -> pd.DataFrame:
    """
    Retorna movimentações de um tipo (Consumo ou Entrada).
    Opcionalmente filtra por canal.

    Retorna DataFrame com: Codigo, Data, Quantidade, Canal
    """
    if df.empty:
        return pd.DataFrame(columns=["Codigo", "Data", "Quantidade", "Canal"])

    df_t = df[df["Tipo"].str.lower() == tipo.lower()].copy()

    if canal and canal != "Todos":
        df_t = df_t[df_t["Canal"].str.lower() == canal.lower()].copy()

    if df_t.empty:
        return pd.DataFrame(columns=["Codigo", "Data", "Quantidade", "Canal"])

    df_t = df_t.rename(columns={
        "Data Relatorio": "Data",
        "Estoque Fisico": "Quantidade",
    })

    df_t["Quantidade"] = df_t["Quantidade"].clip(lower=0).astype(int)
    df_t = df_t[df_t["Quantidade"] > 0].copy()
    df_t = df_t.sort_values(["Codigo", "Data"]).reset_index(drop=True)

    return df_t[["Codigo", "Data", "Quantidade", "Canal"]]


def total_por_tipo(
    df: pd.DataFrame,
    tipo: str,
    canal: str | None = None,
) -> pd.DataFrame:
    """
    Retorna total movimentado por código para um tipo.
    Colunas: Codigo, Total
    """
    mov = calcular_movimentacoes(df, tipo, canal)
    if mov.empty:
        return pd.DataFrame({"Codigo": EMBALAGENS_ORDEM, "Total": 0})

    totais = mov.groupby("Codigo")["Quantidade"].sum().reset_index()
    totais = totais.rename(columns={"Quantidade": "Total"})

    base = pd.DataFrame({"Codigo": EMBALAGENS_ORDEM})
    base = base.merge(totais, on="Codigo", how="left")
    base["Total"] = base["Total"].fillna(0).astype(int)
    return base


# ==========================================
# SALDO INICIAL
# ==========================================


def carregar_saldos_iniciais() -> pd.DataFrame:
    """Lê aba Saldo_Inicial. Retorna DataFrame com Codigo, Saldo_Inicial, Data_Base."""
    df = sheets.ler_aba_como_df(ABA_SALDO_INICIAL)
    if df.empty:
        return pd.DataFrame(columns=["Codigo", "Saldo_Inicial", "Data_Base"])

    df["Codigo"] = df["Codigo"].astype(str).str.strip().str.upper()
    df["Saldo_Inicial"] = (
        pd.to_numeric(df["Saldo_Inicial"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    if "Data_Base" in df.columns:
        df["Data_Base"] = pd.to_datetime(
            df["Data_Base"], dayfirst=True, errors="coerce"
        ).dt.normalize()
    else:
        df["Data_Base"] = pd.NaT

    df = df.drop_duplicates(subset=["Codigo"], keep="last")
    return df[["Codigo", "Saldo_Inicial", "Data_Base"]]


def salvar_saldos_iniciais(saldos: dict, data_base: date) -> str:
    """
    Grava/atualiza aba Saldo_Inicial.
    Returns: 'success' | 'error:<msg>'
    """
    try:
        import gspread

        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        data_base_txt = data_base.strftime("%d/%m/%Y")
        sh = sheets.abrir_planilha()

        try:
            aba = sh.worksheet(ABA_SALDO_INICIAL)
            aba.clear()
        except gspread.exceptions.WorksheetNotFound:
            aba = sh.add_worksheet(title=ABA_SALDO_INICIAL, rows=50, cols=5)

        rows = [CABECALHO_SALDO_INICIAL]
        for codigo in EMBALAGENS_ORDEM:
            val = saldos.get(codigo, 0)
            rows.append([codigo, int(val), data_base_txt, agora])

        aba.update(range_name="A1", values=rows)
        sheets.invalidar_cache()
        return "success"

    except Exception as e:
        return f"error:{e}"


# ==========================================
# SALDO ATUAL (cálculo central)
# ==========================================


def calcular_saldo_atual(
    df_estoque: pd.DataFrame,
    canal: str | None = None,
) -> pd.DataFrame:
    """
    Saldo Atual = Saldo Inicial - Σ Consumo + Σ Entrada

    Retorna DataFrame com:
      Codigo, Saldo_Inicial, Total_Consumo, Total_Entrada, Saldo_Atual
    """
    df_ini = carregar_saldos_iniciais()
    df_consumo = total_por_tipo(df_estoque, "Consumo", canal).rename(
        columns={"Total": "Total_Consumo"}
    )
    df_entrada = total_por_tipo(df_estoque, "Entrada", canal).rename(
        columns={"Total": "Total_Entrada"}
    )

    base = pd.DataFrame({"Codigo": EMBALAGENS_ORDEM})
    base = base.merge(df_ini[["Codigo", "Saldo_Inicial"]], on="Codigo", how="left")
    base = base.merge(df_consumo, on="Codigo", how="left")
    base = base.merge(df_entrada, on="Codigo", how="left")

    base["Saldo_Inicial"] = base["Saldo_Inicial"].fillna(0).astype(int)
    base["Total_Consumo"] = base["Total_Consumo"].fillna(0).astype(int)
    base["Total_Entrada"] = base["Total_Entrada"].fillna(0).astype(int)
    base["Saldo_Atual"] = (
        base["Saldo_Inicial"] - base["Total_Consumo"] + base["Total_Entrada"]
    )

    return base


# ==========================================
# SALDO DIÁRIO (pivot acumulado)
# ==========================================


def calcular_saldo_diario(
    df_estoque: pd.DataFrame,
    canal: str | None = None,
) -> pd.DataFrame:
    """
    Calcula o saldo acumulado por embalagem em cada dia com movimentação.

    Para cada dia: aplica consumos e entradas do dia sobre o saldo anterior.
    Resultado é um pivot: index=Embalagem, columns=datas (dd/mm), values=saldo.
    """
    df_ini = carregar_saldos_iniciais()
    saldos_iniciais = dict(zip(df_ini["Codigo"], df_ini["Saldo_Inicial"]))

    if df_estoque.empty:
        return pd.DataFrame()

    df = df_estoque[
        df_estoque["Tipo"].str.lower().isin(["consumo", "entrada"])
    ].copy()

    if canal and canal != "Todos":
        df = df[df["Canal"].str.lower() == canal.lower()].copy()

    if df.empty:
        return pd.DataFrame()

    datas = sorted(df["Data Relatorio"].dt.normalize().unique())

    linhas = []
    for codigo in EMBALAGENS_ORDEM:
        saldo_ini = int(saldos_iniciais.get(codigo, 0))
        df_cod = df[df["Codigo"] == codigo].copy()

        saldo_acum = saldo_ini
        row = {"Embalagem": EMBALAGENS_LABELS.get(codigo, codigo)}

        for dt in datas:
            df_dia = df_cod[df_cod["Data Relatorio"].dt.normalize() == dt]

            for _, mov in df_dia.iterrows():
                tipo = mov["Tipo"].strip().lower()
                qtd = int(mov["Estoque Fisico"])
                if tipo == "consumo":
                    saldo_acum -= qtd
                elif tipo == "entrada":
                    saldo_acum += qtd

            row[pd.Timestamp(dt).strftime("%d/%m")] = saldo_acum

        linhas.append(row)

    pivot = pd.DataFrame(linhas).set_index("Embalagem")
    return pivot


# ==========================================
# EXTRATO
# ==========================================


def gerar_extrato(
    df_estoque: pd.DataFrame,
    canal: str | None = None,
) -> pd.DataFrame:
    """
    Gera extrato cronológico de movimentações com saldo acumulado.
    """
    df_ini = carregar_saldos_iniciais()
    saldos_iniciais = dict(zip(df_ini["Codigo"], df_ini["Saldo_Inicial"]))

    if df_estoque.empty:
        return pd.DataFrame()

    df = df_estoque[
        df_estoque["Tipo"].str.lower().isin(["consumo", "entrada"])
    ].copy()

    if canal and canal != "Todos":
        df = df[df["Canal"].str.lower() == canal.lower()].copy()

    if df.empty:
        return pd.DataFrame()

    df = df.sort_values(["Codigo", "Data Relatorio"]).reset_index(drop=True)

    linhas = []
    for codigo in EMBALAGENS_ORDEM:
        saldo = int(saldos_iniciais.get(codigo, 0))
        df_cod = df[df["Codigo"] == codigo]

        for _, row in df_cod.iterrows():
            tipo = row["Tipo"].strip().lower()
            qtd = int(row["Estoque Fisico"])

            if tipo == "consumo":
                saldo -= qtd
            elif tipo == "entrada":
                saldo += qtd

            linhas.append({
                "Data": row["Data Relatorio"],
                "Codigo": codigo,
                "Embalagem": EMBALAGENS_LABELS.get(codigo, codigo),
                "Tipo": row["Tipo"].strip(),
                "Canal": row.get("Canal", ""),
                "Quantidade": qtd,
                "Saldo_Acumulado": saldo,
            })

    return pd.DataFrame(linhas)


# ==========================================
# ÚLTIMO RELATÓRIO
# ==========================================


def carregar_ultimo_relatorio() -> tuple:
    """
    Retorna (DataFrame com Codigo + Estoque Fisico, data) do último relatório.
    """
    df = carregar_controle_estoque()
    if df.empty:
        return pd.DataFrame(), None

    ultima_data = df["Data Relatorio"].max()
    df_ultimo = df[df["Data Relatorio"] == ultima_data][
        ["Codigo", "Estoque Fisico"]
    ].copy()
    return df_ultimo, ultima_data