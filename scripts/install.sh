#!/usr/bin/env bash
# Instala o template (cria venv + dependências) - Linux/macOS
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "► Criando ambiente virtual (.venv)..."
python3 -m venv .venv

echo "► Ativando ambiente e atualizando pip..."
source .venv/bin/activate
pip install --upgrade pip

echo "► Instalando dependências..."
pip install -r requirements.txt

echo ""
echo "✅ Instalação concluída!"
echo "   Ative o ambiente com:  source .venv/bin/activate"
echo "   Rode o robô com:       python app/main.py"