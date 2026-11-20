"""Polling de repositórios Git das automações instaladas na Lagoa.

A Lagoa consulta ``git ls-remote`` das automações marcadas como auto-atualizáveis
e troca o código quando o SHA da branch muda. O gate é o SHA gravado no processo:
se não mudou, nada é clonado. Cada troca é atômica e preserva o ``.venv`` do robô.
"""

from __future__ import annotations

import threading
import time

from loguru import logger

from core.control_room import pacote
from core.control_room import servico
from settings.parametros import INTERVALO_ATUALIZACAO

_trava = threading.Lock()


def verificar_atualizacoes() -> dict[str, int]:
    """Verifica todas as automações com auto-update ligado.

    Nunca interrompe um job em andamento: a troca é atômica no disco e o
    subprocesso do job já carregou o módulo. O próximo job pega o código novo.
    """
    resultado = {"verificados": 0, "atualizados": 0, "ignorados": 0, "erros": 0}
    if not _trava.acquire(blocking=False):
        logger.debug("[atualizador] verificação anterior ainda em andamento")
        return resultado
    try:
        for processo in servico.listar_processos_auto_atualizar():
            resultado["verificados"] += 1
            processo_id = processo["id"]
            nome = processo["nome"]
            url = processo["origem"]
            ref = processo.get("origem_ref")
            try:
                sha = pacote.sha_remoto(url, ref)
                if sha and sha == processo.get("commit_sha"):
                    resultado["ignorados"] += 1
                    continue
                pacote.atualizar_git(url, ref)
                servico.registrar_resultado_atualizacao(processo_id, sha=sha)
                logger.success(f"[atualizador] '{nome}' atualizado para {sha[:8]}")
                resultado["atualizados"] += 1
            except Exception as erro:  # noqa: BLE001
                servico.registrar_resultado_atualizacao(processo_id, erro=str(erro))
                logger.warning(f"[atualizador] falha ao atualizar '{nome}': {erro}")
                resultado["erros"] += 1
    finally:
        _trava.release()
    return resultado


def iniciar_atualizador() -> None:
    """Sobe a thread de polling (daemon) que roda a cada INTERVALO_ATUALIZACAO."""

    def laco() -> None:
        while True:
            time.sleep(INTERVALO_ATUALIZACAO)
            try:
                verificar_atualizacoes()
            except Exception as erro:  # noqa: BLE001
                logger.warning(f"[atualizador] erro no ciclo de verificação: {erro}")

    threading.Thread(target=laco, name="atualizador-git", daemon=True).start()
