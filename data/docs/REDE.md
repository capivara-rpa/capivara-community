# Rodando os robôs fora da sua máquina (rede, token, TLS e VPN)

A Lagoa sobe por padrão em `http://127.0.0.1:8765` (só a própria máquina).
Este guia mostra como liberar **agentes em outras máquinas**, com segurança.

> Resumo: rede local = abrir o host; fora da rede = **token** (+ **TLS**) e,
> de preferência, uma **VPN/overlay** (Tailscale).

## 1. Mesma rede local (LAN) — piloto

No `settings/parametros.py` (ou no `.env`):

```dotenv
HOST_LAGOA=0.0.0.0     # escuta a rede
LAGOA_TOKEN=um-segredo-forte
```

Suba a Lagoa e veja no log o comando pronto para os runners:

```bash
python -m core.control_room.servidor
# SUCCESS | Lagoa disponível em http://0.0.0.0:8765
# INFO    | Runners na rede: --lagoa http://192.168.0.10:8765
```

Em cada máquina da rede:

```bash
python -m core.control_room.agente \
    --lagoa http://192.168.0.10:8765 \
    --maquina maquina-sp-01 --tags sp --token um-segredo-forte
```

No Mac, o serviço já sai configurado em um passo: `scripts/instalar_agente_mac.sh
--lagoa http://192.168.0.10:8765 --tags sp --token um-segredo-forte`.

> Se a máquina tiver firewall, libere a porta 8765 (ex.: no macOS,
> Preferências → Rede → Firewall; no Windows, libere no instalador/Defender).

### 1.1 Cadastro da máquina: automático ou pela Lagoa

Há dois caminhos — os dois funcionam, mas o recomendado é cadastrar antes:

| Caminho | Como funciona | Quando usar |
|---|---|---|
| **Cadastrar em Dispositivos** | Você informa nome, tags e observação; depois gera um **token exclusivo** para a máquina. | Produção, várias máquinas, auditoria. |
| **Auto-cadastro pelo agente** | O agente chama `POST /api/orq/agente/<nome>/registrar` ao subir. A máquina aparece no painel e fica `online` no primeiro heartbeat. | Laboratório, teste rápido. |

O nome em `--maquina` precisa ser **exatamente** o mesmo do cadastro. Se você
cadastrou `PC-FINANCEIRO-01`, não suba o agente como `pc-financeiro-01` nem
como o hostname padrão.

Fluxo recomendado para cada máquina:

1. Na aba **Dispositivos**, clique em **Cadastrar máquina** (nome + tags).
2. Clique em **Gerar token** e copie o valor (aparece uma única vez).
3. Na máquina, suba o agente com `--maquina`, `--tags`, `--lagoa` e `--token`.
4. Confirme que o estado mudou para `online`.
5. Dispare um job de teste e veja o trace.

### 1.2 Código e dependências em cada máquina

**A Lagoa não envia o código do robô para os agentes.** O painel central
instala/cadastra processos, mas a execução acontece no processo Python do
agente, na máquina dele. Portanto, cada máquina que vai rodar um robô precisa
ter:

- o projeto Capivara (clone do repositório ou pacote instalado);
- as dependências do motor (`pip install -r requirements.txt` no `.venv`);
- o **código do robô** que ela vai executar;
- as dependências do robô — ou um `requirements.txt` na raiz do robô, que o
  agente instala em um `.venv` isolado (`RPA_INSTALAR_DEPENDENCIAS=true`).

Formas comuns de manter o código sincronizado:

```bash
# Git: clone uma vez e atualize antes do deploy
git clone git@github.com:sua-empresa/robos.git
cd robos
git pull

# Ou copie a pasta do robô para o mesmo caminho em todas as máquinas
# (ex.: /opt/capivara/app/robos/meu_robo)
```

> `Enviar .zip` e `Instalar do Git` na Lagoa instalam o robô **no servidor**.
> Se o job for executado em outra máquina, o código precisa existir lá também.
> O agente **empacotado** (PyInstaller) não importa robôs externos — para
> consumir automações publicadas, rode o agente do **fonte** (`.venv`).

### 1.3 Ordem de subida (evita dor de cabeça)

1. Suba a Lagoa no servidor e confirme `http://IP:8765/`.
2. Cadastre as máquinas e gere os tokens.
3. Prepare o código/dependências em cada máquina.
4. Suba os agentes (`--uma-vez` para testar, depois como serviço).
5. Só então dispare jobs e agendamentos.

## 2. Token: o que ele protege

