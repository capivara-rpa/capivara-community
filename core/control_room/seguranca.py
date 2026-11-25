"""Primitivas de segurança da Lagoa.

Concentra o que não deve ficar espalhado pelo serviço:

- **hash de senha** (PBKDF2-HMAC-SHA256 com salt aleatório);
- **tokens opacos** (sessões de usuário e tokens de máquina), guardados no
  banco apenas como hash SHA-256 — nunca em texto puro;
- **comparação em tempo constante** para evitar timing attacks.

Formato do hash de senha::

    pbkdf2_sha256$<iteracoes>$<salt_hex>$<hash_hex>
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITMO = "pbkdf2_sha256"
_ITERACOES = 200_000
_TAMANHO_SALT = 16


def hash_senha(senha: str, iteracoes: int = _ITERACOES) -> str:
    """Gera o hash de uma senha (nunca guarde a senha em texto puro)."""
    salt = secrets.token_bytes(_TAMANHO_SALT)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes)
    return f"{_ALGORITMO}${iteracoes}${salt.hex()}${digest.hex()}"


def conferir_senha(senha: str, hash_guardado: str | None) -> bool:
    """Confere a senha contra o hash guardado (tempo constante)."""
    if not hash_guardado:
        return False
    partes = hash_guardado.split("$")
    if len(partes) != 4 or partes[0] != _ALGORITMO:
        return False
    try:
        iteracoes = int(partes[1])
        salt = bytes.fromhex(partes[2])
        esperado = bytes.fromhex(partes[3])
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes)
    return hmac.compare_digest(digest, esperado)


def gerar_token(tamanho: int = 32) -> str:
    """Gera um token opaco (URL-safe) para sessões e máquinas."""
    return secrets.token_urlsafe(tamanho)


def hash_token(token: str) -> str:
    """Hash SHA-256 do token (é o que fica guardado no banco)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_confere(token: str | None, hash_guardado: str | None) -> bool:
    """Compara o token recebido com o hash guardado (tempo constante)."""
    if not token or not hash_guardado:
        return False
    return hmac.compare_digest(hash_token(token), hash_guardado)


__all__ = [
    "hash_senha",
    "conferir_senha",
    "gerar_token",
    "hash_token",
    "token_confere",
]
