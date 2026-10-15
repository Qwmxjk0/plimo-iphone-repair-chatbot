#!/usr/bin/env bash
# From your computer: copy the project to the VPS and run the installer there.
#   bash deploy/deploy.sh root@203.0.113.10 [your-domain.com]
# Secrets are typed on the VPS when asked; set PLIMO_COPY_ENV=1 to copy your local .env instead.
set -euo pipefail
TARGET="${1:?usage: deploy/deploy.sh user@server [domain]}"; DOMAIN="${2:-}"; DIR="${PLIMO_REMOTE_DIR:-/opt/plimo}"
cd "$(dirname "$0")/.."
ssh "$TARGET" "sudo mkdir -p $DIR && sudo chown \$(id -u):\$(id -g) $DIR"
rsync -az --delete --exclude .git --exclude .env --exclude .admin-login.txt --exclude .openai --exclude .DS_Store \
  --exclude __pycache__ --exclude 'qa/results' --exclude 'deploy/.ingested-*' ./ "$TARGET:$DIR/"
[ "${PLIMO_COPY_ENV:-0}" = 1 ] && scp .env "$TARGET:$DIR/.env"
ssh -t "$TARGET" "cd $DIR && sudo bash deploy/install.sh $DOMAIN"
