"""Testes do editor de fluxos e do PDD da Lagoa."""

import pytest

from core.control_room import pdd, servico, servidor


def _passos():
    return [
        {"nome": "Abrir o portal", "tipo": "acao", "detalhe": "Chrome headless"},
        {"nome": "Se o cliente estiver inadimplente", "tipo": "decisao", "sim": "Cobrar", "nao": "Baixar"},
        {"nome": "Erro ao consultar a API", "tipo": "excecao", "detalhe": "Registrar ocorrência"},
    ]


def test_passos_de_texto_reconhece_decisao_excecao_e_fim():
    passos = pdd.passos_de_texto(
        "Abrir o portal\n"
        "Se o cliente estiver inadimplente\n"
        "Senão registrar o pagamento\n"
        "Erro ao consultar a API\n"
        "Fim"
    )
    assert [p["tipo"] for p in passos] == ["acao", "decisao", "decisao", "excecao", "fim"]
    assert passos[1]["sim"] == "Sim"
    assert passos[2]["nao"] == "Não"


def test_normalizar_e_serializar_passos():
    normais = pdd.normalizar_passos(_passos())
    assert len(normais) == 3
    assert normais[0]["nome"] == "Abrir o portal"
    assert normais[0]["x"] == 60 and normais[0]["y"] == 60
    assert normais[1]["y"] == 164
    assert normais[2]["tipo"] == "excecao"

    brutos = pdd.serializar_passos(normais)
    assert pdd.carregar_passos(brutos)[1]["sim"] == "Cobrar"

    with pytest.raises(ValueError, match="limite"):
        pdd.normalizar_passos([{"nome": f"Passo {i}"} for i in range(pdd.LIMITE_PASSOS + 1)])


def test_mermaid_e_markdown_documentam_o_processo():
    fluxo = {
        "nome": "Conciliação",
        "descricao": "Concilia boletos",
        "execucoes_por_dia": 3,
        "versao": 2,
        "passos": pdd.normalizar_passos(_passos()),
    }
    grafo = pdd.gerar_mermaid(fluxo)
    assert "flowchart TD" in grafo
    assert "START([Início])" in grafo and "END([Fim])" in grafo
    assert 'P2{Se o cliente estiver inadimplente}' in grafo
    assert "P2 -->|não| D2" in grafo

    markdown = pdd.gerar_markdown(fluxo)
    assert "# PDD — Conciliação" in markdown
    assert "| Execuções por dia | 3 |" in markdown
    assert "1. **Ação — Abrir o portal**" in markdown
    assert "```mermaid" in markdown


def test_html_escapa_conteudo_e_inclui_estilos():
    html = pdd.gerar_html({"nome": "<script>x</script>", "passos": [], "versao": 1})
    assert "&lt;script&gt;" in html
    assert "<script>x</script>" not in html
    assert "flowchart TD" in html
    assert "@page" in html


def test_criar_atualizar_e_apagar_fluxo():
    fluxo = servico.criar_fluxo("Fluxo A", 4, _passos(), descricao="Teste", ator="ana")
    assert fluxo["id"] > 0
    assert fluxo["qtd_passos"] == 3
    assert fluxo["versao"] == 1

    atualizado = servico.atualizar_fluxo(
        fluxo["id"], nome="Fluxo A", execucoes_por_dia=5, passos=_passos(), ator="ana"
    )
    assert atualizado["versao"] == 2
    assert atualizado["execucoes_por_dia"] == 5

    assert [f["id"] for f in servico.listar_fluxos()] == [fluxo["id"]]
    assert servico.apagar_fluxo(fluxo["id"], ator="ana") is True
    assert servico.listar_fluxos() == []
    assert servico.apagar_fluxo(fluxo["id"]) is False
    assert any(a["recurso"] == "pdd:Fluxo A" for a in servico.listar_auditoria())


def test_fluxo_valida_nome_quantidade_e_vinculo():
    servico.criar_fluxo("Fluxo único", 1, _passos())
    with pytest.raises(ValueError, match="Já existe"):
        servico.criar_fluxo("fluxo único", 1, _passos())
    with pytest.raises(ValueError, match="Informe o nome"):
        servico.criar_fluxo("", 1, _passos())
    with pytest.raises(ValueError, match="Execuções por dia"):
        servico.criar_fluxo("Outro", 0, _passos())
    with pytest.raises(ValueError, match="ao menos um passo"):
        servico.criar_fluxo("Outro", 1, [])
    with pytest.raises(ValueError, match="não encontrada"):
        servico.criar_fluxo("Outro", 1, _passos(), processo_id=999999)

    processo = servico.criar_processo("Robô vinculado", "teste", "modo:funcao")
    fluxo = servico.criar_fluxo("Vinculado", 2, _passos(), processo_id=processo["id"])
    assert fluxo["processo_id"] == processo["id"]


def test_documento_pdd_e_painel():
    fluxo = servico.criar_fluxo("Documentado", 7, _passos(), descricao="Rotina diária")
    documento = servico.documento_pdd(fluxo["id"])
    assert documento["fluxo"]["nome"] == "Documentado"
    assert "Rotina diária" in documento["markdown"]
    assert servico.documento_pdd(999999) is None

    painel = servico.montar_painel()
    assert painel["fluxos"][0]["nome"] == "Documentado"
    assert painel["fluxos"][0]["qtd_passos"] == 3

    r0 = servico.revisao()
    servico.atualizar_fluxo(fluxo["id"], passos=_passos())
    r1 = servico.revisao()
    assert r0 != r1


def test_rota_de_fluxos_exige_permissao_pdd_gerir():
    assert servidor._permissao_da_rota("GET", "/api/orq/fluxos") == "pdd.gerir"
    assert servidor._permissao_da_rota("POST", "/api/orq/fluxos/12/remover") == "pdd.gerir"
    assert "pdd.gerir" in servico.PERMISSOES_PADRAO
