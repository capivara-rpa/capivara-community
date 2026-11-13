"""Regras de negócio da Control Room.

Concentra o que o servidor web e os agentes precisam: registro/heartbeat de
máquinas, catálogo de processos, criação e despacho de jobs.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from core.control_room import banco, cofre, feriados as feriados_br, seguranca
from core.control_room.banco import (
    ITEM_ABANDONADO,
    ITEM_CONCLUIDO,
    ITEM_COR,
    ITEM_EM_PROCESSAMENTO,
    ITEM_ENCERRADO,
    ITEM_FALHOU,
    ITEM_NOVO,
    ITEM_ROTULO,
    ITEM_VALIDOS,
    JOB_CANCELADO,
    JOB_CONCLUIDO,
    JOB_COR,
    JOB_EM_EXECUCAO,
    JOB_FALHOU,
    JOB_PENDENTE,
    JOB_ROTULO,
    JOB_VALIDOS,
    MAQUINA_COR,
    MAQUINA_OCUPADA,
    MAQUINA_OFFLINE,
    MAQUINA_ONLINE,
    MAQUINA_ROTULO,
    conectar,
    contagem_itens,
    listar_assets as _listar_assets_brutos,
    listar_auditoria as _listar_auditoria_brutas,
    listar_empresas as _listar_empresas_brutas,
    listar_filas as _listar_filas_brutas,
    listar_itens as _listar_itens_brutos,
    listar_jobs,
    listar_maquinas as _listar_maquinas_brutas,
    listar_papeis as _listar_papeis_brutos,
    listar_papeis_do_usuario as _listar_papeis_do_usuario_brutos,
    listar_permissoes as _listar_permissoes_brutas,
    listar_permissoes_asset as _listar_permissoes_asset_brutas,
    listar_permissoes_do_papel as _listar_permissoes_do_papel_brutas,
    listar_permissoes_do_usuario as _listar_permissoes_do_usuario_brutas,
    listar_processos as _listar_processos_brutos,
    listar_processos_fila,
    listar_sessoes as _listar_sessoes_brutas,
    listar_triggers as _listar_triggers_brutos,
    listar_usuarios as _listar_usuarios_brutos,
    listar_versoes_asset as _listar_versoes_asset_brutas,
    obter_asset_por_nome,
    obter_empresa_por_nome,
    obter_fila,
    obter_fila_por_nome,
    obter_item,
    obter_job,
    obter_maquina_por_nome,
    obter_maquina_por_token_hash,
    obter_papel_por_nome,
    obter_processo,
    obter_processo_por_nome,
    obter_sessao,
    obter_trigger,
    obter_usuario,
    obter_usuario_por_email,
)
from core.monitor.banco import agora_iso
from settings.parametros import (
    ADMIN_EMAIL,
    ADMIN_SENHA,
    LIMITE_JOB_SEGUNDOS,
    RETENCAO_AUDITORIA_DIAS,
    SEGUNDOS_OFFLINE,
    SESSAO_HORAS,
)

# Processos de exemplo já cadastrados na primeira execução
PROCESSOS_EXEMPLO = [
    {
        "nome": "Google — Busca (web)",
        "descricao": "Abre o navegador e faz uma busca no Google.",
        "fluxo": "app.fluxos:buscar_no_google",
        "usa_navegador": True,
    },
    {
        "nome": "Dados — Tratar planilha",
        "descricao": "Lê o CSV de clientes, filtra por estado e gera Excel/CSV.",
        "fluxo": "app.fluxos:tratar_planilha",
        "usa_navegador": False,
    },
]


# ----------------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------------
def _texto(valor: str | None) -> str | None:
    texto = (valor or "").strip()
    return texto or None


def _idade_segundos(instante: str | None) -> float:
    if not instante:
        return float("inf")
    try:
        momento = datetime.strptime(instante, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        momento = datetime.strptime(instante, "%Y-%m-%d %H:%M:%S")
    return (datetime.now() - momento).total_seconds()


def _estado_maquina(maquina: dict[str, Any]) -> str:
    if _idade_segundos(maquina.get("ultima_atividade")) > SEGUNDOS_OFFLINE:
        return MAQUINA_OFFLINE
    return maquina.get("status") or MAQUINA_ONLINE


# ----------------------------------------------------------------------
# Máquinas
# ----------------------------------------------------------------------
def registrar_maquina(
    nome: str,
    tags: str | None = None,
    ip: str | None = None,
    info: str | None = None,
) -> dict[str, Any]:
    """Registra (ou atualiza) uma máquina e marca como online."""
    with conectar() as conexao:
        maquina = _registrar_maquina(conexao, nome, tags, ip, info)
    logger.debug(f"[control-room] máquina '{nome}' registrada")
    return maquina


def _registrar_maquina(
    conexao: sqlite3.Connection,
    nome: str,
    tags: str | None = None,
    ip: str | None = None,
    info: str | None = None,
) -> dict[str, Any]:
    momento = agora_iso()
    linha = conexao.execute(
        """
        INSERT INTO maquinas (nome, status, tags, ip, info, ultima_atividade, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (nome) DO UPDATE SET
            status = excluded.status,
            tags = COALESCE(excluded.tags, maquinas.tags),
            ip = COALESCE(excluded.ip, maquinas.ip),
            info = COALESCE(excluded.info, maquinas.info),
            ultima_atividade = excluded.ultima_atividade
        RETURNING *
        """,
        (nome, MAQUINA_ONLINE, tags, ip, info, momento, momento),
    ).fetchone()
    return dict(linha)


def heartbeat(nome: str) -> dict[str, Any] | None:
    """Atualiza o batimento da máquina (mantém online)."""
    with conectar() as conexao:
        conexao.execute(
            "UPDATE maquinas SET ultima_atividade = ? WHERE nome = ?",
            (agora_iso(), nome),
        )
    return obter_maquina_por_nome(nome)


def _definir_status_maquina(maquina_id: int, status: str) -> None:
    with conectar() as conexao:
        _atualizar_status_maquina(conexao, maquina_id, status)


def _atualizar_status_maquina(
    conexao: sqlite3.Connection, maquina_id: int, status: str
) -> None:
    conexao.execute(
        "UPDATE maquinas SET status = ?, ultima_atividade = ? WHERE id = ?",
        (status, agora_iso(), maquina_id),
    )


def listar_maquinas() -> list[dict[str, Any]]:
    """Lista máquinas com o estado calculado (online/ocupada/offline) e o job atual."""
    maquinas = _listar_maquinas_brutas()
    jobs = listar_jobs(limite=500)

    atual = {}
    for job in jobs:
        if job["status"] == JOB_EM_EXECUCAO and job["maquina_id"] is not None:
            atual[job["maquina_id"]] = job

    for maquina in maquinas:
        maquina["tem_token"] = bool(maquina.pop("token_hash", None))
        maquina["estado"] = _estado_maquina(maquina)
        maquina["cor"] = MAQUINA_COR.get(maquina["estado"], "#64748b")
        maquina["job_atual"] = atual.get(maquina["id"])
    return maquinas


def cadastrar_maquina(
    nome: str,
    tags: str | None = None,
    info: str | None = None,
    ator: str | None = None,
) -> dict[str, Any]:
    """Cadastra uma máquina manualmente (fica offline até um agente conectar).

    Diferente de :func:`registrar_maquina` (chamado pelo próprio agente), aqui a
    máquina entra no inventário sem batimento — o estado vira ``online`` só quando
    o agente correspondente fizer o primeiro heartbeat.
    """
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome da máquina.")
    if obter_maquina_por_nome(nome) is not None:
        raise ValueError(f"A máquina '{nome}' já está cadastrada.")
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO maquinas (nome, status, tags, info, ultima_atividade, criado_em)
            VALUES (?, ?, ?, ?, '', ?)
            """,
            (nome, MAQUINA_OFFLINE, _texto(tags), _texto(info), agora_iso()),
        )
    registrar_auditoria("maquina", recurso=f"maquina:{nome}", ator=ator, detalhe="cadastrada")
    logger.info(f"[control-room] máquina '{nome}' cadastrada")
    return next((m for m in listar_maquinas() if m["nome"] == nome), {})


def atualizar_maquina(
    nome: str,
    tags: str | None = None,
    info: str | None = None,
    ator: str | None = None,
) -> dict[str, Any] | None:
    """Atualiza as tags/observação de uma máquina cadastrada."""
    maquina = obter_maquina_por_nome(nome)
    if maquina is None:
        return None
    with conectar() as conexao:
        conexao.execute(
            "UPDATE maquinas SET tags = ?, info = ? WHERE id = ?",
            (_texto(tags), _texto(info), maquina["id"]),
        )
    registrar_auditoria("maquina", recurso=f"maquina:{nome}", ator=ator, detalhe="atualizada")
    logger.info(f"[control-room] máquina '{nome}' atualizada")
    return next((m for m in listar_maquinas() if m["nome"] == nome), None)


def apagar_maquina(nome: str, ator: str | None = None) -> bool:
    """Remove uma máquina do inventário (solta vínculos de jobs/filas/agendamentos)."""
    maquina = obter_maquina_por_nome(nome)
    if maquina is None:
        return False
    with conectar() as conexao:
        for tabela in ("jobs", "itens_fila", "triggers"):
            conexao.execute(
                f"UPDATE {tabela} SET maquina_id = NULL WHERE maquina_id = ?",
                (maquina["id"],),
            )
        conexao.execute("DELETE FROM maquinas WHERE id = ?", (maquina["id"],))
    registrar_auditoria("maquina", recurso=f"maquina:{nome}", ator=ator, detalhe="removida")
    logger.info(f"[control-room] máquina '{nome}' removida")
    return True


