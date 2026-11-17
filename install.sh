#!/bin/bash
set -e

echo "=================================================================="
echo "⚡ DashStream & TeslaMate Suite (v37.0) — Universal Installer"
echo "=================================================================="
echo ""
echo "Welches Setup möchtest du durchführen?"
echo "  [1] 🚀 KOMPLETT-NEUINSTALLATION (Docker, TeslaMate, Jellyfin, Audiobookshelf, Bridge & Bot)"
echo "  [2] 🔌 NUR ANBINDUNG (Ich habe TeslaMate / Jellyfin bereits und will nur DashStream + Bot)"
echo ""
read -p "👉 Deine Wahl (1 oder 2) [Standard: 2]: " SETUP_MODE
SETUP_MODE=${SETUP_MODE:-2}

if [ "$SETUP_MODE" = "1" ]; then
    echo ""
    echo "🛠 [Modus 1] Prüfe Docker & System-Abhängigkeiten..."
    if ! command -v docker >/dev/null 2>&1; then
        echo "📦 Installiere Docker & Docker Compose..."
        curl -fsSL https://get.docker.com | sudo sh
        sudo usermod -aG docker "$USER" || true
    fi

    read -p "👉 Zielordner für deine neue Server-Installation [Standard: $HOME/teslamate-stack]: " TM_DIR
    TM_DIR=${TM_DIR:-$HOME/teslamate-stack}
    mkdir -p "$TM_DIR/tesla-ui" "$TM_DIR/media/movies" "$TM_DIR/media/tv" "$TM_DIR/media/audiobooks" "$TM_DIR/import"

    # Sichere Zufalls-Keys für TeslaMate generieren, falls noch keine .env existiert
    if [ ! -f "$TM_DIR/.env" ]; then
        ENC_KEY=$(openssl rand -hex 32)
        DB_PASS=$(openssl rand -hex 16)
        echo "TM_ENCRYPTION_KEY=${ENC_KEY}" > "$TM_DIR/.env"
        echo "TM_DB_PASS=${DB_PASS}" >> "$TM_DIR/.env"
        chmod 600 "$TM_DIR/.env"
        echo "🔐 Sichere Datenbank-Passwörter & Verschlüsselungs-Keys in $TM_DIR/.env generiert!"
    fi

    cp docker-compose.full.yml "$TM_DIR/docker-compose.yml"
    cp bridge/bridge.py "$TM_DIR/bridge.py"
    cp dashstream/dashstream.html "$TM_DIR/tesla-ui/dashstream.html"

    echo "🚀 Starte alle Container (TeslaMate, PostgreSQL, Grafana, MQTT, Bridge, Jellyfin & Audiobookshelf)..."
    (cd "$TM_DIR" && sudo docker compose up -d)
    echo "⏳ Warte 8 Sekunden, bis Jellyfin initialisiert ist..."
    sleep 8
    JF_CONTAINER="jellyfin"
else
    echo ""
    read -p "👉 1. Pfad zu deinem bestehenden TeslaMate-Ordner [Standard: $HOME/teslamate]: " TM_DIR
    TM_DIR=${TM_DIR:-$HOME/teslamate}
    read -p "👉 2. Name deines bestehenden Jellyfin-Containers [Standard: jellyfin]: " JF_CONTAINER
    JF_CONTAINER=${JF_CONTAINER:-jellyfin}
    mkdir -p "$TM_DIR/tesla-ui"
    cp bridge/bridge.py "$TM_DIR/bridge.py"
    cp dashstream/dashstream.html "$TM_DIR/tesla-ui/dashstream.html"
fi

echo ""
echo "🎬 Injiziere DashStream Oberfläche in Jellyfin ($JF_CONTAINER)..."
for dir in "/usr/share/jellyfin/web" "/jellyfin/jellyfin-web"; do
    sudo docker cp -L "$TM_DIR/tesla-ui/dashstream.html" "$JF_CONTAINER:$dir/tesla.html" 2>/dev/null || true
    sudo docker cp -L "$TM_DIR/tesla-ui/dashstream.html" "$JF_CONTAINER:$dir/kitt.html" 2>/dev/null || true
done
echo "✅ DashStream ist live unter http://DEINE-SERVER-IP:8096/web/tesla.html"

echo ""
read -p "🤖 Möchtest du auch den AI Telegram-Bot & GPS/Drain-Wächter einrichten? (j/n): " INST_BOT
if [[ "$INST_BOT" =~ ^[JjYy]$ ]]; then
    BOT_DIR="$HOME/telegram-bot"
    mkdir -p "$BOT_DIR"
    cp telegram-bot/bot.py "$BOT_DIR/bot.py"
    cp telegram-bot/requirements.txt "$BOT_DIR/requirements.txt"

    if [ ! -f "$BOT_DIR/config.py" ]; then
        read -p "   🔑 Dein Telegram Bot Token (von @BotFather): " TG_TOKEN
        read -p "   🆔 Deine Telegram Chat-ID (von @userinfobot): " TG_CHATID
        read -p "   🌐 Deine Jellyfin/Tailscale URL: " TG_JFURL
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
    echo "✅ Telegram-Bot läuft im Hintergrund!"
fi

cp scripts/backup_all.sh "$HOME/backup_all.sh"
chmod +x "$HOME/backup_all.sh"
mkdir -p "$HOME/backups"

echo ""
echo "=================================================================="
echo "🎉 INSTALLATION ABGESCHLOSSEN!"
echo "👉 TeslaMate Login:     http://DEINE-SERVER-IP:4000"
echo "👉 Grafana Dashboards:  http://DEINE-SERVER-IP:3000"
echo "👉 DashStream (Tesla):  http://DEINE-SERVER-IP:8096/web/tesla.html"
echo "👉 Audiobookshelf:      http://DEINE-SERVER-IP:13378"
echo "=================================================================="
