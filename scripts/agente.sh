#!/usr/bin/env bash
# Roda o agente (runner) da Lagoa a partir do código-fonte - Linux/macOS
#   scripts/agente.sh                              -> usa o hostname como máquina
#   scripts/agente.sh --maquina meu-mac --tags mac
#   scripts/agente.sh --lagoa http://10.0.0.5:8765
#   scripts/agente.sh --fila pedidos_teste
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado. Rode primeiro:  scripts/install.sh"
    exit 1
fi

source .venv/bin/activate
exec python -m core.control_room.agente "$@"
