#!/usr/bin/env bash
# Deploy the committed HEAD of Visa Assistant (IVAC repo) to the shared Contabo VPS.
# Usage (Git Bash):  bash scripts/deploy.sh
# Steps: upload → backend lint+tests (Docker) → build → migrate+start → smoke test.
# Only committed code is deployed (git archive), never local .env files.
set -euo pipefail

SERVER="${IVAC_SERVER:-root@144.91.74.148}"
REMOTE_DIR="/home/ubuntu/docker/websites/ivac"
DOMAIN="ivac.supersoftltd.com"
COMPOSE="docker compose --env-file $REMOTE_DIR/.env -f $REMOTE_DIR/app/infrastructure/production/docker-compose.yml"

cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree has uncommitted changes — commit first (only HEAD is deployed)." >&2
  exit 1
fi
REV="$(git rev-parse --short HEAD)"
echo "==> Deploying $REV to $SERVER"

# 1. Upload source into a staging dir
git archive --format=tar HEAD | ssh "$SERVER" "
  set -e
  rm -rf $REMOTE_DIR/app.new && mkdir -p $REMOTE_DIR/app.new
  tar -x -C $REMOTE_DIR/app.new
  echo $REV > $REMOTE_DIR/app.new/REVISION
"

# 2. Secrets (first deploy only) and backend tests — abort before touching live containers on failure
ssh "$SERVER" "
  set -e
  if [ ! -f $REMOTE_DIR/.env ]; then
    umask 077
    printf 'POSTGRES_PASSWORD=%s\nREDIS_PASSWORD=%s\n' \"\$(openssl rand -hex 24)\" \"\$(openssl rand -hex 24)\" > $REMOTE_DIR/.env
    echo '    created $REMOTE_DIR/.env with generated secrets'
  fi
  # field-encryption key (passport / NID numbers): generated once, never printed, never rotated here
  if ! grep -q '^DATA_ENCRYPTION_KEY=' $REMOTE_DIR/.env; then
    printf 'DATA_ENCRYPTION_KEY=%s\n' \"\$(openssl rand -base64 32)\" >> $REMOTE_DIR/.env
    echo '    added DATA_ENCRYPTION_KEY to .env — back it up offline (losing it = losing encrypted data)'
  fi
  echo '==> Backend lint + tests'
  docker build --target test -q -t ivac-api-test $REMOTE_DIR/app.new/backend >/dev/null
  docker image rm ivac-api-test >/dev/null
  echo '    passed'
"

# 3. Swap source, build images, migrate + (re)start
ssh "$SERVER" "
  set -e
  rm -rf $REMOTE_DIR/app.prev
  [ -d $REMOTE_DIR/app ] && mv $REMOTE_DIR/app $REMOTE_DIR/app.prev
  mv $REMOTE_DIR/app.new $REMOTE_DIR/app
  # persistent uploads, owned by the API container user (uid 1001), never world-readable
  mkdir -p $REMOTE_DIR/data
  chown 1001:1001 $REMOTE_DIR/data
  chmod 700 $REMOTE_DIR/data
  $COMPOSE build
  $COMPOSE up -d --remove-orphans
  docker image prune -f >/dev/null
  docker builder prune -f --keep-storage 4gb >/dev/null 2>&1 || true

  # nightly DB backup at 03:45 server time
  install -m 755 $REMOTE_DIR/app/infrastructure/production/backup.sh /usr/local/bin/ivac-backup
  echo '45 3 * * * root /usr/local/bin/ivac-backup >> /var/log/ivac-backup.log 2>&1' > /etc/cron.d/ivac-backup
  chmod 644 /etc/cron.d/ivac-backup

  # keep the Nginx site config in sync (only once the domain is enabled; reload only if valid)
  SITE=/home/ubuntu/docker/proxy/data/nginx/custom/sites/ivac.conf
  NEW=$REMOTE_DIR/app/infrastructure/production/nginx/ivac.conf
  if [ -f \$SITE ] && ! cmp -s \$NEW \$SITE; then
    cp \$SITE /root/ivac.conf.bak
    cp \$NEW \$SITE
    if docker exec npm nginx -t >/dev/null 2>&1; then
      docker exec npm nginx -s reload && echo '    nginx site config updated'
    else
      cp /root/ivac.conf.bak \$SITE
      echo '    nginx config test failed; kept the previous config' >&2
    fi
  fi
"

# 4. Smoke test from inside the proxy network
ssh "$SERVER" "
  for i in \$(seq 1 40); do
    docker exec npm sh -c 'curl -fs -o /dev/null http://ivac-web:3000/ && curl -fs -o /dev/null http://ivac-api:8000/api/v1/health/ready' && break
    sleep 3
  done
  docker exec npm sh -c 'curl -s -o /dev/null -w \"web   -> HTTP %{http_code}\n\" http://ivac-web:3000/; curl -s -w \"\nready -> %{http_code}\n\" http://ivac-api:8000/api/v1/health/ready'
"
echo "==> Done: https://$DOMAIN (revision $REV)"