# ----------------------------------------------------------------------
# Processos
# ----------------------------------------------------------------------
def criar_processo(
    nome: str,
    descricao: str | None,
    fluxo: str,
    usa_navegador: bool = False,
    origem: str | None = None,
    origem_ref: str | None = None,
) -> dict[str, Any]:
    """Cadastra (ou atualiza) um processo no catálogo."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO processos (nome, descricao, fluxo, usa_navegador, ativo, criado_em, origem, origem_ref)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT (nome) DO UPDATE SET
                descricao = excluded.descricao,
                fluxo = excluded.fluxo,
                usa_navegador = excluded.usa_navegador,
                origem = COALESCE(excluded.origem, processos.origem),
                origem_ref = COALESCE(excluded.origem_ref, processos.origem_ref)
            """,
            (nome, descricao, fluxo, int(usa_navegador), agora_iso(), origem, origem_ref),
        )
    logger.debug(f"[control-room] processo '{nome}' cadastrado")
    return next((p for p in _listar_processos_brutos() if p["nome"] == nome), {})


def listar_processos() -> list[dict[str, Any]]:
    return _listar_processos_brutos()


def garantir_processos_exemplo() -> None:
    """Garante que o catálogo tenha os processos de exemplo."""
    for processo in PROCESSOS_EXEMPLO:
        criar_processo(**processo)


def apagar_processo(processo_id: int) -> bool:
    """Remove um processo e solta os vínculos (jobs, triggadores, filas, permissões)."""
    with conectar() as conexao:
        linha = conexao.execute("SELECT nome FROM processos WHERE id = ?", (processo_id,)).fetchone()
        if linha is None:
            return False
        conexao.execute("DELETE FROM fila_processos WHERE processo_id = ?", (processo_id,))
        conexao.execute("UPDATE filas SET processo_id = NULL WHERE processo_id = ?", (processo_id,))
        conexao.execute("DELETE FROM jobs WHERE processo_id = ?", (processo_id,))
        conexao.execute("DELETE FROM triggers WHERE processo_id = ?", (processo_id,))
        conexao.execute(
            "UPDATE asset_permissoes SET processo_id = NULL WHERE processo_id = ?", (processo_id,)
        )
        conexao.execute("DELETE FROM processos WHERE id = ?", (processo_id,))
    logger.info(f"[control-room] processo #{processo_id} ({linha['nome']}) removido")
    return True


# ----------------------------------------------------------------------
# Jobs
# ----------------------------------------------------------------------
def criar_job(
    processo_id: int,
    maquina_id: int | None = None,
    requisito_tag: str | None = None,
    mensagem: str | None = None,
) -> dict[str, Any]:
    """Dispara um novo job (status ``pendente``) para um processo.

    - ``maquina_id``: direciona o job para uma máquina específica.
    - ``requisito_tag``: exige que a máquina que pegar o job tenha essa tag (pool).
    """
    with conectar() as conexao:
        job = _criar_job(conexao, processo_id, maquina_id, requisito_tag, mensagem)
    logger.info(f"[control-room] job #{job['id']} criado para o processo {processo_id}")
    return job


