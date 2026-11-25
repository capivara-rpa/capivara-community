"""Roda uma automação de teste localmente (sem Lagoa).

Útil para ver os logs no terminal e a trace no painel de monitoramento::

    python -m bot_test.rodar_local                # roda "ola_mundo"
    python -m bot_test.rodar_local tarefa_longa   # roda uma automação
    python -m bot_test.rodar_local todos          # roda todas as locais
"""

from __future__ import annotations

import sys

from loguru import logger

from bot_test import automacoes
from core.logger import configurar_logger
from core.monitor import Monitor
from core.robo import Robo

LOCAIS = [
    "ola_mundo",
    "contar_ate_dez",
    "gerar_relatorio",
    "simular_erro_negocio",
    "tarefa_longa",
    "consultar_credencial",
]


def rodar(nome: str) -> bool:
    """Executa uma automação sob o monitor, devolvendo ``True`` se deu certo."""
    funcao = automacoes.FLUXOS[nome]
    robo = Robo(nome=nome)
    monitor = Monitor(f"bot_test · {nome}", mensagem="execução local", capturar_logs=True)
    monitor.capturar_logs()
    try:
        sucesso = robo.executar_fluxo(nome, funcao)
    finally:
        robo.finalizar()
        monitor.parar_captura()

    if sucesso:
        monitor.finalizar("execução local concluída")
    else:
        monitor.falha("execução local falhou")
    return sucesso


def main() -> None:
    configurar_logger(nome_processo="bot_test")
    alvo = sys.argv[1] if len(sys.argv) > 1 else "ola_mundo"

    if alvo == "todos":
        nomes = LOCAIS
    elif alvo in automacoes.FLUXOS:
        nomes = [alvo]
    else:
        logger.error(
            f"Automação desconhecida: {alvo!r}. "
            f"Opções: {', '.join(automacoes.FLUXOS)} ou 'todos'."
        )
        sys.exit(2)

    resultados = [(nome, rodar(nome)) for nome in nomes]
    logger.info("─" * 50)
    for nome, deu_certo in resultados:
        logger.info(f"{'✓' if deu_certo else '✗'} {nome}")


if __name__ == "__main__":
    main()
