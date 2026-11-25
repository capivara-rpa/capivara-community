"""Banco de dados do monitor (SQLite).

Toda a persistência do painel fica aqui: as **execuções** dos robôs e os
**passos** (trace) de cada uma. O modelo é enxuto de propósito, para a
comunidade entender e estender com facilidade.

- ``execucoes``: uma linha por rodada de um robô (status atual, início, fim...).
- ``passos``: uma linha por ação registrada dentro de uma execução.

Os status seguem os pedidos do projeto: ``iniciado``, ``processando``,
``erro_sistemico``, ``erro_negocio``, ``erro_critico``, ``finalizado`` e
``falha``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from loguru import logger

from settings.parametros import BANCO_MONITOR

# ----------------------------------------------------------------------
# Status possíveis
# ----------------------------------------------------------------------
STATUS_INICIADO = "iniciado"
STATUS_PROCESSANDO = "processando"
STATUS_ERRO_SISTEMICO = "erro_sistemico"
STATUS_ERRO_NEGOCIO = "erro_negocio"
STATUS_ERRO_CRITICO = "erro_critico"
STATUS_FINALIZADO = "finalizado"
STATUS_FALHA = "falha"

STATUS_VALIDOS: tuple[str, ...] = (
    STATUS_INICIADO,
    STATUS_PROCESSANDO,
    STATUS_ERRO_SISTEMICO,
    STATUS_ERRO_NEGOCIO,
    STATUS_ERRO_CRITICO,
    STATUS_FINALIZADO,
    STATUS_FALHA,
)

# Status que indicam que a execução terminou (usado para preencher o "fim")
STATUS_ENCERRADO: frozenset[str] = frozenset(
    {STATUS_FINALIZADO, STATUS_FALHA, STATUS_ERRO_CRITICO, STATUS_ERRO_SISTEMICO, STATUS_ERRO_NEGOCIO}
)

# Rótulo bonito (com acentos) para exibir no painel
STATUS_ROTULO: dict[str, str] = {
    STATUS_INICIADO: "Iniciado",
    STATUS_PROCESSANDO: "Processando",
    STATUS_ERRO_SISTEMICO: "Erro sistêmico",
    STATUS_ERRO_NEGOCIO: "Erro de negócio",
    STATUS_ERRO_CRITICO: "Erro crítico",
    STATUS_FINALIZADO: "Finalizado",
    STATUS_FALHA: "Falha",
}

# Cor (hex) de cada status — usada no painel para badges e gráficos
STATUS_COR: dict[str, str] = {
    STATUS_INICIADO: "#8A8378",
    STATUS_PROCESSANDO: "#1F5FD1",
    STATUS_ERRO_SISTEMICO: "#E0A400",
    STATUS_ERRO_NEGOCIO: "#9B6B43",
    STATUS_ERRO_CRITICO: "#A93226",
    STATUS_FINALIZADO: "#1FA463",
    STATUS_FALHA: "#C0392B",
}

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS execucoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    robo          TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'iniciado',
    mensagem      TEXT,
    inicio        TEXT    NOT NULL,
    fim           TEXT,
    atualizado_em TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS passos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    execucao_id INTEGER NOT NULL,
    ordem       INTEGER NOT NULL,
    nivel       TEXT    NOT NULL DEFAULT 'INFO',
    status      TEXT    NOT NULL DEFAULT 'processando',
    descricao   TEXT    NOT NULL,
    detalhe     TEXT,
    criado_em   TEXT    NOT NULL,
    FOREIGN KEY (execucao_id) REFERENCES execucoes (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_passos_execucao ON passos (execucao_id, ordem);
CREATE INDEX IF NOT EXISTS idx_execucoes_robo ON execucoes (robo);
CREATE INDEX IF NOT EXISTS idx_execucoes_inicio ON execucoes (inicio);
"""


# ----------------------------------------------------------------------
# Helpers internos
# ----------------------------------------------------------------------
def agora_iso() -> str:
    """Retorna o instante atual como texto ISO com milissegundos."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


@contextmanager
def conectar() -> Iterator[sqlite3.Connection]:
    """Abre conexão com o banco do monitor e sempre fecha ao sair do ``with``.

    O context manager nativo do ``sqlite3.Connection`` só faz commit/rollback;
    não fecha a conexão. Sem o ``close()`` explícito, cada passo do trace vaza
    um file descriptor.
    """
    BANCO_MONITOR.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(BANCO_MONITOR, timeout=10)
    try:
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        yield conexao
        conexao.commit()
    except BaseException:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def iniciar_banco() -> None:
    """Garante que o banco e as tabelas existam."""
    with conectar() as conexao:
        conexao.executescript(_ESQUEMA)


def _linhas(conexao: sqlite3.Connection, sql: str, parametros: tuple = ()) -> list[dict[str, Any]]:
    return [dict(linha) for linha in conexao.execute(sql, parametros).fetchall()]


# ----------------------------------------------------------------------
# Execuções
# ----------------------------------------------------------------------
def iniciar_execucao(robo: str, mensagem: str | None = None, quando: str | None = None) -> int:
    """Cria uma nova execução para o robô e devolve o ``id`` gerado."""
    momento = quando or agora_iso()
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO execucoes (robo, status, mensagem, inicio, atualizado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (robo, STATUS_INICIADO, mensagem, momento, momento),
        )
        execucao_id = int(cursor.lastrowid or 0)
    logger.debug(f"[monitor] execução #{execucao_id} do robô '{robo}' criada")
    return execucao_id


def atualizar_status(
    execucao_id: int,
    status: str,
    mensagem: str | None = None,
    quando: str | None = None,
) -> None:
    """Atualiza o status atual de uma execução (e finaliza se for o caso)."""
    if status not in STATUS_VALIDOS:
        raise ValueError(f"Status inválido: {status!r}. Use um de {STATUS_VALIDOS}.")

    momento = quando or agora_iso()
    finaliza = status in STATUS_ENCERRADO

    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE execucoes
               SET status = ?,
                   mensagem = COALESCE(?, mensagem),
                   fim = CASE WHEN ? THEN ? ELSE fim END,
                   atualizado_em = ?
             WHERE id = ?
            """,
            (status, mensagem, finaliza, momento, momento, execucao_id),
        )
    logger.debug(f"[monitor] execução #{execucao_id} → {status}")


