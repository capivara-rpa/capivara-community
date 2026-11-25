# Catálogo de Funções Low-Code

Todas as funções prontas do motor `core/`. Basta importar e usar — cada chamada
já registra log colorido automaticamente.

---

## 🧭 Navegador — `from core.rpa import Navegador`

Crie uma instância, inicie e use:

```python
navegador = Navegador()          # respeita AMBIENTE/HEADLESS do .env
navegador.iniciar()              # abre o Chrome
navegador.abrir_url("https://...")
# ... ações ...
navegador.capturar_tela("prova")
navegador.finalizar()
```

### Navegação

| Função | O que faz | Exemplo |
|---|---|---|
| `abrir_url(url)` | Navega até a URL | `navegador.abrir_url("https://exemplo.com")` |
| `abrir_site(url)` | Alias de `abrir_url` | — |
| `voltar_pagina()` | Volta uma página | — |
| `recarregar_pagina()` | Recarrega a página | — |
| `obter_url_atual()` | Retorna a URL atual | `url = navegador.obter_url_atual()` |
| `obter_titulo()` | Retorna o título da página | — |
| `aguardar_url_contem(fragmento)` | Espera a URL conter um texto | `navegador.aguardar_url_contem("/search")` |

### Elementos e ações

| Função | O que faz | Exemplo |
|---|---|---|
| `aguardar_elemento(seletor, descricao=)` | Espera o elemento aparecer | `navegador.aguardar_elemento("#login")` |
| `elemento_existe(seletor)` | True/False se existe | `if navegador.elemento_existe("#erro"):` |
| `elemento_visivel(seletor)` | True/False se visível | — |
| `clicar_elemento(seletor, descricao=)` | Clica | `navegador.clicar_elemento("//button")` |
| `clicar_por_texto(texto)` | Clica no texto | `navegador.clicar_por_texto("Enviar")` |
| `escrever_texto(seletor, texto, enter=)` | Digita no campo | `navegador.escrever_texto("#email", "a@b.com")` |
| `ler_texto(seletor)` | Lê o texto do elemento | `texto = navegador.ler_texto("#mensagem")` |
| `pegar_valor_campo(seletor)` | Valor do `value` | — |
| `pegar_atributo(seletor, atributo)` | Qualquer atributo | `navegador.pegar_atributo("img", "src")` |
| `pressionar_tecla("enter")` | Pressiona tecla | `navegador.pressionar_tecla("F5")` |
| `pressionar_enter()/tab()/escape()` | Atalhos de teclas | — |
| `pressionar_combinacao(*teclas)` | Atalho combinado | `navegador.pressionar_combinacao("CONTROL", "A")` |
| `selecionar_opcao(seletor, valor=)` | Select por valor/texto/índice | `navegador.selecionar_opcao("#uf", valor="SP")` |
| `marcar_checkbox(seletor, marcar=)` | Marca/desmarca | `navegador.marcar_checkbox("#termos")` |
| `fazer_upload(seletor, caminho)` | Anexa arquivo | `navegador.fazer_upload("input[type=file]", "doc.pdf")` |
| `arrastar_e_soltar(origem, destino)` | Drag and drop | — |

### Rolagem, tela e quadros

| Função | O que faz | Exemplo |
|---|---|---|
| `rolar_pagina(para='baixo')` | Rola a página | `navegador.rolar_pagina("fim")` |
| `rolar_ate_elemento(seletor)` | Rola até o elemento | — |
| `capturar_tela(nome)` | Salva print em `data/output/` | `navegador.capturar_tela("resultado")` |
| `entrar_iframe(seletor)` | Entra no iframe | — |
| `sair_iframe()` | Sai do iframe | — |
| `mudar_janela_por_titulo(titulo)` | Troca de aba/janela | — |
| `mudar_para_ultima_janela()` | Vai à aba mais recente | — |
| `fechar_janela_por_titulo(titulo)` | Fecha a aba | — |
| `aguardar_download(nome_parcial)` | Espera download terminar | — |
| `encontrar_ultimo_download()` | Último arquivo baixado | — |

