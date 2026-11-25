"""Orquestrador de robôs.

Centraliza a criação do navegador e a execução dos fluxos com logs bonitos.
Cada "fluxo" é uma função que recebe o parâmetro ``navegador`` e retorna
``True`` (sucesso) ou lança uma exceção.

Exemplo::

    from core.robo import Robo
    from core.logger import configurar_logger

    robo = Robo(nome="meu-primeiro-robo")
    if robo.executar_fluxo("Buscar no Google", buscar_no_google):
        logger.success("Tudo certo!")
    robo.finalizar()
"""

from __future__ import annotations

import inspect
from typing import Any
from collections.abc import Callable

from loguru import logger

from core.rpa.browser import Navegador
from core.tratador import ErroCriticoRPA


class Robo:
    """Gerencia o ciclo de vida do robô (navegador + execução de fluxos)."""

    def __init__(
        self,
        nome: str = "robo",
        navegador: Navegador | None = None,
        headless: bool | None = None,
    ) -> None:
        self.nome = nome
        self.navegador = navegador or Navegador(headless=headless)

    # ------------------------------------------------------------------
    def iniciar(self, url: str | None = None) -> None:
        """Abre o navegador (ou apenas prepara o robô)."""
        logger.info(f"Robô '{self.nome}' iniciando...")
        self.navegador.iniciar(url=url)

    def executar_fluxo(
        self,
        nome_fluxo: str,
        funcao: Callable,
        **kwargs: Any,
    ) -> bool:
        """Executa um fluxo (função) tratando erros e registrando logs.

        O ``navegador`` é injetado automaticamente no parâmetro ``navegador``
        da função, caso ela aceite. Argumentos extras (ex.: ``item=...``) só
        são repassados se a função de fluxo os declarar — assim fluxos antigos
        continuam funcionando.

        Retorna ``True`` em caso de sucesso ou ``False`` em caso de falha.
        """
        logger.info("─" * 50)
        logger.info(f"► Iniciando fluxo: {nome_fluxo}")
        logger.info("─" * 50)

        parametros = set(inspect.signature(funcao).parameters)
        extras = {chave: valor for chave, valor in kwargs.items() if chave in parametros}

        try:
            funcionou = funcao(navegador=self.navegador, **extras)
        except ErroCriticoRPA as erro:
            logger.critical(f"Fluxo '{nome_fluxo}' interrompido (erro crítico): {erro}")
            return False
        except Exception as erro:  # noqa: BLE001
            logger.critical(f"Fluxo '{nome_fluxo}' falhou: {erro}")
            return False
        else:
            if funcionou is False:
                logger.error(f"Fluxo '{nome_fluxo}' retornou falha (False).")
                return False
            logger.success(f"✓ Fluxo concluído com sucesso: {nome_fluxo}")
            return True

    def finalizar(self) -> None:
        """Fecha o navegador e finaliza o robô."""
        logger.info(f"Robô '{self.nome}' finalizando...")
        self.navegador.finalizar()
        logger.success(f"Robô '{self.nome}' finalizado com sucesso.")