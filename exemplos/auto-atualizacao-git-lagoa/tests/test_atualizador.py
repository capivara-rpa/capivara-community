"""Testes do polling de atualização de automações via repositório Git."""

from types import SimpleNamespace

import json

from core.control_room import atualizador
from core.control_room import pacote
from core.control_room import servico

URL = "https://github.com/org/robo-teste.git"


def _origem(tmp_path):
    pasta = tmp_path / "origem"
    pasta.mkdir()
    (pasta / "rpa.json").write_text(
        json.dumps(
            {
                "nome": "robo_auto",
                "versao": "1.0.0",
                "descricao": "Robô com auto-update",
                "entrada": "main.py",
                "funcao": "rodar",
                "usa_navegador": False,
            }
        ),
        encoding="utf-8",
    )
    (pasta / "main.py").write_text("VERSAO = 1\n", encoding="utf-8")
    return pasta


def _processo():
    return next(p for p in servico.listar_processos() if p["nome"] == "robo_auto")


def test_sha_remoto_le_primeira_coluna_do_ls_remote(monkeypatch):
    chamados = []

    def falso_run(comando, **kwargs):
        chamados.append(comando)
        return SimpleNamespace(
            returncode=0, stdout="abc123def\trefs/heads/main\n", stderr=""
        )

    monkeypatch.setattr(pacote.shutil, "which", lambda _: "/usr/bin/git")
    monkeypatch.setattr(pacote.subprocess, "run", falso_run)

    assert pacote.sha_remoto(URL, "main") == "abc123def"
    assert chamados[0][:3] == ["git", "ls-remote", URL]
    assert chamados[0][-1] == "refs/heads/main"


def test_instalacao_atomica_preserva_venv_e_registra_sha(tmp_path):
    origem = _origem(tmp_path)
    destino = tmp_path / "robos"

    pacote._instalar_do_diretorio(
        origem, destino, origem=URL, origem_ref="main", commit_sha="aaa111"
    )
    instalado = destino / "robo_auto"
    venv = instalado / ".venv"
    venv.mkdir()
    (venv / "marcador.txt").write_text("venv original", encoding="utf-8")

    (origem / "main.py").write_text("VERSAO = 2\n", encoding="utf-8")
    pacote._instalar_do_diretorio(
        origem,
        destino,
        origem=URL,
        origem_ref="main",
        substituir=True,
        commit_sha="bbb222",
    )

    assert (instalado / "main.py").read_text(encoding="utf-8") == "VERSAO = 2\n"
    assert (venv / "marcador.txt").read_text(encoding="utf-8") == "venv original"
    assert not [p for p in destino.iterdir() if p.name.startswith(".rpa-")]
    assert _processo()["commit_sha"] == "bbb222"


def test_verificar_atualizacoes_ignora_sha_igual(monkeypatch):
    processo = servico.criar_processo(
        "robo_auto", "", "app.robos.robo_auto.main:rodar", origem=URL,
        origem_ref="main", commit_sha="abc123",
    )
    servico.definir_auto_atualizar(processo["id"], True)
    monkeypatch.setattr(pacote, "sha_remoto", lambda url, ref: "abc123")
    monkeypatch.setattr(
        pacote,
        "atualizar_git",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria clonar")),
    )

    resultado = atualizador.verificar_atualizacoes()

    assert resultado == {"verificados": 1, "atualizados": 0, "ignorados": 1, "erros": 0}


def test_verificar_atualizacoes_atualiza_e_grava_sha(monkeypatch):
    processo = servico.criar_processo(
        "robo_auto", "", "app.robos.robo_auto.main:rodar", origem=URL,
        origem_ref="main", commit_sha="abc123",
    )
    servico.definir_auto_atualizar(processo["id"], True)
    chamados = []
    monkeypatch.setattr(pacote, "sha_remoto", lambda url, ref: "def456")
    monkeypatch.setattr(
        pacote,
        "atualizar_git",
        lambda url, ref: chamados.append((url, ref)) or {},
    )

    resultado = atualizador.verificar_atualizacoes()

    assert resultado["atualizados"] == 1
    assert chamados == [(URL, "main")]
    atualizado = _processo()
    assert atualizado["commit_sha"] == "def456"
    assert atualizado["ultimo_erro"] is None
    assert atualizado["ultima_atualizacao"]


def test_verificar_atualizacoes_registra_erro(monkeypatch):
    processo = servico.criar_processo(
        "robo_auto", "", "app.robos.robo_auto.main:rodar", origem=URL
    )
    servico.definir_auto_atualizar(processo["id"], True)

    def falhar(url, ref):
        raise RuntimeError("repo fora do ar")

    monkeypatch.setattr(pacote, "sha_remoto", falhar)

    resultado = atualizador.verificar_atualizacoes()

    assert resultado["erros"] == 1
    assert "repo fora do ar" in _processo()["ultimo_erro"]


def test_auto_atualizar_so_lista_processos_marcados():
    com_git = servico.criar_processo(
        "robo_auto", "", "app.robos.robo_auto.main:rodar", origem=URL
    )
    servico.criar_processo("robo_zip", "", "app.robos.robo_zip.main:rodar")
    servico.definir_auto_atualizar(com_git["id"], True)

    automaticos = servico.listar_processos_auto_atualizar()

    assert [p["nome"] for p in automaticos] == ["robo_auto"]
