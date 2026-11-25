"""Testes das extensões: arquivos, dados, API, e-mail, notificações e sistema."""

import hashlib
import json
import sys

import pandas as pd
import pytest
import requests

from core.rpa import api, arquivo, dados, email, notificacoes, sistema, tracktab
from core.tratador import ErroRPA


# ----------------------------------------------------------------------
# arquivo.py
# ----------------------------------------------------------------------
def test_json_e_ini(tmp_path):
    caminho_json = tmp_path / "dados.json"
    arquivo.escrever_json(caminho_json, {"nome": "Ana", "itens": [1, 2]})
    assert arquivo.ler_json(caminho_json) == {"nome": "Ana", "itens": [1, 2]}

    caminho_ini = tmp_path / "config.ini"
    arquivo.escrever_ini(caminho_ini, {"geral": {"nome": "Ana", "numero": 2}})
    assert arquivo.ler_ini(caminho_ini) == {"geral": {"nome": "Ana", "numero": "2"}}

    invalido = tmp_path / "invalido.json"
    invalido.write_text("{", encoding="utf-8")
    with pytest.raises(ErroRPA):
        arquivo.ler_json(invalido)


def test_hash_comparacao_e_linhas(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("linha 1\nlinha 2\nlinha 3\n", encoding="utf-8")
    b.write_text("linha 1\nlinha 2\nlinha 3\n", encoding="utf-8")
    assert arquivo.calcular_hash(a) == hashlib.sha256(a.read_bytes()).hexdigest()
    assert arquivo.comparar_arquivos(a, b)
    b.write_text("outro", encoding="utf-8")
    assert not arquivo.comparar_arquivos(a, b)
    assert arquivo.ler_ultimas_linhas(a, 2) == ["linha 2", "linha 3"]
    assert arquivo.contar_linhas_arquivo(a) == 3
    assert arquivo.substituir_no_arquivo(a, "linha 2", "linha X") == 1
    assert arquivo.substituir_no_arquivo(a, "nao existe", "x") == 0
    with pytest.raises(ErroRPA):
        arquivo.substituir_no_arquivo(a, "", "x")
    with pytest.raises(ErroRPA):
        arquivo.calcular_hash(a, algoritmo="inexistente")


def test_juntar_dividir_e_tamanho(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("A\n", encoding="utf-8")
    b.write_text("B\n", encoding="utf-8")
    junto = arquivo.juntar_arquivos([a, b], tmp_path / "junto.txt", separador="")
    assert junto.read_text(encoding="utf-8") == "A\nB\n"

    partes = arquivo.dividir_arquivo(junto, linhas_por_arquivo=1, pasta_destino=tmp_path / "partes")
    assert len(partes) == 2
    assert todas_existem(partes)
    assert arquivo.tamanho_arquivo(junto, "B") > 0
    assert arquivo.tamanho_arquivo(junto, "KB") >= 0
    with pytest.raises(ErroRPA):
        arquivo.tamanho_arquivo(junto, "TB")
    with pytest.raises(ErroRPA):
        arquivo.dividir_arquivo(junto, 0)
    with pytest.raises(ErroRPA):
        arquivo.juntar_arquivos([], junto)


def todas_existem(caminhos):
    return all(caminho.is_file() for caminho in caminhos)


# ----------------------------------------------------------------------
# dados.py
# ----------------------------------------------------------------------
def test_transformacoes_de_dataframe():
    df = pd.DataFrame(
        {
            "nome": ["Ana", "Bia", "Ana"],
            "valor": [10, 20, 10],
            "uf": ["SP", "RJ", "SP"],
            "vazio": [None, "x", None],
        }
    )
    assert list(dados.renomear_colunas(df, {"nome": "cliente"}).columns)[0] == "cliente"
    assert len(dados.remover_duplicados(df, ["nome"])) == 2
    assert dados.preencher_vazios(df, valor=0)["vazio"].tolist() == [0, "x", 0]
    frente = dados.preencher_vazios(df, metodo="frente")["vazio"].tolist()
    assert pd.isna(frente[0])
    assert frente[1:] == ["x", "x"]
    assert dados.substituir_valores(df, {"SP": "São Paulo"}, ["uf"])["uf"].iloc[0] == "São Paulo"
    assert dados.ordenar_df(df, "valor", crescente=False)["valor"].iloc[0] == 20
    assert list(dados.selecionar_colunas(df, ["nome", "uf"]).columns) == ["nome", "uf"]
    assert len(dados.dividir_df(df, 2)) == 2
    assert len(dados.amostrar_df(df, 2)) == 2
    assert len(dados.amostrar_df(df, 2, aleatorio=False)) == 2
    assert len(dados.resumo_estatistico(df)) == len(df.columns)
    assert "| nome |" in dados.dataframe_para_markdown(df.head(1))
    with pytest.raises(ErroRPA):
        dados.preencher_vazios(df, metodo="invalido")
    with pytest.raises(ErroRPA):
        dados.selecionar_colunas(df, ["inexistente"])
    with pytest.raises(ErroRPA):
        dados.dividir_df(df, 0)


def test_datas_percentual_pivot_e_melt():
    df = pd.DataFrame(
        {
            "data": ["01/01/2026", "02/01/2026"],
            "uf": ["SP", "RJ"],
            "valor": [30, 70],
        }
    )
    com_data = dados.tratar_datas(df, ["data"])
    assert str(com_data["data"].dtype).startswith("datetime64")
    com_percentual = dados.calcular_percentual(com_data, "valor")
    assert com_percentual["percentual"].tolist() == [30.0, 70.0]
    tabela = dados.pivotar(df, "uf", "data", "valor", funcao="sum")
    assert tabela.loc["SP", "01/01/2026"] == 30
    assert len(dados.derreter(df, ids=["uf"], variaveis=["valor"])) == 2
    with pytest.raises(ErroRPA):
        dados.tratar_datas(df, ["inexistente"])
    with pytest.raises(ErroRPA):
        dados.calcular_percentual(df, "inexistente")
    with pytest.raises(ErroRPA):
        dados.calcular_percentual(pd.DataFrame({"valor": [0]}), "valor")


# ----------------------------------------------------------------------
# api.py
# ----------------------------------------------------------------------
class RespostaFalsa:
    ok = True
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}

    def iter_content(self, chunk_size=8192):
        yield b"conteudo"


def test_cliente_api_metodos(monkeypatch, tmp_path):
    chamadas = []

    def request_falso(metodo, url, **kwargs):
        chamadas.append((metodo, url, kwargs))
        return RespostaFalsa()

    cliente = api.ClienteAPI(base_url="https://exemplo.com")
    monkeypatch.setattr(cliente.sessao, "request", request_falso)
    assert cliente.api_get("/a").status_code == 200
    assert cliente.api_post("/b", json={"x": 1}).status_code == 200
    assert cliente.api_put("/c", json={"x": 1}).status_code == 200
    assert cliente.api_delete("/d").status_code == 200
    assert cliente.api_patch("/e", json={"x": 1}).status_code == 200
    assert cliente.api_head("/f").status_code == 200

    arquivo_upload = tmp_path / "enviar.txt"
    arquivo_upload.write_text("oi", encoding="utf-8")
    assert cliente.api_upload("/g", arquivo_upload, campo="file", dados={"y": "2"}).status_code == 200
    destino = tmp_path / "baixado.txt"
    assert cliente.api_download("/h", destino).read_text() == "conteudo"

    metodos = [chamada[0] for chamada in chamadas]
    assert metodos == ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "POST", "GET"]
    assert chamadas[0][1] == "https://exemplo.com/a"
    assert chamadas[6][2]["data"] == {"y": "2"}
    assert chamadas[7][2]["stream"] is True

    with pytest.raises(ErroRPA):
        cliente.api_upload("/g", tmp_path / "nao_existe.txt")


