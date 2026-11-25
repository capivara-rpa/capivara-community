"""Ponto de entrada do robô.

Executa os fluxos em sequência. Se um fluxo falhar, o processo encerra
(código de saída diferente de zero), facilitando o agendamento.

Uso::

    python app/main.py            # roda todos os fluxos
    python app/main.py --web      # roda só o fluxo web
    python app/main.py --dados    # roda só o fluxo de dados
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no caminho de import
RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from core.logger import configurar_logger, log_titulo  # noqa: E402
from core.robo import Robo  # noqa: E402

from app.fluxos import buscar_no_google, tratar_planilha  # noqa: E402

FLUXOS = {
    "web": ("Busca no Google (navegador)", buscar_no_google),
    "dados": ("Tratamento de dados (pandas)", tratar_planilha),
}


def principal() -> int:
    # 1. Configurar logging colorido
    configurar_logger(nome_processo="capivara")
    log_titulo("Capivara 🦫 — Deixa que a Capivara faz.")

    # 2. Interpretar argumentos: --web / --dados / (padrão = todos)
    permitidos = [arg.lower().lstrip("-") for arg in sys.argv[1:]]
    executar_todos = not any(p in FLUXOS for p in permitidos)

    selecionados = []
    for chave, (nome, funcao) in FLUXOS.items():
        if executar_todos or chave in permitidos:
            selecionados.append((chave, nome, funcao))

    if not selecionados:
        logger_error("Nenhum fluxo válido informado. Use --web, --dados ou nada (todos).")
        return 2

    # 3. Criar o robô
    robo = Robo(nome="rpa-template")

    for chave, nome, funcao in selecionados:
        if chave == "web":
            robo.iniciar()  # só o fluxo web precisa do navegador

        if not robo.executar_fluxo(nome, funcao):
            robo.finalizar()
            return 1

    robo.finalizar()
    return 0


def logger_error(mensagem: str) -> None:
    from loguru import logger

    logger.error(mensagem)


if __name__ == "__main__":
    sys.exit(principal())