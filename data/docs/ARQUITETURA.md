# Arquitetura

Este documento explica como o template se organiza por dentro, para que a
comunidade possa estender com confiança.

## Visão geral

```
┌────────────────────────────────────────────────────────────┐
│ app/  (SEU código)                                        │
│  main.py ──► registra e executa os fluxos                  │
│  fluxos/ ──► cada arquivo = uma tarefa de negócio          │
└───────────────┬────────────────────────────────────────────┘
                │ importa e usa
┌───────────────▼────────────────────────────────────────────┐
│ core/  (motor reutilizável)                               │
│  rpa.browser   → Selenium, ações descritivas               │
│  rpa.dados     → pandas, planilhas                         │
│  rpa.arquivo   → filesystem, downloads                     │
│  rpa.api       → requests, com retry                       │
│  rpa.email     → smtplib                                   │
│  rpa.interacao → teclado/área de transferência             │
│  robo.py       → orquestra fluxos + navegador              │
│  logger.py     → Loguru colorido                           │
│  tratador.py   → @passo, @tentar_novamente, exceções       │
└───────────────┬────────────────────────────────────────────┘
                │ lê parâmetros
┌───────────────▼────────────────────────────────────────────┐
│ settings/ (configuração)                                  │
│  parametros.py → dev/prod, tempos, caminhos, credenciais   │
│  ambiente.py   → carrega .env (dotenv)                     │
└────────────────────────────────────────────────────────────┘
```

## Regras de dependência

1. **`app` depende de `core` e `settings`** — nunca o contrário.
2. **`core` depende de `settings`** (para ler configuração) e das libs externas.
3. **`settings` é "folha"**: não importa `app` nem `core`.

Seguir isso mantém o template fácil de atualizar e de ler.

## Fluxo de execução

```
python app/main.py
   │
   ├─ configura o logger colorido
   ├─ interpreta argumentos (--web, --dados, ou todos)
   ├─ cria Robo(nome="capivara")
   │    └─ cria Navegador()   (headless se AMBIENTE=prod)
   ├─ para cada fluxo registrado:
   │    └─ robo.executar_fluxo(nome, funcao)
   │         ├─ loga "► Iniciando fluxo: ..."
   │         ├─ injeta o navegador na função
   │         ├─ recebe True / or lança exceção
   │         └─ loga sucesso ou erro crítico
   ├─ se algum fluxo falhar → robo.finalizar() e código de saída 1
   └─ robo.finalizar() (fecha o navegador)
```

## Por que cada módulo existe

| Módulo | Responsabilidade | "Gatilho" para mexer |
|---|---|---|
| `core/rpa/browser.py` | Abstrair o Selenium | Site exige comportamento novo (ex.: shadow DOM, autenticação). |
| `core/rpa/dados.py` | Abstrair pandas | Novas formas de tratar dados (ex.: integração com banco). |
| `core/rpa/arquivo.py` | Filesystem + downloads | Novos tipos de arquivo (ex.: PDF). |
| `core/rpa/api.py` | HTTP com retry | Novos padrões de autenticação de API. |
| `core/rpa/email.py` | SMTP | Novos formatos de e-mail (ex.: HTML). |
| `core/robo.py` | Ciclo de vida e fluxos | Mudar como passos se agrupam. |
| `core/logger.py` | Formatação de logs | Personalizar cores/formato. |
| `core/tratador.py` | Erros e retry | Política de tolerância a falhas. |
| `settings/parametros.py` | Configuração | Adicionar parâmetros do projeto. |

## Como criar um novo módulo no motor

Exemplo: suporte a **banco de dados SQL**.

1. Crie `core/rpa/banco.py` com funções em português (`conectar`, `consultar`,
   `executar`), com logs (`logger.success(...)`) e exceções `ErroRPA`.
2. Importe em `core/rpa/__init__.py` para expor como `from core.rpa import banco`.
3. Documente em `data/docs/CATALOGO_FUNCOES.md`.
4. (Opcional) adicione a dependência no `requirements.txt`.

## Decisões técnicas (e por quê)

- **Selenium + Selenium Manager**: driver baixado automaticamente; sem passos
  manuais de instalação — essencial para iniciantes.
- **Loguru + rich**: logs coloridos sem configuração complexa e tabelas bonitas
  no terminal (feedback rápido durante o desenvolvimento).
- **`.env` via python-dotenv**: segredos fora do código, em qualquer ambiente.
- **`python app/main.py` de qualquer lugar**: o `main.py` insere a raiz no
  `sys.path`, então funciona também em Docker e agendadores.
- **Funções com nomes em português**: abaixa a barreira de entrada para o
  público iniciante da comunidade.