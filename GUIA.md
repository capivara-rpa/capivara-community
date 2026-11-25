# Guia de instalação e uso — Capivara 🦫

Este guia leva você **do zero** até um robô rodando na Lagoa, com agente
instalado e **token do dispositivo** configurado. Se você só quer a visão geral,
veja o [`README.md`](README.md); aqui o foco é **passo a passo operacional**.

> Terminologia rápida
> - **Robô / Fluxo**: sua automação (o código Python em `app/fluxos/`).
> - **Lagoa**: o painel/orquestrador que organiza máquinas, processos e jobs.
> - **Monitor**: painel com o *trace* (passo a passo) de cada execução.
> - **Agente (capivara)**: o programinha que roda **em cada máquina** e executa os jobs.
> - **Dispositivo / Máquina**: uma máquina cadastrada onde um agente roda.

---

## 1. Pré-requisitos

| Item | Observação |
|---|---|
| **Python 3.11+** | O projeto foi feito e testado no 3.11. |
| **Google Chrome** | Usado pelos robôs de web. O driver é baixado sozinho (Selenium Manager). |
| **Docker** (opcional) | Para rodar em servidor sem instalar nada na máquina. |
| **Rede local** (opcional) | Se você for rodar agentes em outras máquinas. |

No Windows, se `python` não existir no PATH, use `py` no lugar.

---

## 2. Instalação

### Opção A — script (recomendado)

```bash
# Linux / macOS
bash scripts/install.sh

# Windows
scripts\install.bat
```

O script cria o `.venv` e instala as dependências.

### Opção B — manual

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### Criar o arquivo de configuração

```bash
cp .env.example .env             # Linux / macOS
copy .env.example .env           # Windows
```

> 🔒 O `.env` guarda segredos e **nunca** deve ir para o Git (já está no `.gitignore`).

---

## 3. Configuração do `.env`

Você **não precisa** mexer em tudo — só no que for usar. Os campos mais comuns:

| Variável | Para quê | Exemplo |
|---|---|---|
| `AMBIENTE` | `dev` (navegador visível) ou `prod` (headless) | `dev` |
| `HEADLESS` | Força esconder a janela do Chrome | `false` |
| `HOST_LAGOA` | `127.0.0.1` (só esta máquina) ou `0.0.0.0` (aceita a rede) | `127.0.0.1` |
| `PORTA_LAGOA` | Porta do painel (Lagoa em `/`, Monitor em `/monitor/`) | `8765` |
| `LAGOA_URL` | Onde o robô/agente busca dados (assets/filas) | `http://127.0.0.1:8765` |
| `LAGOA_TOKEN` | Token **global** do agente (vazio = painel aberto em dev) | *(vazio)* |
| `LAGOA_AUTH` | `true` exige **login** no painel; `false` deixa aberto (dev/LAN) | `false` |
| `ADMIN_EMAIL` / `ADMIN_SENHA` | Admin criado no 1º start quando `LAGOA_AUTH=true` | `admin@rpa.local` / `admin` |
| `VAULT_CHAVE` | Frase que cifra os segredos (assets) | *(troque!)* |
| `SEGUNDOS_OFFLINE` | Tempo sem heartbeat até a máquina ficar **offline** | `60` |
| `LIMITE_JOB_SEGUNDOS` | Tempo até um job gerar **alerta de SLA** | `300` |

> Comece com os padrões. Só em produção troque `ADMIN_SENHA`, defina
> `VAULT_CHAVE` e decida sobre `LAGOA_AUTH`/`LAGOA_TOKEN`.

---

## 4. Rodando seu primeiro robô (sem orquestrador)

```bash
python app/main.py            # todos os fluxos de exemplo
python app/main.py --dados    # só o fluxo de planilha (pandas)
python app/main.py --web      # navegador (Google)
```

Saída esperada (colorida no terminal) e arquivos gerados em `data/output/`.
Para criar seu próprio fluxo, veja a seção *Criando seu primeiro robô* no
[`README.md`](README.md).

---

## 4b. Monitor (trace das execuções)

O Monitor mostra o **passo a passo** de cada execução (útil mesmo sem Lagoa):

```bash
bash scripts/monitor.sh --exemplos     # Linux / macOS
scripts\monitor.bat --exemplos         # Windows
# abra http://localhost:8765
```

Nos seus robôs:

