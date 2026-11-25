"""Servidor web da Lagoa (orquestrador).

Reaproveita o handler do painel de trace (``core.monitor.servidor``) e
acrescenta:

- o frontend da Lagoa na raiz (``/``);
- o painel de trace servido em ``/monitor/``;
- as rotas de orquestração ``/api/orq/...`` (máquinas, processos e jobs).

    python -m core.control_room.servidor          # http://localhost:8765
    python -m core.control_room.servidor --porta 9000
"""

from __future__ import annotations

import argparse
import hmac
import json
import socket
import threading
import time
import webbrowser
from datetime import datetime
from http.cookies import SimpleCookie
from pathlib import Path

from urllib.parse import unquote, urlparse

from loguru import logger

from core.control_room import servico
from core.control_room.atualizador import iniciar_atualizador, verificar_atualizacoes
from core.control_room.banco import iniciar_banco as iniciar_banco_orq
from core.monitor.banco import iniciar_banco as iniciar_banco_monitor
from core.monitor.servidor import PASTA_ESTATICO as PASTA_MONITOR
from core.monitor.servidor import ManipuladorPainel, ThreadingHTTPServer, _aplicar_tls
from settings.parametros import (
    ABRIR_PAINEL,
    AUTO_ATUALIZAR,
    HOST_LAGOA,
    INTERVALO_TRIGGERS,
    LAGOA_AUTH,
    LAGOA_TOKEN,
    PORTA_LAGOA,
    TLS_CERT,
    TLS_CHAVE,
)

PASTA_ESTATICO = Path(__file__).resolve().parent / "estatico"
COOKIE_SESSAO = "sessao"


def _rota_de_agente(metodo: str, rota: str) -> bool:
    """Diz se a rota é usada apenas pelos agentes (e portanto exige token).

    As rotas do painel (navegador) continuam abertas; só as que os robôs
    chamam — registrar/buscar job, reportar execução, ler assets — pedem token.
    """
    if metodo == "GET":
        if rota.startswith("/api/orq/credenciais/"):
            return True
        if rota.startswith("/api/orq/assets/"):
            return not rota.endswith(("/versoes", "/auditoria"))
        return False
    if metodo != "POST":
        return False
    if rota.startswith("/api/orq/agente/"):
        return True
    if rota.startswith("/api/orq/jobs/") and rota.endswith(("/execucao", "/concluir")):
        return True
    if rota.startswith("/api/orq/itens/") and rota.endswith(("/resultado", "/abandonar")):
        return True
    if rota.startswith("/api/orq/filas/") and rota.endswith("/proximo"):
        return True
    return False


def _token_do_pedido(cabecalhos) -> str:
    """Extrai o token do cabeçalho (``Authorization: Bearer`` ou ``X-Token``)."""
    autorizacao = cabecalhos.get("Authorization", "")
    if autorizacao.lower().startswith("bearer "):
        return autorizacao[7:].strip()
    return (cabecalhos.get("X-Token") or "").strip()


def _token_confere(cabecalhos, esperado: str | None = None) -> bool:
    """Valida o token do pedido. Sem token configurado, libera (dev/rede local)."""
    esperado = LAGOA_TOKEN if esperado is None else esperado
    if not esperado:
        return True
    return hmac.compare_digest(_token_do_pedido(cabecalhos), esperado)


def _sessao_do_pedido(cabecalhos) -> str | None:
    """Extrai o token de sessão do cookie ``sessao`` (ou ``None``)."""
    bruto = cabecalhos.get("Cookie", "")
    if not bruto:
        return None
    try:
        cookies = SimpleCookie()
        cookies.load(bruto)
    except Exception:  # noqa: BLE001
        return None
    morsel = cookies.get(COOKIE_SESSAO)
    return morsel.value if morsel else None


# Prefixos de GET que expõem dados sensíveis (exigem sessão quando o login está ligado)
_PREFIXOS_SENSIVEIS = (
    "/api/orq/usuarios",
    "/api/orq/sessoes",
    "/api/orq/auditoria",
    "/api/orq/empresas",
    "/api/orq/papeis",
    "/api/orq/permissoes",
)


def _exige_sessao(metodo: str, rota: str) -> bool:
    """Diz se a rota exige um usuário autenticado (só quando o login está ligado)."""
    if not LAGOA_AUTH:
        return False
    if metodo == "POST":
        return True
    if metodo == "GET":
        return rota.startswith(_PREFIXOS_SENSIVEIS)
    return False


def _permissao_da_rota(metodo: str, rota: str) -> str | None:
    """Permissão exigida por uma rota administrativa (``None`` = só autenticação)."""
    if rota.startswith(("/api/orq/pacotes", "/api/orq/automacoes", "/api/orq/processos")):
        return "pacotes.instalar"
    if rota.startswith("/api/orq/jobs/") and rota.endswith("/cancelar"):
        return "jobs.cancelar"
    if rota.startswith(
        ("/api/orq/usuarios", "/api/orq/papeis", "/api/orq/permissoes", "/api/orq/empresas")
    ):
        return "usuarios.gerir"
    if rota.startswith("/api/orq/maquinas"):
        return "maquinas.gerir"
    if rota.startswith("/api/orq/auditoria"):
        return "auditoria.ver"
    if rota.startswith("/api/orq/assets"):
        return "assets.gerir"
    if rota.startswith("/api/orq/filas"):
        return "filas.gerir"
    if rota.startswith("/api/orq/triggers"):
        return "triggers.gerir"
    if rota.startswith("/api/orq/jobs"):
        return "jobs.disparar"
    return None


