#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# upgrade_v0825.sh — Upgrade YASAFlaskified to v0.8.29
# ═══════════════════════════════════════════════════════════════
#
# Run on the Hetzner server (65.108.230.243):
#
#   METHOD A — From zip upload:
#     scp YASAFlaskified_v0_8_25.zip root@65.108.230.243:/tmp/
#     ssh root@65.108.230.243 "bash /tmp/upgrade_v0825.sh"
#
#   METHOD B — From GitHub:
#     ssh root@65.108.230.243
#     cd /data/slaapkliniek && git pull && bash upgrade_v0825.sh
#
# What this script does:
#   1. Backs up current deployment
#   2. Extracts new files (preserving .env, config.json, uploads, DB)
#   3. Rebuilds Docker image (--no-cache for Python changes)
#   4. Restarts all containers
#   5. Verifies health
#
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

APP_DIR="${YASA_DIR:-/data/slaapkliniek}"
ZIP_FILE="${1:-/tmp/YASAFlaskified_v0_8_25.zip}"
BACKUP_DIR="/data/backups/slaapkliniek_$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  YASAFlaskified v0.8.29 Upgrade${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# ── Pre-checks ───────────────────────────────────────────────
[ -d "${APP_DIR}" ] || err "App directory not found: ${APP_DIR}"
[ -f "${APP_DIR}/docker-compose.yml" ] || err "Not a YASAFlaskified installation: ${APP_DIR}"

# ── Step 1: Backup ───────────────────────────────────────────
log "Step 1/5: Backing up to ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"
cp -a "${APP_DIR}/docker-compose.yml" "${BACKUP_DIR}/"
cp -a "${APP_DIR}/Dockerfile" "${BACKUP_DIR}/"
cp -a "${APP_DIR}/myproject/" "${BACKUP_DIR}/myproject/"
[ -f "${APP_DIR}/.env" ] && cp -a "${APP_DIR}/.env" "${BACKUP_DIR}/"
[ -f "${APP_DIR}/config.json" ] && cp -a "${APP_DIR}/config.json" "${BACKUP_DIR}/"
log "Backup complete: $(du -sh ${BACKUP_DIR} | cut -f1)"

# ── Step 2: Extract new files ────────────────────────────────
if [ -f "${ZIP_FILE}" ]; then
    log "Step 2/5: Extracting from ${ZIP_FILE}"
    TMP_DIR=$(mktemp -d)
    unzip -qo "${ZIP_FILE}" -d "${TMP_DIR}"

    # Sync new files, preserving user data
    rsync -a --exclude='.env' \
             --exclude='config.json' \
             --exclude='myproject/uploads/' \
             --exclude='myproject/results/' \
             --exclude='myproject/*.db' \
             --exclude='myproject/*.sqlite3' \
             "${TMP_DIR}/" "${APP_DIR}/"
    rm -rf "${TMP_DIR}"
elif [ -d "${APP_DIR}/.git" ]; then
    log "Step 2/5: Git-based deployment detected, files already updated"
else
    err "No zip file found at ${ZIP_FILE} and no git repo. Provide zip path as argument."
fi

# ── Step 3: Rebuild Docker image ─────────────────────────────
log "Step 3/5: Rebuilding Docker image (--no-cache)"
cd "${APP_DIR}"
docker compose build --no-cache 2>&1 | tail -10
log "Build complete"

# ── Step 4: Restart containers ───────────────────────────────
log "Step 4/5: Restarting containers"
docker compose down
docker compose up -d
sleep 8

# ── Step 5: Health check ─────────────────────────────────────
log "Step 5/5: Health check"

if docker compose ps | grep -q "running"; then
    echo ""
    docker compose ps
    echo ""

    # HTTP check
    HTTP_CODE=$(curl -so /dev/null -w '%{http_code}' http://127.0.0.1:8071/ 2>/dev/null || echo "000")
    if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "302" ]; then
        log "HTTP OK (${HTTP_CODE})"
    else
        warn "HTTP returned ${HTTP_CODE} — app may still be starting"
    fi

    # Version check
    VERSION=$(docker compose exec -T app python3 -c "from version import __version__; print(__version__)" 2>/dev/null || echo "?")
    log "Running version: ${VERSION}"
else
    err "Containers not running! Check: docker compose logs"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Upgrade to v0.8.29 complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "  Backup:   ${BACKUP_DIR}"
echo "  Rollback: rsync -a ${BACKUP_DIR}/myproject/ ${APP_DIR}/myproject/"
echo "            cd ${APP_DIR} && docker compose build --no-cache && docker compose up -d"
echo ""
echo "  Verify:   https://slaapkliniek.be"
echo "  Logs:     cd ${APP_DIR} && docker compose logs -f --tail=50"
echo ""