```python
from core.monitor import Monitor

monitor = Monitor("robo_folha_pagamento")
monitor.passo("Abrindo o portal de RH")
monitor.sucesso("Login realizado")
monitor.erro_negocio("CPF inválido na linha 42")
```

---

## 4. Subir a Lagoa

```bash
# Linux / macOS (--exemplos popula máquinas/processos/jobs de demonstração)
bash scripts/lagoa.sh --exemplos

# Windows
scripts\lagoa.bat --exemplos
```

Abra no navegador:

- **Lagoa** → http://localhost:8765
- **Monitor (trace)** → http://localhost:8765/monitor/

O menu lateral tem: **Lagoa** (jobs), **Dispositivos**, **Filas**,
**Credenciais**, **Acessos** e **Sistema → Monitor**.
Use o botão do rodapé da barra lateral para alternar **tema claro/escuro**.

> A Lagoa e o Monitor usam **SQLite + biblioteca padrão**. Os bancos ficam
> em `data/orquestrador.db` e `data/monitor.db` (fora do Git).

---

## 5. Cadastrar um **Dispositivo** (máquina)

O menu **Dispositivos** é onde você cadastra e gerencia as máquinas.

1. No menu lateral, clique em **Dispositivos**.
2. Preencha o formulário e clique em **Cadastrar máquina**:
   - **nome** — identificador da máquina (ex.: `PC-FINANCEIRO-01`). Use o mesmo nome no agente.
   - **tags** — rótulos separados por vírgula (ex.: `sp, financeiro`). Servem para
     direcionar jobs (pool por tag).
   - **observação** — texto livre (opcional).
3. A máquina aparece na tabela. Assim que um **agente** com o mesmo nome subir e
   fizer *heartbeat*, o estado muda para **online**.

**Estados possíveis:**

| Estado | Significado |
|---|---|
| `online` | Agente vivo (batimento recente) e livre. |
| `ocupada` | Agente online executando um job. |
| `offline` | Sem heartbeat há mais de `SEGUNDOS_OFFLINE` (ou recém-cadastrada). |

> Você também pode deixar a máquina se auto-cadastrar: basta subir o agente com
> `--maquina <nome>` — mas cadastrar antes no painel é o jeito recomendado,
> porque aí você já **gera o token** dela.

---

## 6. O **token do dispositivo** — onde ele vai

Quando você clica em **Gerar token** na tabela de Dispositivos, a Lagoa
cria um segredo **exclusivo daquela máquina**. Ele é a credencial que o **agente**
usa para provar que é aquela máquina.

### 6.1 O que acontece por baixo

1. O servidor gera um token aleatório e guarda no banco **apenas o hash**
   (SHA-256) na coluna `maquinas.token_hash`. O valor puro **não fica salvo**.
2. O valor real aparece **uma única vez** na tela (caixa destacada `token-novo`).
   Se você fechar, perdeu — mas dá para revogar e gerar outro.
3. O agente envia esse token em **todas** as requisições, no cabeçalho
   `Authorization: Bearer <token>`.
4. O servidor recebe, calcula o hash e compara com o que está no banco. Bateu →
   autorizado; não bateu → **401**.

### 6.2 Onde você coloca o token (no agente)

O token vai **para o agente daquela máquina**. Há duas formas:

**a) Na linha de comando** (rodando manualmente):

```bash
python -m core.control_room.agente --maquina PC-FINANCEIRO-01 \
    --tags "sp,financeiro" --token "COLE-O-TOKEN-AQUI"

# ou pelo atalho:
bash scripts/agente.sh --maquina PC-FINANCEIRO-01 --token "COLE-O-TOKEN-AQUI"
```

**b) Como serviço** (sem terminal aberto):

```bash
# macOS: instala um LaunchAgent (sobe no login e reconecta sozinho)
bash scripts/instalar_agente_mac.sh --maquina PC-FINANCEIRO-01 \
    --tags "mac,sp" --token "COLE-O-TOKEN-AQUI"
# remover depois:
bash scripts/instalar_agente_mac.sh --remover
```

No **Windows**, use a Tarefa Agendada apontando para `scripts\agente.bat` (ou o
atalho criado pelo instalador) passando `--token`. O instalador `.exe` também
oferece iniciar o agente junto com o Windows.

