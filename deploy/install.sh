#!/usr/bin/env bash
# One-command install/upgrade on a fresh Ubuntu 22.04/24.04 VPS (run inside the project folder):
#   sudo bash deploy/install.sh [your-domain.com]
# Without a domain the site uses https://<server-ip>.sslip.io with a free Let's Encrypt certificate.
set -euo pipefail
cd "$(dirname "$0")/.."
DOMAIN="${1:-}"
COMPOSE="docker compose -f compose.yaml -f compose.prod.yaml --profile rag"
log() { printf '\n==> %s\n' "$*"; }
set_env() { # set_env KEY VALUE  (replace or append, value never echoed)
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else printf '%s=%s\n' "$1" "$2" >> .env; fi
}
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo bash deploy/install.sh"; exit 1; }

log "1/7 Docker"
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq docker.io docker-compose-v2 || apt-get install -y -qq docker.io docker-compose-plugin
  systemctl enable --now docker
fi
docker compose version

log "2/7 Firewall (SSH, HTTP, HTTPS only)"
if command -v ufw >/dev/null; then
  # sudo drops SSH_CONNECTION; fall back to the port sshd listens on, then 22.
  SSH_PORT="${SSH_CONNECTION:-}"; SSH_PORT="${SSH_PORT##* }"
  [ -n "$SSH_PORT" ] || SSH_PORT="$(ss -tlnp 2>/dev/null | awk '/sshd/{sub(/.*:/,"",$4); print $4; exit}')"
  ufw allow "${SSH_PORT:-22}/tcp" >/dev/null
  ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw allow 443/udp >/dev/null
  ufw --force enable >/dev/null && ufw status | head -8
fi

log "2b/7 Swap (helps image builds on small servers)"
if [ "$(swapon --show | wc -l)" -eq 0 ] && [ "$(free -m | awk '/Mem/{print $2}')" -lt 6000 ]; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
swapon --show

log "3/7 Configuration (.env)"
[ -f .env ] || cp .env.example .env
chmod 600 .env
ask() { # ask "prompt" -> value, or empty when nobody is at the keyboard (remote/non-interactive run)
  local v=""; if [ -t 0 ]; then read -rsp "$1" v || true; echo; fi; printf '%s' "$v"; }
if ! grep -q '^OPENAI_API_KEY=.\+' .env; then v="$(ask 'OpenAI API key (input hidden): ')"; [ -n "$v" ] || { echo "OPENAI_API_KEY missing in .env"; exit 1; }; set_env OPENAI_API_KEY "$v"; fi
grep -q '^LIGHTRAG_API_KEY=.\+' .env || set_env LIGHTRAG_API_KEY "$(openssl rand -hex 24)"
if ! grep -q '^ADMIN_PASSWORD=.\+' .env; then
  pw="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-20)"; set_env ADMIN_PASSWORD "$pw"
  printf 'admin / %s\n' "$pw" > .admin-login.txt; chmod 600 .admin-login.txt
fi
if ! grep -q '^STRIPE_SECRET_KEY=sk_test_' .env; then
  v="$(ask 'Stripe TEST secret key sk_test_... (Enter to skip payments): ')"
  case "$v" in sk_test_*) set_env STRIPE_SECRET_KEY "$v" ;; "") ;; *) echo "Only sk_test_ keys are accepted; payments stay off." ;; esac
fi
if [ -z "$DOMAIN" ]; then
  IP="$(curl -4 -fsS --max-time 5 https://api.ipify.org || hostname -I | awk '{print $1}')"
  DOMAIN="${IP//./-}.sslip.io"
fi
set_env SITE_ADDRESS "$DOMAIN"; set_env PUBLIC_BASE_URL "https://$DOMAIN"; set_env COOKIE_SECURE true
grep -q '^KB_VERSION=' .env || set_env KB_VERSION plimo-estimate-v9

log "4/7 Build and start"
$COMPOSE build
# Volumes created by older versions may be root-owned; the API runs as uid 10001.
$COMPOSE run --rm --no-deps --user root --entrypoint sh api -c 'chown -R 10001:10001 /app/data'
$COMPOSE up -d
for i in $(seq 1 60); do
  $COMPOSE exec -T api python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/ready',timeout=3)" 2>/dev/null && break
  sleep 5; [ "$i" -eq 60 ] && { echo "API not ready; see: $COMPOSE logs api"; exit 1; }
done

log "5/7 Knowledge base"
# Every deploy checks the knowledge base: complete -> nothing to do (no OpenAI cost),
# failed documents -> retried, new volume -> indexed. Waits until LightRAG is done.
if ! $COMPOSE exec -T api python ingest.py --ensure; then
  echo "WARNING: knowledge base is not complete. Chat answers will lack shop documents until it is."
  echo "         Fix the cause (usually OpenAI credit) and run deploy again."
fi

log "6/7 Demo data for reviewers (demo_admin is locked on public servers)"
$COMPOSE exec -T api python seed_demo.py --lock-admin

log "7/7 Daily backups (03:17, keep 7 days)"
install -m 755 deploy/backup.sh /usr/local/bin/plimo-backup
printf '17 3 * * * root PLIMO_DIR=%s /usr/local/bin/plimo-backup >> /var/log/plimo-backup.log 2>&1\n' "$(pwd)" > /etc/cron.d/plimo-backup

cat <<DONE

Plimo is running at: https://$DOMAIN
Admin login:  see $(pwd)/.admin-login.txt (or ADMIN_PASSWORD in .env)
Demo member:  demo_user / PlimoMemberDemo2026!
Stripe webhook (test mode): add endpoint https://$DOMAIN/api/stripe/webhook
  events: checkout.session.completed, checkout.session.async_payment_succeeded, checkout.session.expired
  then put its signing secret in .env as STRIPE_WEBHOOK_SECRET=whsec_... and run: $COMPOSE up -d api
Status: $COMPOSE ps    Logs: $COMPOSE logs -f api
DONE
