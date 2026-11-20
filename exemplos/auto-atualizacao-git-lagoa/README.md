# Auto-atualização de automações Git na Lagoa (polling)

Proposta da comunidade para a Lagoa detectar pushes em repositórios Git de
automações já instaladas e trocar o código sozinha. A escolha foi **polling**
(`git ls-remote`) em vez de webhook: funciona em rede local, sem expor a Lagoa
à internet e sem precisar de segredo de webhook.

**Escopo:** a Lagoa atualiza somente a cópia dela em `PASTA_ROBOS`. Agentes
remotos continuam com o código antigo até receberem a própria atualização —
isso está fora desta proposta.

## O que vem junto

- `mudancas-backend.patch` — diff com as alterações em arquivos já existentes:
  - `core/control_room/banco.py`: colunas `commit_sha`, `auto_atualizar`,
    `ultima_atualizacao` e `ultimo_erro`; leitores/escritores novos; **correção
    definitiva do vazamento de FDs do SQLite** (`conectar()` agora fecha a
    conexão no `finally`);
  - `core/monitor/banco.py`: mesma correção de FD;
  - `core/control_room/servico.py`: `criar_processo(..., commit_sha=)` e
    serviços de auto-atualização com auditoria;
  - `core/control_room/pacote.py`: `sha_remoto()`, `_sha_local()` e troca
    atômica de diretório (staging + backup + `.venv` preservado + rollback);
  - `core/control_room/servidor.py`: thread de polling e rotas
    `POST /api/orq/processos/<id>/auto-atualizar` e
    `POST /api/orq/automacoes/verificar`;
  - `settings/parametros.py`: `AUTO_ATUALIZAR` e `INTERVALO_ATUALIZACAO`;
  - testes de regressão do fechamento de conexão em `tests/test_control_room.py`
    e `tests/test_monitor.py`.
- `interface.patch` — UI da aba Automações (botão de verificação,
  `Auto: sim/não`, SHA curto) e ajustes do dashboard de SLA que estavam
  pendentes.
- `core/control_room/atualizador.py` — arquivo novo: `verificar_atualizacoes()`
  e `iniciar_atualizador()` (thread daemon, lock não-bloqueante).
- `tests/test_atualizador.py` — 6 testes novos.

## Como aplicar em um checkout do oficial

```bash
git clone https://github.com/capivara-rpa/capivara.git /tmp/capivara-auto-validacao
cd /tmp/capivara-auto-validacao
EX=$(pwd)/exemplos/auto-atualizacao-git-lagoa   # ajuste para o caminho deste repo
cp "$EX/core/control_room/atualizador.py" core/control_room/atualizador.py
cp "$EX/tests/test_atualizador.py" tests/test_atualizador.py
git apply "$EX/mudancas-backend.patch"
git apply "$EX/interface.patch"
python -m pip install -r requirements.txt pytest ruff
python -m pytest -q
python -m ruff check app core settings tests bot_test
python -m compileall -q app core settings tests bot_test
node --check core/control_room/estatico/painel.js
```

Ambos os patches foram gerados contra o `main` oficial `44b8e70` e passaram em
`git apply --check`. Se o oficial avançar e houver divergência, aplique os
trechos manualmente — os arquivos novos são autocontidos e este `README`
descreve cada mudança.

## Uso

1. Instale a automação por Git (`POST /api/orq/automacoes/git`) ou pela UI.
2. Ative o toggle **Auto: sim** na coluna Origem da aba Automações
   (`POST /api/orq/processos/<id>/auto-atualizar`).
3. A cada `INTERVALO_ATUALIZACAO` (padrão 300s, mínimo 30s), a Lagoa compara
   `git ls-remote` com o SHA gravado. Se mudou, clona em staging, troca o
   diretório, preserva `.venv`, atualiza o catálogo e grava o novo SHA/erro.
4. O botão **Verificar atualizações agora** dispara uma checagem imediata.

## Validação feita

- `170` testes pytest aprovados; Ruff, `compileall` e `node --check` limpos.
- E2E real: repo Git servido por HTTP local, instalação no SHA `5bf16f6`,
  toggle ligado, commit `v2` (`6ac089e`), verificação imediata atualizou o
  arquivo para `v2`, preservou o `.venv` e gravou SHA/hora; segunda verificação
  retornou `ignorados: 1`.
- O binário da Lagoa foi reconstruído e reiniciado localmente sem novos erros
  de banco; isto **não** foi publicado no repositório oficial.