> 💡 Alternativa sem `--token`: defina o mesmo valor em `LAGOA_TOKEN` no
> `.env` da máquina. Mas atenção: **esse é o token global**, compartilhado por
> todos os agentes — o token **por máquina** é mais seguro e auditável.

### 6.3 Quando o token é realmente exigido

| Cenário | O agente precisa de token? |
|---|---|
| `LAGOA_TOKEN` vazio **e** `LAGOA_AUTH=false` | **Não** — painel aberto (dev/rede local). O agente conecta sem token. |
| `LAGOA_TOKEN` definido (global) | Sim — use o **global** ou um **token de máquina**. |
| `LAGOA_AUTH=true` (login ligado) | Sim — precisa do **token de máquina** (ou global). |

Ou seja: no seu laboratório em rede local, o token é opcional. No momento em que
você expõe a Lagoa (fora da sua máquina) **ou** liga o login, o token passa
a ser obrigatório.

### 6.4 Revogar / trocar

Na tabela de Dispositivos:

- **Revogar token** → apaga o hash no banco; o agente atual passa a receber 401.
- **Gerar token** de novo → cria outro; atualize o `--token` do agente.

Se um token vazar, revogue: o antigo deixa de funcionar imediatamente.

---

## 7. Disparar um job e ver o resultado

1. Na aba **Jobs** (ou no botão **+ Novo job**), escolha o **processo** (seu robô),
   a **máquina** (ou "qualquer") e, se quiser, uma **tag** de filtro.
2. Um agente livre com o mesmo nome/tag pega o job, executa o fluxo e devolve o
   resultado.
3. O job muda de status (`pendente → em_execucao → concluido/falhou/cancelado`) e
   cada job tem um **link para o trace** no Monitor.

4. O botão **Detalhes** abre o job com metadados + **trace embutido** (passo a
   passo), sem sair do painel.
5. **Cancelar**: jobs `pendente` ou `em_execucao` podem ser cancelados pela linha
   ou pelo diálogo de detalhes. Se o fluxo quiser cooperar, ele pode checar
   `agente.cancelado()` e encerrar sozinho.

**Agendamentos** (aba Agendamentos): monte o agendamento escolhendo o **robô**,
**onde** rodar (máquina e/ou tag), a **recorrência** (intervalo, diário ou **cron**,
ex.: `*/15 9-18 * * seg-sex`), os **dias da semana** e se roda em **fins de semana**
e **feriados nacionais**. Cada linha tem **Executar agora**, **Pausar/Ativar** e
**Remover**.

**Automações** (aba Automações): publique um robô enviando um **.zip** com o
manifesto `rpa.json` (senha AES opcional). A Lagoa extrai em
`app/robos/<nome>/` e cadastra o processo no catálogo sozinha; o botão **Remover**
desinstala. Se o robô tiver um **`requirements.txt`** próprio, o agente cria um
**`.venv` isolado** para ele na hora de executar (cria venv → atualiza pip →
instala as dependências → roda nesse ambiente); desligue com
`RPA_INSTALAR_DEPENDENCIAS=false`. Comece pelo modelo em `TEMPLATE/`. Veja o
passo a passo em
[`core/control_room/pacote.py`](core/control_room/pacote.py).

**Instalar de um repositório Git** — na mesma aba, informe a **URL HTTPS**
(pública) de um repositório que tenha o `rpa.json` na raiz e clique em
**Instalar do Git**. Opcionalmente, informe um **branch/tag** no campo ao lado.
A Lagoa clona (shallow), valida o manifesto e instala igual ao `.zip`.
Robôs instalados assim ganham o botão **Atualizar**: ele clona de novo e
substitui a versão em uso (um clique, sem reinstalar à mão). Requer o **`git`**
instalado na máquina da Lagoa. Só repositórios **públicos** por enquanto
(privados exigem token — roadmap). Pela linha de comando:

```bash
python -m core.control_room.pacote instalar-git https://github.com/usuario/meu-robo.git --ref main
```

