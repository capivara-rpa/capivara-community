"""Notificações por webhook (Slack, Teams, Discord e Telegram).

Ideal para avisar o time quando um robô termina, falha ou encontra um erro de
negócio::

    from core.rpa import notificacoes

    notificacoes.enviar_slack(
        "https://hooks.slack.com/services/...",
        "Relatório de clientes gerado com sucesso.",
        titulo="Robô de clientes",
    )
"""

from __future__ import annotations

from typing import Any

import requests
from loguru import logger

from core.tratador import ErroRPA


def _post_json(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    try:
        resposta = requests.post(url, json=payload, timeout=timeout)
        resposta.raise_for_status()
    except requests.RequestException:
        # Não inclui a URL na mensagem: webhooks do Telegram carregam o token.
        raise ErroRPA(
            "Falha ao enviar notificação. Verifique a URL/webhook e a conexão."
        ) from None
    try:
        return resposta.json()
    except ValueError:
        return {"status_code": resposta.status_code}


def enviar_webhook(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    """Envia um JSON qualquer para um webhook."""
    resultado = _post_json(url, payload, timeout=timeout)
    logger.success("Webhook enviado com sucesso.")
    return resultado


def enviar_slack(webhook: str, mensagem: str, titulo: str | None = None) -> dict[str, Any]:
    """Envia uma mensagem para um Incoming Webhook do Slack."""
    texto = f"*{titulo}*\n{mensagem}" if titulo else mensagem
    resultado = _post_json(webhook, {"text": texto})
    logger.success("Notificação enviada ao Slack.")
    return resultado


def enviar_teams(webhook: str, mensagem: str, titulo: str | None = None) -> dict[str, Any]:
    """Envia um MessageCard para um Incoming Webhook do Microsoft Teams."""
    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": titulo or "Capivara",
        "themeColor": "1FA463",
        "title": titulo or "Capivara",
        "text": mensagem,
    }
    resultado = _post_json(webhook, payload)
    logger.success("Notificação enviada ao Teams.")
    return resultado


def enviar_discord(webhook: str, mensagem: str, usuario: str = "Capivara") -> dict[str, Any]:
    """Envia uma mensagem para um webhook do Discord."""
    resultado = _post_json(webhook, {"content": mensagem, "username": usuario})
    logger.success("Notificação enviada ao Discord.")
    return resultado


def enviar_telegram(bot_token: str, chat_id: str | int, mensagem: str) -> dict[str, Any]:
    """Envia uma mensagem pelo Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resultado = _post_json(url, {"chat_id": chat_id, "text": mensagem})
    logger.success("Notificação enviada ao Telegram.")
    return resultado


__all__ = [
    "enviar_webhook",
    "enviar_slack",
    "enviar_teams",
    "enviar_discord",
    "enviar_telegram",
]
