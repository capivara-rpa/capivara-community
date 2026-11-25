# Instaladores (Lagoa + Agente + TrackTab)

Os binários são gerados com **PyInstaller** e empacotados como instaladores de
desktop — assim dá para subir a Lagoa e um agente **sem Python** na
máquina de destino. Os scripts abaixo montam o pacote completo.

> Requisitos (só na máquina que builda): `python -m venv .venv` + as deps do
> projeto + `pip install pyinstaller`.

## Build rápido

| Alvo | Comando | Gera |
|---|---|---|
| macOS (pasta/zip) | `bash packaging/build_mac.sh` | `dist/RPA-Brasil/` + `dist/RPA-Brasil-macos.zip` |
| macOS (.dmg) | `bash packaging/build_dmg.sh` | `dist/RPA-Brasil-macos.dmg` |
| TrackTab | `bash packaging/build_tracktab.sh` | `dist/tracktab.zip` (Chrome Web Store) |
| Windows | (ver abaixo) `iscc packaging/inno_setup.iss` | `dist/instalador/lagoa_instalador.exe` |

### macOS — instalador .dmg (app de duplo-clique)

```bash
bash packaging/build_dmg.sh            # usa dist/RPA-Brasil (builda se faltar)
bash packaging/build_dmg.sh --rebuild  # refaz os binários (PyInstaller) antes
```

Gera `dist/RPA-Brasil-macos.dmg` com o **`Instalar RPA Brasil.app`** (ícone
próprio, assinado ad-hoc) — o app embrulha o `instalar_mac.sh` e mostra o
progresso em janelas nativas, **sem abrir Terminal**. No Mac de destino: abra o
`.dmg`, dê 2 cliques no app (pode arrastar para Aplicativos) e ele instala em
`~/RPA Brasil`, cria os LaunchAgents e abre o painel. Precisa de Python? **Não.**

Para testar **sem mexer** numa instalação existente, rode o instalador de dentro
do app com um prefixo (labels e pasta próprios):

```bash
"/Volumes/RPA Brasil/Instalar RPA Brasil.app/Contents/Resources/payload/instalar_mac.sh" \
    --prefix teste --porta 8899 --maquina meu-mac --tags mac
# remover depois:  .../instalar_mac.sh --prefix teste --remover
```

### macOS — tudo empacotado

```bash
bash packaging/build_mac.sh
```

Monta `dist/RPA-Brasil/` com os binários, a extensão `tracktab/` e o
`instalar_mac.sh`. No Mac de destino, descompacte e rode:

```bash
./instalar_mac.sh                       # instala em ~/RPA Brasil e sobe tudo
./instalar_mac.sh --token segredo --tags mac,sp
./instalar_mac.sh --remover
```

O instalador copia os binários (sem Python), cria o `.env`/`data/`, instala a
Lagoa **e** o agente como serviços (`LaunchAgents`, sobem no login e
reconectam) e remove a quarentena do Gatekeeper.

### Windows — Inno Setup

1. Build os binários (num terminal Windows):
   `pyinstaller --noconfirm packaging/lagoa.spec` e
   `pyinstaller --noconfirm packaging/agente.spec`.
2. Instale o [Inno Setup 6+](https://jrsoftware.org/isinfo.php).
3. `iscc packaging/inno_setup.iss` → `dist/instalador/lagoa_instalador.exe`.

O instalador traz a Lagoa, o Agente (com opção de **iniciar com o
Windows** via atalho na inicialização), a extensão TrackTab e os scripts
`iniciar_lagoa.cmd` / `iniciar_agente.cmd` (definem `RPA_PASTA_DADOS`
ao lado do app).

### TrackTab (extensão Chrome)

```bash
bash packaging/build_tracktab.sh        # dist/tracktab.zip
```

O zip já sai com o `manifest.json` na raiz. Passo a passo para publicar na
**Chrome Web Store** (instalação de 1 clique): [../tracktab/PUBLICAR.md](../tracktab/PUBLICAR.md).

## Variáveis importantes ao rodar um binário

| Variável | Para que serve |
|---|---|
| `RPA_PASTA_DADOS` | Pasta de dados persistentes dos binários (bancos, logs, vault). **Defina sempre.** Os `.cmd`/instaladores já fazem isso. |
| `PORTA_LAGOA` | Porta da Lagoa (default 8765) |
| `HOST_LAGOA` | `0.0.0.0` para aceitar a rede (default 127.0.0.1) |
| `VAULT_CHAVE` | Frase usada para cifrar os assets no cofre |
| `LAGOA_TOKEN` | Token dos agentes (vazio = Lagoa aberta) |
| `LAGOA_URL` | URL que os robôs usam para enxergar a Lagoa |
| `TLS_CERT` / `TLS_CHAVE` | Certificado/chave PEM para HTTPS |

Rede, token, TLS e VPN (Tailscale): veja [../data/docs/REDE.md](../data/docs/REDE.md).

## CD/CI

O workflow `.github/workflows/build-instaladores.yml` compila no GitHub Actions
(Windows e macOS), monta o pacote macOS empacotado e o `tracktab.zip`, e anexa
tudo automaticamente a cada `git tag v*` (release).
