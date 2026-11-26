# Capivara 🦫 — RPA em Python, 100% em português

**Deixa que a Capivara faz.** Um **template low-code de RPA** feito para a
comunidade Python — do dev que nunca abriu um Python até o dev sênior que precisa
de um atalho produtivo. As bibliotecas complexas (Selenium, pandas, requests...)
viraram **funções em português** e todo o processo aparece **colorido no terminal**.

```text
🗃️ Web:   navegador.abrir_url(...)
         navegador.escrever_texto(...)
         navegador.clicar_elemento(...)

📊 Dados: ler_csv(...) -> filtrar_linhas(...) -> escrever_excel(...)

📦 ARQ:   listar_arquivos(...) · baixar_arquivo(...) · extrair_zip(...)

🌐 API:   api_get(...) · api_post(...) · api_upload(...) · api_download(...)

✉️ Email: enviar_email(...) · enviar_email_html(...)

🧰 Útil:  validar_cpf(...) · gerar_senha(...) · notificacoes.enviar_slack(...)
```

> **Espaço da comunidade:** este é um **snapshot funcional** da versão oficial,
> mantido para testar ideias, RFCs e exemplos propostos pela comunidade. A versão
> **estável** continua em
> [`capivara-rpa/capivara`](https://github.com/capivara-rpa/capivara); o que for
> aceito aqui segue para a branch `next` da oficial antes do release.

## Como usar este snapshot

- O código da oficial está presente aqui para você rodar, testar e propor mudanças.
- Use [`CONTRIBUTING.md`](CONTRIBUTING.md), [`GOVERNANCA.md`](GOVERNANCA.md),
  [`ideias/`](ideias/) e [`exemplos/`](exemplos/) para avaliar propostas.
- Para produção, prefira o repo oficial ou `pip install capivara-rpa`.
- A sincronização com a oficial preserva `exemplos/`, `ideias/` e os documentos de
  governança deste repositório.

---

## 📖 Índice

1. [Para quem é este template](#para-quem-é-este-template)
2. [Tecnologias](#tecnologias)
3. [Estrutura de pastas](#estrutura-de-pastas)
4. [Pré-requisitos](#pré-requisitos)
5. [Instalação](#instalação)
6. [Como executar](#como-executar)
7. [Configuração (.env)](#configuração-env)
8. [Criando seu primeiro robô](#criando-seu-primeiro-robô)
9. [Utilidades prontas (+50 funções)](#utilidades-prontas-50-funções)
10. [Modo dev vs prod (headless)](#modo-dev-vs-prod-headless)
11. [Rodando no Docker](#rodando-no-docker)
12. [Lagoa (orquestrador)](#lagoa-orquestrador)
13. [Monitor de execuções (trace)](#monitor-de-execuções-trace)
14. [Testes automatizados](#testes-automatizados)
15. [Dicas para a comunidade](#dicas-para-a-comunidade)
16. [Documentação complementar](#documentação-complementar)

---

## Para quem é este template

| Perfil | O que encontra aqui |
|---|---|
| **Entusiasta / iniciante** | Tutorial do zero abaixo + funções prontas em português. Não precisa decorar Selenium. |
| **Dev Pleno** | Motor `core/` pronto para produção: logs, retry, headless, `.env`, Docker. |
| **Dev Sênior / Especialista** | Arquitetura leve, tudo extensível em `core/`, sem mágica obscura. |

---

## Tecnologias

- **Python 3.11+**
- **Selenium 4** (automação web) + **Selenium Manager** (driver automático — não precisa instalar ChromeDriver)
- **pandas + openpyxl** (planilhas)
- **requests** (APIs)
- **Loguru + rich** (logs coloridos e tabelas bonitas no terminal)
- **python-dotenv** (configurações e segredos)

---

## Estrutura de pastas

```text
capivara/
├── app/                    # 🔌 Componentes da aplicação (o SEU robô)
│   ├── main.py             #    Ponto de entrada / orquestrador
│   └── fluxos/             #    Cada tarefa de negócio em um arquivo
├── capivara_rpa/           # 📚 Fachada pública da biblioteca (pip install capivara-rpa)
├── core/                   # ⚙️ Motor low-code reutilizável
│   ├── rpa/                #    browser · dados · arquivo · api · email · banco
│   │                       #    texto · validacao · seguranca · sistema · notificacoes
│   ├── monitor/            #    Painel de trace das execuções (SQLite + web local)
│   ├── control_room/       #    Lagoa: máquinas, processos, jobs e agente
│   ├── logger.py           #    Logging colorido (Loguru)
│   ├── robo.py             #    Orquestrador dos fluxos
│   └── tratador.py         #    @passo, @tentar_novamente e exceções
├── settings/               # 🎛️ Configurações do projeto
│   ├── parametros.py       #    Parâmetros centrais (dev/prod, tempos, paths)
│   ├── ambiente.py         #    Carrega variáveis do .env
│   └── .env.example        #    Modelo de configuração
├── data/                   # 📁 Documentação e insumos
│   ├── docs/               #    Guias e arquitetura
│   ├── input/              #    Arquivos de entrada dos robôs
│   ├── output/             #    Resultados gerados
│   └── logs/               #    Logs do robô (rotação automática)
├── scripts/                # 🛠️ Helpers: install, run, monitor, lagoa
├── .env.example
├── .gitignore
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

> Regra de bolso: **`app/` é do seu robô, `core/` é do motor.**
> Você muda `app/` e `settings/`; o `core/` já vem pronto.

---

## Pré-requisitos

- **Python 3.11+** ([python.org](https://www.python.org/downloads/))
- **Google Chrome** instalado
- (Opcional) **Docker** para rodar em servidor

O ChromeDriver é baixado automaticamente pelo Selenium Manager na primeira execução.

---

## Instalação

### Opção rápida (scripts)

```bash
# Linux / macOS
bash scripts/install.sh

# Windows
scripts\install.bat
```

### Passo a passo manual

```bash
# 1. Acesse a raiz do projeto
cd capivara

# 2. Crie um ambiente virtual isolado
python -m venv .venv

# 3. Ative-o
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 4. Instale as dependências
pip install -r requirements.txt

# 5. (Opcional) crie o arquivo de configuração
cp .env.example .env
```

> 💡 **Windows**: use `py -m venv .venv` se `python` não existir no PATH.

### Usar como biblioteca (PyPI)

A distribuição pública é **`capivara-rpa`** (import `capivara_rpa`, CLI
`capivara`):

```bash
pip install capivara-rpa              # base: texto, validação, API, arquivos...
pip install "capivara-rpa[web]"       # + Selenium/Navegador
pip install "capivara-rpa[all]"       # kit completo (web + dados + cofre + filas)
```

```python
from capivara_rpa import texto, validacao

texto.slug("Relatório de Clientes 2026")   # 'relatorio-de-clientes-2026'
validacao.validar_cpf("529.982.247-25")    # True
```

Para automação web:

```python
from capivara_rpa import Navegador

with Navegador() as navegador:
    navegador.abrir_url("https://exemplo.com.br")
    navegador.escrever_texto("#busca", "Capivara")
    navegador.clicar_elemento("button[type=submit]")
```

Instale só o que precisar com os extras: `web` (Selenium), `dados` (pandas),
`cofre` (criptografia), `pacotes` (zip com senha), `interacao` (pyperclip),
`lagoa` (orquestrador de robôs), `all` ou `keyring`. O import da raiz é lazy: quem usa apenas
`texto`/`validacao` não carrega Selenium nem pandas.

---

## Como executar

```bash
# Roda TODOS os fluxos de exemplo
python app/main.py

# Roda só um fluxo
python app/main.py --web          # navegador (Google)
python app/main.py --dados        # pandas (planilha)

# Ou via script
bash scripts/run.sh               # Linux / macOS
scripts\run.bat --dados           # Windows
```

Você verá algo assim no terminal:

```text
10:47:07.646 | DEBUG    | Logger configurado para o processo 'capivara'. Arquivo: ...
━━━━━━━━━━━━━━━━━━━━━━━━━
  Capivara 🦫 — Deixa que a Capivara faz.
━━━━━━━━━━━━━━━━━━━━━━━━━
10:47:12.747 | SUCCESS  | Filtro aplicado: 5 de 10 linhas
10:47:13.628 | SUCCESS  | Planilha com 3 abas salva: data/output/relatorio_clientes.xlsx
10:47:13.634 | SUCCESS  | ✓ Fluxo concluído com sucesso: Tratamento de dados (pandas)
```

---

## Configuração (.env)

Copie `.env.example` para `.env` e ajuste:

```dotenv
AMBIENTE=dev                 # dev (janela) | prod (headless)
HEADLESS=false
SITE_DEMO=https://www.google.com.br/
USUARIO=
SENHA=
API_BASE_URL=
API_TOKEN=
SMTP_SERVIDOR=
SMTP_PORTA=465
SMTP_USUARIO=
SMTP_SENHA=
SMTP_ORIGEM=
NOME_LOG=rpa.log
```

> 🔒 **Nunca commite o arquivo `.env`** (ele está no `.gitignore`). Credenciais
> sempre por variável de ambiente, nunca hardcoded no código.

---

## Criando seu primeiro robô

1. Crie um arquivo em `app/fluxos/`, ex.: `app/fluxos/meu_fluxo.py`:

```python
"""Meu primeiro fluxo: preencher um formulário."""
from settings.parametros import SITE_DEMO


def preencher_formulario(navegador) -> bool:
    navegador.abrir_url(SITE_DEMO)
    navegador.escrever_texto("#nome", "Fulano de Tal")
    navegador.escrever_texto("#email", "fulano@exemplo.com")
    navegador.selecionar_opcao("#estado", valor="SP")
    navegador.marcar_checkbox("#termos", marcar=True)
    navegador.clicar_elemento("//button[@type='submit']")
    navegador.capturar_tela("formulario_enviado")
    return True
```

2. Registre o fluxo em `app/main.py`:

```python
FLUXOS = {
    "web": ("Busca no Google (navegador)", buscar_no_google),
    "dados": ("Tratamento de dados (pandas)", tratar_planilha),
    "form": ("Preencher formulário", preencher_formulario),  # 👈 novo
}
```

3. Execute:

```bash
python app/main.py --form
```

Pronto: o robô abre o site, preenche, mostra **cada passo colorido no terminal**
e salva prints em `data/output/`. Isso é RPA low-code na prática.

---

## Utilidades prontas (+50 funções)

Além do navegador e das planilhas, o motor ganhou módulos para o dia a dia do
robô. Tudo em português, com log automático e sem dependência nova:

| Módulo | Arquivo | O que resolve |
|---|---|---|
| `texto` | `core/rpa/texto.py` | limpar, normalizar, slug, extrair e-mails/URLs/números, regex, similaridade |
| `validacao` | `core/rpa/validacao.py` | CPF/CNPJ (validar, formatar, gerar), CEP, telefone, e-mail, datas úteis e moeda BR |
| `banco` | `core/rpa/banco.py` | SQLite: conectar, consultar, inserir/atualizar/apagar, DataFrame, importar/exportar CSV |
| `seguranca` | `core/rpa/seguranca.py` | senha/token, SHA-256, Base64, Fernet (criptografia), máscara e comparação segura |
| `sistema` | `core/rpa/sistema.py` | executar comandos, abrir pastas/arquivos, esperar arquivo, variáveis de ambiente e notificação desktop |
| `notificacoes` | `core/rpa/notificacoes.py` | webhooks para Slack, Teams, Discord, Telegram e webhook genérico |
| `arquivo` | `core/rpa/arquivo.py` | + JSON/INI, hash, comparar, últimas linhas, juntar/dividir e tamanho |
| `dados` | `core/rpa/dados.py` | + renomear, deduplicar, preencher, ordenar, pivotar, melt, Markdown e percentual |
| `api` | `core/rpa/api.py` | + PATCH/HEAD, upload multipart e download para arquivo |
| `email` | `core/rpa/email.py` | + HTML, CC/BCC, Reply-To e teste de SMTP |
| `Navegador` | `core/rpa/browser.py` | + texto/HTML da página, tabelas, cookies, abas, alertas, JS e captura de elemento |
| `tracktab` | `core/rpa/tracktab.py` | + buscar/obter seletor, listar, CSV, resumo e combinar exports |

```python
from core.rpa import banco, notificacoes, seguranca, texto, validacao

texto.slug("Relatório de Clientes 2026")        # 'relatorio-de-clientes-2026'
validacao.validar_cpf("529.982.247-25")         # True
seguranca.gerar_senha(20)                       # senha forte
notificacoes.enviar_slack(webhook, "Robô terminou!")

con = banco.conectar("data/input/dados.db")
banco.consultar(con, "SELECT * FROM clientes WHERE uf = ?", ("SP",))
```

> A lista completa, com assinaturas e exemplos, está em
> [`data/docs/CATALOGO_FUNCOES.md`](data/docs/CATALOGO_FUNCOES.md).

---

## Modo dev vs prod (headless)

| Ambiente | Janela do navegador | Uso típico |
|---|---|---|
| `AMBIENTE=dev` (padrão) | ✅ Visível | Desenvolvimento e debug |
| `AMBIENTE=prod` | ❌ Oculta (headless) | Servidor, agendador, Docker |

Mude o ambiente com o `.env` ou variável de ambiente:

```bash
AMBIENTE=prod python app/main.py
```

---

## Rodando no Docker

```bash
docker build -t meurobo .
docker run --rm meurobo
```

O Dockerfile já instala o Chrome, roda em headless (`AMBIENTE=prod`) e os
resultados ficam em `data/output/` dentro do container.

> 💡 Para pegar os arquivos gerados, monte um volume:
> `docker run --rm -v "$PWD/data/output:/app/data/output" meurobo`

---

## Lagoa (orquestrador)

Um **orquestrador de robôs**: um painel online onde você cadastra
**máquinas**, mantém um catálogo de **processos** (seus robôs) e **dispara jobs**
em máquinas específicas. Os **agentes** (as capivaras) instalados em cada máquina fazem o
heartbeat, buscam os jobs e devolvem o resultado — que vira uma *trace* no
painel de monitoramento.

```text
   Lagoa (servidor)                 Agente (em cada máquina)
  ┌────────────────────────┐   jobs     ┌──────────────────────────┐
  │ máquinas · processos   │ ─────────► │ registra · heartbeat     │
  │ jobs · disparo         │ ◄───────── │ executa fluxo · resultado│
  └────────────────────────┘  heartbeat └──────────────────────────┘
```

Tudo com **SQLite + biblioteca padrão** (o agente usa `requests`), sem novas
dependências.

> **Várias máquinas:** a Lagoa é central; cada máquina rodando um agente precisa
> ter o **código do robô** e as dependências localmente. `Enviar .zip` e
> `Instalar do Git` instalam no servidor, não empurram código para os agentes.
> Passo a passo completo em [`GUIA.md`](GUIA.md) (seção 10) e
> [`data/docs/REDE.md`](data/docs/REDE.md).

```bash
# 1. Popular com máquinas/processos/jobs de exemplo e subir a Lagoa
bash scripts/lagoa.sh --exemplos     # Linux / macOS
scripts\lagoa.bat --exemplos         # Windows

# 2. Abra:  http://localhost:8765            (Lagoa)
#           http://localhost:8765/monitor/   (trace das execuções)

# 3. Simule uma máquina (abra um terminal por máquina)
python -m core.control_room.agente --maquina maquina-01
python -m core.control_room.agente --maquina maquina-02 --tags "rh,sp"
bash scripts/agente.sh --maquina maquina-03 --tags "mac"   # atalho
```

> **Sem terminal aberto** — dá para deixar o agente rodando como serviço:
> no **macOS**, `bash scripts/instalar_agente_mac.sh` instala um *LaunchAgent*
> (sobe junto com a sessão, reconecta sozinho; `--remover` desinstala); no
> **Windows**, crie uma *Tarefa Agendada* apontando para `scripts\agente.bat`.

No painel: clique em **Executar** num processo (ou “+ Novo job”), escolha a
máquina (ou “qualquer”), e o agente que estiver livre pega o job. O resultado e
o passo a passo aparecem na hora — cada job tem link para o seu **trace**.

O painel tem as abas: **Jobs** (Lagoa), **Dispositivos**, **Fluxos & PDD**,
**Agendamentos**, **Automações**, **Filas**, **Assets** e **Acessos** (usuários,
papéis e permissões).

- **Login / RBAC (multiempresa)** — por padrão a Lagoa é aberta
  (`LAGOA_AUTH=false`, ideal para dev/LAN). Ligue `LAGOA_AUTH=true`
  para exigir login: o primeiro start cria o admin padrão
  (`ADMIN_EMAIL`/`ADMIN_SENHA`, padrão `admin@rpa.local` / `admin` — **troque em
  produção**). A aba **Acessos** gerencia usuários, papéis e permissões
  granulares (`jobs.disparar`, `assets.gerir`, `usuarios.gerir`…); a sessão é um
  cookie `HttpOnly` com validade de `SESSAO_HORAS`.

  ```bash
  LAGOA_AUTH=true ADMIN_EMAIL=eu@empresa.com ADMIN_SENHA=segredo \
      python -m core.control_room.servidor
  ```

- **Pools por tag** — cadastre tags nas máquinas (`--tags "sp,financeiro"`) e use
  o campo *Requisito (tag)* ao disparar um job. Só uma máquina com a tag pega o
  job, permitindo distribuir robôs por pool.

  ```bash
  python -m core.control_room.agente --maquina maquina-02 --tags "rh,sp"
  ```

- **Token por máquina** — cada máquina pode ter o seu próprio token (emitido em
  `POST /api/orq/maquinas/<nome>/token` ou na aba Acessos), revogável
  individualmente. O agente usa com `--token`; o `LAGOA_TOKEN` global
  continua valendo como coringa.

- **Agendamentos (triggers)** — dispare jobs automaticamente por **intervalo**
  (a cada N minutos), **diário** (HH:MM) ou **cron** (expressão de 5 campos, ex.:
  `*/15 9-18 * * seg-sex`). Cada agendamento escolhe o **robô**, **onde** rodar
  (máquina e/ou tag), os **dias da semana** e se roda em **fins de semana** e
  **feriados nacionais** (cálculo próprio, sem dependência: `core/control_room/feriados.py`).
  Na aba dá para **pausar/ativar**, **executar na hora** e remover. O servidor
  verifica os vencidos num *loop* de fundo (`INTERVALO_TRIGGERS` no `.env`, 15s).

- **Fluxos & PDD (documentação do processo)** — na aba **Fluxos & PDD** você
  informa o nome do processo, **quantas vezes o robô roda por dia** e descreve o
  passo a passo. Linhas começando com `Se`/`Senão`/`Erro` viram **decisões** e
  **exceções** no diagrama (arrastável). Cada alteração gera uma nova versão do
  **PDD** (Documento de Definição de Processo) em Markdown/HTML, com Mermaid,
  passos, exceções e critérios de aceite. A permissão é `pdd.gerir`.

- **Automações (pacotes de robô)** — publica um robô pela UI de duas formas:
  - **.zip** — envie um **.zip** com o manifesto `rpa.json` na aba **Automações**
    e a Lagoa extrai em `app/robos/<nome>/` e cadastra o processo no
    catálogo automaticamente (senha AES opcional). Dá para **remover** (apaga
    arquivos + catálogo).
  - **repositório Git** — informe a **URL HTTPS pública** de um repo que tenha o
    `rpa.json` na raiz (+ branch/tag opcional) e clique em **Instalar do Git**.
    A Lagoa clona (shallow) e instala igual ao `.zip`; robôs de Git ganham
    o botão **Atualizar** (clona de novo e substitui com um clique). Requer o
    `git` instalado na máquina. Só repositórios **públicos** por enquanto.

  O mesmo fluxo existe por CLI (`python -m core.control_room.pacote`):
  `empacotar`, `instalar` e `instalar-git <url> [--ref]`. Exemplo de robô público
  para testar: [`arthurfs11/robo-teste-popup`](https://github.com/arthurfs11/robo-teste-popup).

- **Assets / credenciais (v2)** — guarde segredos na Lagoa e busque-os no
  fluxo (sem espalhar senha pelo código). Cada asset tem **tipo** (`segredo` ou
  `texto`), **usuário** opcional, **versão** e histórico. Assets `segredo` são
  **cifrados no banco** (Fernet). A chave vem de `VAULT_CHAVE` (`.env`), do
  **chaveiro do sistema** (`VAULT_USAR_KEYRING=true` + extra `[keyring]`) ou de
  `data/vault.key` se você não definir nenhum. Na UI eles aparecem mascarados
  (`••••••••`) e o agente recebe o valor real:

  ```python
  from core.rpa import vault

  usuario = vault.obter("portal_usuario")   # valor simples (ou agente.asset(...))
  senha = vault.exigir("portal_senha")      # igual, mas falha se não existir

  cred = vault.buscar_credencial("portal")  # {usuario, senha, tipo, versao}
  vault.rotacionar("portal", "nova-senha")  # troca o valor, versão + 1
  ```

  * **Rotação**: `POST /api/orq/assets/<nome>/rotacionar` (ou `vault.rotacionar`)
    incrementa a versão e guarda a anterior em `asset_versoes`.
  * **Permissões por processo**: `POST /api/orq/assets/<nome>/permissoes` — sem
    nenhuma permissão o asset é aberto; com permissões, só o processo autorizado
    lê (via `?processo_id=` na rota `GET /api/orq/credenciais/<nome>`).
  * **Auditoria** (append-only): toda criação, leitura, rotação e permissão entra
    na tabela `auditoria`; veja na aba **Assets** do painel ou em
    `GET /api/orq/auditoria?recurso=&ator=`. Exporte com o botão **Exportar CSV**
    (`GET /api/orq/auditoria/exportar`) e descarte os antigos com
    `POST /api/orq/auditoria/expurgar` (retenção automática de
    `RETENCAO_AUDITORIA_DIAS`, padrão 90, expurgada ~1x/hora).
  * Segredos que por acaso escapem para uma mensagem de log são **mascarados**
    automaticamente pelo logger (`core/logger.py`).

- **Alertas de SLA** — jobs em execução há mais de `LIMITE_JOB_SEGUNDOS` (padrão
  300s) viram alerta (`GET /api/orq/alertas` e faixa de aviso no topo do painel),
  sinalizando robôs travados.

- **Filas / datapool (estilo filas de trabalho)** — crie um *pool de itens* e deixe
  os robôs consumirem um por um, com retry e status:

  ```python
  from core.rpa import fila

  fila.criar("clientes", descricao="NFs de hoje", processo="Dados — Tratar planilha")
  fila.adicionar("clientes", [
      {"nome": "ACME", "uf": "SP"},
      {"nome": "XPTO", "uf": "RJ"},
  ], referencia_campo="nome")
  ```

  O agente consome a fila com `--fila` (o job nasce automaticamente do processo
  executor e o fluxo recebe `item`):

  ```bash
  python -m core.control_room.agente --maquina maquina-01 --fila clientes
  ```

  ```python
  def meu_fluxo(navegador=None, item=None, agente=None):
      dados_item = item["dados"]   # {"nome": "ACME", "uf": "SP"}
      if agente and agente.cancelado():
          return False             # job cancelado na Lagoa
  ```

  Internamente há claim atômico (sem dois agentes pegarem o mesmo item),
  prioridade (inclusive **por item**, editável na UI), contagem de tentativas
  (`max_retentativas`, padrão 3) e estados
  `novo / em_processamento / concluído / falhou / abandonado`. A aba **Filas**
  permite **pausar/ativar**, **filtrar itens por status**, definir a **prioridade
  de cada item** e apontar **vários processos executores** — distribuídos em
  **round-robin**. Jobs podem ser **cancelados** (pendente ou em execução) e têm
  tela de **detalhe com o trace embutido**.

- **Pacotes de robô (.zip ou Git)** — empacote um robô com um manifesto `rpa.json`
  e envie para a Lagoa, que instala em `app/robos/<nome>/` e já cadastra o
  processo. Também dá para instalar **direto de um repositório Git público** e
  depois **atualizar** re-clonando:

  ```bash
  python -m core.control_room.pacote empacotar minha_pasta_robo/ --senha "opcional"
  python -m core.control_room.pacote instalar meu_robo.zip
  python -m core.control_room.pacote instalar-git https://github.com/usuario/meu-robo.git --ref main
  ```

  `rpa.json` mínimo:

  ```json
  {
    "nome": "cliente_mock",
    "versao": "1.0.0",
    "entrada": "main.py",
    "funcao": "rodar",
    "usa_navegador": false
  }
  ```

  Se o robô tiver um **`requirements.txt`** próprio, o agente cria um **`.venv`
  isolado** para ele na hora da execução: cria a venv, atualiza o pip, instala as
  dependências e roda o robô nesse ambiente (assim dependências de robôs não
  conflitam). Desligue com `RPA_INSTALAR_DEPENDENCIAS=false`. Comece pelo exemplo
  em `TEMPLATE/`.

- **Rede + token + TLS** — para rodar agentes em **outras máquinas**, suba a
  Lagoa com `HOST_LAGOA=0.0.0.0` (aceita a rede). Se for expor fora
  de uma rede confiável (VPN/hosted), defina `LAGOA_TOKEN` no `.env` do
  servidor **e** em cada agente (`--token` ou a mesma variável), e ligue HTTPS com
  `--cert`/`--chave` (ou `TLS_CERT`/`TLS_CHAVE`). Sem token, a Lagoa fica
  aberta (ideal para dev/rede local). Só as rotas dos **agentes** (registrar,
  buscar job, reportar execução, ler assets) exigem o token — o painel continua
  acessível no navegador:

  ```bash
  # servidor (com token e HTTPS opcional)
  export HOST_LAGOA=0.0.0.0 LAGOA_TOKEN="meu-segredo"
  python -m core.control_room.servidor --cert data/cert.pem --chave data/chave.pem

  # agente em outra máquina (na mesma rede)
  python -m core.control_room.agente --maquina maquina-02 \
      --lagoa https://10.0.0.5:8765 --token "meu-segredo"
  ```

  Para máquinas em redes diferentes, use um **overlay** (Tailscale/ZeroTier) em
  vez de abrir porta no roteador. Guia completo (token, TLS, VPN, firewall):
  [`data/docs/REDE.md`](data/docs/REDE.md). Os painéis usam **SSE**
  (`/api/orq/eventos` e `/api/eventos`) para atualizar em tempo real, com polling
  como reserva.

O catálogo de processos aponta para fluxos Python (`app.fluxos:buscar_no_google`),
então cadastrar um robô novo é só criar o fluxo e registrá-lo. Para o piloto, o
catálogo já vem com dois exemplos.

> Bancos em `data/orquestrador.db` (máquinas/jobs/triggers/assets/filas e
> identidade) e `data/monitor.db` (trace), ambos fora do Git. Ajuste porta, host,
> heartbeat, intervalo dos agendamentos, URL de consumo, token e chave do vault no
> `.env` (`PORTA_LAGOA`, `HOST_LAGOA`, `SEGUNDOS_OFFLINE`,
> `INTERVALO_TRIGGERS`, `LAGOA_URL`, `LAGOA_TOKEN`, `VAULT_CHAVE`,
> `LAGOA_AUTH`, `ADMIN_EMAIL`, `ADMIN_SENHA`, `SESSAO_HORAS`,
> `RETENCAO_AUDITORIA_DIAS`, `LIMITE_JOB_SEGUNDOS`).

### Automações de teste (`bot_test/`)

Para experimentar o orquestrador sem escrever um robô do zero, o template traz a
pasta **`bot_test/`** com automações simples que só registram logs (e umas que
falham, demoram ou consomem fila de propósito):

```bash
python -m bot_test.registrar          # cadastra os robôs de teste no catálogo
python -m bot_test.rodar_local todos  # ou rode localmente, sem Lagoa
```

Depois é só subir um agente e clicar em **Executar** no painel. Veja o passo a
passo completo em [`bot_test/README.md`](bot_test/README.md).

### Instaladores (servidor e agente sem Python)

Para rodar a Lagoa (e um agente) numa máquina **sem Python**, gere os
binários com **PyInstaller** — ou use os scripts que montam o pacote completo:

```bash
pip install pyinstaller

# macOS/Linux: binários soltos
pyinstaller --noconfirm packaging/lagoa.spec   # dist/lagoa
pyinstaller --noconfirm packaging/agente.spec         # dist/robo_agente

# macOS: pacote "tudo empacotado" (binários + TrackTab + instalador de serviços)
bash packaging/build_mac.sh                           # dist/RPA-Brasil-macos.zip

# Windows: instalador .exe (Inno Setup) com Lagoa + Agente + TrackTab
iscc packaging/inno_setup.iss                         # dist/instalador/lagoa_instalador.exe

# ao rodar um binário, defina onde persistir os dados:
RPA_PASTA_DADOS="$HOME/.rpa_brasil" ./dist/lagoa
```

No macOS, o `dist/RPA-Brasil/instalar_mac.sh` copia tudo para `~/RPA Brasil`,
cria o `.env`/`data/` e instala Lagoa **e** agente como serviços
(`LaunchAgents`, sobem no login). No Windows, o instalador cria atalhos e
oferece iniciar o agente junto com o Windows. O workflow
`.github/workflows/build-instaladores.yml` gera tudo isso no CI a cada tag `v*`.
Detalhes em [`packaging/README.md`](packaging/README.md).

### Extensão TrackTab (seletores com um clique)

A extensão **TrackTab** (`tracktab/`) captura os elementos de uma página e exporta
XPath (absoluto/relativo e um caminho "amigável") em JSON — ótimo para montar
selectores sem ficar inspecionando o HTML no olho. Leia o export no robô:

```python
from core.rpa import tracktab

elementos = tracktab.carregar("data/input/tracktab_exemplo.json")
seletores = tracktab.seletores("data/input/tracktab_exemplo.json", "relativo")
# {"nome": "//div[@id='...']", ...}
```

Enquanto não estiver na Chrome Web Store, carregue a pasta `tracktab/` em
`chrome://extensions` (**Modo do desenvolvedor** → *Carregar sem compactação*).
Para publicar (instalação de **1 clique**):

```bash
bash packaging/build_tracktab.sh        # gera dist/tracktab.zip
```

Passo a passo completo: [`tracktab/PUBLICAR.md`](tracktab/PUBLICAR.md).

---

## Monitor de execuções (trace)

Cansado de caçar o que o robô fez só no terminal? O template traz um **painel
local** que transforma cada execução numa *trace*: status do robô e o passo a
passo de cada ação, atualizando sozinho a cada 2 segundos.

**Status acompanhados:** `iniciado` · `processando` · `finalizado` · `falha` ·
`erro de negócio` · `erro sistêmico` · `erro crítico`.

Tudo roda com **SQLite + biblioteca padrão** — nenhuma dependência nova.

```bash
# 1. Popular o banco com robôs de exemplo (mock) e subir o painel
bash scripts/monitor.sh --exemplos     # Linux / macOS
scripts\monitor.bat --exemplos         # Windows

# 2. Abra no navegador:  http://localhost:8765
```

**Usando nos seus robôs** (registro em tempo real):

```python
from core.monitor import Monitor

monitor = Monitor("robo_folha_pagamento")
monitor.passo("Abrindo o portal de RH")
monitor.sucesso("Login realizado")
monitor.erro_negocio("CPF inválido na linha 42")   # ou .finalizar(...) / .falha(...)
```

> Os dados ficam em `data/monitor.db` (fora do Git). Sem os exemplos, o painel
> sobe vazio e vai enchendo conforme os robôs rodam.

---

## Testes automatizados

Testes de `pytest` cobrem o motor do **monitor** (execuções/passos) e as regras do
**Lagoa** (pools por tag, agendamentos, assets cifrados no vault — com
tipos, versões, rotação, permissões e auditoria —, filas com retry/claim, pacotes
`.zip` e claim de jobs). Os testes apontam os bancos para um
diretório temporário, então **nunca tocam** em `data/*.db`.

```bash
pip install -e ".[dev]"     # instala pytest + ruff
pytest                      # roda toda a suíte
ruff check app core settings tests
```

---

## Dicas para a comunidade

- **Selectores**: entender XPATH e CSS ajuda muito. Comece com `@id`, depois
  `//tag[@atributo='valor']`. Extraia-os em constantes no topo do arquivo de fluxo.
- **Esperas**: prefira `aguardar_elemento(...)` / `aguardar_url_contem(...)` a
  `time.sleep()`. Em oposição ao sono cego, esperar é determinístico e mais rápido.
- **Retry**: use o decorador `@tentar_novamente(vezes=3)` em passos sujeitos a
  instabilidade de rede.
- **Passo a passo**: use `@passo("Descrição")` para ver o andamento do robô no log.
- **Segredos**: tudo que for senha/token morre no `.env`, nunca no código.
- **Falhas do Google**: em IPs de cloud o Google pode apresentar CAPTCHA. Para
  bots de produção, prefira `AMBIENTE=prod` em máquina local ou políticas de
  WebDriver de verdade (isto é só um template de exemplo).

---

## Documentação complementar

- 🚀 **[Guia passo a passo](GUIA.md)** — instalar, configurar, token do dispositivo e subir agentes
- 📋 **[Catálogo de funções](data/docs/CATALOGO_FUNCOES.md)** — todas as funções low-code com exemplos
- 🏗️ **[Arquitetura](data/docs/ARQUITETURA.md)** — como os módulos se relacionam e como estender
- 🌐 **[Rede, token, TLS e VPN](data/docs/REDE.md)** — rodar agentes em outras máquinas com segurança
- 📦 **[Instaladores](packaging/README.md)** — Lagoa/agente sem Python (macOS e Windows) e a extensão TrackTab

---

Feito com ❤️ para a comunidade **Python Brasil**. Contribuições são bem-vindas!