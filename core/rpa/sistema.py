"""Interação com o sistema operacional: comandos, pastas, espera e avisos.

Funções úteis para robôs que precisam abrir um programa, esperar um arquivo
aparecer ou avisar o usuário no desktop::

    from core.rpa import sistema

    sistema.executar_comando("git status")
    sistema.abrir_pasta("data/output")
    sistema.esperar_arquivo("data/output/relatorio.xlsx", tempo_max=120)
"""

from __future__ import annotations

import getpass
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from loguru import logger

from core.tratador import ErroRPA


def executar_comando(
    comando: str | list[str],
    pasta: str | Path | None = None,
    tempo_max: int = 60,
    verificar: bool = False,
) -> dict[str, Any]:
    """Executa um comando do sistema e devolve ``codigo``, ``saida`` e ``erro``.

    Use apenas comandos confiáveis: quando ``comando`` é uma string, ela é
    executada pelo shell (permite pipes e redirecionamentos).
    """
    usar_shell = isinstance(comando, str)
    try:
        resultado = subprocess.run(
            comando,
            cwd=str(pasta) if pasta else None,
            capture_output=True,
            text=True,
            timeout=tempo_max,
            shell=usar_shell,
            check=False,
        )
    except subprocess.TimeoutExpired as erro:
        raise ErroRPA(f"Comando excedeu {tempo_max}s: {comando!r}") from erro
    except FileNotFoundError as erro:
        raise ErroRPA(f"Comando não encontrado: {comando!r}") from erro

    retorno = {
        "codigo": resultado.returncode,
        "saida": (resultado.stdout or "").strip(),
        "erro": (resultado.stderr or "").strip(),
    }
    if resultado.returncode == 0:
        logger.success(f"Comando concluído (código 0): {comando!r}")
    else:
        logger.warning(f"Comando terminou com código {resultado.returncode}: {comando!r}")
    if verificar and resultado.returncode != 0:
        raise ErroRPA(f"Comando falhou ({resultado.returncode}): {retorno['erro']}")
    return retorno


def abrir_programa(programa: str | Path, argumentos: list[str] | None = None) -> None:
    """Abre um programa/executável (sem esperar ele terminar)."""
    caminho = str(programa)
    args = list(argumentos or [])
    try:
        if sys.platform == "darwin" and caminho.endswith(".app"):
            subprocess.Popen(["open", "-a", caminho, *args])
        else:
            subprocess.Popen([caminho, *args])
    except FileNotFoundError as erro:
        raise ErroRPA(f"Programa não encontrado: {caminho}") from erro
    logger.success(f"Programa aberto: {caminho}")


def _abrir_com_padrao(caminho: str | Path) -> None:
    caminho = Path(caminho).expanduser().resolve()
    if not caminho.exists():
        raise ErroRPA(f"Caminho não encontrado: {caminho}")
    try:
        if os.name == "nt":
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(caminho)])
        else:
            subprocess.Popen(["xdg-open", str(caminho)])
    except OSError as erro:
        raise ErroRPA(f"Não foi possível abrir {caminho}: {erro}") from erro
    logger.success(f"Aberto com o programa padrão: {caminho}")


def abrir_pasta(caminho: str | Path) -> None:
    """Abre uma pasta no gerenciador de arquivos do sistema."""
    pasta = Path(caminho).expanduser()
    if not pasta.is_dir():
        raise ErroRPA(f"Pasta não encontrada: {pasta}")
    _abrir_com_padrao(pasta)


def abrir_arquivo(caminho: str | Path) -> None:
    """Abre um arquivo com o programa padrão do sistema."""
    arquivo = Path(caminho).expanduser()
    if not arquivo.is_file():
        raise ErroRPA(f"Arquivo não encontrado: {arquivo}")
    _abrir_com_padrao(arquivo)


