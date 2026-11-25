"""Envio de e-mail (SMTP) com logs coloridos.

Uso::

    from core.rpa.email import enviar_email

    enviar_email(
        destinatarios=["cliente@exemplo.com"],
        assunto="Relatório do robô",
        corpo="Segue o relatório em anexo.",
        anexos=["data/output/relatorio.xlsx"],
    )

As configurações do servidor podem vir do ``.env`` (SMTP_SERVIDOR etc.).
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from loguru import logger

from core.tratador import ErroRPA
from settings.parametros import SMTP_ORIGEM, SMTP_PORTA, SMTP_SENHA, SMTP_SERVIDOR, SMTP_USUARIO


def _normalizar_lista(valor: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if not valor:
        return []
    if isinstance(valor, str):
        return [item.strip() for item in valor.split(",") if item.strip()]
    return [str(item).strip() for item in valor if str(item).strip()]


def _conectar_smtp(servidor: str, porta: int) -> smtplib.SMTP:
    if porta == 465:
        return smtplib.SMTP_SSL(servidor, porta)
    conexao = smtplib.SMTP(servidor, porta)
    conexao.starttls()
    return conexao


def enviar_email(
    destinatarios: list[str] | tuple[str, ...] | str,
    assunto: str,
    corpo: str = "",
    anexos: list[str | Path] | None = None,
    servidor: str | None = None,
    porta: int | None = None,
    usuario: str | None = None,
    senha: str | None = None,
    remetente: str | None = None,
    html: bool = False,
    cc: list[str] | tuple[str, ...] | str | None = None,
    bcc: list[str] | tuple[str, ...] | str | None = None,
    responder_para: str | None = None,
) -> None:
    """Envia um e-mail (texto ou HTML), com cópias e anexos opcionais.

    Parâmetros que não forem informados são lidos do ``.env``.
    """
    servidor = servidor or SMTP_SERVIDOR
    porta = porta or SMTP_PORTA
    usuario = SMTP_USUARIO if usuario is None else usuario
    senha = SMTP_SENHA if senha is None else senha
    remetente = remetente or SMTP_ORIGEM or usuario

    para = _normalizar_lista(destinatarios)
    copia = _normalizar_lista(cc)
    copia_oculta = _normalizar_lista(bcc)
    if not para:
        raise ErroRPA("Informe ao menos um destinatário.")

    if not servidor or not remetente:
        raise ErroRPA(
            "Configuração de e-mail incompleta. Preencha SMTP_SERVIDOR e SMTP_ORIGEM no .env."
        )

    mensagem = EmailMessage()
    mensagem["From"] = remetente
    mensagem["To"] = ", ".join(para)
    if copia:
        mensagem["Cc"] = ", ".join(copia)
    if responder_para:
        mensagem["Reply-To"] = responder_para
    mensagem["Subject"] = assunto
    if html:
        mensagem.set_content("Este e-mail contém conteúdo HTML.")
        mensagem.add_alternative(corpo or "", subtype="html")
    else:
        mensagem.set_content(corpo or "")

    for anexo in anexos or []:
        caminho = Path(anexo)
        if not caminho.is_file():
            raise ErroRPA(f"Anexo não encontrado: {caminho}")
        mensagem.add_attachment(
            caminho.read_bytes(),
            maintype="application",
            subtype="octet-stream",
            filename=caminho.name,
        )

    todos = para + copia + copia_oculta
    logger.info(f"Enviando e-mail para {len(todos)} destinatário(s) via {servidor}:{porta}...")

    conexao = _conectar_smtp(servidor, porta)
    try:
        if usuario and senha:
            conexao.login(usuario, senha)
        conexao.send_message(mensagem, to_addrs=todos)
        logger.success(f"E-mail enviado para: {', '.join(todos)}")
    except Exception as erro:  # noqa: BLE001
        raise ErroRPA(f"Falha ao enviar e-mail: {erro}") from erro
    finally:
        conexao.quit()


def enviar_email_html(
    destinatarios: list[str] | tuple[str, ...] | str,
    assunto: str,
    html: str,
    **kwargs,
) -> None:
    """Atalho para enviar um e-mail com corpo HTML."""
    enviar_email(destinatarios, assunto, corpo=html, html=True, **kwargs)


def testar_smtp(
    servidor: str | None = None,
    porta: int | None = None,
    usuario: str | None = None,
    senha: str | None = None,
) -> bool:
    """Testa a conexão/login SMTP e devolve ``True`` se estiver tudo certo."""
    servidor = servidor or SMTP_SERVIDOR
    porta = porta or SMTP_PORTA
    usuario = SMTP_USUARIO if usuario is None else usuario
    senha = SMTP_SENHA if senha is None else senha
    if not servidor:
        raise ErroRPA("SMTP_SERVIDOR não configurado no .env.")
    conexao = _conectar_smtp(servidor, porta)
    try:
        if usuario and senha:
            conexao.login(usuario, senha)
        codigo, mensagem = conexao.noop()
        logger.success(f"SMTP OK em {servidor}:{porta} ({codigo} {mensagem.decode(errors='ignore')})")
        return True
    except Exception as erro:  # noqa: BLE001
        logger.error(f"Falha no teste SMTP: {erro}")
        return False
    finally:
        conexao.quit()