> **Sobre selectores**: você pode passar XPATH (`//div[@id='x']`), ID (`@nome`)
> ou CSS (`#id`, `.classe`). Tudo é convertido sozinho.

---

## 📊 Dados — `from core.rpa import dados`

| Função | O que faz |
|---|---|
| `dados.ler_csv(caminho, separador=',')` | Lê CSV → DataFrame |
| `dados.ler_excel(caminho, aba=0)` | Lê planilha → DataFrame |
| `dados.ler_json(caminho)` | Lê JSON → DataFrame |
| `dados.listar_abas_excel(caminho)` | Lista as abas de um xlsx |
| `dados.escrever_csv(df, caminho)` | Salva DataFrame em CSV (separador `;`, UTF-8) |
| `dados.escrever_excel(df, caminho, aba=)` | Salva DataFrame em xlsx |
| `dados.escrever_planilha({aba: df}, caminho)` | Salva várias abas num xlsx |
| `dados.mostrar_df(df, n_linhas=10)` | Exibe tabela colorida no terminal |
| `dados.resumo_df(df)` | Dimensões + tipos + primeiras linhas |
| `dados.listar_colunas(df)` | Lista as colunas |
| `dados.contar_linhas(df)` | Conta linhas |
| `dados.filtrar_linhas(df, "condicao")` | Filtro estilo query (`estado == 'SP'`) |
| `dados.unir_tabelas(df1, df2, chave)` | Join por chave |
| `dados.agrupar_somar(df, por, colunas)` | GroupBy + soma |
| `dados.converter_para_texto(df)` | DataFrame → texto (anexo de e-mail, etc.) |

```python
from core.rpa import dados

df = dados.ler_csv("data/input/clientes.csv")
dados.mostrar_df(df)
sp = dados.filtrar_linhas(df, "estado == 'SP'")
dados.escrever_planilha({"Todos": df, "SP": sp}, "data/output/relatorio.xlsx")
```

---

## 📦 Arquivos — `from core.rpa import arquivo`

| Função | O que faz |
|---|---|
| `arquivo.listar_arquivos(pasta, extensao=)` | Lista arquivos (opcional filtro) |
| `arquivo.listar_pastas(pasta)` | Lista subpastas |
| `arquivo.criar_pasta(caminho)` | Cria pasta se faltar |
| `arquivo.ler_arquivo_texto(caminho)` / `escrever_arquivo_texto(...)` | Texto puro |
| `arquivo.copiar_arquivo(origem, destino)` | Copia |
| `arquivo.mover_arquivo(origem, destino)` | Move |
| `arquivo.renomear_arquivo(origem, novo_nome)` | Renomeia |
| `arquivo.apagar_arquivo(caminho, confirmar=True)` | Apaga (protegido) |
| `arquivo.baixar_arquivo(url, destino)` | Download com barra de progresso |
| `arquivo.compactar_pasta(pasta, destino)` | Zip de pasta |
| `arquivo.extrair_zip(zip, pasta_destino)` | Descompacta |

---

## 🌐 API — `from core.rpa.api import ClienteAPI, api_get, api_post`

| Função | O que faz |
|---|---|
| `ClienteAPI(base_url, token=, headers=)` | Cliente reutilizável com retry |
| `cliente.api_get(caminho, params=)` | GET com retry e log |
| `cliente.api_post(caminho, json=)` | POST com retry e log |
| `cliente.api_put(...)` / `api_delete(...)` | PUT / DELETE |
| `api_get(caminho)` / `api_post(caminho)` | Versão "padrão" usando o `.env` |

```python
from core.rpa.api import ClienteAPI

api = ClienteAPI(base_url="https://api.exemplo.com", token="meu-token")
resposta = api.api_get("/usuarios")
if resposta.status_code == 200:
    usuarios = resposta.json()
```

---

## ✉️ E-mail — `from core.rpa.email import enviar_email`

