"""Complementos de interação: pausas, digitação pausada e área de transferência.

Uso::

    from core.rpa import interacao

    interacao.dormir(3, motivo="aguardando carregamento da planilha")
    interacao.digitar_pausadamente(navegador, "#nome", "Arthur Faria")
    interacao.copiar_para_area_transferencia("texto qualquer")
"""

from __future__ import annotations

import time

from loguru import logger

try:
    import pyperclip
except ImportError:  # pragma: no cover
    pyperclip = None


def dormir(segundos: float = 1.0, motivo: str | None = None) -> None:
    """Pausa a execução por alguns segundos (opcionalmente com explicação)."""
    if motivo:
        logger.info(f"Aguardando {segundos:.1f}s - {motivo}")
    else:
        logger.debug(f"Aguardando {segundos:.1f}s...")
    time.sleep(segundos)


def aguardar(segundos: float = 1.0) -> None:
    """Alias de :func:`dormir`."""
    dormir(segundos)


def digitar_pausadamente(navegador, seletor, texto: str, pausa: float = 0.05) -> None:
    """Digita um texto caractere por caractere, com pequena pausa.

    Útil para sites que validam a velocidade de digitação ou para
    deixar a automação mais "humana".
    """
    navegador.escrever_texto(seletor, "", limpar=True)
    navegador.pressionar_tecla("DELETE")
    for caractere in str(texto):
        elemento = navegador._localizar_ou_erro(seletor, "digitar pausadamente")
        elemento.send_keys(caractere)
        time.sleep(pausa)
    logger.success(f"Digitação pausada concluída em {seletor}.")


def copiar_para_area_transferencia(texto: str) -> None:
    """Copia um texto para a área de transferência do sistema."""
    if pyperclip is None:
        logger.warning("pyperclip não instalado; instale com 'pip install pyperclip'.")
        return
    pyperclip.copy(texto)
    logger.info("Texto copiado para a área de transferência.")


def colar_para_area_transferencia(navegador, seletor) -> None:
    """Cola o conteúdo da área de transferência em um campo."""
    if pyperclip is None:
        logger.warning("pyperclip não instalado.")
        return
    texto = pyperclip.paste()
    navegador.escrever_texto(seletor, texto)
    logger.success("Texto colado a partir da área de transferência.")