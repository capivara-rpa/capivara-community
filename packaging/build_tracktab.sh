#!/usr/bin/env bash
# Empacota a extensão TrackTab (tracktab/) num .zip pronto para a Chrome Web Store.
#
#   bash packaging/build_tracktab.sh                 # gera dist/tracktab.zip
#   bash packaging/build_tracktab.sh /tmp/tracktab.zip
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAIDA="${1:-$ROOT/dist/tracktab.zip}"

# O zip roda de dentro de tracktab/ (ver cd abaixo), então o caminho de saída
# precisa ser absoluto — senão "dist/x.zip" viraria "tracktab/dist/x.zip".
case "$SAIDA" in
    /*) ;;
    *) SAIDA="$PWD/$SAIDA" ;;
esac

if ! command -v zip >/dev/null 2>&1; then
    echo "❌ 'zip' não encontrado. Instale-o e tente de novo."
    exit 1
fi

mkdir -p "$(dirname "$SAIDA")"
rm -f "$SAIDA"

# O manifest precisa estar na raiz do zip (não dentro de uma pasta).
( cd "$ROOT/tracktab" && zip -r -X "$SAIDA" . \
    -x '*.DS_Store' -x '__MACOSX/*' -x 'PUBLICAR.md' -x 'README.md' >/dev/null )

echo "✅ Extensão empacotada em: $SAIDA"
echo "   Publique em: https://chrome.google.com/webstore/devconsole"
echo "   Passo a passo: tracktab/PUBLICAR.md"
