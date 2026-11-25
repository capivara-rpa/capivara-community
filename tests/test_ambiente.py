"""Testes do ambiente isolado por robô (.venv + requirements)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from core.control_room import ambiente


def _fazer_robo(tmp_path: Path, nome: str = "robo_req", requirements: str | None = "pandas\n"):
    pasta = tmp_path / nome
    pasta.mkdir()
    (pasta / "rpa.json").write_text(
        f'{{"nome": "{nome}", "entrada": "main.py", "funcao": "rodar"}}', encoding="utf-8"
    )
    (pasta / "main.py").write_text("def rodar(navegador=None):\n    return True\n", encoding="utf-8")
    if requirements is not None:
        (pasta / "requirements.txt").write_text(requirements, encoding="utf-8")
    return pasta


def test_sem_requirements_dispensa_venv(tmp_path):
    pasta = _fazer_robo(tmp_path, requirements=None)
    assert ambiente.garantir_ambiente("robo_req", pasta) is None
    assert not (pasta / ".venv").exists()


def test_desligado_dispensa_venv(tmp_path, monkeypatch):
    pasta = _fazer_robo(tmp_path)
    monkeypatch.setattr(ambiente.parametros, "INSTALAR_DEPENDENCIAS", False)
    assert ambiente.garantir_ambiente("robo_req", pasta) is None
    assert not (pasta / ".venv").exists()


def test_cria_venv_instala_e_reaproveita(tmp_path, monkeypatch):
    pasta = _fazer_robo(tmp_path)
    chamadas = {"pip": 0, "req": None, "atualizar": None}

    def fake_criar_venv(venv: Path) -> None:
        python = ambiente.python_do_venv(venv)
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_text("")

    def fake_instalar(python: Path, requirements: Path, atualizar_pip: bool = True) -> None:
        chamadas["pip"] += 1
        chamadas["req"] = requirements.name
        chamadas["atualizar"] = atualizar_pip

    monkeypatch.setattr(ambiente, "criar_venv", fake_criar_venv)
    monkeypatch.setattr(ambiente, "_instalar_requirements", fake_instalar)

    python = ambiente.garantir_ambiente("robo_req", pasta)
    assert python == ambiente.python_do_venv(pasta / ".venv")
    assert python.is_file()
    assert chamadas == {"pip": 1, "req": "requirements.txt", "atualizar": True}

    # requirements inalterado -> não reinstala
    ambiente.garantir_ambiente("robo_req", pasta)
    assert chamadas["pip"] == 1

    # requirements mudou -> reinstala
    (pasta / "requirements.txt").write_text("requests\n", encoding="utf-8")
    ambiente.garantir_ambiente("robo_req", pasta)
    assert chamadas["pip"] == 2


def test_rodar_no_venv_executa_fluxo_de_verdade(tmp_path):
    from core.control_room.agente import Agente

    agente = Agente(control_room="http://127.0.0.1:1", maquina="teste", capturar_logs=False)
    job = {
        "id": 1,
        "processo_nome": "Olá",
        "fluxo": "bot_test.automacoes:ola_mundo",
        "usa_navegador": 0,
    }
    sucesso, mensagem = agente._rodar_no_venv(job, Path(sys.executable), None)
    assert sucesso is True
    assert "sucesso" in mensagem


def test_pythonpath_inclui_raiz_do_projeto():
    from core.control_room.agente import RAIZ_PROJETO, Agente

    agente = Agente(control_room="http://127.0.0.1:1", maquina="teste")
    assert str(RAIZ_PROJETO) in agente._pythonpath().split(os.pathsep)