```python
enviar_email(
    destinatarios=["fulano@exemplo.com"],
    assunto="Relatório do robô",
    corpo="Segue em anexo.",
    anexos=["data/output/relatorio.xlsx"],
)
```

Usa SMTP do `.env` (`SMTP_SERVIDOR`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `SMTP_ORIGEM`).

---

## 🧩 Complementos — `from core.rpa import interacao`

| Função | O que faz |
|---|---|
| `dormir(segundos, motivo=)` | Pausa com explicação no log |
| `aguardar(segundos)` | Alias de dormir |
| `digitar_pausadamente(navegador, seletor, texto)` | Digita caractere a caractere |
| `copiar_para_area_transferencia(texto)` | Copia texto para o sistema |
| `colar_para_area_transferencia(navegador, seletor)` | Cola num campo |

---

## 🛡️ Tratador — `from core.tratador import passo, tentar_novamente`

```python
from core.tratador import passo, tentar_novamente

@passo("Fazer login no sistema")
@tentar_novamente(vezes=3, espera=2)
def fazer_login(navegador):
    navegador.abrir_url(SITE)
    navegador.escrever_texto("#usuario", "admin")
    navegador.escrever_texto("#senha", "123")
    navegador.clicar_elemento("#entrar")
    return navegador.elemento_existe("#painel")
```

- `@passo("descrição")` → loga início, sucesso ou erro do passo.
- `@tentar_novamente(vezes=3, espera=2)` → repete em caso de exceção.
- `ErroRPA` → erro controlado (dentro do fluxo).
- `ErroCriticoRPA` → encerra o processo (levanta abort no `Robo`).

---

## 🤖 Orquestrador — `from core.robo import Robo`

```python
from core.logger import configurar_logger
from core.robo import Robo

configurar_logger(nome_processo="meu-robo")
robo = Robo(nome="meu-robo")

se_ok = robo.executar_fluxo("Buscar no Google", buscar_no_google)
if not se_ok:
    robo.finalizar()
    exit(1)

robo.finalizar()
```

- `robo.iniciar(url=)` → abre o navegador.
- `robo.executar_fluxo(nome, funcao)` → roda a função injetando `navegador`,
  retorna `True`/`False` e registra tudo no log.
- `robo.finalizar()` → fecha o navegador com segurança.
- Os fluxos também podem ser usados com `Navegador` em contexto:

```python
with Navegador() as navegador:
    buscar_no_google(navegador)
```

---

## 🔐 Cofre / Credenciais v2 — `from core.rpa import vault`

Segredos ficam centralizados e cifrados na Lagoa (vault Fernet). O fluxo
busca na hora de usar — nada de senha no código nem no `.env`.

```python
from core.rpa import vault

usuario = vault.obter("portal_usuario")        # valor simples
senha = vault.exigir("portal_senha")           # igual, mas falha (ErroRPA) se faltar

cred = vault.buscar_credencial("portal")       # {nome, usuario, senha, tipo, versao}
vault.rotacionar("portal", "nova-senha")       # troca o valor e incrementa a versão
vault.versoes("portal")                        # histórico (valores mascarados)

# Criar/atualizar com tipo e usuário:
vault.definir("portal", "s3nh4", usuario="joao", tipo="segredo")
vault.definir("regiao_padrao", "SP", tipo="texto")   # texto = não cifrado
```

Dentro de um fluxo executado por um **agente**, use o contexto da máquina:

```python
def meu_fluxo(agente):
    cred = agente.credencial("portal")             # auditado com o nome da máquina
    usuario, senha = cred["usuario"], cred["senha"]
    # ou só um valor: agente.asset("portal_usuario")
```

- **Rotação/versões**: cada valor novo vira uma linha em `asset_versoes`
  (`GET /api/orq/assets/<nome>/versoes`).
- **Permissões por processo**: `POST /api/orq/assets/<nome>/permissoes`. Sem
  permissões o asset é aberto; com permissões, só o processo autorizado lê
  (`GET /api/orq/credenciais/<nome>?processo_id=`).
