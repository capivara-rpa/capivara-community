"""Testes das utilidades de texto."""

import pytest

from core.rpa import texto
from core.tratador import ErroRPA


def test_limpar_texto_remove_controle_e_espacos():
    assert texto.limpar_texto("  Olá\x00   mundo \n") == "Olá mundo"


def test_remover_acentos_e_normalizar():
    assert texto.remover_acentos("Ação, coração e pão") == "Acao, coracao e pao"
    assert texto.normalizar_espacos("  a\t b\n c ") == "a b c"


def test_slug():
    assert texto.slug("Relatório de Clientes 2026") == "relatorio-de-clientes-2026"
    assert texto.slug("Já existe!", separador="_") == "ja_existe"


def test_capitalizar_nome_preserva_conectores():
    assert texto.capitalizar_nome("ana DE souza dos santos") == "Ana de Souza dos Santos"


def test_extracoes():
    bruto = "Fale com A@B.com ou c@d.com. Acesse https://x.com/a e 12 reais."
    assert texto.extrair_numeros(bruto) == ["12"]
    assert texto.extrair_emails(bruto) == ["A@B.com", "c@d.com"]
    assert texto.extrair_urls(bruto) == ["https://x.com/a"]


def test_mascarar_email():
    assert texto.mascarar_email("arthur@exemplo.com") == "a****r@exemplo.com"
    assert texto.mascarar_email("a@exemplo.com") == "*@exemplo.com"
    with pytest.raises(ErroRPA):
        texto.mascarar_email("sem-arroba")


def test_contar_palavras_e_similaridade():
    assert texto.contar_palavras("  uma  frase com quatro palavras ") == 5
    assert texto.similaridade("Capivara", "capivara") == 1.0
    assert texto.similaridade("abc", "xyz") < 0.5


def test_encontrar_e_substituir_padrao():
    assert texto.encontrar_padrao("a1 b2 c3", r"\d") == ["1", "2", "3"]
    assert texto.encontrar_padrao("a1 b2", r"([a-z])(\d)", grupo=1) == ["a", "b"]
    assert texto.substituir_padrao("a1 b2", r"\d", "#") == "a# b#"
    assert texto.substituir_padrao("a1 b2", r"\d", "#", contar=1) == "a# b2"
    with pytest.raises(ErroRPA):
        texto.encontrar_padrao("x", "(")
    with pytest.raises(ErroRPA):
        texto.substituir_padrao("x", "(", "y")


def test_truncar_texto():
    assert texto.truncar_texto("abcdef", limite=4) == "a..."
    assert texto.truncar_texto("abc", limite=10) == "abc"
    with pytest.raises(ErroRPA):
        texto.truncar_texto("abc", limite=0)
