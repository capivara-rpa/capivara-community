"""Servidor local do painel de monitoramento (trace).

Sobe uma API JSON e serve o frontend (HTML/CSS/JS) usando apenas a
biblioteca padrão do Python — nada de frameworks para instalar.

    python -m core.monitor.servidor           # http://localhost:8765

Rotas:
    GET /                      → painel (index.html)
    GET /api/painel            → resumo + lista de execuções
    GET /api/execucoes/<id>    → execução + trace (passos)
    GET /api/ultimos           → últimos passos de todos os robôs

O mesmo ``ManipuladorPainel`` é reaproveitado pela Lagoa
(``core.control_room.servidor``), que adiciona as rotas de orquestração e
serve este painel sob o prefixo ``/monitor/``.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import ssl
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from loguru import logger

from core.monitor.banco import (
    STATUS_COR,
    STATUS_ROTULO,
    STATUS_VALIDOS,
    iniciar_banco,
    listar_execucoes,
    listar_passos,
    obter_execucao,
    resumo_status,
    revisao,
    ultimos_passos,
)
from settings.parametros import ABRIR_PAINEL, HOST_MONITOR, PORTA_MONITOR, TLS_CERT, TLS_CHAVE

PASTA_ESTATICO = Path(__file__).resolve().parent / "estatico"

_MIME_EXTRA = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
}


class ManipuladorPainel(BaseHTTPRequestHandler):
    """Atende as requisições do painel (API + arquivos estáticos)."""

    server_version = "MonitorRPA/1.0"

    # Lista de (prefixo, pasta). O prefixo "" é a raiz. Subclasses podem
    # montar vários aplicativos (ex.: Lagoa na raiz e monitor em /monitor/).
    estaticos: list[tuple[str, Path]] = [("", PASTA_ESTATICO)]

    # ------------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela stdlib)
        url = urlparse(self.path)

        if url.path.startswith("/api/"):
            self._atender_api(url.path, parse_qs(url.query))
        else:
            self._atender_estatico(url.path)

    # ------------------------------------------------------------------
    # API (sobrescreva/estenda em subclasses para novas rotas)
    # ------------------------------------------------------------------
    def _atender_api(self, rota: str, query: dict[str, list[str]]) -> None:
        if rota == "/api/painel":
            self._json(200, self._montar_painel())
        elif rota == "/api/eventos":
            self._servir_eventos()
        elif rota == "/api/ultimos":
            limite = _como_int(query.get("limite", ["20"])[0], 20)
            self._json(200, {"passos": ultimos_passos(limite)})
        elif rota.startswith("/api/execucoes/"):
            self._atender_execucao(rota)
        else:
            self._json(404, {"erro": "Rota de API não encontrada."})

    def _atender_execucao(self, rota: str) -> None:
        pedaco = rota.rsplit("/", 1)[-1]
        if not pedaco.isdigit():
            self._json(400, {"erro": "Id de execução inválido."})
            return

        execucao = obter_execucao(int(pedaco))
        if execucao is None:
            self._json(404, {"erro": "Execução não encontrada."})
            return

        self._json(200, {"execucao": execucao, "passos": listar_passos(execucao["id"])})

    def _montar_painel(self) -> dict:
        resumo = resumo_status()
        resumo["total"] = sum(resumo.values())
        return {
            "resumo": resumo,
            "execucoes": listar_execucoes(),
            "status_info": {
                status: {"rotulo": STATUS_ROTULO[status], "cor": STATUS_COR[status]}
                for status in STATUS_VALIDOS
            },
        }

    # ------------------------------------------------------------------
    # Push em tempo real (SSE) — sem dependências externas
    # ------------------------------------------------------------------
    def _revisao(self) -> str:
        """Assinatura do estado; subclasses (Lagoa) podem sobrescrever."""
        return revisao()

    def _servir_eventos(self) -> None:
        """Stream ``text/event-stream`` que avisa o painel quando algo muda."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        anterior = None
        try:
            while True:
                atual = self._revisao()
                if atual != anterior:
                    anterior = atual
                    dados = json.dumps({"rev": atual}).encode("utf-8")
                    self.wfile.write(b"data: " + dados + b"\n\n")
                else:
                    self.wfile.write(b": ping\n\n")  # keep-alive
                self.wfile.flush()
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    # ------------------------------------------------------------------
    # Arquivos estáticos (com suporte a múltiplos prefixos)
    # ------------------------------------------------------------------
    def _atender_estatico(self, rota: str) -> None:
        for prefixo, pasta in sorted(self.estaticos, key=lambda item: len(item[0]), reverse=True):
            if prefixo and not (rota == prefixo or rota.startswith(prefixo + "/")):
                continue

            # Redireciona "/monitor" -> "/monitor/" para os caminhos relativos funcionarem
            if prefixo and rota == prefixo:
                self._redirecionar(prefixo + "/")
                return

            relativo = rota[len(prefixo):].lstrip("/") or "index.html"
            if self._servir_arquivo(pasta, relativo):
                return

        self._json(404, {"erro": "Arquivo não encontrado."})

    def _servir_arquivo(self, pasta: Path, relativo: str) -> bool:
        raiz = pasta.resolve()
        arquivo = (raiz / relativo).resolve()

        if raiz != arquivo and raiz not in arquivo.parents:
            self._json(403, {"erro": "Acesso negado."})
            return True
        if not arquivo.is_file():
            return False

        tipo = _MIME_EXTRA.get(arquivo.suffix) or mimetypes.guess_type(arquivo.name)[0]
        self._responder(200, arquivo.read_bytes(), tipo or "application/octet-stream")
        return True

    # ------------------------------------------------------------------
    def _redirecionar(self, destino: str) -> None:
        self.send_response(301)
        self.send_header("Location", destino)
        self.end_headers()

    def _json(self, status: int, dados: dict) -> None:
        corpo = json.dumps(dados, ensure_ascii=False, default=str).encode("utf-8")
        self._responder(status, corpo, "application/json; charset=utf-8")

    def _responder(self, status: int, corpo: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, formato: str, *args) -> None:  # silencia o log padrão
        logger.trace(f"[web] {self.address_string()} {formato % args}")