- **Auditoria** (append-only): criação, leitura, rotação e permissão vão para a
  tabela `auditoria` (`GET /api/orq/auditoria?recurso=&ator=`), visível na aba
  **Assets** do painel. Segredos que escapem para o log são mascarados
  automaticamente (`core/logger.py`). O painel exporta CSV
  (`GET /api/orq/auditoria/exportar`) e expurga os antigos
  (`POST /api/orq/auditoria/expurgar`; retenção `RETENCAO_AUDITORIA_DIAS`).

---

## 🛡️ Governança / identidade — `from core.control_room import servico`

Tudo local no SQLite (`data/orquestrador.db`), sem dependência externa.

- **Login / RBAC**: `LAGOA_AUTH=true` exige sessão no painel. Na primeira
  subida é criado o admin de `ADMIN_EMAIL`/`ADMIN_SENHA`. A sessão é um cookie
  `HttpOnly` válido por `SESSAO_HORAS`.

  ```python
  servico.garantir_admin_padrao()                 # cria admin + permissões padrão
  usuario = servico.autenticar("eu@empresa.com", "segredo")
  token = servico.criar_sessao(usuario)            # cookie
  sessao = servico.validar_sessao(token)           # {usuario, permissoes, ...}
  servico.apagar_sessao(token)
  ```

- **Usuários / papéis / permissões**: `criar_usuario`, `criar_papel`,
  `definir_permissoes_papel`, `atribuir_papel`, `criar_empresa` (multiempresa).
  Permissões padrão: `painel.ver`, `jobs.disparar`, `jobs.cancelar`,
  `processos.gerir`, `triggers.gerir`, `filas.gerir`, `assets.ler`,
  `assets.gerir`, `maquinas.gerir`, `usuarios.gerir`, `auditoria.ver`,
  `pacotes.instalar`.

- **Token por máquina**: `emitir_token_maquina(nome)` devolve o token (guardado
  só como hash) e `revogar_token_maquina(nome)` o invalida; o agente usa
  `--token`. O `LAGOA_TOKEN` global continua válido.

- **Cron**: `criar_trigger(processo_id, tipo="cron", expressao="*/15 9-18 * * seg-sex")`
  — 5 campos com `*`, `*/n`, `a-b`, listas e nomes de dia (`seg-sex`).

- **Agendamentos avançados**: `criar_trigger(..., dias_semana=[1,2,3,4,5],
  incluir_fins=False, incluir_feriados=False)` restringe os dias da semana
  (1=seg … 7=dom) e exclui fins de semana/feriados nacionais (cálculo próprio em
  `core/control_room/feriados.py`). `definir_trigger_ativo(id, ativo)` pausa/
  retoma e `disparar_trigger(id)` executa na hora. `apagar_processo(id)` remove
  o robô do catálogo e seus agendamentos.

- **Automações (pacotes)**: `pacote.instalar_zip(bytes|arquivo, senha=...)` extrai
  em `PASTA_ROBOS` e cadastra o processo; `pacote.remover(nome)` desinstala
  (arquivos + catálogo). Também dá para instalar de um **repositório Git público**:
  `pacote.instalar_git(url, ref=None)` clona (shallow) e instala igual ao `.zip`
  (cadastra a `origem`/`origem_ref` no processo), e `pacote.atualizar_git(url, ref=None)`
  clona de novo e **substitui** a versão instalada. Só aceita **HTTPS público**
  (e `http` em localhost/127.0.0.1, para dev/CI); exige o `git` no PATH. CLI:
  `python -m core.control_room.pacote empacotar|instalar|instalar-git <url> [--ref]`.
  `apagar_processo(id)` solta os vínculos (jobs, triggers, filas, permissões)
  antes de remover.

- **Ambiente isolado por robô**: se o robô tiver um `requirements.txt`,
  `ambiente.garantir_ambiente(nome)` cria/reutiliza um `.venv` na pasta do robô
  (atualiza o pip, instala as dependências) e devolve o interpretador; o agente
  então roda o robô via `executar_robo` (subprocess). Desligue com
  `RPA_INSTALAR_DEPENDENCIAS=false`. Modelo pronto em `TEMPLATE/`.

