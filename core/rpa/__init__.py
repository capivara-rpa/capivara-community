"""Motor low-code de RPA: web, dados, arquivos, API, e-mail e utilidades.

Facilita o uso de bibliotecas complexas (Selenium, pandas, requests...)
através de funções descritivas em português: texto, validação BR, banco,
segurança, sistema, notificações e muito mais.

Os módulos são carregados sob demanda (PEP 562). Assim, quem usa apenas
``texto`` ou ``validacao`` não precisa instalar Selenium/pandas.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = [
    "arquivo",
    "banco",
    "dados",
    "email",
    "fila",
    "interacao",
    "notificacoes",
    "seguranca",
    "sistema",
    "texto",
    "tracktab",
    "validacao",
    "vault",
    "ClienteAPI",
    "api_delete",
    "api_download",
    "api_get",
    "api_patch",
    "api_post",
    "api_put",
    "api_upload",
    "Navegador",
]

_MODULOS = {
    "arquivo",
    "banco",
    "dados",
    "email",
    "fila",
    "interacao",
    "notificacoes",
    "seguranca",
    "sistema",
    "texto",
    "tracktab",
    "validacao",
    "vault",
}

_FUNCOES = {
    "ClienteAPI": "core.rpa.api",
    "api_delete": "core.rpa.api",
    "api_download": "core.rpa.api",
    "api_get": "core.rpa.api",
    "api_patch": "core.rpa.api",
    "api_post": "core.rpa.api",
    "api_put": "core.rpa.api",
    "api_upload": "core.rpa.api",
    "Navegador": "core.rpa.browser",
}


def __getattr__(nome: str) -> Any:  # noqa: ANN401
    """Carrega módulos/funções só quando forem realmente usados."""
    if nome in _MODULOS:
        modulo = importlib.import_module(f"core.rpa.{nome}")
        globals()[nome] = modulo
        return modulo

    if nome in _FUNCOES:
        modulo = importlib.import_module(_FUNCOES[nome])
        valor = getattr(modulo, nome)
        globals()[nome] = valor
        return valor

    raise AttributeError(f"module 'core.rpa' has no attribute {nome!r}")
