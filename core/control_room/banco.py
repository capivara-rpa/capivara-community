"""Persistência da Lagoa (SQLite).

Três tabelas:

- ``maquinas``: cada máquina/agente que se registra na Lagoa.
- ``processos``: catálogo de robôs executáveis (aponta para um fluxo Python).
- ``jobs``: cada disparo de um processo numa máquina, com o seu ciclo de vida.

O banco é separado do trace (``core/monitor``), mas o campo ``jobs.execucao_id``
aponta para a execução correspondente no monitor, permitindo abrir o passo a
passo de cada job.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from core.monitor.banco import agora_iso
from settings.parametros import BANCO_ORQUESTRADOR

# ----------------------------------------------------------------------
# Estados das máquinas
# ----------------------------------------------------------------------
MAQUINA_ONLINE = "online"
MAQUINA_OCUPADA = "ocupada"
MAQUINA_OFFLINE = "offline"

MAQUINA_ROTULO: dict[str, str] = {
    MAQUINA_ONLINE: "Online",
    MAQUINA_OCUPADA: "Ocupada",
    MAQUINA_OFFLINE: "Offline",
}
MAQUINA_COR: dict[str, str] = {
    MAQUINA_ONLINE: "#1FA463",
    MAQUINA_OCUPADA: "#1F5FD1",
    MAQUINA_OFFLINE: "#8A8378",
}

# ----------------------------------------------------------------------
# Estados dos jobs
# ----------------------------------------------------------------------
JOB_PENDENTE = "pendente"
JOB_EM_EXECUCAO = "em_execucao"
JOB_CONCLUIDO = "concluido"
JOB_FALHOU = "falhou"
JOB_CANCELADO = "cancelado"

JOB_VALIDOS: tuple[str, ...] = (
    JOB_PENDENTE,
    JOB_EM_EXECUCAO,
    JOB_CONCLUIDO,
    JOB_FALHOU,
    JOB_CANCELADO,
)

JOB_ROTULO: dict[str, str] = {
    JOB_PENDENTE: "Pendente",
    JOB_EM_EXECUCAO: "Em execução",
    JOB_CONCLUIDO: "Concluído",
    JOB_FALHOU: "Falhou",
    JOB_CANCELADO: "Cancelado",
}
JOB_COR: dict[str, str] = {
    JOB_PENDENTE: "#E0A400",
    JOB_EM_EXECUCAO: "#1F5FD1",
    JOB_CONCLUIDO: "#1FA463",
    JOB_FALHOU: "#C0392B",
    JOB_CANCELADO: "#8A8378",
}
JOB_ENCERRADO: frozenset[str] = frozenset({JOB_CONCLUIDO, JOB_FALHOU, JOB_CANCELADO})

# ----------------------------------------------------------------------
# Estados dos itens de fila (datapool, estilo filas de trabalho)
# ----------------------------------------------------------------------
ITEM_NOVO = "novo"
ITEM_EM_PROCESSAMENTO = "em_processamento"
ITEM_CONCLUIDO = "concluido"
ITEM_FALHOU = "falhou"
ITEM_ABANDONADO = "abandonado"

ITEM_VALIDOS: tuple[str, ...] = (
    ITEM_NOVO,
    ITEM_EM_PROCESSAMENTO,
    ITEM_CONCLUIDO,
    ITEM_FALHOU,
    ITEM_ABANDONADO,
)

ITEM_ROTULO: dict[str, str] = {
    ITEM_NOVO: "Novo",
    ITEM_EM_PROCESSAMENTO: "Em processamento",
    ITEM_CONCLUIDO: "Concluído",
    ITEM_FALHOU: "Falhou",
    ITEM_ABANDONADO: "Abandonado",
}
ITEM_COR: dict[str, str] = {
    ITEM_NOVO: "#9B6B43",
    ITEM_EM_PROCESSAMENTO: "#1F5FD1",
    ITEM_CONCLUIDO: "#1FA463",
    ITEM_FALHOU: "#C0392B",
    ITEM_ABANDONADO: "#8A8378",
}
ITEM_ENCERRADO: frozenset[str] = frozenset({ITEM_CONCLUIDO, ITEM_FALHOU, ITEM_ABANDONADO})

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS maquinas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL UNIQUE,
    status          TEXT    NOT NULL DEFAULT 'online',
    tags            TEXT,
    ip              TEXT,
    info            TEXT,
    ultima_atividade TEXT   NOT NULL,
    criado_em       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS processos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL UNIQUE,
    descricao TEXT,
    fluxo     TEXT    NOT NULL,
    usa_navegador INTEGER NOT NULL DEFAULT 0,
    ativo     INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    processo_id  INTEGER NOT NULL,
    maquina_id   INTEGER,
    requisito_tag TEXT,
    item_id      INTEGER,
    status       TEXT    NOT NULL DEFAULT 'pendente',
    execucao_id  INTEGER,
    mensagem     TEXT,
    criado_em    TEXT    NOT NULL,
    iniciado_em  TEXT,
    finalizado_em TEXT,
    FOREIGN KEY (processo_id) REFERENCES processos (id),
    FOREIGN KEY (maquina_id)  REFERENCES maquinas (id)
);

CREATE TABLE IF NOT EXISTS triggers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    processo_id    INTEGER NOT NULL,
    maquina_id     INTEGER,
    requisito_tag  TEXT,
    tipo           TEXT    NOT NULL DEFAULT 'intervalo',
    intervalo_min  INTEGER,
    hora           TEXT,
    dias_semana    TEXT,
    incluir_fins   INTEGER NOT NULL DEFAULT 1,
    incluir_feriados INTEGER NOT NULL DEFAULT 1,
    ativo          INTEGER NOT NULL DEFAULT 1,
    ultima_execucao TEXT,
    proxima_execucao TEXT,
    criado_em      TEXT    NOT NULL,
    FOREIGN KEY (processo_id) REFERENCES processos (id),
    FOREIGN KEY (maquina_id)  REFERENCES maquinas (id)
);

CREATE TABLE IF NOT EXISTS assets (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL UNIQUE,
    valor     TEXT,
    secreto   INTEGER NOT NULL DEFAULT 1,
    tipo      TEXT    NOT NULL DEFAULT 'segredo',
    usuario   TEXT,
    pasta     TEXT,
    versao    INTEGER NOT NULL DEFAULT 1,
    descricao TEXT,
    criado_em TEXT    NOT NULL,
    atualizado_em TEXT,
    atualizado_por TEXT
);

CREATE TABLE IF NOT EXISTS asset_versoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_nome TEXT    NOT NULL,
    versao     INTEGER NOT NULL,
    valor      TEXT,
    criado_em  TEXT    NOT NULL,
    criado_por TEXT
);

CREATE TABLE IF NOT EXISTS asset_permissoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_nome  TEXT    NOT NULL,
    processo_id INTEGER,
    pasta       TEXT,
    criado_em   TEXT    NOT NULL,
    FOREIGN KEY (processo_id) REFERENCES processos (id)
);

CREATE TABLE IF NOT EXISTS auditoria (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    quando     TEXT    NOT NULL,
    ator       TEXT,
    acao       TEXT    NOT NULL,
    recurso    TEXT,
    resultado  TEXT,
    detalhe    TEXT,
    ip         TEXT,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS filas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT    NOT NULL UNIQUE,
    descricao  TEXT,
    processo_id INTEGER,
    ativo      INTEGER NOT NULL DEFAULT 1,
    rr         INTEGER NOT NULL DEFAULT 0,
    criado_em  TEXT    NOT NULL,
    FOREIGN KEY (processo_id) REFERENCES processos (id)
);

CREATE TABLE IF NOT EXISTS fila_processos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fila_id     INTEGER NOT NULL,
    processo_id INTEGER NOT NULL,
    FOREIGN KEY (fila_id)     REFERENCES filas (id),
    FOREIGN KEY (processo_id) REFERENCES processos (id),
    UNIQUE (fila_id, processo_id)
);

CREATE TABLE IF NOT EXISTS itens_fila (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fila_id      INTEGER NOT NULL,
    dados        TEXT    NOT NULL DEFAULT '{}',
    referencia   TEXT,
    status       TEXT    NOT NULL DEFAULT 'novo',
    tentativas   INTEGER NOT NULL DEFAULT 0,
    prioridade   INTEGER NOT NULL DEFAULT 0,
    maquina_id   INTEGER,
    job_id       INTEGER,
    mensagem     TEXT,
    criado_em    TEXT    NOT NULL,
    atualizado_em TEXT   NOT NULL,
    finalizado_em TEXT,
    FOREIGN KEY (fila_id)    REFERENCES filas (id),
    FOREIGN KEY (maquina_id) REFERENCES maquinas (id)
);

CREATE TABLE IF NOT EXISTS empresas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL UNIQUE,
    ativa     INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id  INTEGER,
    nome        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL,
    ativo       INTEGER NOT NULL DEFAULT 1,
    admin       INTEGER NOT NULL DEFAULT 0,
    criado_em   TEXT    NOT NULL,
    FOREIGN KEY (empresa_id) REFERENCES empresas (id)
);

CREATE TABLE IF NOT EXISTS papeis (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL UNIQUE,
    descricao TEXT,
    criado_em TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS permissoes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL UNIQUE,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS papel_permissoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    papel_id     INTEGER NOT NULL,
    permissao_id INTEGER NOT NULL,
    FOREIGN KEY (papel_id)     REFERENCES papeis (id),
    FOREIGN KEY (permissao_id) REFERENCES permissoes (id),
    UNIQUE (papel_id, permissao_id)
);

CREATE TABLE IF NOT EXISTS usuario_papeis (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    papel_id   INTEGER NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    FOREIGN KEY (papel_id)   REFERENCES papeis (id),
    UNIQUE (usuario_id, papel_id)
);

CREATE TABLE IF NOT EXISTS sessoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL,
    token_hash   TEXT    NOT NULL UNIQUE,
    criado_em    TEXT    NOT NULL,
    expira_em    TEXT    NOT NULL,
    ip           TEXT,
    user_agent   TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_maquina ON jobs (maquina_id);
CREATE INDEX IF NOT EXISTS idx_maquinas_nome ON maquinas (nome);
CREATE INDEX IF NOT EXISTS idx_itens_fila_status ON itens_fila (fila_id, status);
CREATE INDEX IF NOT EXISTS idx_asset_versoes ON asset_versoes (asset_nome, versao);
CREATE INDEX IF NOT EXISTS idx_asset_permissoes ON asset_permissoes (asset_nome);
CREATE INDEX IF NOT EXISTS idx_auditoria_quando ON auditoria (quando);
CREATE INDEX IF NOT EXISTS idx_auditoria_recurso ON auditoria (recurso);
"""

