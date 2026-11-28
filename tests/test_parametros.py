"""Testes do carregamento de configuração sem efeitos colaterais."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _rodar(codigo: str, destino: Path) -> str:
    ambiente = os.environ.copy()
    ambiente["RPA_PASTA_DADOS"] = str(destino)
    ambiente.pop("BANCO_MONITOR", None)
    ambiente.pop("BANCO_ORQUESTRADOR", None)
    return subprocess.check_output(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env=ambiente,
        text=True,
    ).strip()


def test_importar_parametros_nao_cria_pastas(tmp_path):
    destino = tmp_path / "dados"
    saida = _rodar("import settings.parametros as p; print(p.PASTA_DATA)", destino)
    assert saida == str(destino)
    assert not destino.exists()


def test_garantir_pastas_cria_sob_demanda(tmp_path):
    destino = tmp_path / "dados"
    _rodar("from settings.parametros import garantir_pastas; garantir_pastas()", destino)
    assert (destino / "input").is_dir()
    assert (destino / "output").is_dir()
    assert (destino / "logs").is_dir()


def test_login_ligado_por_padrao(tmp_path):
    """Lagoa exige login por padrão, igual ao Cloud (override explícito continua)."""
    ambiente = os.environ.copy()
    ambiente["RPA_PASTA_DADOS"] = str(tmp_path / "dados")
    ambiente.pop("LAGOA_AUTH", None)
    ambiente.pop("CONTROL_ROOM_AUTH", None)
    saida = subprocess.check_output(
        [sys.executable, "-c", "import settings.parametros as p; print(p.LAGOA_AUTH)"],
        cwd=RAIZ,
        env=ambiente,
        text=True,
    ).strip()
    assert saida == "True"
