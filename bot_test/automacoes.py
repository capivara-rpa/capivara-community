"""Automações de teste para exercitar a Lagoa de ponta a ponta.

Cada função abaixo é um "fluxo" que pode ser cadastrado como processo e
disparado a partir do painel da Lagoa para uma máquina (agente).
O robô injeta automaticamente os parâmetros que a função declarar:

- ``navegador``: o navegador Selenium (criado pela classe ``Robo``);
- ``agente``: o agente em execução — acesso ao vault (``agente.asset``) e item;
- ``item``: o item da fila sendo processado (datapool), quando aplicável.

Cadastre os processos com::

    python -m bot_test.registrar

e depois clique em **Executar** no processo desejado, escolhendo a máquina
(ou deixando "qualquer"). Para ver os logs sem a Lagoa::

    python -m bot_test.rodar_local ola_mundo
"""

from __future__ import annotations

import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from core.tratador import ErroRPA, passo
from settings.parametros import PASTA_OUTPUT


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _pasta_saida() -> Path:
    PASTA_OUTPUT.mkdir(parents=True, exist_ok=True)
    return PASTA_OUTPUT


def ola_mundo(navegador=None) -> bool:
    """O robô mais simples possível: registra logs e encerra com sucesso."""
    logger.info(f"Olá! Sou o robô de teste (execução às {_agora()}).")
    logger.info("Estou rodando a partir de uma máquina da Lagoa.")
    time.sleep(0.5)
    logger.success("Olá mundo concluído sem erros.")
    return True


@passo("Contagem progressiva")
def contar_ate_dez(navegador=None) -> bool:
    """Gera vários passos no trace, contando de 1 a 10."""
    for numero in range(1, 11):
        logger.info(f"Contando... {numero}")
        time.sleep(0.2)
    logger.success("Contei até 10.")
    return True


@passo("Gerar relatório de teste")
def gerar_relatorio(navegador=None) -> bool:
    """Cria um arquivo de texto em ``data/output`` para você conferir."""
    arquivo = _pasta_saida() / f"relatorio_teste_{datetime.now():%Y%m%d_%H%M%S}.txt"
    linhas = [
        "Relatório gerado pelo robô de teste",
        f"Data/hora: {_agora()}",
        f"Total de registros: {random.randint(10, 99)}",
    ]
    arquivo.write_text("\n".join(linhas), encoding="utf-8")
    logger.info(f"Arquivo gerado: {arquivo.name}")
    logger.success(f"Relatório salvo em {arquivo}")
    return True


@passo("Validar cadastro")
def simular_erro_negocio(navegador=None) -> bool:
    """Falha de propósito (erro de negócio) para ver o status de falha."""
    logger.warning("Validando o cadastro recebido...")
    time.sleep(0.3)
    raise ErroRPA("CPF inválido no cadastro (erro de negócio simulado)")


@passo("Tarefa longa")
def tarefa_longa(navegador=None, segundos: int = 15) -> bool:
    """Tarefa demorada, para ver a máquina como 'ocupada' no painel."""
    for restante in range(segundos, 0, -1):
        logger.info(f"Processando... faltam {restante}s")
        time.sleep(1)
    logger.success("Tarefa longa concluída.")
    return True


@passo("Processar item da fila")
def processar_item(navegador=None, agente=None, item=None) -> bool:
    """Consome um item de fila (use com ``agente --fila``).

    Itens com ``uf == "RJ"`` falham de propósito para demonstrar o retry.
    """
    dados = (item or {}).get("dados", {})
    referencia = (
        (item or {}).get("referencia")
        or dados.get("nome")
        or f"item {(item or {}).get('id')}"
    )
    logger.info(f"Processando: {referencia}")
    logger.info(f"Dados recebidos: {dados}")

    if str(dados.get("uf", "")).upper() == "RJ":
        logger.warning("UF 'RJ' marcada para falhar de propósito (teste de retry).")
        return False

    time.sleep(0.5)
    logger.success(f"Item '{referencia}' processado com sucesso.")
    return True


@passo("Abrir pop-up")
def abrir_popup(
    navegador=None,
    mensagem: str = "Olá! Sou um robô rodando nesta máquina via Lagoa.",
    segundos: int = 30,
) -> bool:
    """Abre um pop-up nativo (macOS) para confirmar a execução visualmente.

    Usa o ``osascript`` para mostrar um diálogo na tela da máquina. O pop-up
    fecha sozinho depois de ``segundos`` caso ninguém clique em OK.
    """
    if sys.platform != "darwin":
        logger.warning("Pop-up nativo disponível apenas no macOS; nada a exibir.")
        return True

    titulo = "Capivara - Lagoa"
    script = (
        f'display dialog "{mensagem}" '
        f'buttons {{"OK"}} default button 1 with title "{titulo}" '
        f"giving up after {segundos}"
    )
    logger.info(f"Abrindo pop-up na tela (fecha sozinho em {segundos}s)...")
    resultado = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    saida = (resultado.stdout or resultado.stderr or "").strip()
    logger.info(f"Pop-up retornou: {saida or '(sem saída)'}")
    if resultado.returncode != 0:
        raise ErroRPA(f"Não foi possível exibir o pop-up: {saida}")
    logger.success("Pop-up exibido no Mac.")
    return True


@passo("Consultar credencial no vault")
def consultar_credencial(navegador=None, agente=None) -> bool:
    """Lê uma credencial do vault da Lagoa (demonstra o cofre v2)."""
    if agente is None:
        logger.warning("Sem agente: rodando localmente, pulando leitura do vault.")
        return True

    credencial = agente.credencial("portal")
    if credencial is None:
        logger.warning("Credencial 'portal' não encontrada. Cadastre na Lagoa.")
        return True
    logger.info(
        f"Credencial do vault: usuario={credencial['usuario']!r} "
        f"tipo={credencial['tipo']} v{credencial['versao']}"
    )
    return True


FLUXOS = {
    "ola_mundo": ola_mundo,
    "contar_ate_dez": contar_ate_dez,
    "gerar_relatorio": gerar_relatorio,
    "simular_erro_negocio": simular_erro_negocio,
    "tarefa_longa": tarefa_longa,
    "processar_item": processar_item,
    "consultar_credencial": consultar_credencial,
    "abrir_popup": abrir_popup,
}

__all__ = ["FLUXOS", *FLUXOS]