def _criar_job(
    conexao: sqlite3.Connection,
    processo_id: int,
    maquina_id: int | None = None,
    requisito_tag: str | None = None,
    mensagem: str | None = None,
) -> dict[str, Any]:
    tag = requisito_tag.strip() if isinstance(requisito_tag, str) and requisito_tag.strip() else None
    cursor = conexao.execute(
        """
        INSERT INTO jobs (processo_id, maquina_id, requisito_tag, status, mensagem, criado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (processo_id, maquina_id, tag, JOB_PENDENTE, mensagem, agora_iso()),
    )
    job_id = int(cursor.lastrowid or 0)
    return banco._linha(conexao, banco._SQL_JOB_DETALHE + " WHERE j.id = ?", (job_id,)) or {}


def cancelar_job(job_id: int) -> dict[str, Any] | None:
    """Cancela um job pendente ou em execução.

    Para jobs **em execução**, marca o status como ``cancelado`` de imediato; o
    agente (se o fluxo cooperar via ``agente.cancelado()``) pode encerrar mais
    cedo, e a máquina só é liberada quando ele reporta a conclusão. Um job já
    encerrado não é alterado.
    """
    job = obter_job(job_id)
    if job is None:
        return None
    if job["status"] not in (JOB_PENDENTE, JOB_EM_EXECUCAO):
        return job

    with conectar() as conexao:
        conexao.execute(
            "UPDATE jobs SET status = ?, finalizado_em = ? WHERE id = ?",
            (JOB_CANCELADO, agora_iso(), job_id),
        )
    logger.info(f"[control-room] job #{job_id} cancelado (era {job['status']})")
    return obter_job(job_id)


def job_cancelado(job_id: int) -> bool:
    """Diz se um job foi cancelado (usado pelo agente para abortar com cooperação)."""
    job = obter_job(job_id)
    return bool(job and job["status"] == JOB_CANCELADO)



def reservar_proximo_job(nome_maquina: str) -> dict[str, Any] | None:
    """Reserva o próximo job pendente para a máquina (claim atômico).

    Retorna o job já com ``processo_nome`` e ``fluxo`` ou ``None`` se não houver.
    """
    maquina = registrar_maquina(nome_maquina)
    if not maquina:
        return None

    momento = agora_iso()
    with conectar() as conexao:
        linha = conexao.execute(
            """
            UPDATE jobs
               SET status = ?, maquina_id = ?, iniciado_em = ?
             WHERE id = (
                 SELECT j.id
                   FROM jobs j
                   LEFT JOIN maquinas m ON m.id = ?
                  WHERE j.status = ?
                    AND (j.maquina_id IS NULL OR j.maquina_id = ?)
                    AND (
                        j.requisito_tag IS NULL
                        OR (',' || REPLACE(COALESCE(m.tags, ''), ' ', '') || ',')
                           LIKE ('%,' || j.requisito_tag || ',%')
                    )
                  ORDER BY j.id
                  LIMIT 1
             )
            RETURNING id
            """,
            (JOB_EM_EXECUCAO, maquina["id"], momento, maquina["id"], JOB_PENDENTE, maquina["id"]),
        ).fetchone()

    if linha is None:
        return None

    _definir_status_maquina(maquina["id"], MAQUINA_OCUPADA)
    job = obter_job(int(linha["id"]))
    if job:
        logger.info(f"[control-room] job #{job['id']} reservado para '{nome_maquina}'")
    return job


def anexar_execucao(job_id: int, execucao_id: int) -> None:
    """Liga o job à execução do monitor (para abrir o trace)."""
    with conectar() as conexao:
        conexao.execute("UPDATE jobs SET execucao_id = ? WHERE id = ?", (execucao_id, job_id))


def concluir_job(job_id: int, sucesso: bool, mensagem: str | None = None) -> dict[str, Any] | None:
    """Finaliza um job como concluído ou falhou e libera a máquina.

    Se o job já tiver sido **cancelado** (enquanto rodava), o status é mantido —
    apenas a mensagem final é registrada e a máquina é liberada.
    """
    status = JOB_CONCLUIDO if sucesso else JOB_FALHOU
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT maquina_id, status FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        cancelado = bool(linha and linha["status"] == JOB_CANCELADO)
        if cancelado:
            conexao.execute(
                "UPDATE jobs SET mensagem = ? WHERE id = ?",
                (mensagem or "cancelado durante a execução", job_id),
            )
        else:
            conexao.execute(
                "UPDATE jobs SET status = ?, mensagem = ?, finalizado_em = ? WHERE id = ?",
                (status, mensagem, agora_iso(), job_id),
            )

    if linha and linha["maquina_id"] is not None:
        _definir_status_maquina(int(linha["maquina_id"]), MAQUINA_ONLINE)

    if cancelado:
        logger.info(f"[control-room] job #{job_id} encerrado após cancelamento")
    else:
        logger.info(f"[control-room] job #{job_id} → {JOB_ROTULO.get(status, status)}")
    return obter_job(job_id)


# ----------------------------------------------------------------------
# Triggers (agendamentos)
# ----------------------------------------------------------------------
def _formatar(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _para_datetime(instante: str) -> datetime:
    try:
        return datetime.strptime(instante, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return datetime.strptime(instante, "%Y-%m-%d %H:%M:%S")


def _parse_hora(hora: str | None) -> tuple[int, int]:
    try:
        hh, mm = (hora or "00:00").split(":")
        return int(hh), int(mm)
    except (ValueError, AttributeError):
        return 0, 0


# Limites de cada campo do cron (minuto, hora, dia, mês, dia da semana)
_CRON_LIMITES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
_CRON_DIAS_SEMANA = {
    "dom": 0, "seg": 1, "ter": 2, "qua": 3, "qui": 4, "sex": 5, "sab": 6, "sáb": 6,
}


def _campo_cron(campo: str, indice: int) -> set[int]:
    """Expande um campo do cron (``*``, ``*/n``, ``a-b``, listas, nomes de dia)."""
    minimo, maximo = _CRON_LIMITES[indice]
    valores: set[int] = set()

    def item(parte: str) -> None:
        parte = parte.strip().lower()
        if indice == 4 and parte in _CRON_DIAS_SEMANA:
            valores.add(_CRON_DIAS_SEMANA[parte])
            return

        def numero(txt: str) -> int:
            txt = txt.strip().lower()
            if indice == 4 and txt in _CRON_DIAS_SEMANA:
                return _CRON_DIAS_SEMANA[txt]
            return int(txt)

        passo = 1
        if "/" in parte:
            base_parte, _, passo_txt = parte.partition("/")
            passo = int(passo_txt) if passo_txt.isdigit() and int(passo_txt) > 0 else 1
            parte = base_parte or "*"
        if parte in ("*", ""):
            inicio, fim = minimo, maximo
        elif "-" in parte:
            inicio_txt, _, fim_txt = parte.partition("-")
            inicio, fim = numero(inicio_txt), numero(fim_txt)
        else:
            inicio = fim = numero(parte)
        for valor in range(inicio, fim + 1, passo):
            if minimo <= valor <= maximo:
                valores.add(7 if (indice == 4 and valor == 7) else valor)

    for parte in campo.split(","):
        if parte.strip():
            item(parte)
    return valores or {minimo}


def _proxima_cron(expressao: str, base: datetime | None = None) -> str:
    """Calcula a próxima execução de uma expressão cron de 5 campos.

    Campos: ``minuto hora dia mês dia_semana``. Aceita ``*``, ``*/n``, ``a-b``
    e listas (``1,15``) além de nomes de dia (``seg,qua``). Dia da semana: 0/7
    = domingo.
    """
    return _formatar(_proxima_cron_dt(expressao, base))


def _proxima_cron_dt(expressao: str, base: datetime | None = None) -> datetime:
    campos = (expressao or "").split()
    if len(campos) != 5:
        raise ValueError("expressão cron deve ter 5 campos: 'min hora dia mês dia_semana'")
    minutos = _campo_cron(campos[0], 0)
    horas = _campo_cron(campos[1], 1)
    dias = _campo_cron(campos[2], 2)
    meses = _campo_cron(campos[3], 3)
    dias_semana = _campo_cron(campos[4], 4)

    momento = (base or datetime.now()).replace(second=0, microsecond=0) + timedelta(minutes=1)
    limite = momento + timedelta(days=366 * 5)
    while momento < limite:
        if (
            momento.minute in minutos
            and momento.hour in horas
            and momento.month in meses
            and (momento.weekday() + 1) % 7 in dias_semana
            and momento.day in dias
        ):
            return momento
        momento += timedelta(minutes=1)
    raise ValueError(f"não foi possível calcular a próxima execução de {expressao!r}")


def _dias_validos() -> set[int]:
    return {1, 2, 3, 4, 5, 6, 7}


def _normalizar_dias(dias: Any) -> str | None:
    """Normaliza os dias da semana (1=seg … 7=dom) para ``"1,2,3"`` (ou ``None``).

    Aceita lista/tupla de inteiros, string separada por vírgula, conjunto ou
    nomes (``seg``…``dom``). ``None`` ou o conjunto completo = "todos os dias".
    """
    if dias is None:
        return None
    if isinstance(dias, str):
        partes = [p.strip() for p in dias.split(",") if p.strip()]
    elif isinstance(dias, (list, tuple, set, frozenset)):
        partes = [str(p).strip() for p in dias]
    else:
        partes = [str(dias).strip()]

    nomes = {"seg": 1, "ter": 2, "qua": 3, "qui": 4, "sex": 5, "sab": 6, "sáb": 6, "dom": 7}
    valores: set[int] = set()
    for parte in partes:
        chave = parte.lower()
        if chave in nomes:
            valores.add(nomes[chave])
        elif chave.isdigit() and int(chave) in _dias_validos():
            valores.add(int(chave))
    if not valores or valores == _dias_validos():
        return None
    return ",".join(str(v) for v in sorted(valores))


def _dias_set(dias_semana: str | None) -> set[int]:
    if not dias_semana:
        return _dias_validos()
    return {int(p) for p in str(dias_semana).split(",") if p.strip().isdigit()}


def _dia_permitido(
    quando: datetime,
    dias_semana: str | None,
    incluir_fins: bool,
    incluir_feriados: bool,
) -> bool:
    if quando.isoweekday() >= 6 and not incluir_fins:
        return False
    if not incluir_feriados and feriados_br.e_feriado(quando.date()):
        return False
    return quando.isoweekday() in _dias_set(dias_semana)


def _proxima_execucao(
    tipo: str,
    intervalo_min: int | None,
    hora: str | None,
    base: datetime | None = None,
    expressao: str | None = None,
    dias_semana: str | None = None,
    incluir_fins: bool = True,
    incluir_feriados: bool = True,
) -> str:
    """Calcula a próxima execução já pulando dias não permitidos.

    ``tipo`` = ``intervalo`` (a cada ``intervalo_min`` minutos), ``diario``
    (``hora`` HH:MM) ou ``cron`` (5 campos). Fins de semana/feriados podem ser
    excluídos e ``dias_semana`` (1=seg … 7=dom) restringe os dias.
    """
    momento = _proximo_candidato(tipo, intervalo_min, hora, base, expressao)
    for _ in range(60 * 24 * 366):  # no máximo ~1 ano em minutos
        if _dia_permitido(momento, dias_semana, incluir_fins, incluir_feriados):
            break
        momento = _avancar_candidato(tipo, intervalo_min, hora, momento, expressao)
    return _formatar(momento)


def _proximo_candidato(
    tipo: str,
    intervalo_min: int | None,
    hora: str | None,
    base: datetime | None,
    expressao: str | None,
) -> datetime:
    base = base or datetime.now()
    if tipo == "diario":
        hh, mm = _parse_hora(hora)
        alvo = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return alvo if alvo > base else alvo + timedelta(days=1)
    if tipo == "cron":
        return _proxima_cron_dt(expressao or "", base)
    return base + timedelta(minutes=max(1, int(intervalo_min or 1)))


def _avancar_candidato(
    tipo: str,
    intervalo_min: int | None,
    hora: str | None,
    momento: datetime,
    expressao: str | None,
) -> datetime:
    if tipo == "diario":
        return momento + timedelta(days=1)
    if tipo == "cron":
        return _proxima_cron_dt(expressao or "", momento + timedelta(minutes=1))
    return momento + timedelta(minutes=max(1, int(intervalo_min or 1)))


def criar_trigger(
    processo_id: int,
    tipo: str = "intervalo",
    intervalo_min: int | None = None,
    hora: str | None = None,
    maquina_id: int | None = None,
    requisito_tag: str | None = None,
    expressao: str | None = None,
    dias_semana: Any = None,
    incluir_fins: bool = True,
    incluir_feriados: bool = True,
) -> dict[str, Any]:
    """Cria um agendamento que dispara jobs automaticamente.

    Tipos: ``intervalo`` (a cada N minutos), ``diario`` (HH:MM) e ``cron``
    (expressão de 5 campos em ``expressao``). ``dias_semana`` restringe os dias
    (1=seg … 7=dom); ``incluir_fins``/``incluir_feriados`` excluem fins de
    semana e feriados nacionais quando ``False``.
    """
    tipo = tipo if tipo in ("intervalo", "diario", "cron") else "intervalo"
    if tipo == "cron" and not (expressao or "").strip():
        raise ValueError("tipo 'cron' exige o campo 'expressao'")
    tag = requisito_tag.strip() if isinstance(requisito_tag, str) and requisito_tag.strip() else None
    dias = _normalizar_dias(dias_semana)
    proxima = _proxima_execucao(
        tipo, intervalo_min, hora, expressao=expressao,
        dias_semana=dias, incluir_fins=incluir_fins, incluir_feriados=incluir_feriados,
    )

    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO triggers
                (processo_id, maquina_id, requisito_tag, tipo, intervalo_min, hora,
                 expressao, dias_semana, incluir_fins, incluir_feriados, ativo,
                 proxima_execucao, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                processo_id, maquina_id, tag, tipo, intervalo_min, hora, expressao,
                dias, int(bool(incluir_fins)), int(bool(incluir_feriados)),
                proxima, agora_iso(),
            ),
        )
        trigger_id = int(cursor.lastrowid or 0)
    logger.info(f"[control-room] trigger #{trigger_id} criado ({tipo}) → próximo {proxima}")
    return obter_trigger(trigger_id) or {}


def listar_triggers() -> list[dict[str, Any]]:
    return _listar_triggers_brutos()


def apagar_trigger(trigger_id: int) -> None:
    with conectar() as conexao:
        conexao.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
    logger.info(f"[control-room] trigger #{trigger_id} removido")


def definir_trigger_ativo(trigger_id: int, ativo: bool) -> dict[str, Any] | None:
    """Pausa/retoma um agendamento (``ativo = 0/1``)."""
    with conectar() as conexao:
        conexao.execute("UPDATE triggers SET ativo = ? WHERE id = ?", (1 if ativo else 0, trigger_id))
    logger.info(f"[control-room] trigger #{trigger_id} {'ativado' if ativo else 'pausado'}")
    return obter_trigger(trigger_id)


def disparar_trigger(trigger_id: int) -> dict[str, Any] | None:
    """Dispara um agendamento manualmente (cria o job agora, sem mexer na agenda)."""
    trigger = obter_trigger(trigger_id)
    if trigger is None:
        return None
    criar_job(
        trigger["processo_id"],
        trigger["maquina_id"],
        trigger["requisito_tag"],
        mensagem=f"disparado manualmente pelo trigger #{trigger_id}",
    )
    return trigger


def _proxima_do_trigger(trigger: dict[str, Any], base: datetime) -> str:
    return _proxima_execucao(
        trigger["tipo"],
        trigger["intervalo_min"],
        trigger["hora"],
        base=base,
        expressao=trigger.get("expressao"),
        dias_semana=trigger.get("dias_semana"),
        incluir_fins=bool(trigger.get("incluir_fins", 1)),
        incluir_feriados=bool(trigger.get("incluir_feriados", 1)),
    )


def verificar_triggers() -> int:
    """Dispara os triggers vencidos e reagenda. Retorna quantos dispararam.

    Se o dia atual não for permitido (fim de semana/feriado/dia fora da lista),
    o agendamento é apenas reagendado — sem criar job.
    """
    agora = datetime.now()
    disparados = 0
    for trigger in _listar_triggers_brutos():
        if not trigger["ativo"] or not trigger["proxima_execucao"]:
            continue
        if _para_datetime(trigger["proxima_execucao"]) > agora:
            continue

        permitido = _dia_permitido(
            agora,
            trigger.get("dias_semana"),
            bool(trigger.get("incluir_fins", 1)),
            bool(trigger.get("incluir_feriados", 1)),
        )
        if permitido:
            criar_job(
                trigger["processo_id"],
                trigger["maquina_id"],
                trigger["requisito_tag"],
                mensagem=f"agendado pelo trigger #{trigger['id']}",
            )
            disparados += 1
        proxima = _proxima_do_trigger(trigger, agora)
        with conectar() as conexao:
            conexao.execute(
                "UPDATE triggers SET ultima_execucao = ?, proxima_execucao = ? WHERE id = ?",
                (agora_iso(), proxima, trigger["id"]),
            )
    return disparados


# ----------------------------------------------------------------------
# Assets (credenciais / variáveis centralizadas) — v2
# ----------------------------------------------------------------------
ASSET_SEGREDO = "segredo"
ASSET_TEXTO = "texto"
ASSET_TIPOS = (ASSET_SEGREDO, ASSET_TEXTO)

ACAO_CRIAR = "criar"
ACAO_LER = "ler"
ACAO_ROTACIONAR = "rotacionar"
ACAO_APAGAR = "apagar"
ACAO_PERMISSAO = "permissao"


def registrar_auditoria(
    acao: str,
    recurso: str | None = None,
    ator: str | None = None,
    resultado: str = "ok",
    detalhe: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Grava um evento na trilha de auditoria (append-only)."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO auditoria
                (quando, ator, acao, recurso, resultado, detalhe, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (agora_iso(), ator, acao, recurso, resultado, detalhe, ip, user_agent),
        )


def listar_auditoria(
    limite: int = 200,
    recurso: str | None = None,
    ator: str | None = None,
) -> list[dict[str, Any]]:
    """Trilha de auditoria (mais recente primeiro)."""
    return _listar_auditoria_brutas(limite=limite, recurso=recurso, ator=ator)


def expurgar_auditoria(dias: int | None = None) -> int:
    """Remove eventos de auditoria mais antigos que ``dias``.

    A retenção padrão vem de ``RETENCAO_AUDITORIA_DIAS`` (0 = não expurgar).
    Registra o próprio expurgo (append-only) e devolve quantos eventos saíram.
    """
    dias = RETENCAO_AUDITORIA_DIAS if dias is None else dias
    if not dias or dias <= 0:
        return 0
    limite = _formatar(datetime.now() - timedelta(days=int(dias)))
    with conectar() as conexao:
        cursor = conexao.execute("DELETE FROM auditoria WHERE quando < ?", (limite,))
        removidos = int(cursor.rowcount or 0)
    if removidos:
        registrar_auditoria(
            "expurgo", recurso="auditoria", detalhe=f"{removidos} evento(s) > {dias} dias"
        )
        logger.info(f"[control-room] auditoria: {removidos} evento(s) expurgado(s)")
    return removidos


def exportar_auditoria_csv(
    recurso: str | None = None,
    ator: str | None = None,
    limite: int = 100_000,
) -> str:
    """Exporta a auditoria em CSV (cabeçalho + eventos, mais antigos primeiro)."""
    import csv
    import io

    eventos = listar_auditoria(limite=limite, recurso=recurso, ator=ator)
    colunas = ["quando", "ator", "acao", "recurso", "resultado", "detalhe", "ip", "user_agent"]
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\n")
    escritor.writerow(colunas)
    for evento in reversed(eventos):
        escritor.writerow([evento.get(coluna, "") or "" for coluna in colunas])
    registrar_auditoria("exportar", recurso="auditoria", detalhe=f"{len(eventos)} evento(s)")
    return buffer.getvalue()


# ----------------------------------------------------------------------
# Monitoramento de SLA (jobs lentos / excedidos)
# ----------------------------------------------------------------------
ALERTA_OK = "ok"
ALERTA_LENTO = "lento"
ALERTA_EXCEDIDO = "excedido"


def duracao_segundos(job: dict[str, Any]) -> float | None:
    """Duração do job em segundos (até finalizar ou até agora, se em execução)."""
    inicio_txt = job.get("iniciado_em") or job.get("criado_em")
    if not inicio_txt:
        return None
    inicio = _para_datetime(inicio_txt)
    fim_txt = job.get("finalizado_em")
    fim = _para_datetime(fim_txt) if fim_txt else datetime.now()
    return (fim - inicio).total_seconds()


def classificar_job(job: dict[str, Any], limite: int | None = None) -> str:
    """Classifica um job em ``ok``/``lento``/``excedido`` conforme o SLA."""
    limite = limite or LIMITE_JOB_SEGUNDOS
    duracao = duracao_segundos(job)
    if duracao is None or not limite:
        return ALERTA_OK
    if duracao >= limite:
        return ALERTA_EXCEDIDO
    if duracao >= limite * 0.75:
        return ALERTA_LENTO
    return ALERTA_OK


def listar_alertas(limite_job: int | None = None) -> list[dict[str, Any]]:
    """Jobs que merecem atenção: em execução/lentos/excedidos acima do SLA."""
    limite_job = limite_job or LIMITE_JOB_SEGUNDOS
    alertas: list[dict[str, Any]] = []
    for job in listar_jobs(limite=200):
        classe = classificar_job(job, limite_job)
        if classe == ALERTA_OK:
            continue
        job["alerta"] = classe
        job["duracao_seg"] = round(duracao_segundos(job) or 0, 1)
        alertas.append(job)
    return alertas


def _gravar_versao(conexao, nome: str, versao: int, valor_guardado, ator) -> None:
    conexao.execute(
        """
        INSERT INTO asset_versoes (asset_nome, versao, valor, criado_em, criado_por)
        VALUES (?, ?, ?, ?, ?)
        """,
        (nome, versao, valor_guardado, agora_iso(), ator),
    )


def _asset_com_valor(nome: str) -> dict[str, Any] | None:
    """Asset com o valor real (decifrado), sem checar permissão nem auditar."""
    asset = obter_asset_por_nome(nome)
    if asset and asset["secreto"]:
        asset["valor"] = cofre.decifrar(asset["valor"])
    return asset


def criar_asset(
    nome: str,
    valor: str,
    secreto: bool = True,
    descricao: str | None = None,
    tipo: str | None = None,
    usuario: str | None = None,
    pasta: str | None = None,
    ator: str | None = None,
) -> dict[str, Any]:
    """Cadastra (ou atualiza) um asset. Segredos são **cifrados** no banco.

    Quando o asset já existe, o valor anterior fica guardado no histórico
    de versões (``asset_versoes``).
    """
    tipo = (tipo or (ASSET_SEGREDO if secreto else ASSET_TEXTO)).lower()
    if tipo not in ASSET_TIPOS:
        tipo = ASSET_SEGREDO if secreto else ASSET_TEXTO
    secreto = tipo == ASSET_SEGREDO
    valor_guardado = cofre.cifrar(valor) if secreto else valor
    momento = agora_iso()
    existente = obter_asset_por_nome(nome)
    with conectar() as conexao:
        if existente:
            nova_versao = int(existente.get("versao") or 1) + 1
            conexao.execute(
                """
                UPDATE assets
                   SET valor = ?, secreto = ?, tipo = ?, usuario = ?,
                       pasta = ?, descricao = ?, versao = ?,
                       atualizado_em = ?, atualizado_por = ?
                 WHERE nome = ?
                """,
                (
                    valor_guardado, int(secreto), tipo, usuario,
                    pasta, descricao, nova_versao, momento, ator, nome,
                ),
            )
        else:
            nova_versao = 1
            conexao.execute(
                """
                INSERT INTO assets
                    (nome, valor, secreto, tipo, usuario, pasta, versao,
                     descricao, criado_em, atualizado_em, atualizado_por)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    nome, valor_guardado, int(secreto), tipo, usuario,
                    pasta, descricao, momento, momento, ator,
                ),
            )
        _gravar_versao(conexao, nome, nova_versao, valor_guardado, ator)
    registrar_auditoria(
        ACAO_CRIAR if not existente else ACAO_ROTACIONAR,
        recurso=f"asset:{nome}",
        ator=ator,
        detalhe=f"versao={nova_versao}",
    )
    logger.debug(f"[control-room] asset '{nome}' salvo (v{nova_versao})")
    return _asset_com_valor(nome) or {}


