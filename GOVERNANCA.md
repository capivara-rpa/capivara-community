# Governança e fluxo de avaliação

## Papéis

| Papel | Responsabilidade |
|---|---|
| Comunidade | Abrir ideias, discutir, testar, enviar PRs |
| Mantenedores | Triar, avaliar, decidir e integrar |
| Repositório oficial | Código, releases e versão **stable** |
| Branch `next` (oficial) | Integração das propostas aceitas |
| Branch `main` (oficial) | Versão estável publicada |

## Fluxo

```text
Discussão / issue / RFC
        │
        ▼
   em-avaliacao
        │
   ┌────┴────┐
   ▼         ▼
 aceita    recusada
   │
   ▼
PR no repo oficial (next)
   │
   ▼
testes + revisão
   │
   ▼
merge em next → release → main
```

## Labels

| Label | Significado |
|---|---|
| `sugestao` | Ideia ou pedido de melhoria |
| `em-avaliacao` | Em triagem pelos mantenedores |
| `aceita` | Aprovada para virar PR |
| `recusada` | Fora de escopo ou não faz sentido agora |
| `precisa-de-mais-info` | Falta contexto para decidir |
| `rfc` | Proposta de mudança maior em `ideias/` |
| `documentacao` | Texto, guia ou tradução |
| `exemplo` | Robô, plugin ou caso de uso |
| `integracao` | Conexão com outra ferramenta/serviço |
| `boa-primeira-contribuicao` | Boa entrada para quem quer começar |

## Critérios de avaliação

- Alinhamento com o escopo da Capivara (RPA low-code em português).
- Impacto para a comunidade e frequência do problema.
- Complexidade de implementação e manutenção.
- Compatibilidade com a API pública e com a versão stable.
- Segurança, privacidade e tratamento de credenciais.
- Existência de testes e documentação possíveis.

## Decisões

- Toda decisão relevante é registrada na issue/RFC com o motivo.
- `aceita` não significa prazo garantido.
- Propostas recusadas podem voltar se o contexto mudar.
- Correções de segurança podem ir direto para a `main` quando necessário.
- Mudanças que quebram compatibilidade precisam de discussão explícita e plano
  de migração.

## Releases

- `main`: stable, pronta para uso.
- `next`: propostas aceitas em validação.
- Tags `v*`: releases da stable, com notas no repositório oficial.
- O snapshot da comunidade é avaliado antes de entrar em `next`.
