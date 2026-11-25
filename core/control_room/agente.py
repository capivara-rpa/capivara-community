"""Agente de execução (o "robot" que roda dentro de cada máquina).

Fica registrado na Lagoa, envia heartbeat, busca jobs direcionados à
sua máquina, executa o fluxo Python correspondente e devolve o resultado —
registrando o passo a passo no monitor (trace).

    python -m core.control_room.agente --maquina maquina-01
    python -m core.control_room.agente --maquina maquina-01 --tags "financeiro,sp"
    python -m core.control_room.agente --maquina maquina-01 --uma-vez   # testa 1 job
    python -m core.control_room.agente --maquina maquina-01 --fila clientes
    python -m core.control_room.agente --maquina maquina-01 --token <token-da-maquina>

Cada máquina pode ter o seu próprio token (emitido na aba Acessos da Lagoa
ou via ``POST /api/orq/maquinas/<nome>/token``). Sem ``--token`` o agente
usa ``LAGOA_TOKEN`` do ``.env``.

Cada máquina tem o seu próprio processo de agente. Para simular várias
máquinas, abra vários terminais com nomes diferentes.

Fluxos executados por um agente podem receber ``agente`` e ``item`` como
parâmetros opcionais (o agente injeta o que a função declarar)::

    def meu_fluxo(navegador=None, agente=None, item=None):
        usuario = agente.asset("portal_usuario")   # do vault
        dados = item.get("dados")                   # item da fila
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import requests
from loguru import logger

# Garante que a raiz do projeto esteja no caminho de import
RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from core.control_room import ambiente  # noqa: E402
from core.logger import configurar_logger  # noqa: E402
from core.monitor import Monitor  # noqa: E402
from core.robo import Robo  # noqa: E402
from settings.parametros import LAGOA_TOKEN, LAGOA_URL, PASTA_ROBOS  # noqa: E402


def resolver_fluxo(caminho: str) -> Callable:
    """Resolve ``"pacote.modulo:funcao"`` para a função real."""
    modulo, separador, atributo = caminho.partition(":")
    if not separador or not atributo:
        raise ValueError(f"Fluxo inválido: {caminho!r}. Esperado 'modulo:funcao'.")
    return getattr(importlib.import_module(modulo), atributo)


class Agente:
    """Agente que executa jobs de uma máquina."""

    def __init__(
        self,
        control_room: str,
        maquina: str,
        tags: str | None = None,
        intervalo: float = 3.0,
        capturar_logs: bool = True,
        fila: str | None = None,
        token: str | None = None,
    ) -> None:
        self.base = control_room.rstrip("/")
        self.maquina = maquina
        self.tags = tags
        self.intervalo = intervalo
        self.capturar_logs = capturar_logs
        self.fila = fila
        self.token = token if token is not None else LAGOA_TOKEN

    # ------------------------------------------------------------------
    def _cabecalhos(self) -> dict[str, str]:
        """Cabeçalhos extras (token do agente, quando configurado)."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _post(self, rota: str, dados: dict | None = None) -> dict:
        resposta = requests.post(
            f"{self.base}{rota}", json=dados or {}, timeout=30, headers=self._cabecalhos()
        )
        resposta.raise_for_status()
        return resposta.json()

    def _get(self, rota: str, params: dict | None = None) -> dict:
        resposta = requests.get(
            f"{self.base}{rota}", timeout=30, headers=self._cabecalhos(), params=params
        )
        resposta.raise_for_status()
        return resposta.json()

    def asset(self, nome: str) -> str | None:
        """Busca um asset (credencial/variável) na Lagoa.

        Uso dentro de um fluxo::

            usuario = agente.asset("portal_usuario")
            senha = agente.asset("portal_senha")
        """
        dados = self._get(f"/api/orq/assets/{nome}", params={"ator": self.maquina})
        return dados.get("valor")

    def credencial(self, nome: str, processo_id: int | None = None) -> dict | None:
        """Busca uma credencial completa (``{usuario, senha, ...}``) na Lagoa.

        Uso dentro de um fluxo::

            cred = agente.credencial("portal")
            usuario, senha = cred["usuario"], cred["senha"]
        """
        dados = self._get(
            f"/api/orq/credenciais/{nome}",
            params={"ator": self.maquina, "processo_id": processo_id},
        )
        return dados.get("credencial")

    def item_atual(self) -> dict | None:
        """Devolve o item da fila sendo processado neste ciclo (ou None).

        Dentro de um fluxo que consome filas, use::

            item = agente.item_atual()
        """
        return getattr(self, "_item_atual", None)

    def cancelado(self) -> bool:
        """Diz se o job em execução foi cancelado na Lagoa.

        Fluxos longos podem checar periodicamente para encerrar mais cedo::

            for linha in linhas:
                if agente and agente.cancelado():
                    logger.warning("Job cancelado — encerrando")
                    return False
                processar(linha)

        (A checagem é uma consulta HTTP; use com moderação.)
        """
        job = getattr(self, "_job_atual", None)
        if not job:
            return False
        try:
            dados = self._get(f"/api/orq/jobs/{job['id']}")
        except requests.RequestException:
            return False
        return (dados.get("job") or {}).get("status") == "cancelado"

    def registrar(self) -> None:
        """Registra a máquina na Lagoa."""
        info = f"Python {sys.version.split()[0]}"
        self._post(
            f"/api/orq/agente/{self.maquina}/registrar",
            {"tags": self.tags, "ip": self._ip, "info": info},
        )
        logger.success(f"Agente registrado como '{self.maquina}' (tag: {self.tags or '-'})")

    @property
    def _ip(self) -> str:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"

    # ------------------------------------------------------------------
    def ciclo(self) -> bool:
        """Busca, executa e reporta um job. Retorna True se executou algum."""
        if self.fila:
            return self.ciclo_fila()

        job = self._post(f"/api/orq/agente/{self.maquina}/proximo").get("job")
        if not job:
            return False

        logger.info(f"Job #{job['id']} recebido: {job['processo_nome']}")
        execucao_id, sucesso, mensagem = self.executar(job)

        self._post(f"/api/orq/jobs/{job['id']}/execucao", {"execucao_id": execucao_id})
        self._post(
            f"/api/orq/jobs/{job['id']}/concluir",
            {"sucesso": sucesso, "mensagem": mensagem},
        )
        return True

    def ciclo_fila(self) -> bool:
        """Consome o próximo item de uma fila como um job (estilo filas de RPA)."""
        resposta = self._post(
            f"/api/orq/filas/{quote(self.fila)}/proximo", {"maquina": self.maquina}
        )
        item = resposta.get("item")
        if not item:
            return False

        self._item_atual = item
        try:
            job = resposta.get("job")
            if not job:
                logger.warning(
                    f"A fila '{self.fila}' não tem processo executor; abandonando item #{item['id']}"
                )
                self._post(
                    f"/api/orq/itens/{item['id']}/abandonar",
                    {"mensagem": "fila sem processo executor"},
                )
                return True

            logger.info(
                f"Item #{item['id']} da fila '{self.fila}' → job #{job['id']}"
                + (f" (ref: {item.get('referencia')})" if item.get("referencia") else "")
            )
            execucao_id, sucesso, mensagem = self.executar(job, item=item)

            self._post(f"/api/orq/jobs/{job['id']}/execucao", {"execucao_id": execucao_id})
            self._post(
                f"/api/orq/jobs/{job['id']}/concluir",
                {"sucesso": sucesso, "mensagem": mensagem},
            )
            self._post(
                f"/api/orq/itens/{item['id']}/resultado",
                {"sucesso": sucesso, "mensagem": mensagem},
            )
            return True
        finally:
            self._item_atual = None

    def executar(self, job: dict, item: dict | None = None) -> tuple[int, bool, str]:
        """Executa o fluxo do job e devolve (execucao_id, sucesso, mensagem).

        O fluxo recebe **apenas** os parâmetros que declarar. Além do
        ``navegador`` (automático), ele pode receber:
        - ``agente``: para ``agente.asset(...)`` e ``agente.item_atual()``;
        - ``item``: o item da fila (dicionário) que está sendo processado.

        Se o robô tiver um ``requirements.txt`` próprio, ele roda num ``.venv``
        isolado (criado/instalado na hora); senão, roda no ambiente do agente.
        """
        self._job_atual = job
        try:
            return self._executar_fluxo(job, item)
        finally:
            self._job_atual = None

    def _ambiente_do_robo(self, nome: str) -> Path | None:
        """Devolve o interpretador do ``.venv`` do robô (ou None se dispensa)."""
        pasta = Path(PASTA_ROBOS) / nome
        if not pasta.is_dir():
            return None
        return ambiente.garantir_ambiente(nome, pasta)

    def _pythonpath(self) -> str:
        """PYTHONPATH do subprocesso: raiz do projeto + site-packages do agente."""
        caminhos = [str(RAIZ_PROJETO)]
        for caminho in sys.path:
            if not caminho or caminho in caminhos:
                continue
            if "site-packages" in caminho or "dist-packages" in caminho:
                caminhos.append(caminho)
        return os.pathsep.join(caminhos)

    @staticmethod
    def _variaveis_do_job(job: dict) -> dict[str, str]:
        """Variáveis de ambiente configuradas para a automação do job."""
        bruto = job.get("processo_variaveis")
        if not bruto:
            return {}
        try:
            dados = json.loads(bruto) if isinstance(bruto, str) else bruto
        except (TypeError, ValueError):
            logger.warning(f"[lagoa] variáveis inválidas no job #{job.get('id')}; ignorando")
            return {}
        if not isinstance(dados, dict):
            return {}
        return {
            str(chave): "" if valor is None else str(valor)
            for chave, valor in dados.items()
        }

    @contextmanager
    def _ambiente_com_variaveis(self, variaveis: dict[str, str]):
        """Aplica variáveis no processo atual e restaura o ambiente ao sair."""
        anteriores: dict[str, str | None] = {}
        try:
            for chave, valor in variaveis.items():
                anteriores[chave] = os.environ.get(chave)
                os.environ[chave] = valor
            yield
        finally:
            for chave, valor in anteriores.items():
                if valor is None:
                    os.environ.pop(chave, None)
                else:
                    os.environ[chave] = valor

    def _rodar_no_venv(
        self,
        job: dict,
        python_venv: Path,
        item: dict | None,
        variaveis: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """Executa o robô num subprocesso usando o ``.venv`` dele."""
        nome = job["processo_nome"]
        variaveis = variaveis or {}
        config = {
            "fluxo": job["fluxo"],
            "nome": nome,
            "usa_navegador": bool(job.get("usa_navegador")),
            "item": item,
            "job_id": job.get("id"),
            "control_room": self.base,
            "token": self.token,
            "maquina": self.maquina,
        }
        amb = os.environ.copy()
        amb.update(variaveis)
        amb["PYTHONPATH"] = self._pythonpath()
        amb["PYTHONUNBUFFERED"] = "1"

        with tempfile.TemporaryDirectory(prefix="rpa-robo-") as tmp:
            config_path = Path(tmp) / "config.json"
            resultado_path = Path(tmp) / "resultado.json"
            config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
            logger.info(f"[ambiente] executando no .venv: {python_venv}")
            processo = subprocess.Popen(
                [
                    str(python_venv),
                    "-m",
                    "core.control_room.executar_robo",
                    str(config_path),
                    str(resultado_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=amb,
                cwd=str(RAIZ_PROJETO),
            )
            if processo.stdout is not None:
                for linha in processo.stdout:
                    texto = linha.rstrip("\n")
                    if texto:
                        logger.info(texto)
            codigo = processo.wait()

            if resultado_path.is_file():
                dados = json.loads(resultado_path.read_text(encoding="utf-8"))
                return bool(dados.get("sucesso")), str(dados.get("mensagem") or "")
            return False, f"O robô terminou sem resultado (código {codigo})."

    def _executar_fluxo(self, job: dict, item: dict | None) -> tuple[int, bool, str]:
        nome = job["processo_nome"]

        robo = Robo(nome=nome)
        monitor = Monitor(nome, mensagem=f"job #{job['id']}", capturar_logs=self.capturar_logs)
        execucao_id = monitor.execucao_id
        monitor.capturar_logs()

        sucesso = False
        mensagem = ""
        variaveis = self._variaveis_do_job(job)
        if variaveis:
            logger.info(
                f"[ambiente] {len(variaveis)} variável(is) de ambiente aplicada(s) ao job #{job['id']}"
            )
        try:
            python_venv = self._ambiente_do_robo(nome)
            if python_venv is not None:
                sucesso, mensagem = self._rodar_no_venv(job, python_venv, item, variaveis)
            else:
                funcao = resolver_fluxo(job["fluxo"])
                if job.get("usa_navegador"):
                    robo.iniciar()
                with self._ambiente_com_variaveis(variaveis):
                    sucesso = robo.executar_fluxo(nome, funcao, agente=self, item=item)
        except Exception as erro:  # noqa: BLE001
            mensagem = f"Erro no agente: {erro}"
            logger.error(mensagem)
        finally:
            robo.finalizar()
            monitor.parar_captura()

        if sucesso:
            mensagem = mensagem or "Executado com sucesso"
            monitor.finalizar(mensagem)
        else:
            mensagem = mensagem or "Fluxo retornou falha"
            monitor.falha(mensagem)

        logger.success(f"Job #{job['id']} {'concluído' if sucesso else 'falhou'}")
        return execucao_id, sucesso, mensagem

    # ------------------------------------------------------------------
    def rodar(self, uma_vez: bool = False) -> None:
        """Loop principal do agente."""
        self._registrar_com_retry()
        logger.info(f"Aguardando jobs para '{self.maquina}'... (Ctrl+C para sair)")
        while True:
            try:
                executou = self.ciclo()
            except requests.RequestException as erro:
                logger.warning(f"Lagoa indisponível ({erro}). Tentando de novo...")
                executou = False

            if uma_vez:
                return
            if not executou:
                time.sleep(self.intervalo)

    def _registrar_com_retry(self) -> None:
        """Registra a máquina; insiste se a Lagoa estiver fora do ar.

        Um erro 401 (token ausente/inválido) é definitivo: avisa e encerra.
        """
        while True:
            try:
                self.registrar()
                return
            except requests.HTTPError as erro:
                if erro.response is not None and erro.response.status_code == 401:
                    logger.error(
                        "Lagoa recusou o agente (401). Confira o token "
                        "(--token ou LAGOA_TOKEN no .env)."
                    )
                    raise
                logger.warning(f"Falha ao registrar ({erro}). Tentando de novo...")
            except requests.RequestException as erro:
                logger.warning(f"Lagoa indisponível ({erro}). Tentando de novo...")
            time.sleep(self.intervalo)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente de execução de robôs.")
    parser.add_argument(
        "--lagoa",
        "--control-room",
        dest="control_room",
        metavar="URL",
        default=LAGOA_URL,
        help="URL da Lagoa",
    )
    parser.add_argument("--maquina", default=socket.gethostname(), help="Nome desta máquina")
    parser.add_argument("--tags", default=None, help="Tags separadas por vírgula")
    parser.add_argument("--intervalo", type=float, default=3.0, help="Segundos entre consultas")
    parser.add_argument("--uma-vez", action="store_true", help="Executa no máximo 1 job e sai")
    parser.add_argument("--sem-captura", action="store_true", help="Não capturar logs no trace")
    parser.add_argument(
        "--fila",
        default=None,
        help="Consome itens de uma fila (o job é criado pelo processo executor da fila)",
    )
    parser.add_argument(
        "--token",
        default=LAGOA_TOKEN,
        help="Token do agente (Authorization: Bearer). Default: LAGOA_TOKEN do .env",
    )
    opcoes = parser.parse_args()

    configurar_logger(nome_processo=f"agente-{opcoes.maquina}")
    agente = Agente(
        control_room=opcoes.control_room,
        maquina=opcoes.maquina,
        tags=opcoes.tags,
        intervalo=opcoes.intervalo,
        capturar_logs=not opcoes.sem_captura,
        fila=opcoes.fila,
        token=opcoes.token,
    )
    try:
        agente.rodar(uma_vez=opcoes.uma_vez)
    except KeyboardInterrupt:
        logger.info("Agente encerrado.")
    except requests.HTTPError as erro:
        logger.error(f"Agente encerrado por erro HTTP: {erro}")
        sys.exit(1)


if __name__ == "__main__":
    main()
