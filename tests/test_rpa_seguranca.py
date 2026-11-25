"""Testes das utilidades de segurança do motor (core.rpa.seguranca)."""

import uuid

import pytest

from core.rpa import seguranca
from core.tratador import ErroRPA


def test_gerar_senha():
    senha = seguranca.gerar_senha(20)
    assert len(senha) == 20
    assert any(c.islower() for c in senha)
    assert any(c.isupper() for c in senha)
    assert any(c.isdigit() for c in senha)
    assert any(not c.isalnum() for c in senha)
    assert len(seguranca.gerar_senha(8, simbolos=False)) == 8
    with pytest.raises(ErroRPA):
        seguranca.gerar_senha(3)


def test_gerar_token_e_uuid():
    token = seguranca.gerar_token(24)
    assert len(token) >= 24
    assert seguranca.gerar_token() != seguranca.gerar_token()
    uuid.UUID(seguranca.gerar_uuid())
    with pytest.raises(ErroRPA):
        seguranca.gerar_token(4)


def test_hashes(tmp_path):
    assert (
        seguranca.hash_sha256("abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    arquivo = tmp_path / "dados.txt"
    arquivo.write_text("conteudo", encoding="utf-8")
    assert seguranca.hash_arquivo(arquivo) == seguranca.hash_sha256("conteudo")
    with pytest.raises(ErroRPA):
        seguranca.hash_arquivo(tmp_path / "nao_existe.txt")
    with pytest.raises(ErroRPA):
        seguranca.hash_arquivo(arquivo, algoritmo="inexistente")


def test_base64():
    codificado = seguranca.base64_codificar("Capivara 🦫")
    assert seguranca.base64_decodificar(codificado) == "Capivara 🦫"
    assert seguranca.base64_decodificar(codificado, como_bytes=True) == "Capivara 🦫".encode()
    with pytest.raises(ErroRPA):
        seguranca.base64_decodificar("***")


def test_criptografia():
    token = seguranca.criptografar_texto("segredo", chave="chave-de-teste")
    assert token != "segredo"
    assert seguranca.descriptografar_texto(token, chave="chave-de-teste") == "segredo"
    with pytest.raises(ErroRPA):
        seguranca.descriptografar_texto(token, chave="outra-chave")
    with pytest.raises(ErroRPA):
        seguranca.descriptografar_texto("texto-invalido", chave="chave-de-teste")


def test_criptografia_com_chave_do_ambiente():
    token = seguranca.criptografar_texto("valor")
    assert seguranca.descriptografar_texto(token) == "valor"


def test_mascarar_comparar():
    assert seguranca.mascarar_segredo("123456", manter=2) == "****56"
    assert seguranca.mascarar_segredo("ab", manter=5) == "**"
    assert seguranca.mascarar_segredo("") == ""
    assert seguranca.comparar_seguro("abc", "abc")
    assert not seguranca.comparar_seguro("abc", "abd")
