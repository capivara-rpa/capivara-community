"""Atomicidade da reserva usando SQLite real e falhas injetadas por triggers."""

import json
import sqlite3
import traceback
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from core.control_room import banco, servico


@pytest.fixture
def reserva(tmp_path, monkeypatch):
    monkeypatch.setattr(banco, "BANCO_ORQUESTRADOR", tmp_path / "reserva.db")
    banco.iniciar_banco()
    principal = servico.criar_processo("Principal", None, "app.fluxos:tratar_planilha")
    extra = servico.criar_processo("Extra", None, "app.fluxos:tratar_planilha")
    fila = servico.criar_fila(
        "clientes", processo_id=principal["id"], processos=[principal["id"], extra["id"]]
    )
    item = servico.adicionar_item(fila["id"], {"nome": "ACME"}, referencia="ACME")
    maquina = servico.registrar_maquina("maq-01", tags="teste", info="preservar")
    return fila, item, maquina, [principal["id"], extra["id"]]


def _estado(fila_id, item_id, maquina_id):
    with banco.conectar() as conexao:
        return {
            "item": dict(
                conexao.execute("SELECT * FROM itens_fila WHERE id = ?", (item_id,)).fetchone()
            ),
            "jobs": [
                dict(linha) for linha in conexao.execute("SELECT * FROM jobs ORDER BY id")
            ],
            "rr": conexao.execute(
                "SELECT rr FROM filas WHERE id = ?", (fila_id,)
            ).fetchone()["rr"],
            "maquina": dict(
                conexao.execute("SELECT * FROM maquinas WHERE id = ?", (maquina_id,)).fetchone()
            ),
        }


def test_falha_criacao_job_reverte_reserva(reserva):
    fila, item, maquina, executores = reserva
    antes = _estado(fila["id"], item["id"], maquina["id"])
    with banco.conectar() as conexao:
        conexao.execute(
            """
            CREATE TRIGGER falha_criacao_job BEFORE INSERT ON jobs
            BEGIN
                SELECT RAISE(ABORT, 'falha controlada na criacao do job');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="falha controlada") as erro:
        servico.reservar_item_e_job("clientes", "maq-01")

    depois = _estado(fila["id"], item["id"], maquina["id"])
    with banco.conectar() as conexao:
        conexao.execute("DROP TRIGGER falha_criacao_job")
    recuperado = servico.reservar_item_e_job("clientes", "maq-01")
    print("".join(traceback.format_exception(erro.value)))
    print("ESTADO_APOS_FALHA=" + json.dumps(depois, ensure_ascii=False, sort_keys=True))
    print("ITEM_RECUPERADO=" + json.dumps(recuperado, ensure_ascii=False, sort_keys=True))

    assert depois == antes
    assert recuperado["item"]["id"] == item["id"]
    assert recuperado["item"]["tentativas"] == 1
    assert recuperado["item"]["maquina_id"] == maquina["id"]
    assert recuperado["item"]["job_id"] == recuperado["job"]["id"]
    assert recuperado["job"]["item_id"] == item["id"]
    assert recuperado["job"]["processo_id"] == executores[0]
    assert banco.obter_fila(fila["id"])["rr"] == 1


@pytest.mark.parametrize(
    "operacao",
    [
        "UPDATE OF item_id ON jobs",
        "UPDATE OF job_id ON itens_fila",
        "UPDATE OF rr ON filas",
        "UPDATE OF status ON maquinas WHEN NEW.status = 'ocupada'",
    ],
    ids=["vinculo_job", "vinculo_item", "round_robin", "estado_maquina"],
)
def test_falha_intermediaria_reverte_tudo(reserva, operacao):
    fila, item, maquina, executores = reserva
    with banco.conectar() as conexao:
        conexao.execute("UPDATE filas SET rr = 3 WHERE id = ?", (fila["id"],))
        conexao.execute(
            "UPDATE maquinas SET status = 'offline', ultima_atividade = '2000-01-01 00:00:00'"
        )
    antes = _estado(fila["id"], item["id"], maquina["id"])
    with banco.conectar() as conexao:
        conexao.execute(
            f"""
            CREATE TRIGGER falha_intermediaria BEFORE {operacao}
            BEGIN
                SELECT RAISE(ABORT, 'falha intermediaria');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="falha intermediaria"):
        servico.reservar_item_e_job("clientes", "maq-01")

    assert _estado(fila["id"], item["id"], maquina["id"]) == antes
    with banco.conectar() as conexao:
        conexao.execute("DROP TRIGGER falha_intermediaria")
    recuperado = servico.reservar_item_e_job("clientes", "maq-01")
    assert recuperado["item"]["id"] == item["id"]
    assert recuperado["job"]["processo_id"] == executores[1]
    assert banco.obter_fila(fila["id"])["rr"] == 4


def test_falha_reverte_cadastro_de_maquina(reserva):
    fila, item, _, _ = reserva
    with banco.conectar() as conexao:
        conexao.execute(
            """
            CREATE TRIGGER falha_job BEFORE INSERT ON jobs
            BEGIN SELECT RAISE(ABORT, 'falha job'); END
            """
        )
    with pytest.raises(sqlite3.IntegrityError, match="falha job"):
        servico.reservar_item_e_job("clientes", "maquina-nova")
    assert banco.obter_maquina_por_nome("maquina-nova") is None
    assert banco.obter_item(item["id"])["status"] == "novo"
    assert banco.obter_item(item["id"])["tentativas"] == 0
    assert banco.obter_item(item["id"])["maquina_id"] is None
    assert banco.obter_item(item["id"])["job_id"] is None
    assert banco.listar_jobs() == []
    assert banco.obter_fila(fila["id"])["rr"] == 0