- **SLA**: `listar_alertas(limite_job)` lista jobs em execução acima de
  `LIMITE_JOB_SEGUNDOS`; `classificar_job(job)` devolve `ok/lento/excedido`.

- **Expurgo de auditoria**: `expurgar_auditoria(dias)` e
  `exportar_auditoria_csv(recurso, ator)`.

---

# 🧰 Utilidades novas (+50 funções)

Adicionadas na v1.1 do Capivara. Todas seguem o padrão do motor: nomes em
português, log automático e `ErroRPA` em caso de uso inválido.

## 📝 Texto — `from core.rpa import texto` (`core/rpa/texto.py`)

| Função | O que faz |
|---|---|
| `limpar_texto(texto, reduzir_espacos=True)` | Remove caracteres de controle e espaços sobrando |
| `remover_acentos(texto)` | Troca acentos pelas letras sem acento |
| `normalizar_espacos(texto)` | Junta tabs/quebras em um espaço |
| `slug(texto, separador="-")` | Gera identificador para URL/arquivo |
| `capitalizar_nome(nome)` | Capitaliza preservando `de/da/dos` |
| `extrair_numeros(texto)` | Lista grupos de dígitos |
| `extrair_emails(texto)` / `extrair_urls(texto)` | Listas únicas na ordem de aparição |
| `mascarar_email(email)` | `arthur@x.com` → `a****r@x.com` |
| `contar_palavras(texto)` | Conta palavras |
| `similaridade(a, b)` | Similaridade de 0.0 a 1.0 |
| `encontrar_padrao(texto, padrao, grupo=0)` | Todas as ocorrências de uma regex |
| `substituir_padrao(texto, padrao, substituto, contar=0)` | Substituição por regex |
| `truncar_texto(texto, limite=80, sufixo="...")` | Corta com sufixo |

```python
from core.rpa import texto

texto.slug("Relatório de Clientes 2026")        # 'relatorio-de-clientes-2026'
texto.extrair_emails("fale com a@b.com")        # ['a@b.com']
texto.capitalizar_nome("ana de souza")          # 'Ana de Souza'
```

## 🇧🇷 Validação / formatos BR — `from core.rpa import validacao` (`core/rpa/validacao.py`)

| Função | O que faz |
|---|---|
| `limpar_digitos(valor)` | Mantém só números |
| `validar_cpf(cpf)` / `formatar_cpf(cpf)` / `gerar_cpf(formatar=True)` | CPF completo |
| `validar_cnpj(cnpj)` / `formatar_cnpj(cnpj)` / `gerar_cnpj(formatar=True)` | CNPJ completo |
| `validar_cpf_ou_cnpj(documento)` | Detecta pelo tamanho |
| `formatar_documento(documento)` | Formata CPF ou CNPJ |
| `validar_cep(cep)` / `formatar_cep(cep)` | CEP |
| `validar_telefone_br(tel)` / `formatar_telefone_br(tel)` | Fixo/celular com DDD |
| `validar_email(email)` | Formato de e-mail |
| `validar_data(data, formato=)` | Data válida |
| `converter_data(data, de=, para=)` / `formatar_data_br(data)` | Conversão de datas |
| `adicionar_dias_uteis(data, dias, feriados=None)` | Soma/subtrai dias úteis |
| `dias_uteis_entre(inicio, fim, feriados=None)` | Conta dias úteis |
| `proximo_dia_util(data, feriados=None)` | Próximo dia útil |
| `idade(nascimento, referencia=None)` | Anos completos |
| `formatar_moeda_br(valor)` / `converter_moeda_br(texto)` | `R$ 1.234,56` ↔ `1234.56` |

```python
from core.rpa import validacao

validacao.validar_cpf("529.982.247-25")          # True
validacao.adicionar_dias_uteis("2026-01-02", 1)  # date(2026, 1, 5)
validacao.formatar_moeda_br(1234.56)             # 'R$ 1.234,56'
```

