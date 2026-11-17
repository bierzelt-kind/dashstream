#!/bin/bash
set -e

echo "=================================================================="
echo "⚡ DashStream, TeslaMate & Usenet Suite (v37.0) — Installer"
echo "=================================================================="
echo ""
echo "Welches Setup möchtest du durchführen?"
echo "  [1] 🚀 KOMPLETT-SERVER NEU (TeslaMate + Jellyfin + ABS + Usenet/*arr-Stack + Bot)"
echo "  [2] 📦 NUR USENET & *ARR NACHRÜSTEN (SABnzbd, Prowlarr, Radarr, Sonarr, Jellyseerr)"
echo "  [3] 🔌 NUR DASHSTREAM & BOT ANBINDEN (Für bestehende TeslaMate/Jellyfin-Server)"
echo ""
read -p "👉 Deine Wahl (1, 2 oder 3) [Standard: 3]: " SETUP_MODE
SETUP_MODE=${SETUP_MODE:-3}

if ! command -v docker >/dev/null 2>&1; then
    echo "📦 Docker nicht gefunden — installiere Docker & Docker Compose..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
fi

if [ "$SETUP_MODE" = "1" ]; then
    read -p "👉 Zielordner für deinen Komplett-Server [Standard: $HOME/teslamate-stack]: " TM_DIR
    TM_DIR=${TM_DIR:-$HOME/teslamate-stack}
    mkdir -p "$TM_DIR/tesla-ui" "$TM_DIR/import"              "$TM_DIR/data/media/movies" "$TM_DIR/data/media/tv"              "$TM_DIR/data/media/audiobooks" "$TM_DIR/data/media/podcasts"              "$TM_DIR/data/usenet/incomplete" "$TM_DIR/data/usenet/complete/movies" "$TM_DIR/data/usenet/complete/tv"              "$TM_DIR/arr-configs/sabnzbd" "$TM_DIR/arr-configs/prowlarr"              "$TM_DIR/arr-configs/radarr" "$TM_DIR/arr-configs/sonarr" "$TM_DIR/arr-configs/jellyseerr"

    if [ ! -f "$TM_DIR/.env" ]; then
        ENC_KEY=$(openssl rand -hex 32)
        DB_PASS=$(openssl rand -hex 16)
        echo "TM_ENCRYPTION_KEY=${ENC_KEY}" > "$TM_DIR/.env"
        echo "TM_DB_PASS=${DB_PASS}" >> "$TM_DIR/.env"
        chmod 600 "$TM_DIR/.env"
        echo "🔐 Sichere Datenbank-Passwörter in $TM_DIR/.env generiert!"
    fi

    cp docker-compose.full.yml "$TM_DIR/docker-compose.yml"
    cp bridge/bridge.py "$TM_DIR/bridge.py"
    cp dashstream/dashstream.html "$TM_DIR/tesla-ui/dashstream.html"

    echo "🚀 Starte Komplett-Stack (TeslaMate, Jellyfin, ABS, SABnzbd, Prowlarr, Radarr, Sonarr, Jellyseerr)..."
    (cd "$TM_DIR" && sudo docker compose up -d)
    sleep 8
    JF_CONTAINER="jellyfin"

elif [ "$SETUP_MODE" = "2" ]; then
    read -p "👉 Zielordner für deinen Usenet/*arr-Stack [Standard: $HOME/usenet-stack]: " ARR_DIR
    ARR_DIR=${ARR_DIR:-$HOME/usenet-stack}
    mkdir -p "$ARR_DIR/data/media/movies" "$ARR_DIR/data/media/tv"              "$ARR_DIR/data/usenet/incomplete" "$ARR_DIR/data/usenet/complete/movies" "$ARR_DIR/data/usenet/complete/tv"              "$ARR_DIR/arr-configs/sabnzbd" "$ARR_DIR/arr-configs/prowlarr"              "$ARR_DIR/arr-configs/radarr" "$ARR_DIR/arr-configs/sonarr" "$ARR_DIR/arr-configs/jellyseerr"
    cp docker-compose.usenet.yml "$ARR_DIR/docker-compose.yml"
    echo "🚀 Starte Usenet-Stack (SABnzbd, Prowlarr, Radarr, Sonarr, Jellyseerr)..."
    (cd "$ARR_DIR" && sudo docker compose up -d)
    read -p "👉 Pfad zu deinem TeslaMate-Ordner [Standard: $HOME/teslamate]: " TM_DIR
    TM_DIR=${TM_DIR:-$HOME/teslamate}
    JF_CONTAINER="jellyfin"
else
    read -p "👉 1. Pfad zu deinem bestehenden TeslaMate-Ordner [Standard: $HOME/teslamate]: " TM_DIR
    TM_DIR=${TM_DIR:-$HOME/teslamate}
    read -p "👉 2. Name deines bestehenden Jellyfin-Containers [Standard: jellyfin]: " JF_CONTAINER
    JF_CONTAINER=${JF_CONTAINER:-jellyfin}
fi

mkdir -p "$TM_DIR/tesla-ui"
cp bridge/bridge.py "$TM_DIR/bridge.py" 2>/dev/null || true
cp dashstream/dashstream.html "$TM_DIR/tesla-ui/dashstream.html"

echo ""
echo "🎬 Injiziere DashStream Oberfläche in Jellyfin ($JF_CONTAINER)..."
for dir in "/usr/share/jellyfin/web" "/jellyfin/jellyfin-web"; do
    sudo docker cp -L "$TM_DIR/tesla-ui/dashstream.html" "$JF_CONTAINER:$dir/tesla.html" 2>/dev/null || true
    sudo docker cp -L "$TM_DIR/tesla-ui/dashstream.html" "$JF_CONTAINER:$dir/kitt.html" 2>/dev/null || true
done

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
echo "🎉 INSTALLATION ABGESCHLOSSEN! Deine Web-Interfaces:"
echo "  🚗 DashStream (Tesla UI): http://DEINE-SERVER-IP:8096/web/tesla.html"
echo "  🎧 Audiobookshelf:        http://DEINE-SERVER-IP:13378"
echo "  🍿 Jellyseerr (Wünsche):  http://DEINE-SERVER-IP:5055"
echo "  📥 SABnzbd (Usenet DL):   http://DEINE-SERVER-IP:8080"
echo "  🔎 Prowlarr (Indexer):    http://DEINE-SERVER-IP:9696"
echo "  🎬 Radarr (Filme):        http://DEINE-SERVER-IP:7878"
echo "  📺 Sonarr (Serien):       http://DEINE-SERVER-IP:8989"
echo "  ⚡ TeslaMate & Grafana:   http://DEINE-SERVER-IP:4000 & :3000"
echo "=================================================================="
