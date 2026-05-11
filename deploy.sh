#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# deploy.sh — YASAFlaskified v0.10.0 automated deployment
# ═══════════════════════════════════════════════════════════════
#
# Installs YASAFlaskified on a vanilla Ubuntu 22.04/24.04 server.
# Run as root or with sudo:
#
#   curl -sSL https://raw.githubusercontent.com/bartromb/yasaflaskified/main/deploy.sh | sudo bash
#
# Or locally:
#   sudo bash deploy.sh
#
# What this script does:
#   1. Creates application user (auto-detected or specified via YASA_USER)
#   2. Installs Docker + Docker Compose
#   3. Installs Nginx + Certbot
#   4. Creates /data/slaapkliniek directory structure
#   5. Clones or copies YASAFlaskified
#   6. Generates .env with random SECRET_KEY
#   7. Configures Nginx reverse proxy
#   8. Configures UFW firewall
#   9. Builds and starts Docker containers
#  10. (Optional) Obtains Let's Encrypt SSL certificate
#
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colors and logging helpers ────────────────────────────────
# Defined first so that error-paths in the configuration block
# below can use err() without printing "command not found".

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${BLUE}══════════════════════════════════════════${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}══════════════════════════════════════════${NC}"; }

# ── Configuration ─────────────────────────────────────────────
# User detection priority:
#   1. YASA_USER environment variable (explicit)
#   2. SUDO_USER (the user who ran sudo)
#   3. logname (login session user)
#   4. Error — require explicit YASA_USER

if [ -n "${YASA_USER:-}" ]; then
    APP_USER="${YASA_USER}"
elif [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    APP_USER="${SUDO_USER}"
elif logname &>/dev/null && [ "$(logname)" != "root" ]; then
    APP_USER="$(logname)"
elif [ -t 0 ]; then
    # Interactive terminal — ask
    read -rp "Linux username for YASAFlaskified: " APP_USER
    [ -z "${APP_USER}" ] && err "No username provided."
else
    # Piped (curl | sudo bash) — no tty, no SUDO_USER
    err "Cannot detect username in pipe mode. Use: curl ... | sudo YASA_USER=yourname bash"
fi

# Safety: never run as root
if [ "${APP_USER}" = "root" ]; then
    err "Refusing to install as root. Set YASA_USER=yourname."
fi
APP_DIR="/data/slaapkliniek"
APP_PORT="${YASA_PORT:-8071}"
DOMAIN="${YASA_DOMAIN:-}"          # Set to enable SSL (e.g. slaapkliniek.be)
ADMIN_PASSWORD="${YASA_ADMIN_PASSWORD:-}"
BRANCH="${YASA_BRANCH:-main}"
REPO="https://github.com/bartromb/yasaflaskified.git"

# ── Pre-flight checks ────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    err "This script must be run as root (use: sudo bash deploy.sh)"
fi

if ! grep -qiE "ubuntu|debian" /etc/os-release 2>/dev/null; then
    warn "This script is designed for Ubuntu/Debian. Proceeding anyway..."
fi

# ══════════════════════════════════════════════════════════════
step "1/10  Creating user '${APP_USER}'"
# ══════════════════════════════════════════════════════════════

if id "${APP_USER}" &>/dev/null; then
    log "User '${APP_USER}' already exists"
else
    adduser --disabled-password --gecos "YASAFlaskified" "${APP_USER}"
    log "User '${APP_USER}' created"
fi

# ══════════════════════════════════════════════════════════════
step "2/10  Installing Docker"
# ══════════════════════════════════════════════════════════════

if command -v docker &>/dev/null; then
    log "Docker already installed: $(docker --version)"
else
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    log "Docker installed: $(docker --version)"
fi

if usermod -aG docker "${APP_USER}"; then
    log "User '${APP_USER}' added to docker group"
else
    warn "Failed to add '${APP_USER}' to docker group — continuing, but the user may need sudo for docker commands."
fi

# ══════════════════════════════════════════════════════════════
step "3/10  Installing Nginx + Certbot"
# ══════════════════════════════════════════════════════════════

apt-get install -y -qq nginx certbot python3-certbot-nginx
systemctl enable nginx
# Ensure nginx is actually running — `enable` only queues for boot.
# Without this, the reload at step 7 would fail with
# "nginx.service is not active, cannot reload".
systemctl start nginx
log "Nginx installed and started"

# ══════════════════════════════════════════════════════════════
step "4/10  Creating directory structure"
# ══════════════════════════════════════════════════════════════

mkdir -p "${APP_DIR}"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}"
log "Created ${APP_DIR}"

# ══════════════════════════════════════════════════════════════
step "5/10  Deploying YASAFlaskified"
# ══════════════════════════════════════════════════════════════

if [ -f "${APP_DIR}/docker-compose.yml" ]; then
    warn "Existing installation found at ${APP_DIR}"
    warn "Pulling latest changes..."
    cd "${APP_DIR}"
    if [ -d .git ]; then
        if ! sudo -u "${APP_USER}" git pull origin "${BRANCH}"; then
            warn "git pull failed (merge conflict or local changes?) — continuing with the existing checkout."
            warn "Resolve manually with: cd ${APP_DIR} && sudo -u ${APP_USER} git status"
        fi
    fi
