# Ideias e RFCs

Use esta pasta para propostas que precisam de mais contexto do que uma issue:
novas APIs, mudanças de arquitetura, integrações, mudanças de comportamento ou
qualquer coisa que afete a versão estável.

## Como enviar

1. Copie [`TEMPLATE.md`](TEMPLATE.md).
2. Renomeie para `NNNN-titulo-curto.md` (ex.: `0001-fila-com-prioridade.md`).
3. Preencha as seções.
4. Abra um PR neste repositório.

O número pode ser o próximo disponível. A discussão acontece no PR; o RFC só é
considerado aceito quando um mantenedor marca a issue/PR como `aceita`.

## O que um bom RFC tem

- problema real e contexto;
- proposta clara, com exemplos de uso;
- alternativas consideradas;
- impacto na compatibilidade e na segurança;
- plano de testes e documentação;
- riscos e o que fica fora de escopo.

## Depois de aceito

A implementação vai para o repositório oficial, na branch `next`, e entra na
`main` no próximo release estável. Mudanças grandes podem ser divididas em
etapas.
