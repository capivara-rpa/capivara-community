"""Cofre de credenciais (vault) consumido pelos robôs.

Os segredos ficam centralizados e **cifrados** na Lagoa. Este módulo é o
cliente usado dentro dos fluxos para buscar credenciais sem deixá-las no código
nem no ``.env``::

    from core.rpa import vault

    usuario = vault.obter("portal_usuario")
    senha   = vault.obter("portal_senha")

    # ou, lendo um par de credenciais de uma vez:
    usuario, senha = vault.credencial("portal_usuario", "portal_senha")

A URL da Lagoa vem de ``LAGOA_URL`` (``.env``) e pode ser
sobrescrita passando ``control_room=...``.
"""

from __future__ import annotations

from typing import Any

import requests
from loguru import logger

from core.tratador import ErroRPA
from settings.parametros import LAGOA_TOKEN, LAGOA_URL


def _cabecalhos() -> dict[str, str]:
    """Token do agente, quando configurado (Authorization: Bearer)."""
    return {"Authorization": f"Bearer {LAGOA_TOKEN}"} if LAGOA_TOKEN else {}


class Cofre:
    """Cliente HTTP do cofre de credenciais da Lagoa."""

    def __init__(self, control_room: str | None = None) -> None:
        self.base = (control_room or LAGOA_URL).rstrip("/")

    # ------------------------------------------------------------------
    def obter(
        self,
        nome: str,
        ator: str | None = None,
        processo_id: int | None = None,
    ) -> str | None:
        """Busca o valor (decifrado) de um segredo pelo nome."""
        params: dict[str, Any] = {}
        if ator:
            params["ator"] = ator
        if processo_id is not None:
            params["processo_id"] = processo_id
        try:
            resposta = requests.get(
                f"{self.base}/api/orq/assets/{nome}",
                timeout=30,
                headers=_cabecalhos(),
                params=params,
            )
        except requests.RequestException as erro:
            raise ErroRPA(f"Lagoa indisponível: {erro}") from erro

        if resposta.status_code == 404:
            logger.warning(f"[vault] segredo '{nome}' não encontrado na Lagoa")
            return None
        resposta.raise_for_status()
        return resposta.json().get("valor")

    def exigir(self, nome: str, **contexto: Any) -> str:
        """Como :meth:`obter`, mas levanta :class:`ErroRPA` se não encontrar."""
        valor = self.obter(nome, **contexto)
        if valor is None:
            raise ErroRPA(f"Credencial '{nome}' não encontrada (ou sem permissão) no cofre.")
        return valor

    def buscar_credencial(
        self,
        nome: str,
        ator: str | None = None,
        processo_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Busca uma credencial completa: ``{nome, usuario, senha, tipo, versao}``."""
        params: dict[str, Any] = {}
        if ator:
            params["ator"] = ator
        if processo_id is not None:
            params["processo_id"] = processo_id
        try:
            resposta = requests.get(
                f"{self.base}/api/orq/credenciais/{nome}",
                timeout=30,
                headers=_cabecalhos(),
                params=params,
            )
        except requests.RequestException as erro:
            raise ErroRPA(f"Lagoa indisponível: {erro}") from erro

        if resposta.status_code == 404:
            logger.warning(f"[vault] credencial '{nome}' não encontrada (ou sem permissão)")
            return None
        resposta.raise_for_status()
        return resposta.json().get("credencial")

    def credencial(self, usuario: str, senha: str) -> tuple[str | None, str | None]:
        """Busca um par usuário/senha de uma vez."""
        return self.obter(usuario), self.obter(senha)

    def definir(
        self,
        nome: str,
        valor: str,
        secreto: bool = True,
        descricao: str | None = None,
        tipo: str | None = None,
        usuario: str | None = None,
        pasta: str | None = None,
    ) -> dict[str, Any]:
        """Cria/atualiza um segredo na Lagoa."""
        resposta = requests.post(
            f"{self.base}/api/orq/assets",
            json={
                "nome": nome,
                "valor": valor,
                "secreto": secreto,
                "descricao": descricao,
                "tipo": tipo,
                "usuario": usuario,
                "pasta": pasta,
            },
            timeout=30,
            headers=_cabecalhos(),
        )
        resposta.raise_for_status()
        logger.success(f"[vault] segredo '{nome}' gravado na Lagoa")
        return resposta.json()

    def rotacionar(self, nome: str, novo_valor: str) -> dict[str, Any] | None:
        """Troca o valor de um segredo (incrementa a versão); ``None`` se não existir."""
        resposta = requests.post(
            f"{self.base}/api/orq/assets/{nome}/rotacionar",
            json={"valor": novo_valor},
            timeout=30,
            headers=_cabecalhos(),
        )
        if resposta.status_code == 404:
            logger.warning(f"[vault] segredo '{nome}' não existe para rotacionar")
            return None
        resposta.raise_for_status()
        logger.success(f"[vault] segredo '{nome}' rotacionado na Lagoa")
        return resposta.json().get("asset")

    def versoes(self, nome: str) -> list[dict[str, Any]]:
        """Histórico de versões de um segredo (valores mascarados)."""
        resposta = requests.get(
            f"{self.base}/api/orq/assets/{nome}/versoes", timeout=30, headers=_cabecalhos()
        )
        resposta.raise_for_status()
        return resposta.json().get("versoes", [])

    def listar(self) -> list[dict[str, Any]]:
        """Lista os segredos (valores mascarados)."""
        resposta = requests.get(
            f"{self.base}/api/orq/assets", timeout=30, headers=_cabecalhos()
        )
        resposta.raise_for_status()
        return resposta.json().get("assets", [])

    def existe(self, nome: str) -> bool:
        """Diz se um segredo existe no cofre."""
        try:
            return (
                requests.get(
                    f"{self.base}/api/orq/assets/{nome}", timeout=30, headers=_cabecalhos()
                ).status_code
                == 200
            )
        except requests.RequestException:
            return False


def obter(nome: str, control_room: str | None = None) -> str | None:
    """Atalho: busca o valor de um segredo no cofre."""
    return Cofre(control_room).obter(nome)


def exigir(nome: str, control_room: str | None = None) -> str:
    """Atalho: busca o valor de um segredo e falha (ErroRPA) se não existir."""
    return Cofre(control_room).exigir(nome)


def buscar_credencial(
    nome: str,
    control_room: str | None = None,
    ator: str | None = None,
    processo_id: int | None = None,
) -> dict[str, Any] | None:
    """Atalho: busca uma credencial completa do cofre."""
    return Cofre(control_room).buscar_credencial(nome, ator=ator, processo_id=processo_id)


def definir(
    nome: str,
    valor: str,
    secreto: bool = True,
    descricao: str | None = None,
    control_room: str | None = None,
) -> dict[str, Any]:
    """Atalho: cria/atualiza um segredo no cofre."""
    return Cofre(control_room).definir(nome, valor, secreto=secreto, descricao=descricao)


def rotacionar(nome: str, novo_valor: str, control_room: str | None = None) -> dict[str, Any] | None:
    """Atalho: rotaciona o valor de um segredo no cofre."""
    return Cofre(control_room).rotacionar(nome, novo_valor)


def credencial(
    usuario: str,
    senha: str,
    control_room: str | None = None,
) -> tuple[str | None, str | None]:
    """Atalho: busca um par usuário/senha do cofre."""
    return Cofre(control_room).credencial(usuario, senha)


__all__ = [
    "Cofre",
    "obter",
    "exigir",
    "buscar_credencial",
    "definir",
    "rotacionar",
    "credencial",
]