## 🗄️ Banco SQLite — `from core.rpa import banco` (`core/rpa/banco.py`)

| Função | O que faz |
|---|---|
| `conectar(caminho=":memory:")` | Abre conexão (row factory por nome) |
| `executar(conexao, sql, parametros=())` | SQL livre com commit |
| `consultar(conexao, sql, parametros=())` | SELECT → lista de dicionários |
| `consultar_dataframe(conexao, sql, parametros=())` | SELECT → DataFrame |
| `inserir(conexao, tabela, dados)` | INSERT e devolve o id |
| `atualizar(conexao, tabela, dados, onde, parametros_onde=())` | UPDATE |
| `apagar(conexao, tabela, onde, parametros=())` | DELETE |
| `listar_tabelas(conexao)` / `tabela_existe(conexao, tabela)` | Metadados |
| `descrever_tabela(conexao, tabela)` | Colunas, tipos e PK |
| `contar_registros(conexao, tabela, onde=None, parametros=())` | COUNT |
| `criar_tabela(conexao, tabela, colunas, chave_primaria=None)` | CREATE TABLE |
| `importar_csv(conexao, tabela, caminho, separador=",")` | CSV → tabela |
| `exportar_csv(conexao, tabela, caminho, separador=";")` | Tabela → CSV |
| `fechar(conexao)` | Fecha a conexão |

```python
from core.rpa import banco

con = banco.conectar("data/input/dados.db")
banco.criar_tabela(con, "clientes", {"id": "INTEGER", "nome": "TEXT"}, "id")
banco.inserir(con, "clientes", {"nome": "Ana"})
banco.consultar(con, "SELECT * FROM clientes WHERE nome = ?", ("Ana",))
banco.fechar(con)
```

## 🔐 Segurança — `from core.rpa import seguranca` (`core/rpa/seguranca.py`)

| Função | O que faz |
|---|---|
| `gerar_senha(tamanho=16, simbolos=True)` | Senha forte aleatória |
| `gerar_token(tamanho=32)` | Token URL-safe |
| `hash_sha256(texto)` / `hash_arquivo(caminho, algoritmo="sha256")` | Hashes |
| `base64_codificar(texto)` / `base64_decodificar(texto)` | Base64 |
| `criptografar_texto(texto, chave=None)` / `descriptografar_texto(token, chave=None)` | Fernet (usa `VAULT_CHAVE` se omitida) |
| `mascarar_segredo(valor, manter=2)` | Mascara para log |
| `comparar_seguro(a, b)` | Comparação em tempo constante |
| `gerar_uuid()` | UUID v4 |

```python
from core.rpa import seguranca

token = seguranca.criptografar_texto("segredo", chave="minha-frase")
seguranca.descriptografar_texto(token, chave="minha-frase")
seguranca.mascarar_segredo("123456")   # '****56'
```

## 🖥️ Sistema — `from core.rpa import sistema` (`core/rpa/sistema.py`)

| Função | O que faz |
|---|---|
| `executar_comando(comando, pasta=None, tempo_max=60, verificar=False)` | Roda comando e devolve `{codigo, saida, erro}` |
| `abrir_programa(programa, argumentos=None)` | Abre executável/.app |
| `abrir_pasta(caminho)` / `abrir_arquivo(caminho)` | Abre no programa padrão |
| `obter_variavel_ambiente(nome, padrao=None)` / `definir_variavel_ambiente(nome, valor)` | Env vars |
| `obter_info_sistema()` | SO, Python, máquina, usuário, pasta |
| `pasta_temporaria()` | Pasta temp do SO |
| `esperar_arquivo(caminho, tempo_max=60)` / `esperar_pasta(...)` | Aguarda aparecer |
| `notificar_desktop(titulo, mensagem)` / `tocar_som()` | Aviso nativo |

## 🔔 Notificações — `from core.rpa import notificacoes` (`core/rpa/notificacoes.py`)