> Exemplo pronto para testar: o repositório público
> [`arthurfs11/robo-teste-popup`](https://github.com/arthurfs11/robo-teste-popup)
> contém um robô que abre um **pop-up nativo** na máquina — instale pela UI
> (**Automações → Instalar do Git**) e dispare o processo `teste_popup`.


**Filas** (aba Filas): crie um pool de itens e consuma com o agente:

```bash
python -m core.control_room.agente --maquina PC-01 --fila clientes --token "COLE-O-TOKEN"
```

Na fila você pode: **pausar/ativar**, **filtrar itens por status**, definir a
**prioridade de cada item** (maior = consumido antes; edite na própria linha) e
apontar **vários processos executores** — nesse caso os itens são distribuídos em
**round-robin** entre eles.

O fluxo recebe `item`:

```python
def meu_fluxo(navegador=None, item=None, agente=None):
    dados = item["dados"]   # {"nome": "ACME", "uf": "SP"}
    if agente and agente.cancelado():   # job cancelado na Lagoa
        return False
```

---

## 8. Credenciais (segredos) — em vez de senha no código

Na aba **Credenciais** você guarda segredos usados pelos robôs. Os segredos são
**cifrados** (Fernet). A chave vem de `VAULT_CHAVE` (`.env`) ou, se vazia, do
**chaveiro do sistema** (keyring, com `VAULT_USAR_KEYRING=true`) ou de
`data/vault.key`. Na UI aparecem mascarados (`••••••••`) e o agente recebe o
valor real:

```python
from core.rpa import vault

senha = vault.exigir("portal_senha")          # falha se não existir
cred  = vault.buscar_credencial("portal")     # {usuario, senha, tipo, versao}
vault.rotacionar("portal", "nova-senha")      # versão + 1
```

Há **auditoria** de todas as leituras/trocas (aba Credenciais → Auditoria
recente) e botões para **Exportar CSV** e **Expurgar antigos**.

---

## 9. Login e permissões (multiempresa)

Por padrão o painel é aberto (`LAGOA_AUTH=false`). Para exigir login:

```bash
# no .env:
LAGOA_AUTH=true
ADMIN_EMAIL=admin@rpa.local
ADMIN_SENHA=admin        # troque pelo painel depois do 1º login
```

No 1º start, o admin é criado automaticamente. A aba **Acessos** gerencia
usuários, papéis e permissões (`jobs.disparar`, `maquinas.gerir`, `assets.gerir`,
`usuarios.gerir`, ...).

---

## 10. Rodar várias máquinas apontando para uma Lagoa

Este é o desenho mais comum em produção: **uma Lagoa central** (servidor) e
**um agente em cada máquina** que vai executar robôs.

```text
                    rede local / VPN
  ┌──────────────────────────────┐
  │  SERVIDOR                    │
  │  Lagoa :8765                 │
  │  painel · banco · arquivos   │
  └──────────────┬───────────────┘
                 │ HTTP/HTTPS
     ┌───────────┼───────────┐
     │           │           │
  ┌──▼───┐    ┌──▼───┐    ┌──▼───┐
  │ PC 1 │    │ PC 2 │    │ PC 3 │
  │agente│    │agente│    │agente│
  └──────┘    └──────┘    └──────┘
```

### 10.1 O que fica em cada lugar

| Onde | O que precisa ter |
|---|---|
| **Servidor da Lagoa** | O projeto Capivara, o banco (`data/orquestrador.db`) e o painel. É aqui que você cadastra máquinas, processos, filas, agendamentos e credenciais. |
| **Cada máquina agente** | O projeto Capivara (fonte ou pacote instalado), as dependências dos robôs e o **código dos robôs** que ela vai executar. **Não precisa** subir a Lagoa nela. |

> ⚠️ **Ponto mais importante:** instalar um robô pela Lagoa (`Enviar .zip`,
> `Instalar do Git` ou `pacote.instalar_zip`) instala o código **no servidor**,
> não o empurra para os agentes. Cada máquina que for executar aquele robô
> precisa ter o mesmo código disponível localmente (clone do repositório,
> `git pull`, cópia da pasta ou instalação do pacote). As dependências também
> precisam existir na máquina — ou vir de um `requirements.txt` do robô, que o
> agente instala em um `.venv` isolado.

### 10.2 Passo a passo

**1. No servidor, suba a Lagoa aceitando a rede**

No `.env` do servidor:

```bash
HOST_LAGOA=0.0.0.0
PORTA_LAGOA=8765

# recomendado: token global para os agentes
LAGOA_TOKEN="um-segredo-bem-grande"
```

```bash
bash scripts/lagoa.sh
# ou: python -m core.control_room.servidor
```

Descubra o IP do servidor na rede (ex.: `10.0.0.5`). Em outra máquina, teste
`http://10.0.0.5:8765/` no navegador. Se não abrir, libere a porta `8765` no
firewall do servidor.

**2. Cadastre as máquinas (recomendado)**

Na aba **Dispositivos**, cadastre cada máquina com o nome exato que o agente
vai usar (ex.: `PC-FINANCEIRO-01`) e as tags do pool (ex.: `sp,financeiro`).
Cadastrar antes permite gerar um **token exclusivo por máquina**.

Também é possível deixar o agente se auto-cadastrar: basta subir o agente com
`--maquina <nome>`. Nesse caso, a máquina aparece no painel assim que o primeiro
heartbeat chegar.

**3. Gere o token de cada máquina**

Na tabela de **Dispositivos**, clique em **Gerar token** e copie o valor. Ele
aparece **uma única vez** — só o hash fica no banco. Se perder, revogue e gere
outro.

**4. Prepare cada máquina agente**

Em cada máquina, clone o projeto e crie o ambiente:

```bash
git clone git@github.com:capivara-rpa/capivara.git
cd capivara

python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Se o robô tiver `requirements.txt` próprio, o agente cria um `.venv` isolado
para ele automaticamente na hora da execução (`RPA_INSTALAR_DEPENDENCIAS=true`,
o padrão).

**5. Suba o agente apontando para a Lagoa**

```bash
python -m core.control_room.agente \
    --maquina PC-FINANCEIRO-01 \
    --tags "sp,financeiro" \
    --lagoa http://10.0.0.5:8765 \
    --token "TOKEN-DA-MAQUINA"
```

Teste uma vez com `--uma-vez` para registrar/heartbeat e ver o log no terminal:

```bash
python -m core.control_room.agente --maquina PC-FINANCEIRO-01 \
    --lagoa http://10.0.0.5:8765 --token "TOKEN-DA-MAQUINA" --uma-vez
```

**6. Deixe o agente como serviço (opcional, mas recomendado)**

No **macOS**:

```bash
bash scripts/instalar_agente_mac.sh \
    --maquina PC-FINANCEIRO-01 --tags "mac,sp" \
    --lagoa http://10.0.0.5:8765 --token "TOKEN-DA-MAQUINA"
```

No **Windows**, use a Tarefa Agendada apontando para `scripts\agente.bat` (ou o
atalho do instalador) com os mesmos argumentos. Em Linux, use `systemd` ou
`cron @reboot`.

**7. Confirme no painel e dispare um job**

A máquina deve sair de `offline` para `online`. Dispare um job escolhendo a
máquina (ou “qualquer”) e acompanhe o trace. Se o job ficar `pendente`, veja a
seção de solução de problemas.

### 10.3 Checklist de uma máquina nova

- [ ] Consegue abrir `http://IP-DO-SERVIDOR:8765/` no navegador.
- [ ] O nome em `--maquina` é **idêntico** ao cadastrado em **Dispositivos**.
- [ ] O token é o daquela máquina (não o global de outra).
- [ ] O projeto Capivara está na máquina e o `.venv` tem as dependências.
- [ ] O **código do robô** está na máquina (clone, `git pull` ou cópia).
- [ ] O agente subiu com `--uma-vez` sem erro e a máquina ficou `online`.
- [ ] Um job de teste concluiu e gerou trace.

### 10.4 Sincronização do código dos robôs

A Lagoa **não distribui código** para os agentes. Escolha um fluxo:

- **Git (recomendado):** cada máquina tem o clone do repositório do robô e roda
  `git pull` antes do deploy (ou um agendamento/cron faz isso).
- **Pacote:** publique o robô como pacote Python interno e instale no `.venv` de
  cada máquina.
- **Pasta compartilhada:** monte a mesma pasta em todas as máquinas e aponte o
  processo para o mesmo caminho.

Depois de atualizar o código em todas as máquinas, o próximo job já usa a versão
nova. Se o robô mudou dependências, atualize o `requirements.txt` e o `.venv`.

> Para expor a Lagoa fora da rede local, prefira um **overlay**
> (Tailscale/ZeroTier) e/ou **HTTPS** (`--cert`/`--chave` ou
> `TLS_CERT`/`TLS_CHAVE`). Guia completo em
> [`data/docs/REDE.md`](data/docs/REDE.md).

---

## 11. Rodar sem Python (instaladores)

Para uma máquina **sem Python**, gere binários com **PyInstaller**:

```bash
pip install pyinstaller

# macOS: pacote completo (Lagoa + Agente + TrackTab + serviços)
bash packaging/build_mac.sh          # gera dist/RPA-Brasil-macos.zip

# Windows: instalador .exe (Inno Setup)
iscc packaging/inno_setup.iss        # gera o instalador com atalhos/autostart
```

No pacote macOS, `instalar_mac.sh` copia tudo para `~/RPA Brasil`, cria `.env` e
`data/`, e instala Lagoa **e** agente como serviços. Detalhes em
[`packaging/README.md`](packaging/README.md).

> Os binários guardam dados em `RPA_PASTA_DADOS` (defina para persistir fora da
> pasta temporária do executável).

---

## 12. Solução de problemas

| Sintoma | Causa provável / solução |
|---|---|
| **"Gerar token" mas o agente não conecta** | O token do agente não confere. Confira se copiou o valor **completo** e se o `--token` é o mesmo da máquina. Teste com `--uma-vez`. |
| **Agente recebe `401`** | Token ausente/inválido, ou `LAGOA_AUTH=true` sem token de máquina. Veja a seção [6.3](#63-quando-o-token-é-realmente-exigido). |
| **Máquina aparece `offline` logo após cadastrar** | Normal: ela só fica `online` quando o agente com **o mesmo nome** faz heartbeat. |
| **Job fica `pendente` para sempre / máquina `offline` com plist instalado** | O serviço do agente **não está carregado** no launchd (comum após reboot ou instalação interrompida). Confira: `launchctl print gui/$(id -u)/com.rpabrasil.agente` — se não achar, rode de novo `bash scripts/instalar_agente_mac.sh --maquina NOME`. O script já retenta o carregamento e **só imprime ✅ se o serviço subir de verdade**. |
| **`MAC address`/nome diferente do esperado** | O agente usa `--maquina`; o padrão é o hostname. Use o mesmo nome do cadastro. |
| **Perdi o token** | Não tem como recuperar (só guardamos o hash). Clique em **Revogar token** e **Gerar token** de novo. |
| **Login pede senha e não sei qual** | Sem `ADMIN_SENHA` definido, o padrão é `admin@rpa.local` / `admin`. Troque no `.env` e reinicie. |
| **Painel não abre em outra máquina** | Suba com `HOST_LAGOA=0.0.0.0` e libere a porta no firewall. |
| **Robô web abre CAPTCHA do Google** | Comum em IP de cloud/sandbox. Use `AMBIENTE=prod` (headless) e/ou outro site de teste. |
| **Agente empacotado não acha meus fluxos** | Os binários (PyInstaller) não importam fluxos externos (`bot_test`, `.zip`). Rode do **fonte** (`.venv`) para isso. |
| **Agente demora ~10s pra subir no macOS** | *Cold start* do Rosetta ao rodar Python Intel; depois fica rápido. |
| **`scripts/*.sh: Permission denied`** | Rode com `bash scripts/arquivo.sh` (não precisa `chmod`). |

**Diagnóstico rápido:**

```bash
# a máquina está autorizada?
curl -s http://127.0.0.1:8765/api/orq/painel | python -m json.tool | grep -A2 '"maquinas"'

# o serviço do agente (macOS) está carregado e rodando?
launchctl print gui/$(id -u)/com.rpabrasil.agente | grep -E "state|pid|program"

# teste o agente só uma vez, vendo o log no terminal:
python -m core.control_room.agente --maquina PC-01 --uma-vez --token "SEU-TOKEN"
```

---

## 13. Verificações de qualidade (para contribuir)

```bash
pip install -e ".[dev]"                       # pytest + ruff
pytest                                        # suíte de testes
ruff check app core settings tests bot_test
python -m compileall -q app core settings bot_test
```

---

## Documentação complementar

- [`README.md`](README.md) — visão geral, funções low-code e arquitetura.
- [`data/docs/CATALOGO_FUNCOES.md`](data/docs/CATALOGO_FUNCOES.md) — todas as funções em português.
- [`data/docs/ARQUITETURA.md`](data/docs/ARQUITETURA.md) — como o motor é organizado.
- [`data/docs/REDE.md`](data/docs/REDE.md) — rede, token, TLS, VPN.
- [`packaging/README.md`](packaging/README.md) — instaladores e TrackTab.
- [`bot_test/README.md`](bot_test/README.md) — robôs de teste prontos.
