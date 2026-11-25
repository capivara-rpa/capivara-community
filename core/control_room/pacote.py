"""Pacote de robô em .zip (padrão estilo BotCity) com manifesto ``rpa.json``.

Um robô pode ser empacotado e enviado para a Lagoa, que o instala
em ``app/robos/<nome>/`` e o cadastra no catálogo de processos — sem precisar
editar o projeto manualmente.

Estrutura esperada do .zip::

    meu_robo/
      rpa.json        → manifesto (obrigatório)
      main.py         → arquivo com a função que executa o robô
      ...             → quaisquer outros arquivos (deps, templates, etc.)

Exemplo de ``rpa.json``::

    {
      "nome": "cliente_mock",
      "versao": "1.0.0",
      "descricao": "Gera a planilha de clientes de exemplo.",
      "entrada": "main.py",
      "funcao": "rodar",
      "usa_navegador": false
    }

Uso::

    python -m core.control_room.pacote empacotar minha_pasta_robo/
    python -m core.control_room.pacote empacotar minha_pasta_robo/ --saida meu_robo.zip --senha "srcta"
    python -m core.control_room.pacote instalar meu_robo.zip             # instala numa Lagoa
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import re
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

import pyzipper
import requests
from loguru import logger

from core.control_room import servico
from settings.parametros import LAGOA_URL, PASTA_ROBOS

NOME_VALIDO = re.compile(r"^[a-z0-9_-]+$")

MANIFESTO = "rpa.json"

# Esquemas aceitos para clonar robôs de repositórios Git:
# - https:// públicos (uso normal);
# - http:// em localhost/127.0.0.1 (dev/CI e servidores git internos na própria
#   máquina — não sai da máquina, então não enfraquece a segurança).
# Barra `file://`, `ssh://` e caminhos locais para evitar leitura arbitrária do
# disco e comandos de transporte não previstos.
_GIT_URL = re.compile(r"^https://[^\s]+$", re.IGNORECASE)
_GIT_URL_LOCAL = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?/[^\s]+$", re.IGNORECASE)
_GIT_REF = re.compile(r"^[A-Za-z0-9._/\-]+$")
_CLONE_TIMEOUT = 120


# ----------------------------------------------------------------------
# Manifesto
# ----------------------------------------------------------------------
def _carregar_manifesto(raiz: Path) -> dict[str, Any]:
    arquivo = raiz / MANIFESTO
    if not arquivo.is_file():
        raise ValueError(f"Manifesto '{MANIFESTO}' não encontrado em {raiz}.")
    manifest = json.loads(arquivo.read_text(encoding="utf-8"))
    obrigatorios = ("nome", "entrada", "funcao")
    faltando = [c for c in obrigatorios if not manifest.get(c)]
    if faltando:
        raise ValueError(f"Manifesto incompleto: faltou {'/'.join(faltando)}.")
    nome = str(manifest["nome"]).strip().lower()
    if not NOME_VALIDO.match(nome):
        raise ValueError("O 'nome' do robô só pode ter letras minúsculas, números, '_' e '-'.")
    manifest["nome"] = nome
    manifest.setdefault("versao", "1.0.0")
    manifest.setdefault("descricao", "")
    return manifest


def _validar_entrada(pasta: Path, manifest: dict[str, Any]) -> None:
    entrada = pasta / str(manifest["entrada"])
    if not entrada.is_file():
        raise ValueError(f"Arquivo de entrada '{manifest['entrada']}' não existe em {pasta}.")


# ----------------------------------------------------------------------
# Empacotar
# ----------------------------------------------------------------------
def empacotar(
    pasta: str,
    destino: str | None = None,
    senha: str | None = None,
) -> Path:
    """Compacta uma pasta de robô em um .zip com manifesto validado.

    Se ``senha`` for informada, o .zip é criptografado (AES/256 via pyzipper).
    """
    raiz = Path(pasta)
    if not raiz.is_dir():
        raise ValueError(f"Pasta não encontrada: {raiz}")

    manifest = _carregar_manifesto(raiz)
    _validar_entrada(raiz, manifest)

    caminho_destino = Path(destino) if destino else raiz.with_name(f"{manifest['nome']}.zip")
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)

    with pyzipper.AESZipFile(str(caminho_destino), "w") as zipado:
        if senha:
            zipado.setpassword(senha.encode("utf-8"))
            zipado.setencryption(pyzipper.WZ_AES, nbits=256)
        for arquivo in sorted(raiz.rglob("*")):
            if arquivo.is_dir():
                continue
            zipado.write(arquivo, arquivo.relative_to(raiz))

    logger.success(f"[pacote] '{manifest['nome']}' v{manifest['versao']} → {caminho_destino}")
    return caminho_destino


# ----------------------------------------------------------------------
# Instalar
# ----------------------------------------------------------------------
def _membro_inseguro(nome: str) -> bool:
    if nome.startswith(("/", "\\")):
        return True
    partes = nome.replace("\\", "/").split("/")
    return ".." in partes


def _raiz_do_zip(membros: list[zipfile.ZipInfo]) -> Path:
    """Caminho da pasta raiz comum dos membros (vazio se os arquivos estão na raiz)."""
    nomes = [m.filename.replace("\\", "/") for m in membros]
    primeiros = {n.split("/", 1)[0] for n in nomes}
    if len(primeiros) == 1:
        return Path(primeiros.pop())
    return Path("")


def instalar_zip(
    arquivo: str | bytes,
    senha: str | None = None,
    pasta_robos: str | None = None,
) -> dict[str, Any]:
    """Instala um .zip de robô e o cadastra no catálogo de processos."""
    dados = arquivo if isinstance(arquivo, bytes) else Path(arquivo).read_bytes()
    destino_base = Path(pasta_robos or PASTA_ROBOS)

    try:
        zipado_aberto = pyzipper.AESZipFile(io.BytesIO(dados), "r")
    except (zipfile.BadZipFile, OSError) as erro:
        raise ValueError("Arquivo inválido: envie um .zip (não um .rar/.7z nem a pasta solta).") from erro

    with zipado_aberto as zipado:
        if senha:
            zipado.setpassword(senha.encode("utf-8"))
        membros = [z for z in zipado.infolist() if not z.is_dir() and not _membro_inseguro(z.filename)]
        if not membros:
            raise ValueError("Zip vazio ou com caminhos inseguros.")

        raiz_zip = _raiz_do_zip(membros)

        def _extrair_manifesto(zipado: zipfile.ZipFile) -> dict[str, Any]:
            caminho = f"{raiz_zip / MANIFESTO}" if raiz_zip.parts else MANIFESTO
            try:
                info = zipado.getinfo(caminho)
            except KeyError as erro:
                raise ValueError(
                    f"Manifesto '{MANIFESTO}' não encontrado no .zip (procurei por '{caminho}'). "
                    "Inclua um arquivo rpa.json na raiz do robô — veja o modelo em GUIA.md."
                ) from erro
            return json.loads(zipado.read(info).decode("utf-8"))

        manifest = _extrair_manifesto(zipado)
        nome = str(manifest["nome"]).strip().lower()
        if not NOME_VALIDO.match(nome):
            raise ValueError(f"Nome de robô inválido no manifesto: {nome!r}")
        if manifest.get("entrada") and "\\" in str(manifest["entrada"]) or ".." in str(manifest.get("entrada", "")):
            raise ValueError("'entrada' do manifesto não pode apontar para fora da pasta.")

        destino_robo = destino_base / nome
        if destino_robo.exists():
            raise ValueError(f"Robô '{nome}' já instalado. Remova app/robos/{nome} para reinstalar.")

        destino_robo.mkdir(parents=True)
        for zipinfo in membros:
            relativo = zipinfo.filename.replace("\\", "/")
            if raiz_zip.parts:
                prefixo = f"{raiz_zip.parts[0]}/"
                if not relativo.startswith(prefixo):
                    raise ValueError(f"Membro fora da pasta do robô: {zipinfo.filename!r}")
                relativo = relativo.removeprefix(prefixo)
            destino_arquivo = destino_robo / relativo
            destino_arquivo.parent.mkdir(parents=True, exist_ok=True)
            destino_arquivo.write_bytes(zipado.read(zipinfo))

        _validar_entrada(destino_robo, manifest)
        _garantir_importavel(destino_base)
        processo = servico.criar_processo(
            nome=nome,
            descricao=str(manifest.get("descricao") or ""),
            fluxo=_fluxo_do_pacote(nome, manifest),
            usa_navegador=bool(manifest.get("usa_navegador", False)),
        )

    logger.success(f"[pacote] robô '{nome}' v{manifest.get('versao', '')} instalado em {destino_robo}")
    return {"nome": nome, "versao": manifest.get("versao", ""), "pasta": str(destino_robo), "processo": processo}


def _fluxo_do_pacote(nome: str, manifest: dict[str, Any]) -> str:
    relativo = Path(str(manifest["entrada"]).replace("\\", "/")).with_suffix("")
    modulo = ".".join(parte for parte in relativo.parts if parte not in ("", "."))
    return f"app.robos.{nome}.{modulo}:{manifest['funcao']}"


# ----------------------------------------------------------------------
# Git (repositórios públicos)
# ----------------------------------------------------------------------
def _validar_url_git(url: str) -> str:
    url = str(url or "").strip()
    if not (_GIT_URL.match(url) or _GIT_URL_LOCAL.match(url)):
        raise ValueError(
            "URL de repositório inválida. Use uma URL HTTPS pública, "
            "por exemplo: https://github.com/usuario/meu-robo.git"
        )
    return url


def _validar_ref(ref: str | None) -> str | None:
    ref = (ref or "").strip()
    if not ref:
        return None
    if not _GIT_REF.match(ref) or ref.startswith("-") or ".." in ref:
        raise ValueError("Branch/tag inválido. Use letras, números, '.', '_', '-' e '/'.")
    return ref


def _clonar(url: str, ref: str | None, destino: Path) -> None:
    """Clona um repositório público (shallow quando possível) numa pasta temporária."""
    if shutil.which("git") is None:
        raise ValueError(
            "O comando 'git' não está instalado nesta máquina. "
            "Instale o Git para usar automações por repositório."
        )
    ambiente = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
        "HOME": os.environ.get("HOME", str(destino)),
        # nunca abrir prompt interativo (repo privado/inexistente falha rápido)
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
        "GIT_LFS_SKIP_SMUDGE": "1",
    }

    def _executar(comando: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            comando, capture_output=True, text=True, timeout=_CLONE_TIMEOUT, env=ambiente
        )

    def _montar(profundidade: bool) -> list[str]:
        comando = ["git", "clone"]
        if profundidade:
            comando += ["--depth", "1"]
        if ref:
            comando += ["--branch", ref]
        return comando + ["--", url, str(destino)]

    logger.info(f"[pacote] clonando {url}{f' (ref {ref})' if ref else ''}")
    processo = _executar(_montar(profundidade=True))
    # servidores "dumb http" não suportam clone shallow: refaz completo
    if processo.returncode != 0 and "shallow" in (processo.stderr or "").lower():
        shutil.rmtree(destino, ignore_errors=True)
        processo = _executar(_montar(profundidade=False))

    if processo.returncode != 0:
        detalhe = (processo.stderr or processo.stdout or "").strip().splitlines()
        resumo = detalhe[-1] if detalhe else "erro desconhecido"
        raise ValueError(
            f"Não foi possível clonar o repositório. Confira se a URL é pública "
            f"e se o branch/tag existe. ({resumo})"
        )


def _ambiente_git(destino: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
        "HOME": os.environ.get("HOME", str(destino)),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
        "GIT_LFS_SKIP_SMUDGE": "1",
    }


def sha_remoto(url: str, ref: str | None = None) -> str:
    """Retorna o SHA do commit no topo da branch/tag remota (``git ls-remote``)."""
    url = _validar_url_git(url)
    ref = _validar_ref(ref)
    if shutil.which("git") is None:
        raise ValueError(
            "O comando 'git' não está instalado nesta máquina. "
            "Instale o Git para atualizar automações por repositório."
        )
    referencia = f"refs/heads/{ref}" if ref else "HEAD"
    processo = subprocess.run(
        ["git", "ls-remote", url, referencia],
        capture_output=True,
        text=True,
        timeout=_CLONE_TIMEOUT,
        env=_ambiente_git(Path(os.getcwd())),
    )
    if processo.returncode != 0:
        detalhe = (processo.stderr or "").strip().splitlines()
        resumo = detalhe[-1] if detalhe else "erro desconhecido"
        raise ValueError(f"Não foi possível consultar o repositório. ({resumo})")
    linhas = [linha for linha in processo.stdout.splitlines() if linha.strip()]
    if not linhas:
        raise ValueError(f"Branch/tag '{ref or 'padrão'}' não encontrada no repositório.")
    return linhas[0].split()[0].strip()


def _sha_local(repo: Path) -> str | None:
    """SHA do commit já clonado (evita um segundo acesso à rede)."""
    processo = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=_CLONE_TIMEOUT,
        env=_ambiente_git(repo),
    )
    if processo.returncode != 0:
        return None
    return processo.stdout.strip() or None


def _instalar_do_diretorio(
    origem_pasta: Path,
    destino_base: Path,
    origem: str | None = None,
    origem_ref: str | None = None,
    substituir: bool = False,
    commit_sha: str | None = None,
) -> dict[str, Any]:
    """Valida o manifesto de uma pasta de robô, instala e cadastra o processo."""
    manifest = _carregar_manifesto(origem_pasta)
    _validar_entrada(origem_pasta, manifest)
    nome = str(manifest["nome"]).strip().lower()

    destino_base.mkdir(parents=True, exist_ok=True)
    destino_robo = destino_base / nome
    if destino_robo.exists() and not substituir:
        raise ValueError(
            f"Robô '{nome}' já instalado. Use 'Atualizar' ou remova app/robos/{nome}."
        )

    # Troca atômica: tudo acontece dentro de PASTA_ROBOS (mesmo volume), então
    # rename não cruza dispositivos. Um job em execução continua lendo a pasta
    # antiga até terminar; o próximo já pega a nova.
    sufixo = uuid.uuid4().hex[:12]
    staging = destino_base / f".rpa-novo-{nome}-{sufixo}"
    backup = destino_base / f".rpa-antigo-{nome}-{sufixo}"
    venv_guardado = destino_base / f".rpa-venv-{nome}-{sufixo}"
    try:
        shutil.copytree(origem_pasta, staging)
        git_dir = staging / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir, ignore_errors=True)

        if destino_robo.exists():
            venv_atual = destino_robo / ".venv"
            if venv_atual.exists():
                venv_atual.rename(venv_guardado)
            destino_robo.rename(backup)
        staging.rename(destino_robo)
        if venv_guardado.exists():
            venv_guardado.rename(destino_robo / ".venv")
    except BaseException:
        if backup.exists() and not destino_robo.exists():
            backup.rename(destino_robo)
        if venv_guardado.exists():
            destino = destino_robo / ".venv"
            if destino.exists():
                shutil.rmtree(destino, ignore_errors=True)
            venv_guardado.rename(destino)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
        shutil.rmtree(venv_guardado, ignore_errors=True)

    _garantir_importavel(destino_base)
    processo = servico.criar_processo(
        nome=nome,
        descricao=str(manifest.get("descricao") or ""),
        fluxo=_fluxo_do_pacote(nome, manifest),
        usa_navegador=bool(manifest.get("usa_navegador", False)),
        origem=origem,
        origem_ref=origem_ref,
        commit_sha=commit_sha,
    )
    logger.success(f"[pacote] robô '{nome}' v{manifest.get('versao', '')} instalado em {destino_robo}")
    return {
        "nome": nome,
        "versao": manifest.get("versao", ""),
        "pasta": str(destino_robo),
        "processo": processo,
        "origem": origem,
        "origem_ref": origem_ref,
        "commit_sha": commit_sha,
    }


def instalar_git(
    url: str,
    ref: str | None = None,
    pasta_robos: str | None = None,
) -> dict[str, Any]:
    """Instala um robô a partir de um repositório Git público (via ``git clone``)."""
    url = _validar_url_git(url)
    ref = _validar_ref(ref)
    destino_base = Path(pasta_robos or PASTA_ROBOS)
    with tempfile.TemporaryDirectory(prefix="rpa-git-") as tmp:
        clonado = Path(tmp) / "repo"
        _clonar(url, ref, clonado)
        # se o repo tiver uma subpasta com rpa.json na raiz, usa a raiz
        return _instalar_do_diretorio(
            clonado,
            destino_base,
            origem=url,
            origem_ref=ref,
            commit_sha=_sha_local(clonado),
        )


def atualizar_git(
    url: str,
    ref: str | None = None,
    pasta_robos: str | None = None,
) -> dict[str, Any]:
    """Atualiza um robô já instalado: clona de novo e substitui a versão em uso."""
    url = _validar_url_git(url)
    ref = _validar_ref(ref)
    destino_base = Path(pasta_robos or PASTA_ROBOS)
    with tempfile.TemporaryDirectory(prefix="rpa-git-") as tmp:
        clonado = Path(tmp) / "repo"
        _clonar(url, ref, clonado)
        return _instalar_do_diretorio(
            clonado,
            destino_base,
            origem=url,
            origem_ref=ref,
            substituir=True,
            commit_sha=_sha_local(clonado),
        )


def _garantir_importavel(pasta_robos: Path) -> None:
    """Cria o __init__.py do pacote 'app.robos' para o resolver importar módulos."""
    if not (pasta_robos / "__init__.py").exists():
        (pasta_robos / "__init__.py").write_text("", encoding="utf-8")


def remover(nome: str, pasta_robos: str | None = None) -> dict[str, Any]:
    """Desinstala um robô: apaga os arquivos e o remove do catálogo de processos."""
    nome = str(nome or "").strip().lower()
    if not NOME_VALIDO.match(nome):
        raise ValueError("Nome de robô inválido.")
    destino = Path(pasta_robos or PASTA_ROBOS) / nome
    processo = next((p for p in servico.listar_processos() if p["nome"] == nome), None)
    if not destino.exists() and processo is None:
        raise ValueError(f"Robô '{nome}' não encontrado.")

    if destino.exists():
        shutil.rmtree(destino)
    if processo is not None:
        servico.apagar_processo(int(processo["id"]))

    logger.success(f"[pacote] robô '{nome}' removido")
    return {"nome": nome, "pasta": str(destino), "removido": True}


# ----------------------------------------------------------------------
# Enviar para uma Lagoa
# ----------------------------------------------------------------------
def _enviar(
    arquivo: str | bytes,
    control_room: str | None = None,
    senha: str | None = None,
) -> dict[str, Any]:
    base = (control_room or LAGOA_URL).rstrip("/")
    dados = arquivo if isinstance(arquivo, bytes) else Path(arquivo).read_bytes()
    url = f"{base}/api/orq/pacotes"
    if senha:
        url += f"?senha={senha}"
    resposta = requests.post(
        url,
        data=dados,
        headers={"Content-Type": "application/zip"},
        timeout=60,
    )
    if resposta.status_code >= 400:
        raise RuntimeError(f"Falha ao enviar pacote: {resposta.status_code} {resposta.text}")
    return resposta.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Empacota, instala .zip ou instala de um repo Git.")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub_emp = sub.add_parser("empacotar", help="Cria o .zip a partir de uma pasta")
    sub_emp.add_argument("pasta", help="Pasta do robô (com rpa.json)")
    sub_emp.add_argument("--saida", help="Caminho do .zip gerado (default: <pasta>/<nome>.zip)")
    sub_emp.add_argument("--senha", help="Criptografa o .zip com esta senha")

    sub_inst = sub.add_parser("instalar", help="Instala um .zip numa Lagoa")
    sub_inst.add_argument("arquivo", help="Caminho do .zip")
    sub_inst.add_argument(
        "--lagoa",
        "--control-room",
        dest="control_room",
        metavar="URL",
        default=LAGOA_URL,
        help="URL da Lagoa",
    )
    sub_inst.add_argument("--senha", help="Senha do .zip (se criptografado)")

    sub_git = sub.add_parser("instalar-git", help="Instala um robô de um repositório Git público")
    sub_git.add_argument("url", help="URL HTTPS do repositório (público)")
    sub_git.add_argument("--ref", help="Branch ou tag (default: branch padrão)")
    sub_git.add_argument("--pasta-robos", help="Onde instalar (default: app/robos)")

    opcoes = parser.parse_args()
    if opcoes.comando == "empacotar":
        empacotar(opcoes.pasta, opcoes.saida, opcoes.senha)
    elif opcoes.comando == "instalar":
        resultado = _enviar(opcoes.arquivo, opcoes.control_room, opcoes.senha)
        logger.success(f"Robô '{resultado['nome']}' instalado via Lagoa.")
    elif opcoes.comando == "instalar-git":
        resultado = instalar_git(opcoes.url, ref=opcoes.ref, pasta_robos=opcoes.pasta_robos)
        logger.success(f"Robô '{resultado['nome']}' instalado de {opcoes.url}.")
    else:
        parser.print_help()
        sys.exit(1)


__all__ = [
    "empacotar",
    "instalar_zip",
    "instalar_git",
    "atualizar_git",
    "remover",
    "_enviar",
    "main",
]


if __name__ == "__main__":
    main()