# Hetzner Current State

> For the step-by-step deploy procedure, see **`DEPLOY_RUNBOOK.md`**.

**Last updated:** 2026-07-25
**Server:** dedodedodo.be / 65.108.230.243 (Ryzen 9 5950X, 128 GB RAM)
**Container set:** `kliniek_app` (Flask/Gunicorn) + `kliniek_worker[1-8]` (RQ workers) + `kliniek_redis` + host `pneumo-web` (Nginx)
**Public endpoint:** https://slaapkliniek.be
**Project root on host:** `/data/slaapkliniek/` (file-copy deployment, not a git checkout)

## Current versions in production

| Component | Version | Source |
|---|---|---|
| YASAFlaskified | **v0.16.5** | `version.py` + `APP_VERSION` in `.env`; Docker image `yasaflaskified:0.16.5` (deployed 2026-07-27). v0.16.5 = **ventilatory-burden '≤25%' reference hidden for central-dominant studies (>50% central events / CSAS)** — the VB norm (AJRCCM 2023) is obstructive-OSA-derived and inherently high in central apnea/Cheyne-Stokes; the VB value stays shown (`_is_central_dominant` in generate_pdf_report + Jinja in results_extended). Also: absolute DISCLAIMER link in README (fix dead PyPI link). v0.16.4 = **ML `ml_help` tooltip de-detailed** (dropped 'paper v35 §3.6.1' + model version tag). v0.16.3 = **disclaimer 'Vallat & Walker' backslash fix + landing-page publication de-detailed (no journal/version/authors) + 'AASM v3.0' roadmap card removed (done)**. v0.16.2 = **landing page refreshed** (What's New → AASM v3, dual AHI, burdens, phenotypes, clinician report, arousal aetiology; badge/stack updated). v0.16.1 = **ventilatory burden made breath-based** (psgscoring 0.12.1; pin → 0.12.1): VB is now the proportion of breaths whose peak amplitude is <50% of the eupneic baseline (v0.16.0 used the envelope time-fraction → over-counted, e.g. 82.9%). Report display unchanged (bounded `%`, ref ≤25%). Earlier: v0.16.0 = **VB recalibration + saturation bands + arousal-aetiology fix** (psgscoring 0.12.0; pin → 0.12.0): ventilatory burden now the validated % of "small breaths" (airflow <50% eupneic, AJRCCM 2023) shown as bounded `%` with ref ≤25% (was implausible `%·min/h`); time-in-saturation-bands table now populated; respiratory+spontaneous arousal indices now sum to the arousal index. No AHI/OSAS-grade change. Earlier: v0.15.0 = **clinician-focused PDF report** (from psgscoring 0.11.0; pin → 0.11.0): auto-generated conclusion, dual AHI (Rule 1A vs 1B/CMS 4%), AASM AHI reference scale, page-1 phenotype line + descriptive "Aandachtspunten" box, arousal aetiology indices, ventilatory burden marked experimental. **Removed from the PDF:** signal-quality/confidence section + banners, and the "OSAS severity profile" (strict/std/sensitive comparison, AHI-robustness interval, OAHI 3-point sweep, O-S-A-S score table) — ESS kept. **Fix:** KPI syndrome/apnea-breakdown now read the canonical summary (were empty → generic "SAS"). No scoring-numerics change. Earlier: v0.14.0 = phenotypes + ventilatory burden in report; v0.13.0 = arousal & RERA moved to psgscoring + multi-derivation arousals by default |
| psgscoring | **v0.12.1** | Installed from PyPI via `requirements.txt` (`psgscoring[ml]==0.12.1` — `[ml]` extra installs `lightgbm`). 0.12.1 = **VB made breath-based** (proportion of breaths with peak <50% of eupneic baseline; `compute_ventilatory_burden(flow_norm, sf, breaths, hypno)`) — fixes the v0.12.0 envelope-time-fraction over-count. 0.12.0 = **VB recalibrated** to the validated % of "small breaths" (airflow <50% eupneic; `compute_ventilatory_burden(flow_norm, sf, hypno, threshold=0.5)`, `VB_NORMATIVE_MAX=25`), **saturation-band keys** added to SpO2 summary, **arousal-aetiology indices** now split `arousal_index` so resp+spont sum to it. **No AHI/OSAS-grade change** (golden byte-identical). 0.11.0 = output-additive **AASM v3 enrichments**: dual AHI (`summary["ahi_dual"]` — Rule 1A vs 1B/4%), Cheyne-Stokes density criterion G.1(b), arousal aetiology indices (respiratory/spontaneous/PLM per hour), `meta["hypopnea_criterion"]`, hypoventilation "not assessed" statement; apnea/hypopnea max-dur cap overridable via env (default unchanged). **No AHI/OSAS-grade change** (golden byte-identical). 0.10.0 = phenotype flags + ventilatory burden. Arousal mode: env `PSGSCORING_AROUSAL_DERIVATION=single\|multi` |
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
