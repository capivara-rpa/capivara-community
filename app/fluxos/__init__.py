"""Fluxos de negócio do robô.

Cada arquivo representa uma ou mais tarefas encadeadas. As funções de fluxo
recebem o parâmetro ``navegador`` (injetado pelo ``Robo``) e retornam ``True``
em caso de sucesso.
"""

from app.fluxos.exemplo_dados import tratar_planilha
from app.fluxos.exemplo_web import buscar_no_google

__all__ = ["tratar_planilha", "buscar_no_google"]