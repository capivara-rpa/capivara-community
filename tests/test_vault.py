"""Testes do vault (assets criptografados) e do cliente para robôs."""

from core.control_room import cofre
from core.control_room import servico
from core.rpa import vault


def _asset(nome: str, valor: str, secreto: bool) -> dict:
    return servico.criar_asset(nome, valor, secreto=secreto)


# ----------------------------------------------------------------------
# Motor de cifra (cofre)
# ----------------------------------------------------------------------
def test_cifrar_e_decifrar_arredonda():
    segredo = "portal@s3nh4-forte"
    cifrado = cofre.cifrar(segredo)
    assert cifrado != segredo
    assert cofre.esta_cifrado(cifrado)
    assert cofre.decifrar(cifrado) == segredo
    assert cofre.decifrar(segredo) == segredo  # legado em texto puro passa


def test_assets_secretos_sao_cifrados_no_banco():
    _asset("portal_senha", "m0rra-segredo", secreto=True)
    _asset("portal_usuario", "rpa_bot", secreto=False)

    brutos = _ler_assets_do_banco()
    por_nome = {a["nome"]: a["valor"] for a in brutos}
    assert cofre.esta_cifrado(por_nome["portal_senha"])
    assert not cofre.esta_cifrado(por_nome["portal_usuario"])


def test_listar_mascara_e_obter_decifra():
    _asset("api_key", "abc-123-segredo", secreto=True)

    todos_mascarados = servico.listar_assets(mascarar=True)
    this = next(a for a in todos_mascarados if a["nome"] == "api_key")
    assert this["valor"] == "••••••••"

    saido_limpo = [a for a in servico.listar_assets(mascarar=False) if a["nome"] == "api_key"][0]
    assert saido_limpo["valor"] == "abc-123-segredo"

    obtido = servico.obter_asset("api_key")
    assert obtido["valor"] == "abc-123-segredo"


def test_assets_decifrados_elegiveis_pelo_agente():
    _asset("extrato_senha", "senha-do-banco", secreto=True)
    valor = servico.obter_asset("extrato_senha")["valor"]
    assert valor == "senha-do-banco"
    assert not cofre.esta_cifrado(valor)


# ----------------------------------------------------------------------
# Cliente para robôs (core.rpa.vault)
# ----------------------------------------------------------------------
def test_vault_expõe_cliente_e_atalhos():
    assert hasattr(vault, "Cofre")
    assert hasattr(vault, "obter")
    assert hasattr(vault, "definir")
    # Não toca em rede; só garante que a API existe para os fluxos.
    assert callable(vault.Cofre)


def _ler_assets_do_banco() -> list[dict]:
    from core.control_room.banco import conectar

    with conectar() as conexao:
        return [
            {"nome": linha["nome"], "valor": linha["valor"]}
            for linha in conexao.execute("SELECT nome, valor FROM assets ORDER BY nome")
        ]