def _como_int(valor: str, padrao: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _aplicar_tls(servidor: ThreadingHTTPServer, cert: str | None, chave: str | None) -> bool:
    """Ativa HTTPS no servidor quando certificado e chave (PEM) são informados."""
    if not cert or not chave:
        return False
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.load_cert_chain(cert, chave)
    servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
    return True


def iniciar_painel(
    host: str = HOST_MONITOR,
    porta: int = PORTA_MONITOR,
    abrir_navegador: bool = ABRIR_PAINEL,
    cert: str | None = None,
    chave: str | None = None,
) -> None:
    """Sobe o painel de trace e fica servindo até receber Ctrl+C."""
    iniciar_banco()
    servidor = ThreadingHTTPServer((host, porta), ManipuladorPainel)
    esquema = "https" if _aplicar_tls(servidor, cert, chave) else "http"
    endereco = f"{esquema}://{host}:{porta}"

    logger.success(f"Painel do monitor disponível em {endereco}")
    logger.info("Pressione Ctrl+C para encerrar.")

    if not listar_execucoes(limite=1):
        logger.warning(
            "Nenhuma execução no banco. Rode: python -m core.monitor.dados_exemplo"
        )

    if abrir_navegador:
        webbrowser.open(endereco)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        logger.info("Encerrando o painel...")
    finally:
        servidor.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel web de monitoramento dos robôs.")
    parser.add_argument(
        "--host",
        default=HOST_MONITOR,
        help="Endereço (default: 127.0.0.1; use 0.0.0.0 p/ a rede)",
    )
    parser.add_argument("--porta", type=int, default=PORTA_MONITOR, help="Porta (default: 8765)")
    parser.add_argument(
        "--sem-navegador", action="store_true", help="Não abrir o navegador automaticamente"
    )
    parser.add_argument("--cert", default=TLS_CERT, help="Certificado TLS (PEM) p/ HTTPS")
    parser.add_argument("--chave", default=TLS_CHAVE, help="Chave TLS (PEM) p/ HTTPS")
    opcoes = parser.parse_args()

    iniciar_painel(
        host=opcoes.host,
        porta=opcoes.porta,
        abrir_navegador=not opcoes.sem_navegador,
        cert=opcoes.cert or None,
        chave=opcoes.chave or None,
    )


if __name__ == "__main__":
    main()
