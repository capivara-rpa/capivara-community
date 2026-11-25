# Evidências de instalação — capivara-rpa 1.2.0a1

Data do teste: 2026-11-16 (aprox. 17:26–17:31, -03)
Pacote: `capivara-rpa==1.2.0a1` (alpha no TestPyPI)
Índice: <https://test.pypi.org/project/capivara-rpa/1.2.0a1/>

## Ambiente

- macOS 27.0.1 (build 26A434)
- Python 3.11.15 (`/usr/local/bin/python3.11`)
- Homebrew 7.0.14
- Instalações feitas em diretórios temporários, fora do repositório.

## Artefatos publicados

- `capivara_rpa-1.2.0a1-py3-none-any.whl` — 165 KB
  - SHA-256: `b83a4b222c4dee9532248f117afabb8809b2ef591dc743a242bb30ba45060100`
- `capivara_rpa-1.2.0a1.tar.gz` — 179 KB
  - SHA-256: `64007fc26940d310b0210b48cff25ee5c5c7759c7b3b7930987b6edb135a906c`

## 1. pip install — base

Comando:

```bash
python3.11 -m venv /tmp/capi-base
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  'capivara-rpa==1.2.0a1'
```

Resultados:

- `pip show capivara-rpa` → `Version: 1.2.0a1`
- `capivara --version` → `capivara 1.2.0a1`
- `python -m capivara_rpa --version` → `capivara 1.2.0a1`
- `texto.slug("Relatório de Clientes 2026")` → `relatorio-de-clientes-2026`
- `validacao.validar_cpf("529.982.247-25")` → `True`
- `selenium` carregado no import? `False`
- `pandas` carregado no import? `False`
- `Navegador` indisponível sem o extra `web` → `ModuleNotFoundError` (esperado)
- `pip check` → `No broken requirements found.`
- `data/` criado no diretório de teste? `NAO`

## 2. pip install — extra `[all]`

Comando:

```bash
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  'capivara-rpa[all]==1.2.0a1'
```

Resultados:

- `capivara --version` → `capivara 1.2.0a1`
- `from capivara_rpa import texto, validacao, ClienteAPI, Navegador` → OK
- `selenium` carregado no import? `False`
- `pandas` carregado no import? `False`
- `pip check` → `No broken requirements found.`
- `data/` criado no diretório de teste? `NAO`

Dependências principais instaladas:

```text
capivara-rpa==1.2.0a1
cryptography==50.0.2
loguru==0.8.0
pandas==3.1.1
python-dotenv==1.2.4
pyzipper==0.4.0
requests==2.34.2
rich==15.0.0
selenium==4.52.0.202610260015
```

## 3. pipx — CLI isolada

`pipx` foi instalado em um venv temporário. `PIPX_HOME` e `PIPX_BIN_DIR`
apontaram para diretórios temporários.

Comando:

```bash
pipx install \
  --pip-args="--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/" \
  'capivara-rpa[all]==1.2.0a1'
```

Resultados:

- `pipx list` → `capivara-rpa 1.2.0a1`, app `capivara`
- `capivara --version` → `capivara 1.2.0a1`
- imports dentro do venv do pipx: `texto`, `validacao`, `Navegador` OK
- `selenium`/`pandas` carregados no import? `False`/`False`
- `pip check` no venv do pipx → `No broken requirements found.`
- `pipx uninstall capivara-rpa` → OK
- `pipx list` depois → `nothing has been installed with pipx`

## 4. Homebrew — fórmula local

Foi criado um tap **local** (`capivara-rpa/tap`) e uma fórmula de teste. A
fórmula não foi publicada.

Fórmula usada:

