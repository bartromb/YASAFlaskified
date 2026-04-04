#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# upgrade_v0822.sh — YASAFlaskified v0.8.19 → v0.8.22
# ═══════════════════════════════════════════════════════════════
# Run as user bart on dedodedodo.be:
#
#   bash /data/slaapkliniek/upgrade_v0822.sh
#
# What this script does:
#   1. Backs up current code to /data/slaapkliniek/_backup_pre_v0822/
#   2. Copies patched files into place
#   3. Rebuilds Docker image (--no-cache)
#   4. Restarts all containers (app + workers)
#   5. Verifies health endpoint returns v0.8.22
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

BASE="/data/slaapkliniek"
BACKUP="${BASE}/_backup_pre_v0822"
STAMP=$(date +%Y%m%d_%H%M%S)

echo "═══════════════════════════════════════════════════"
echo "  YASAFlaskified upgrade → v0.8.22"
echo "  $(date)"
echo "═══════════════════════════════════════════════════"

# ── 1. Backup ─────────────────────────────────────────────────
echo ""
echo "▶ [1/5] Backup huidige code..."
mkdir -p "${BACKUP}"
for f in \
    myproject/generate_pdf_report.py \
    myproject/psgscoring/spo2.py \
    myproject/yasa_analysis.py \
    myproject/app.py \
    myproject/i18n.py \
    myproject/psgscoring/signal_quality.py \
    docker-compose.yml \
    CHANGES.md \
    README.md \
    DISCLAIMER.md; do
    if [ -f "${BASE}/${f}" ]; then
        mkdir -p "${BACKUP}/$(dirname ${f})"
        cp "${BASE}/${f}" "${BACKUP}/${f}.${STAMP}"
        echo "   ✓ ${f}"
    fi
done
echo "   Backup → ${BACKUP}"

# ── 2. Kopieer gepatste bestanden ────────────────────────────
echo ""
echo "▶ [2/5] Installeer v0.8.22 bestanden..."
PATCH_DIR="$(cd "$(dirname "$0")" && pwd)"

for f in \
    myproject/generate_pdf_report.py \
    myproject/psgscoring/spo2.py \
    myproject/yasa_analysis.py \
    myproject/app.py \
    myproject/i18n.py \
    myproject/psgscoring/signal_quality.py \
    docker-compose.yml \
    CHANGES.md \
    README.md \
    DISCLAIMER.md; do
    if [ -f "${PATCH_DIR}/${f}" ]; then
        cp "${PATCH_DIR}/${f}" "${BASE}/${f}"
        echo "   ✓ ${f}"
    else
        echo "   ⚠ ${f} niet gevonden in patch — overgeslagen"
    fi
done

# ── 3. Rebuild Docker image ──────────────────────────────────
echo ""
echo "▶ [3/5] Docker image rebuilden (--no-cache)..."
cd "${BASE}"
docker compose build --no-cache app
echo "   ✓ Image gebouwd"

# ── 4. Herstart containers ───────────────────────────────────
echo ""
echo "▶ [4/5] Containers herstarten..."
docker compose down
docker compose up -d
echo "   ✓ Containers gestart"

# ── 5. Verificatie ───────────────────────────────────────────
echo ""
echo "▶ [5/5] Wachten op health check..."
sleep 15
HEALTH=$(curl -sf http://127.0.0.1:8071/health 2>/dev/null || echo '{"error":"unreachable"}')
VERSION=$(echo "${HEALTH}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")

if [ "${VERSION}" = "0.8.22" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  ✅ YASAFlaskified v0.8.22 draait!"
    echo "  Health: ${HEALTH}"
    echo "═══════════════════════════════════════════════════"
else
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  ⚠ Versie-check: verwacht 0.8.22, got '${VERSION}'"
    echo "  Health: ${HEALTH}"
    echo "  → Check logs: docker compose logs app --tail 50"
    echo "═══════════════════════════════════════════════════"
    exit 1
fi