Quando `LAGOA_TOKEN` está **definido**, só as **rotas de agente** pedem o
token (`Authorization: Bearer` ou `X-Token`):

| Rota | Método |
|---|---|
| `/api/orq/agente/*` | POST |
| `/api/orq/jobs/<id>/execucao` · `/concluir` | POST |
| `/api/orq/itens/<id>/resultado` · `/abandonar` | POST |
| `/api/orq/filas/<nome>/proximo` | POST |
| `/api/orq/assets/<nome>` | GET |

O **painel** (e as rotas de leitura/criação de jobs) fica aberto — é a interface
humana. Com o token **vazio**, tudo fica aberto (ideal só para dev/rede local).

Os clientes do template já mandam o token sozinhos quando `LAGOA_TOKEN`
está no ambiente: o **agente** (`--token`), `core/rpa/vault.py` e
`core/rpa/fila.py`.

## 3. TLS (HTTPS) — tráfego cifrado

Gere um certificado (self-signed serve para testar):

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout data/chave.pem -out data/cert.pem \
  -subj "/CN=rpa.local" \
  -addext "subjectAltName=DNS:rpa.local,IP:192.168.0.10"
```

Suba a Lagoa com TLS (ou use `TLS_CERT`/`TLS_CHAVE` no `.env`):

```bash
python -m core.control_room.servidor \
    --host 0.0.0.0 --cert data/cert.pem --chave data/chave.pem
```

Os agentes passam a usar `https://`:

```bash
python -m core.control_room.agente \
    --lagoa https://192.168.0.10:8765 \
    --maquina maquina-sp-01 --token um-segredo-forte
```

O painel de trace (`/monitor/`) também sobe em HTTPS. Como o certificado é
self-signed, o navegador vai pedir para confirmar uma vez.

> Se o OpenSSL do seu Mac não aceitar `-addext`, crie um arquivo de config com
> `[v3_req] subjectAltName=...` e passe `-extensions v3_req -config seu.cnf`.

## 4. Fora da rede: VPN/overlay com Tailscale

Para máquinas em redes diferentes (casa, escritório, cloud), o caminho mais
simples e seguro é um **overlay** — todas entram numa rede privada virtual e a
Lagoa continua sendo "local" para os agentes.

1. Instale o [Tailscale](https://tailscale.com/download) nas máquinas.
2. Em cada uma: `tailscale up` e faça login na mesma conta.
3. `tailscale ip -4` mostra o IP (ex.: `100.101.102.103`).
4. Suba a Lagoa com `HOST_LAGOA=0.0.0.0` (o Tailscale já cifra o
   tráfego; o token continua valendo como 2ª camada).
5. Aponte os agentes para `http://100.101.102.103:8765`.

Vantagens: sem abrir portas no roteador, sem IP fixo, tráfego cifrado pelo
WireGuard. **Alternativas ao Tailscale**: [ZeroTier](https://www.zerotier.com/)
ou um WireGuard/OpenVPN próprio.

### Lagoa hospedada (internet)

Se preferir expor a Lagoa diretamente, faça **sempre** as três coisas
juntas: (1) `LAGOA_TOKEN` forte, (2) TLS com certificado válido
(Let's Encrypt) e (3) um proxy reverso (Caddy/Nginx) na frente. Sem token +
TLS, qualquer um com a URL dispara jobs na sua rede.

## 5. Push em tempo real (SSE)

Os painéis usam **SSE (Server-Sent Events)** — sem dependências extras:

- Lagoa: `GET /api/orq/eventos`
- Monitor: `GET /api/eventos`

O navegador recebe `data: {"rev": <n>}` sempre que algo muda (job, fila,
máquina, execução) e recarrega sozinho; se o SSE cair, o painel volta ao
auto-refresh por polling automaticamente.

## 6. Checklist rápido

- [ ] `LAGOA_TOKEN` forte definido? (nunca comitar o `.env`)
- [ ] `HOST_LAGOA=0.0.0.0` só quando precisar de outra máquina.
- [ ] TLS ligado (`--cert/--chave`) se o tráfego sai da LAN/VPN?
- [ ] Preferir Tailscale/overlay a abrir porta no roteador.
- [ ] Agente como serviço (`scripts/instalar_agente_mac.sh`, Atalho/Tarefa no
      Windows, ou o pacote instalável) para reconectar sozinho.
- [ ] Nome do agente igual ao cadastro em **Dispositivos**.
- [ ] Código do robô e dependências presentes **em cada máquina** que vai
      executá-lo (a Lagoa não empurra código para os agentes).
- [ ] Job de teste concluído em cada máquina antes de ligar os agendamentos.