def rotacionar_asset(
    nome: str,
    novo_valor: str,
    ator: str | None = None,
) -> dict[str, Any] | None:
    """Troca o valor de um asset existente, incrementando a versão."""
    existente = obter_asset_por_nome(nome)
    if not existente:
        return None
    secreto = bool(existente["secreto"])
    valor_guardado = cofre.cifrar(novo_valor) if secreto else novo_valor
    nova_versao = int(existente.get("versao") or 1) + 1
    momento = agora_iso()
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE assets
               SET valor = ?, versao = ?, atualizado_em = ?, atualizado_por = ?
             WHERE nome = ?
            """,
            (valor_guardado, nova_versao, momento, ator, nome),
        )
        _gravar_versao(conexao, nome, nova_versao, valor_guardado, ator)
    registrar_auditoria(
        ACAO_ROTACIONAR,
        recurso=f"asset:{nome}",
        ator=ator,
        detalhe=f"versao={nova_versao}",
    )
    logger.info(f"[control-room] asset '{nome}' rotacionado (v{nova_versao})")
    return _asset_com_valor(nome)


def listar_assets(mascarar: bool = True) -> list[dict[str, Any]]:
    """Lista os assets; por padrão mascara o valor dos secretos (para a UI)."""
    assets = _listar_assets_brutos()
    for asset in assets:
        if not asset["secreto"]:
            continue
        if mascarar:
            asset["valor"] = "••••••••" if asset["valor"] else asset["valor"]
        else:
            asset["valor"] = cofre.decifrar(asset["valor"])
    return assets


def listar_versoes_asset(nome: str, mascarar: bool = True) -> list[dict[str, Any]]:
    """Histórico de versões de um asset."""
    asset = obter_asset_por_nome(nome)
    secreto = bool(asset["secreto"]) if asset else True
    versoes = _listar_versoes_asset_brutas(nome)
    for versao in versoes:
        if not secreto:
            continue
        if mascarar:
            versao["valor"] = "••••••••" if versao["valor"] else versao["valor"]
        else:
            versao["valor"] = cofre.decifrar(versao["valor"])
    return versoes


def obter_asset(
    nome: str,
    ator: str | None = None,
    processo_id: int | None = None,
    auditar: bool = False,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any] | None:
    """Retorna o asset com o valor real (decifrado), usado pelo agente/robô.

    Respeita permissões por processo (quando existirem) e, se ``auditar``,
    grava a leitura na trilha de auditoria.
    """
    asset = obter_asset_por_nome(nome)
    if asset is None:
        if auditar:
            registrar_auditoria(
                ACAO_LER, recurso=f"asset:{nome}", ator=ator, resultado="negado",
                detalhe="inexistente", ip=ip, user_agent=user_agent,
            )
        return None
    if not _asset_permitido(nome, processo_id):
        registrar_auditoria(
            ACAO_LER, recurso=f"asset:{nome}", ator=ator, resultado="negado",
            detalhe="sem permissao", ip=ip, user_agent=user_agent,
        )
        return None
    if asset["secreto"]:
        asset["valor"] = cofre.decifrar(asset["valor"])
    if auditar:
        registrar_auditoria(
            ACAO_LER, recurso=f"asset:{nome}", ator=ator, resultado="ok",
            detalhe=f"versao={asset.get('versao')}", ip=ip, user_agent=user_agent,
        )
    return asset


def obter_credencial(
    nome: str,
    ator: str | None = None,
    processo_id: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any] | None:
    """Retorna ``{nome, usuario, senha, tipo, versao}`` de uma credencial."""
    asset = obter_asset(
        nome, ator=ator, processo_id=processo_id, auditar=True, ip=ip, user_agent=user_agent
    )
    if asset is None:
        return None
    return {
        "nome": asset["nome"],
        "usuario": asset.get("usuario"),
        "senha": asset["valor"],
        "tipo": asset.get("tipo"),
        "versao": asset.get("versao"),
    }


def _asset_permitido(nome: str, processo_id: int | None) -> bool:
    """Sem permissões cadastradas, o asset é aberto; com permissões, exige match."""
    permissoes = _listar_permissoes_asset_brutas(nome)
    if not permissoes:
        return True
    if processo_id is None:
        return False
    return any(p.get("processo_id") == processo_id for p in permissoes)


def conceder_permissao(
    nome: str,
    processo_id: int | None = None,
    pasta: str | None = None,
    ator: str | None = None,
) -> dict[str, Any]:
    """Concede acesso a um asset para um processo (ou pasta de robôs)."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO asset_permissoes (asset_nome, processo_id, pasta, criado_em)
            VALUES (?, ?, ?, ?)
            """,
            (nome, processo_id, pasta, agora_iso()),
        )
    registrar_auditoria(
        ACAO_PERMISSAO, recurso=f"asset:{nome}", ator=ator,
        detalhe=f"processo_id={processo_id} pasta={pasta}",
    )
    logger.info(f"[control-room] permissão concedida em '{nome}'")
    return {"asset": nome, "processo_id": processo_id, "pasta": pasta}


def listar_permissoes_asset(nome: str) -> list[dict[str, Any]]:
    """Permissões cadastradas em um asset."""
    return _listar_permissoes_asset_brutas(nome)


def remover_permissao(permissao_id: int, ator: str | None = None) -> None:
    with conectar() as conexao:
        conexao.execute("DELETE FROM asset_permissoes WHERE id = ?", (permissao_id,))
    registrar_auditoria(
        ACAO_PERMISSAO, recurso="permissoes", ator=ator, detalhe=f"removido id={permissao_id}"
    )
    logger.info(f"[control-room] permissão #{permissao_id} removida")


def apagar_asset(asset_id: int, ator: str | None = None) -> None:
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT nome FROM assets WHERE id = ?", (asset_id,)
        ).fetchone()
        nome = linha["nome"] if linha else None
        if nome:
            conexao.execute("DELETE FROM asset_versoes WHERE asset_nome = ?", (nome,))
            conexao.execute("DELETE FROM asset_permissoes WHERE asset_nome = ?", (nome,))
        conexao.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    if nome:
        registrar_auditoria(ACAO_APAGAR, recurso=f"asset:{nome}", ator=ator)
    logger.info(f"[control-room] asset #{asset_id} removido")


# ----------------------------------------------------------------------
# Filas (datapool — estilo UiPath Queues)
# ----------------------------------------------------------------------
def criar_fila(
    nome: str,
    descricao: str | None = None,
    processo_id: int | None = None,
    processos: list[int] | None = None,
) -> dict[str, Any]:
    """Cria uma fila de itens a processar.

    - ``processo_id``: robô "executor" principal.
    - ``processos``: lista de executores extras — a fila passa a distribuí-los
      em **round-robin**.
    """
    if processo_id is not None and obter_processo(processo_id) is None:
        raise ValueError(f"processo {processo_id} não existe no catálogo")
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO filas (nome, descricao, processo_id, criado_em)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (nome) DO UPDATE SET
                descricao = excluded.descricao,
                processo_id = excluded.processo_id
            """,
            (nome, descricao, processo_id, agora_iso()),
        )
    fila = obter_fila_por_nome(nome) or {}
    if fila.get("id") and processos is not None:
        definir_processos_fila(fila["id"], processos)
    logger.info(f"[control-room] fila '{nome}' garantida")
    resultado = obter_fila_por_nome(nome) or fila
    if resultado.get("id"):
        resultado["processos"] = listar_processos_fila(resultado["id"])
    return resultado


