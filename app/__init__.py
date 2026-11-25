"""Componentes da aplicação: o código dos seus robôs.

- ``main.py``     -> ponto de entrada / orquestração dos fluxos
- ``fluxos/``     -> cada tarefa de negócio em um arquivo
"""

from pathlib import Path

RAIZ_APP = Path(__file__).resolve().parent