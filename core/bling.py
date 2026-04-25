"""
Cliente Bling API v3.
Toda chamada ao Bling passa por aqui. Autenticação, refresh de token,
busca de produtos, saldos e (futuro) baixa de estoque.
"""

import base64
import json
import os
import time
from typing import Optional

import requests
import streamlit as st

from core.config import (
    BLING_API_BASE,
    REDIRECT_URI,
    TOKEN_FILE,
    get_bling_credentials,
)


# ==========================================
# AUTENTICAÇÃO
# ==========================================

def _auth_header() -> dict:
    """Header Basic para endpoints OAuth do Bling."""
    client_id, client_secret = get_bling_credentials()
    creds = f"{client_id}:{client_secret}"
    return {
        "Authorization": "Basic " + base64.b64encode(creds.encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }


def _salvar_token(token: dict) -> None:
    """Salva token no arquivo + adiciona timestamp pra checar expiração depois."""
    token["_timestamp"] = int(time.time())
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)


def _carregar_token() -> Optional[dict]:
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


def _token_valido(token: dict) -> bool:
    """Checa se o token ainda está dentro do prazo (com margem de 60s)."""
    if "access_token" not in token:
        return False
    timestamp = token.get("_timestamp", 0)
    expires_in = token.get("expires_in", 0)
    agora = int(time.time())
    return (timestamp + expires_in - 60) > agora


def renovar_token(refresh_token: str) -> dict:
    """Troca o refresh_token por um novo access_token."""
    resp = requests.post(
        f"{BLING_API_BASE}/oauth/token",
        headers=_auth_header(),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=30,
    )
    token = resp.json()
    if "access_token" in token:
        _salvar_token(token)
    return token


def get_access_token() -> Optional[str]:
    """
    Retorna um access_token válido.
    1. Se existe token salvo e ainda válido → retorna direto
    2. Se existe mas expirado → renova via refresh_token
    3. Se nada existe → retorna None (usuário precisa autorizar manualmente)
    """
    token = _carregar_token()
    if not token:
        return None

    if _token_valido(token):
        return token["access_token"]

    if "refresh_token" in token:
        novo = renovar_token(token["refresh_token"])
        if "access_token" in novo:
            return novo["access_token"]

    return None


# ==========================================
# CHAMADAS AO BLING
# ==========================================

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _respeitar_rate_limit():
    """Bling permite 3 req/s. Pausa mínima entre chamadas."""
    time.sleep(0.35)


def buscar_produtos(token: str, filtro_prefixo: str = "EMB", codigos_especificos: Optional[list] = None) -> list:
    """
    Busca produtos no Bling com paginação.

    Args:
        token: access_token válido
        filtro_prefixo: prefixo do código (ex: "EMB" pega todos começando com EMB)
        codigos_especificos: lista específica de códigos. Se passado, ignora filtro_prefixo.

    Returns:
        Lista de produtos (dicts do Bling)
    """
    produtos = []
    pagina = 1

    codigos_upper = [c.upper() for c in codigos_especificos] if codigos_especificos else None

    while True:
        resp = requests.get(
            f"{BLING_API_BASE}/produtos",
            params={"pagina": pagina, "limite": 100},
            headers=_headers(token),
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Bling retornou {resp.status_code}: {resp.text[:200]}")

        itens = resp.json().get("data", [])
        if not itens:
            break

        for p in itens:
            codigo = p.get("codigo", "").upper()
            if codigos_upper:
                if codigo in codigos_upper:
                    produtos.append(p)
            else:
                if codigo.startswith(filtro_prefixo.upper()):
                    produtos.append(p)

        if len(itens) < 100:
            break
        pagina += 1
        _respeitar_rate_limit()

    return produtos


def buscar_saldos(token: str, ids_produtos: list, deposito_id: Optional[int] = None) -> dict:
    """
    Busca saldos físicos REAIS via endpoint /produtos/{id}.
    Este endpoint retorna o saldo físico puro (sem descontar reservas),
    igual ao relatório Bling com a flag 'Considerar reserva' DESMARCADA.

    Returns:
        dict {produto_id: {
            "saldoFisico": X,          # saldo no depósito filtrado
            "saldoVirtual": Y,         # disponível (físico - reserva)
            "saldoFisicoTotal": Z,     # físico somado de todos depósitos
            "saldoVirtualTotal": W,    # disponível total
        }}
    """
    saldos = {}

    for prod_id in ids_produtos:
        resp = requests.get(
            f"{BLING_API_BASE}/produtos/{prod_id}",
            headers=_headers(token),
            timeout=30,
        )

        if resp.status_code != 200:
            # Não quebra tudo se 1 produto falhar
            saldos[prod_id] = {
                "saldoFisico": 0, "saldoVirtual": 0,
                "saldoFisicoTotal": 0, "saldoVirtualTotal": 0
            }
            _respeitar_rate_limit()
            continue

        produto = resp.json().get("data", {})
        estoque = produto.get("estoque", {})
        depositos = estoque.get("depositos", [])

        # Totais globais (somando todos depósitos)
        fisico_total = sum(d.get("saldoFisico", 0) for d in depositos)
        virtual_total = sum(d.get("saldoVirtual", 0) for d in depositos)

        # Saldo do depósito específico
        if deposito_id:
            dep = next((d for d in depositos if d.get("id") == deposito_id), None)
            fisico = dep.get("saldoFisico", 0) if dep else 0
            virtual = dep.get("saldoVirtual", 0) if dep else 0
        else:
            fisico = fisico_total
            virtual = virtual_total

        saldos[prod_id] = {
            "saldoFisico": fisico,
            "saldoVirtual": virtual,
            "saldoFisicoTotal": fisico_total,
            "saldoVirtualTotal": virtual_total,
        }

        _respeitar_rate_limit()

    return saldos


# ==========================================
# CACHE (streamlit)
# ==========================================

@st.cache_data(ttl=300, show_spinner=False)
def buscar_produtos_cached(filtro_prefixo: str = "EMB") -> list:
    """Cache de 5 min. Se mudou produto, clicar em 'atualizar' limpa o cache."""
    token = get_access_token()
    if not token:
        raise RuntimeError("Sem token válido. Rode o fluxo de autorização inicial.")
    return buscar_produtos(token, filtro_prefixo=filtro_prefixo)


@st.cache_data(ttl=120, show_spinner=False)
def buscar_saldos_cached(ids_produtos_tuple: tuple, deposito_id: Optional[int]) -> dict:
    """Cache curto (2 min) — saldo muda mais que cadastro."""
    token = get_access_token()
    if not token:
        raise RuntimeError("Sem token válido.")
    return buscar_saldos(token, list(ids_produtos_tuple), deposito_id)