def definir_processos_fila(fila_id: int, processos: list[int]) -> list[dict[str, Any]]:
    """Define a lista de processos executores de uma fila (round-robin).

    O ``processo_id`` principal da fila é mantido à frente, se existir.
    """
    ids: list[int] = []
    for valor in processos or []:
        try:
            pid = int(valor)
        except (TypeError, ValueError):
            continue
        if pid not in ids and obter_processo(pid) is not None:
            ids.append(pid)
    with conectar() as conexao:
        conexao.execute("DELETE FROM fila_processos WHERE fila_id = ?", (fila_id,))
        conexao.executemany(
            "INSERT INTO fila_processos (fila_id, processo_id) VALUES (?, ?)",
            [(fila_id, pid) for pid in ids],
        )
    logger.info(f"[control-room] fila #{fila_id}: {len(ids)} processo(s) executor(es)")
    return listar_processos_fila(fila_id)



def listar_filas() -> list[dict[str, Any]]:
    """Lista as filas com a contagem de itens por status e executores."""
    filas = _listar_filas_brutas()
    for fila in filas:
        fila["contagem"] = contagem_itens(fila["id"])
        fila["processos"] = listar_processos_fila(fila["id"])
    return filas


def apagar_fila(fila_id: int) -> None:
    with conectar() as conexao:
        conexao.execute("DELETE FROM fila_processos WHERE fila_id = ?", (fila_id,))
        conexao.execute("DELETE FROM itens_fila WHERE fila_id = ?", (fila_id,))
        conexao.execute("DELETE FROM filas WHERE id = ?", (fila_id,))
    logger.info(f"[control-room] fila #{fila_id} removida")


def definir_fila_ativa(fila_id: int, ativo: bool) -> dict[str, Any] | None:
    """Ativa/desativa uma fila. Filas desativadas não entregam novos itens."""
    with conectar() as conexao:
        conexao.execute("UPDATE filas SET ativo = ? WHERE id = ?", (int(ativo), fila_id))
    logger.info(f"[control-room] fila #{fila_id} {'ativada' if ativo else 'desativada'}")
    return obter_fila(fila_id)


def _json_itens(dados: dict | None) -> str:
    return json.dumps(dados or {}, ensure_ascii=False, default=str)


def _carregar_dados(item: dict[str, Any]) -> dict[str, Any]:
    try:
        item["dados"] = json.loads(item.get("dados") or "{}")
    except (ValueError, TypeError):
        item["dados"] = {}
    return item