# Colunas adicionadas depois (migração simples para bancos já existentes)
_COLUNAS_EXTRA = {
    "jobs": [("requisito_tag", "TEXT"), ("item_id", "INTEGER")],
    "itens_fila": [("prioridade", "INTEGER")],
    "maquinas": [("token_hash", "TEXT")],
    "filas": [("ativo", "INTEGER NOT NULL DEFAULT 1"), ("rr", "INTEGER NOT NULL DEFAULT 0")],
    "triggers": [
        ("expressao", "TEXT"),
        ("dias_semana", "TEXT"),
        ("incluir_fins", "INTEGER NOT NULL DEFAULT 1"),
        ("incluir_feriados", "INTEGER NOT NULL DEFAULT 1"),
    ],
    "assets": [
        ("tipo", "TEXT NOT NULL DEFAULT 'segredo'"),
        ("usuario", "TEXT"),
        ("pasta", "TEXT"),
        ("versao", "INTEGER NOT NULL DEFAULT 1"),
        ("atualizado_em", "TEXT"),
        ("atualizado_por", "TEXT"),
    ],
    "processos": [
        ("origem", "TEXT"),
        ("origem_ref", "TEXT"),
        ("variaveis", "TEXT"),
        ("commit_sha", "TEXT"),
        ("auto_atualizar", "INTEGER NOT NULL DEFAULT 0"),
        ("ultima_atualizacao", "TEXT"),
        ("ultimo_erro", "TEXT"),
    ],
}


