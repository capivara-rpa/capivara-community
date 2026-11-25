"""Registra as automações de teste no catálogo da Lagoa.

Uso::

    python -m bot_test.registrar

Isso cria/atualiza os processos (apontando para ``bot_test.automacoes:...``) e
uma fila de exemplo (``pedidos_teste``) ligada ao processo de fila. Depois é só
disparar pelo painel ou subir um agente::

    python -m core.control_room.agente --maquina maquina-teste --tags teste
    python -m core.control_room.agente --maquina maquina-teste --fila pedidos_teste
"""

from __future__ import annotations

from loguru import logger

from core.control_room import servico
from core.control_room.banco import iniciar_banco

PROCESSOS = [
    {
        "nome": "Teste — Olá mundo",
        "descricao": "Fluxo mais simples: registra logs e finaliza com sucesso.",
        "fluxo": "bot_test.automacoes:ola_mundo",
        "usa_navegador": False,
    },
    {
        "nome": "Teste — Contar até 10",
        "descricao": "Gera vários passos no trace, contando de 1 a 10.",
        "fluxo": "bot_test.automacoes:contar_ate_dez",
        "usa_navegador": False,
    },
    {
        "nome": "Teste — Gerar relatório",
        "descricao": "Cria um arquivo de texto em data/output.",
        "fluxo": "bot_test.automacoes:gerar_relatorio",
        "usa_navegador": False,
    },
    {
        "nome": "Teste — Erro de negócio",
        "descricao": "Falha de propósito (ErroRPA) para ver o status de erro.",
        "fluxo": "bot_test.automacoes:simular_erro_negocio",
        "usa_navegador": False,
    },
    {
        "nome": "Teste — Tarefa longa",
        "descricao": "Demora ~15s para ver a máquina como ocupada.",
        "fluxo": "bot_test.automacoes:tarefa_longa",
        "usa_navegador": False,
    },
    {
        "nome": "Teste — Consultar credencial",
        "descricao": "Lê um asset do vault da Lagoa.",
        "fluxo": "bot_test.automacoes:consultar_credencial",
        "usa_navegador": False,
    },
    {
        "nome": "Teste — Processar item de fila",
        "descricao": "Consome um item da fila 'pedidos_teste' (use agente --fila).",
        "fluxo": "bot_test.automacoes:processar_item",
        "usa_navegador": False,
    },
    {
        "nome": "Teste — Abrir pop-up",
        "descricao": "Abre um pop-up nativo (macOS) para confirmar a execução.",
        "fluxo": "bot_test.automacoes:abrir_popup",
        "usa_navegador": False,
    },
]

NOME_FILA = "pedidos_teste"
NOME_PROCESSO_FILA = "Teste — Processar item de fila"

ITENS_EXEMPLO = [
    {"nome": "Cliente Alfa", "uf": "SP", "valor": 1500.0},
    {"nome": "Cliente Bravo", "uf": "MG", "valor": 2300.5},
    {"nome": "Cliente Charlie", "uf": "SP", "valor": 980.0},
    {"nome": "Cliente Delta", "uf": "RJ", "valor": 4100.0},  # falha de propósito (retry)
]


def registrar() -> None:
    """Cadastra os processos e a fila de teste (idempotente)."""
    iniciar_banco()
    for processo in PROCESSOS:
        servico.criar_processo(**processo)
        logger.success(f"Processo registrado: {processo['nome']}")

    processo_fila = next(
        p for p in servico.listar_processos() if p["nome"] == NOME_PROCESSO_FILA
    )
    fila = servico.criar_fila(
        NOME_FILA,
        descricao="Fila de teste do bot_test (use: agente --fila pedidos_teste)",
        processo_id=processo_fila["id"],
    )
    if servico.listar_itens(fila["id"]):
        logger.info(f"Fila '{NOME_FILA}' já possui itens (nada a fazer).")
    else:
        servico.adicionar_itens(fila["id"], ITENS_EXEMPLO, referencia_campo="nome")
        logger.success(f"Fila '{NOME_FILA}' criada com {len(ITENS_EXEMPLO)} itens.")

    logger.info("Pronto! Dispare os robôs pelo painel ou suba um agente.")


def main() -> None:
    registrar()


if __name__ == "__main__":
    main()