def adicionar_item(
    fila_id: int,
    dados: dict | None = None,
    referencia: str | None = None,
    prioridade: int = 0,
) -> dict[str, Any]:
    """Insere um item na fila (o robô executor vai consumi-lo)."""
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO itens_fila (fila_id, dados, referencia, prioridade, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (fila_id, _json_itens(dados), referencia, int(prioridade), agora_iso(), agora_iso()),
        )
        item_id = int(cursor.lastrowid or 0)
    logger.info(f"[control-room] item #{item_id} adicionado à fila {fila_id}")
    return _carregar_dados(obter_item(item_id) or {})


def adicionar_itens(
    fila_id: int,
    itens: list[dict[str, Any]],
    referencia_campo: str | None = None,
    prioridade: int = 0,
) -> int:
    """Insere vários itens de uma vez (retorna quantos foram adicionados).

    A prioridade pode vir por item (campo ``prioridade`` dentro do dicionário);
    senão usa-se a prioridade padrão do lote.
    """
    momento = agora_iso()

    def _prioridade(item: dict[str, Any]) -> int:
        try:
            return int(item.get("prioridade", prioridade))
        except (TypeError, ValueError):
            return int(prioridade)

    with conectar() as conexao:
        conexao.executemany(
            """
            INSERT INTO itens_fila (fila_id, dados, referencia, prioridade, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    fila_id,
                    _json_itens(item),
                    (item.get(referencia_campo) if referencia_campo else None),
                    _prioridade(item),
                    momento,
                    momento,
                )
                for item in itens
            ],
        )
    logger.info(f"[control-room] {len(itens)} item(ns) adicionados à fila {fila_id}")
    return len(itens)


def definir_prioridade_item(item_id: int, prioridade: int) -> dict[str, Any] | None:
    """Altera a prioridade de um item da fila (maior = consumido antes)."""
    item = obter_item(item_id)
    if item is None:
        return None
    with conectar() as conexao:
        conexao.execute(
            "UPDATE itens_fila SET prioridade = ?, atualizado_em = ? WHERE id = ?",
            (int(prioridade), agora_iso(), item_id),
        )
    logger.info(f"[control-room] item #{item_id} prioridade → {int(prioridade)}")
    return _carregar_dados(obter_item(item_id) or {})


def listar_itens(fila_id: int, status: str | None = None, limite: int = 200) -> list[dict[str, Any]]:
    """Lista os itens da fila (o campo ``dados`` volta como dict)."""
    itens = _listar_itens_brutos(fila_id, status=status, limite=limite)
    for item in itens:
        _carregar_dados(item)
    return itens


def obter_item_detalhe(item_id: int) -> dict[str, Any] | None:
    item = obter_item(item_id)
    return _carregar_dados(item) if item else None


def reservar_item(nome_fila: str, nome_maquina: str) -> dict[str, Any] | None:
    """Reivindica o próximo item ``novo`` da fila para uma máquina (claim atômico)."""
    with conectar() as conexao:
        conexao.execute("BEGIN IMMEDIATE")
        item = _reservar_item(conexao, nome_fila, nome_maquina)
    if item:
        logger.info(f"[control-room] item #{item['id']} reservado para '{nome_maquina}'")
    return item


def _reservar_item(
    conexao: sqlite3.Connection, nome_fila: str, nome_maquina: str
) -> dict[str, Any] | None:
    fila = banco._linha(conexao, "SELECT * FROM filas WHERE nome = ?", (nome_fila,))
    if fila and not fila.get("ativo", 1):
        logger.info(f"[control-room] fila '{nome_fila}' está desativada")
        return None
    maquina = _registrar_maquina(conexao, nome_maquina) if fila else None
    if not fila or not maquina:
        return None

    linha = conexao.execute(
        """
        UPDATE itens_fila
           SET status = ?, tentativas = tentativas + 1,
               maquina_id = ?, atualizado_em = ?
         WHERE id = (
             SELECT id FROM itens_fila
              WHERE fila_id = ? AND status = ?
              ORDER BY prioridade DESC, id
              LIMIT 1
         )
        RETURNING id
        """,
        (ITEM_EM_PROCESSAMENTO, maquina["id"], agora_iso(), fila["id"], ITEM_NOVO),
    ).fetchone()

    if linha is None:
        return None

    _atualizar_status_maquina(conexao, maquina["id"], MAQUINA_OCUPADA)
    item = banco._linha(
        conexao, banco._SQL_ITEM_DETALHE + " WHERE i.id = ?", (int(linha["id"]),)
    )
    return _carregar_dados(item) if item else None


def _executores_da_fila(conexao: sqlite3.Connection, fila: dict[str, Any]) -> list[int]:
    """Lista os processos executores da fila (principal + extras), sem repetir."""
    ids: list[int] = []
    principal = fila.get("processo_id")
    if principal is not None:
        ids.append(int(principal))
    for processo in conexao.execute(
        "SELECT processo_id FROM fila_processos WHERE fila_id = ? ORDER BY id", (fila["id"],)
    ):
        pid = processo["processo_id"]
        if pid is not None and int(pid) not in ids:
            ids.append(int(pid))
    return ids


def reservar_item_e_job(nome_fila: str, nome_maquina: str) -> dict[str, Any]:
    """Reserva um item e cria o job com o próximo processo executor.

    Se a fila tiver mais de um executor, eles são distribuídos em **round-robin**
    (o ponteiro ``filas.rr`` é avançado a cada item reservado).

    A reserva, o job e seus vínculos são persistidos na mesma transação.
    Filas sem executores continuam reservando o item sem criar um job.
    """
    job: dict[str, Any] | None = None
    with conectar() as conexao:
        # Serializa consumidores antes de ler a fila e selecionar o executor.
        # O contexto da conexão faz rollback se qualquer operação falhar.
        conexao.execute("BEGIN IMMEDIATE")
        item = _reservar_item(conexao, nome_fila, nome_maquina)
        if item is None:
            return {"item": None, "job": None}

        fila = banco._linha(conexao, "SELECT * FROM filas WHERE id = ?", (item["fila_id"],))
        executores = _executores_da_fila(conexao, fila)
        if executores:
            linha = conexao.execute(
                "UPDATE filas SET rr = rr + 1 WHERE id = ? RETURNING rr", (fila["id"],)
            ).fetchone()
            indice = (int(linha["rr"]) - 1) % len(executores) if linha else 0
            processo_id = executores[indice]
            job = _criar_job(
                conexao,
                processo_id,
                maquina_id=item["maquina_id"],
                mensagem=f"item #{item['id']} da fila '{nome_fila}'",
            )
            conexao.execute("UPDATE jobs SET item_id = ? WHERE id = ?", (item["id"], job["id"]))
            conexao.execute(
                "UPDATE itens_fila SET job_id = ? WHERE id = ?", (job["id"], item["id"])
            )
            item["job_id"] = job["id"]
            job["item_id"] = item["id"]
    logger.info(f"[control-room] item #{item['id']} reservado para '{nome_maquina}'")
    return {"item": item, "job": job}


def concluir_item(
    item_id: int,
    sucesso: bool,
    mensagem: str | None = None,
    max_retentativas: int = 3,
) -> dict[str, Any] | None:
    """Finaliza um item: concluído, falhou ou de volta à fila para retry."""
    item = obter_item(item_id)
    if item is None:
        return None

    if sucesso:
        status = ITEM_CONCLUIDO
    elif item["tentativas"] >= max_retentativas:
        status = ITEM_FALHOU
    else:
        status = ITEM_NOVO

    finaliza = status in ITEM_ENCERRADO
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE itens_fila
               SET status = ?, mensagem = ?, maquina_id = NULL,
                   atualizado_em = ?, finalizado_em = CASE WHEN ? THEN ? ELSE NULL END
             WHERE id = ?
            """,
            (status, mensagem, agora_iso(), finaliza, agora_iso(), item_id),
        )

    if item["maquina_id"] is not None:
        _definir_status_maquina(int(item["maquina_id"]), MAQUINA_ONLINE)

    resultado = obter_item(item_id)
    if resultado:
        logger.info(
            f"[control-room] item #{item_id} → {ITEM_ROTULO.get(status, status)}"
            + (" (retry)" if status == ITEM_NOVO else "")
        )
    return _carregar_dados(resultado) if resultado else None


