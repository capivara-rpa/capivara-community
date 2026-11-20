# Novidades

Registro das mudanças do framework que impactam a comunidade. O código e as
releases estáveis ficam no repositório oficial.

## 2026-11-18 — Dashboard de SLA na Lagoa

- A tarja amarela de SLA no topo do painel foi removida.
- Jobs lentos ou acima do tempo limite agora aparecem em uma lista ao lado do
  gráfico de execuções dos últimos 7 dias.
- O gráfico ficou mais compacto; clicar em um job abre o detalhe com o trace.
- Commit oficial: [`495a36b`](https://github.com/capivara-rpa/capivara/commit/495a36b)
  (`main` e `next`).

## 2026-11-20 — Auto-atualização Git na Lagoa (proposta)

- Novo exemplo em `exemplos/auto-atualizacao-git-lagoa/` com polling de
  repositórios Git, troca atômica preservando `.venv` e toggle por automação.
- Inclui a correção do vazamento de file descriptors do SQLite nas duas
  camadas (`core/control_room/banco.py` e `core/monitor/banco.py`).
- **Ainda não entrou no oficial**: está apenas neste repositório da comunidade,
  aguardando avaliação via issue/RFC antes de ir para a branch `next`.
