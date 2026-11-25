"""Monitor de execuções (trace dos robôs) do template.

Guarda cada execução e o seu passo a passo num banco SQLite e expõe tudo
num painel web local em HTML/CSS/JS (sem dependências extras além do que o
template já usa).

Uso rápido::

    # 1. Popular com dados de exemplo (mock)
    python -m core.monitor.dados_exemplo

    # 2. Subir o painel
    python -m core.monitor.servidor

    # 3. Abrir http://localhost:8765
"""

from core.monitor.banco import (
    STATUS_ENCERRADO,
    STATUS_ERRO_CRITICO,
    STATUS_ERRO_NEGOCIO,
    STATUS_ERRO_SISTEMICO,
    STATUS_FALHA,
    STATUS_FINALIZADO,
    STATUS_INICIADO,
    STATUS_PROCESSANDO,
    STATUS_VALIDOS,
    iniciar_banco,
)
from core.monitor.monitor import Monitor

__all__ = [
    "Monitor",
    "STATUS_INICIADO",
    "STATUS_PROCESSANDO",
    "STATUS_ERRO_SISTEMICO",
    "STATUS_ERRO_NEGOCIO",
    "STATUS_ERRO_CRITICO",
    "STATUS_FALHA",
    "STATUS_FINALIZADO",
    "STATUS_VALIDOS",
    "STATUS_ENCERRADO",
    "iniciar_banco",
]
