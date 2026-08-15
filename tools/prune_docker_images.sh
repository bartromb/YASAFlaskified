#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# prune_docker_images.sh — keep the Docker image store from filling the disk
# ═══════════════════════════════════════════════════════════════
#
# WHY THIS EXISTS
#
# DEPLOY_RUNBOOK.md §2 step 6 says to remove the old image once the new one is
# healthy. In practice that step is skipped, because the deploy is already
# working by the time you get there and nothing complains. On 2026-08-15 the
# test VM had 27 `yasaflaskified` images of ~1.9 GB plus 11.7 GB of build
# cache and had reached 100% disk with 0 bytes free; production was on the
# same path with 50 images (60 GB).
#
# The failure does NOT look like a full disk. Redis cannot write its RDB
# snapshot, so `stop-writes-on-bgsave-error` makes it refuse every write;
# flask-limiter writes to Redis on every request, so the health check fails and
# `docker compose up -d` reports only:
#
#     dependency failed to start: container kliniek_app is unhealthy
#
# The stack trace points at flask_limiter and redis.exceptions.ResponseError.
# Nothing points at the disk. That is why this runs on a timer instead of
# relying on someone remembering step 6.
#
# WHAT IT WILL NOT DO
#
#   * It never removes an image that a container is using — running OR stopped.
#   * It never touches volumes. `docker system prune --volumes` would delete
#     the Redis volume and any named volume holding data; this script has no
#     code path that can do that, deliberately.
#   * It never removes the newest KEEP images, so a rollback target always
#     survives alongside the running one.
#
# USAGE
#
#   sudo bash prune_docker_images.sh                # prune, using defaults
#   sudo bash prune_docker_images.sh --dry-run      # show what it would do
#   KEEP=3 sudo bash prune_docker_images.sh         # keep 3 versions
#   IMAGE=other CACHE_AGE=72h bash prune_docker_images.sh
#
# Exit status is 0 even when there is nothing to remove — this is a cron job,
# and a non-zero exit on "already clean" would mail the operator every night.
# ═══════════════════════════════════════════════════════════════

set -uo pipefail

IMAGE="${IMAGE:-yasaflaskified}"
KEEP="${KEEP:-2}"                 # running version + one rollback target
CACHE_AGE="${CACHE_AGE:-168h}"    # keep a week of build cache; it speeds up deploys
LOG="${LOG:-/var/log/prune_docker_images.log}"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# Decide once whether we can log, rather than per line. `echo >> file
# 2>/dev/null` does NOT silence this: the shell reports the failed redirection
# itself, before the command runs, so the suppression never applies and every
# line prints a "Permission denied" next to it. Test the file once instead.
if [ "$DRY_RUN" -eq 0 ] && ! { : >> "$LOG"; } 2>/dev/null; then
    LOG="${TMPDIR:-/tmp}/prune_docker_images.log"
    { : >> "$LOG"; } 2>/dev/null || LOG=""
fi

say() {
    local line
    line="$(date '+%F %T')  $*"
    echo "$line"
    if [ "$DRY_RUN" -eq 0 ] && [ -n "$LOG" ]; then
        { printf '%s\n' "$line" >> "$LOG"; } 2>/dev/null || true
    fi
}

command -v docker >/dev/null 2>&1 || { say "docker not found, nothing to do"; exit 0; }

FREE_BEFORE="$(df -h --output=avail / | tail -1 | tr -d ' ')"
USED_PCT_BEFORE="$(df --output=pcent / | tail -1 | tr -d ' %')"

# ── Which images are spoken for? ──────────────────────────────
# -a includes stopped containers: a stopped container is a rollback that still
# needs its image. `docker rmi` would refuse anyway, but being explicit keeps
# the intent readable and the log honest about what was protected.
IN_USE="$(docker ps -a --format '{{.Image}}' 2>/dev/null | sort -u)"

# ── Which tags exist, newest first? ───────────────────────────
# sort -V orders 0.9.0 before 0.20.0; a plain lexical sort does not.
ALL_TAGS="$(docker images "$IMAGE" --format '{{.Tag}}' 2>/dev/null \
            | grep -v '^<none>$' | sort -Vr)"

if [ -z "$ALL_TAGS" ]; then
    say "no ${IMAGE} images present"
else
    KEEP_TAGS="$(echo "$ALL_TAGS" | head -n "$KEEP")"
    say "keeping newest ${KEEP}: $(echo "$KEEP_TAGS" | tr '\n' ' ')"

    REMOVED=0
    for tag in $ALL_TAGS; do
        echo "$KEEP_TAGS" | grep -qx "$tag" && continue
        if echo "$IN_USE" | grep -qx "${IMAGE}:${tag}"; then
            say "  keeping ${IMAGE}:${tag} — a container still references it"
            continue
        fi
        if [ "$DRY_RUN" -eq 1 ]; then
            say "  would remove ${IMAGE}:${tag}"
        elif docker rmi "${IMAGE}:${tag}" >/dev/null 2>&1; then
            say "  removed ${IMAGE}:${tag}"
        else
            # Almost always "image is in use by container" — not an error worth
            # failing a nightly job over.
            say "  could not remove ${IMAGE}:${tag} (in use?), left in place"
            continue
        fi
        REMOVED=$((REMOVED + 1))
    done
    say "${REMOVED} image(s) $([ "$DRY_RUN" -eq 1 ] && echo 'would be ' )removed"
fi

# ── Dangling layers and aged build cache ──────────────────────
# `image prune` without -a removes ONLY untagged leftovers, never a tagged
# image. `builder prune` with a `until` filter keeps recent cache so the next
# deploy does not rebuild from zero.
if [ "$DRY_RUN" -eq 1 ]; then
    say "would prune dangling images and build cache older than ${CACHE_AGE}"
else
    docker image prune -f >/dev/null 2>&1 || true
    docker builder prune -f --filter "until=${CACHE_AGE}" >/dev/null 2>&1 || true
    say "pruned dangling images and build cache older than ${CACHE_AGE}"
fi

FREE_AFTER="$(df -h --output=avail / | tail -1 | tr -d ' ')"
USED_PCT_AFTER="$(df --output=pcent / | tail -1 | tr -d ' %')"
say "disk: ${USED_PCT_BEFORE}% used (${FREE_BEFORE} free) -> ${USED_PCT_AFTER}% used (${FREE_AFTER} free)"

# ── Warn while there is still room to act ─────────────────────
if [ "${USED_PCT_AFTER:-0}" -ge 85 ] 2>/dev/null; then
    say "WARNING: root filesystem is ${USED_PCT_AFTER}% full after pruning."
    say "         Look beyond images: uploads/, processed/, and Docker volumes."
fi

exit 0
