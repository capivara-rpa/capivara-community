"""Testes do módulo de banco (SQLite)."""

import pytest

from core.rpa import banco
from core.tratador import ErroRPA


@pytest.fixture()
def conexao():
    con = banco.conectar(":memory:")
    banco.criar_tabela(
        con,
        "clientes",
        {"id": "INTEGER", "nome": "TEXT", "uf": "TEXT"},
        chave_primaria="id",
    )
    yield con
    banco.fechar(con)


def test_criar_inserir_consultar_e_contar(conexao):
    primeiro = banco.inserir(conexao, "clientes", {"nome": "Ana", "uf": "SP"})
    segundo = banco.inserir(conexao, "clientes", {"nome": "Bia", "uf": "RJ"})
    assert primeiro == 1
    assert segundo == 2
    assert banco.contar_registros(conexao, "clientes") == 2
    assert banco.contar_registros(conexao, "clientes", "uf = ?", ("SP",)) == 1
    linhas = banco.consultar(conexao, "SELECT nome FROM clientes ORDER BY nome")
    assert linhas == [{"nome": "Ana"}, {"nome": "Bia"}]
    df = banco.consultar_dataframe(conexao, "SELECT * FROM clientes ORDER BY id")
    assert list(df["nome"]) == ["Ana", "Bia"]


def test_atualizar_e_apagar(conexao):
    banco.inserir(conexao, "clientes", {"nome": "Ana", "uf": "SP"})
    assert banco.atualizar(conexao, "clientes", {"uf": "MG"}, "nome = ?", ("Ana",)) == 1
    assert banco.consultar(conexao, "SELECT uf FROM clientes") == [{"uf": "MG"}]
    assert banco.apagar(conexao, "clientes", "nome = ?", ("Ana",)) == 1
    assert banco.contar_registros(conexao, "clientes") == 0


def test_metadados(conexao):
    assert banco.tabela_existe(conexao, "clientes")
    assert not banco.tabela_existe(conexao, "inexistente")
    assert banco.listar_tabelas(conexao) == ["clientes"]
    colunas = banco.descrever_tabela(conexao, "clientes")
    assert [coluna["name"] for coluna in colunas] == ["id", "nome", "uf"]
    assert colunas[0]["pk"] == 1


def test_executar_sql_livre(conexao):
    cursor = banco.executar(conexao, "INSERT INTO clientes (nome, uf) VALUES (?, ?)", ("Ana", "SP"))
    assert cursor.rowcount == 1
    assert banco.contar_registros(conexao, "clientes") == 1


def test_validacoes(conexao):
    with pytest.raises(ErroRPA):
        banco.criar_tabela(conexao, "x", {})
    with pytest.raises(ErroRPA):
        banco.criar_tabela(conexao, "x", {"id": "TEXTO_INVALIDO"})
    with pytest.raises(ErroRPA):
        banco.criar_tabela(conexao, "x", {"id": "INTEGER"}, chave_primaria="outra")
    with pytest.raises(ErroRPA):
        banco.inserir(conexao, "clientes", {})
    with pytest.raises(ErroRPA):
        banco.atualizar(conexao, "clientes", {}, "1=1")
    with pytest.raises(ErroRPA):
        banco.atualizar(conexao, "clientes", {"nome": "X"}, " ")
    with pytest.raises(ErroRPA):
        banco.apagar(conexao, "clientes", "")
    with pytest.raises(ErroRPA):
        banco.inserir(conexao, "tabela; DROP", {"nome": "X"})


def test_importar_e_exportar_csv(conexao, tmp_path):
    origem = tmp_path / "clientes.csv"
    origem.write_text("nome;uf\nAna;SP\nBia;RJ\n", encoding="utf-8")
    assert banco.importar_csv(conexao, "clientes", origem, separador=";") == 2
    assert banco.contar_registros(conexao, "clientes") == 2

    destino = tmp_path / "saida.csv"
    banco.exportar_csv(conexao, "clientes", destino)
    assert destino.is_file()
    assert "Ana" in destino.read_text(encoding="utf-8-sig")
