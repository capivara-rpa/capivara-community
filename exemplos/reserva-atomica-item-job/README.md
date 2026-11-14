# Reserva atômica de item e job

Código e 14 casos de teste da [PR original capivara-rpa/capivara#1](https://github.com/capivara-rpa/capivara/pull/1),
idênticos ao commit [`89146c1`](https://github.com/guilhermefabio/capivara/commit/89146c19fcc5253b5b241e47cbaab30e102a7f04).
A reserva usa uma transação SQLite para reverter item, job, vínculos, máquina
e round-robin se qualquer etapa falhar.

Requer Git, Python >=3.11, ambiente virtual ativo e o restante do projeto
oficial. A partir da raiz do Community, prepare a base e aplique os dois arquivos:

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

Validação: **161 testes passaram**, Ruff e compilação passaram, no Windows
com Python 3.12.13 e SQLite 3.50.4. Permanece um aviso preexistente de pandas.
Os testes usam bancos temporários e dados fictícios.
