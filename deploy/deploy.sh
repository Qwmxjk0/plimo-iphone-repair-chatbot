#!/usr/bin/env bash
# From your computer: copy the project to the VPS and run the installer there.
#   bash deploy/deploy.sh root@203.0.113.10 [your-domain.com]
# Uses your local .env (see .env.example); missing values are asked for on the VPS.
set -euo pipefail
TARGET="${1:?usage: deploy/deploy.sh user@server [domain]}"; DOMAIN="${2:-}"; DIR="${PLIMO_REMOTE_DIR:-/opt/plimo}"
cd "$(dirname "$0")/.."
ssh "$TARGET" "command -v rsync >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq rsync); sudo mkdir -p $DIR && sudo chown \$(id -u):\$(id -g) $DIR"
rsync -az --delete --exclude .git --exclude .env --exclude .admin-login.txt --exclude .openai --exclude .DS_Store \
  --exclude __pycache__ --exclude 'qa/results' --exclude 'deploy/.ingested-*' ./ "$TARGET:$DIR/"
# One settings file: your local .env is uploaded; install.sh then sets the server-only values
# (SITE_ADDRESS, PUBLIC_BASE_URL, COOKIE_SECURE=true). Set PLIMO_COPY_ENV=0 to type secrets on the VPS instead.
if [ -f .env ] && [ "${PLIMO_COPY_ENV:-1}" = 1 ]; then scp .env "$TARGET:$DIR/.env" && ssh "$TARGET" "chmod 600 $DIR/.env"; fi
ssh -t "$TARGET" "cd $DIR && sudo bash deploy/install.sh $DOMAIN"
