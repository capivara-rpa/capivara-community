"""Testes das credenciais v2 (cofre, versões, permissões, auditoria e redação)."""

from core.control_room import banco as banco_orq
from core.control_room import servico
from core.control_room import servidor as servidor_orq
from core.logger import _redigir_registro, redigir


def _criar_processo(nome: str = "Processo Teste") -> dict:
    return servico.criar_processo(nome, "descrição", "app.fluxos:tratar_planilha")


# ----------------------------------------------------------------------
# Fase 0 — redação de segredos no log
# ----------------------------------------------------------------------
def test_redigir_mascara_segredos():
    assert "segredo123" not in redigir('senha="segredo123"')
    assert "abc" not in redigir("token=abc")
    assert "minha-senha" not in redigir('{"usuario":"x","valor":"minha-senha"}')
    assert redigir("mensagem normal") == "mensagem normal"


def test_redigir_registro_limpa_mensagem():
    registro = {"message": "login senha=123456"}
    _redigir_registro(registro)
    assert "123456" not in registro["message"]


# ----------------------------------------------------------------------
# Credenciais v2 (tipos, versões e rotação)
# ----------------------------------------------------------------------
def test_criar_asset_tipo_usuario_versao():
    asset = servico.criar_asset("portal", "s3nh4", usuario="joao", descricao="Portal")
    assert asset["tipo"] == "segredo"
    assert asset["usuario"] == "joao"
    assert asset["versao"] == 1

    atualizado = servico.criar_asset("portal", "nova", usuario="joao")
    assert atualizado["versao"] == 2

    versoes = servico.listar_versoes_asset("portal", mascarar=False)
    assert [v["versao"] for v in versoes] == [2, 1]
    assert versoes[1]["valor"] == "s3nh4"


def test_asset_tipo_texto_nao_cifra():
    asset = servico.criar_asset("regiao", "SP", tipo="texto")
    assert not asset["secreto"]
    assert asset["valor"] == "SP"
    assert banco_orq.obter_asset_por_nome("regiao")["valor"] == "SP"


def test_obter_credencial_retorna_par():
    servico.criar_asset("portal", "s3nh4", usuario="joao")
    credencial = servico.obter_credencial("portal", ator="maq-01")
    assert credencial["usuario"] == "joao"
    assert credencial["senha"] == "s3nh4"
    assert credencial["versao"] == 1


def test_rotacionar_asset_guarda_historico():
    servico.criar_asset("portal", "a", usuario="joao")
    servico.rotacionar_asset("portal", "b", ator="admin")
    assert servico.obter_credencial("portal")["senha"] == "b"
    assert len(servico.listar_versoes_asset("portal")) == 2
    assert servico.rotacionar_asset("inexistente", "x") is None


# ----------------------------------------------------------------------
# Permissões por processo
# ----------------------------------------------------------------------
def test_permissao_por_processo():
    processo = _criar_processo()
    servico.criar_asset("portal", "s", usuario="u")

    # Sem permissões cadastradas, o asset é aberto
    assert servico.obter_credencial("portal", ator="maq") is not None

    servico.conceder_permissao("portal", processo_id=processo["id"], ator="admin")

    # Com permissões, só o processo autorizado acessa
    assert servico.obter_credencial("portal", ator="maq") is None
    assert servico.obter_credencial("portal", ator="maq", processo_id=processo["id"]) is not None

    permissao_id = servico.listar_permissoes_asset("portal")[0]["id"]
    servico.remover_permissao(permissao_id, ator="admin")
    assert servico.obter_credencial("portal", ator="maq") is not None


# ----------------------------------------------------------------------
# Auditoria e revisão
# ----------------------------------------------------------------------
def test_auditoria_registra_acoes():
    servico.criar_asset("portal", "s", usuario="u", ator="admin")
    servico.obter_credencial("portal", ator="maq")
    servico.rotacionar_asset("portal", "n", ator="admin")

    acoes = {evento["acao"] for evento in servico.listar_auditoria()}
    assert {"criar", "ler", "rotacionar"} <= acoes
    assert servico.listar_auditoria(recurso="asset:portal")


def test_revisao_muda_ao_rotacionar():
    servico.criar_asset("portal", "a")
    antes = servico.revisao()
    servico.rotacionar_asset("portal", "b")
    assert servico.revisao() != antes


def test_painel_traz_auditoria_e_asset_info():
    servico.criar_asset("portal", "a")
    painel = servico.montar_painel()
    assert "auditoria" in painel
    assert painel["asset_info"]["tipos"] == ["segredo", "texto"]


# ----------------------------------------------------------------------
# Rotas (token de agente)
# ----------------------------------------------------------------------
def test_rotas_de_credencial_exigem_token():
    assert servidor_orq._rota_de_agente("GET", "/api/orq/credenciais/portal")
    assert not servidor_orq._rota_de_agente("GET", "/api/orq/assets/portal/versoes")
    assert not servidor_orq._rota_de_agente("GET", "/api/orq/assets/portal/auditoria")
    assert not servidor_orq._rota_de_agente("POST", "/api/orq/assets/portal/rotacionar")
    assert not servidor_orq._rota_de_agente("POST", "/api/orq/assets/portal/permissoes")
