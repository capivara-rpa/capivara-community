"""Carregamento das variáveis de ambiente (arquivo .env).

Procura por ``.env`` na raiz do projeto e em ``settings/``.
Qualquer valor já presente no sistema operacional tem prioridade.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_CARREGADO = False


def carregar_variaveis() -> Path | None:
    """Carrega os arquivos ``.env`` e retorna o caminho do primeiro encontrado."""
    global _CARREGADO

    if _CARREGADO:
        return None

    raiz = Path(__file__).resolve().parents[1]
    caminhos = [raiz / ".env", Path(__file__).resolve().parent / ".env"]

    carregado: Path | None = None
    for caminho in caminhos:
        if caminho.exists():
            load_dotenv(caminho, override=False)
            carregado = caminho

    _CARREGADO = True
    return carregado