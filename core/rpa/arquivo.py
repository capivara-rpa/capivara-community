"""Operações com arquivos e pastas (explorer) com cara de low-code.

Inclui listar, copiar, mover, renomear, apagar, baixar, compactar e extrair::

    from core.rpa import arquivo

    arquivos = arquivo.listar_arquivos("data/input")
    arquivo.mover_arquivo("data/input/a.csv", "data/output/a.csv")
    arquivo.baixar_arquivo("https://.../relatorio.pdf", "data/output/")
"""

from __future__ import annotations

import configparser
import hashlib
import json
import shutil
import zipfile
from collections import deque
from pathlib import Path
from typing import Any

import requests
from loguru import logger
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from core.tratador import ErroRPA


# ----------------------------------------------------------------------
# Explorar / listar
# ----------------------------------------------------------------------
def listar_arquivos(pasta: str | Path, extensao: str | None = None, completo: bool = True) -> list[Path]:
    """Lista os arquivos de uma pasta (opcionalmente filtrando por extensão).

    ``extensao`` pode ser passada com ou sem ponto (ex.: ``"csv"`` ou ``".CSV"``).
    """
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise ErroRPA(f"Pasta não encontrada: {pasta}")

    padrao = "*" if extensao is None else f"*.{extensao.lower().lstrip('.')}"
    arquivos = [p for p in pasta.glob(padrao) if p.is_file()]
    ordenados = sorted(arquivos, key=lambda p: p.name.lower())

    logger.info(f"{len(ordenados)} arquivo(s) em '{pasta}'{f' ({extensao})' if extensao else ''}:")
    for arquivo in ordenados:
        logger.info(f"  - {arquivo.name}")
    return [p.resolve() for p in ordenados] if completo else ordenados


def criar_pasta(caminho: str | Path) -> Path:
    """Cria uma pasta (e subpastas) se ela não existir."""
    caminho = Path(caminho)
    caminho.mkdir(parents=True, exist_ok=True)
    logger.success(f"Pasta garantida: {caminho}")
    return caminho


def listar_pastas(pasta: str | Path, completo: bool = True) -> list[Path]:
    """Lista as subpastas de um diretório."""
    pasta = Path(pasta)
    pastas = sorted(p for p in pasta.iterdir() if p.is_dir())
    logger.info(f"{len(pastas)} pasta(s) em '{pasta}': {[p.name for p in pastas]}")
    return [p.resolve() for p in pastas] if completo else pastas


# ----------------------------------------------------------------------
# Texto puro
# ----------------------------------------------------------------------
def ler_arquivo_texto(caminho: str | Path, codificacao: str = "utf-8") -> str:
    """Lê o conteúdo de um arquivo de texto."""
    caminho = Path(caminho)
    conteudo = caminho.read_text(encoding=codificacao)
    logger.info(f"Arquivo lido: {caminho.name} ({len(conteudo)} caracteres)")
    return conteudo


def escrever_arquivo_texto(caminho: str | Path, conteudo: str, codificacao: str = "utf-8") -> Path:
    """Escreve um conteúdo de texto em um arquivo."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding=codificacao)
    logger.success(f"Arquivo escrito: {caminho}")
    return caminho


# ----------------------------------------------------------------------
# Copiar / mover / renomear / apagar
# ----------------------------------------------------------------------
def _resolver_destino(origem: Path, destino: Path) -> Path:
    if destino.is_dir() or str(destino).endswith(("/", "\\")):
        return destino / origem.name
    return destino


def copiar_arquivo(origem: str | Path, destino: str | Path, sobrescrever: bool = True) -> Path:
    """Copia um arquivo para outro local."""
    origem, destino = Path(origem), Path(destino)
    if not origem.is_file():
        raise ErroRPA(f"Arquivo de origem não encontrado: {origem}")
    destino = _resolver_destino(origem, destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not sobrescrever:
        raise ErroRPA(f"Destino já existe e sobrescrever=False: {destino}")
    shutil.copy2(origem, destino)
    logger.success(f"Arquivo copiado: {origem.name} -> {destino}")
    return destino


def mover_arquivo(origem: str | Path, destino: str | Path, sobrescrever: bool = True) -> Path:
    """Move um arquivo para outro local (corta e cola)."""
    origem, destino = Path(origem), Path(destino)
    if not origem.is_file():
        raise ErroRPA(f"Arquivo de origem não encontrado: {origem}")
    destino = _resolver_destino(origem, destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not sobrescrever:
        raise ErroRPA(f"Destino já existe e sobrescrever=False: {destino}")
    shutil.move(str(origem), str(destino))
    logger.success(f"Arquivo movido: {origem.name} -> {destino}")
    return destino


def renomear_arquivo(origem: str | Path, novo_nome: str) -> Path:
    """Renomeia um arquivo dentro da mesma pasta."""
    origem = Path(origem)
    destino = origem.parent / novo_nome
    if destino.exists():
        raise ErroRPA(f"Já existe um arquivo com o nome: {destino}")
    origem.rename(destino)
    logger.success(f"Arquivo renomeado: {origem.name} -> {novo_nome}")
    return destino


def apagar_arquivo(caminho: str | Path, confirmar: bool = False) -> None:
    """Apaga um arquivo. Marque ``confirmar=True`` para executar de fato."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroRPA(f"Arquivo não encontrado: {caminho}")
    if not confirmar:
        logger.warning(f"Apagamento evitado (confirme com confirmar=True): {caminho}")
        return
    caminho.unlink()
    logger.success(f"Arquivo apagado: {caminho}")