def abandonar_item(item_id: int, mensagem: str | None = None) -> dict[str, Any] | None:
    """Marca um item como abandonado (ex.: máquina caiu no meio do processamento)."""
    item = obter_item(item_id)
    if item is None:
        return None
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE itens_fila
               SET status = ?, mensagem = ?, maquina_id = NULL,
                   atualizado_em = ?, finalizado_em = ?
             WHERE id = ?
            """,
            (ITEM_ABANDONADO, mensagem, agora_iso(), agora_iso(), item_id),
        )
    if item["maquina_id"] is not None:
        _definir_status_maquina(int(item["maquina_id"]), MAQUINA_ONLINE)
    logger.info(f"[control-room] item #{item_id} abandonado")
    return _carregar_dados(obter_item(item_id) or {})


def resumo_fila(nome_fila: str) -> dict[str, Any] | None:
    """Resumo de uma fila (dados + contagem). Devolve None se a fila não existe."""
    fila = obter_fila_por_nome(nome_fila)
    if fila is None:
        return None
    return {"fila": fila, "contagem": contagem_itens(fila["id"])}


# ----------------------------------------------------------------------
# Identidade: empresas, usuários, papéis e permissões (RBAC)
# ----------------------------------------------------------------------
PAPEL_ADMIN = "admin"

PERMISSOES_PADRAO: dict[str, str] = {
    "painel.ver": "Ver o painel e as execuções",
    "jobs.disparar": "Criar/disparar jobs",
    "jobs.cancelar": "Cancelar jobs",
    "processos.gerir": "Gerenciar o catálogo de processos",
    "triggers.gerir": "Gerenciar agendamentos",
    "assets.gerir": "Gerenciar assets e permissões",
    "assets.ler": "Ler credenciais/segredos",
    "filas.gerir": "Gerenciar filas e itens",
    "usuarios.gerir": "Gerenciar usuários, papéis e permissões",
    "auditoria.ver": "Consultar/exportar a auditoria",
    "maquinas.gerir": "Gerenciar máquinas e tokens",
    "pacotes.instalar": "Instalar pacotes de robôs",
}


def criar_empresa(nome: str, ativa: bool = True) -> dict[str, Any]:
    """Cria (ou atualiza) uma empresa — base do isolamento multiempresa."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO empresas (nome, ativa, criado_em)
            VALUES (?, ?, ?)
            ON CONFLICT (nome) DO UPDATE SET ativa = excluded.ativa
            """,
            (nome, int(ativa), agora_iso()),
        )
    return obter_empresa_por_nome(nome) or {}


def listar_empresas() -> list[dict[str, Any]]:
    return _listar_empresas_brutas()


def criar_permissao(nome: str, descricao: str | None = None) -> dict[str, Any]:
    """Cadastra uma permissão (recurso.acao)."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO permissoes (nome, descricao)
            VALUES (?, ?)
            ON CONFLICT (nome) DO UPDATE SET descricao = excluded.descricao
            """,
            (nome, descricao),
        )
        linha = conexao.execute("SELECT * FROM permissoes WHERE nome = ?", (nome,)).fetchone()
    return dict(linha) if linha else {}


def listar_permissoes() -> list[dict[str, Any]]:
    return _listar_permissoes_brutas()


def garantir_permissoes_padrao() -> None:
    for nome, descricao in PERMISSOES_PADRAO.items():
        criar_permissao(nome, descricao)


def criar_papel(
    nome: str,
    descricao: str | None = None,
    permissoes: list[str] | None = None,
) -> dict[str, Any]:
    """Cria (ou atualiza) um papel e, se informado, define suas permissões."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO papeis (nome, descricao, criado_em)
            VALUES (?, ?, ?)
            ON CONFLICT (nome) DO UPDATE SET descricao = excluded.descricao
            """,
            (nome, descricao, agora_iso()),
        )
    if permissoes is not None:
        definir_permissoes_papel(nome, permissoes)
    return obter_papel_por_nome(nome) or {}


def listar_papeis() -> list[dict[str, Any]]:
    """Lista os papéis com as permissões associadas."""
    papeis = _listar_papeis_brutos()
    for papel in papeis:
        papel["permissoes"] = [p["nome"] for p in listar_permissoes_do_papel(papel["id"])]
    return papeis


def definir_permissoes_papel(nome: str, permissoes: list[str]) -> None:
    """Substitui as permissões de um papel. Ações novas são criadas se preciso."""
    papel = obter_papel_por_nome(nome)
    if papel is None:
        raise ValueError(f"papel '{nome}' não existe")
    for permissao in permissoes:
        criar_permissao(permissao)
    with conectar() as conexao:
        conexao.execute("DELETE FROM papel_permissoes WHERE papel_id = ?", (papel["id"],))
        for permissao in permissoes:
            linha = conexao.execute(
                "SELECT id FROM permissoes WHERE nome = ?", (permissao,)
            ).fetchone()
            if linha:
                conexao.execute(
                    "INSERT OR IGNORE INTO papel_permissoes (papel_id, permissao_id) VALUES (?, ?)",
                    (papel["id"], linha["id"]),
                )
    logger.info(f"[control-room] papel '{nome}' com {len(permissoes)} permissão(ões)")


def listar_permissoes_do_papel(papel_id: int) -> list[dict[str, Any]]:
    return _listar_permissoes_do_papel_brutas(papel_id)


def criar_usuario(
    nome: str,
    email: str,
    senha: str,
    empresa_id: int | None = None,
    papeis: list[str] | None = None,
    admin: bool = False,
) -> dict[str, Any]:
    """Cria (ou atualiza) um usuário; a senha é guardada como hash."""
    email = email.strip().lower()
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO usuarios (empresa_id, nome, email, senha_hash, ativo, admin, criado_em)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT (email) DO UPDATE SET
                nome = excluded.nome,
                empresa_id = excluded.empresa_id,
                senha_hash = excluded.senha_hash,
                admin = excluded.admin
            """,
            (empresa_id, nome, email, seguranca.hash_senha(senha), int(admin), agora_iso()),
        )
    usuario = obter_usuario_por_email(email) or {}
    for papel in papeis or []:
        atribuir_papel(usuario["id"], papel)
    if admin:
        atribuir_papel(usuario["id"], PAPEL_ADMIN)
    logger.info(f"[control-room] usuário '{email}' salvo")
    return usuario


def listar_usuarios() -> list[dict[str, Any]]:
    """Lista os usuários (sem expor o hash da senha) com papéis e permissões."""
    usuarios = _listar_usuarios_brutos()
    for usuario in usuarios:
        usuario.pop("senha_hash", None)
        usuario["papeis"] = [p["nome"] for p in papeis_do_usuario(usuario["id"])]
        usuario["permissoes"] = permissoes_do_usuario(usuario["id"])
        empresa = usuario.get("empresa_id")
        usuario["empresa_nome"] = None
        if empresa:
            for emp in _listar_empresas_brutas():
                if emp["id"] == empresa:
                    usuario["empresa_nome"] = emp["nome"]
                    break
    return usuarios


def atribuir_papel(usuario_id: int, papel: str) -> None:
    """Associa um papel a um usuário (cria o papel se ainda não existir)."""
    if obter_papel_por_nome(papel) is None:
        criar_papel(papel)
    papel_id = (obter_papel_por_nome(papel) or {})["id"]
    with conectar() as conexao:
        conexao.execute(
            "INSERT OR IGNORE INTO usuario_papeis (usuario_id, papel_id) VALUES (?, ?)",
            (usuario_id, papel_id),
        )


def remover_papel(usuario_id: int, papel: str) -> None:
    papel = obter_papel_por_nome(papel)
    if papel is None:
        return
    with conectar() as conexao:
        conexao.execute(
            "DELETE FROM usuario_papeis WHERE usuario_id = ? AND papel_id = ?",
            (usuario_id, papel["id"]),
        )


def papeis_do_usuario(usuario_id: int) -> list[dict[str, Any]]:
    return _listar_papeis_do_usuario_brutos(usuario_id)


def permissoes_do_usuario(usuario_id: int) -> list[str]:
    return _listar_permissoes_do_usuario_brutas(usuario_id)


def autenticar(email: str, senha: str) -> dict[str, Any] | None:
    """Valida e-mail/senha. Devolve o usuário (sem hash) ou ``None``."""
    usuario = obter_usuario_por_email((email or "").strip().lower())
    if usuario is None or not usuario.get("ativo"):
        return None
    if not seguranca.conferir_senha(senha or "", usuario.get("senha_hash")):
        return None
    usuario.pop("senha_hash", None)
    return usuario


