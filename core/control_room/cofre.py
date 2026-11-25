"""Cofre de credenciais (vault) da Lagoa.

Cifra os segredos antes de gravá-los no banco e os decifra sob demanda. A chave
vem de ``VAULT_CHAVE`` (``.env``) — uma frase-senha qualquer — ou, na ausência
dela, do chaveiro do sistema (``keyring``, quando ``VAULT_USAR_KEYRING=true``)
ou de um arquivo local ``data/vault.key`` gerado automaticamente na primeira
execução (fora do Git, permissão ``0600``).

É por isso que o banco ``data/orquestrador.db`` pode ser versionado/copiado sem
expor as senhas: os valores secretos ficam cifrados (Fernet/AES-128).

Uso interno (servidor)::

    from core.control_room import cofre

    guardado = cofre.cifrar("minha-senha")
    assert cofre.decifrar(guardado) == "minha-senha"
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from settings.parametros import VAULT_ARQUIVO_CHAVE, VAULT_CHAVE, VAULT_USAR_KEYRING

# Marca os valores que passaram pelo cofre (permite valores legados em texto)
_PREFIXO = "enc::"

# Identificação da chave no chaveiro do sistema (keyring)
_SERVICO_KEYRING = "rpa-brasil"
_USUARIO_KEYRING = "vault"


def _chave_do_keyring() -> str | None:
    """Lê (ou cria) a chave do cofre no chaveiro do sistema.

    Devolve ``None`` quando o ``keyring`` não está instalado ou indisponível,
    para o cofre cair de volta ao arquivo local ``data/vault.key``.
    """
    try:
        import keyring
    except ImportError:
        logger.warning(
            "[cofre] VAULT_USAR_KEYRING=true, mas o 'keyring' não está instalado "
            '(pip install -e ".[keyring]"). Usando data/vault.key.'
        )
        return None

    try:
        guardada = keyring.get_password(_SERVICO_KEYRING, _USUARIO_KEYRING)
        if guardada:
            return guardada
        nova = Fernet.generate_key().decode("ascii")
        keyring.set_password(_SERVICO_KEYRING, _USUARIO_KEYRING, nova)
        logger.success("[cofre] chave do cofre criada no chaveiro do sistema")
        return nova
    except Exception as erro:  # noqa: BLE001 (keyring pode falhar sem backend)
        logger.warning(f"[cofre] chaveiro indisponível ({erro}). Usando data/vault.key.")
        return None


def _material_chave() -> bytes:
    """Devolve 32 bytes de chave (frase-senha, keyring ou arquivo local)."""
    frase = (VAULT_CHAVE or "").strip()
    if frase:
        return hashlib.sha256(frase.encode("utf-8")).digest()

    if VAULT_USAR_KEYRING:
        valor = _chave_do_keyring()
        if valor:
            return base64.urlsafe_b64decode(valor.encode("ascii"))

    if not VAULT_ARQUIVO_CHAVE.exists():
        VAULT_ARQUIVO_CHAVE.parent.mkdir(parents=True, exist_ok=True)
        VAULT_ARQUIVO_CHAVE.write_bytes(Fernet.generate_key())
        try:
            os.chmod(VAULT_ARQUIVO_CHAVE, 0o600)
        except OSError:  # pragma: no cover (Windows não suporta o modo POSIX)
            pass
        logger.warning(
            f"[cofre] chave local criada em {VAULT_ARQUIVO_CHAVE}. "
            "Defina VAULT_CHAVE no .env para compartilhar o cofre entre máquinas."
        )

    return base64.urlsafe_b64decode(VAULT_ARQUIVO_CHAVE.read_bytes())


def _fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_material_chave()))


def esta_cifrado(valor: str | None) -> bool:
    """Diz se um valor já está cifrado pelo cofre."""
    return isinstance(valor, str) and valor.startswith(_PREFIXO)


def cifrar(valor: str | None) -> str | None:
    """Cifra um valor (idempotente: não cifra o que já está cifrado)."""
    if valor is None or esta_cifrado(valor):
        return valor
    return _PREFIXO + _fernet().encrypt(str(valor).encode("utf-8")).decode("ascii")


def decifrar(valor: str | None) -> str | None:
    """Decifra um valor. Valores legados (texto puro) são devolvidos como estão."""
    if valor is None or not esta_cifrado(valor):
        return valor
    try:
        return _fernet().decrypt(valor[len(_PREFIXO):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error("[cofre] não foi possível decifrar um segredo (chave diferente?)")
        return None


__all__ = ["cifrar", "decifrar", "esta_cifrado"]
