# -*- mode: python ; coding: utf-8 -*-
"""Gera o binário do Agente de uma máquina (worker da Lagoa).

Build:
    pyinstaller --noconfirm packaging/agente.spec

O executável conecta na Lagoa (--lagoa), registra a máquina,
busca jobs/filas e executa os fluxos. Como o agente carrega Robo (Selenium)
e o motor de dados (pandas), o binário fica maior que o da Lagoa.

Obs.: aplica-se a alguém que rode os robôs do próprio projeto/instalados
na pasta de dados (RPA_PASTA_DADOS/robos); para um orquestrador robusto,
prefira rodar o agente a partir do código-fonte.
"""

import os
from pathlib import Path

PROJETO = str(Path(SPECPATH).parent) if "SPECPATH" in globals() else os.getcwd()

DATA_ESTATICOS = [
    (os.path.join(PROJETO, "core", "control_room", "estatico"),
     os.path.join("core", "control_room", "estatico")),
    (os.path.join(PROJETO, "core", "monitor", "estatico"),
     os.path.join("core", "monitor", "estatico")),
]

arquivo = os.path.join(PROJETO, "core", "control_room", "agente.py")

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
        "selenium",
        "pandas",
        "openpyxl",
        "core.rpa.browser",
        "core.rpa.dados",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["IPython", "matplotlib"],
    noarchive=False,
)

pyzk = PYZ(analyze.pure)

exe = EXE(
    pyzk,
    analyze.scripts,
    analyze.binaries,
    analyze.datas,
    [],
    name="robo_agente",
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