def test_sucesso_preserva_detalhes_prioridade_e_round_robin(reserva):
    fila, primeiro, maquina, executores = reserva
    prioritario = servico.adicionar_item(fila["id"], {"nome": "urgente"}, prioridade=10)
    respostas = [servico.reservar_item_e_job("clientes", "maq-01") for _ in range(2)]
    assert [r["item"]["id"] for r in respostas] == [prioritario["id"], primeiro["id"]]
    assert [r["job"]["processo_id"] for r in respostas] == executores
    for resposta in respostas:
        item, job = resposta["item"], resposta["job"]
        assert item == servico.obter_item_detalhe(item["id"])
        assert job == banco.obter_job(job["id"])
        assert item["status"] == "em_processamento"
        assert item["tentativas"] == 1
        assert item["maquina_id"] == job["maquina_id"] == maquina["id"]
        assert item["job_id"] == job["id"]
        assert job["item_id"] == item["id"]
        assert job["status"] == "pendente"
        assert job["processo_nome"] in {"Principal", "Extra"}
        assert job["fluxo"] == "app.fluxos:tratar_planilha"
        assert job["mensagem"] == f"item #{item['id']} da fila 'clientes'"
    assert banco.obter_fila(fila["id"])["rr"] == 2
    assert banco.obter_maquina_por_nome("maq-01")["status"] == "ocupada"
    assert banco.obter_maquina_por_nome("maq-01")["tags"] == "teste"
    assert banco.obter_maquina_por_nome("maq-01")["info"] == "preservar"
    assert servico.reservar_item_e_job("clientes", "maq-01") == {"item": None, "job": None}
    assert banco.obter_fila(fila["id"])["rr"] == 2


@pytest.mark.parametrize("estado_fila", ["inexistente", "pausada", "vazia"])
def test_sem_item_nao_cria_job_nem_avanca_round_robin(reserva, estado_fila):
    fila, _, _, _ = reserva
    nome = "clientes"
    if estado_fila == "inexistente":
        nome = "inexistente"
    elif estado_fila == "pausada":
        servico.definir_fila_ativa(fila["id"], False)
    else:
        with banco.conectar() as conexao:
            conexao.execute("DELETE FROM itens_fila")
    assert servico.reservar_item_e_job(nome, "nova") == {"item": None, "job": None}
    assert banco.listar_jobs() == []
    assert banco.obter_fila(fila["id"])["rr"] == 0
    maquina = banco.obter_maquina_por_nome("nova")
    if estado_fila == "vazia":
        assert maquina["status"] == "online"
    else:
        assert maquina is None


def test_fila_sem_executores_reserva_item_sem_job(reserva):
    fila = servico.criar_fila("sem-executor")
    esperado = servico.adicionar_item(fila["id"], {"nome": "manual"})
    resposta = servico.reservar_item_e_job("sem-executor", "maq-01")
    assert resposta["item"]["id"] == esperado["id"]
    assert resposta["item"]["status"] == "em_processamento"
    assert resposta["item"]["tentativas"] == 1
    assert resposta["item"]["job_id"] is None
    assert resposta["job"] is None
    assert banco.obter_fila(fila["id"])["rr"] == 0
    assert banco.obter_maquina_por_nome("maq-01")["status"] == "ocupada"


def test_fila_com_apenas_executor_extra(reserva):
    _, _, _, executores = reserva
    fila = servico.criar_fila("somente-extra", processos=[executores[1]])
    servico.adicionar_item(fila["id"], {})
    resposta = servico.reservar_item_e_job("somente-extra", "maq-01")
    assert resposta["job"]["processo_id"] == executores[1]
    assert banco.obter_fila(fila["id"])["rr"] == 1


@pytest.mark.parametrize("total_itens", [1, 24])
def test_consumidores_concorrentes_sem_duplicidade(reserva, total_itens):
    fila, _, _, executores = reserva
    servico.adicionar_itens(fila["id"], [{"n": n} for n in range(total_itens - 1)])
    consumidores = 6
    inicio = Barrier(consumidores)

    def consumir(numero):
        inicio.wait(timeout=10)
        respostas = []
        while True:
            resposta = servico.reservar_item_e_job("clientes", f"consumidor-{numero}")
            if resposta["item"] is None:
                return respostas
            respostas.append(resposta)

    with ThreadPoolExecutor(max_workers=consumidores) as pool:
        grupos = list(pool.map(consumir, range(consumidores)))
    respostas = [resposta for grupo in grupos for resposta in grupo]
    itens = servico.listar_itens(fila["id"])
    jobs = sorted(banco.listar_jobs(), key=lambda job: job["id"])
    assert len(respostas) == len(itens) == len(jobs) == total_itens
    assert {r["item"]["id"] for r in respostas} == {i["id"] for i in itens}
    assert len({r["job"]["id"] for r in respostas}) == total_itens
    assert all(i["tentativas"] == 1 and i["status"] == "em_processamento" for i in itens)
    por_id = {i["id"]: i for i in itens}
    for job in jobs:
        assert por_id[job["item_id"]]["job_id"] == job["id"]
        assert por_id[job["item_id"]]["maquina_id"] == job["maquina_id"]
    assert [j["processo_id"] for j in jobs] == [
        executores[n % 2] for n in range(total_itens)
    ]
    assert banco.obter_fila(fila["id"])["rr"] == total_itens
