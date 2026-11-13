# Como contribuir

Obrigado por querer melhorar a Capivara. Este repositório é o espaço de
**ideias e avaliação**; o código estável vive no
[repositório oficial](https://github.com/capivara-rpa/capivara).

## Antes de abrir

- Procure nas **issues** e **discussions** se alguém já propôs algo parecido.
- Para bug na versão estável, abra uma issue no repositório oficial ou use o
  template de bug daqui, informando a versão e o ambiente.
- Não publique tokens, senhas, dados de clientes ou logs com informações
  sensíveis.

## Sugestões

Use o template **Sugestão de melhoria**. Quanto mais concreto, melhor:

- qual problema você quer resolver;
- como é hoje e como poderia ser;
- quem se beneficia;
- impacto esperado e riscos;
- se você pode contribuir com código, testes ou documentação.

## RFCs

Mudanças maiores (novas APIs, mudanças de arquitetura, integrações, mudanças de
comportamento) devem virar um RFC em [`ideias/`](ideias/):

1. Copie `ideias/TEMPLATE.md` para `ideias/NNNN-titulo-curto.md`.
2. Preencha as seções.
3. Abra um PR **neste repositório**.
4. A discussão acontece no PR; ajustes são bem-vindos.

## Código

Depois que uma proposta for aceita:

1. Faça um fork de `capivara-rpa/capivara`.
2. Crie uma branch a partir de `next` (quando existir) ou de `main`.
3. Mantenha o padrão do projeto:
   - funções em português, com nomes descritivos;
   - logs automáticos (`logger.info/success/warning/error`);
   - erros de domínio com `ErroRPA`/`ErroCriticoRPA`;
   - segredos sempre via `.env`/cofre, nunca no código;
   - testes para o comportamento novo.
4. Rode antes de abrir o PR:

```bash
ruff check app core settings tests bot_test
pytest
python -m compileall app core settings tests bot_test
```

5. Abra o PR no repositório oficial, explicando o problema, a solução e como
   testar. Link a issue/RFC deste repositório.

## Commits

Use mensagens curtas no padrão:

```text
feat: adiciona função para ler e-mail IMAP
fix: corrige retry de item abandonado na fila
docs: explica o fluxo de agentes na rede local
test: cobre prioridade por item na fila
```

## Checklist do PR

- [ ] O problema e a solução estão descritos.
- [ ] O comportamento novo tem teste.
- [ ] `ruff`, `pytest` e `compileall` passam.
- [ ] Não há segredo, token ou dado sensível.
- [ ] A documentação foi atualizada quando necessário.
- [ ] A mudança não quebra a API pública sem discussão.

## Segurança

Não abra issue pública para vulnerabilidade. Siga o [`SECURITY.md`](SECURITY.md).

## Código de conduta

Ao participar, você concorda com o [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