def criar_sessao(
    usuario: dict[str, Any],
    ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Cria uma sessão e devolve o token opaco (a guardar no cookie)."""
    token = seguranca.gerar_token()
    expira = _formatar(datetime.now() + timedelta(hours=SESSAO_HORAS))
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO sessoes (usuario_id, token_hash, criado_em, expira_em, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (usuario["id"], seguranca.hash_token(token), agora_iso(), expira, ip, user_agent),
        )
    logger.info(f"[control-room] sessão criada para '{usuario.get('email')}'")
    return token


def validar_sessao(token: str | None) -> dict[str, Any] | None:
    """Valida um token de sessão. Devolve ``{usuario, permissoes}`` ou ``None``."""
    if not token:
        return None
    sessao = obter_sessao(seguranca.hash_token(token))
    if sessao is None:
        return None
    if _para_datetime(sessao["expira_em"]) <= datetime.now():
        apagar_sessao(token)
        return None
    usuario = obter_usuario(int(sessao["usuario_id"]))
    if usuario is None or not usuario.get("ativo"):
        return None
    usuario.pop("senha_hash", None)
    return {
        "usuario": usuario,
        "permissoes": permissoes_do_usuario(usuario["id"]),
        "sessao_id": sessao["id"],
    }


def apagar_sessao(token: str | None) -> None:
    if not token:
        return
    with conectar() as conexao:
        conexao.execute("DELETE FROM sessoes WHERE token_hash = ?", (seguranca.hash_token(token),))


def limpar_sessoes_expiradas() -> int:
    """Remove sessões vencidas. Devolve quantas foram apagadas."""
    limite = _formatar(datetime.now())
    with conectar() as conexao:
        cursor = conexao.execute("DELETE FROM sessoes WHERE expira_em <= ?", (limite,))
        return int(cursor.rowcount or 0)


def listar_sessoes() -> list[dict[str, Any]]:
    """Sessões ativas (sem expor o token; apenas o ator e a validade)."""
    sessoes = _listar_sessoes_brutas()
    usuarios = {u["id"]: u for u in _listar_usuarios_brutos()}
    for sessao in sessoes:
        usuario = usuarios.get(sessao["usuario_id"], {})
        sessao["usuario_nome"] = usuario.get("nome")
        sessao["usuario_email"] = usuario.get("email")
        sessao.pop("token_hash", None)
    return sessoes


def garantir_admin_padrao() -> None:
    """Na primeira execução, cria o admin a partir de ``ADMIN_EMAIL``/``ADMIN_SENHA``."""
    garantir_permissoes_padrao()
    criar_papel(PAPEL_ADMIN, "Acesso total", list(PERMISSOES_PADRAO))
    if obter_usuario_por_email(ADMIN_EMAIL) is None:
        criar_usuario("Administrador", ADMIN_EMAIL, ADMIN_SENHA, papeis=[PAPEL_ADMIN], admin=True)
        logger.info(f"[control-room] admin padrão criado ({ADMIN_EMAIL})")


# ----------------------------------------------------------------------
# Token por máquina (identidade do agente)
# ----------------------------------------------------------------------
def emitir_token_maquina(nome: str) -> str:
    """Gera (e guarda o hash de) um token exclusivo para uma máquina.

    O token em texto puro só é devolvido aqui — guarde-o no agente.
    """
    token = seguranca.gerar_token(24)
    registrar_maquina(nome)
    with conectar() as conexao:
        conexao.execute(
            "UPDATE maquinas SET token_hash = ? WHERE nome = ?",
            (seguranca.hash_token(token), nome),
        )
    registrar_auditoria("token", recurso=f"maquina:{nome}", detalhe="emitido")
    logger.info(f"[control-room] token de máquina emitido para '{nome}'")
    return token


def revogar_token_maquina(nome: str) -> None:
    with conectar() as conexao:
        conexao.execute("UPDATE maquinas SET token_hash = NULL WHERE nome = ?", (nome,))
    registrar_auditoria("token", recurso=f"maquina:{nome}", detalhe="revogado")
    logger.info(f"[control-room] token de máquina revogado para '{nome}'")


def validar_token_maquina(token: str | None) -> dict[str, Any] | None:
    """Devolve a máquina dona do token (ou ``None``)."""
    if not token:
        return None
    return obter_maquina_por_token_hash(seguranca.hash_token(token))


# ----------------------------------------------------------------------
# Painel
# ----------------------------------------------------------------------
def resumo() -> dict[str, int]:
    """Contagens para os cartões da Control Room."""
    maquinas = listar_maquinas()
    online = sum(1 for m in maquinas if m["estado"] != MAQUINA_OFFLINE)
    offline = len(maquinas) - online

    contagem = {status: 0 for status in JOB_VALIDOS}
    with conectar() as conexao:
        for linha in conexao.execute(
            "SELECT status, COUNT(*) AS total FROM jobs GROUP BY status"
        ).fetchall():
            if linha["status"] in contagem:
                contagem[linha["status"]] = linha["total"]

    return {
        "maquinas_online": online,
        "maquinas_offline": offline,
        "maquinas_total": len(maquinas),
        "pendentes": contagem[JOB_PENDENTE],
        "em_execucao": contagem[JOB_EM_EXECUCAO],
        "concluidos": contagem[JOB_CONCLUIDO],
        "falhas": contagem[JOB_FALHOU],
        "cancelados": contagem[JOB_CANCELADO],
        "jobs_total": sum(contagem.values()),
    }


def montar_painel() -> dict[str, Any]:
    """Payload completo consumido pela Control Room."""
    return {
        "resumo": resumo(),
        "maquinas": listar_maquinas(),
        "processos": listar_processos(),
        "jobs": listar_jobs(limite=100),
        "triggers": listar_triggers(),
        "assets": listar_assets(mascarar=True),
        "asset_info": {"tipos": list(ASSET_TIPOS)},
        "auditoria": listar_auditoria(limite=50),
        "filas": listar_filas(),
        "itens_por_fila": {
            fila["nome"]: [_carregar_dados(i) for i in listar_itens(fila["id"], limite=50)]
            for fila in _listar_filas_brutas()
        },
        "alertas": listar_alertas(),
        "sla": {
            "limite_segundos": LIMITE_JOB_SEGUNDOS,
            "rotulos": {
                ALERTA_LENTO: "Lento",
                ALERTA_EXCEDIDO: "Excedido",
            },
            "cores": {ALERTA_LENTO: "#E0A400", ALERTA_EXCEDIDO: "#C0392B"},
        },
        "usuarios": listar_usuarios(),
        "papeis": listar_papeis(),
        "permissoes": listar_permissoes(),
        "empresas": listar_empresas(),
        "job_info": {
            status: {"rotulo": JOB_ROTULO[status], "cor": JOB_COR[status]} for status in JOB_VALIDOS
        },
        "item_info": {
            status: {"rotulo": ITEM_ROTULO[status], "cor": ITEM_COR[status]} for status in ITEM_VALIDOS
        },
        "maquina_info": {
            estado: {"rotulo": MAQUINA_ROTULO[estado], "cor": MAQUINA_COR[estado]}
            for estado in (MAQUINA_ONLINE, MAQUINA_OCUPADA, MAQUINA_OFFLINE)
        },
    }


def revisao() -> str:
    """Assinatura barata do estado da orquestração (para push em tempo real).

    Muda sempre que máquinas, jobs, itens de fila, assets ou triggers mudam. O
    painel usa isso via SSE para saber a hora de recarregar.
    """
    with conectar() as conexao:
        linha = conexao.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM maquinas) AS nm,
              (SELECT GROUP_CONCAT(ultima_atividade, '|')
                 FROM (SELECT ultima_atividade FROM maquinas ORDER BY id)) AS ma,
              (SELECT COUNT(*) FROM jobs) AS nj,
              (SELECT GROUP_CONCAT(status, '|')
                 FROM (SELECT status FROM jobs ORDER BY id)) AS js,
              (SELECT COALESCE(MAX(COALESCE(finalizado_em, iniciado_em, criado_em)), '')
                 FROM jobs) AS jt,
              (SELECT COUNT(*) FROM itens_fila) AS ni,
              (SELECT GROUP_CONCAT(id || ':' || status, '|')
                 FROM (SELECT id, status FROM itens_fila ORDER BY id)) AS is_,
              (SELECT COUNT(*) FROM processos) AS npr,
              (SELECT COUNT(*) FROM assets) AS na,
              (SELECT COALESCE(GROUP_CONCAT(nome || ':' || versao, '|'), '')
                 FROM (SELECT nome, versao FROM assets ORDER BY id)) AS av,
              (SELECT COUNT(*) FROM auditoria) AS nau,
              (SELECT COUNT(*) FROM filas) AS nf,
              (SELECT COUNT(*) FROM fila_processos) AS nfp,
              (SELECT COUNT(*) FROM triggers) AS nt,
              (SELECT COALESCE(GROUP_CONCAT(ativo || ':' || nome, '|'), '')
                 FROM (SELECT ativo, nome FROM filas ORDER BY id)) AS fa,
              (SELECT COUNT(*) FROM usuarios) AS nu,
              (SELECT COUNT(*) FROM papeis) AS np,
              (SELECT COALESCE(MAX(COALESCE(ultima_execucao, '')), '') FROM triggers) AS tt
            """
        ).fetchone()
    return ":".join(str(linha[chave]) for chave in linha.keys())


__all__ = [
    "registrar_maquina",
    "heartbeat",
    "listar_maquinas",
    "cadastrar_maquina",
    "atualizar_maquina",
    "apagar_maquina",
    "criar_processo",
    "listar_processos",
    "garantir_processos_exemplo",
    "criar_job",
    "cancelar_job",
    "job_cancelado",
    "reservar_proximo_job",
    "anexar_execucao",
    "concluir_job",
    "criar_trigger",
    "listar_triggers",
    "apagar_trigger",
    "criar_asset",
    "listar_assets",
    "listar_versoes_asset",
    "obter_asset",
    "obter_credencial",
    "rotacionar_asset",
    "conceder_permissao",
    "listar_permissoes_asset",
    "remover_permissao",
    "registrar_auditoria",
    "listar_auditoria",
    "apagar_asset",
    "obter_processo",
    "obter_processo_por_nome",
    "obter_fila",
    "criar_fila",
    "listar_filas",
    "apagar_fila",
    "definir_fila_ativa",
    "definir_processos_fila",
    "listar_processos_fila",
    "adicionar_item",
    "adicionar_itens",
    "definir_prioridade_item",
    "listar_itens",
    "obter_item_detalhe",
    "reservar_item",
    "reservar_item_e_job",
    "concluir_item",
    "abandonar_item",
    "resumo_fila",
    "resumo",
    "montar_painel",
    "revisao",
    "criar_empresa",
    "listar_empresas",
    "criar_permissao",
    "listar_permissoes",
    "garantir_permissoes_padrao",
    "criar_papel",
    "listar_papeis",
    "definir_permissoes_papel",
    "listar_permissoes_do_papel",
    "criar_usuario",
    "listar_usuarios",
    "atribuir_papel",
    "remover_papel",
    "papeis_do_usuario",
    "permissoes_do_usuario",
    "autenticar",
    "criar_sessao",
    "validar_sessao",
    "apagar_sessao",
    "limpar_sessoes_expiradas",
    "listar_sessoes",
    "garantir_admin_padrao",
    "emitir_token_maquina",
    "revogar_token_maquina",
    "validar_token_maquina",
    "expurgar_auditoria",
    "exportar_auditoria_csv",
    "duracao_segundos",
    "classificar_job",
    "listar_alertas",
]