@contextmanager
def conectar() -> Iterator[sqlite3.Connection]:
    """Abre conexão com o banco da Lagoa e sempre fecha ao sair do ``with``.

    O context manager nativo do ``sqlite3.Connection`` só faz commit/rollback;
    não fecha a conexão. Sem o ``close()`` explícito, cada heartbeat da Lagoa
    vaza um file descriptor até estourar o limite do launchd.
    """
    BANCO_ORQUESTRADOR.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(BANCO_ORQUESTRADOR, timeout=10)
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
    """Garante que o banco e as tabelas existam (com migrações leves)."""
    with conectar() as conexao:
        conexao.executescript(_ESQUEMA)
        for tabela, colunas in _COLUNAS_EXTRA.items():
            existentes = {
                linha["name"] for linha in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
            }
            for nome, tipo in colunas:
                if nome not in existentes:
                    conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")


def _linhas(conexao: sqlite3.Connection, sql: str, parametros: tuple = ()) -> list[dict[str, Any]]:
    return [dict(linha) for linha in conexao.execute(sql, parametros).fetchall()]


def _linha(conexao: sqlite3.Connection, sql: str, parametros: tuple = ()) -> dict[str, Any] | None:
    resultado = _linhas(conexao, sql, parametros)
    return resultado[0] if resultado else None