else
    # Check if we're running from inside the repo. BASH_SOURCE is
    # unset when the script is piped from stdin (curl | sudo bash),
    # so guard against set -u with :- and fall through to git clone.
    if [ -n "${BASH_SOURCE[0]:-}" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    else
        SCRIPT_DIR=""
    fi
    if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/docker-compose.yml" ] && [ -f "${SCRIPT_DIR}/Dockerfile" ]; then
        log "Copying from local source: ${SCRIPT_DIR}"
        cp -r "${SCRIPT_DIR}/"* "${APP_DIR}/"
        cp -r "${SCRIPT_DIR}/".[!.]* "${APP_DIR}/" 2>/dev/null || true
    else
        log "Cloning from ${REPO} (branch: ${BRANCH})"
        apt-get install -y -qq git
        sudo -u "${APP_USER}" git clone --branch "${BRANCH}" "${REPO}" "${APP_DIR}"
    fi
fi

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
log "YASAFlaskified deployed to ${APP_DIR}"

# ══════════════════════════════════════════════════════════════
step "6/10  Generating .env and instance/config.json"
# ══════════════════════════════════════════════════════════════
#
# In the current layout SECRET_KEY and ADMIN_PASSWORD live in
# instance/config.json (not .env). The .env file only carries the
# image tag for Docker Compose interpolation.

ENV_FILE="${APP_DIR}/.env"
CONFIG_FILE="${APP_DIR}/instance/config.json"
EXPECTED_VERSION="$(grep -oE '__version__\s*=\s*"[^"]+"' \
    "${APP_DIR}/myproject/version.py" 2>/dev/null \
    | sed -E 's/.*"([^"]+)".*/\1/' || true)"
[ -z "${EXPECTED_VERSION}" ] && EXPECTED_VERSION="0.10.0"

# ── .env (Docker Compose image tag) ───────────────────────────
if [ -f "${ENV_FILE}" ]; then
    warn ".env already exists — leaving in place"
else
    cp "${APP_DIR}/.env.example" "${ENV_FILE}"
    # Pin APP_VERSION to whatever myproject/version.py declares.
    sed -i -E "s|^APP_VERSION=.*|APP_VERSION=${EXPECTED_VERSION}|" "${ENV_FILE}"
    chmod 600 "${ENV_FILE}"
    chown "${APP_USER}:${APP_USER}" "${ENV_FILE}"
    log ".env created (APP_VERSION=${EXPECTED_VERSION})"
fi

# ── instance/config.json (SECRET_KEY + ADMIN_PASSWORD) ────────
mkdir -p "${APP_DIR}/instance"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/instance"

if [ -f "${CONFIG_FILE}" ]; then
    warn "instance/config.json already exists — not overwriting"
    warn "To regenerate: rm ${CONFIG_FILE} && re-run this script"
else
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
        || openssl rand -hex 32)

    if [ -z "${ADMIN_PASSWORD}" ]; then
        ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null \
            || openssl rand -base64 16)
        warn "Generated admin password: ${ADMIN_PASSWORD}"
        warn "SAVE THIS PASSWORD — it will not be shown again!"
    fi

    # Sanity check: the template must contain both placeholders.
    # Catches the silent-no-op bug class where config.json.example
    # is renamed or restructured without updating this script.
    SRC_TEMPLATE="${APP_DIR}/config.json.example"
    if ! grep -q "VERANDER_DIT_NAAR_EEN_LANGE_WILLEKEURIGE_STRING" "${SRC_TEMPLATE}" \
       || ! grep -q "VERANDER_DIT_WACHTWOORD" "${SRC_TEMPLATE}"; then
        err "config.json.example is missing the expected VERANDER_DIT_* placeholders — deploy.sh and the template are out of sync."
    fi

    cp "${SRC_TEMPLATE}" "${CONFIG_FILE}"

    # Use # as delimiter so any | or / in the generated secrets is safe.
    sed -i "s#VERANDER_DIT_NAAR_EEN_LANGE_WILLEKEURIGE_STRING#${SECRET_KEY}#" "${CONFIG_FILE}"
    sed -i "s#VERANDER_DIT_WACHTWOORD#${ADMIN_PASSWORD}#" "${CONFIG_FILE}"

    # Belt-and-braces: confirm no placeholder is left behind.
    if grep -q "VERANDER_DIT" "${CONFIG_FILE}"; then
        err "Placeholder substitution incomplete in ${CONFIG_FILE} — refusing to ship a half-configured file."
    fi

    chmod 600 "${CONFIG_FILE}"
    chown "${APP_USER}:${APP_USER}" "${CONFIG_FILE}"
    log "instance/config.json created with random SECRET_KEY"
fi

# ══════════════════════════════════════════════════════════════
step "7/10  Configuring Nginx reverse proxy"
# ══════════════════════════════════════════════════════════════

NGINX_CONF="/etc/nginx/sites-available/yasaflaskified"