class ManipuladorControlRoom(ManipuladorPainel):
    """Handler do painel + rotas de orquestração."""

    server_version = "Lagoa/1.0"

    # Lagoa na raiz; monitor de trace sob /monitor/
    estaticos: list[tuple[str, Path]] = [("/monitor", PASTA_MONITOR), ("", PASTA_ESTATICO)]

    # ------------------------------------------------------------------
    # Sessão / autorização
    # ------------------------------------------------------------------
    def _sessao_atual(self) -> dict | None:
        return servico.validar_sessao(_sessao_do_pedido(self.headers))

    def _token_agente_ok(self) -> bool:
        """Aceita o token global (LAGOA_TOKEN) ou o token da máquina.

        Quando não há token global nem login obrigatório, as rotas de agente
        ficam abertas (dev/rede local). Com ``LAGOA_AUTH=true`` e sem
        token global, o agente precisa de um token de máquina.
        """
        enviado = _token_do_pedido(self.headers)
        if LAGOA_TOKEN:
            if _token_confere(self.headers):
                return True
        elif not LAGOA_AUTH and not enviado:
            return True
        return servico.validar_token_maquina(enviado) is not None

    def _autorizado(self, metodo: str, rota: str) -> bool:
        """Barra rotas de agente sem token e rotas administrativas sem sessão."""
        if _rota_de_agente(metodo, rota):
            if self._token_agente_ok():
                return True
            self._json(401, {"erro": "Token de agente ausente ou inválido."})
            return False
        if _exige_sessao(metodo, rota):
            sessao = self._sessao_atual()
            if sessao is None:
                self._json(401, {"erro": "Faça login para continuar."})
                return False
            permissao = _permissao_da_rota(metodo, rota)
            admin = bool(sessao["usuario"].get("admin"))
            if permissao and not admin and permissao not in sessao["permissoes"]:
                self._json(403, {"erro": f"Sem permissão ({permissao})."})
                return False
        return True

    def _definir_cookie(self, token: str) -> None:
        self._cabecalhos_extra = getattr(self, "_cabecalhos_extra", [])
        self._cabecalhos_extra.append(
            ("Set-Cookie", f"{COOKIE_SESSAO}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200")
        )

    def _limpar_cookie(self) -> None:
        self._cabecalhos_extra = getattr(self, "_cabecalhos_extra", [])
        self._cabecalhos_extra.append(
            ("Set-Cookie", f"{COOKIE_SESSAO}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")
        )

    def _responder(self, status: int, corpo: bytes, content_type: str) -> None:
        """Igual ao handler base, mas inclui os cabeçalhos extras (Set-Cookie)."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        for nome, valor in getattr(self, "_cabecalhos_extra", []):
            self.send_header(nome, valor)
        self._cabecalhos_extra = []
        self.end_headers()
        self.wfile.write(corpo)

    def _revisao(self) -> str:
        """Combina o estado da orquestração com o do monitor (para o SSE)."""
        from core.monitor.banco import revisao as revisao_monitor

        return f"{servico.revisao()}#{revisao_monitor()}"

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------
    def _atender_api(self, rota: str, query: dict[str, list[str]]) -> None:
        if rota.startswith("/api/orq/"):
            self._obter_orq(rota, query)
            return
        super()._atender_api(rota, query)

    @staticmethod
    def _primeiro(query: dict[str, list[str]] | None, chave: str, padrao=None):
        valores = (query or {}).get(chave)
        return valores[0] if valores else padrao

    @staticmethod
    def _inteiro(valor):
        try:
            return int(valor)
        except (TypeError, ValueError):
            return None

    def _contexto(self, query: dict[str, list[str]] | None) -> dict:
        """Ator/processo/IP/user-agent do pedido (para permissão e auditoria)."""
        processo_id = self._inteiro(self._primeiro(query, "processo_id"))
        return {
            "ator": self._primeiro(query, "ator") or self._primeiro(query, "maquina"),
            "processo_id": processo_id,
            "ip": self.client_address[0] if self.client_address else None,
            "user_agent": self.headers.get("User-Agent"),
        }

    def _obter_orq(self, rota: str, query: dict[str, list[str]] | None = None) -> None:
        if not self._autorizado("GET", rota):
            return
        if rota == "/api/orq/painel":
            self._json(200, servico.montar_painel())
        elif rota == "/api/orq/calendario":
            agora = datetime.now()
            ano = self._inteiro(self._primeiro(query, "ano")) or agora.year
            mes = self._inteiro(self._primeiro(query, "mes")) or agora.month
            try:
                self._json(200, servico.listar_calendario(ano, mes))
            except ValueError as erro:
                self._json(400, {"erro": str(erro)})
        elif rota == "/api/orq/eu":
            self._json(200, {"sessao": self._sessao_atual(), "auth": LAGOA_AUTH})
        elif rota == "/api/orq/eventos":
            self._servir_eventos()
        elif rota == "/api/orq/usuarios":
            self._json(200, {"usuarios": servico.listar_usuarios()})
        elif rota == "/api/orq/papeis":
            self._json(200, {"papeis": servico.listar_papeis(), "permissoes": servico.listar_permissoes()})
        elif rota == "/api/orq/empresas":
            self._json(200, {"empresas": servico.listar_empresas()})
        elif rota == "/api/orq/sessoes":
            self._json(200, {"sessoes": servico.listar_sessoes()})
        elif rota == "/api/orq/maquinas":
            self._json(200, {"maquinas": servico.listar_maquinas()})
        elif rota == "/api/orq/alertas":
            self._json(200, {"alertas": servico.listar_alertas()})
        elif rota == "/api/orq/jobs":
            self._json(200, {"jobs": servico.listar_jobs(limite=100)})
        elif rota.startswith("/api/orq/jobs/"):
            self._obter_job(rota)
        elif rota.startswith("/api/orq/processos/") and rota.endswith("/variaveis"):
            pedaco = rota[len("/api/orq/processos/"):-len("/variaveis")]
            if not pedaco.isdigit():
                self._json(400, {"erro": "Id de processo inválido."})
                return
            variaveis = servico.obter_variaveis_processo(int(pedaco))
            if variaveis is None:
                self._json(404, {"erro": "Processo não encontrado."})
            else:
                self._json(200, {"processo_id": int(pedaco), "variaveis": variaveis})
        elif rota == "/api/orq/assets":
            self._json(200, {"assets": servico.listar_assets(mascarar=True)})
        elif rota.startswith("/api/orq/assets/") and rota.endswith("/versoes"):
            self._obter_versoes_asset(rota)
        elif rota.startswith("/api/orq/assets/") and rota.endswith("/auditoria"):
            self._obter_auditoria_asset(rota)
        elif rota.startswith("/api/orq/assets/"):
            self._obter_asset(rota, query)
        elif rota.startswith("/api/orq/credenciais/"):
            self._obter_credencial(rota, query)
        elif rota == "/api/orq/auditoria/exportar":
            self._exportar_auditoria(query)
        elif rota == "/api/orq/auditoria":
            self._obter_auditoria(query)
        elif rota == "/api/orq/filas":
            self._json(200, {"filas": servico.listar_filas()})
        elif rota.startswith("/api/orq/filas/") and rota.endswith("/itens"):
            self._obter_itens_fila(rota)
        elif rota == "/api/orq/itens":
            self._json(200, {"itens": []})
        else:
            self._json(404, {"erro": "Rota de orquestração não encontrada."})

    def _exportar_auditoria(self, query: dict[str, list[str]] | None = None) -> None:
        csv_texto = servico.exportar_auditoria_csv(
            recurso=self._primeiro(query, "recurso"),
            ator=self._primeiro(query, "ator"),
        )
        corpo = csv_texto.encode("utf-8")
        self._cabecalhos_extra = getattr(self, "_cabecalhos_extra", [])
        self._cabecalhos_extra.append(
            ("Content-Disposition", 'attachment; filename="auditoria.csv"')
        )
        self._responder(200, corpo, "text/csv; charset=utf-8")

    def _obter_itens_fila(self, rota: str) -> None:
        partes = rota.strip("/").split("/")  # api / orq / filas / <id> / itens
        if len(partes) != 5 or not partes[3].isdigit():
            self._json(400, {"erro": "Id de fila inválido."})
            return
        fila = servico.obter_fila(int(partes[3])) or {}
        fila_id = fila.get("id")
        if fila_id is None:
            self._json(404, {"erro": "Fila não encontrada."})
            return
        fila["processos"] = servico.listar_processos_fila(fila_id)
        self._json(
            200,
            {
                "fila": fila,
                "itens": servico.listar_itens(fila_id),
                "processos": servico.listar_processos_fila(fila_id),
            },
        )

    def _obter_asset(self, rota: str, query: dict[str, list[str]] | None = None) -> None:
        nome = unquote(rota[len("/api/orq/assets/"):])
        asset = servico.obter_asset(nome, auditar=True, **self._contexto(query))
        if asset is None:
            self._json(404, {"erro": "Asset não encontrado."})
        else:
            self._json(200, asset)

    def _obter_credencial(self, rota: str, query: dict[str, list[str]] | None = None) -> None:
        nome = unquote(rota[len("/api/orq/credenciais/"):])
        credencial = servico.obter_credencial(nome, **self._contexto(query))
        if credencial is None:
            self._json(404, {"erro": "Credencial não encontrada."})
        else:
            self._json(200, {"credencial": credencial})

    def _obter_versoes_asset(self, rota: str) -> None:
        nome = unquote(rota[len("/api/orq/assets/"):-len("/versoes")])
        self._json(200, {"asset": nome, "versoes": servico.listar_versoes_asset(nome)})

    def _obter_auditoria_asset(self, rota: str) -> None:
        nome = unquote(rota[len("/api/orq/assets/"):-len("/auditoria")])
        self._json(
            200,
            {
                "recurso": nome,
                "auditoria": servico.listar_auditoria(limite=100, recurso=f"asset:{nome}"),
            },
        )

    def _obter_auditoria(self, query: dict[str, list[str]] | None = None) -> None:
        limite = self._inteiro(self._primeiro(query, "limite")) or 200
        self._json(
            200,
            {
                "auditoria": servico.listar_auditoria(
                    limite=min(limite, 1000),
                    recurso=self._primeiro(query, "recurso"),
                    ator=self._primeiro(query, "ator"),
                )
            },
        )

    def _obter_job(self, rota: str) -> None:
        pedaco = rota.rsplit("/", 1)[-1]
        if not pedaco.isdigit():
            self._json(400, {"erro": "Id de job inválido."})
            return
        job = servico.obter_job(int(pedaco))
        if job is None:
            self._json(404, {"erro": "Job não encontrado."})
        else:
            self._json(200, {"job": job})

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------
    def do_POST(self) -> None:  # noqa: N802
        parse = urlparse(self.path)
        if parse.path == "/api/orq/login":
            self._login(self._ler_corpo())
            return
        if parse.path == "/api/orq/logout":
            self._logout()
            return
        if parse.path == "/api/orq/pacotes":
            from urllib.parse import parse_qs

            senha = parse_qs(parse.query).get("senha", [None])[0]
            if not self._autorizado("POST", parse.path):
                return
            self._instalar_pacote(senha=senha)
            return
        if not parse.path.startswith("/api/orq/"):
            self._json(404, {"erro": "Rota não encontrada."})
            return
        if not self._autorizado("POST", parse.path):
            return
        self._atender_post_orq(parse.path, self._ler_corpo())

    def _login(self, corpo: dict) -> None:
        usuario = servico.autenticar(corpo.get("email"), corpo.get("senha"))
        if usuario is None:
            servico.registrar_auditoria(
                "login", recurso="sessao", ator=corpo.get("email"), resultado="negado",
                ip=self.client_address[0] if self.client_address else None,
            )
            self._json(401, {"erro": "E-mail ou senha inválidos."})
            return
        token = servico.criar_sessao(
            usuario,
            ip=self.client_address[0] if self.client_address else None,
            user_agent=self.headers.get("User-Agent"),
        )
        self._definir_cookie(token)
        servico.registrar_auditoria("login", recurso="sessao", ator=usuario.get("email"))
        self._json(
            200,
            {
                "usuario": usuario,
                "permissoes": servico.permissoes_do_usuario(usuario["id"]),
            },
        )

    def _logout(self) -> None:
        sessao = self._sessao_atual()
        servico.apagar_sessao(_sessao_do_pedido(self.headers))
        self._limpar_cookie()
        if sessao:
            servico.registrar_auditoria("logout", recurso="sessao", ator=sessao["usuario"].get("email"))
        self._json(200, {"ok": True})

    def _instalar_pacote(self, senha: str | None = None) -> None:
        from core.control_room import pacote

        bzip = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if not bzip:
            self._json(400, {"erro": "Nenhum arquivo recebido."})
            return
        try:
            resultado = pacote.instalar_zip(bzip, senha=senha)
            self._json(201, resultado)
        except (ValueError, KeyError) as erro:
            self._json(400, {"erro": str(erro)})
        except Exception as erro:  # nunca derrubar a conexão (o browser mostra "Failed to fetch")
            logger.warning(f"[lagoa] falha ao instalar pacote: {erro!r}")
            self._json(
                400,
                {"erro": "Não foi possível instalar o .zip. Confira se é um arquivo válido "
                         "com o manifesto rpa.json."},
            )

    def _instalar_pacote_git(self, corpo: dict, atualizar: bool = False) -> None:
        from core.control_room import pacote

        url = corpo.get("url") or corpo.get("git")
        ref = corpo.get("ref") or corpo.get("branch")
        if not url:
            self._json(400, {"erro": "Informe a URL do repositório (https://...)."})
            return
        try:
            if atualizar:
                resultado = pacote.atualizar_git(url, ref=ref)
            else:
                resultado = pacote.instalar_git(url, ref=ref)
            self._json(201, resultado)
        except ValueError as erro:
            self._json(400, {"erro": str(erro)})
        except Exception as erro:  # nunca derrubar a conexão
            logger.warning(f"[lagoa] falha ao instalar robô do Git: {erro!r}")
            self._json(
                400,
                {"erro": "Não foi possível instalar o robô do repositório. "
                         "Confira se a URL é pública e se contém um rpa.json."},
            )

    def _ler_corpo(self) -> dict:
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho == 0:
            return {}
        bruto = self.rfile.read(tamanho)
        try:
            return json.loads(bruto.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _atender_post_orq(self, rota: str, corpo: dict) -> None:
        partes = rota.strip("/").split("/")  # api / orq / ...

        # /api/orq/jobs
        if partes == ["api", "orq", "jobs"]:
            self._criar_job(corpo)
        # /api/orq/jobs/<id>/<acao>
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "jobs"]:
            self._acao_job(partes[3], partes[4], corpo)
        # /api/orq/agente/<nome>/<acao>
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "agente"]:
            self._acao_agente(partes[3], partes[4], corpo)
        # /api/orq/triggers  e  /api/orq/triggers/<id>/remover
        elif partes == ["api", "orq", "triggers"]:
            self._criar_trigger(corpo)
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "triggers"] and partes[4] == "remover":
            if not partes[3].isdigit():
                self._json(400, {"erro": "Id de agendamento inválido."})
                return
            servico.apagar_trigger(int(partes[3]))
            self._json(200, {"ok": True})
        # /api/orq/triggers/<id>/ativo  e  /executar
        elif (
            len(partes) == 5
            and partes[:3] == ["api", "orq", "triggers"]
            and partes[4] in ("ativo", "executar")
        ):
            self._acao_trigger(partes[3], partes[4], corpo)
        # /api/orq/processos/<id>/variaveis
        elif (
            len(partes) == 5
            and partes[:3] == ["api", "orq", "processos"]
            and partes[4] == "variaveis"
        ):
            self._salvar_variaveis_processo(partes[3], corpo)
        # /api/orq/processos/<id>/auto-atualizar
        elif (
            len(partes) == 5
            and partes[:3] == ["api", "orq", "processos"]
            and partes[4] == "auto-atualizar"
        ):
            self._acao_auto_atualizar(partes[3], corpo)
        # /api/orq/automacoes/verificar  (roda o polling agora)
        elif partes == ["api", "orq", "automacoes", "verificar"]:
            self._json(200, verificar_atualizacoes())
        # /api/orq/automacoes/<nome>/remover
        elif (
            len(partes) == 5
            and partes[:3] == ["api", "orq", "automacoes"]
            and partes[4] == "remover"
        ):
            from core.control_room import pacote

            try:
                self._json(200, pacote.remover(unquote(partes[3])))
            except ValueError as erro:
                self._json(400, {"erro": str(erro)})
        # /api/orq/automacoes/git  (instalar de repositório público)
        elif partes == ["api", "orq", "automacoes", "git"]:
            self._instalar_pacote_git(corpo, atualizar=False)
        # /api/orq/automacoes/git/atualizar  (clona de novo e substitui)
        elif partes == ["api", "orq", "automacoes", "git", "atualizar"]:
            self._instalar_pacote_git(corpo, atualizar=True)
        # /api/orq/assets  e  /api/orq/assets/<id>/remover
        elif partes == ["api", "orq", "assets"]:
            self._criar_asset(corpo)
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "assets"]:
            if partes[4] == "remover":
                if not partes[3].isdigit():
                    self._json(400, {"erro": "Id de asset inválido."})
                    return
                servico.apagar_asset(int(partes[3]), ator=corpo.get("ator"))
                self._json(200, {"ok": True})
            elif partes[4] == "rotacionar":
                self._rotacionar_asset(partes[3], corpo)
            elif partes[4] == "permissoes":
                self._conceder_permissao_asset(partes[3], corpo)
            else:
                self._json(404, {"erro": "Ação de asset desconhecida."})
        # /api/orq/permissoes/<id>/remover
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "permissoes"] and partes[4] == "remover":
            if not partes[3].isdigit():
                self._json(400, {"erro": "Id de permissão inválido."})
                return
            servico.remover_permissao(int(partes[3]), ator=corpo.get("ator"))
            self._json(200, {"ok": True})
        # /api/orq/filas
        elif partes == ["api", "orq", "filas"]:
            self._criar_fila(corpo)
        # /api/orq/filas/<id>/<acao>
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "filas"]:
            self._acao_fila(partes[3], partes[4], corpo)
        # /api/orq/itens/<id>/<acao>
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "itens"]:
            self._acao_item(partes[3], partes[4], corpo)
        # /api/orq/usuarios  e  /api/orq/usuarios/<id>/<acao>
        elif partes == ["api", "orq", "usuarios"]:
            self._criar_usuario(corpo)
        elif len(partes) == 5 and partes[:3] == ["api", "orq", "usuarios"]:
            self._acao_usuario(partes[3], partes[4], corpo)
        # /api/orq/papeis  e  /api/orq/papeis/<nome>/permissoes
        elif partes == ["api", "orq", "papeis"]:
            self._criar_papel(corpo)
        elif (
            len(partes) == 5
            and partes[:3] == ["api", "orq", "papeis"]
            and partes[4] == "permissoes"
        ):
            self._definir_permissoes_papel(unquote(partes[3]), corpo)
        # /api/orq/empresas
        elif partes == ["api", "orq", "empresas"]:
            self._criar_empresa(corpo)
        # /api/orq/maquinas  (cadastrar)
        elif partes == ["api", "orq", "maquinas"]:
            self._criar_maquina(corpo)
        # /api/orq/maquinas/<nome>/editar  e  /<nome>/remover
        elif (
            len(partes) == 5
            and partes[:3] == ["api", "orq", "maquinas"]
            and partes[4] in ("editar", "remover")
        ):
            self._acao_maquina(unquote(partes[3]), partes[4], corpo)
        # /api/orq/maquinas/<nome>/token[/revogar]
        elif (
            len(partes) == 5
            and partes[:3] == ["api", "orq", "maquinas"]
            and partes[4] == "token"
        ):
            self._emitir_token_maquina(unquote(partes[3]))
        elif (
            len(partes) == 6
            and partes[:3] == ["api", "orq", "maquinas"]
            and partes[4] == "token"
            and partes[5] == "revogar"
        ):
            servico.revogar_token_maquina(unquote(partes[3]))
            self._json(200, {"ok": True})
        # /api/orq/auditoria/expurgar
        elif len(partes) == 4 and partes[:3] == ["api", "orq", "auditoria"] and partes[3] == "expurgar":
            removidos = servico.expurgar_auditoria(self._inteiro(corpo.get("dias")))
            self._json(200, {"ok": True, "removidos": removidos})
        else:
            self._json(404, {"erro": "Rota de orquestração não encontrada."})

    def _criar_usuario(self, corpo: dict) -> None:
        nome = (corpo.get("nome") or "").strip()
        email = (corpo.get("email") or "").strip()
        senha = corpo.get("senha") or ""
        if not (nome and email and senha):
            self._json(400, {"erro": "Informe 'nome', 'email' e 'senha'."})
            return
        papeis = corpo.get("papeis") if isinstance(corpo.get("papeis"), list) else None
        usuario = servico.criar_usuario(
            nome,
            email,
            senha,
            empresa_id=self._inteiro(corpo.get("empresa_id")),
            papeis=papeis,
            admin=bool(corpo.get("admin")),
        )
        self._json(201, {"usuario": {k: v for k, v in usuario.items() if k != "senha_hash"}})

    def _acao_usuario(self, pedaco: str, acao: str, corpo: dict) -> None:
        if not pedaco.isdigit():
            self._json(400, {"erro": "Id de usuário inválido."})
            return
        usuario_id = int(pedaco)
        if acao == "papeis":
            papeis = corpo.get("papeis") if isinstance(corpo.get("papeis"), list) else []
            for atual in servico.papeis_do_usuario(usuario_id):
                servico.remover_papel(usuario_id, atual["nome"])
            for papel in papeis:
                servico.atribuir_papel(usuario_id, str(papel))
            self._json(200, {"ok": True, "id": usuario_id, "papeis": [str(p) for p in papeis]})
        elif acao == "ativo":
            with servico.conectar() as conexao:
                conexao.execute(
                    "UPDATE usuarios SET ativo = ? WHERE id = ?",
                    (int(bool(corpo.get("ativo", True))), usuario_id),
                )
            self._json(200, {"ok": True})
        else:
            self._json(404, {"erro": "Ação de usuário desconhecida."})

    def _criar_papel(self, corpo: dict) -> None:
        nome = (corpo.get("nome") or "").strip()
        if not nome:
            self._json(400, {"erro": "Informe 'nome' do papel."})
            return
        permissoes = corpo.get("permissoes") if isinstance(corpo.get("permissoes"), list) else None
        papel = servico.criar_papel(nome, corpo.get("descricao"), permissoes)
        self._json(201, {"papel": papel})

    def _definir_permissoes_papel(self, nome: str, corpo: dict) -> None:
        permissoes = corpo.get("permissoes")
        if not isinstance(permissoes, list):
            self._json(400, {"erro": "Envie 'permissoes' como lista."})
            return
        try:
            servico.definir_permissoes_papel(nome, [str(p) for p in permissoes])
        except ValueError as erro:
            self._json(404, {"erro": str(erro)})
            return
        self._json(200, {"ok": True, "papel": servico.obter_papel_por_nome(nome)})

    def _criar_empresa(self, corpo: dict) -> None:
        nome = (corpo.get("nome") or "").strip()
        if not nome:
            self._json(400, {"erro": "Informe 'nome' da empresa."})
            return
        empresa = servico.criar_empresa(nome, ativa=bool(corpo.get("ativa", True)))
        self._json(201, {"empresa": empresa})

    def _criar_maquina(self, corpo: dict) -> None:
        nome = (corpo.get("nome") or "").strip()
        if not nome:
            self._json(400, {"erro": "Informe 'nome' da máquina."})
            return
        try:
            maquina = servico.cadastrar_maquina(
                nome,
                tags=corpo.get("tags"),
                info=corpo.get("info"),
                ator=corpo.get("ator"),
            )
        except ValueError as erro:
            self._json(409, {"erro": str(erro)})
            return
        self._json(201, {"maquina": maquina})

    def _acao_maquina(self, nome: str, acao: str, corpo: dict) -> None:
        if acao == "editar":
            maquina = servico.atualizar_maquina(
                nome,
                tags=corpo.get("tags"),
                info=corpo.get("info"),
                ator=corpo.get("ator"),
            )
            if maquina is None:
                self._json(404, {"erro": "Máquina não encontrada."})
                return
            self._json(200, {"maquina": maquina})
        elif acao == "remover":
            if not servico.apagar_maquina(nome, ator=corpo.get("ator")):
                self._json(404, {"erro": "Máquina não encontrada."})
                return
            self._json(200, {"ok": True})
        else:
            self._json(404, {"erro": "Ação de máquina desconhecida."})

    def _emitir_token_maquina(self, nome: str) -> None:
        token = servico.emitir_token_maquina(nome)
        self._json(201, {"maquina": nome, "token": token})

    def _criar_fila(self, corpo: dict) -> None:
        nome = (corpo.get("nome") or "").strip()
        if not nome:
            self._json(400, {"erro": "Informe 'nome' da fila."})
            return
        processos = corpo.get("processos") if isinstance(corpo.get("processos"), list) else None
        fila = servico.criar_fila(
            nome,
            descricao=corpo.get("descricao"),
            processo_id=corpo.get("processo_id"),
            processos=processos,
        )
        if fila.get("processo_id") is None and corpo.get("processo_nome"):
            processo = servico.obter_processo_por_nome(corpo.get("processo_nome"))
            if processo is None:
                self._json(400, {"erro": f"Processo '{corpo.get('processo_nome')}' não existe."})
                return
            fila = servico.criar_fila(
                nome,
                descricao=corpo.get("descricao"),
                processo_id=processo["id"],
                processos=processos,
            )
        self._json(201, {"fila": fila})

    def _acao_fila(self, pedaco: str, acao: str, corpo: dict) -> None:
        if acao == "remover":
            if not pedaco.isdigit():
                self._json(400, {"erro": "Id de fila inválido."})
                return
            servico.apagar_fila(int(pedaco))
            self._json(200, {"ok": True})
        elif acao == "itens":
            if not pedaco.isdigit():
                self._json(400, {"erro": "Id de fila inválido."})
                return
            self._adicionar_itens(int(pedaco), corpo)
        elif acao == "proximo":
            self._proximo_item(unquote(pedaco), corpo)
        elif acao == "ativo":
            if not pedaco.isdigit():
                self._json(400, {"erro": "Id de fila inválido."})
                return
            fila = servico.definir_fila_ativa(int(pedaco), bool(corpo.get("ativo", True)))
            self._json(200, {"fila": fila})
        elif acao == "processos":
            if not pedaco.isdigit():
                self._json(400, {"erro": "Id de fila inválido."})
                return
            lista = corpo.get("processos") if isinstance(corpo.get("processos"), list) else []
            processos = servico.definir_processos_fila(int(pedaco), lista)
            self._json(200, {"ok": True, "processos": processos})
        else:
            self._json(404, {"erro": "Ação de fila desconhecida."})

    def _adicionar_itens(self, fila_id: int, corpo: dict) -> None:
        itens = corpo.get("itens")
        if not isinstance(itens, list):
            self._json(400, {"erro": "Envie 'itens' como lista de objetos."})
            return
        total = servico.adicionar_itens(
            fila_id,
            itens,
            referencia_campo=corpo.get("referencia_campo"),
            prioridade=corpo.get("prioridade") or 0,
        )
        self._json(201, {"ok": True, "adicionados": total})

    def _proximo_item(self, nome_fila: str, corpo: dict) -> None:
        maquina = (corpo.get("maquina") or "").strip()
        if not maquina:
            self._json(400, {"erro": "Informe 'maquina'."})
            return
        self._json(200, servico.reservar_item_e_job(nome_fila, maquina))

    def _acao_item(self, pedaco: str, acao: str, corpo: dict) -> None:
        if not pedaco.isdigit():
            self._json(400, {"erro": "Id de item inválido."})
            return
        item_id = int(pedaco)
        if acao == "resultado":
            item = servico.concluir_item(
                item_id,
                bool(corpo.get("sucesso")),
                mensagem=corpo.get("mensagem"),
            )
            self._json(200, {"item": item})
        elif acao == "abandonar":
            item = servico.abandonar_item(item_id, corpo.get("mensagem"))
            self._json(200, {"item": item})
        elif acao == "prioridade":
            item = servico.definir_prioridade_item(item_id, self._inteiro(corpo.get("prioridade")) or 0)
            if item is None:
                self._json(404, {"erro": "Item não encontrado."})
                return
            self._json(200, {"item": item})
        else:
            self._json(404, {"erro": "Ação de item desconhecida."})

    def _criar_trigger(self, corpo: dict) -> None:
        processo_id = corpo.get("processo_id")
        if not isinstance(processo_id, int):
            self._json(400, {"erro": "Informe 'processo_id' (inteiro)."})
            return
        try:
            trigger = servico.criar_trigger(
                processo_id,
                tipo=corpo.get("tipo", "intervalo"),
                intervalo_min=corpo.get("intervalo_min"),
                hora=corpo.get("hora"),
                maquina_id=corpo.get("maquina_id"),
                requisito_tag=corpo.get("requisito_tag"),
                expressao=corpo.get("expressao"),
                dias_semana=corpo.get("dias_semana"),
                incluir_fins=bool(corpo.get("incluir_fins", True)),
                incluir_feriados=bool(corpo.get("incluir_feriados", True)),
            )
        except ValueError as erro:
            self._json(400, {"erro": str(erro)})
            return
        self._json(201, {"trigger": trigger})

    def _acao_trigger(self, pedaco: str, acao: str, corpo: dict) -> None:
        if not pedaco.isdigit():
            self._json(400, {"erro": "Id de agendamento inválido."})
            return
        trigger_id = int(pedaco)
        if acao == "ativo":
            ativo = bool(corpo.get("ativo", True))
            trigger = servico.definir_trigger_ativo(trigger_id, ativo)
        else:  # executar
            trigger = servico.disparar_trigger(trigger_id)
        if trigger is None:
            self._json(404, {"erro": "Agendamento não encontrado."})
            return
        self._json(200, {"trigger": trigger})

    def _criar_asset(self, corpo: dict) -> None:
        nome = (corpo.get("nome") or "").strip()
        if not nome:
            self._json(400, {"erro": "Informe 'nome' do asset."})
            return
        asset = servico.criar_asset(
            nome,
            corpo.get("valor") or "",
            secreto=bool(corpo.get("secreto", True)),
            descricao=corpo.get("descricao"),
            tipo=corpo.get("tipo"),
            usuario=corpo.get("usuario"),
            pasta=corpo.get("pasta"),
            ator=corpo.get("ator"),
        )
        self._json(201, {"asset": {**asset, "valor": "••••••••" if asset.get("secreto") else asset.get("valor")}})

    def _rotacionar_asset(self, nome: str, corpo: dict) -> None:
        nome = unquote(nome)
        if "valor" not in corpo:
            self._json(400, {"erro": "Informe 'valor' (novo segredo)."})
            return
        asset = servico.rotacionar_asset(nome, corpo.get("valor") or "", ator=corpo.get("ator"))
        if asset is None:
            self._json(404, {"erro": "Asset não encontrado."})
            return
        self._json(200, {"asset": {**asset, "valor": "••••••••" if asset.get("secreto") else asset.get("valor")}})

    def _conceder_permissao_asset(self, nome: str, corpo: dict) -> None:
        nome = unquote(nome)
        permissao = servico.conceder_permissao(
            nome,
            processo_id=self._inteiro(corpo.get("processo_id")),
            pasta=corpo.get("pasta"),
            ator=corpo.get("ator"),
        )
        self._json(201, {"permissao": permissao})

    def _salvar_variaveis_processo(self, pedaco_id: str, corpo: dict) -> None:
        if not pedaco_id.isdigit():
            self._json(400, {"erro": "Id de processo inválido."})
            return
        try:
            variaveis = servico.definir_variaveis_processo(
                int(pedaco_id),
                corpo.get("variaveis") if "variaveis" in corpo else corpo.get("texto"),
                ator=corpo.get("ator"),
            )
        except ValueError as erro:
            self._json(400, {"erro": str(erro)})
            return
        if variaveis is None:
            self._json(404, {"erro": "Processo não encontrado."})
            return
        self._json(200, {"processo_id": int(pedaco_id), "variaveis": variaveis})

    def _acao_auto_atualizar(self, pedaco_id: str, corpo: dict) -> None:
        if not pedaco_id.isdigit():
            self._json(400, {"erro": "Id de processo inválido."})
            return
        ativo = corpo.get("ativo", True)
        if not isinstance(ativo, bool):
            self._json(400, {"erro": "Informe 'ativo' como verdadeiro/falso."})
            return
        if servico.obter_processo(int(pedaco_id)) is None:
            self._json(404, {"erro": "Processo não encontrado."})
            return
        servico.definir_auto_atualizar(
            int(pedaco_id), ativo, ator=corpo.get("ator") or "painel"
        )
        self._json(200, {"processo_id": int(pedaco_id), "auto_atualizar": ativo})

    def _criar_job(self, corpo: dict) -> None:
        processo_id = corpo.get("processo_id")
        maquina_id = corpo.get("maquina_id")
        if not isinstance(processo_id, int):
            self._json(400, {"erro": "Informe 'processo_id' (inteiro)."})
            return
        job = servico.criar_job(
            processo_id,
            maquina_id,
            requisito_tag=corpo.get("requisito_tag"),
            mensagem=corpo.get("mensagem"),
        )
        self._json(201, {"job": job})

    def _acao_job(self, pedaco_id: str, acao: str, corpo: dict) -> None:
        if not pedaco_id.isdigit():
            self._json(400, {"erro": "Id de job inválido."})
            return
        job_id = int(pedaco_id)

        if acao == "cancelar":
            self._json(200, {"job": servico.cancelar_job(job_id)})
        elif acao == "execucao":
            servico.anexar_execucao(job_id, int(corpo.get("execucao_id") or 0))
            self._json(200, {"ok": True})
        elif acao == "concluir":
            sucesso = bool(corpo.get("sucesso"))
            job = servico.concluir_job(job_id, sucesso, corpo.get("mensagem"))
            self._json(200, {"job": job})
        else:
            self._json(404, {"erro": "Ação de job desconhecida."})

    def _acao_agente(self, nome: str, acao: str, corpo: dict) -> None:
        if acao == "registrar":
            maquina = servico.registrar_maquina(
                nome, tags=corpo.get("tags"), ip=corpo.get("ip"), info=corpo.get("info")
            )
            self._json(200, {"maquina": maquina})
        elif acao == "proximo":
            job = servico.reservar_proximo_job(nome)
            self._json(200, {"job": job})
        else:
            self._json(404, {"erro": "Ação de agente desconhecida."})


def _iniciar_agendador() -> None:
    """Thread em segundo plano que dispara os triggers vencidos."""

    def laco() -> None:
        ciclos = 0
        while True:
            try:
                servico.verificar_triggers()
                ciclos += 1
                # A cada ~1h limpa sessões vencidas e expurga auditoria antiga
                if ciclos % max(1, int(3600 / max(1, INTERVALO_TRIGGERS))) == 0:
                    servico.limpar_sessoes_expiradas()
                    servico.expurgar_auditoria()
            except Exception as erro:  # noqa: BLE001
                logger.warning(f"[lagoa] erro ao verificar agendamentos: {erro}")
            time.sleep(INTERVALO_TRIGGERS)

    threading.Thread(target=laco, name="agendador-triggers", daemon=True).start()


def _ips_da_rede() -> list[str]:
    """Descobre o(s) IP(s) da máquina na rede local (para mostrar aos runners)."""
    ips: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonda:
            sonda.connect(("8.8.8.8", 80))
            ips.append(sonda.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


def iniciar_lagoa(
    host: str = HOST_LAGOA,
    porta: int = PORTA_LAGOA,
    abrir_navegador: bool = ABRIR_PAINEL,
    cert: str | None = None,
    chave: str | None = None,
) -> None:
    """Sobe a Lagoa (com o monitor em /monitor/) até receber Ctrl+C."""
    iniciar_banco_monitor()
    iniciar_banco_orq()
    servico.garantir_processos_exemplo()
    servico.garantir_admin_padrao()
    servico.limpar_sessoes_expiradas()
    _iniciar_agendador()
    if AUTO_ATUALIZAR:
        iniciar_atualizador()

    servidor = ThreadingHTTPServer((host, porta), ManipuladorControlRoom)
    esquema = "https" if _aplicar_tls(servidor, cert, chave) else "http"
    endereco = f"{esquema}://{host}:{porta}"

    logger.success(f"Lagoa disponível em {endereco}")
    logger.info(f"Painel de trace em {endereco}/monitor/")

    if host in ("0.0.0.0", "::"):
        for ip in _ips_da_rede():
            logger.info(f"Runners na rede: --lagoa {esquema}://{ip}:{porta}")

    logger.info("Pressione Ctrl+C para encerrar.")

    if abrir_navegador:
        webbrowser.open(endereco)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        logger.info("Encerrando a Lagoa...")
    finally:
        servidor.server_close()


# Compatibilidade: nome antigo da função de subida.
iniciar_control_room = iniciar_lagoa


def main() -> None:
    parser = argparse.ArgumentParser(description="Lagoa (orquestrador de robôs).")
    parser.add_argument(
        "--host",
        default=HOST_LAGOA,
        help="Endereço (default: 127.0.0.1; use 0.0.0.0 p/ a rede)",
    )
    parser.add_argument(
        "--porta", type=int, default=PORTA_LAGOA, help="Porta (default: 8765)"
    )
    parser.add_argument(
        "--sem-navegador", action="store_true", help="Não abrir o navegador automaticamente"
    )
    parser.add_argument("--cert", default=TLS_CERT, help="Certificado TLS (PEM) p/ HTTPS")
    parser.add_argument("--chave", default=TLS_CHAVE, help="Chave TLS (PEM) p/ HTTPS")
    opcoes = parser.parse_args()

    iniciar_lagoa(
        host=opcoes.host,
        porta=opcoes.porta,
        abrir_navegador=not opcoes.sem_navegador,
        cert=opcoes.cert or None,
        chave=opcoes.chave or None,
    )


if __name__ == "__main__":
    main()
