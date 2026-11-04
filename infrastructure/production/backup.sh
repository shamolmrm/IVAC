#!/usr/bin/env bash
# Nightly PostgreSQL backup for Visa Assistant (installed as /etc/cron.d/ivac-backup by deploy.sh).
# Keeps 14 days of compressed dumps in /home/ubuntu/backups/ivac.
# Restore: gunzip -c FILE | docker exec -i ivac-postgres psql -U ivac -d ivac
set -euo pipefail

DEST=/home/ubuntu/backups/ivac
KEEP_DAYS=14
mkdir -p "$DEST"
chmod 700 "$DEST"

file="$DEST/ivac-$(date +%Y%m%d-%H%M%S).sql.gz"
docker exec ivac-postgres pg_dump -U ivac -d ivac --no-owner --clean --if-exists | gzip -9 > "$file.tmp"
mv "$file.tmp" "$file"
chmod 600 "$file"
find "$DEST" -name 'ivac-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
echo "$(date -Is) backup ok: $file ($(du -h "$file" | cut -f1))"

# Uploaded documents (already encrypted by the app once task 6 lands): local mirror
DATA_SRC=/home/ubuntu/docker/websites/ivac/data
if [ -d "$DATA_SRC" ] && command -v rsync >/dev/null; then
  mkdir -p "$DEST/data" && rsync -a --delete "$DATA_SRC/" "$DEST/data/"
fi
