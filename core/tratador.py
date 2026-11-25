"""Tratamento de erros e decoradores úteis para os robôs.

- :class:`ErroRPA`: erro controlado (esperado no fluxo).
- :class:`ErroCriticoRPA`: erro que deve encerrar o processo inteiro.
- :func:`passo`: registra início/fim de cada passo automaticamente.
- :func:`tentar_novamente`: repete uma função com tolerância a falhas.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import TypeVar

from loguru import logger

T = TypeVar("T")


class ErroRPA(Exception):
    """Erro controlado do robô: esperado e tratável dentro do fluxo."""


class ErroCriticoRPA(Exception):
    """Erro que impede a continuidade do processo (encerra o robô)."""


def passo(descricao: str) -> Callable:
    """Decorator que registra o andamento de um passo no log.

    Exemplo::

        @passo("Preencher formulário de login")
        def fazer_login(navegador):
            ...
    """

    def decorador(func: Callable) -> Callable:
        @functools.wraps(func)
        def envolve(*args, **kwargs) -> T:
            logger.info(f"► Passo: {descricao}")
            try:
                resultado = func(*args, **kwargs)
            except Exception as erro:
                logger.error(f"✗ Falha no passo '{descricao}': {erro}")
                raise

            if resultado is False:
                logger.error(f"✗ Passo '{descricao}' retornou falha")
            else:
                logger.success(f"✓ Passo concluído: {descricao}")
            return resultado

        return envolve

    return decorador


def tentar_novamente(
    vezes: int = 3,
    espera: float = 1.0,
    excecoes: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator que repete uma função até N vezes diante de exceções.

    Exemplo::

        @tentar_novamente(vezes=3, espera=2)
        def chamada_api(navegador):
            ...
    """

    def decorador(func: Callable) -> Callable:
        @functools.wraps(func)
        def envolve(*args, **kwargs) -> T:
            ultimo_erro: Exception | None = None
            for tentativa in range(1, vezes + 1):
                try:
                    return func(*args, **kwargs)
                except excecoes as erro:  # type: ignore[misc]
                    ultimo_erro = erro
                    logger.warning(
                        f"Tentativa {tentativa}/{vezes} falhou"
                        f" ({erro}). Aguardando {espera}s..."
                    )
                    if tentativa < vezes:
                        time.sleep(espera)
            raise ultimo_erro  # type: ignore[misc]

        return envolve

    return decorador