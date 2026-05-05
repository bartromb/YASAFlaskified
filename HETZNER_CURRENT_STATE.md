# Hetzner Current State

**Last updated:** 2026-05-01
**Server:** dedodedodo.be / 65.108.230.243 (Ryzen 9 5950X, 128 GB RAM)
**Container set:** `kliniek_app` (Flask/Gunicorn) + `kliniek_worker[1-8]` (RQ workers) + `kliniek_redis` + host `pneumo-web` (Nginx)
**Public endpoint:** https://slaapkliniek.be
**Project root on host:** `/data/slaapkliniek/` (file-copy deployment, not a git checkout)

## Current versions in production

| Component | Version | Source |
|---|---|---|
| YASAFlaskified | **v0.9.6** | `version.py` + `APP_VERSION` in `.env` both updated; Docker image tagged `yasaflaskified:0.9.6` |
| psgscoring | **v0.6.0** | Installed from PyPI via `requirements.txt` (`psgscoring[ml]==0.6.0` — `[ml]` extra installs `lightgbm` for the v0.6 candidate-classifier on `mesa_shhs`); previously bundled under `myproject/psgscoring/`, removed in v0.9.2 |
| Python | 3.11 | `python:3.11-slim` base image |
| YASA | 0.7.x | Vallat & Walker 2021 (transitive dep of psgscoring) |
| Redis | 7-alpine | Queue backend |

## Architecture summary

- 8 RQ workers + 1 Gunicorn app, all on the same Docker network
- Host Nginx terminates TLS (Let's Encrypt) and reverse-proxies to the
  app on `127.0.0.1:8071`
- Persistent volumes on the host: `/data/slaapkliniek/{uploads,processed,logs,instance}`
- Secrets in `/data/slaapkliniek/.env` (never committed)

## Deployment verification

To confirm the live state matches this document:

```bash
ssh root@dedodedodo.be 'docker exec kliniek_app python3 -c "
from version import __version__, PSGSCORING_VERSION
import psgscoring
print(f\"YASAFlaskified: {__version__}\")
print(f\"PSGSCORING_VERSION constant: {PSGSCORING_VERSION}\")
print(f\"psgscoring runtime: {psgscoring.__version__}\")
print(f\"psgscoring source: {psgscoring.__file__}\")
"'
```

Expected output (as of 2026-05-05):

```
YASAFlaskified: 0.9.5
PSGSCORING_VERSION constant: 0.6.0
psgscoring runtime: 0.6.0
psgscoring source: /usr/local/lib/python3.11/site-packages/psgscoring/__init__.py
```

The `site-packages` path confirms the de-vendor: psgscoring is no longer
loaded from a bundled `myproject/psgscoring/` copy.

## Update procedure

Standard update from a clean local checkout of `bartromb/YASAFlaskified`:

```bash
# 1. (Optional) Backup the current state — excludes data dirs
ssh root@dedodedodo.be 'cd /data && tar \
  --exclude="slaapkliniek/uploads" \
  --exclude="slaapkliniek/processed" \
  --exclude="slaapkliniek/logs" \
  --exclude="slaapkliniek/instance" \
  -czf slaapkliniek.bak.$(date +%Y%m%d).tgz slaapkliniek/'

# 2. Rsync source (preserves .env, instance/, uploads/, processed/, logs/)
rsync -avz \
  --exclude='.git/' --exclude='.venv/' --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='.pytest_cache/' --exclude='.ruff_cache/' \
  --exclude='/uploads/' --exclude='/processed/' --exclude='/logs/' \
  --exclude='/instance/' --exclude='.env' \
  --exclude='*.bak*' --exclude='*.pre_*' --exclude='*.OLD*' \
  ./ root@dedodedodo.be:/data/slaapkliniek/

# 3. (If applicable) Bump APP_VERSION in /data/slaapkliniek/.env so the
#    Docker image gets tagged with the new version
ssh root@dedodedodo.be 'sed -i "s/^APP_VERSION=.*/APP_VERSION=0.9.6/" /data/slaapkliniek/.env'

# 4. Build and recreate
ssh root@dedodedodo.be 'cd /data/slaapkliniek && docker compose build && docker compose up -d'
```

Recreating all containers takes ~30-60 s; deploy when the RQ queue is
empty to avoid killing in-flight analyses:

```bash
ssh root@dedodedodo.be 'docker exec kliniek_app python3 -c "
import redis
from rq import Queue
r = redis.Redis(host=\"redis\", port=6379)
q = Queue(\"default\", connection=r)
print(f\"Queued: {len(q)}, Started: {q.started_job_registry.count}\")
"'
```

## Recent migration history

### 2026-05-01 — v0.9.1 → v0.9.3 (de-vendor + paper-faithful validation)

- **De-vendored psgscoring** from `myproject/psgscoring/` to PyPI
  (`psgscoring==0.4.3`, was a manually-patched 0.4.2 bundled copy)
- **psgscoring v0.4.3** ships the paper-faithful `validate_psgipa.py`
  rewrite (single-source-of-truth scorer-1 file from `Resp_events/`,
  no cross-subtree `meas_date` alignment) and a regression test
  guarding paper v31 metrics
- **Three real bugs fixed** in `myproject/`:
  - `generate_psg_report.py` — undefined `site` and `pneumo` (should be
    `institution` and `pneumo_results`); would crash for affected
    code paths
  - `generate_pdf_report.py` — loop variable `t` shadowed the imported
    translation function `t` in `_sev` and `_sev_clr`, silently
    breaking translations in those branches
- **CI restored to green** on `main` (had been red since 2026-04-12 due
  to ruff failures on the bundled psgscoring code which is no longer
  in the repo)
- **Backup tarball:** `/data/slaapkliniek.bak.20260501.tgz` (35 MB)

### Earlier (pre-2026-05-01) fix lineage

The Loos case (AZORG, April 2026) — a clinically significant
single-RIP-sensor failure that defaulted to misleading severe-OSAS
classification — drove a series of psgscoring fixes that culminated
in v0.2.963: `compare_rip_pair()` for asymmetric RIP failure
detection plus the `assess_rip_channel()` SQUEEZE2D defensive
1D-coercion. Both fixes are present in the current production
psgscoring install (carried forward through every release;
currently v0.6.0 in production). See the psgscoring `CHANGELOG.md`
for the full per-version detail.

## Outstanding follow-ups

1. **`requirements.txt` and `version.py` may drift again** if the next
   psgscoring release ships without updating the YASAFlaskified pin
   simultaneously. Keep the two in lockstep; the `test_psgscoring_from_pypi`
   smoke test catches divergence at the `(major, minor)` level.

2. **OIDC trusted publisher** for psgscoring on PyPI was set up
   2026-05-01 (one-time configuration); GitHub Releases on the
   psgscoring repo now auto-publish to PyPI without manual `twine`.

## Resolved follow-ups (historical)

- **`APP_VERSION` stale at `0.8.39` in `/data/slaapkliniek/.env`** —
  resolved 2026-05-03 onward; each release now bumps APP_VERSION as
  part of the deploy procedure (see step 3 above).
