"""Motor de logging colorido do template.

Configura o Loguru com níveis coloridos no terminal e registro em arquivo
com rotação diária. Chame :func:`configurar_logger` uma única vez (no
``main.py`` ou na criação do robô).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from loguru import logger

from settings.parametros import NIVEL_LOG, NOME_LOG, PASTA_LOGS, garantir_pastas

# Formato do console: hora + nível colorido + mensagem
_FORMATO_CONSOLE = (
    "<cyan>{time:HH:mm:ss.SSS}</cyan> "
    "| <level>{level: <8}</level> "
    "| <level>{message}</level>"
)

# Formato do arquivo: completo, sem cores (com origem do log)
_FORMATO_ARQUIVO = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} "
    "| {level: <8} "
    "| {name}:{function} "
    "| {message}"
)

_CONFIGURADO = False

# ----------------------------------------------------------------------
# Redação de segredos (defesa em profundidade)
# Nada sensível deve cair no log. Mesmo assim, se um valor escapar por
# engano (ex.: um payload impresso), este padrão o mascara antes de
# qualquer sink (console/arquivo) escrever a mensagem.
# ----------------------------------------------------------------------
_PADRAO_SEGREDO = re.compile(
    r"""(?i)"""
    r"""(?P<chave>["']?(?:senha|password|passwd|token|secret|segredo|api[_-]?key|chave|valor)["']?)"""
    r"""(?P<sep>\s*[:=]\s*)"""
    r"""(?P<valor>"[^"]*"|'[^']*'|[^\s,;]+)"""
)


def redigir(texto: str) -> str:
    """Mascara valores de segredos que tenham vazado para uma mensagem de log."""
    if not texto:
        return texto
    return _PADRAO_SEGREDO.sub(lambda m: f"{m.group('chave')}{m.group('sep')}***", texto)


def _redigir_registro(registro) -> None:  # noqa: ANN001 (assinatura do Loguru)
    """Patcher do Loguru: aplica :func:`redigir` à mensagem de cada registro."""
    registro["message"] = redigir(registro["message"])


def configurar_logger(nome_processo: str = "rpa") -> None:
    """Configura o logger (console colorido + arquivo com rotação).

    Só realiza a configuração uma vez por execução.
    """
    global _CONFIGURADO

    if _CONFIGURADO:
        return

    garantir_pastas()

    # Remover o handler padrão para termos controle total no formato
    logger.remove()

    # Redação global: nenhum sink escreve segredos que escapem para a mensagem
    logger.configure(patcher=_redigir_registro)

    # Cores de cada nível
    logger.level("DEBUG", color="<dim><white>")
    logger.level("INFO", color="<cyan>")
    logger.level("SUCCESS", color="<green>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<bold red>")

    # Saída no terminal (colorida)
    logger.add(
        sys.stderr,
        format=_FORMATO_CONSOLE,
        level=NIVEL_LOG,
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # Arquivo de log com rotação e retenção
    arquivo_log: Path = PASTA_LOGS / NOME_LOG
    logger.add(
        arquivo_log,
        format=_FORMATO_ARQUIVO,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    _CONFIGURADO = True
    logger.debug(f"Logger configurado para o processo '{nome_processo}'. Arquivo: {arquivo_log}")


def log_titulo(texto: str, caractere: str = "━") -> None:
    """Imprime um título de seção destacado."""
    linha = caractere * min(len(texto) + 6, 60)
    logger.info(f"\n{linha}\n  {texto}\n{linha}")
