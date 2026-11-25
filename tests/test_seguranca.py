"""Testes do módulo de segurança: hash de senha e tokens."""

import re

from core.control_room import seguranca


def test_hash_senha_gera_formato_esperado():
    guardado = seguranca.hash_senha("minha-senha")
    assert guardado.startswith("pbkdf2_sha256$")
    assert re.match(r"^pbkdf2_sha256\$\d+\$[0-9a-f]+\$[0-9a-f]+$", guardado)


def test_conferir_senha_aceita_correta_e_recusa_errada():
    guardado = seguranca.hash_senha("senha-certa")
    assert seguranca.conferir_senha("senha-certa", guardado)
    assert not seguranca.conferir_senha("senha-errada", guardado)


def test_conferir_senha_e_estavel_entre_hashes():
    a = seguranca.hash_senha("mesma")
    b = seguranca.hash_senha("mesma")
    assert a != b  # salt aleatório
    assert seguranca.conferir_senha("mesma", a)
    assert seguranca.conferir_senha("mesma", b)


def test_gerar_token_e_hash_token():
    token = seguranca.gerar_token()
    assert len(token) > 20
    assert seguranca.hash_token(token) == seguranca.hash_token(token)


def test_token_confere_tempo_constante():
    token = seguranca.gerar_token()
    guardado = seguranca.hash_token(token)
    assert seguranca.token_confere(token, guardado)
    assert not seguranca.token_confere("outro-token", guardado)
    assert not seguranca.token_confere("", guardado)
