"""Configuração compartilhada dos testes.

Aponta os bancos SQLite para um diretório temporário **antes** de importar o
``core`` (as constantes de caminho são resolvidas no import de
``settings.parametros``) e garante bancos limpos a cada teste.
"""

import os
import tempfile

_DIRETORIO_TMP = tempfile.mkdtemp(prefix="rpa-testes-")
os.environ["BANCO_MONITOR"] = os.path.join(_DIRETORIO_TMP, "monitor.db")
os.environ["BANCO_ORQUESTRADOR"] = os.path.join(_DIRETORIO_TMP, "orquestrador.db")
os.environ["VAULT_CHAVE"] = "senha-de-teste-do-template"
os.environ["VAULT_ARQUIVO_CHAVE"] = os.path.join(_DIRETORIO_TMP, "vault.key")
os.environ["PASTA_ROBOS"] = os.path.join(_DIRETORIO_TMP, "robos")
os.environ["HEADLESS"] = "true"

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def bancos_limpos():
    """Inicializa e limpa os bancos do monitor e da Lagoa a cada teste."""
    from core.control_room import banco as banco_orq
    from core.monitor import banco as banco_mon

    banco_orq.iniciar_banco()
    banco_mon.iniciar_banco()
    banco_orq.apagar_tudo()
    banco_mon.apagar_tudo()
    yield