# ----------------------------------------------------------------------
# Download
# ----------------------------------------------------------------------
def baixar_arquivo(url: str, destino: str | Path, tempo_max: int = 120, nome_arquivo: str | None = None) -> Path:
    """Baixa um arquivo de uma URL, exibindo barra de progresso."""
    destino = Path(destino)
    if destino.is_dir() or str(destino).endswith(("/", "\\")):
        nome = nome_arquivo or url.split("/")[-1].split("?")[0] or "download"
        destino = destino / nome
    destino.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=tempo_max) as resposta:
        resposta.raise_for_status()
        total = int(resposta.headers.get("content-length", 0))

        with Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progresso:
            tarefa = progresso.add_task(f"Baixando {destino.name}...", total=total)
            with open(destino, "wb") as arquivo:
                for parte in resposta.iter_content(chunk_size=1024 * 256):
                    if parte:
                        arquivo.write(parte)
                        progresso.update(tarefa, advance=len(parte))

    logger.success(f"Download concluído: {destino}")
    return destino


# ----------------------------------------------------------------------
# ZIP
# ----------------------------------------------------------------------
def compactar_pasta(pasta: str | Path, destino_zip: str | Path | None = None) -> Path:
    """Compacta uma pasta inteira em um arquivo .zip."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise ErroRPA(f"Pasta não encontrada: {pasta}")
    destino_zip = Path(destino_zip or pasta.parent / f"{pasta.name}.zip")
    destino_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(destino_zip, "w", zipfile.ZIP_DEFLATED) as zip_final:
        for arquivo in pasta.rglob("*"):
            if arquivo.is_file():
                zip_final.write(arquivo, arquivo.relative_to(pasta))

    logger.success(f"Pasta compactada: {pasta.name} -> {destino_zip}")
    return destino_zip


def extrair_zip(caminho_zip: str | Path, pasta_destino: str | Path | None = None) -> Path:
    """Extrai um arquivo .zip para uma pasta."""
    caminho_zip = Path(caminho_zip)
    if not caminho_zip.is_file():
        raise ErroRPA(f"Arquivo ZIP não encontrado: {caminho_zip}")
    pasta_destino = Path(pasta_destino or caminho_zip.parent / caminho_zip.stem)
    pasta_destino.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(caminho_zip, "r") as zip_aberto:
        zip_aberto.extractall(pasta_destino)

    logger.success(f"ZIP extraído: {caminho_zip.name} -> {pasta_destino}")
    return pasta_destino


# ----------------------------------------------------------------------
# JSON / INI
# ----------------------------------------------------------------------
def ler_json(caminho: str | Path) -> Any:
    """Lê um arquivo JSON e devolve a estrutura Python (dict/list)."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroRPA(f"Arquivo JSON não encontrado: {caminho}")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ErroRPA(f"JSON inválido em {caminho}: {erro}") from erro
    logger.success(f"JSON lido: {caminho.name}")
    return dados


def escrever_json(caminho: str | Path, dados: Any, indentar: int = 2) -> Path:
    """Escreve uma estrutura Python em um arquivo JSON."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=indentar) + "\n",
        encoding="utf-8",
    )
    logger.success(f"JSON escrito: {caminho}")
    return caminho


def ler_ini(caminho: str | Path) -> dict[str, dict[str, str]]:
    """Lê um arquivo .ini e devolve ``{seção: {chave: valor}}``."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroRPA(f"Arquivo INI não encontrado: {caminho}")
    config = configparser.ConfigParser()
    config.read(caminho, encoding="utf-8")
    dados = {secao: dict(config[secao]) for secao in config.sections()}
    if not dados and config.defaults():
        dados["DEFAULT"] = dict(config.defaults())
    logger.success(f"INI lido: {caminho.name} ({len(dados)} seção(ões))")
    return dados


