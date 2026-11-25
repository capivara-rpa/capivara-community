"""Utilidades de segurança: senhas, tokens, hashes e criptografia simples.

Não substitui um cofre/KMS em produção, mas resolve o dia a dia dos robôs::

    from core.rpa import seguranca

    senha = seguranca.gerar_senha(20)
    resumo = seguranca.hash_sha256("texto")
    token = seguranca.criptografar_texto("segredo", chave="minha-frase")
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import string
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from core.tratador import ErroRPA
from settings.parametros import VAULT_CHAVE


def gerar_senha(tamanho: int = 16, simbolos: bool = True) -> str:
    """Gera uma senha aleatória com maiúsculas, minúsculas, números e símbolos."""
    if tamanho < 4:
        raise ErroRPA("A senha precisa ter pelo menos 4 caracteres.")
    minusculas = string.ascii_lowercase
    maiusculas = string.ascii_uppercase
    digitos = string.digits
    especiais = "!@#$%&*()-_=+[]{};:,.?/" if simbolos else ""
    alfabeto = minusculas + maiusculas + digitos + especiais
    obrigatorios = [secrets.choice(minusculas), secrets.choice(maiusculas), secrets.choice(digitos)]
    if simbolos:
        obrigatorios.append(secrets.choice(especiais))
    restante = [secrets.choice(alfabeto) for _ in range(max(0, tamanho - len(obrigatorios)))]
    caracteres = obrigatorios + restante
    secrets.SystemRandom().shuffle(caracteres)
    senha = "".join(caracteres[:tamanho])
    logger.info(f"Senha aleatória gerada ({tamanho} caracteres).")
    return senha


def gerar_token(tamanho: int = 32) -> str:
    """Gera um token URL-safe (útil para APIs e integrações)."""
    if tamanho < 8:
        raise ErroRPA("O token precisa ter pelo menos 8 bytes de entropia.")
    return secrets.token_urlsafe(tamanho)


def hash_sha256(texto: str | bytes) -> str:
    """Calcula o hash SHA-256 de um texto."""
    material = texto.encode("utf-8") if isinstance(texto, str) else texto
    return hashlib.sha256(material).hexdigest()


def hash_arquivo(caminho: str | Path, algoritmo: str = "sha256") -> str:
    """Calcula o hash de um arquivo lendo em blocos (não carrega tudo na memória)."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroRPA(f"Arquivo não encontrado para hash: {caminho}")
    try:
        resumo = hashlib.new(algoritmo)
    except ValueError as erro:
        raise ErroRPA(f"Algoritmo de hash inválido: {algoritmo}") from erro
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    logger.info(f"Hash {algoritmo} de {caminho.name}: {resumo.hexdigest()[:16]}...")
    return resumo.hexdigest()


def base64_codificar(texto: str | bytes) -> str:
    """Codifica um texto/bytes em Base64."""
    material = texto.encode("utf-8") if isinstance(texto, str) else texto
    return base64.b64encode(material).decode("ascii")


def base64_decodificar(texto: str | bytes, como_bytes: bool = False) -> str | bytes:
    """Decodifica um Base64 (texto UTF-8 por padrão)."""
    material = texto.encode("ascii") if isinstance(texto, str) else texto
    try:
        decodificado = base64.b64decode(material, validate=True)
    except (ValueError, TypeError) as erro:
        raise ErroRPA(f"Base64 inválido: {erro}") from erro
    return decodificado if como_bytes else decodificado.decode("utf-8", errors="replace")


def _chave_fernet(chave: str | bytes | None) -> bytes:
    material = chave if chave is not None else VAULT_CHAVE
    if not material:
        raise ErroRPA(
            "Informe uma chave ou defina VAULT_CHAVE no .env para criptografar/descriptografar."
        )
    if isinstance(material, str):
        material = material.encode("utf-8")
    return base64.urlsafe_b64encode(hashlib.sha256(material).digest())


def criptografar_texto(texto: str, chave: str | bytes | None = None) -> str:
    """Criptografa um texto com Fernet (AES-128 em modo CBC + HMAC)."""
    token = Fernet(_chave_fernet(chave)).encrypt(str(texto).encode("utf-8")).decode("ascii")
    logger.info("Texto criptografado com sucesso.")
    return token


def descriptografar_texto(token: str, chave: str | bytes | None = None) -> str:
    """Descriptografa um token gerado por :func:`criptografar_texto`."""
    try:
        return Fernet(_chave_fernet(chave)).decrypt(str(token).encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as erro:
        raise ErroRPA("Não foi possível descriptografar: token ou chave inválidos.") from erro


def mascarar_segredo(valor: str, manter: int = 2) -> str:
    """Mascara um segredo para logs, mantendo só os últimos caracteres."""
    texto = str(valor)
    if not texto:
        return ""
    if manter <= 0 or len(texto) <= manter:
        return "*" * len(texto)
    return "*" * (len(texto) - manter) + texto[-manter:]


def comparar_seguro(valor_a: str, valor_b: str) -> bool:
    """Compara dois valores em tempo constante (evita timing attacks)."""
    return hmac.compare_digest(str(valor_a), str(valor_b))


def gerar_uuid() -> str:
    """Gera um UUID versão 4 em texto."""
    return str(uuid.uuid4())


__all__ = [
    "gerar_senha",
    "gerar_token",
    "hash_sha256",
    "hash_arquivo",
    "base64_codificar",
    "base64_decodificar",
    "criptografar_texto",
    "descriptografar_texto",
    "mascarar_segredo",
    "comparar_seguro",
    "gerar_uuid",
]
