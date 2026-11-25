"""Pacote ``core``: motor genérico (camada reutilizável/diretamente códigos low-code).

Composto por:
- ``logger``    -> logging colorido (Loguru)
- ``robo``      -> orquestrador das tarefas
- ``tratador``  -> decoradores de passos, retry e exceções
- ``rpa``       -> motor low-code (web, dados, arquivos, API, e-mail e filas)

Para não forçar o carregamento de dependências pesadas (Selenium/pandas)
em binários que só servem a Lagoa, os atalhos são carregados sob
demanda via ``__getattr__`` (PEP 562).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "configurar_logger",
    "Robo",
    "ErroCriticoRPA",
    "ErroRPA",
    "passo",
    "tentar_novamente",
]

_CARREGAR: dict[str, str] = {
    "configurar_logger": "core.logger",
    "Robo": "core.robo",
    "ErroCriticoRPA": "core.tratador",
    "ErroRPA": "core.tratador",
    "passo": "core.tratador",
    "tentar_novamente": "core.tratador",
}


def __getattr__(nome: str) -> Any:  # noqa: ANN401
    if nome in _CARREGAR:
        import importlib

        modulo = importlib.import_module(_CARREGAR[nome])
        return getattr(modulo, nome)
    raise AttributeError(f"module 'core' has no attribute {nome!r}")