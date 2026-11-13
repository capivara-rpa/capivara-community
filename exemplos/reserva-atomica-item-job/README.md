# Reserva atômica de item e job

Implementação completa da [PR original capivara-rpa/capivara#1](https://github.com/capivara-rpa/capivara/pull/1),
acompanhada dos testes de rollback, compatibilidade e concorrência.

Quando a criação do job falha, a reserva deve reverter também o item, a
máquina, os vínculos e o round-robin. A implementação usa uma única conexão
SQLite e uma transação `BEGIN IMMEDIATE` para garantir esse comportamento.

## Código incluído

- [`core/control_room/servico.py`](core/control_room/servico.py): arquivo completo
  com a implementação da reserva e seus helpers.
- [`tests/test_reserva_atomica.py`](tests/test_reserva_atomica.py): arquivo completo
  com os 14 casos de teste da contribuição.

Os dois arquivos são idênticos, byte a byte, às versões do commit original
[`89146c19fcc5253b5b241e47cbaab30e102a7f04`](https://github.com/guilhermefabio/capivara/commit/89146c19fcc5253b5b241e47cbaab30e102a7f04),
de [@guilhermefabio](https://github.com/guilhermefabio), na branch
`fix/atomic-queue-item-job-reservation`. A origem do commit permanece registrada
também na [RFC](../../ideias/0001-reserva-atomica-item-job.md).

| Arquivo | Blob Git original |
|---|---|
| `core/control_room/servico.py` | `c744f2864c8ff997b24d0eb0edfb2b83fa7e2853` |
| `tests/test_reserva_atomica.py` | `7020fd22dd053f260411692120978b0b0ddb38f0` |

## Pré-requisitos

Python >=3.11, Git e um ambiente virtual ativo. O código depende do restante
do projeto oficial Capivara; use a base fixada abaixo para reproduzir a PR.
Nenhuma dependência de produção foi adicionada pela contribuição.

## Como executar

A partir da **raiz do clone do Community**, prepare uma cópia isolada da base
oficial e aplique os arquivos Python incluídos neste exemplo:

```bash
git clone https://github.com/capivara-rpa/capivara.git .venv/capivara-reserva-validacao
git -C .venv/capivara-reserva-validacao checkout --detach a4ea91d59a7c2808b5fb66c26454c5164e726e67
python -c "from pathlib import Path; from shutil import copyfile; origem=Path('exemplos/reserva-atomica-item-job'); destino=Path('.venv/capivara-reserva-validacao'); arquivos=('core/control_room/servico.py', 'tests/test_reserva_atomica.py'); [copyfile(origem/nome, destino/nome) for nome in arquivos]"
cd .venv/capivara-reserva-validacao
python -m pip install -r requirements.txt pytest ruff
python -m pytest tests/test_reserva_atomica.py
python -m pytest
python -m ruff check app core settings tests bot_test
python -m compileall -q app core settings tests bot_test
git diff --check
```

A pasta de validação fica em `.venv/`, ignorada pelo Community. Os testes usam
o `tests/conftest.py` da base oficial para isolar bancos e cofre em diretórios
temporários, com dados fictícios.

Para observar o defeito na mesma cópia de validação, restaure somente o serviço
da base, mantendo o arquivo de testes da contribuição:

```bash
git restore --source=a4ea91d59a7c2808b5fb66c26454c5164e726e67 -- core/control_room/servico.py
python -m pytest tests/test_reserva_atomica.py::test_falha_criacao_job_reverte_reserva
```

O teste deve falhar: o item permanece reservado sem job. Para voltar à versão
corrigida, repita a cópia dos dois arquivos a partir da raiz do Community.

## Resultado da validação

Windows, Python 3.12.13 e SQLite 3.50.4: **161 testes passaram**, incluindo os
14 casos novos; Ruff, compilação e verificação do diff passaram. Um aviso
preexistente de pandas permanece em `test_transformacoes_de_dataframe`.

O teste de regressão isolado falha na base original e passa com o serviço
corrigido. A integração ao núcleo oficial continua sujeita à avaliação dos
mantenedores, conforme a RFC e a governança do Community.