def escrever_ini(caminho: str | Path, dados: dict[str, dict[str, Any]]) -> Path:
    """Escreve um dicionário de seções em um arquivo .ini."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    for secao, valores in dados.items():
        if secao.upper() == "DEFAULT":
            destino = config["DEFAULT"]
        else:
            if not config.has_section(secao):
                config.add_section(secao)
            destino = config[secao]
        for chave, valor in valores.items():
            destino[str(chave)] = str(valor)
    with caminho.open("w", encoding="utf-8") as arquivo:
        config.write(arquivo)
    logger.success(f"INI escrito: {caminho}")
    return caminho


# ----------------------------------------------------------------------
# Hash / comparação / linhas
# ----------------------------------------------------------------------
def calcular_hash(caminho: str | Path, algoritmo: str = "sha256") -> str:
    """Calcula o hash de um arquivo (lendo em blocos)."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroRPA(f"Arquivo não encontrado: {caminho}")
    try:
        resumo = hashlib.new(algoritmo)
    except ValueError as erro:
        raise ErroRPA(f"Algoritmo de hash inválido: {algoritmo}") from erro
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def comparar_arquivos(arquivo_a: str | Path, arquivo_b: str | Path) -> bool:
    """Diz se dois arquivos têm o mesmo conteúdo (tamanho + hash)."""
    a, b = Path(arquivo_a), Path(arquivo_b)
    if not a.is_file() or not b.is_file():
        raise ErroRPA(f"Arquivo não encontrado: {a if not a.is_file() else b}")
    if a.stat().st_size != b.stat().st_size:
        return False
    iguais = calcular_hash(a) == calcular_hash(b)
    logger.info(f"Arquivos {'iguais' if iguais else 'diferentes'}: {a.name} / {b.name}")
    return iguais


def ler_ultimas_linhas(caminho: str | Path, quantidade: int = 10) -> list[str]:
    """Lê as últimas N linhas de um arquivo de texto."""
    if quantidade < 1:
        raise ErroRPA("A quantidade de linhas precisa ser maior que zero.")
    caminho = Path(caminho)
    with caminho.open("r", encoding="utf-8", errors="replace") as arquivo:
        linhas = list(deque(arquivo, maxlen=quantidade))
    return [linha.rstrip("\r\n") for linha in linhas]


def contar_linhas_arquivo(caminho: str | Path) -> int:
    """Conta as linhas de um arquivo de texto."""
    caminho = Path(caminho)
    with caminho.open("r", encoding="utf-8", errors="replace") as arquivo:
        total = sum(1 for _ in arquivo)
    logger.info(f"{caminho.name}: {total} linha(s)")
    return total


def substituir_no_arquivo(
    caminho: str | Path,
    antigo: str,
    novo: str,
    codificacao: str = "utf-8",
) -> int:
    """Substitui um texto em um arquivo e devolve quantas trocas fez."""
    if not antigo:
        raise ErroRPA("O texto a substituir não pode ser vazio.")
    caminho = Path(caminho)
    conteudo = caminho.read_text(encoding=codificacao)
    total = conteudo.count(antigo)
    if total:
        caminho.write_text(conteudo.replace(antigo, novo), encoding=codificacao)
        logger.success(f"{total} substituição(ões) em {caminho.name}")
    else:
        logger.warning(f"Nenhuma ocorrência encontrada em {caminho.name}")
    return total


# ----------------------------------------------------------------------
# Juntar / dividir / tamanho
# ----------------------------------------------------------------------
def juntar_arquivos(
    arquivos: list[str | Path],
    destino: str | Path,
    separador: str = "\n",
) -> Path:
    """Junta vários arquivos de texto em um único arquivo."""
    if not arquivos:
        raise ErroRPA("Informe ao menos um arquivo para juntar.")
    conteudos = [Path(arquivo).read_text(encoding="utf-8") for arquivo in arquivos]
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(separador.join(conteudos), encoding="utf-8")
    logger.success(f"{len(arquivos)} arquivo(s) juntados em {destino}")
    return destino


def dividir_arquivo(
    caminho: str | Path,
    linhas_por_arquivo: int,
    pasta_destino: str | Path | None = None,
) -> list[Path]:
    """Divide um arquivo de texto em partes com N linhas cada."""
    if linhas_por_arquivo < 1:
        raise ErroRPA("A quantidade de linhas por arquivo precisa ser maior que zero.")
    caminho = Path(caminho)
    linhas = caminho.read_text(encoding="utf-8").splitlines(keepends=True)
    pasta = Path(pasta_destino or caminho.parent)
    pasta.mkdir(parents=True, exist_ok=True)
    partes: list[Path] = []
    for indice, inicio in enumerate(range(0, len(linhas), linhas_por_arquivo), start=1):
        parte = pasta / f"{caminho.stem}_parte{indice:03d}{caminho.suffix}"
        parte.write_text("".join(linhas[inicio : inicio + linhas_por_arquivo]), encoding="utf-8")
        partes.append(parte)
    logger.success(f"{caminho.name} dividido em {len(partes)} parte(s).")
    return partes


def tamanho_arquivo(caminho: str | Path, unidade: str = "MB") -> float:
    """Retorna o tamanho de um arquivo na unidade pedida (B, KB, MB, GB)."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroRPA(f"Arquivo não encontrado: {caminho}")
    fatores = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    fator = fatores.get(unidade.upper())
    if fator is None:
        raise ErroRPA(f"Unidade inválida: {unidade!r}. Use B, KB, MB ou GB.")
    return round(caminho.stat().st_size / fator, 2)