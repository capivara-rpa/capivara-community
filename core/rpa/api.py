"""Cliente HTTP simples (requests) com logs coloridos e retry automático.

Uso rápido::

    from core.rpa.api import api_get, api_post

    resposta = api_get("https://api.exemplo.com/usuarios")
    if resposta.status_code == 200:
        dados = resposta.json()
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests
from loguru import logger

from core.tratador import ErroRPA, tentar_novamente
from settings.parametros import API_BASE_URL, API_TOKEN


class ClienteAPI:
    """Cliente HTTP reutilizável dentro dos robôs.

    Exemplo::

        api = ClienteAPI(base_url="https://api.exemplo.com", token="...")
        api.api_get("/usuarios")
        api.api_post("/pedidos", json={...})
    """

    def __init__(
        self,
        base_url: str = "",
        token: str | None = None,
        headers: dict[str, str] | None = None,
        tempo_timeout: int = 30,
        verificar_ssl: bool = True,
    ) -> None:
        self.base_url = (base_url or API_BASE_URL).rstrip("/")
        self.sessao = requests.Session()
        self.sessao.headers.update({"User-Agent": "Capivara/1.0"})
        if headers:
            self.sessao.headers.update(headers)
        if token:
            self.sessao.headers.update({"Authorization": f"Bearer {token}"})
        elif API_TOKEN:
            self.sessao.headers.update({"Authorization": f"Bearer {API_TOKEN}"})
        self.tempo_timeout = tempo_timeout
        self.verificar_ssl = verificar_ssl

    # --------------------------------------------------------------
    @tentar_novamente(vezes=3, espera=1.5, excecoes=(requests.exceptions.RequestException,))
    def _requisitar(self, metodo: str, caminho: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/{caminho.lstrip('/')}" if caminho else self.base_url
        kwargs.setdefault("timeout", self.tempo_timeout)
        kwargs.setdefault("verify", self.verificar_ssl)

        inicio = time.perf_counter()
        resposta = self.sessao.request(metodo.upper(), url, **kwargs)
        duracao = time.perf_counter() - inicio

        if resposta.ok:
            logger.success(f"{metodo.upper()} {url} -> {resposta.status_code} ({duracao:.2f}s)")
        else:
            logger.error(f"{metodo.upper()} {url} -> {resposta.status_code} ({duracao:.2f}s)")

        return resposta

    def api_get(self, caminho: str = "", params: dict[str, Any] | None = None, **kwargs) -> requests.Response:
        """Faz uma requisição GET."""
        return self._requisitar("GET", caminho, params=params, **kwargs)

    def api_post(self, caminho: str = "", json: dict[str, Any] | None = None, dados: dict[str, Any] | None = None, **kwargs) -> requests.Response:
        """Faz uma requisição POST."""
        return self._requisitar("POST", caminho, json=json, data=dados, **kwargs)

    def api_put(self, caminho: str = "", json: dict[str, Any] | None = None, **kwargs) -> requests.Response:
        """Faz uma requisição PUT."""
        return self._requisitar("PUT", caminho, json=json, **kwargs)

    def api_delete(self, caminho: str = "", **kwargs) -> requests.Response:
        """Faz uma requisição DELETE."""
        return self._requisitar("DELETE", caminho, **kwargs)

    def api_patch(self, caminho: str = "", json: dict[str, Any] | None = None, **kwargs) -> requests.Response:
        """Faz uma requisição PATCH."""
        return self._requisitar("PATCH", caminho, json=json, **kwargs)

    def api_head(self, caminho: str = "", **kwargs) -> requests.Response:
        """Faz uma requisição HEAD (útil para checar existência/tamanho)."""
        return self._requisitar("HEAD", caminho, **kwargs)

    def api_upload(
        self,
        caminho: str,
        arquivo: str | Path,
        campo: str = "arquivo",
        dados: dict[str, Any] | None = None,
        **kwargs,
    ) -> requests.Response:
        """Envia um arquivo via multipart/form-data (POST)."""
        arquivo = Path(arquivo)
        if not arquivo.is_file():
            raise ErroRPA(f"Arquivo não encontrado para upload: {arquivo}")
        with arquivo.open("rb") as aberto:
            arquivos = {campo: (arquivo.name, aberto)}
            return self._requisitar("POST", caminho, files=arquivos, data=dados, **kwargs)

    def api_download(
        self,
        caminho: str,
        destino: str | Path,
        **kwargs,
    ) -> Path:
        """Baixa o conteúdo de uma URL/rota para um arquivo local."""
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        resposta = self._requisitar("GET", caminho, stream=True, **kwargs)
        try:
            resposta.raise_for_status()
        except requests.RequestException as erro:
            raise ErroRPA(f"Falha ao baixar {caminho}: {erro}") from erro
        with destino.open("wb") as arquivo:
            for bloco in resposta.iter_content(chunk_size=8192):
                if bloco:
                    arquivo.write(bloco)
        logger.success(f"Download concluído: {destino}")
        return destino


# ----------------------------------------------------------------------
# Padrão da biblioteca padrão: instância de uso simples
# ----------------------------------------------------------------------
def _cliente_padrao() -> ClienteAPI:
    return ClienteAPI()


def api_get(caminho: str = "", params: dict[str, Any] | None = None, **kwargs) -> requests.Response:
    """Requisição GET com o cliente padrão (usa API_BASE_URL do .env)."""
    return _cliente_padrao().api_get(caminho, params=params, **kwargs)


def api_post(caminho: str = "", json: dict[str, Any] | None = None, dados: dict[str, Any] | None = None, **kwargs) -> requests.Response:
    """Requisição POST com o cliente padrão (usa API_BASE_URL do .env)."""
    return _cliente_padrao().api_post(caminho, json=json, dados=dados, **kwargs)


def api_put(caminho: str = "", json: dict[str, Any] | None = None, **kwargs) -> requests.Response:
    """Requisição PUT com o cliente padrão (usa API_BASE_URL do .env)."""
    return _cliente_padrao().api_put(caminho, json=json, **kwargs)


def api_delete(caminho: str = "", **kwargs) -> requests.Response:
    """Requisição DELETE com o cliente padrão (usa API_BASE_URL do .env)."""
    return _cliente_padrao().api_delete(caminho, **kwargs)


def api_patch(caminho: str = "", json: dict[str, Any] | None = None, **kwargs) -> requests.Response:
    """Requisição PATCH com o cliente padrão (usa API_BASE_URL do .env)."""
    return _cliente_padrao().api_patch(caminho, json=json, **kwargs)


def api_upload(
    caminho: str,
    arquivo: str | Path,
    campo: str = "arquivo",
    dados: dict[str, Any] | None = None,
    **kwargs,
) -> requests.Response:
    """Upload multipart com o cliente padrão (usa API_BASE_URL do .env)."""
    return _cliente_padrao().api_upload(caminho, arquivo, campo=campo, dados=dados, **kwargs)


def api_download(caminho: str, destino: str | Path, **kwargs) -> Path:
    """Download com o cliente padrão (usa API_BASE_URL do .env)."""
    return _cliente_padrao().api_download(caminho, destino, **kwargs)