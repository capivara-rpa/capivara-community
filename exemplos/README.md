# Exemplos e plugins da comunidade

Este espaço é para robôs de exemplo, conectores e plugins que mostram a Capivara
em cenários reais. Exemplos pequenos e bem documentados ajudam mais do que
projetos gigantes.

## O que enviar

- um caso de uso completo (entrada, processamento e saída);
- um conector para um serviço (planilha, API, banco, mensageria);
- um fluxo de Control Room (fila, agendamento, agente);
- uma integração com outra ferramenta.

## Regras

- Nada de token, senha, dado de cliente ou informação pessoal.
- Use dados fictícios ou um `.env.example`.
- Explique o pré-requisito e como rodar.
- Prefira dependências que já existem no projeto; se adicionar alguma, justifique.
- Um exemplo não entra automaticamente no núcleo: ele é avaliado e pode virar
  documentação, template ou função oficial.

## Como enviar

Abra uma issue com o template **Sugestão de melhoria** escolhendo “Exemplo ou
plugin”, ou envie um PR com uma pasta:

```text
exemplos/nome-do-exemplo/
├── README.md
├── main.py
├── rpa.json
└── requirements.txt (opcional)
```

O `README.md` deve dizer o que o exemplo faz, o que precisa e como executar.
