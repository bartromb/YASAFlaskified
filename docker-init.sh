#!/bin/bash
set -e

APP_DIR="/data/slaapkliniek"
PROJECT_DIR="${APP_DIR}/myproject"

echo "──────────────────────────────────────────"
echo " YASAFlaskified v12 — opstart"
echo " Pad: ${APP_DIR}"
echo "──────────────────────────────────────────"

for dir in uploads processed logs instance .mplconfig .numba_cache; do
    mkdir -p "${APP_DIR}/${dir}"
done

# Numba cache seeden als volume leeg is
NUMBA_DIR="${APP_DIR}/.numba_cache"
NUMBA_SEED="${APP_DIR}/.numba_cache_seed"
if [ -d "$NUMBA_SEED" ] && [ -z "$(ls -A "$NUMBA_DIR" 2>/dev/null)" ]; then
    echo "[init] Numba cache seeden vanuit build..."
    cp -r "${NUMBA_SEED}/." "${NUMBA_DIR}/"
fi
echo "[init] Numba cache: $(ls "$NUMBA_DIR" 2>/dev/null | wc -l) bestanden"

echo "[init] Database controleren..."
cd "${PROJECT_DIR}"
python3 -c "
import sys; sys.path.insert(0, '.')
from app import initialize_database
initialize_database()
print('[init] Database OK')
"

echo "[init] Redis verbinding testen..."
REDIS_HOST="${YASAFLASKIFIED_REDIS_HOST:-redis}"
REDIS_PORT="${YASAFLASKIFIED_REDIS_PORT:-6379}"
for i in $(seq 1 10); do
    if python3 -c "
from redis import Redis
r = Redis(host='${REDIS_HOST}', port=${REDIS_PORT})
r.ping()
print('[init] Redis OK')
" 2>/dev/null; then
        break
    fi
    echo "[init] Wachten op Redis... ($i/10)"
    sleep 2
done

echo "[init] Starten: $@"
exec "$@"
