#!/usr/bin/env bash
# Instala o agente da Lagoa como serviço (LaunchAgent) no macOS.
# O agente sobe junto com a sua sessão, sem precisar de terminal aberto, e
# fica reconectando sozinho na Lagoa.
#
#   scripts/instalar_agente_mac.sh
#   scripts/instalar_agente_mac.sh --maquina mac-do-arthur --tags mac,sp
#   scripts/instalar_agente_mac.sh --lagoa http://10.0.0.5:8765
#   scripts/instalar_agente_mac.sh --fila pedidos_teste
#   scripts/instalar_agente_mac.sh --remover
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.rpabrasil.agente"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON="$ROOT/.venv/bin/python"
LOGS="$ROOT/data/logs"

MAQUINA="$(hostname -s 2>/dev/null || hostname)"
LAGOA="http://127.0.0.1:8765"
TAGS="mac"
FILA=""
TOKEN="${LAGOA_TOKEN:-}"
REMOVER=0

while [ $# -gt 0 ]; do
    case "$1" in
        --remover) REMOVER=1; shift ;;
        --maquina) MAQUINA="$2"; shift 2 ;;
        --lagoa) LAGOA="$2"; shift 2 ;;
        --tags) TAGS="$2"; shift 2 ;;
        --fila) FILA="$2"; shift 2 ;;
        --token) TOKEN="$2"; shift 2 ;;
        *) echo "Opção desconhecida: $1"; exit 1 ;;
    esac
done

UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"

remover() {
    launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✅ Serviço '${LABEL}' removido."
}

if [ "$REMOVER" = "1" ]; then
    remover
    exit 0
fi

if [ ! -x "$PYTHON" ]; then
    echo "❌ Python do venv não encontrado em $PYTHON. Rode primeiro:  scripts/install.sh"
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOGS"

ARGS="        <string>${PYTHON}</string>
        <string>-m</string>
        <string>core.control_room.agente</string>
        <string>--maquina</string>
        <string>${MAQUINA}</string>
        <string>--lagoa</string>
        <string>${LAGOA}</string>"
if [ -n "$TAGS" ]; then
    ARGS="${ARGS}
        <string>--tags</string>
        <string>${TAGS}</string>"
fi
if [ -n "$FILA" ]; then
    ARGS="${ARGS}
        <string>--fila</string>
        <string>${FILA}</string>"
fi
if [ -n "$TOKEN" ]; then
    ARGS="${ARGS}
        <string>--token</string>
        <string>${TOKEN}</string>"
fi

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
${ARGS}
    </array>
    <key>WorkingDirectory</key>
    <string>${ROOT}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>LAGOA_URL</key>
        <string>${LAGOA}</string>
        <key>LAGOA_TOKEN</key>
        <string>${TOKEN}</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>${LOGS}/agente.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOGS}/agente.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
# o bootout derruba o serviço antigo em background: se o bootstrap vier logo
# depois, o launchctl ainda está com o label ocupado e falha com
# "Input/output error" (5). Por isso a retentativa com espera.
SUBIU=0
for tentativa in 1 2 3 4 5; do
    if launchctl bootstrap "$DOMAIN" "$PLIST" 2>/dev/null; then
        SUBIU=1
        break
    fi
    sleep 1
    if launchctl load -w "$PLIST" 2>/dev/null; then
        SUBIU=1
        break
    fi
done
launchctl kickstart -k "${DOMAIN}/${LABEL}" 2>/dev/null || true

# confirma que o serviço realmente está registrado (o bootstrap pode falhar
# em silêncio e o plist ficar "instalado" sem rodar — a máquina fica offline)
if [ "$SUBIU" != "1" ] || ! launchctl print "${DOMAIN}/${LABEL}" >/dev/null 2>&1; then
    echo "❌ O serviço NÃO subiu. Rode de novo em ~2s (o launchctl ainda"
    echo "   estava liberando o serviço antigo) ou verifique com:"
    echo "   launchctl print ${DOMAIN}/${LABEL}"
    exit 1
fi

echo "✅ Agente instalado como serviço (${LABEL})."
echo "   Máquina:      ${MAQUINA}"
echo "   Lagoa: ${LAGOA}${FILA:+  (fila: ${FILA})}"
if [ -n "$TOKEN" ]; then
    echo "   Token:        definido"
else
    echo "   Token:        não definido (Lagoa aberta)"
fi
echo "   Logs:         ${LOGS}/agente.out.log e agente.err.log"
echo "   Status:       launchctl print ${DOMAIN}/${LABEL}"
echo "   Remover:      scripts/instalar_agente_mac.sh --remover"
echo ""
echo "ℹ️  A 1ª subida pode demorar ~30s (tradução do Rosetta em Macs Apple Silicon)."
echo "    Confira a máquina '${MAQUINA}' ficar ONLINE no painel da Lagoa."
