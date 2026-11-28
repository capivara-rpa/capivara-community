"""Configurações centrais do projeto.

Todos os robôs leem os parâmetros deste módulo. Você pode editar os valores
diretamente aqui ou sobrescrevê-los via arquivo ``.env`` (recomendado para
senhas, tokens e valores diferentes entre máquinas).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from settings.ambiente import carregar_variaveis

carregar_variaveis()

# Quando o app roda empacotado (PyInstaller), não existe um "projeto" físico:
# os dados ficam num diretório configurável (RPA_PASTA_DADOS) para persistirem
# entre execuções do binário instalado.
_EMBALADO = bool(getattr(sys, "frozen", False))


def _como_bool(valor: str | None, padrao: bool = False) -> bool:
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


def _como_int(valor: str | None, padrao: int) -> int:
    if valor is None or not valor.strip().isdigit():
        return padrao
    return int(valor.strip())


# ----------------------------------------------------------------------
# Caminhos do projeto
# ----------------------------------------------------------------------
_RAIZ_ARQUIVO = Path(__file__).resolve().parents[1]
# Instalada via pip, a lib fica em site-packages; nesse caso os dados do
# usuário devem ficar no diretório atual, não dentro do site-packages.
_INSTALADO = any(parte in {"site-packages", "dist-packages"} for parte in _RAIZ_ARQUIVO.parts)
RAIZ_PROJETO = Path.cwd() if _INSTALADO else _RAIZ_ARQUIVO

# Em binários instalados, os dados (bancos, logs, vault) vão para RPA_PASTA_DADOS
# para não se perderem a cada execução extraída no _MEIPASS.
_PASTA_DADOS = os.getenv("RPA_PASTA_DADOS", "")
PASTA_DATA = Path(_PASTA_DADOS) if _PASTA_DADOS else RAIZ_PROJETO / "data"
PASTA_INPUT = PASTA_DATA / "input"
PASTA_OUTPUT = PASTA_DATA / "output"
PASTA_LOGS = PASTA_DATA / "logs"


def garantir_pastas() -> None:
    """Cria as pastas de dados sob demanda.

    Importar ``settings.parametros`` não deve criar ``data/``: a biblioteca
    pública pode ser usada só com funções puras. Quem executa o app, o logger
    ou um painel chama esta função quando precisa gravar algo.
    """
    for pasta in (PASTA_INPUT, PASTA_OUTPUT, PASTA_LOGS):
        pasta.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Ambiente de execução
# ----------------------------------------------------------------------
# dev  -> abre a janela do navegador (ideal para desenvolvimento)
# prod -> executa em modo headless (sem janela, ideal para servidores/Docker)
AMBIENTE = os.getenv("AMBIENTE", "dev").strip().lower()

# Se AMBIENTE == "prod", o navegador roda escondido por padrão
HEADLESS = _como_bool(os.getenv("HEADLESS"), AMBIENTE == "prod")

# Tempos (segundos)
TEMPO_ESPERA_PADRAO = _como_int(os.getenv("TEMPO_ESPERA_PADRAO"), 5)
TEMPO_TIMEOUT = _como_int(os.getenv("TEMPO_TIMEOUT"), 15)

# URL utilizada pelos robôs de exemplo
SITE_DEMO = os.getenv("SITE_DEMO", "https://www.google.com.br/")

# ----------------------------------------------------------------------
# Credenciais (sempre via .env, nunca hardcoded!)
# ----------------------------------------------------------------------
USUARIO = os.getenv("USUARIO", "")
SENHA = os.getenv("SENHA", "")

# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "")
API_TOKEN = os.getenv("API_TOKEN", "")

# ----------------------------------------------------------------------
# E-mail / SMTP
# ----------------------------------------------------------------------
SMTP_SERVIDOR = os.getenv("SMTP_SERVIDOR", "")
SMTP_PORTA = _como_int(os.getenv("SMTP_PORTA"), 465)
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
SMTP_SENHA = os.getenv("SMTP_SENHA", "")
SMTP_ORIGEM = os.getenv("SMTP_ORIGEM", "")

# ----------------------------------------------------------------------
# Logs
# ----------------------------------------------------------------------
NOME_LOG = os.getenv("NOME_LOG", "rpa.log")
NIVEL_LOG = os.getenv("NIVEL_LOG", "DEBUG").strip().upper()

# ----------------------------------------------------------------------
# Monitor / painel web de trace (core/monitor)
# ----------------------------------------------------------------------
# Banco SQLite onde ficam as execuções e o passo a passo dos robôs.
_caminho_banco = os.getenv("BANCO_MONITOR", "").strip()
BANCO_MONITOR = Path(_caminho_banco) if _caminho_banco else PASTA_DATA / "monitor.db"

# Porta do painel local (http://localhost:8765)
PORTA_MONITOR = _como_int(os.getenv("PORTA_MONITOR"), 8765)

# Host/interface do painel. Use 0.0.0.0 para aceitar conexões da rede local.
HOST_MONITOR = os.getenv("HOST_MONITOR", "127.0.0.1").strip()

# Abrir o navegador automaticamente ao subir o painel
ABRIR_PAINEL = _como_bool(os.getenv("ABRIR_PAINEL"), True)

# ----------------------------------------------------------------------
# Orquestrador / Lagoa (core/control_room)
# ----------------------------------------------------------------------
# Banco com máquinas, processos e jobs (separado do trace do monitor)
_caminho_orq = os.getenv("BANCO_ORQUESTRADOR", "").strip()
BANCO_ORQUESTRADOR = Path(_caminho_orq) if _caminho_orq else PASTA_DATA / "orquestrador.db"


def _env(*nomes: str, padrao: str = "") -> str:
    """Lê a primeira variável definida (nomes novos antes dos legados)."""
    for nome in nomes:
        valor = os.getenv(nome)
        if valor is not None and valor.strip():
            return valor.strip()
    return padrao


# Porta da Lagoa (serve também o painel de trace em /monitor/).
# LAGOA_* é o nome novo; CONTROL_ROOM_* continua aceito por compatibilidade.
PORTA_LAGOA = _como_int(_env("PORTA_LAGOA", "PORTA_CONTROL_ROOM"), 8765)
PORTA_CONTROL_ROOM = PORTA_LAGOA

# Host/interface da Lagoa. Use 0.0.0.0 para aceitar runners da rede local.
HOST_LAGOA = _env("HOST_LAGOA", "HOST_CONTROL_ROOM", padrao="127.0.0.1")
HOST_CONTROL_ROOM = HOST_LAGOA

# Segundos sem heartbeat até considerar uma máquina "offline"
SEGUNDOS_OFFLINE = _como_int(os.getenv("SEGUNDOS_OFFLINE"), 20)

# Intervalo (segundos) da verificação de agendamentos (triggers)
INTERVALO_TRIGGERS = _como_int(os.getenv("INTERVALO_TRIGGERS"), 15)

# Atualização automática das automações instaladas de repositório Git.
# A Lagoa consulta `git ls-remote` no intervalo abaixo e troca o código quando o
# commit da branch muda. Cada automação precisa estar marcada como auto-atualizável.
AUTO_ATUALIZAR = _como_bool(os.getenv("AUTO_ATUALIZAR"), True)
INTERVALO_ATUALIZACAO = max(30, _como_int(os.getenv("INTERVALO_ATUALIZACAO"), 300))

# URL da Lagoa usada pelos robôs/CLI para consumir vault e filas
LAGOA_URL = _env("LAGOA_URL", "CONTROL_ROOM_URL", padrao="http://127.0.0.1:8765").rstrip("/")
CONTROL_ROOM_URL = LAGOA_URL

# Token que os agentes enviam à Lagoa (cabeçalho Authorization: Bearer).
# Vazio = Lagoa aberta (ideal para dev/rede local). Defina para expor a
# Lagoa fora da rede confiável (VPN/hosted): todos os agentes precisam do
# mesmo token.
LAGOA_TOKEN = _env("LAGOA_TOKEN", "CONTROL_ROOM_TOKEN", padrao="")
CONTROL_ROOM_TOKEN = LAGOA_TOKEN

# Login/RBAC da Lagoa (interface web). O primeiro admin é criado na
# primeira subida com estas credenciais (troque a senha depois!).
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@rpa.local").strip()
ADMIN_SENHA = os.getenv("ADMIN_SENHA", "admin")

# Exigir login (sessão) para as ações do painel? Ligado por padrão (igual ao
# Cloud). Use LAGOA_AUTH=false apenas em laboratório isolado/sem rede.
LAGOA_AUTH = _como_bool(_env("LAGOA_AUTH", "CONTROL_ROOM_AUTH", padrao="true"), True)
CONTROL_ROOM_AUTH = LAGOA_AUTH

# Horas de validade de uma sessão de usuário
SESSAO_HORAS = _como_int(os.getenv("SESSAO_HORAS"), 12)

# Retenção da trilha de auditoria em dias (0 = nunca expurgar)
RETENCAO_AUDITORIA_DIAS = _como_int(os.getenv("RETENCAO_AUDITORIA_DIAS"), 90)

# SLA de execução: acima disso um job é "excedido" (e 75% disso = "lento")
LIMITE_JOB_SEGUNDOS = _como_int(os.getenv("LIMITE_JOB_SEGUNDOS"), 300)

# TLS (HTTPS) opcional para expor a Lagoa/monitor fora da rede local.
# Informe o certificado e a chave em PEM. Vazio = HTTP puro (dev/rede local).
TLS_CERT = os.getenv("TLS_CERT", "").strip()
TLS_CHAVE = os.getenv("TLS_CHAVE", "").strip()

# ----------------------------------------------------------------------
# Cofre de credenciais (vault) — segredos cifrados
# ----------------------------------------------------------------------
# Frase-senha usada para cifrar os segredos. Se vazia, o cofre gera e guarda
# uma chave local em ``data/vault.key`` (fora do Git). Em produção, defina no
# ``.env`` e mantenha a mesma chave em todas as máquinas que consomem o cofre.
VAULT_CHAVE = os.getenv("VAULT_CHAVE", "")

# Arquivo de chave local (usado só quando VAULT_CHAVE não está definida)
VAULT_ARQUIVO_CHAVE = PASTA_DATA / "vault.key"

# Guardar a chave do cofre no chaveiro do sistema (macOS Keychain, Windows
# Credential Manager, Secret Service no Linux) em vez do arquivo local. Requer
# o extra ``keyring`` (``pip install -e ".[keyring]"``). Ignorado quando
# ``VAULT_CHAVE`` está definida. Para um KMS/segredo externo, basta alimentar
# ``VAULT_CHAVE`` a partir dele.
VAULT_USAR_KEYRING = _como_bool(os.getenv("VAULT_USAR_KEYRING"), False)

# ----------------------------------------------------------------------
# Pacotes de robôs (.zip) enviados para a Lagoa
# ----------------------------------------------------------------------
# Pasta onde os pacotes enviados são extraídos e registrados automaticamente
# Pasta onde os robôs empacotados (.zip) são instalados
if _EMBALADO:
    PASTA_ROBOS = PASTA_DATA / "robos"
else:
    PASTA_ROBOS = Path(os.getenv("PASTA_ROBOS", "") or (RAIZ_PROJETO / "app" / "robos"))

# Quando verdadeiro, robôs publicados com um requirements.txt próprio ganham um
# ambiente isolado (.venv): o agente cria a venv, atualiza o pip, instala as
# dependências e executa o fluxo nesse ambiente. Desligue com
# RPA_INSTALAR_DEPENDENCIAS=false para sempre rodar no ambiente do agente.
INSTALAR_DEPENDENCIAS = _como_bool(os.getenv("RPA_INSTALAR_DEPENDENCIAS"), True)