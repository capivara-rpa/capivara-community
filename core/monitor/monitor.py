"""Classe :class:`Monitor` — registra a execução do robô em tempo real.

É o caminho fácil para o robô "aparecer" no painel: cria a execução, grava
cada passo e atualiza o status. Os métodos devolvem o próprio objeto, então
dá para encadear::

    from core.monitor import Monitor

    monitor = Monitor("robo_folha")
    monitor.passo("Abrindo o portal do RH")
    monitor.passo("Fazendo login", detalhe="usuário: financeiro")
    monitor.finalizar("Folha enviada com sucesso")

Se um fluxo falhar, o status certo é registrado automaticamente::

    monitor.erro_negocio("CNPJ não encontrado na base")
"""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger as _loguru

from core.monitor.banco import (
    STATUS_ERRO_CRITICO,
    STATUS_ERRO_NEGOCIO,
    STATUS_ERRO_SISTEMICO,
    STATUS_FALHA,
    STATUS_FINALIZADO,
    STATUS_PROCESSANDO,
    agora_iso,
    atualizar_status,
    iniciar_banco,
    iniciar_execucao,
    registrar_passo,
)


class Monitor:
    """Acompanha uma execução de robô no banco do monitor.

    Use como *context manager* com ``capturar_logs=True`` para transformar
    automaticamente cada log (``logger.info``, ``logger.success``...) da
    execução num passo do trace::

        with Monitor("robo_folha", capturar_logs=True) as monitor:
            logger.info("Abrindo o portal")
            ...
    """

    def __init__(
        self,
        robo: str,
        mensagem: str | None = None,
        relogio: Callable[[], str] | None = None,
        capturar_logs: bool = False,
    ) -> None:
        self.robo = robo
        self._relogio = relogio or agora_iso
        self._capturar_logs = capturar_logs
        self._sink_id: int | None = None
        iniciar_banco()
        self.execucao_id = iniciar_execucao(robo, mensagem=mensagem, quando=self._relogio())

    # ------------------------------------------------------------------
    # Context manager / captura automática de logs
    # ------------------------------------------------------------------
    def __enter__(self) -> Monitor:
        if self._capturar_logs:
            self.capturar_logs()
        return self

    def __exit__(self, tipo_erro, erro, traceback) -> bool:
        if tipo_erro is not None:
            self.erro_critico(f"{tipo_erro.__name__}: {erro}")
        self.parar_captura()
        return False

    def capturar_logs(self) -> Monitor:
        """Passa a gravar cada log INFO+ desta execução como um passo do trace."""
        if self._sink_id is not None:
            return self

        def _sink(mensagem) -> None:
            registro = mensagem.record
            if registro["name"].startswith("core.monitor"):
                return
            self.passo(registro["message"], nivel=registro["level"].name)

        self._sink_id = _loguru.add(
            _sink,
            level="INFO",
            format="{message}",
            filter=lambda registro: not registro["name"].startswith("core.monitor"),
            enqueue=False,
        )
        return self

    def parar_captura(self) -> None:
        """Remove o sink de captura de logs, se estiver ativo."""
        if self._sink_id is not None:
            _loguru.remove(self._sink_id)
            self._sink_id = None

    # ------------------------------------------------------------------
    def passo(
        self,
        descricao: str,
        detalhe: str | None = None,
        nivel: str = "INFO",
        quando: str | None = None,
    ) -> Monitor:
        """Registra um passo do robô (marcando a execução como ``processando``)."""
        registrar_passo(
            self.execucao_id,
            descricao,
            nivel=nivel,
            status=STATUS_PROCESSANDO,
            detalhe=detalhe,
            quando=quando or self._relogio(),
        )
        return self

    def sucesso(self, descricao: str, detalhe: str | None = None) -> Monitor:
        """Registra um passo que deu certo (nível SUCCESS)."""
        return self.passo(descricao, detalhe=detalhe, nivel="SUCCESS")

    def aviso(self, descricao: str, detalhe: str | None = None) -> Monitor:
        """Registra um passo de atenção (nível WARNING)."""
        return self.passo(descricao, detalhe=detalhe, nivel="WARNING")

    # ------------------------------------------------------------------
    # Encerramentos (mudam o status final da execução)
    # ------------------------------------------------------------------
    def _encerrar(self, status: str, mensagem: str | None) -> Monitor:
        if mensagem:
            registrar_passo(
                self.execucao_id,
                mensagem,
                nivel="CRITICAL" if status in (STATUS_ERRO_CRITICO, STATUS_FALHA) else "INFO",
                status=status,
                quando=self._relogio(),
            )
        atualizar_status(self.execucao_id, status, mensagem=mensagem, quando=self._relogio())
        return self

    def finalizar(self, mensagem: str | None = None) -> Monitor:
        """Marca a execução como finalizada com sucesso."""
        return self._encerrar(STATUS_FINALIZADO, mensagem)

    def falha(self, mensagem: str | None = None) -> Monitor:
        """Marca a execução como falha (o fluxo retornou erro sem exceção)."""
        return self._encerrar(STATUS_FALHA, mensagem)

    def erro_negocio(self, mensagem: str | None = None) -> Monitor:
        """Marca um erro de negócio (regra esperada, ex.: dado inválido)."""
        return self._encerrar(STATUS_ERRO_NEGOCIO, mensagem)

    def erro_sistemico(self, mensagem: str | None = None) -> Monitor:
        """Marca um erro sistêmico (integração/ambiente fora do ar, etc.)."""
        return self._encerrar(STATUS_ERRO_SISTEMICO, mensagem)

    def erro_critico(self, mensagem: str | None = None) -> Monitor:
        """Marca um erro crítico (encerra o processo inteiro)."""
        return self._encerrar(STATUS_ERRO_CRITICO, mensagem)
