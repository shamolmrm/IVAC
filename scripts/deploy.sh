#!/usr/bin/env bash
# Deploy the committed HEAD of IVAC to the shared Contabo VPS.
# Usage (Git Bash):  bash scripts/deploy.sh
# Only committed code is deployed (git archive), never local .env files.
set -euo pipefail

SERVER="${IVAC_SERVER:-root@144.91.74.148}"
REMOTE_DIR="/home/ubuntu/docker/websites/ivac"
DOMAIN="ivac.supersoftltd.com"
COMPOSE="docker compose -f $REMOTE_DIR/app/infrastructure/production/docker-compose.yml"

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

# 2. Swap source and (re)start
ssh "$SERVER" "
  set -e
  rm -rf $REMOTE_DIR/app.prev
  [ -d $REMOTE_DIR/app ] && mv $REMOTE_DIR/app $REMOTE_DIR/app.prev
  mv $REMOTE_DIR/app.new $REMOTE_DIR/app
  $COMPOSE up -d --remove-orphans --force-recreate

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

# 3. Smoke test from inside the proxy network
ssh "$SERVER" "
  for i in \$(seq 1 20); do
    docker exec npm sh -c 'curl -fs -o /dev/null http://ivac-web:80/' && break
    sleep 2
  done
  docker exec npm sh -c 'curl -s -o /dev/null -w \"web -> HTTP %{http_code}\n\" http://ivac-web:80/'
"
echo "==> Done: https://$DOMAIN (revision $REV)"
