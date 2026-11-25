"""Filas de processamento (datapool) consumidas pelos robôs.

Você cria itens a processar na Lagoa e os robôs (agentes com ``--fila``)
reivindicam e processam um por um — algo próximo das *filas* de RPA::

    from core.rpa import fila

    fila.criar("clientes", descricao="Notas fiscais de hoje", processo="Dados — Tratar planilha")
    fila.adicionar("clientes", [
        {"nome": "ACME Ltda", "uf": "SP"},
        {"nome": "XPTO S.A", "uf": "RJ"},
    ], referencia_campo="nome")
    resumo = fila.resumo("clientes")
"""

from __future__ import annotations

from typing import Any

import requests
from loguru import logger

from settings.parametros import LAGOA_TOKEN, LAGOA_URL


def _base(control_room: str | None) -> str:
    return (control_room or LAGOA_URL).rstrip("/")


def _cabecalhos() -> dict[str, str]:
    """Token do agente, quando configurado (Authorization: Bearer)."""
    return {"Authorization": f"Bearer {LAGOA_TOKEN}"} if LAGOA_TOKEN else {}


class Fila:
    """Cliente de uma fila da Lagoa."""

    def __init__(self, nome: str, control_room: str | None = None) -> None:
        self.nome = nome
        self.base = _base(control_room)

    def adicionar(
        self,
        dados: dict[str, Any] | list[dict[str, Any]],
        referencia: str | None = None,
        referencia_campo: str | None = None,
        prioridade: int = 0,
    ) -> int:
        """Insere um item (ou vários) na fila. Retorna quantos foram adicionados."""
        itens = dados if isinstance(dados, list) else [dados]
        resposta = requests.post(
            f"{self.base}/api/orq/filas/{self.nome}/itens",
            json={
                "itens": itens,
                "referencia_campo": referencia_campo or None,
                "prioridade": prioridade,
            },
            timeout=30,
            headers=_cabecalhos(),
        )
        resposta.raise_for_status()
        total = resposta.json().get("adicionados", 0)
        logger.success(f"[fila] {total} item(ns) adicionado(s) à fila '{self.nome}'")
        return total

    def listar(self, status: str | None = None) -> list[dict[str, Any]]:
        """Lista os itens da fila."""
        resposta = requests.get(
            f"{self.base}/api/orq/filas/{self.nome}/itens", timeout=30, headers=_cabecalhos()
        )
        resposta.raise_for_status()
        return resposta.json().get("itens", [])

    def resumo(self) -> dict[str, Any]:
        """Contagem de itens por status."""
        dados = self.listar()
        resumo_fila: dict[str, int] = {}
        for item in dados:
            resumo_fila[item["status"]] = resumo_fila.get(item["status"], 0) + 1
        return resumo_fila


def criar(
    nome: str,
    descricao: str | None = None,
    processo: str | int | None = None,
    control_room: str | None = None,
) -> dict[str, Any]:
    """Cria uma fila. ``processo`` pode ser o nome ou o id do processo executor."""
    corpo: dict[str, Any] = {"nome": nome, "descricao": descricao}
    if isinstance(processo, int):
        corpo["processo_id"] = processo
    elif isinstance(processo, str):
        corpo["processo_nome"] = processo
    resposta = requests.post(
        f"{_base(control_room)}/api/orq/filas", json=corpo, timeout=30, headers=_cabecalhos()
    )
    resposta.raise_for_status()
    return resposta.json().get("fila", {})


def adicionar(
    fila: str,
    itens: dict[str, Any] | list[dict[str, Any]],
    referencia_campo: str | None = None,
    prioridade: int = 0,
    control_room: str | None = None,
) -> int:
    """Atalho: adiciona itens a uma fila pelo nome."""
    return Fila(fila, control_room).adicionar(
        itens, referencia_campo=referencia_campo, prioridade=prioridade
    )


def resumo(nome: str, control_room: str | None = None) -> dict[str, int]:
    """Atalho: resumo de uma fila."""
    return Fila(nome, control_room).resumo()


__all__ = ["Fila", "criar", "adicionar", "resumo"]