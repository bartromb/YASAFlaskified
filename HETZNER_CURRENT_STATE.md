# Hetzner Current State

**Last updated:** 2026-04-20
**Server:** dedodedodo.be / 65.108.230.243 (Ryzen 9 5950X, 128 GB RAM)
**Container:** kliniek_app (Docker Compose, 8 RQ workers + Redis + Gunicorn)

## Current versions in production

| Component | Version | Released | Notes |
|-----------|---------|----------|-------|
| YASAFlaskified | v0.8.41 | 2026-04-19 | pipeline channel_quality split integrated |
| psgscoring | v0.2.963 | 2026-04-20 | SQUEEZE2D fix on top of RIP pair quality gate |
| YASA (dependency) | 0.7.x | upstream | Vallat & Walker 2021 |

## Release history (current fix lineage)

### v0.2.962 — RIP pair quality gate (2026-04-19, 23:11 CET)

Introduced `compare_rip_pair()` in `psgscoring/signal_quality.py` to
detect asymmetric failures between thorax and abdomen RIP sensors.
Pipeline renamed output key from `signal_quality` (flatline/clipping
detection) to `channel_quality`, freeing `signal_quality` for the new
RIP pair check.

**Motivation:** Loos case (AZORG, April 2026) — thorax RIP sensor
dead, abdomen OK. Energy ratio 6862×. Without the gate, psgscoring
defaulted to obstructive classification, producing a misleading
OSAS diagnosis (AHI 56.6, CAI 3.8) instead of the correct CSAS
(CAI 45.1, 217 events reclassified).

**Commits:** `7c8fe0c` (fix) + `8d9f18c` (version bump).

### v0.2.963 — SQUEEZE2D fix (2026-04-20)

Fixes a silent 2D-shape handling bug in `assess_rip_channel()` that
rendered the v0.2.962 RIP pair gate ineffective in the real
deployment pipeline.

**Root cause:** MNE's `raw.get_data(picks=[ch])` returns shape
`(1, N)` even for single-channel picks. The `welch()` PSD produced a
2D output, breaking 1D boolean masking in breath-band energy
calculation downstream. The result was that `assess_rip_channel()`
silently returned invalid data, which `compare_rip_pair()` then
consumed without protest.

**Fix:** Defensive `np.asarray(signal, dtype=float).squeeze()` at top
of `assess_rip_channel()` with `ndim != 1` fallback to 'failed'
status for higher-dimensional input.

**Deployment path:**
1. Applied directly to Hetzner via base64 patch earlier on 2026-04-20
2. Committed to `bartromb/psgscoring` as v0.2.963
3. Uploaded to PyPI as v0.2.963
4. YASAFlaskified bundled psgscoring updated to match

**Validation:** 5 regression tests in `tests/test_signal_quality_2d.py`
covering 1D baseline, 2D MNE-shape input, higher-dim defensive
rejection, `compare_rip_pair` end-to-end, and Loos-like single-sensor
scenario. All passing.

## Clinical impact summary

The Loos case (AZORG PSG, April 2026) is the empirical validation
anchor for this fix lineage. The scenario is clinically significant:

- Patient presented with sleep-disordered breathing
- Thorax RIP sensor recorded essentially zero breath-band energy
  (MAD 0.0017, ratio 6862× below abdomen)
- Without signal quality gate: classified as severe OSAS (AHI 56.6)
- With gate (v0.2.963 live): correctly classified as CSAS (CAI 45.1)
- Dashboard now shows yellow 'Abdomen-only' Sig badge for this case

The fix addresses a patient-safety-relevant failure mode: a dead
sensor silently producing the wrong diagnosis category, which would
route the patient to inappropriate therapy (CPAP instead of ASV or
other central-apnea-appropriate treatment).

## Infrastructure

| Item | Value |
|------|-------|
| SSH | `ssh root@dedodedodo.be` |
| Project root | `/data/slaapkliniek/` |
| App directory | `/data/slaapkliniek/myproject/` |
| Docker Compose | `/data/slaapkliniek/docker-compose.yml` |
| Container name | `kliniek_app` |
| Web endpoint | https://slaapkliniek.be |
| Nginx Proxy Manager | https://panel.dedodedodo.be |

## Deployment verification

To verify the current live state matches this document:

```bash
ssh root@dedodedodo.be "docker exec kliniek_app python3 -c '
from psgscoring import __version__ as psg_ver
from version import __version__ as yas_ver
print(f\"psgscoring: {psg_ver}\")
print(f\"YASAFlaskified: {yas_ver}\")
from psgscoring.signal_quality import compare_rip_pair, assess_rip_channel
import inspect
src = inspect.getsource(assess_rip_channel)
assert \"SQUEEZE2D MARKER\" in src, \"SQUEEZE2D fix missing\"
print(\"SQUEEZE2D fix: present\")
'"
```

Expected output:

```
psgscoring: 0.2.963
YASAFlaskified: 0.8.41
SQUEEZE2D fix: present
```

## Previous state documents (superseded)

Any earlier `HETZNER_CURRENT_STATE.md` referencing the SQUEEZE2D fix
as a pending change, or describing the fix as a separate code path
outside v0.2.962/v0.2.963, is superseded by this document.

---

*This document is maintained alongside `CHANGELOG.md` in the
psgscoring repository and duplicated in YASAFlaskified for
operational visibility.*
