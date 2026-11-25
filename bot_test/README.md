# bot_test — automações de teste da Lagoa

Pasta com robôs de exemplo para você testar o fluxo completo do orquestrador:

```
Lagoa (painel)  ──dispara job──►  agente (máquina)  ──roda──►  automação
        ▲                                                              │
        └──────────────── trace (logs) no painel ◄─────────────────────┘
```

Cada automação em `bot_test/automacoes.py` é uma função simples que **registra
logs** e devolve `True` (sucesso) ou falha de propósito — ideal para ver o
trace, os status e as máquinas mudando no painel.

## 1. Registrar os processos

Com o ambiente ativo (`source .venv/bin/activate`), cadastre os robôs de teste
no catálogo da Lagoa:

```bash
python -m bot_test.registrar
```

Isso cria 7 processos (Olá mundo, Contar até 10, Gerar relatório, Erro de
negócio, Tarefa longa, Consultar credencial e Processar item de fila) e uma
**fila** `pedidos_teste` com 4 itens. É idempotente: pode rodar de novo sem
duplicar.

> ⚠️ Se você rodar `python -m core.control_room.dados_exemplo` (ou
> `--exemplos`) **depois**, ele recria o banco e apaga tudo — inclusive estes
> robôs de teste. Nesse caso, é só rodar `python -m bot_test.registrar`
> novamente.

## 2. Subir a Lagoa

Se ainda não estiver rodando:

```bash
scripts/lagoa.sh          # Linux / macOS
scripts\lagoa.bat         # Windows
```

Abra <http://localhost:8765>.

## 3. Subir uma máquina (agente)

Em outro terminal, simule uma máquina:

```bash
python -m core.control_room.agente --maquina maquina-teste --tags teste
```

> Para simular **várias máquinas**, abra vários terminais com nomes diferentes
> (`maquina-01`, `maquina-02`, ...). Use `--uma-vez` para executar só 1 job.

> **Deixar rodando sem terminal (macOS):** `bash scripts/instalar_agente_mac.sh
> --maquina maquina-teste --tags teste` instala o agente como serviço
> (*LaunchAgent*) que sobe junto com a sessão e reconecta sozinho. Na 1ª subida
> pode demorar ~30s (Rosetta). Use `--remover` para desinstalar.

## 4. Disparar do painel

No painel, na lista de **Processos**, clique em **Executar** no robô "Teste —
..." e escolha a máquina `maquina-teste` (ou deixe "qualquer"). O agente pega o
job na hora e o passo a passo aparece no **trace** (clique no job).

Automações para observar:

| Processo | O que mostra |
|---|---|
| Teste — Olá mundo | sucesso simples com poucos passos |
| Teste — Contar até 10 | vários passos no trace |
| Teste — Gerar relatório | cria um arquivo em `data/output/` |
| Teste — Erro de negócio | falha de propósito (status de erro) |
| Teste — Tarefa longa | ~15s, máquina fica "ocupada" |
| Teste — Consultar credencial | lê o asset `portal_usuario` do vault |

## 5. Testar uma fila (datapool)

O processo "Teste — Processar item de fila" consome itens da fila
`pedidos_teste`. Suba um agente em modo fila:

```bash
python -m core.control_room.agente --maquina maquina-teste --fila pedidos_teste
```

Os itens são processados um a um. O item `Cliente Delta` (UF `RJ`) falha de
propósito e volta para a fila (**retry**, até 3 tentativas) — veja na aba
**Filas** do painel.

## 6. Rodar localmente (sem Lagoa)

Para ver só os logs no terminal (e a trace no painel de monitoramento):

```bash
python -m bot_test.rodar_local                # roda "ola_mundo"
python -m bot_test.rodar_local tarefa_longa   # roda uma automação
python -m bot_test.rodar_local todos          # roda todas as locais
```
