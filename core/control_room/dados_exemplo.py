"""Dados de exemplo (mock) para a Lagoa.

Cadastra algumas máquinas, o catálogo de processos e um histórico de jobs
(pendentes, concluídos e com falha) — assim dá para ver a Lagoa cheia
e testar o despacho com um agente de verdade.

Uso::

    python -m core.control_room.dados_exemplo
"""

from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger

from core.control_room import servico
from core.control_room.banco import (
    JOB_CONCLUIDO,
    JOB_FALHOU,
    apagar_tudo,
    conectar,
    iniciar_banco,
)


def _quando(minutos_atras: float) -> str:
    return (datetime.now() - timedelta(minutes=minutos_atras)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _processo_id(nome: str) -> int:
    return next(p["id"] for p in servico.listar_processos() if p["nome"] == nome)


def _job_historico(
    processo_id: int,
    maquina_id: int,
    status: str,
    minutos: float,
    mensagem: str,
) -> None:
    job = servico.criar_job(processo_id, maquina_id)
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE jobs
               SET status = ?, mensagem = ?, iniciado_em = ?, finalizado_em = ?
             WHERE id = ?
            """,
            (status, mensagem, _quando(minutos), _quando(minutos - 1), job["id"]),
        )


def popular(reimprimir: bool = True) -> None:
    """Recria a Lagoa com máquinas, processos e jobs de exemplo."""
    iniciar_banco()
    apagar_tudo()
    servico.garantir_processos_exemplo()

    m1 = servico.registrar_maquina("maquina-01", tags="financeiro,sp", info="Windows Server 2022")
    m2 = servico.registrar_maquina("maquina-02", tags="rh,sp", info="Ubuntu 24.04")
    m3 = servico.registrar_maquina("maquina-03", tags="dados", info="VM no Docker")

    p_web = _processo_id("Google — Busca (web)")
    p_dados = _processo_id("Dados — Tratar planilha")

    # Jobs pendentes (os agentes vão buscá-los)
    servico.criar_job(p_dados, m1["id"], mensagem="Fechamento do dia")
    servico.criar_job(p_web, m2["id"], mensagem="Busca agendada")
    servico.criar_job(p_dados, None, mensagem="Qualquer máquina")
    servico.criar_job(p_dados, None, requisito_tag="sp", mensagem="Fila financeiro (pool: sp)")

    # Histórico
    _job_historico(p_dados, m1["id"], JOB_CONCLUIDO, 120, "Fechamento de ontem concluído")
    _job_historico(p_dados, m3["id"], JOB_FALHOU, 60, "CSV de entrada vazio")

    # Agendamentos (triggers)
    servico.criar_trigger(p_dados, tipo="intervalo", intervalo_min=30, requisito_tag="sp")
    servico.criar_trigger(p_web, tipo="diario", hora="06:00")

    # Assets (credenciais centralizadas)
    servico.criar_asset("portal_usuario", "rpa_bot", secreto=False, descricao="Usuário do portal")
    servico.criar_asset("portal_senha", "troque-esta-senha", secreto=True, descricao="Senha do portal")
    # Credencial completa (usuário + senha em um só asset, com auditoria):
    servico.criar_asset(
        "portal", "troque-esta-senha", usuario="rpa_bot", descricao="Credencial do portal"
    )

    # Fila de processamento (datapool)
    fila = servico.criar_fila(
        "clientes",
        descricao="Cadastros para o robô tratar (exemplo)",
        processo_id=p_dados,
    )
    servico.adicionar_itens(
        fila["id"],
        [
            {"nome": "ACME Ltda", "uf": "SP", "vendas": 4520.0},
            {"nome": "XPTO S.A", "uf": "RJ", "vendas": 3180.0},
            {"nome": "Zeta Eireli", "uf": "MG", "vendas": 2013.5},
            {"nome": "Beta Holding", "uf": "SP", "vendas": 9800.0},
        ],
        referencia_campo="nome",
        prioridade=0,
    )

    if reimprimir:
        logger.success(
            "Lagoa populada: 3 máquinas, 2 processos, 6 jobs, "
            "2 agendamentos, 2 assets e 1 fila com 4 itens."
        )


def main() -> None:
    popular()


if __name__ == "__main__":
    main()
