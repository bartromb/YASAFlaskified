#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# redeploy.sh — PURGE + fresh reinstall of YASAFlaskified
# ═══════════════════════════════════════════════════════════════
#
# ⚠️  DESTRUCTIVE — TEST / THROWAWAY INSTANCES ONLY.
# Removes ALL yasaflaskified containers + images AND everything under
# /data/slaapkliniek (uploads, processed, instance/users.db, the admin
# password in instance/config.json). Then clones the latest main and runs
# deploy.sh from scratch (which generates a NEW random admin password).
#
# Usage (run as root on the target box):
#     sudo bash redeploy.sh                 # interactive confirmation
#     sudo YASA_PURGE_CONFIRM=yes bash redeploy.sh   # non-interactive
#
# Bootstrap on a fresh box (no checkout yet):
#     curl -sSL https://raw.githubusercontent.com/bartromb/YASAFlaskified/main/redeploy.sh \
#       | sudo YASA_USER=bart YASA_PURGE_CONFIRM=yes bash
#
# Env knobs: YASA_USER (default bart), YASA_APP_DIR (/data/slaapkliniek),
#            YASA_REPO, YASA_BRANCH (main), YASA_SRC (/root/YASAFlaskified-src),
#            YASA_PORT (8071), YASA_PURGE_CONFIRM (skip prompt if "yes").
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="${YASA_APP_DIR:-/data/slaapkliniek}"
APP_USER="${YASA_USER:-bart}"
REPO="${YASA_REPO:-https://github.com/bartromb/YASAFlaskified.git}"
BRANCH="${YASA_BRANCH:-main}"
SRC_DIR="${YASA_SRC:-/root/YASAFlaskified-src}"
APP_PORT="${YASA_PORT:-8071}"

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; BLU='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GRN}[✓]${NC} $1"; }
warn() { echo -e "${YEL}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${BLU}── $1 ──${NC}"; }

[ "$(id -u)" -eq 0 ] || err "Run as root:  sudo bash redeploy.sh"
command -v docker >/dev/null || err "Docker not found — run deploy.sh for a first install instead."

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

# ── Safety gate ────────────────────────────────────────────────
if [ "${YASA_PURGE_CONFIRM:-}" != "yes" ]; then
    warn "This PERMANENTLY DELETES ${APP_DIR} (all PSGs, users, admin password)"
    warn "and every yasaflaskified Docker container/image on host ${IP:-this machine}."
    warn "TEST / THROWAWAY INSTANCES ONLY — never run this on production."
    read -rp "Type 'PURGE' to continue: " ans
    [ "${ans}" = "PURGE" ] || err "Aborted (no changes made)."
fi

# ── 1. Stop + remove old containers and volumes ───────────────
step "1/4  Stopping old stack"
if [ -f "${APP_DIR}/docker-compose.yml" ]; then
    ( cd "${APP_DIR}" && docker compose down -v --remove-orphans ) \
        || warn "compose down failed (continuing anyway)"
else
    warn "no ${APP_DIR}/docker-compose.yml — nothing to compose-down"
fi

# ── 2. Remove old images ──────────────────────────────────────
step "2/4  Removing old images"
# shellcheck disable=SC2046
docker rmi -f $(docker images 'yasaflaskified*' -q | sort -u) 2>/dev/null || true
docker image prune -f >/dev/null 2>&1 || true

# ── 3. Wipe app dir + fetch latest source ─────────────────────
step "3/4  Wiping ${APP_DIR} and fetching latest source"
rm -rf "${APP_DIR}"
rm -rf "${SRC_DIR}"
command -v git >/dev/null || { apt-get update -qq && apt-get install -y -qq git; }
git clone --branch "${BRANCH}" "${REPO}" "${SRC_DIR}"
log "cloned ${BRANCH} → ${SRC_DIR} ($(cd "${SRC_DIR}" && git rev-parse --short HEAD))"

# ── 4. Fresh install via deploy.sh ────────────────────────────
step "4/4  Running deploy.sh (fresh install)"
cd "${SRC_DIR}"
YASA_USER="${APP_USER}" bash deploy.sh

echo
log "Redeploy complete. ⚠️ A NEW admin password was printed above — save it."
echo   "  Verify:"
echo   "    cd ${APP_DIR} && docker compose ps"
echo   "    docker compose exec -T app pip show psgscoring | grep Version"
echo   "    curl -fsS http://localhost:${APP_PORT}/ -o /dev/null && echo 'Flask OK'"
[ -n "${IP}" ] && echo "    open  http://${IP}/   (nginx → :${APP_PORT})"