if [ -n "${DOMAIN}" ]; then
    SERVER_NAME="${DOMAIN} www.${DOMAIN}"
else
    SERVER_NAME="_"
    warn "No DOMAIN set — Nginx will listen on all hostnames"
    warn "Set YASA_DOMAIN=yourdomain.com to configure specific domain"
fi

cat > "${NGINX_CONF}" << NGINXEOF
server {
    listen 80;
    server_name ${SERVER_NAME};

    client_max_body_size 520M;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
NGINXEOF

ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

if ! nginx -t; then
    err "Nginx config test failed — refusing to reload. Inspect: nginx -t"
fi
# Reload if nginx is already running, otherwise start it. This avoids
# the "nginx.service is not active, cannot reload" failure on fresh
# installs where step 3 enabled but did not start nginx.
if systemctl is-active --quiet nginx; then
    systemctl reload nginx
else
    systemctl start nginx
fi
log "Nginx configured → http://$(hostname -I | awk '{print $1}'):80"

# ══════════════════════════════════════════════════════════════
step "8/10  Configuring firewall (UFW)"
# ══════════════════════════════════════════════════════════════

if command -v ufw &>/dev/null; then
    ufw allow 22/tcp   comment "SSH"   >/dev/null 2>&1 || warn "ufw allow 22 failed"
    ufw allow 80/tcp   comment "HTTP"  >/dev/null 2>&1 || warn "ufw allow 80 failed"
    ufw allow 443/tcp  comment "HTTPS" >/dev/null 2>&1 || warn "ufw allow 443 failed"
    ufw --force enable >/dev/null 2>&1 || warn "ufw enable failed"
    log "UFW firewall enabled (SSH + HTTP + HTTPS)"
else
    warn "UFW not found — firewall not configured"
fi

# ══════════════════════════════════════════════════════════════
step "9/10  Building and starting Docker containers"
# ══════════════════════════════════════════════════════════════

cd "${APP_DIR}"

sudo -u "${APP_USER}" docker compose build 2>&1 | tail -5
sudo -u "${APP_USER}" docker compose up -d

# Count expected services from docker-compose.yml so the health
# check stays correct if worker count or service set changes.
EXPECTED_SERVICES="$(sudo -u "${APP_USER}" docker compose config --services | wc -l)"
log "Waiting for ${EXPECTED_SERVICES} services to reach 'running' state (timeout 60s)..."

DEADLINE=$((SECONDS + 60))
while [ ${SECONDS} -lt ${DEADLINE} ]; do
    RUNNING="$(sudo -u "${APP_USER}" docker compose ps --status=running --services 2>/dev/null | wc -l)"
    if [ "${RUNNING}" -eq "${EXPECTED_SERVICES}" ]; then
        break
    fi
    sleep 2
done

if [ "${RUNNING}" -eq "${EXPECTED_SERVICES}" ]; then
    log "All ${EXPECTED_SERVICES} services are running."
    sudo -u "${APP_USER}" docker compose ps
else
    warn "${RUNNING}/${EXPECTED_SERVICES} services running after timeout."
    warn "Inspect with: cd ${APP_DIR} && docker compose logs --tail 50"
    sudo -u "${APP_USER}" docker compose ps
fi

# End-to-end smoke check: does Flask actually respond on the bound port?
log "Smoke-checking http://127.0.0.1:${APP_PORT} ..."
if curl -fsS --max-time 10 "http://127.0.0.1:${APP_PORT}/" -o /dev/null; then
    log "Flask responded on port ${APP_PORT}."
else
    warn "Flask did not respond on port ${APP_PORT} within 10s."
    warn "Inspect with: cd ${APP_DIR} && docker compose logs --tail 100 app"
fi

# ══════════════════════════════════════════════════════════════
step "10/10  SSL Certificate (Let's Encrypt)"
# ══════════════════════════════════════════════════════════════

if [ -n "${DOMAIN}" ]; then
    log "Requesting SSL certificate for ${DOMAIN}..."
    certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" \
        --non-interactive --agree-tos --email "admin@${DOMAIN}" \
        --redirect \
        || warn "Certbot failed — you can retry manually: certbot --nginx -d ${DOMAIN}"
else
    warn "No DOMAIN set — skipping SSL"
    warn "To add SSL later:"
    warn "  certbot --nginx -d yourdomain.com -d www.yourdomain.com"
fi

# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  YASAFlaskified deployment complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo "  Application:  http://$(hostname -I | awk '{print $1}')"
[ -n "${DOMAIN}" ] && echo "  Domain:       https://${DOMAIN}"
echo "  Login:        admin / <password from step 6>"
echo "  App directory: ${APP_DIR}"
echo ""
echo "  Useful commands:"
echo "    cd ${APP_DIR}"
echo "    docker compose logs -f app       # Flask logs"
echo "    docker compose logs -f worker    # Analysis worker"
echo "    docker compose restart           # Restart all"
echo "    docker compose down              # Stop all"
echo ""
echo "  Update to latest version:"
echo "    cd ${APP_DIR}"
echo "    git pull"
echo "    docker compose build --no-cache"
echo "    docker compose up -d"
echo ""
