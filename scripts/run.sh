#!/usr/bin/env bash
# Roda o robô usando o ambiente virtual - Linux/macOS
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado. Rode primeiro:  scripts/install.sh"
    exit 1
fi

source .venv/bin/activate
python app/main.py "$@"