"""Testes da fachada pública ``capivara_rpa`` e do import lazy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import capivara_rpa
from capivara_rpa import ClienteAPI, ErroRPA, Robo, configurar_logger, texto, validacao
from capivara_rpa.cli import main

RAIZ = Path(__file__).resolve().parents[1]


def test_versao_e_all_publico():
    assert capivara_rpa.__version__ == "1.2.0"
    assert "texto" in capivara_rpa.__all__
    assert "validacao" in capivara_rpa.__all__
    assert "Navegador" in capivara_rpa.__all__
    assert "ErroRPA" in capivara_rpa.__all__


def test_import_texto_e_validacao():
    assert texto.slug("Relatório de Clientes 2026") == "relatorio-de-clientes-2026"
    assert validacao.validar_cpf("529.982.247-25") is True
    assert validacao.validar_cpf("111.111.111-11") is False


def test_import_api_e_erro():
    assert ClienteAPI.__name__ == "ClienteAPI"
    assert issubclass(ErroRPA, Exception)


def test_import_robo_e_logger():
    assert Robo.__name__ == "Robo"
    assert callable(configurar_logger)


def test_import_nao_carrega_dependencias_pesadas():
    codigo = (
        "import sys, capivara_rpa; "
        "print(int('selenium' in sys.modules), int('pandas' in sys.modules))"
    )
    saida = subprocess.check_output(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        text=True,
    ).strip()
    assert saida == "0 0"


def test_cli_ajuda_e_listagem(capsys):
    assert main([]) == 0
    ajuda = capsys.readouterr().out
    assert "RPA low-code" in ajuda

    assert main(["--listar"]) == 0
    listagem = capsys.readouterr().out
    assert "texto" in listagem
    assert "validacao" in listagem


def test_cli_version_por_modulo():
    resultado = subprocess.run(
        [sys.executable, "-m", "capivara_rpa", "--version"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0
    assert "capivara 1.2.0" in resultado.stdout
