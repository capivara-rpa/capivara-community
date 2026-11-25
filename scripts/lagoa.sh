#!/usr/bin/env bash
# Sobe a Lagoa (orquestrador + painel de trace) - Linux/macOS
#   scripts/lagoa.sh              -> sobe a Lagoa
#   scripts/lagoa.sh --exemplos   -> popula máquinas/processos/jobs e sobe
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado. Rode primeiro:  scripts/install.sh"
    exit 1
fi

source .venv/bin/activate

if [ "${1:-}" = "--exemplos" ]; then
    python -m core.control_room.dados_exemplo
    shift
fi

python -m core.control_room.servidor "$@"
