#!/usr/bin/env bash
# From your computer: copy the project to the VPS and run the installer there.
#   bash deploy/deploy.sh root@203.0.113.10 [your-domain.com]
# Fill in .env.vps first (it is uploaded as the server's .env); without it the installer asks on the VPS.
set -euo pipefail
TARGET="${1:?usage: deploy/deploy.sh user@server [domain]}"; DOMAIN="${2:-}"; DIR="${PLIMO_REMOTE_DIR:-/opt/plimo}"
cd "$(dirname "$0")/.."
ssh "$TARGET" "command -v rsync >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq rsync); sudo mkdir -p $DIR && sudo chown \$(id -u):\$(id -g) $DIR"
rsync -az --delete --exclude .git --exclude .env --exclude .admin-login.txt --exclude .openai --exclude .DS_Store \
  --exclude __pycache__ --exclude 'qa/results' --exclude 'deploy/.ingested-*' ./ "$TARGET:$DIR/"
# Server settings: .env.vps (filled in locally, never committed) is uploaded as the server's .env.
if [ -f .env.vps ]; then scp .env.vps "$TARGET:$DIR/.env" && ssh "$TARGET" "chmod 600 $DIR/.env"
elif [ "${PLIMO_COPY_ENV:-0}" = 1 ]; then scp .env "$TARGET:$DIR/.env"; fi
ssh -t "$TARGET" "cd $DIR && sudo bash deploy/install.sh $DOMAIN"
