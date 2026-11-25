"""Ambiente isolado por robô (``.venv`` + ``requirements.txt``).

Quando um robô publicado na Lagoa traz um ``requirements.txt`` na sua
pasta, o agente cria um ambiente virtual só para ele: cria a ``.venv`` (se
ainda não existir), atualiza o ``pip``, instala as dependências e executa o
fluxo nesse interpretador — evitando que um robô quebre o outro por causa de
versões de bibliotecas.

O robô continua rodando a partir do próprio código (``app/robos/<nome>/``);
o que muda é o interpretador usado. Para o robô enxergar o motor low-code
(``core``/``settings``), o agente acrescenta a raiz do projeto e os
``site-packages`` do agente ao ``PYTHONPATH`` do processo filho.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from loguru import logger

from settings import parametros

REQUIREMENTS = "requirements.txt"
_ARQUIVO_MARCADOR = ".rpa-ambiente"
_TIMEOUT_VENV = 120
_TIMEOUT_PIP = 1800


def pasta_venv(pasta_robo: str | Path) -> Path:
    """Caminho do ``.venv`` do robô (dentro da própria pasta do robô)."""
    return Path(pasta_robo) / ".venv"


def python_do_venv(venv: str | Path) -> Path:
    """Interpretador do ``.venv`` (``Scripts`` no Windows, ``bin`` nos demais)."""
    venv = Path(venv)
    if sys.platform.startswith("win"):
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _hash_requirements(arquivo: Path) -> str:
    return hashlib.sha256(arquivo.read_bytes()).hexdigest()


def criar_venv(venv: Path) -> None:
    """Cria o ``.venv`` (com pip) usando o interpretador atual."""
    logger.info(f"[ambiente] criando .venv em {venv} ...")
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv)],
        check=True,
        timeout=_TIMEOUT_VENV,
    )


def _instalar_requirements(
    python: Path, requirements: Path, atualizar_pip: bool = True
) -> None:
    """Atualiza o pip e instala o requirements dentro do ``.venv``."""
    if atualizar_pip:
        logger.info("[ambiente] atualizando o pip do robô...")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            timeout=_TIMEOUT_PIP,
        )
    logger.info(f"[ambiente] instalando dependências de {requirements.name} ...")
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(requirements)],
        check=True,
        timeout=_TIMEOUT_PIP,
    )


def garantir_ambiente(
    nome_robo: str, pasta_robo: str | Path | None = None
) -> Path | None:
    """Garante o ``.venv`` do robô com as dependências instaladas.

    Devolve o interpretador do ``.venv`` (para rodar o robô nele) ou ``None``
    quando o robô dispensa ambiente próprio (sem ``requirements.txt`` ou com
    ``RPA_INSTALAR_DEPENDENCIAS=false``). ``pasta_robo`` default é
    ``PASTA_ROBOS/<nome_robo>``.
    """
    if not parametros.INSTALAR_DEPENDENCIAS:
        return None

    pasta = Path(pasta_robo) if pasta_robo else Path(parametros.PASTA_ROBOS) / nome_robo
    requirements = pasta / REQUIREMENTS
    if not requirements.is_file():
        return None

    venv = pasta_venv(pasta)
    python = python_do_venv(venv)
    if not python.exists():
        criar_venv(venv)

    assinatura = _hash_requirements(requirements)
    marcador = venv / _ARQUIVO_MARCADOR
    if marcador.is_file() and marcador.read_text(encoding="utf-8").strip() == assinatura:
        logger.info("[ambiente] dependências já instaladas (requirements inalterado).")
        return python

    _instalar_requirements(python, requirements)
    venv.mkdir(parents=True, exist_ok=True)
    (venv / _ARQUIVO_MARCADOR).write_text(assinatura, encoding="utf-8")
    logger.success("[ambiente] ambiente do robô pronto.")
    return python


__all__ = [
    "REQUIREMENTS",
    "criar_venv",
    "garantir_ambiente",
    "pasta_venv",
    "python_do_venv",
]