def test_funcoes_api_diretas(monkeypatch):
    monkeypatch.setattr(
        api.ClienteAPI,
        "api_get",
        lambda self, caminho="", params=None, **kwargs: RespostaFalsa(),
    )
    assert api.api_get("/x").status_code == 200


# ----------------------------------------------------------------------
# email.py
# ----------------------------------------------------------------------
class SMTPFalso:
    instancias = []

    def __init__(self, servidor, porta):
        self.servidor = servidor
        self.porta = porta
        self.starttls_chamado = False
        self.login_feito = None
        self.mensagem = None
        self.destinatarios = None
        self.fechado = False
        SMTPFalso.instancias.append(self)

    def starttls(self):
        self.starttls_chamado = True

    def login(self, usuario, senha):
        self.login_feito = (usuario, senha)

    def send_message(self, mensagem, to_addrs=None):
        self.mensagem = mensagem
        self.destinatarios = to_addrs

    def noop(self):
        return 250, b"OK"

    def quit(self):
        self.fechado = True


def test_enviar_email_com_html_copias_e_anexo(monkeypatch, tmp_path):
    SMTPFalso.instancias.clear()
    monkeypatch.setattr(email.smtplib, "SMTP", SMTPFalso)
    anexo = tmp_path / "relatorio.txt"
    anexo.write_text("dados", encoding="utf-8")
    email.enviar_email(
        ["a@exemplo.com"],
        "Assunto",
        "<b>Olá</b>",
        anexos=[anexo],
        servidor="smtp.exemplo.com",
        porta=587,
        usuario="usuario",
        senha="senha",
        remetente="robo@exemplo.com",
        html=True,
        cc="c@exemplo.com",
        bcc=["b@exemplo.com"],
        responder_para="resposta@exemplo.com",
    )
    conexao = SMTPFalso.instancias[-1]
    assert conexao.starttls_chamado
    assert conexao.login_feito == ("usuario", "senha")
    assert conexao.destinatarios == ["a@exemplo.com", "c@exemplo.com", "b@exemplo.com"]
    assert conexao.mensagem["Cc"] == "c@exemplo.com"
    assert conexao.mensagem["Reply-To"] == "resposta@exemplo.com"
    assert conexao.mensagem["Bcc"] is None
    assert conexao.mensagem.get_content_type() == "multipart/mixed"
    assert conexao.fechado