def obter_variavel_ambiente(nome: str, padrao: str | None = None) -> str | None:
    """Lê uma variável de ambiente."""
    valor = os.getenv(nome, padrao)
    logger.info(f"Variável de ambiente {nome}: {'definida' if valor is not None else 'ausente'}")
    return valor


def definir_variavel_ambiente(nome: str, valor: str) -> None:
    """Define uma variável de ambiente para o processo atual (e filhos)."""
    os.environ[str(nome)] = str(valor)
    logger.success(f"Variável de ambiente definida: {nome}")


def obter_info_sistema() -> dict[str, str]:
    """Retorna informações úteis da máquina/ambiente de execução."""
    info = {
        "sistema": platform.system(),
        "plataforma": platform.platform(),
        "maquina": platform.node(),
        "python": platform.python_version(),
        "usuario": getpass.getuser(),
        "pasta_atual": str(Path.cwd()),
    }
    logger.info(f"Sistema: {info['sistema']} | Python {info['python']} | máquina {info['maquina']}")
    return info


def pasta_temporaria() -> Path:
    """Retorna a pasta temporária do sistema."""
    return Path(tempfile.gettempdir())


def esperar_arquivo(
    caminho: str | Path,
    tempo_max: int = 60,
    intervalo: float = 0.5,
) -> Path:
    """Aguarda um arquivo existir e devolve o caminho resolvido."""
    arquivo = Path(caminho)
    inicio = time.time()
    while time.time() - inicio < tempo_max:
        if arquivo.is_file():
            logger.success(f"Arquivo encontrado: {arquivo}")
            return arquivo.resolve()
        time.sleep(intervalo)
    raise ErroRPA(f"Arquivo não apareceu em {tempo_max}s: {arquivo}")


def esperar_pasta(
    caminho: str | Path,
    tempo_max: int = 60,
    intervalo: float = 0.5,
) -> Path:
    """Aguarda uma pasta existir e devolve o caminho resolvido."""
    pasta = Path(caminho)
    inicio = time.time()
    while time.time() - inicio < tempo_max:
        if pasta.is_dir():
            logger.success(f"Pasta encontrada: {pasta}")
            return pasta.resolve()
        time.sleep(intervalo)
    raise ErroRPA(f"Pasta não apareceu em {tempo_max}s: {pasta}")


def _escapar_applescript(texto: str) -> str:
    return str(texto).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def notificar_desktop(titulo: str, mensagem: str) -> None:
    """Mostra uma notificação nativa do sistema (macOS, Windows ou Linux)."""
    try:
        if sys.platform == "darwin":
            script = (
                f'display notification "{_escapar_applescript(mensagem)}" '
                f'with title "{_escapar_applescript(titulo)}"'
            )
            subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
        elif os.name == "nt":
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, str(mensagem), str(titulo), 0x40)
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", str(titulo), str(mensagem)], check=False)
        else:
            logger.warning(f"Notificação nativa indisponível: {titulo} - {mensagem}")
            return
    except OSError as erro:
        raise ErroRPA(f"Falha ao notificar no desktop: {erro}") from erro
    logger.success(f"Notificação enviada: {titulo}")


def tocar_som() -> None:
    """Toca um som curto de atenção no sistema."""
    if sys.platform == "darwin":
        subprocess.run(
            ["afplay", "/System/Library/Sounds/Glass.aiff"],
            check=False,
            capture_output=True,
        )
    elif os.name == "nt":
        import winsound

        winsound.MessageBeep()
    else:
        print("\a", end="", flush=True)
    logger.info("Som de atenção reproduzido.")


__all__ = [
    "executar_comando",
    "abrir_programa",
    "abrir_pasta",
    "abrir_arquivo",
    "obter_variavel_ambiente",
    "definir_variavel_ambiente",
    "obter_info_sistema",
    "pasta_temporaria",
    "esperar_arquivo",
    "esperar_pasta",
    "notificar_desktop",
    "tocar_som",
]
