"""Utilidades de texto para limpar, extrair e comparar dados.

São funções puras (sem navegador/rede) úteis em qualquer fluxo::

    from core.rpa import texto

    texto.slug("Relatório de Clientes 2026")
    # 'relatorio-de-clientes-2026'

    texto.extrair_emails("fale com a@b.com ou c@d.com")
    # ['a@b.com', 'c@d.com']
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from loguru import logger

from core.tratador import ErroRPA

_ESPACOS = re.compile(r"\s+")
_NUMEROS = re.compile(r"\d+")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"https?://[^\s<>\"']+")
_CONECTORES = {"de", "da", "das", "do", "dos", "e", "em", "na", "nas", "no", "nos"}


def limpar_texto(texto: str, reduzir_espacos: bool = True) -> str:
    """Remove caracteres de controle e espaços sobrando nas pontas."""
    limpo = "".join(
        caractere
        for caractere in str(texto)
        if caractere in "\n\t" or unicodedata.category(caractere)[0] != "C"
    ).strip()
    if reduzir_espacos:
        limpo = _ESPACOS.sub(" ", limpo)
    logger.debug(f"Texto limpo ({len(str(texto))} -> {len(limpo)} caracteres)")
    return limpo


def remover_acentos(texto: str) -> str:
    """Troca letras acentuadas pelas versões sem acento."""
    decomposto = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def normalizar_espacos(texto: str) -> str:
    """Junta espaços, tabs e quebras de linha em um único espaço."""
    return _ESPACOS.sub(" ", str(texto)).strip()


def slug(texto: str, separador: str = "-") -> str:
    """Gera um identificador amigável para URL/arquivo.

    ``slug("Relatório de Clientes 2026")`` -> ``"relatorio-de-clientes-2026"``.
    """
    base = remover_acentos(str(texto)).lower()
    base = re.sub(r"[^a-z0-9]+", separador, base)
    return base.strip(separador)


def capitalizar_nome(nome: str) -> str:
    """Capitaliza nomes preservando conectores (de, da, dos...)."""
    palavras = normalizar_espacos(nome).lower().split()
    resultado = [
        palavra if indice and palavra in _CONECTORES else palavra.capitalize()
        for indice, palavra in enumerate(palavras)
    ]
    return " ".join(resultado)


def extrair_numeros(texto: str) -> list[str]:
    """Extrai todos os grupos de dígitos encontrados no texto."""
    return _NUMEROS.findall(str(texto))


def extrair_emails(texto: str) -> list[str]:
    """Extrai e-mails únicos (preservando a ordem de aparição)."""
    return list(dict.fromkeys(_EMAIL.findall(str(texto))))


def extrair_urls(texto: str) -> list[str]:
    """Extrai URLs http/https únicas de um texto."""
    return list(dict.fromkeys(_URL.findall(str(texto))))


def mascarar_email(email: str) -> str:
    """Mascara um e-mail para logs: ``arthur@x.com`` -> ``a***@x.com``."""
    email = str(email).strip()
    if "@" not in email:
        raise ErroRPA(f"E-mail inválido para mascarar: {email!r}")
    usuario, dominio = email.split("@", 1)
    if len(usuario) <= 1:
        mascarado = "*"
    else:
        mascarado = usuario[0] + "*" * max(1, len(usuario) - 2) + usuario[-1]
    return f"{mascarado}@{dominio}"


def contar_palavras(texto: str) -> int:
    """Conta palavras (sequências separadas por espaço)."""
    return len(normalizar_espacos(texto).split())


def similaridade(texto_a: str, texto_b: str) -> float:
    """Retorna a similaridade entre dois textos (0.0 a 1.0)."""
    return SequenceMatcher(None, str(texto_a).lower(), str(texto_b).lower()).ratio()


def encontrar_padrao(texto: str, padrao: str, grupo: int = 0) -> list[str]:
    """Retorna todas as ocorrências de uma expressão regular.

    ``grupo`` escolhe o grupo de captura (0 = ocorrência inteira).
    """
    try:
        return [ocorrencia.group(grupo) for ocorrencia in re.finditer(padrao, str(texto))]
    except re.error as erro:
        raise ErroRPA(f"Expressão regular inválida: {erro}") from erro


def substituir_padrao(texto: str, padrao: str, substituto: str, contar: int = 0) -> str:
    """Substitui ocorrências de uma expressão regular.

    ``contar=0`` substitui todas; ``contar=1`` só a primeira.
    """
    try:
        return re.sub(padrao, substituto, str(texto), count=contar)
    except re.error as erro:
        raise ErroRPA(f"Expressão regular inválida: {erro}") from erro


def truncar_texto(texto: str, limite: int = 80, sufixo: str = "...") -> str:
    """Corta um texto no limite, adicionando sufixo quando necessário."""
    if limite < 1:
        raise ErroRPA("O limite precisa ser maior que zero.")
    texto = str(texto)
    if len(texto) <= limite:
        return texto
    return texto[: max(0, limite - len(sufixo))].rstrip() + sufixo


__all__ = [
    "limpar_texto",
    "remover_acentos",
    "normalizar_espacos",
    "slug",
    "capitalizar_nome",
    "extrair_numeros",
    "extrair_emails",
    "extrair_urls",
    "mascarar_email",
    "contar_palavras",
    "similaridade",
    "encontrar_padrao",
    "substituir_padrao",
    "truncar_texto",
]