def test_testar_smtp(monkeypatch):
    SMTPFalso.instancias.clear()
    monkeypatch.setattr(email.smtplib, "SMTP", SMTPFalso)
    assert email.testar_smtp("smtp.exemplo.com", 587, "u", "s")
    assert SMTPFalso.instancias[-1].fechado


# ----------------------------------------------------------------------
# notificacoes.py
# ----------------------------------------------------------------------
class PostFalso:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


def test_notificacoes(monkeypatch):
    chamadas = []

    def post_falso(url, json=None, timeout=None):
        chamadas.append((url, json))
        return PostFalso()

    monkeypatch.setattr(notificacoes.requests, "post", post_falso)
    assert notificacoes.enviar_slack("https://slack", "Oi", titulo="Robô") == {"ok": True}
    assert chamadas[-1][1]["text"] == "*Robô*\nOi"
    notificacoes.enviar_teams("https://teams", "Oi", titulo="Robô")
    assert chamadas[-1][1]["@type"] == "MessageCard"
    notificacoes.enviar_discord("https://discord", "Oi")
    assert chamadas[-1][1]["content"] == "Oi"
    notificacoes.enviar_telegram("token", 123, "Oi")
    assert chamadas[-1][0].endswith("/sendMessage")
    notificacoes.enviar_webhook("https://webhook", {"a": 1})
    assert chamadas[-1][1] == {"a": 1}


def test_notificacao_com_falha(monkeypatch):
    def post_com_erro(*args, **kwargs):
        raise requests.RequestException("falhou")

    monkeypatch.setattr(notificacoes.requests, "post", post_com_erro)
    with pytest.raises(ErroRPA):
        notificacoes.enviar_slack("https://slack", "Oi")


