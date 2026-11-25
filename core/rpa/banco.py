"""Acesso a banco de dados SQLite com cara de low-code.

O foco é o SQLite (arquivo local, sem instalar servidor), mas o mesmo padrão
pode ser usado com qualquer driver DB-API. Tudo loga e devolve estruturas
simples (listas de dicionários / DataFrame)::

    from core.rpa import banco

    con = banco.conectar("data/input/clientes.db")
    banco.criar_tabela(con, "clientes", {"id": "INTEGER", "nome": "TEXT"})
    banco.inserir(con, "clientes", {"nome": "ACME"})
    banco.consultar(con, "SELECT * FROM clientes")
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from core.tratador import ErroRPA

_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TIPOS_SQL = {"TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC", "BOOLEAN", "DATE", "DATETIME"}


def _nome_seguro(nome: str) -> str:
    if not _IDENTIFICADOR.match(str(nome)):
        raise ErroRPA(f"Nome de tabela/coluna inválido: {nome!r}")
    return f'"{nome}"'


def conectar(caminho: str | Path = ":memory:") -> sqlite3.Connection:
    """Abre (ou cria) um banco SQLite e devolve a conexão."""
    destino = str(caminho)
    conexao = sqlite3.connect(destino)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    logger.success(f"Banco conectado: {destino}")
    return conexao


def executar(
    conexao: sqlite3.Connection,
    sql: str,
    parametros: tuple[Any, ...] | list[Any] = (),
) -> sqlite3.Cursor:
    """Executa um SQL livre e confirma a transação."""
    cursor = conexao.execute(sql, parametros)
    conexao.commit()
    logger.success(f"SQL executado ({cursor.rowcount} linha(s) afetada(s)).")
    return cursor


def consultar(
    conexao: sqlite3.Connection,
    sql: str,
    parametros: tuple[Any, ...] | list[Any] = (),
) -> list[dict[str, Any]]:
    """Executa um SELECT e devolve uma lista de dicionários."""
    linhas = conexao.execute(sql, parametros).fetchall()
    resultado = [dict(linha) for linha in linhas]
    logger.info(f"Consulta retornou {len(resultado)} linha(s).")
    return resultado


def consultar_dataframe(
    conexao: sqlite3.Connection,
    sql: str,
    parametros: tuple[Any, ...] | list[Any] = (),
) -> pd.DataFrame:
    """Executa um SELECT e devolve um DataFrame do pandas."""
    df = pd.read_sql_query(sql, conexao, params=parametros)
    logger.success(f"Consulta convertida em DataFrame ({len(df)} linha(s)).")
    return df


def inserir(
    conexao: sqlite3.Connection,
    tabela: str,
    dados: dict[str, Any],
) -> int:
    """Insere um registro e devolve o id gerado."""
    if not dados:
        raise ErroRPA("Informe ao menos uma coluna para inserir.")
    colunas = list(dados)
    sql = (
        f"INSERT INTO {_nome_seguro(tabela)} "
        f"({', '.join(_nome_seguro(c) for c in colunas)}) "
        f"VALUES ({', '.join('?' for _ in colunas)})"
    )
    cursor = conexao.execute(sql, tuple(dados.values()))
    conexao.commit()
    logger.success(f"Registro inserido em '{tabela}' (id {cursor.lastrowid}).")
    return int(cursor.lastrowid or 0)


def atualizar(
    conexao: sqlite3.Connection,
    tabela: str,
    dados: dict[str, Any],
    onde: str,
    parametros_onde: tuple[Any, ...] | list[Any] = (),
) -> int:
    """Atualiza registros que atendem à cláusula ``onde`` e devolve quantos mudaram."""
    if not dados:
        raise ErroRPA("Informe ao menos uma coluna para atualizar.")
    if not onde.strip():
        raise ErroRPA("Informe a cláusula 'onde' (use '1=1' para atualizar todos).")
    sets = ", ".join(f"{_nome_seguro(coluna)} = ?" for coluna in dados)
    sql = f"UPDATE {_nome_seguro(tabela)} SET {sets} WHERE {onde}"
    cursor = conexao.execute(sql, (*dados.values(), *parametros_onde))
    conexao.commit()
    logger.success(f"UPDATE em '{tabela}': {cursor.rowcount} linha(s) alterada(s).")
    return int(cursor.rowcount)


def apagar(
    conexao: sqlite3.Connection,
    tabela: str,
    onde: str,
    parametros: tuple[Any, ...] | list[Any] = (),
) -> int:
    """Apaga registros que atendem à cláusula ``onde``."""
    if not onde.strip():
        raise ErroRPA("Informe a cláusula 'onde' (use '1=1' para apagar todos).")
    cursor = conexao.execute(f"DELETE FROM {_nome_seguro(tabela)} WHERE {onde}", parametros)
    conexao.commit()
    logger.success(f"DELETE em '{tabela}': {cursor.rowcount} linha(s) apagada(s).")
    return int(cursor.rowcount)


def listar_tabelas(conexao: sqlite3.Connection) -> list[str]:
    """Lista as tabelas do banco."""
    linhas = conexao.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    tabelas = [linha["name"] for linha in linhas]
    logger.info(f"Tabelas ({len(tabelas)}): {tabelas}")
    return tabelas


def tabela_existe(conexao: sqlite3.Connection, tabela: str) -> bool:
    """Diz se uma tabela existe."""
    linha = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabela,)
    ).fetchone()
    return linha is not None


def descrever_tabela(conexao: sqlite3.Connection, tabela: str) -> list[dict[str, Any]]:
    """Descreve as colunas de uma tabela (nome, tipo, nulidade, chave)."""
    linhas = conexao.execute(f"PRAGMA table_info({_nome_seguro(tabela)})").fetchall()
    return [dict(linha) for linha in linhas]


def contar_registros(
    conexao: sqlite3.Connection,
    tabela: str,
    onde: str | None = None,
    parametros: tuple[Any, ...] | list[Any] = (),
) -> int:
    """Conta os registros de uma tabela (opcionalmente com filtro)."""
    sql = f"SELECT COUNT(*) AS total FROM {_nome_seguro(tabela)}"
    if onde:
        sql += f" WHERE {onde}"
    linha = conexao.execute(sql, parametros).fetchone()
    total = int(linha["total"]) if linha else 0
    logger.info(f"'{tabela}' tem {total} registro(s).")
    return total


def criar_tabela(
    conexao: sqlite3.Connection,
    tabela: str,
    colunas: dict[str, str],
    chave_primaria: str | None = None,
) -> None:
    """Cria uma tabela se ela ainda não existir.

    ``colunas`` é um dicionário ``{nome: tipo}`` (ex.: ``{"id": "INTEGER"}``).
    """
    if not colunas:
        raise ErroRPA("Informe ao menos uma coluna para criar a tabela.")
    definicoes: list[str] = []
    for nome, tipo in colunas.items():
        tipo_normalizado = str(tipo).upper().split("(")[0].strip()
        if tipo_normalizado not in _TIPOS_SQL:
            raise ErroRPA(f"Tipo SQL não suportado para '{nome}': {tipo!r}")
        definicoes.append(f"{_nome_seguro(nome)} {tipo}")
    if chave_primaria:
        if chave_primaria not in colunas:
            raise ErroRPA(
                f"A chave primária '{chave_primaria}' precisa estar entre as colunas."
            )
        definicoes.append(f"PRIMARY KEY ({_nome_seguro(chave_primaria)})")
    sql = f"CREATE TABLE IF NOT EXISTS {_nome_seguro(tabela)} ({', '.join(definicoes)})"
    conexao.execute(sql)
    conexao.commit()
    logger.success(f"Tabela garantida: {tabela}")


def importar_csv(
    conexao: sqlite3.Connection,
    tabela: str,
    caminho: str | Path,
    separador: str = ",",
    codificacao: str = "utf-8",
    **kwargs: Any,
) -> int:
    """Importa um CSV para uma tabela (cria a tabela se não existir)."""
    _nome_seguro(tabela)
    df = pd.read_csv(caminho, sep=separador, encoding=codificacao, **kwargs)
    df.to_sql(tabela, conexao, if_exists="append", index=False)
    conexao.commit()
    logger.success(f"CSV importado para '{tabela}': {len(df)} linha(s).")
    return len(df)


def exportar_csv(
    conexao: sqlite3.Connection,
    tabela: str,
    caminho: str | Path,
    separador: str = ";",
    codificacao: str = "utf-8-sig",
) -> Path:
    """Exporta uma tabela para CSV (separador ``;`` por padrão, Excel BR)."""
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_sql_query(f"SELECT * FROM {_nome_seguro(tabela)}", conexao)
    df.to_csv(destino, sep=separador, encoding=codificacao, index=False)
    logger.success(f"Tabela '{tabela}' exportada: {destino} ({len(df)} linha(s)).")
    return destino


def fechar(conexao: sqlite3.Connection) -> None:
    """Fecha a conexão com o banco."""
    conexao.close()
    logger.info("Conexão com o banco fechada.")


__all__ = [
    "conectar",
    "executar",
    "consultar",
    "consultar_dataframe",
    "inserir",
    "atualizar",
    "apagar",
    "listar_tabelas",
    "tabela_existe",
    "descrever_tabela",
    "contar_registros",
    "criar_tabela",
    "importar_csv",
    "exportar_csv",
    "fechar",
]
