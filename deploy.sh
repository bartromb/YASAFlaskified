#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# deploy.sh — YASAFlaskified v0.8.30 automated deployment
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

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${BLUE}══════════════════════════════════════════${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}══════════════════════════════════════════${NC}"; }

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

usermod -aG docker "${APP_USER}" 2>/dev/null || true
log "User '${APP_USER}' added to docker group"

# ══════════════════════════════════════════════════════════════
step "3/10  Installing Nginx + Certbot"
# ══════════════════════════════════════════════════════════════

apt-get install -y -qq nginx certbot python3-certbot-nginx
systemctl enable nginx
log "Nginx installed and enabled"

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
        sudo -u "${APP_USER}" git pull origin "${BRANCH}" || true
    fi
else
    # Check if we're running from inside the repo
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "${SCRIPT_DIR}/docker-compose.yml" ] && [ -f "${SCRIPT_DIR}/Dockerfile" ]; then
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
step "6/10  Generating .env configuration"
# ══════════════════════════════════════════════════════════════

ENV_FILE="${APP_DIR}/.env"

if [ -f "${ENV_FILE}" ]; then
    warn ".env already exists — not overwriting"
    warn "To regenerate: rm ${ENV_FILE} && re-run this script"
else
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
        || openssl rand -hex 32)

    if [ -z "${ADMIN_PASSWORD}" ]; then
        ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null \
            || openssl rand -base64 16)
        warn "Generated admin password: ${ADMIN_PASSWORD}"
        warn "SAVE THIS PASSWORD — it will not be shown again!"
    fi

    cp "${APP_DIR}/.env.example" "${ENV_FILE}"

    sed -i "s|VERANDER_DIT_NAAR_EEN_LANGE_WILLEKEURIGE_STRING|${SECRET_KEY}|" "${ENV_FILE}"
    sed -i "s|VERANDER_DIT_WACHTWOORD|${ADMIN_PASSWORD}|" "${ENV_FILE}"

    chmod 600 "${ENV_FILE}"
    chown "${APP_USER}:${APP_USER}" "${ENV_FILE}"
    log ".env created with random SECRET_KEY"
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

nginx -t && systemctl reload nginx
log "Nginx configured → http://$(hostname -I | awk '{print $1}'):80"

# ══════════════════════════════════════════════════════════════
step "8/10  Configuring firewall (UFW)"
# ══════════════════════════════════════════════════════════════

if command -v ufw &>/dev/null; then
    ufw allow 22/tcp   comment "SSH"      >/dev/null 2>&1 || true
    ufw allow 80/tcp   comment "HTTP"     >/dev/null 2>&1 || true
    ufw allow 443/tcp  comment "HTTPS"    >/dev/null 2>&1 || true
    echo "y" | ufw enable >/dev/null 2>&1 || true
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

log "Waiting for containers to start..."
sleep 10

if sudo -u "${APP_USER}" docker compose ps | grep -q "running"; then
    log "Containers are running!"
    echo ""
    sudo -u "${APP_USER}" docker compose ps
else
    warn "Some containers may not be running. Check with:"
    warn "  cd ${APP_DIR} && docker compose logs"
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