# ----------------------------------------------------------------------
# sistema.py
# ----------------------------------------------------------------------
def test_executar_comando():
    resultado = sistema.executar_comando([sys.executable, "-c", "print('oi')"])
    assert resultado["codigo"] == 0
    assert resultado["saida"] == "oi"
    falha = sistema.executar_comando([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert falha["codigo"] == 3
    with pytest.raises(ErroRPA):
        sistema.executar_comando(
            [sys.executable, "-c", "import sys; sys.exit(3)"], verificar=True
        )
    with pytest.raises(ErroRPA):
        sistema.executar_comando([sys.executable, "-c", "import time; time.sleep(2)"], tempo_max=1)
    with pytest.raises(ErroRPA):
        sistema.executar_comando(["comando-que-nao-existe-xyz"])


def test_ambiente_e_info(monkeypatch):
    monkeypatch.setenv("CAPIVARA_TESTE", "1")
    assert sistema.obter_variavel_ambiente("CAPIVARA_TESTE") == "1"
    sistema.definir_variavel_ambiente("CAPIVARA_TESTE", "2")
    assert sistema.obter_variavel_ambiente("CAPIVARA_TESTE") == "2"
    info = sistema.obter_info_sistema()
    assert {"sistema", "python", "usuario", "pasta_atual"} <= set(info)
    assert sistema.pasta_temporaria().is_dir()


def test_esperar_arquivo_e_pasta(tmp_path):
    arquivo_existente = tmp_path / "pronto.txt"
    arquivo_existente.write_text("ok", encoding="utf-8")
    assert sistema.esperar_arquivo(arquivo_existente, tempo_max=1) == arquivo_existente.resolve()
    assert sistema.esperar_pasta(tmp_path, tempo_max=1) == tmp_path.resolve()
    with pytest.raises(ErroRPA):
        sistema.esperar_arquivo(tmp_path / "nao_existe.txt", tempo_max=1)
    with pytest.raises(ErroRPA):
        sistema.esperar_pasta(tmp_path / "nao_existe", tempo_max=1)


# ----------------------------------------------------------------------
# tracktab.py
# ----------------------------------------------------------------------
def _export_tracktab(nome_arquivo, elementos):
    return {
        "page": "https://exemplo.com",
        "title": "Exemplo",
        "timestamp": "2026-01-01T00:00:00",
        "elements": elementos,
    }


def test_tracktab(tmp_path):
    export = tmp_path / "tracktab.json"
    export.write_text(
        json.dumps(
            _export_tracktab(
                "x",
                [
                    {
                        "name": "Campo E-mail",
                        "tag": "input",
                        "text": "",
                        "fullXpath": "/html/body/input",
                        "relativeXpath": "//input[@id='email']",
                        "customPath": "#email",
                    },
                    {
                        "name": "Botão Entrar",
                        "tag": "button",
                        "text": "Entrar",
                        "fullXpath": "/html/body/button",
                        "relativeXpath": "//button[text()='Entrar']",
                        "customPath": "",
                    },
                ],
            )
        ),
        encoding="utf-8",
    )
    elementos = tracktab.carregar(export)
    assert set(elementos) == {"Campo E-mail", "Botão Entrar"}
    assert elementos["Campo E-mail"].seletor == "//input[@id='email']"
    assert tracktab.seletores(export, "custom")["Campo E-mail"] == "#email"
    assert tracktab.obter(export, "Botão Entrar") == "//button[text()='Entrar']"
    assert tracktab.buscar(export, "campo") == {"Campo E-mail": "//input[@id='email']"}
    assert tracktab.listar_nomes(export) == ["Campo E-mail", "Botão Entrar"]
    assert tracktab.para_lista(export)[0]["tag"] == "input"
    assert tracktab.resumo(export)["total"] == 2

    csv_saida = tmp_path / "seletores.csv"
    tracktab.exportar_csv(export, csv_saida)
    assert "Campo E-mail" in csv_saida.read_text(encoding="utf-8")

    segundo = tmp_path / "outro.json"
    segundo.write_text(
        json.dumps(
            _export_tracktab(
                "y",
                [
                    {
                        "name": "Campo Senha",
                        "tag": "input",
                        "text": "",
                        "fullXpath": "/html/body/input2",
                        "relativeXpath": "//input[@id='senha']",
                        "customPath": "#senha",
                    }
                ],
            )
        ),
        encoding="utf-8",
    )
    assert len(tracktab.combinar(export, segundo)) == 3

    with pytest.raises(ErroRPA):
        tracktab.seletores(export, "inexistente")
    with pytest.raises(ErroRPA):
        tracktab.obter(export, "Inexistente")
    with pytest.raises(ErroRPA):
        tracktab.combinar()
