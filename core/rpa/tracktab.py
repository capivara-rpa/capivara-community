"""Integração com a extensão TrackTab (gravador de elementos/XPath).

O TrackTab (pasta ``tracktab/`` na raiz do projeto) é uma extensão de navegador
que captura elementos de qualquer página e exporta um JSON com três variações
de seletor por elemento. Este módulo lê esse arquivo e entrega os seletores
prontos para usar com o :class:`core.rpa.browser.Navegador`.

Fluxo típico::

    from core.rpa import tracktab

    elementos = tracktab.carregar("data/input/tracktab.json")
    navegador.clicar_elemento(elementos["Botão Entrar"].relativo)

    # ou apenas os seletores, por nome
    seletores = tracktab.seletores("data/input/tracktab.json")
    navegador.escrever_texto(seletores["Input E-mail"], "eu@exemplo.com")
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from core.tratador import ErroRPA

TIPOS = {
    "relativo": "relativo",
    "relative": "relativo",
    "custom": "custom",
    "completo": "completo",
    "full": "completo",
}


@dataclass(frozen=True)
class Elemento:
    """Um elemento capturado pelo TrackTab, com seus três seletores."""

    nome: str
    tag: str
    texto: str
    completo: str
    relativo: str
    custom: str

    @property
    def seletor(self) -> str:
        """Melhor seletor disponível (relativo → custom → completo)."""
        return self.relativo or self.custom or self.completo


def _ler_export(caminho: str | Path) -> dict:
    arquivo = Path(caminho)
    if not arquivo.is_file():
        raise ErroRPA(f"Export do TrackTab não encontrado: {arquivo}")
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ErroRPA(f"JSON inválido em {arquivo}: {erro}") from erro


def carregar(caminho: str | Path) -> dict[str, Elemento]:
    """Lê um export do TrackTab e devolve ``{nome: Elemento}``."""
    dados = _ler_export(caminho)
    elementos: dict[str, Elemento] = {}
    for item in dados.get("elements", []):
        elemento = Elemento(
            nome=item.get("name") or item.get("tag") or "elemento",
            tag=item.get("tag", ""),
            texto=item.get("text", ""),
            completo=item.get("fullXpath", ""),
            relativo=item.get("relativeXpath", ""),
            custom=item.get("customPath", ""),
        )
        elementos[elemento.nome] = elemento

    logger.success(
        f"TrackTab: {len(elementos)} elemento(s) carregado(s) de {Path(caminho).name}"
    )
    return elementos


def seletores(caminho: str | Path, tipo: str = "relativo") -> dict[str, str]:
    """Devolve ``{nome: seletor}`` usando o tipo pedido.

    ``tipo`` aceita ``relativo`` (padrão), ``custom`` ou ``completo``.
    """
    chave = TIPOS.get(tipo)
    if chave is None:
        raise ErroRPA(
            f"Tipo de seletor inválido: {tipo!r}. Use: {', '.join(sorted(TIPOS))}."
        )
    return {
        nome: getattr(elemento, chave)
        for nome, elemento in carregar(caminho).items()
    }


def _validar_tipo(tipo: str) -> str:
    chave = TIPOS.get(tipo)
    if chave is None:
        raise ErroRPA(f"Tipo de seletor inválido: {tipo!r}. Use: {', '.join(sorted(TIPOS))}.")
    return chave


def obter(caminho: str | Path, nome: str, tipo: str = "relativo") -> str:
    """Retorna o seletor de um elemento pelo nome exato."""
    chave = _validar_tipo(tipo)
    elementos = carregar(caminho)
    elemento = elementos.get(nome)
    if elemento is None:
        raise ErroRPA(f"Elemento '{nome}' não encontrado no TrackTab.")
    return getattr(elemento, chave)


def buscar(
    caminho: str | Path,
    nome_contem: str,
    tipo: str = "relativo",
) -> dict[str, str]:
    """Busca elementos cujo nome contenha o texto (sem diferenciar maiúsculas)."""
    chave = _validar_tipo(tipo)
    alvo = nome_contem.lower()
    encontrados = {
        nome: getattr(elemento, chave)
        for nome, elemento in carregar(caminho).items()
        if alvo in nome.lower()
    }
    logger.info(f"TrackTab: {len(encontrados)} elemento(s) casaram com '{nome_contem}'.")
    return encontrados


def listar_nomes(caminho: str | Path) -> list[str]:
    """Lista os nomes dos elementos capturados."""
    return list(carregar(caminho))


def para_lista(caminho: str | Path) -> list[dict[str, Any]]:
    """Converte o export em uma lista de dicionários (pronta para DataFrame/CSV)."""
    return [
        {
            "nome": elemento.nome,
            "tag": elemento.tag,
            "texto": elemento.texto,
            "relativo": elemento.relativo,
            "custom": elemento.custom,
            "completo": elemento.completo,
        }
        for elemento in carregar(caminho).values()
    ]


def exportar_csv(
    caminho_export: str | Path,
    caminho_csv: str | Path,
    tipo: str = "relativo",
) -> Path:
    """Exporta ``nome`` e o seletor escolhido para um CSV."""
    chave = _validar_tipo(tipo)
    caminho_csv = Path(caminho_csv)
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    with caminho_csv.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=["nome", "seletor"])
        escritor.writeheader()
        for nome, elemento in carregar(caminho_export).items():
            escritor.writerow({"nome": nome, "seletor": getattr(elemento, chave)})
    logger.success(f"TrackTab exportado para CSV: {caminho_csv}")
    return caminho_csv


def resumo(caminho: str | Path) -> dict[str, Any]:
    """Resumo do export: total, tags e quantos elementos têm cada seletor."""
    elementos = carregar(caminho)
    dados = {
        "total": len(elementos),
        "tags": dict(Counter(elemento.tag for elemento in elementos.values())),
        "com_relativo": sum(1 for elemento in elementos.values() if elemento.relativo),
        "com_custom": sum(1 for elemento in elementos.values() if elemento.custom),
        "com_completo": sum(1 for elemento in elementos.values() if elemento.completo),
    }
    logger.info(f"TrackTab: resumo {dados['total']} elemento(s).")
    return dados


def combinar(*caminhos: str | Path) -> dict[str, Elemento]:
    """Junta vários exports do TrackTab em um único dicionário."""
    if not caminhos:
        raise ErroRPA("Informe ao menos um export do TrackTab.")
    combinados: dict[str, Elemento] = {}
    for caminho in caminhos:
        combinados.update(carregar(caminho))
    logger.success(f"TrackTab: {len(combinados)} elemento(s) combinados.")
    return combinados


__all__ = [
    "Elemento",
    "TIPOS",
    "carregar",
    "seletores",
    "obter",
    "buscar",
    "listar_nomes",
    "para_lista",
    "exportar_csv",
    "resumo",
    "combinar",
]
