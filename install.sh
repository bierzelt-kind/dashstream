#!/bin/bash
set -e

echo "=================================================================="
echo "⚡ DashStream & TeslaMate Suite (v37.0) — Interactive Installer"
echo "=================================================================="
echo ""

read -p "👉 1. Pfad zu deinem TeslaMate-Ordner [Standard: $HOME/teslamate]: " TM_DIR
TM_DIR=${TM_DIR:-$HOME/teslamate}

read -p "👉 2. Name deines Jellyfin Docker-Containers [Standard: jellyfin]: " JF_CONTAINER
JF_CONTAINER=${JF_CONTAINER:-jellyfin}

echo ""
echo "📦 [1/4] Installiere DashStream Web-Frontend in Jellyfin ($JF_CONTAINER)..."
mkdir -p "$TM_DIR/tesla-ui"
cp dashstream/dashstream.html "$TM_DIR/tesla-ui/dashstream.html"
for dir in "/usr/share/jellyfin/web" "/jellyfin/jellyfin-web"; do
    docker cp -L "$TM_DIR/tesla-ui/dashstream.html" "$JF_CONTAINER:$dir/tesla.html" 2>/dev/null || true
    docker cp -L "$TM_DIR/tesla-ui/dashstream.html" "$JF_CONTAINER:$dir/kitt.html" 2>/dev/null || true
done
echo "✅ DashStream UI erfolgreich in Jellyfin injiziert!"

echo ""
echo "📡 [2/4] Richte TeslaMate Telemetry Bridge ein..."
cp bridge/bridge.py "$TM_DIR/bridge.py"
echo "✅ bridge.py nach $TM_DIR/bridge.py kopiert."

echo ""
read -p "🤖 [3/4] Möchtest du den AI Telegram-Bot & GPS/Drain-Wächter installieren? (j/n): " INST_BOT
if [[ "$INST_BOT" =~ ^[JjYy]$ ]]; then
    BOT_DIR="$HOME/telegram-bot"
    mkdir -p "$BOT_DIR"
    cp telegram-bot/bot.py "$BOT_DIR/bot.py"
    cp telegram-bot/requirements.txt "$BOT_DIR/requirements.txt"

    if [ ! -f "$BOT_DIR/config.py" ]; then
        echo ""
        read -p "   🔑 Dein Telegram Bot Token (von @BotFather): " TG_TOKEN
        read -p "   🆔 Deine Telegram Chat-ID (von @userinfobot): " TG_CHATID
        read -p "   🌐 Deine Tailscale/Jellyfin URL: " TG_JFURL
        cat << CFG > "$BOT_DIR/config.py"
TOKEN = "${TG_TOKEN}"
MY_CHAT_ID = ${TG_CHATID:-0}
JELLYFIN_URL = "${TG_JFURL}"
AUDIOBOOK_URL = "${TG_JFURL}:8443"
CFG
        chmod 600 "$BOT_DIR/config.py"
    fi

    sudo apt-get update -qq && sudo apt-get install -y python3-venv ffmpeg -qq
    python3 -m venv "$BOT_DIR/venv"
    "$BOT_DIR/venv/bin/pip" install -r "$BOT_DIR/requirements.txt" --quiet

    sudo bash -c "cat << SVC > /etc/systemd/system/telegram-bot.service
[Unit]
Description=DashStream & TeslaMate Telegram Sentinel Bot
After=network.target docker.service

[Service]
User=$USER
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python3 $BOT_DIR/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC"
    sudo systemctl daemon-reload
    sudo systemctl enable --now telegram-bot.service
    echo "✅ Telegram-Bot als Systemdienst gestartet!"
fi

echo ""
echo "💾 [4/4] Richte automatisches Backup-Skript ein..."
cp scripts/backup_all.sh "$HOME/backup_all.sh"
chmod +x "$HOME/backup_all.sh"
mkdir -p "$HOME/backups"
echo "✅ Fertig! Dein System läuft jetzt auf v37.0!"
