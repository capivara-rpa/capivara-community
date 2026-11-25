# TEMPLATE — publicar um robô na Lagoa

Ponto de partida para publicar sua automação na aba **Automações**.

## Estrutura do .zip

```
meu_robo/
  rpa.json      ← manifesto (obrigatório)
  main.py       ← arquivo de entrada (a função de dentro dele é executada)
  ...           ← quaisquer outros arquivos do seu projeto
```

Pode ter uma pasta raiz (como `meu_robo/`) ou os arquivos soltos — o que importa é
o `rpa.json` ficar na origem do robô.

A estrutura interna é **livre**: você pode ter quantas pastas quiser (`app/`,
`core/`, `functions/`, `src/`…). Tudo é extraído junto em `app/robos/<nome>/`, e o
`entrada` pode apontar para um arquivo dentro de subpasta (ex.: `"src/main.py"`).

```
meu_robo/
  rpa.json
  src/
    main.py            ← entrada: "src/main.py"
    functions/
      auxiliar.py
  dados/planilha.xlsx
```

Para importar outros arquivos do robô, use **import relativo** ou o caminho do
pacote (o robô vira o pacote `app.robos.<nome>`):

```python
from .functions.auxiliar import minha_funcao   # relativo ao próprio robô
# ou
from app.robos.meu_robo.functions.auxiliar import minha_funcao
```

## Campos do `rpa.json`

| Campo           | Obrigatório | Descrição                                                        |
|-----------------|-------------|------------------------------------------------------------------|
| `nome`          | sim         | Nome do robô: minúsculas, números, `-` e `_`.                    |
| `entrada`       | sim         | Arquivo `.py` que contém a função.                               |
| `funcao`        | sim         | Nome da função dentro do arquivo de entrada.                     |
| `versao`        | não         | Versão do robô (default `1.0.0`).                                |
| `descricao`     | não         | Texto exibido no catálogo de processos.                          |
| `usa_navegador` | não         | `true` se o robô usa o navegador (abre o Chrome automaticamente).|

> No lugar (ou além) do `.zip`, você pode **instalar direto de um repositório Git
> público**: coloque este robô (com o `rpa.json`) num repositório e use
> **Automações → Instalar do Git** informando a URL HTTPS e, se quiser, o
> branch/tag. Robôs de Git ganham o botão **Atualizar** (clona de novo e substitui
> a versão em uso com um clique). Requer o `git` instalado na máquina da Lagoa.

## Dependências próprias (requirements.txt)

Se o robô precisar de bibliotecas que o agente não tem, coloque um
`requirements.txt` na **raiz do robô** (há um `requirements.exemplo.txt` aqui —
renomeie para ativar). Ao executar, o agente:

1. cria um `.venv` isolado dentro da pasta do robô (se ainda não existir);
2. atualiza o pip (`python -m pip install --upgrade pip`);
3. instala as dependências (`pip install -r requirements.txt`);
4. executa o robô com o Python desse `.venv`.

O `.venv` é reaproveitado enquanto o `requirements.txt` não mudar. Para desligar
esse comportamento (sempre usar o ambiente do agente), defina
`RPA_INSTALAR_DEPENDENCIAS=false` no `.env`.

## Passo a passo

```bash
# 1. (opcional) ajuste nome/descricao no rpa.json e escreva sua automação
# 2. empacote (gera meu_robo.zip); --senha cifra o zip com AES
python -m core.control_room.pacote empacotar TEMPLATE/ --saida meu_robo.zip

# ou envie direto para a Lagoa sem gerar arquivo:
python -m core.control_room.pacote instalar meu_robo.zip --lagoa http://127.0.0.1:8765

# ou instale de um repositório Git público (com o rpa.json na raiz do repo):
python -m core.control_room.pacote instalar-git https://github.com/usuario/meu-robo.git --ref main
```

Ou, pela interface: **Automações → Enviar .zip** ou **Automações → Instalar do Git**.

## A função executada

O agente importa `app.robos.<nome>.<entrada>:<funcao>` e roda o robô. Ela recebe
**apenas** os parâmetros que declarar:

```python
def rodar(navegador=None, agente=None, item=None):
    ...
    return True   # True = sucesso; exceção/False = falha
```

- `navegador`: Chrome já aberto (quando `usa_navegador` = true).
- `agente`: `agente.asset("x")`, `agente.credencial("portal")`, `agente.cancelado()`.
- `item`: o item da fila em processamento.

## Observações

- O robô roda **dentro do ambiente do agente**: as dependências dele (pandas,
  selenium, etc.) precisam estar instaladas na máquina onde o agente roda.
- **A Lagoa não distribui o código do robô para os agentes.** O upload/instalação
  pela Lagoa cadastra o processo no servidor; cada máquina que for executá-lo
  precisa ter o código localmente (clone do repo, `git pull` ou cópia da pasta).
- Upload só **instala e cadastra** o processo; executar é disparar um **job**
  (aba Jobs) ou criar um **agendamento** (aba Agendamentos).
- O agente **empacotado** (PyInstaller) não importa robôs externos — use o agente
  rodando do fonte (`.venv`) para consumir automações publicadas.