| Função | O que faz |
|---|---|
| `enviar_webhook(url, payload, timeout=30)` | POST JSON genérico |
| `enviar_slack(webhook, mensagem, titulo=None)` | Incoming Webhook do Slack |
| `enviar_teams(webhook, mensagem, titulo=None)` | MessageCard do Teams |
| `enviar_discord(webhook, mensagem, usuario="Capivara")` | Webhook do Discord |
| `enviar_telegram(bot_token, chat_id, mensagem)` | Telegram Bot API |

```python
from core.rpa import notificacoes

notificacoes.enviar_slack(webhook, "Relatório gerado!", titulo="Robô de clientes")
notificacoes.enviar_telegram(BOT_TOKEN, CHAT_ID, "Job concluído ✅")
```

## ➕ Extensões nos módulos existentes

| Módulo / arquivo | Funções novas |
|---|---|
| `arquivo` (`core/rpa/arquivo.py`) | `ler_json`, `escrever_json`, `ler_ini`, `escrever_ini`, `calcular_hash`, `comparar_arquivos`, `ler_ultimas_linhas`, `contar_linhas_arquivo`, `substituir_no_arquivo`, `juntar_arquivos`, `dividir_arquivo`, `tamanho_arquivo` |
| `dados` (`core/rpa/dados.py`) | `renomear_colunas`, `remover_duplicados`, `preencher_vazios`, `substituir_valores`, `ordenar_df`, `selecionar_colunas`, `dividir_df`, `amostrar_df`, `resumo_estatistico`, `dataframe_para_markdown`, `tratar_datas`, `calcular_percentual`, `pivotar`, `derreter` |
| `api` (`core/rpa/api.py`) | `ClienteAPI.api_patch/api_head/api_upload/api_download` + `api_put`, `api_delete`, `api_patch`, `api_upload`, `api_download` |
| `email` (`core/rpa/email.py`) | `enviar_email(..., html=True, cc=, bcc=, responder_para=)`, `enviar_email_html`, `testar_smtp` |
| `tracktab` (`core/rpa/tracktab.py`) | `obter`, `buscar`, `listar_nomes`, `para_lista`, `exportar_csv`, `resumo`, `combinar` |

### Navegador (novas ações em `core/rpa/browser.py`)

| Função | O que faz |
|---|---|
| `obter_texto_pagina()` / `obter_html()` | Texto visível / HTML completo |
| `contar_elementos(seletor)` | Quantos elementos casam |
| `aguardar_pagina_carregar()` | Espera `document.readyState` |
| `aguardar_texto_na_pagina(texto)` | Espera texto aparecer |
| `aguardar_elemento_sumir(seletor)` | Espera o elemento sumir |
| `clicar_se_existir(seletor)` | Clica só se existir |
| `limpar_campo(seletor)` / `focar_elemento(seletor)` | Limpa / foca |
| `executar_js(script, *args)` | Executa JavaScript |
| `obter_opcoes_select(seletor)` / `obter_valor_select(seletor)` | Opções / valor do select |
| `ler_tabela(seletor)` | Tabela HTML → lista de linhas |
| `capturar_elemento(seletor, nome)` | Print só do elemento |
| `obter_cookies()` / `adicionar_cookie(...)` | Cookies da sessão |
| `salvar_cookies(caminho)` / `carregar_cookies(caminho)` | Persistência de cookies |
| `abrir_nova_aba(url=None)` / `fechar_aba_atual()` / `mudar_para_aba(indice=-1)` | Abas |
| `aceitar_alerta()` / `recusar_alerta()` / `obter_texto_alerta()` | Alertas/diálogos |

> Resumo: **+50 funções novas** (texto, validação BR, banco, segurança, sistema,
> notificações) **+ extensões** em arquivos, dados, API, e-mail, navegador e
> TrackTab. Tudo coberto por pytest (`tests/test_texto.py`,
> `test_validacao.py`, `test_banco.py`, `test_rpa_seguranca.py` e
> `test_utilidades.py`).
