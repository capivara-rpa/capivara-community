"""Biblioteca pública da Capivara.

A distribuição PyPI chama-se ``capivara-rpa``; o import é ``capivara_rpa``
para não colidir com o pacote antigo ``capivara`` existente no PyPI.

Exemplo::

    from capivara_rpa import texto

    texto.slug("Relatório de Clientes 2026")
"""

from __future__ import annotations

import importlib
from typing import Any

from core.rpa import __all__ as _ALL_RPA

__version__ = "1.2.0"

__all__ = [
    *_ALL_RPA,
    "ErroCriticoRPA",
    "ErroRPA",
    "Robo",
    "configurar_logger",
    "passo",
    "tentar_novamente",
]

_CORE = {
    "Robo": "core.robo",
    "configurar_logger": "core.logger",
}

_TRATADOR = {
    "ErroCriticoRPA",
    "ErroRPA",
    "passo",
    "tentar_novamente",
}


def __getattr__(nome: str) -> Any:  # noqa: ANN401
    """Expõe o motor RPA e os erros sem carregar dependências pesadas."""
    if nome in _ALL_RPA:
        rpa = importlib.import_module("core.rpa")
        valor = getattr(rpa, nome)
        globals()[nome] = valor
        return valor

    if nome in _CORE:
        modulo = importlib.import_module(_CORE[nome])
        valor = getattr(modulo, nome)
        globals()[nome] = valor
        return valor

    if nome in _TRATADOR:
        tratador = importlib.import_module("core.tratador")
        valor = getattr(tratador, nome)
        globals()[nome] = valor
        return valor

    raise AttributeError(f"module 'capivara_rpa' has no attribute {nome!r}")