def registrar_passo(
    execucao_id: int,
    descricao: str,
    nivel: str = "INFO",
    status: str = STATUS_PROCESSANDO,
    detalhe: str | None = None,
    quando: str | None = None,
) -> int:
    """Grava um passo do robô (linha do trace) e devolve o ``id``."""
    momento = quando or agora_iso()
    with conectar() as conexao:
        proxima = conexao.execute(
            "SELECT COALESCE(MAX(ordem), 0) + 1 FROM passos WHERE execucao_id = ?",
            (execucao_id,),
        ).fetchone()[0]
        cursor = conexao.execute(
            """
            INSERT INTO passos (execucao_id, ordem, nivel, status, descricao, detalhe, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (execucao_id, proxima, nivel.upper(), status, descricao, detalhe, momento),
        )
        conexao.execute(
            "UPDATE execucoes SET status = ?, atualizado_em = ? WHERE id = ?",
            (status, momento, execucao_id),
        )
        passo_id = int(cursor.lastrowid or 0)
    return passo_id


def listar_execucoes(limite: int = 50) -> list[dict[str, Any]]:
    """Lista as execuções mais recentes (com contagem e último passo)."""
    with conectar() as conexao:
        return _linhas(
            conexao,
            """
            SELECT e.*,
                   (SELECT COUNT(*) FROM passos p WHERE p.execucao_id = e.id) AS total_passos,
                   (SELECT p.descricao FROM passos p
                     WHERE p.execucao_id = e.id
                     ORDER BY p.ordem DESC LIMIT 1) AS ultimo_passo
              FROM execucoes e
             ORDER BY e.inicio DESC, e.id DESC
             LIMIT ?
            """,
            (limite,),
        )


def obter_execucao(execucao_id: int) -> dict[str, Any] | None:
    """Busca uma execução pelo id."""
    with conectar() as conexao:
        linhas = _linhas(conexao, "SELECT * FROM execucoes WHERE id = ?", (execucao_id,))
    return linhas[0] if linhas else None


def listar_passos(execucao_id: int) -> list[dict[str, Any]]:
    """Lista o trace (passo a passo) de uma execução, em ordem."""
    with conectar() as conexao:
        return _linhas(
            conexao,
            "SELECT * FROM passos WHERE execucao_id = ? ORDER BY ordem",
            (execucao_id,),
        )


def ultimos_passos(limite: int = 20) -> list[dict[str, Any]]:
    """Lista os passos mais recentes de todos os robôs (feed ao vivo)."""
    with conectar() as conexao:
        return _linhas(
            conexao,
            """
            SELECT p.*, e.robo
              FROM passos p
              JOIN execucoes e ON e.id = p.execucao_id
             ORDER BY p.criado_em DESC, p.id DESC
             LIMIT ?
            """,
            (limite,),
        )


def resumo_status() -> dict[str, int]:
    """Conta quantas execuções existem em cada status."""
    contagem = {status: 0 for status in STATUS_VALIDOS}
    with conectar() as conexao:
        for linha in conexao.execute(
            "SELECT status, COUNT(*) AS total FROM execucoes GROUP BY status"
        ).fetchall():
            if linha["status"] in contagem:
                contagem[linha["status"]] = linha["total"]
    return contagem


def apagar_tudo() -> None:
    """Remove todas as execuções e passos (usado para recarregar exemplos)."""
    with conectar() as conexao:
        conexao.execute("DELETE FROM passos")
        conexao.execute("DELETE FROM execucoes")
    logger.debug("[monitor] banco esvaziado")


def revisao() -> str:
    """Assinatura barata do estado do monitor (para push em tempo real).

    Muda sempre que uma execução ou passo é criado/atualizado. O painel usa
    isso via SSE para saber a hora de recarregar.
    """
    with conectar() as conexao:
        linha = conexao.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM execucoes) AS ne,
              (SELECT COALESCE(MAX(atualizado_em), '') FROM execucoes) AS ue,
              (SELECT COUNT(*) FROM passos) AS np,
              (SELECT COALESCE(MAX(id), 0) FROM passos) AS ip
            """
        ).fetchone()
    return f"{linha['ne']}:{linha['ue']}:{linha['np']}:{linha['ip']}"
