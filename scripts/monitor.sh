#!/usr/bin/env bash
# Sobe o painel de monitoramento dos robôs - Linux/macOS
#   scripts/monitor.sh              -> sobe o painel
#   scripts/monitor.sh --exemplos   -> popula o banco com dados de exemplo e sobe
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado. Rode primeiro:  scripts/install.sh"
    exit 1
fi

source .venv/bin/activate

if [ "${1:-}" = "--exemplos" ]; then
    python -m core.monitor.dados_exemplo
    shift
fi

python -m core.monitor.servidor "$@"
