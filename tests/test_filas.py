"""Testes do datapool (filas + itens com retry e consumo transacional)."""

import pytest

from core.control_room import servico


def _criar_fila_com_processo(nome: str = "clientes") -> dict:
    processo = servico.criar_processo("Processo Fila", "desc", "app.fluxos:tratar_planilha")
    return servico.criar_fila(nome, descricao="fila de teste", processo_id=processo["id"])


def _preencher(fila_id: int, dados: list[dict], prioridade: int = 0) -> None:
    servico.adicionar_itens(fila_id, dados, referencia_campo="nome", prioridade=prioridade)


# ----------------------------------------------------------------------
# Criação e itens
# ----------------------------------------------------------------------
def test_criar_fila_e_painel():
    _criar_fila_com_processo()
    filas = servico.listar_filas()
    assert len(filas) == 1
    assert filas[0]["nome"] == "clientes"
    assert filas[0]["processo_nome"] == "Processo Fila"

    painel = servico.montar_painel()
    assert "filas" in painel
    assert "itens_por_fila" in painel
    assert "item_info" in painel


def test_criar_fila_rejeita_processo_inexistente():
    with pytest.raises(ValueError):
        servico.criar_fila("qualquer", processo_id=9999)


def test_adicionar_e_listar_itens():
    fila = _criar_fila_com_processo()
    _preencher(fila["id"], [{"nome": "ACME"}, {"nome": "XPTO"}])
    itens = servico.listar_itens(fila["id"])
    assert [i["referencia"] for i in itens] == ["ACME", "XPTO"]
    assert all(i["status"] == "novo" for i in itens)
    assert itens[0]["dados"] == {"nome": "ACME"}


def test_contagem_de_itens():
    fila = _criar_fila_com_processo()
    _preencher(fila["id"], [{"nome": "A"}, {"nome": "B"}, {"nome": "C"}])
    resumo = servico.resumo_fila("clientes")
    assert resumo["contagem"]["novo"] == 3
    assert resumo["contagem"]["em_processamento"] == 0
    assert resumo["contagem"]["concluido"] == 0


# ----------------------------------------------------------------------
# Consumo transacional
# ----------------------------------------------------------------------
def test_reservar_respeita_prioridade():
    fila = _criar_fila_com_processo()
    servico.adicionar_itens(fila["id"], [{"nome": "baixa"}], referencia_campo="nome", prioridade=0)
    servico.adicionar_itens(fila["id"], [{"nome": "alta"}], referencia_campo="nome", prioridade=50)

    primeiro = servico.reservar_item("clientes", "maq-01")
    assert primeiro["referencia"] == "alta"
    assert primeiro["status"] == "em_processamento"
    assert primeiro["tentativas"] == 1

    segundo = servico.reservar_item("clientes", "maq-01")
    assert segundo["referencia"] == "baixa"
    assert servico.reservar_item("clientes", "maq-01") is None


def test_reservar_item_e_job_ligam_item():
    fila = _criar_fila_com_processo()
    _preencher(fila["id"], [{"nome": "ACME"}])

    resposta = servico.reservar_item_e_job("clientes", "maq-01")
    assert resposta["item"] is not None
    assert resposta["job"] is not None
    assert resposta["item"]["job_id"] == resposta["job"]["id"]
    assert resposta["job"]["item_id"] == resposta["item"]["id"]


def test_concluir_com_sucesso():
    fila = _criar_fila_com_processo()
    _preencher(fila["id"], [{"nome": "ACME"}])
    item = servico.reservar_item("clientes", "maq-01")
    final = servico.concluir_item(item["id"], sucesso=True)
    assert final["status"] == "concluido"
    assert final["mensagem"] is None


def test_retry_ate_o_limite_e_depois_falha():
    fila = _criar_fila_com_processo()
    _preencher(fila["id"], [{"nome": "ACME"}])

    # tentativa 1 → falha antes do limite → volta para 'novo'
    item = servico.reservar_item("clientes", "maq-01")
    voltou = servico.concluir_item(item["id"], sucesso=False, max_retentativas=2)
    assert voltou["status"] == "novo"
    assert voltou["tentativas"] == 1

    # tentativa 2 → atinge o limite → falhou
    de_novo = servico.reservar_item("clientes", "maq-01")
    assert de_novo["id"] == item["id"]
    final = servico.concluir_item(de_novo["id"], sucesso=False, max_retentativas=2)
    assert final["status"] == "falhou"
    assert final["tentativas"] == 2


def test_abandonar_item_libera_maquina():
    fila = _criar_fila_com_processo()
    _preencher(fila["id"], [{"nome": "ACME"}])
    item = servico.reservar_item("clientes", "maq-01")
    maquina = next(m for m in servico.listar_maquinas() if m["nome"] == "maq-01")
    assert maquina["estado"] == "ocupada"

    abandonado = servico.abandonar_item(item["id"], "máquina caiu")
    assert abandonado["status"] == "abandonado"
    maquina = next(m for m in servico.listar_maquinas() if m["nome"] == "maq-01")
    assert maquina["estado"] == "online"


def test_apagar_fila_remove_itens():
    fila = _criar_fila_com_processo()
    _preencher(fila["id"], [{"nome": "ACME"}])
    servico.apagar_fila(fila["id"])
    assert servico.listar_filas() == []
    assert servico.resumo_fila("clientes") is None