#!/usr/bin/env bash
# Remove caches do Python (__pycache__ e .pyc) - Linux/macOS
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "► Removendo caches do Python..."
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "✅ Caches removidos."