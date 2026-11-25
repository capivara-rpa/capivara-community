"""Pacote do orquestrador / Lagoa.

Um orquestrador de robôs: cadastra **máquinas**, um catálogo de
**processos** (robôs) e permite **disparar jobs** que os agentes instalados
em cada máquina buscam, executam e devolvem o resultado.

Peças:

- :mod:`core.control_room.banco`  — persistência (SQLite).
- :mod:`core.control_room.servico` — regras de negócio (heartbeat, dispatch...).
- :mod:`core.control_room.servidor` — Lagoa web + painel de trace.
- :mod:`core.control_room.agente` — agente que roda na máquina e executa jobs.

Uso rápido::

    python -m core.control_room.dados_exemplo   # opcional: máquinas/processos/jobs
    python -m core.control_room.servidor        # sobe a Lagoa
    python -m core.control_room.agente --maquina maquina-01
"""

from core.control_room.banco import (
    JOB_CANCELADO,
    JOB_CONCLUIDO,
    JOB_EM_EXECUCAO,
    JOB_FALHOU,
    JOB_PENDENTE,
    MAQUINA_OCUPADA,
    MAQUINA_OFFLINE,
    MAQUINA_ONLINE,
    iniciar_banco,
)

__all__ = [
    "iniciar_banco",
    "MAQUINA_ONLINE",
    "MAQUINA_OCUPADA",
    "MAQUINA_OFFLINE",
    "JOB_PENDENTE",
    "JOB_EM_EXECUCAO",
    "JOB_CONCLUIDO",
    "JOB_FALHOU",
    "JOB_CANCELADO",
]