# ----------------------------------------------------------------------
# Máquinas
# ----------------------------------------------------------------------
def obter_maquina_por_nome(nome: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM maquinas WHERE nome = ?", (nome,))


def listar_maquinas() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM maquinas ORDER BY nome")


# ----------------------------------------------------------------------
# Processos
# ----------------------------------------------------------------------
def listar_processos() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM processos ORDER BY nome")


def listar_processos_auto_atualizar() -> list[dict[str, Any]]:
    """Processos de repositório Git marcados para atualização automática."""
    with conectar() as conexao:
        return _linhas(
            conexao,
            "SELECT * FROM processos WHERE auto_atualizar = 1 AND origem IS NOT NULL AND origem != '' ORDER BY nome",
        )


def definir_auto_atualizar(processo_id: int, ativo: bool) -> bool:
    with conectar() as conexao:
        cursor = conexao.execute(
            "UPDATE processos SET auto_atualizar = ? WHERE id = ?",
            (int(bool(ativo)), processo_id),
        )
        return cursor.rowcount > 0


def registrar_resultado_atualizacao(
    processo_id: int,
    sha: str | None = None,
    erro: str | None = None,
) -> bool:
    """Registra o SHA visto na última verificação (ou o erro, se falhou)."""
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE processos
               SET commit_sha = COALESCE(?, commit_sha),
                   ultima_atualizacao = ?,
                   ultimo_erro = ?
             WHERE id = ?
            """,
            (sha, agora_iso(), (erro or "")[:500] or None, processo_id),
        )
        return cursor.rowcount > 0


def obter_processo(processo_id: int) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM processos WHERE id = ?", (processo_id,))


def obter_processo_por_nome(nome: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM processos WHERE nome = ?", (nome,))


# ----------------------------------------------------------------------
# Jobs
# ----------------------------------------------------------------------
def obter_job(job_id: int) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, _SQL_JOB_DETALHE + " WHERE j.id = ?", (job_id,))


def listar_jobs(limite: int = 50) -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(
            conexao,
            _SQL_JOB_DETALHE + " ORDER BY j.id DESC LIMIT ?",
            (limite,),
        )


_SQL_JOB_DETALHE = """
SELECT j.*,
       p.nome  AS processo_nome,
       p.fluxo AS fluxo,
       p.usa_navegador AS usa_navegador,
       p.variaveis AS processo_variaveis,
       m.nome  AS maquina_nome
  FROM jobs j
  LEFT JOIN processos p ON p.id = j.processo_id
  LEFT JOIN maquinas  m ON m.id = j.maquina_id
"""


def apagar_tudo() -> None:
    """Remove máquinas, processos, jobs, triggers, assets, filas e identidade."""
    with conectar() as conexao:
        conexao.execute("DELETE FROM itens_fila")
        conexao.execute("DELETE FROM fila_processos")
        conexao.execute("DELETE FROM filas")
        conexao.execute("DELETE FROM triggers")
        conexao.execute("DELETE FROM jobs")
        conexao.execute("DELETE FROM asset_versoes")
        conexao.execute("DELETE FROM asset_permissoes")
        conexao.execute("DELETE FROM auditoria")
        conexao.execute("DELETE FROM assets")
        conexao.execute("DELETE FROM sessoes")
        conexao.execute("DELETE FROM usuario_papeis")
        conexao.execute("DELETE FROM papel_permissoes")
        conexao.execute("DELETE FROM papeis")
        conexao.execute("DELETE FROM permissoes")
        conexao.execute("DELETE FROM usuarios")
        conexao.execute("DELETE FROM empresas")
        conexao.execute("DELETE FROM processos")
        conexao.execute("DELETE FROM maquinas")


# ----------------------------------------------------------------------
# Triggers (agendamentos)
# ----------------------------------------------------------------------
def listar_triggers() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(
            conexao,
            _SQL_TRIGGER_DETALHE + " ORDER BY t.id",
        )


def obter_trigger(trigger_id: int) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, _SQL_TRIGGER_DETALHE + " WHERE t.id = ?", (trigger_id,))


_SQL_TRIGGER_DETALHE = """
SELECT t.*,
       p.nome AS processo_nome,
       m.nome AS maquina_nome
  FROM triggers t
  LEFT JOIN processos p ON p.id = t.processo_id
  LEFT JOIN maquinas  m ON m.id = t.maquina_id
"""


# ----------------------------------------------------------------------
# Assets (credenciais / variáveis centralizadas)
# ----------------------------------------------------------------------
def listar_assets() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM assets ORDER BY nome")


def obter_asset_por_nome(nome: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM assets WHERE nome = ?", (nome,))


def listar_versoes_asset(asset_nome: str) -> list[dict[str, Any]]:
    """Histórico de versões de um asset (mais recente primeiro)."""
    with conectar() as conexao:
        return _linhas(
            conexao,
            "SELECT * FROM asset_versoes WHERE asset_nome = ? ORDER BY versao DESC",
            (asset_nome,),
        )


def listar_permissoes_asset(asset_nome: str) -> list[dict[str, Any]]:
    """Permissões (por processo) concedidas para um asset."""
    with conectar() as conexao:
        return _linhas(
            conexao,
            _SQL_PERMISSAO_DETALHE + " WHERE a.asset_nome = ? ORDER BY a.id",
            (asset_nome,),
        )


_SQL_PERMISSAO_DETALHE = """
SELECT a.*,
       p.nome AS processo_nome
  FROM asset_permissoes a
  LEFT JOIN processos p ON p.id = a.processo_id
"""


def listar_auditoria(
    limite: int = 200,
    recurso: str | None = None,
    ator: str | None = None,
) -> list[dict[str, Any]]:
    """Trilha de auditoria (mais recente primeiro), com filtros opcionais."""
    sql = "SELECT * FROM auditoria"
    condicoes: list[str] = []
    parametros: list = []
    if recurso:
        condicoes.append("recurso LIKE ?")
        parametros.append(f"%{recurso}%")
    if ator:
        condicoes.append("ator = ?")
        parametros.append(ator)
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY id DESC LIMIT ?"
    parametros.append(limite)
    with conectar() as conexao:
        return _linhas(conexao, sql, tuple(parametros))


# ----------------------------------------------------------------------
# Filas (datapool)
# ----------------------------------------------------------------------
_SQL_FILA_DETALHE = """
SELECT f.*,
       p.nome AS processo_nome,
       p.fluxo AS fluxo,
       p.usa_navegador AS usa_navegador,
       (SELECT COUNT(*) FROM itens_fila i WHERE i.fila_id = f.id) AS total_itens
  FROM filas f
  LEFT JOIN processos p ON p.id = f.processo_id
"""


def listar_filas() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, _SQL_FILA_DETALHE + " ORDER BY f.nome")


def obter_fila(fila_id: int) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, _SQL_FILA_DETALHE + " WHERE f.id = ?", (fila_id,))


def listar_processos_fila(fila_id: int) -> list[dict[str, Any]]:
    """Processos executores de uma fila (para distribuição round-robin)."""
    with conectar() as conexao:
        return _linhas(
            conexao,
            """
            SELECT fp.processo_id,
                   p.id   AS id,
                   p.nome AS nome,
                   p.nome AS processo_nome,
                   p.fluxo AS fluxo,
                   p.usa_navegador AS usa_navegador
              FROM fila_processos fp
              LEFT JOIN processos p ON p.id = fp.processo_id
             WHERE fp.fila_id = ?
             ORDER BY fp.id
            """,
            (fila_id,),
        )


def obter_fila_por_nome(nome: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, _SQL_FILA_DETALHE + " WHERE f.nome = ?", (nome,))


_SQL_ITEM_DETALHE = """
SELECT i.*,
       f.nome  AS fila_nome,
       m.nome  AS maquina_nome
  FROM itens_fila i
  LEFT JOIN filas     f ON f.id = i.fila_id
  LEFT JOIN maquinas  m ON m.id = i.maquina_id
"""


def listar_itens(fila_id: int, status: str | None = None, limite: int = 200) -> list[dict[str, Any]]:
    """Lista os itens de uma fila (opcionalmente filtrados por status)."""
    sql = _SQL_ITEM_DETALHE + " WHERE i.fila_id = ?"
    parametros: tuple = (fila_id,)
    if status:
        sql += " AND i.status = ?"
        parametros = (fila_id, status)
    sql += " ORDER BY i.prioridade DESC, i.id LIMIT ?"
    parametros = parametros + (limite,)
    with conectar() as conexao:
        return _linhas(conexao, sql, parametros)


def obter_item(item_id: int) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, _SQL_ITEM_DETALHE + " WHERE i.id = ?", (item_id,))


def contagem_itens(fila_id: int) -> dict[str, int]:
    """Contagem de itens por status para uma fila."""
    with conectar() as conexao:
        linhas = conexao.execute(
            "SELECT status, COUNT(*) AS total FROM itens_fila WHERE fila_id = ? GROUP BY status",
            (fila_id,),
        ).fetchall()
    contagem = {status: 0 for status in ITEM_VALIDOS}
    for linha in linhas:
        if linha["status"] in contagem:
            contagem[linha["status"]] = linha["total"]
    return contagem


# ----------------------------------------------------------------------
# Empresas / usuários / papéis / permissões / sessões (identidade)
# ----------------------------------------------------------------------
def listar_empresas() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM empresas ORDER BY nome")


def obter_empresa_por_nome(nome: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM empresas WHERE nome = ?", (nome,))


def listar_usuarios() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM usuarios ORDER BY nome")


def obter_usuario(usuario_id: int) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM usuarios WHERE id = ?", (usuario_id,))


def obter_usuario_por_email(email: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM usuarios WHERE email = ?", (email,))


def listar_papeis() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM papeis ORDER BY nome")


def obter_papel_por_nome(nome: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM papeis WHERE nome = ?", (nome,))


def listar_permissoes() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM permissoes ORDER BY nome")


def listar_papeis_do_usuario(usuario_id: int) -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(
            conexao,
            """
            SELECT p.* FROM papeis p
              JOIN usuario_papeis up ON up.papel_id = p.id
             WHERE up.usuario_id = ?
             ORDER BY p.nome
            """,
            (usuario_id,),
        )


def listar_permissoes_do_usuario(usuario_id: int) -> list[str]:
    with conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT DISTINCT pe.nome AS nome
              FROM permissoes pe
              JOIN papel_permissoes pp ON pp.permissao_id = pe.id
              JOIN usuario_papeis up    ON up.papel_id = pp.papel_id
             WHERE up.usuario_id = ?
             ORDER BY pe.nome
            """,
            (usuario_id,),
        ).fetchall()
    return [linha["nome"] for linha in linhas]


def listar_permissoes_do_papel(papel_id: int) -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(
            conexao,
            """
            SELECT pe.* FROM permissoes pe
              JOIN papel_permissoes pp ON pp.permissao_id = pe.id
             WHERE pp.papel_id = ?
             ORDER BY pe.nome
            """,
            (papel_id,),
        )


def obter_sessao(token_hash: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM sessoes WHERE token_hash = ?", (token_hash,))


def listar_sessoes() -> list[dict[str, Any]]:
    with conectar() as conexao:
        return _linhas(conexao, "SELECT * FROM sessoes ORDER BY id DESC")


def obter_maquina_por_token_hash(token_hash: str) -> dict[str, Any] | None:
    with conectar() as conexao:
        return _linha(conexao, "SELECT * FROM maquinas WHERE token_hash = ?", (token_hash,))
