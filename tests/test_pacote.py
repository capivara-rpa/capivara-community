"""Testes do empacotamento e instalação de robôs em .zip (padrão BotCity)."""

from pathlib import Path

import json
import zipfile

import pytest

from core.control_room import pacote
from core.control_room import servico


MANIFESTO = {
    "nome": "cliente_mock",
    "versao": "1.0.0",
    "descricao": "Robô de exemplo",
    "entrada": "main.py",
    "funcao": "rodar",
    "usa_navegador": False,
}


@pytest.fixture
def robo(tmp_path):
    pasta = tmp_path / "robo"
    pasta.mkdir()
    (pasta / "rpa.json").write_text(json.dumps(MANIFESTO), encoding="utf-8")
    (pasta / "main.py").write_text(
        "from core.rpa import dados\n\n"
        "def rodar(navegador=None, item=None):\n"
        "    return True\n",
        encoding="utf-8",
    )
    (pasta / "aux.txt").write_text("dado auxiliar", encoding="utf-8")
    return pasta


def _destino_robos(robo) -> str:
    return str(robo.parent / "robos-instalados")


def _processo_por_nome(nome: str) -> dict:
    return next(p for p in servico.listar_processos() if p["nome"] == nome)


def test_empacotar_cria_zip_com_manifesto(robo):
    zipado = pacote.empacotar(str(robo))
    assert zipado.name == "cliente_mock.zip"
    assert zipado.exists()
    with zipfile.ZipFile(zipado) as zipado_aberto:
        nomes = zipado_aberto.namelist()
    assert "rpa.json" in nomes
    assert "main.py" in nomes


def test_instalar_zip_extrai_e_registra_processo(robo):
    zipado = pacote.empacotar(str(robo))
    destino = _destino_robos(robo)
    resultado = pacote.instalar_zip(zipado, pasta_robos=destino)

    assert resultado["nome"] == "cliente_mock"
    assert resultado["versao"] == "1.0.0"

    pasta_instalada = _pasta_instalada(robo)
    assert (pasta_instalada / "rpa.json").is_file()
    assert (pasta_instalada / "main.py").is_file()
    assert (pasta_instalada / "aux.txt").is_file()

    processo = _processo_por_nome("cliente_mock")
    assert processo["fluxo"] == "app.robos.cliente_mock.main:rodar"
    assert processo["usa_navegador"] == 0


def test_entrada_em_subpasta_gera_fluxo_com_pacotes(tmp_path):
    manifest = {**MANIFESTO, "nome": "robo_pastas", "entrada": "src/main.py"}
    pasta = tmp_path / "robo_pastas"
    (pasta / "src" / "functions").mkdir(parents=True)
    (pasta / "rpa.json").write_text(json.dumps(manifest), encoding="utf-8")
    (pasta / "src" / "main.py").write_text(
        "from .functions.aux import valor\n\ndef rodar():\n    return valor()\n",
        encoding="utf-8",
    )
    (pasta / "src" / "functions" / "aux.py").write_text(
        "def valor():\n    return True\n", encoding="utf-8"
    )

    destino = tmp_path / "robos"
    zipado = pacote.empacotar(str(pasta))
    pacote.instalar_zip(zipado, pasta_robos=str(destino))

    processo = _processo_por_nome("robo_pastas")
    assert processo["fluxo"] == "app.robos.robo_pastas.src.main:rodar"
    assert (destino / "robo_pastas" / "src" / "functions" / "aux.py").is_file()


def test_reinstalar_mesmo_robo_falha(robo):
    destino = _destino_robos(robo)
    zipado = pacote.empacotar(str(robo))
    pacote.instalar_zip(zipado, pasta_robos=destino)
    with pytest.raises(ValueError, match="já instalado"):
        pacote.instalar_zip(zipado, pasta_robos=destino)


def test_nome_invalido_no_manifesto_falha(tmp_path):
    pasta = tmp_path / "robo"
    pasta.mkdir()
    (pasta / "rpa.json").write_text(
        json.dumps({**MANIFESTO, "nome": "inválido espaço"}), encoding="utf-8"
    )
    (pasta / "main.py").write_text("def rodar():\n    pass\n", encoding="utf-8")

    with pytest.raises(ValueError, match="nome"):
        pacote.empacotar(str(pasta))


