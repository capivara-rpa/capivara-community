#!/usr/bin/env bash
# Gera o instalador .dmg do macOS com um app de duplo-clique:
#
#   "Instalar RPA Brasil.app"  ->  instala a Lagoa + o Agente (LaunchAgents)
#
# Uso:
#   bash packaging/build_dmg.sh            # usa dist/RPA-Brasil (builda se faltar)
#   bash packaging/build_dmg.sh --rebuild  # refaz os binários (PyInstaller) antes
#
# Resultado: dist/RPA-Brasil-macos.dmg
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="$RAIZ/dist/RPA-Brasil"
APP="$RAIZ/dist/Instalar RPA Brasil.app"
DMG="$RAIZ/dist/RPA-Brasil-macos.dmg"
STAGE="$RAIZ/dist/.dmg-stage"
ICONE_DIR="$RAIZ/dist/.icone"
VOLUME="RPA Brasil"

REBUILD=0
for arg in "$@"; do
    case "$arg" in
        --rebuild) REBUILD=1 ;;
        *) echo "Opção desconhecida: $arg"; exit 1 ;;
    esac
done

if [ "$REBUILD" = "1" ] || [ ! -x "$PAYLOAD/lagoa" ] || [ ! -x "$PAYLOAD/robo_agente" ]; then
    echo "🔨 Buildando o pacote macOS (PyInstaller)..."
    bash "$RAIZ/packaging/build_mac.sh"
fi

# ------------------------------- ícone (.icns) -------------------------------
ICNS=""
if [ -f "$RAIZ/tracktab/icons/icon128.png" ]; then
    echo "🎨 Montando o ícone..."
    rm -rf "$RAIZ/dist/.icone"
    mkdir -p "$RAIZ/dist/.icone/AppIcon.iconset"
    ICON="$RAIZ/dist/.icone/AppIcon.iconset"
    for par in 16:icon_16x16.png 32:icon_16x16@2x.png 32:icon_32x32.png \
               64:icon_32x32@2x.png 128:icon_128x128.png 256:icon_128x128@2x.png \
               256:icon_256x256.png 512:icon_256x256@2x.png 512:icon_512x512.png \
               1024:icon_512x512@2x.png; do
        px="${par%%:*}"; nome="${par##*:}"
        sips -z "$px" "$px" "$RAIZ/tracktab/icons/icon128.png" --out "$ICON/$nome" >/dev/null 2>&1 || true
    done
    if iconutil -c icns "$ICON" -o "$RAIZ/dist/.icone/AppIcon.icns" >/dev/null 2>&1; then
        ICONE="$RAIZ/dist/.icone/AppIcon.icns"
    fi
fi

# ------------------------------ bundle do app -------------------------------
echo "🧩 Montando \"Instalar RPA Brasil.app\" ..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
ditto "$PAYLOAD" "$APP/Contents/Resources/payload"
[ -n "$ICONE" ] && cp -f "$ICONE" "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Instalar RPA Brasil</string>
    <key>CFBundleDisplayName</key><string>Instalar RPA Brasil</string>
    <key>CFBundleIdentifier</key><string>com.rpabrasil.instalador</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>launcher</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>LSUIElement</key><true/>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/launcher" <<'LAUNCHER'
#!/usr/bin/env bash
# Launcher do "Instalar RPA Brasil.app".
# Copia o pacote para um temporário (limpo de quarentena), roda o instalar_mac.sh
# e mostra o resultado em janelas nativas — sem abrir o Terminal.
set -u

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PAYLOAD="$APP_DIR/Resources/payload"
LOG="$HOME/Library/Logs/RPA Brasil/instalar.log"
mkdir -p "$(dirname "$LOG")"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ditto "$PAYLOAD" "$TMP/payload"
xattr -dr com.apple.quarantine "$TMP" 2>/dev/null || true

osascript -e 'display notification "Instalando a Lagoa e o Agente…" with title "RPA Brasil"' 2>/dev/null || true

# ignora o argumento -psn_... que o Finder às vezes passa
args=()
for a in "$@"; do
    case "$a" in -psn_*) ;; *) args+=("$a") ;; esac
done

if "$TMP/payload/instalar_mac.sh" ${args[@]+"${args[@]}"} >"$LOG" 2>&1; then
    URL="$(sed -n 's/^.*Painel:[[:space:]]*//p' "$LOG" | tail -1)"
    [ -z "$URL" ] && URL="http://127.0.0.1:8765"
    for _ in $(seq 1 40); do
        curl -s -o /dev/null "$URL/api/orq/painel" && break
        sleep 1
    done
    osascript -e 'display dialog "RPA Brasil instalado com sucesso!\n\nA Lagoa vai abrir no navegador." buttons {"OK"} default button "OK" with title "RPA Brasil" with icon note' 2>/dev/null || true
    open "$URL" 2>/dev/null || true
else
    osascript -e "display dialog \"A instalação falhou.\n\nVeja o log em:\n$LOG\" buttons {\"OK\"} default button \"OK\" with title \"RPA Brasil\" with icon stop" 2>/dev/null || true
    exit 1
fi
LAUNCHER

chmod +x "$APP/Contents/MacOS/launcher"

# assinatura ad-hoc (sem conta Apple) — ajuda o Gatekeeper a não tratar como corrompido
codesign --force --sign - "$APP" >/dev/null 2>&1 || true

# --------------------------------- .dmg -------------------------------------
echo "💿 Gerando $DMG ..."
rm -rf "$STAGE"; mkdir -p "$STAGE"
ditto "$APP" "$STAGE/Instalar RPA Brasil.app"
ln -sf /Applications "$STAGE/Aplicativos"
cat > "$STAGE/LEIA-ME.txt" <<'TXT'
RPA Brasil — instalação (macOS)
===============================

1) Dê 2 cliques em "Instalar RPA Brasil.app" (pode arrastar para Aplicativos).

2) O instalador:
   - copia tudo para ~/RPA Brasil;
   - cria o .env e a pasta data/;
   - instala a Lagoa e o Agente como serviços (sobem no login);
   - abre o painel no navegador.

3) Painel:  http://127.0.0.1:8765
   Monitor: http://127.0.0.1:8765/monitor/

Remover serviços depois:
   RPA_DEST="$HOME/RPA Brasil" ./instalar_mac.sh --remover
   (ou apague ~/Library/LaunchAgents/com.rpabrasil.*.plist)

Se o macOS bloquear ("desenvolvedor não identificado"): botão direito no app
→ Abrir, ou em Ajustes do Sistema → Privacidade e Segurança → Abrir mesmo assim.
TXT

rm -f "$DMG"
hdiutil create -volname "$VOLUME" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE" "$RAIZ/dist/.icone"

echo ""
echo "✅ Pronto:"
echo "   DMG: $DMG"
echo "   Abrir: open \"$DMG\""
