"""Testes das validações/formatações brasileiras."""

from datetime import date

import pytest

from core.rpa import validacao
from core.tratador import ErroRPA


def test_cpf():
    assert validacao.validar_cpf("529.982.247-25")
    assert validacao.validar_cpf(11144477735)
    assert not validacao.validar_cpf("111.111.111-11")
    assert not validacao.validar_cpf("123")
    assert validacao.formatar_cpf("52998224725") == "529.982.247-25"
    assert validacao.validar_cpf(validacao.gerar_cpf(formatar=False))
    with pytest.raises(ErroRPA):
        validacao.formatar_cpf("123")


def test_cnpj():
    assert validacao.validar_cnpj("11.222.333/0001-81")
    assert not validacao.validar_cnpj("11.111.111/1111-11")
    assert not validacao.validar_cnpj("123")
    assert validacao.formatar_cnpj("11222333000181") == "11.222.333/0001-81"
    assert validacao.validar_cnpj(validacao.gerar_cnpj(formatar=False))
    with pytest.raises(ErroRPA):
        validacao.formatar_cnpj("123")


def test_documento_generico():
    assert validacao.validar_cpf_ou_cnpj("52998224725")
    assert validacao.validar_cpf_ou_cnpj("11222333000181")
    assert not validacao.validar_cpf_ou_cnpj("123")
    assert validacao.formatar_documento("52998224725") == "529.982.247-25"
    assert validacao.formatar_documento("11222333000181") == "11.222.333/0001-81"
    with pytest.raises(ErroRPA):
        validacao.formatar_documento("123")


def test_cep():
    assert validacao.validar_cep("01001-000")
    assert not validacao.validar_cep("00000000")
    assert not validacao.validar_cep("123")
    assert validacao.formatar_cep("01001000") == "01001-000"
    with pytest.raises(ErroRPA):
        validacao.formatar_cep("123")


def test_telefone():
    assert validacao.validar_telefone_br("(11) 98765-4321")
    assert validacao.validar_telefone_br("(11) 3456-7890")
    assert validacao.validar_telefone_br("+55 11 98765-4321")
    assert not validacao.validar_telefone_br("1198765432")
    assert not validacao.validar_telefone_br("(10) 98765-4321")
    assert validacao.formatar_telefone_br("11987654321") == "(11) 98765-4321"
    assert validacao.formatar_telefone_br("1134567890") == "(11) 3456-7890"
    with pytest.raises(ErroRPA):
        validacao.formatar_telefone_br("123")


def test_email():
    assert validacao.validar_email("eu@exemplo.com")
    assert not validacao.validar_email("eu@exemplo")
    assert not validacao.validar_email("sem arroba")


def test_datas():
    assert validacao.validar_data("31/12/2026")
    assert not validacao.validar_data("31/02/2026")
    assert validacao.converter_data("31/12/2026") == "2026-12-31"
    assert validacao.formatar_data_br("2026-12-31") == "31/12/2026"
    assert validacao.adicionar_dias_uteis("2026-01-02", 1) == date(2026, 1, 5)
    assert validacao.dias_uteis_entre("2026-01-02", "2026-01-06") == 2
    assert validacao.proximo_dia_util("2026-01-02") == date(2026, 1, 5)
    assert validacao.idade("2000-01-01", "2026-01-01") == 26
    with pytest.raises(ErroRPA):
        validacao.converter_data("31/02/2026")
    with pytest.raises(ErroRPA):
        validacao.idade("2030-01-01", "2026-01-01")


def test_moeda():
    assert validacao.formatar_moeda_br(1234.56) == "R$ 1.234,56"
    assert validacao.formatar_moeda_br(-10) == "-R$ 10,00"
    assert validacao.converter_moeda_br("R$ 1.234,56") == 1234.56
    assert validacao.converter_moeda_br("(R$ 10,00)") == -10.0
    assert validacao.converter_moeda_br(12.5) == 12.5
    with pytest.raises(ErroRPA):
        validacao.formatar_moeda_br("abc")
    with pytest.raises(ErroRPA):
        validacao.converter_moeda_br("")