def test_manifesto_incompleto_falha(tmp_path):
    pasta = tmp_path / "robo"
    pasta.mkdir()
    (pasta / "rpa.json").write_text(json.dumps({"nome": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="incompleto"):
        pacote.empacotar(str(pasta))


def test_pacote_com_senha_exige_senha_para_instalar(robo):
    destino = _destino_robos(robo)
    zipado = pacote.empacotar(str(robo), senha="segredo-123")

    with pytest.raises((RuntimeError, ValueError)):
        pacote.instalar_zip(zipado, pasta_robos=destino)  # sem senha

    resultado = pacote.instalar_zip(zipado, senha="segredo-123", pasta_robos=destino)
    assert resultado["nome"] == "cliente_mock"


def test_zip_sem_manifesto_e_recusado(tmp_path):
    vazio = tmp_path / "vazio.zip"
    with zipfile.ZipFile(vazio, "w"):
        pass
    with pytest.raises((ValueError, KeyError)):
        pacote.instalar_zip(str(vazio), pasta_robos=str(tmp_path / "robos"))


def test_remover_desinstala_e_tira_do_catalogo(robo):
    destino = _destino_robos(robo)
    zipado = pacote.empacotar(str(robo))
    pacote.instalar_zip(zipado, pasta_robos=destino)
    assert _pasta_instalada(robo).exists()

    resultado = pacote.remover("cliente_mock", pasta_robos=destino)
    assert resultado["removido"] is True
    assert not _pasta_instalada(robo).exists()
    assert all(p["nome"] != "cliente_mock" for p in servico.listar_processos())

    with pytest.raises(ValueError, match="não encontrado"):
        pacote.remover("cliente_mock", pasta_robos=destino)


def _pasta_instalada(robo) -> Path:
    return Path(_destino_robos(robo)) / "cliente_mock"


# ----------------------------------------------------------------------
# Instalação a partir de repositório Git (público)
# ----------------------------------------------------------------------
def test_validar_url_git_aceita_https_e_barra_o_resto():
    assert pacote._validar_url_git("https://github.com/u/r.git").startswith("https://")
    # localhost via http é permitido (dev/CI)
    assert pacote._validar_url_git("http://127.0.0.1:8901/r.git").startswith("http://")
    assert pacote._validar_url_git("http://localhost/r.git").startswith("http://")
    for ruim in (
        "file:///etc/passwd",
        "git@github.com:u/r.git",
        "http://x.com/r.git",
        "-u x",
        "ssh://git@host/r.git",
    ):
        with pytest.raises(ValueError, match="inválida"):
            pacote._validar_url_git(ruim)


def test_validar_ref_git_barra_injecao():
    assert pacote._validar_ref("main") == "main"
    assert pacote._validar_ref("feature/x") == "feature/x"
    assert pacote._validar_ref("") is None
    assert pacote._validar_ref(None) is None
    for ruim in ("-x", "..", "a b", "a;rm"):
        with pytest.raises(ValueError, match="inválido"):
            pacote._validar_ref(ruim)


def test_instalar_do_diretorio_registra_origem_e_remove_git(tmp_path, robo):
    destino = tmp_path / "robos"
    (robo / ".git").mkdir()  # simula o repo clonado
    (robo / ".git" / "config").write_text("[core]", encoding="utf-8")

    resultado = pacote._instalar_do_diretorio(
        robo, destino, origem="https://github.com/u/r.git", origem_ref="v1"
    )

    assert resultado["nome"] == "cliente_mock"
    assert resultado["origem"] == "https://github.com/u/r.git"
    assert resultado["origem_ref"] == "v1"
    assert not (destino / "cliente_mock" / ".git").exists()

    processo = _processo_por_nome("cliente_mock")
    assert processo["origem"] == "https://github.com/u/r.git"
    assert processo["origem_ref"] == "v1"


def test_instalar_do_diretorio_substitui_quando_pedido(tmp_path, robo):
    destino = tmp_path / "robos"
    pacote._instalar_do_diretorio(robo, destino, origem="https://github.com/u/r.git")
    with pytest.raises(ValueError, match="já instalado"):
        pacote._instalar_do_diretorio(robo, destino)

    # altera o conteúdo e reinstala substituindo
    (robo / "aux.txt").write_text("versão 2", encoding="utf-8")
    pacote._instalar_do_diretorio(robo, destino, origem="https://github.com/u/r.git", substituir=True)
    assert (destino / "cliente_mock" / "aux.txt").read_text(encoding="utf-8") == "versão 2"


def test_instalar_git_clona_e_instala(tmp_path, robo, monkeypatch):
    """Simula o clone copiando um repo local para a pasta de destino do _clonar."""
    destino = tmp_path / "robos"

    def clone_falso(url, ref, pasta):  # noqa: ANN001
        assert url == "https://github.com/u/r.git"
        assert ref == "main"
        import shutil

        shutil.copytree(robo, pasta)

    monkeypatch.setattr(pacote, "_clonar", clone_falso)
    resultado = pacote.instalar_git("https://github.com/u/r.git", ref="main", pasta_robos=str(destino))

    assert resultado["nome"] == "cliente_mock"
    assert resultado["origem"] == "https://github.com/u/r.git"
    assert resultado["origem_ref"] == "main"


def test_atualizar_git_substitui_versao(tmp_path, robo, monkeypatch):
    destino = tmp_path / "robos"
    import shutil

    monkeypatch.setattr(pacote, "_clonar", lambda url, ref, pasta: shutil.copytree(robo, pasta))
    pacote.instalar_git("https://github.com/u/r.git", pasta_robos=str(destino))

    (robo / "aux.txt").write_text("novo", encoding="utf-8")
    resultado = pacote.atualizar_git("https://github.com/u/r.git", pasta_robos=str(destino))

    assert resultado["nome"] == "cliente_mock"
    assert (destino / "cliente_mock" / "aux.txt").read_text(encoding="utf-8") == "novo"