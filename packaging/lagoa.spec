# -*- mode: python ; coding: utf-8 -*-
"""Gera o binário/instalável da Lagoa (servidor + monitor + API).

Build:
    pyinstaller --noconfirm packaging/lagoa.spec

Gera um executável único ("onefile") que serve a Lagoa na raiz, o
painel de trace em /monitor e a API /api/*. Crie um .env ao lado do binário
(ou exporte as variáveis) para portas/chaves personalizadas.
"""

import os
from pathlib import Path

PROJETO = str(Path(SPECPATH).parent) if "SPECPATH" in globals() else os.getcwd()

# Estáticos servidos pelos dois apps (Lagoa e Monitor)
# Obs.: control_room/servidor.py roda como entry point → seu __file__ fica na
# raiz do _MEIPASS, então o estático dele é copiado para a raiz "estatico/".
DATA_ESTATICOS = [
    (os.path.join(PROJETO, "core", "control_room", "estatico"), "estatico"),
    (os.path.join(PROJETO, "core", "monitor", "estatico"),
     os.path.join("core", "monitor", "estatico")),
]

arquivo = os.path.join(PROJETO, "core", "control_room", "servidor.py")

analyze = Analysis(
    [arquivo],
    pathex=[PROJETO],
    binaries=[],
    datas=DATA_ESTATICOS,
    hiddenimports=[
        "loguru",
        "requests",
        "pyzipper",
        "cryptography",
        # backend das rotas de pacote/vault importado sob demanda no servidor
        "core.control_room.pacote",
        "core.control_room.cofre",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pandas", "selenium", "numpy", "IPython"],
    noarchive=False,
)

pyzk = PYZ(analyze.pure)

exe = EXE(
    pyzk,
    analyze.scripts,
    analyze.binaries,
    analyze.datas,
    [],
    name="lagoa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)