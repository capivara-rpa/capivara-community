#!/usr/bin/env bash
# Instalador macOS "tudo empacotado" — NÃO exige Python na máquina.
#
# Roda de dentro do pacote gerado por `packaging/build_mac.sh` (pasta que contém
# os binários lagoa / robo_agente, a extensão tracktab/ (Capivara Captura) e o .env.example):
#
#   ./instalar_mac.sh                     # instala em ~/RPA Brasil e sobe tudo
#   ./instalar_mac.sh --token segredo
#   ./instalar_mac.sh --porta 9000 --maquina mac-arthur --tags mac,sp
#   ./instalar_mac.sh --sem-agente        # só a Lagoa
#   ./instalar_mac.sh --prefix teste      # instância paralela (não briga com a padrão)
#   ./instalar_mac.sh --remover
#
# Instala Lagoa + Agente como serviços (LaunchAgents), para subirem
# sozinhos no login e reconectarem. A Capivara Captura fica em <DEST>/tracktab
# (para carregar como "descompactada" enquanto não estiver na Chrome Web Store).
set -euo pipefail

ORIGEM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DEST="${RPA_DEST:-$HOME/RPA Brasil}"
DADOS="$DEST/data"
LOGS="$DADOS/logs"

LABEL_CR="com.rpabrasil.lagoa"
LABEL_AG="com.rpabrasil.agente"
LABEL_CR_ANTIGO="com.rpabrasil.controlroom"
PLIST_CR="$HOME/Library/LaunchAgents/${LABEL_CR}.plist"
PLIST_AG="$HOME/Library/LaunchAgents/${LABEL_AG}.plist"

PORTA="8765"
MAQUINA="$(hostname -s 2>/dev/null || hostname)"
TAGS="mac"
TOKEN="${LAGOA_TOKEN:-}"
INSTALAR_AGENTE=1
REMOVER=0
PREFIXO=""

while [ $# -gt 0 ]; do
    case "$1" in
        --remover) REMOVER=1; shift ;;
        --sem-agente) INSTALAR_AGENTE=0; shift ;;
        --porta) PORTA="$2"; shift 2 ;;
        --maquina) MAQUINA="$2"; shift 2 ;;
        --tags) TAGS="$2"; shift 2 ;;
        --token) TOKEN="$2"; shift 2 ;;
        --prefix) PREFIXO="$2"; shift 2 ;;
        *) echo "Opção desconhecida: $1"; exit 1 ;;
    esac
done

# --prefix permite instalar uma 2ª cópia lado a lado (labels/pasta próprios),
# útil para testar sem mexer na instalação padrão.
if [ -n "$PREFIXO" ]; then
    LABEL_CR="com.rpabrasil.${PREFIXO}.lagoa"
    LABEL_AG="com.rpabrasil.${PREFIXO}.agente"
    LABEL_CR_ANTIGO="com.rpabrasil.${PREFIXO}.controlroom"
    PLIST_CR="$HOME/Library/LaunchAgents/${LABEL_CR}.plist"
    PLIST_AG="$HOME/Library/LaunchAgents/${LABEL_AG}.plist"
    if [ -z "${RPA_DEST:-}" ]; then
        DEST="$HOME/RPA Brasil $PREFIXO"
        DADOS="$DEST/data"
        LOGS="$DADOS/logs"
    fi
fi

LAGOA="http://127.0.0.1:${PORTA}"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"

remover() {
    for label in "$LABEL_CR" "$LABEL_AG" "$LABEL_CR_ANTIGO"; do
        launchctl bootout "${DOMAIN}/${label}" 2>/dev/null || true
    done
    rm -f "$PLIST_CR" "$PLIST_AG" "$HOME/Library/LaunchAgents/${LABEL_CR_ANTIGO}.plist"
    echo "✅ Serviços da Lagoa e do Agente removidos."
    echo "   (Os arquivos em '${DEST}' foram mantidos; apague a pasta se quiser.)"
}

if [ "$REMOVER" = "1" ]; then
    remover
    exit 0
fi

# Migração do nome antigo (Control Room -> Lagoa): derruba o serviço antigo.
launchctl bootout "${DOMAIN}/${LABEL_CR_ANTIGO}" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/${LABEL_CR_ANTIGO}.plist"

