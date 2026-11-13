# 0001 — Reserva atômica de item e job na Control Room

- **Autor:** [@guilhermefabio](https://github.com/guilhermefabio)
- **Data:** 2026-11-13
- **Status:** em avaliação
- **Área:** Control Room / filas

## Problema

Em `reservar_item_e_job()`, a reserva do item, a atualização da máquina, o
avanço do round-robin, a criação do job e os vínculos item/job são persistidos
por conexões e transações separadas. Se a criação do job falhar, o item fica
em `em_processamento`, com uma tentativa consumida, mas sem job. Uma nova
chamada não consegue reservar esse item.

Isso afeta agentes que consomem filas com executores e pode interromper o
processamento mesmo depois de removida a causa da falha.

A reprodução usa a base
[`a4ea91d59a7c2808b5fb66c26454c5164e726e67`](https://github.com/capivara-rpa/capivara/commit/a4ea91d59a7c2808b5fb66c26454c5164e726e67)
e um trigger SQLite real que aborta o `INSERT` em `jobs`.

| Estado após a falha injetada | Base original | Implementação proposta |
|---|---|---|
| Status / tentativas do item | `em_processamento` / 1 | `novo` / 0 |
| Máquina atribuída ao item | Preenchida | `NULL` |
| Job e vínculos | Nenhum job; item sem `job_id` | Nenhum job ou vínculo persistido |
| Round-robin | Avança | Mantém o valor anterior |
| Estado da máquina | `ocupada` | Retorna ao estado anterior |
| Nova reserva após remover a falha | Não retorna o item | Retorna o mesmo item e seu job |

## Proposta

Executar toda a reserva em uma única conexão SQLite, iniciada com
`BEGIN IMMEDIATE`, antes de ler a fila e selecionar o executor:

1. Consultar a fila e registrar ou atualizar a máquina.
2. Reivindicar o próximo item `novo`, por prioridade e depois por ID.
3. Marcar a máquina como ocupada e selecionar os executores da fila.
4. Avançar o round-robin e criar o job quando houver executor.
5. Gravar os dois vínculos, `jobs.item_id` e `itens_fila.job_id`.
6. Confirmar tudo ao sair do contexto da conexão; qualquer exceção reverte
   todas as alterações da transação.

Helpers privados recebem a conexão do chamador, evitando commits
intermediários. As assinaturas públicas e o formato de retorno continuam iguais:

```python
resposta = servico.reservar_item_e_job("clientes", "agente-01")
item, job = resposta["item"], resposta["job"]
```

Fila inexistente, pausada ou vazia continua retornando
`{"item": None, "job": None}`. Fila sem executor continua reservando o item
sem criar job. A prioridade, a ordem do round-robin e os metadados da máquina
são preservados.

### Implementação existente e preservação do histórico

Esta RFC direciona à Community a contribuição da
[PR original capivara-rpa/capivara#1](https://github.com/capivara-rpa/capivara/pull/1),
conforme orientação do mantenedor. Na verificação de 2026-11-13, essa PR já
estava fechada, sem merge; esta migração não altera seu estado.

O único commit da contribuição é
[`89146c19fcc5253b5b241e47cbaab30e102a7f04`](https://github.com/guilhermefabio/capivara/commit/89146c19fcc5253b5b241e47cbaab30e102a7f04),
com a mensagem `feat: implement atomic reservation for items and jobs with SQLite transactions`.
Ele permanece na branch `fix/atomic-queue-item-job-reservation` do fork
`guilhermefabio/capivara`, com seu conteúdo e autoria originais:

- [core/control_room/servico.py](https://github.com/guilhermefabio/capivara/blob/89146c19fcc5253b5b241e47cbaab30e102a7f04/core/control_room/servico.py):
  transação compartilhada e helpers privados.
- [tests/test_reserva_atomica.py](https://github.com/guilhermefabio/capivara/blob/89146c19fcc5253b5b241e47cbaab30e102a7f04/tests/test_reserva_atomica.py):
  14 casos de regressão, compatibilidade e concorrência.

O diff contém somente esses dois arquivos, com 364 inserções e 74 remoções.
Os links usam o SHA completo para identificar exatamente a versão avaliada.

O Community tem histórico próprio e recebe propostas em `ideias/`; não contém
o pacote `core` nem a suíte Python do oficial. Por isso, este PR adiciona
somente a RFC. A implementação existente fica referenciada, sem copiar o
núcleo para uma estrutura incompatível ou unir os históricos dos repositórios.

Após aceite pelos mantenedores, o commit pode ser reaproveitado em uma branch
do oficial baseada em `next`, conforme `CONTRIBUTING.md` e `GOVERNANCA.md`.
Por exemplo, em um novo clone, após conferir se o estado de `next` exige adaptação:

```bash
git clone https://github.com/capivara-rpa/capivara.git capivara-integracao
cd capivara-integracao
git switch -c fix/reserva-atomica-item-job origin/next
git fetch https://github.com/guilhermefabio/capivara.git fix/atomic-queue-item-job-reservation
git cherry-pick -x 89146c19fcc5253b5b241e47cbaab30e102a7f04
```

O cherry-pick futuro cria um novo SHA no histórico de destino, preservando a
autoria e registrando a origem com `-x`. A integração em `next` e a revalidação
são etapas posteriores ao aceite, não realizadas por esta RFC.

## Alternativas consideradas

- **Repetir a chamada após falha:** não recupera o item já reservado sem job.
- **Compensar com atualizações após a exceção:** a compensação também pode
  falhar e deixa estados intermediários observáveis por outros consumidores.
- **Usar um lock Python:** não coordena agentes em processos diferentes nem
  fornece rollback no banco.
- **Levar a branch de código diretamente ao Community:** não corresponde à
  organização deste repositório; a implementação segue para o oficial após aceite.

## Impacto

- **Quem se beneficia:** agentes e operadores que usam filas da Control Room,
  especialmente com múltiplos consumidores e executores.
- **API pública:** nenhuma nova assinatura ou alteração no formato de retorno.
  Exceções do SQLite continuam propagando ao chamador.
- **Compatibilidade com stable:** sem mudança de esquema ou migração de dados;
  mantém filas sem executor, prioridade e round-robin. Não recupera itens que
  já estavam presos antes da correção.
- **Segurança/privacidade:** não adiciona credenciais, dados reais ou mudanças
  nas regras de acesso. Os testes usam dados fictícios e bancos temporários.
- **Performance:** a transação mantém o lock de escrita por mais operações.
  O teste com seis consumidores verifica correção, não é um benchmark de carga.

## Testes

Validação repetida em 2026-11-13, Windows, Python 3.12.13 e SQLite 3.50.4:

- Suíte completa da implementação: **161 testes passaram**, incluindo os
  14 casos novos. Um aviso existente de pandas em
  `test_transformacoes_de_dataframe` permanece, fora do escopo desta proposta.
- `ruff check app core settings tests bot_test`: passou.
- `python -m compileall -q app core settings tests bot_test`: passou.
- `git diff --check`: passou.
- O mesmo teste `test_falha_criacao_job_reverte_reserva`, com arquivo idêntico,
  executado sobre a base original, **falhou como esperado**: item preso,
  round-robin avançado e máquina ocupada. Na implementação corrigida ele passa.

Os 14 casos cobrem falhas na criação do job, em ambos os vínculos, no
round-robin e no status da máquina; rollback do cadastro de máquina nova;
prioridade e metadados; filas inexistente, pausada, vazia ou sem executor;
executor extra; seis consumidores concorrentes com um e com 24 itens,
verificando reservas únicas, vínculos e ordem exata do round-robin.

Para validar a implementação referenciada em um novo clone, com Python >=3.11
e ambiente virtual ativo:

```bash
git clone https://github.com/guilhermefabio/capivara.git capivara-reserva-atomica
cd capivara-reserva-atomica
git checkout --detach 89146c19fcc5253b5b241e47cbaab30e102a7f04
python -m pip install -r requirements.txt pytest ruff
python -m pytest tests/test_reserva_atomica.py
python -m pytest
python -m ruff check app core settings tests bot_test
python -m compileall -q app core settings tests bot_test
```

Para reproduzir o defeito, use um segundo clone na base `a4ea91d59a7c2808b5fb66c26454c5164e726e67`,
copie apenas `tests/test_reserva_atomica.py` da implementação referenciada e rode
`python -m pytest tests/test_reserva_atomica.py::test_falha_criacao_job_reverte_reserva`.
Esse teste deve falhar na base e passar com a correção. O `tests/conftest.py`
isola os bancos em diretórios temporários.

O Community não possui suíte executável ou CI configurada nesta base. A
validação deste PR verifica o template, as referências, o escopo e a formatação
da RFC; os resultados Python acima pertencem ao código referenciado.

## Documentação

Esta RFC documenta a garantia de atomicidade e a reprodução do problema.
Após aceite e integração, documentar essa garantia junto à descrição de filas
da Control Room no `GUIA.md` do oficial, incluindo o comportamento após falha.
Não há nova função pública para acrescentar ao catálogo.

## Riscos e decisões

- Avaliar a contenção de escrita e o timeout SQLite em cargas reais. Não se
  propõe retry automático nem alteração do timeout nesta contribuição.
- A atomicidade cobre apenas persistência SQLite, sem incluir efeitos externos
  de execução do robô.
- Recuperar itens já presos, mudar o scheduler, alterar autenticação ou criar
  novas APIs fica fora do escopo.
- A proposta depende de avaliação dos mantenedores; a implementação existente
  não implica aprovação nem prazo de integração.

## Critérios de aceite

- [ ] Mantenedores aceitam a garantia transacional e o escopo desta RFC.
- [ ] Falhas em qualquer etapa revertem item, job, vínculos, máquina e round-robin.
- [ ] Prioridade, filas sem executor, metadados e API pública permanecem compatíveis.
- [ ] Consumidores concorrentes não duplicam reservas nem jobs.
- [ ] Implementação reaproveitada em `next`, com testes, Ruff e compilação passando.
- [ ] Garantia documentada no guia do oficial antes do release estável.
