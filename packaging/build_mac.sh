#!/usr/bin/env bash
# Gera o pacote macOS "tudo empacotado" (sem exigir Python):
#   dist/RPA-Brasil/                 ← pasta pronta (binários + Capivara Captura + instalador)
#   dist/RPA-Brasil-macos.zip        ← zip para distribuir/release
#
# Uso:
#   bash packaging/build_mac.sh
#
# Pré-requisitos: venv com as deps do projeto + pyinstaller.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="python"
if [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
fi

echo "🔨 Compilando a Lagoa..."
"$PY" -m PyInstaller --noconfirm packaging/lagoa.spec

echo "🔨 Compilando o Agente..."
"$PY" -m PyInstaller --noconfirm packaging/agente.spec

BUNDLE="$ROOT/dist/RPA-Brasil"
echo "📦 Montando $BUNDLE ..."
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE"

cp -f dist/lagoa dist/robo_agente "$BUNDLE/"
rm -rf "$BUNDLE/tracktab"
cp -Rf tracktab "$BUNDLE/tracktab"
cp -f packaging/instalar_mac.sh "$BUNDLE/"
cp -f .env.example "$BUNDLE/.env.example"
chmod +x "$BUNDLE/lagoa" "$BUNDLE/robo_agente" "$BUNDLE/instalar_mac.sh"

echo "🗜️  Empacotando zip..."
( cd dist && rm -f RPA-Brasil-macos.zip && zip -r -X RPA-Brasil-macos.zip RPA-Brasil >/dev/null )

echo ""
echo "✅ Pronto:"
echo "   Pasta:  $BUNDLE"
echo "   Zip:    $ROOT/dist/RPA-Brasil-macos.zip"
echo "   Instalar (no Mac de destino): descompacte e rode ./instalar_mac.sh"