for bin in lagoa robo_agente; do
    if [ ! -x "$ORIGEM/$bin" ]; then
        echo "❌ Binário '$bin' não encontrado em '$ORIGEM'."
        echo "   Rode este instalador de dentro do pacote gerado por build_mac.sh."
        exit 1
    fi
done

echo "📦 Instalando em: $DEST"
mkdir -p "$DEST" "$HOME/Library/LaunchAgents" "$DADOS" "$LOGS"
cp -f "$ORIGEM/lagoa" "$ORIGEM/robo_agente" "$DEST/"
rm -rf "$DEST/tracktab"
cp -Rf "$ORIGEM/tracktab" "$DEST/tracktab" 2>/dev/null || true
cp -f "$ORIGEM/.env.example" "$DEST/.env.example" 2>/dev/null || true
chmod +x "$DEST/lagoa" "$DEST/robo_agente"

# Sem isso o Gatekeeper pode bloquear binários baixados da internet.
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true

if [ ! -f "$DEST/.env" ]; then
    cat > "$DEST/.env" <<ENV
# Configuração da instalação local da Lagoa (Capivara)
RPA_PASTA_DADOS=$DADOS
PORTA_LAGOA=$PORTA
LAGOA_URL=$LAGOA
LAGOA_TOKEN=$TOKEN
VAULT_CHAVE=troque-esta-chave
ENV
    echo "ℹ️  .env criado em $DEST/.env"
fi

plist_comum_env() {
    cat <<ENV
        <key>RPA_PASTA_DADOS</key>
        <string>${DADOS}</string>
        <key>LAGOA_URL</key>
        <string>${LAGOA}</string>
        <key>LAGOA_TOKEN</key>
        <string>${TOKEN}</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
ENV
}

# ------------------------- Lagoa (serviço) -------------------------
cat > "$PLIST_CR" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL_CR}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${DEST}/lagoa</string>
        <string>--porta</string>
        <string>${PORTA}</string>
        <string>--sem-navegador</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${DEST}</string>
    <key>EnvironmentVariables</key>
    <dict>
$(plist_comum_env)
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>${LOGS}/lagoa.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOGS}/lagoa.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "${DOMAIN}/${LABEL_CR}" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_CR" || launchctl load -w "$PLIST_CR"
launchctl kickstart -k "${DOMAIN}/${LABEL_CR}" 2>/dev/null || true
echo "✅ Lagoa instalada como serviço (${LABEL_CR})."

# ----------------------------- Agente (serviço) -----------------------------
if [ "$INSTALAR_AGENTE" = "1" ]; then
    cat > "$PLIST_AG" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL_AG}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${DEST}/robo_agente</string>
        <string>--lagoa</string>
        <string>${LAGOA}</string>
        <string>--maquina</string>
        <string>${MAQUINA}</string>
        <string>--tags</string>
        <string>${TAGS}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${DEST}</string>
    <key>EnvironmentVariables</key>
    <dict>
$(plist_comum_env)
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

    launchctl bootout "${DOMAIN}/${LABEL_AG}" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST_AG" || launchctl load -w "$PLIST_AG"
    launchctl kickstart -k "${DOMAIN}/${LABEL_AG}" 2>/dev/null || true
    echo "✅ Agente instalado como serviço (${LABEL_AG}) — máquina '${MAQUINA}' (tags: ${TAGS})."
else
    echo "ℹ️  Agente não instalado (--sem-agente)."
fi

echo ""
echo "🎉 Pronto! A Lagoa sobe sozinha no login."
echo "   Painel:        ${LAGOA}"
echo "   Trace:         ${LAGOA}/monitor/"
echo "   Dados/logs:    ${DADOS}"
echo "   Extensão:      Capivara Captura — carregue '${DEST}/tracktab' em chrome://extensions (Modo dev)"
echo "   Status:        launchctl print ${DOMAIN}/${LABEL_CR}"
echo "   Remover:       $ORIGEM/instalar_mac.sh --remover"
echo ""
echo "ℹ️  A 1ª subida pode demorar ~30s em Macs Apple Silicon (tradução do Rosetta)."
