#!/bin/bash
set -e
TS=$(date +"%Y-%m-%d_%H-%M")
BDIR="$HOME/backups"
TMP_DIR="/tmp/backup_dumps_${TS}"
mkdir -p "$BDIR" "$TMP_DIR"

docker exec teslamate-database-1 pg_dump -U teslamate teslamate > "${TMP_DIR}/teslamate_db.sql" 2>/dev/null || true
PAPERLESS_DB=$(docker ps --format '{{.Names}}' | grep -iE 'paperless.*db|paperless.*postgres' | head -n 1)
if [ -n "$PAPERLESS_DB" ]; then
    docker exec "$PAPERLESS_DB" pg_dumpall -U paperless > "${TMP_DIR}/paperless_db.sql" 2>/dev/null || true
fi

docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" > "${TMP_DIR}/docker_containers.txt"
crontab -l > "${TMP_DIR}/user_crontab.txt" 2>/dev/null || true
cp /etc/systemd/system/telegram-bot.service "${TMP_DIR}/" 2>/dev/null || true

tar -czf "${BDIR}/full_server_backup_${TS}.tar.gz" \
    --exclude="$HOME/backups" \
    --exclude="*/venv/*" \
    --exclude="*/.cache/*" \
    --exclude="*/cache/*" \
    --exclude="*/transcodes/*" \
    --exclude="*/MediaBrowser/cache/*" \
    --exclude="*/metadata/*" \
    --exclude="*/downloads/*" \
    --exclude="*/incomplete/*" \
    --exclude="*/complete/*" \
    --exclude="*/usenet/*" \
    --exclude="*/movies/*" \
    --exclude="*/tv/*" \
    --exclude="*/serien/*" \
    --exclude="*/filme/*" \
    --exclude="*.mkv" \
    --exclude="*.mp4" \
    --exclude="*.avi" \
    --exclude="*.iso" \
    "$TMP_DIR" $HOME /opt 2>/dev/null || true

rm -rf "$TMP_DIR"
ls -1t "${BDIR}"/*backup_*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
LATEST=$(ls -lh "${BDIR}/full_server_backup_${TS}.tar.gz" | awk '{print $5}')
echo "✅ Komplett-Backup fertig: full_server_backup_${TS}.tar.gz (${LATEST})"
