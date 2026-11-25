"""Testes do monitor de trace (execuções e passos)."""

from core.monitor import banco
from core.monitor.monitor import Monitor


def test_iniciar_execucao_e_registrar_passos():
    execucao_id = banco.iniciar_execucao("Robô de teste", mensagem="início")

    banco.registrar_passo(execucao_id, "Passo 1")
    banco.registrar_passo(execucao_id, "Passo 2", nivel="SUCCESS")

    passos = banco.listar_passos(execucao_id)
    assert [p["descricao"] for p in passos] == ["Passo 1", "Passo 2"]
    assert [p["ordem"] for p in passos] == [1, 2]

    banco.atualizar_status(execucao_id, banco.STATUS_FINALIZADO)
    execucao = banco.obter_execucao(execucao_id)
    assert execucao["status"] == "finalizado"
    assert execucao["fim"] is not None


def test_status_invalido_levanta_erro():
    execucao_id = banco.iniciar_execucao("Robô")
    try:
        banco.atualizar_status(execucao_id, "status-que-nao-existe")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("esperava ValueError para status inválido")


def test_monitor_registra_passos_e_finaliza():
    with Monitor("Robô de teste") as monitor:
        monitor.passo("Abrindo navegador")
        monitor.sucesso("Login realizado")
        monitor.finalizar()

    execucoes = banco.listar_execucoes()
    assert len(execucoes) == 1
    assert execucoes[0]["status"] == "finalizado"

    passos = banco.listar_passos(execucoes[0]["id"])
    assert len(passos) == 2


def test_monitor_captura_logs_automaticamente():
    from loguru import logger

    with Monitor("Robô com captura") as monitor:
        monitor.capturar_logs()
        logger.info("Evento de negócio relevante")

    execucoes = banco.listar_execucoes()
    passos = banco.listar_passos(execucoes[0]["id"])
    assert any("Evento de negócio relevante" in p["descricao"] for p in passos)


def test_resumo_status():
    banco.iniciar_execucao("A")
    execucao_b = banco.iniciar_execucao("B")
    banco.atualizar_status(execucao_b, banco.STATUS_FALHA)

    resumo = banco.resumo_status()
    assert resumo.get("iniciado", 0) == 1
    assert resumo.get("falha", 0) == 1


def test_revisao_muda_ao_criar_execucao_e_passo():
    r0 = banco.revisao()
    execucao_id = banco.iniciar_execucao("Robô revisão")
    r1 = banco.revisao()
    banco.registrar_passo(execucao_id, "passo")
    r2 = banco.revisao()

    assert r0 != r1
    assert r1 != r2


def test_conectar_fecha_conexao(monkeypatch):
    import sqlite3

    import pytest

    conexoes = []
    connect_original = sqlite3.connect

    def connect_espiado(*args, **kwargs):
        conexao = connect_original(*args, **kwargs)
        conexoes.append(conexao)
        return conexao

    monkeypatch.setattr(banco.sqlite3, "connect", connect_espiado)

    for _ in range(20):
        with banco.conectar():
            pass

    assert len(conexoes) == 20
    for conexao in conexoes:
        with pytest.raises(sqlite3.ProgrammingError):
            conexao.execute("SELECT 1")