```ruby
class Capivara < Formula
  include Language::Python::Virtualenv

  desc "RPA em Python 100% em portugues"
  homepage "https://github.com/capivara-rpa/capivara"
  url "https://test-files.pythonhosted.org/packages/6c/15/b2619d9c3c655ead13336044ea14bb010b5a8ad96e5b706d4f09186a335f/capivara_rpa-1.2.0a1.tar.gz"
  sha256 "64007fc26940d310b0210b48cff25ee5c5c7759c7b3b7930987b6edb135a906c"
  license "MIT"

  depends_on "python@3.11"

  def install
    python = formula_opt_bin("python@3.11")/"python3.11"
    virtualenv_create(libexec, python)
    system libexec/"bin/pip", "install", "--no-cache-dir", buildpath
    bin.install_symlink libexec/"bin/capivara"
  end

  test do
    assert_match "capivara 1.2.0a1", shell_output("#{bin}/capivara --version")
  end
end
```

Resultados:

- `brew style capivara-rpa/tap/capivara` → `1 file inspected, no offenses detected`
- `brew install --build-from-source capivara-rpa/tap/capivara` → **bloqueado pelo ambiente**
  - Erro: `Your Command Line Tools (CLT) does not support macOS 27.`
  - O Homebrew pediu atualização do CLT para Xcode 27.0.
  - `capivara` **não** foi instalado.
  - As versões das dependências existentes não mudaram após a falha
    (`python@3.11 3.11.15`, `ca-certificates 2025-12-02`, etc.).
- `brew audit --strict --online` → também bloqueado pelo mesmo erro de CLT.
- Tap local removido (`brew untap capivara-rpa/tap`) e developer mode desligado.

Conclusão do Homebrew: a fórmula é sintaticamente válida (`brew style` OK), mas
a instalação real não pôde ser validada nesta máquina por incompatibilidade
entre Homebrew, macOS 27 e o Command Line Tools instalado. Precisa rodar em CI
macOS com CLT compatível ou após atualizar o CLT.

## 5. Limpeza

- Venvs temporários (`venv-base`, `venv-all`, `venv-pipx`) removidos.
- `PIPX_HOME`/`PIPX_BIN_DIR` temporários removidos.
- Tap local do Homebrew removido.
- Token do TestPyPI não foi gravado neste arquivo nem mantido em disco.
- Este arquivo é a única evidência mantida.

## Resumo

| Canal | Status |
|---|---|
| `pip install` base (TestPyPI) | Validado |
| `pip install [all]` (TestPyPI) | Validado |
| `pipx install [all]` (TestPyPI) | Validado |
| `brew install` via tap local | Bloqueado por CLT/macOS 27; fórmula passou no `brew style` |
| `brew install capivara` (Homebrew core) | Ainda não existe |
| PyPI real | Ainda não publicado |

## 6. PyPI real — 1.2.0 (produção)

O alpha `1.2.0a1` foi promovido para a release estável `1.2.0` para que
`pip install capivara-rpa` funcione sem `--pre`.

- Publicação: <https://pypi.org/project/capivara-rpa/1.2.0/>
- `pip install capivara-rpa` em venv limpa → `capivara 1.2.0`
- `pip install "capivara-rpa[all]"` em venv limpa → `capivara 1.2.0`
- `texto.slug` e `validacao.validar_cpf` OK
- `Navegador` disponível no extra `[all]`
- `pip check` → `No broken requirements found.`
- Nenhum `data/` criado no diretório de teste
- Venvs temporários removidos

Artefatos estáveis:

- `capivara_rpa-1.2.0-py3-none-any.whl`
  - SHA-256: `960edca36a022ba533de2cda1742ddd54f07a6810c9daeb6dc7bc78cfe7a4437`
- `capivara_rpa-1.2.0.tar.gz`
  - SHA-256: `adfee9034293eef28c46ec3a952b3ef55fe6427e37b4d87cf500351c2424059e`

## 7. Release GitHub v1.2.0

Assets anexados (nomes da época, antes do rebrand para Lagoa):

- `control_room_instalador.exe`
- `control_room.exe`
- `robo_agente.exe`
- `RPA-Brasil-macos.zip`
- `tracktab.zip`

O workflow da tag falhou só no upload por falta de `permissions: contents: write`;
corrigido no commit `3c34ffe` (official `8fc79f9`, PR #5). Os assets foram
anexados manualmente via `gh release upload`.
