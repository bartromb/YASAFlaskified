# YASAFlaskified

**An open-source web platform for automated polysomnography (PSG) analysis.**

[![License: BSD-3](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.8.11-green.svg)](CHANGES.md)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](requirements.txt)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](docker-compose.yml)

YASAFlaskified builds on [YASA](https://github.com/raphaelvallat/yasa) (**Y**et **A**nother **S**pindle **A**lgorithm), the outstanding open-source sleep analysis library created by [Raphaël Vallat](https://raphaelvallat.com) (UC Berkeley) together with Matthew P. Walker. YASA's LightGBM sleep staging model — trained on thousands of polysomnographic recordings and validated in *eLife* (2021) — provides the automated hypnogram that underpins every analysis in this platform.

YASAFlaskified extends YASA into a complete clinical platform: AASM 2.6-compliant respiratory event scoring, arousal detection, PLM analysis, and automated multilingual reporting — all in a Docker-deployed web application accessible from any browser.

**Live instance:** [slaapkliniek.be](https://slaapkliniek.be) or [sleepai.be](https://sleepai.be) — researchers may request a free account and upload anonymized EDF recordings.

> **Companion library:** Core respiratory scoring algorithms are available as a standalone Python library: [psgscoring](https://github.com/bartromb/psgscoring)

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Clinical Pipeline](#clinical-pipeline)
- [Scoring Algorithms](#scoring-algorithms)
- [Over-counting Corrections (v0.8.10)](#over-counting-corrections-v0810)
- [Signal Processing Improvements (v0.8.11)](#signal-processing-improvements-v0811)
- [Multi-site Access Control](#multi-site-access-control)
- [Report Generation](#report-generation)
- [Configuration](#configuration)
- [Development](#development)
- [Citation](#citation)
- [License](#license)

---

## Features

### Clinical Analysis
- **AI sleep staging** via YASA LightGBM (~85% epoch agreement with RPSGT)
- **AASM 2.6 respiratory scoring** — apneas, hypopneas (Rule 1A + 1B), RERAs
- **Apnea type classification** — obstructive / central / mixed with confidence scores
- **Two-phase arousal detection** with spindle exclusion and K-complex filter (v0.8.11)
- **PLM scoring** per AASM 2.6 + WASM criteria
- **SpO₂ analysis** — ODI 3%/4%, T90, CT85, nadir distribution
- **Cheyne-Stokes detection** via autocorrelation
- **Snoring index** and position-dependent AHI breakdown
- **Signal quality assessment** per channel with artifact epoch flagging

### Scoring Quality
- **Five systematic over-counting corrections** (v0.8.10):
  post-apnoea baseline exclusion, SpO₂ cross-contamination filtering,
  Cheyne-Stokes flagging, confidence stratification, artefact-flank masking
- **Threshold sensitivity table** — OAHI at confidence ≥0.85 / ≥0.60 / ≥0.40 / all
- **Phase-angle effort classification** via Hilbert transform (v0.8.11)
- **Patient-specific baseline anchoring** — mouth-breathing detection (v0.8.11)
- **CVR arousal confidence boost** — bradycardia/tachycardia coupling (v0.8.11)

### Platform
- **Interactive EDF browser** — channel-group filters, event overlay, multi-epoch zoom
- **Manual scoring editor** — epoch-by-epoch review and correction
- **Automated reports** — PDF (portrait A4), PSG report, Excel, EDF+ annotations, FHIR R4
- **Multilingual** — Dutch, French, English, German (369 translation keys)
- **Multi-site** — data isolation per clinical centre, role-based access
- **8 parallel workers** — concurrent analysis on multi-core hardware
- **Docker Compose** deployment — reproducible, single-command install

---

## Quick Start

### Prerequisites
- Ubuntu 22.04 / 24.04 (or any Docker-capable Linux)
- Docker + Docker Compose v2
- 4+ CPU cores, 8+ GB RAM recommended

### One-command deploy

```bash
curl -sSL https://raw.githubusercontent.com/bartromb/YASAFlaskified/main/deploy.sh \
  | sudo YASA_USER=$(whoami) bash
```

### Manual deploy

```bash
git clone https://github.com/bartromb/YASAFlaskified.git
cd YASAFlaskified
cp config.json.example config.json
# Edit config.json: set SECRET_KEY, ADMIN_PASSWORD, site name
docker compose build --no-cache
docker compose up -d
```

The app is now running at `http://localhost:8071`.

### Upgrade from previous version

```bash
scp YASAFlaskified_0_8_11.zip root@yourserver:/tmp/
ssh root@yourserver << 'EOF'
  cd /tmp && unzip -o YASAFlaskified_0_8_11.zip
  rsync -av --exclude='.env' --exclude='instance/' \
    --exclude='uploads/' --exclude='processed/' \
    --exclude='logs/' --exclude='config.json' \
    YASAFlaskified_0.8.11/ /data/slaapkliniek/
  cd /data/slaapkliniek
  docker compose build --no-cache
  docker compose down --remove-orphans && docker compose up -d
EOF
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (HTTPS)                   │
└──────────────────────┬──────────────────────────────┘
                       │ nginx reverse proxy
┌──────────────────────▼──────────────────────────────┐
│           Flask / Gunicorn  (kliniek_app)            │
│           SQLite · Flask-Login · Flask-Limiter       │
└──────────────────────┬──────────────────────────────┘
                       │ RQ jobs
┌──────────────────────▼──────────────────────────────┐
│        Redis Queue  (kliniek_redis)                  │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬───────┘
   │      │      │      │      │      │      │
  W1     W2     W3     W4     W5     W6     W7     W8
  (8 parallel RQ workers — kliniek_worker1..8)
   │
   ▼
┌──────────────────────────────────────────────────────┐
│  Analysis pipeline (psgscoring + YASA)               │
│  1. EDF load (MNE)          6. PLM                   │
│  2. Sleep staging (YASA)    7. Arousal + Rule 1B     │
│  3. Respiratory events      8. Rule 1B reinstatement │
│  4. SpO₂                    9. Cheyne-Stokes         │
│  5. Snore / position        + Anchor baseline (v0.8.11)│
└──────────────────────────────────────────────────────┘
```

**Hardware reference:** Hetzner AX52 — AMD Ryzen 9 5950X (16 cores), 128 GB RAM.
End-to-end analysis: 5–10 minutes per 8-hour PSG recording.

---

## Clinical Pipeline

| Step | Module | Description |
|------|--------|-------------|
| 1 | `psgscoring/pipeline.py` | EDF load, channel mapping, unit validation |
| 2 | `yasa_analysis.py` | Sleep staging (YASA LightGBM) + artifact epochs |
| 3 | `psgscoring/respiratory.py` | Apnoea + hypopnoea detection (AASM 2.6) |
| 3b | `psgscoring/signal.py` | Baseline anchoring — mouth-breathing detection (v0.8.11) |
| 4 | `psgscoring/spo2.py` | SpO₂ coupling, ODI, T90 |
| 5 | `psgscoring/ancillary.py` | Snoring, position, heart rate |
| 6 | `psgscoring/plm.py` | PLM detection (tibialis EMG) |
| 7 | `arousal_analysis.py` | Arousal detection + RERA + respiratory coupling |
| 8 | `psgscoring/respiratory.py` | Rule 1B reinstatement |
| 9 | `psgscoring/ancillary.py` | Cheyne-Stokes autocorrelation |
| Post | `psgscoring/pipeline.py` | CSR event flagging (Fix 3) |

---

## Scoring Algorithms

### Respiratory Scoring

**Signal processing:**
- Square-root linearisation of nasal pressure (Bernoulli correction, per AASM 2.6)
- Butterworth bandpass 0.05–3 Hz
- Hilbert envelope for instantaneous amplitude
- Dynamic 5-minute sliding baseline (95th percentile, 10-second steps)
- Stage-specific baseline blending (N2/N3/REM separate estimates)
- MMSD validation to distinguish apnoea from signal-dropout artefacts

**Apnoea detection:** thermistor, ≥90% reduction, ≥10 s, sleep epochs only

**Hypopnoea detection:** nasal pressure transducer (NPT), 30–90% reduction, ≥10 s,
Rule 1A (SpO₂ ≥3% drop) or Rule 1B (EEG arousal within 3 s)

**Apnoea type classification** — 7-rule decision tree (`psgscoring/classify.py`):

| Rule | Condition | Type |
|------|-----------|------|
| 0 | Phase angle ≥45° (Hilbert, v0.8.11) | Obstructive |
| 1 | Paradox correlation + raw variability | Obstructive |
| 2 | High raw variability, low envelope | Obstructive |
| 3 | First half absent, second half present | Mixed |
| 4 | Clear effort present | Obstructive |
| 5 | Truly flat — no effort signs | Central |
| 6 | Borderline default | Obstructive (low confidence) |

### Sleep Staging — powered by YASA

YASAFlaskified owes its staging capability entirely to the work of
[Raphaël Vallat](https://raphaelvallat.com) and Matthew P. Walker.
Their LightGBM model (published in *eLife* 2021, doi:[10.7554/eLife.70092](https://doi.org/10.7554/eLife.70092))
was trained on >3,000 PSG nights from four large public datasets
(MESA, SHHS, CFS, CHAT) and achieves ~85% epoch-level agreement with
certified RPSGT technologists — comparable to human inter-rater reliability.

Per-epoch features: delta/theta/alpha/sigma/beta band power, Hjorth parameters,
spectral entropy, temporal context (adjacent epoch stages). The MNE-Python
integration (Gramfort et al. 2013) handles EDF loading and channel preprocessing.

If you use YASAFlaskified for sleep staging, please cite Vallat & Walker (2021)
directly — their work is the scientific foundation of every hypnogram this platform produces.

---

## Over-counting Corrections (v0.8.10)

Five systematic bias mechanisms are identified and corrected. The official AASM
AHI/OAHI remain unchanged; corrected indices are supplementary.

| Fix | Mechanism | Correction |
|-----|-----------|------------|
| 1 | Post-apnoea hyperpnoea inflates baseline → false hypopnoeas | 30-s recovery mask excluded from baseline (sparse cumsum loop) |
| 2 | SpO₂ nadir of event N attributed to event N+1 at AHI >60/h | Cross-contamination check; suppress SpO₂ coupling if preceding window still active |
| 3 | Cheyne-Stokes decrescendo scored as hypopnoea | Retroactive CSR flagging via IEI matching (`csr_flagged` per event) |
| 4 | Borderline Rule-6 defaults at poor RIP quality | Separate counts: `n_low_conf_borderline` (0.40–0.59), `n_low_conf_noise` (<0.40) |
| 5 | Post-gap recovery ramp scored as event | 15-s post-gap exclusion mask after ≥10-s flatline gaps |

---

## Signal Processing Improvements (v0.8.11)

| Feature | Module | Description |
|---------|--------|-------------|
| Phase-angle classification | `classify.py` | Hilbert instantaneous phase difference thorax/abdomen; Rule 0: ≥45° → obstructive |
| K-complex exclusion | `arousal_analysis.py` | Bipolar waveform check (−75 µV + positive peak within 1 s); local min-duration raised to 5 s |
| CVR arousal boost | `arousal_analysis.py` | Bradycardia → tachycardia (≥10 bpm) around borderline arousals: confidence +0.10–0.20 |
| Baseline anchoring | `signal.py` | Event-free N2 median RMS as patient-specific anchor; `mouth_breathing_suspected` flag |
| LightGBM confidence | `classify.py` | Optional pre-trained model via `PSGSCORING_LGBM_MODEL` env var; 10-feature schema |

---

## Multi-site Access Control

Three roles:

| Role | Permissions |
|------|-------------|
| `admin` | All sites, user management, system config |
| `site_admin` | Own site only — manage users, view all studies |
| `user` | Upload, analyse, view own studies |

Data isolation: each site has its own upload/processed directory and database scope.
Patients of site A are never visible to site B users.

---

## Report Generation

| Format | Module | Contents |
|--------|--------|----------|
| PDF (A4 portrait) | `generate_pdf_report.py` | Hypnogram, respiratory indices, confidence table, threshold sensitivity, over-counting corrections |
| PSG Report | `generate_psg_report.py` | Portrait layout, per-stage breakdown, Cheyne-Stokes section |
| Excel | `generate_excel_report.py` | All indices, event list, raw summary |
| EDF+ | `generate_edfplus.py` | Annotations for each scored event |
| FHIR R4 | `fhir_export.py` | Observation + DiagnosticReport + CarePlan resources |

Languages: Dutch (NL), French (FR), English (EN), German (DE).

---

## Configuration

Copy `config.json.example` to `config.json`:

```json
{
  "SECRET_KEY": "change-me-to-random-64-chars",
  "ADMIN_PASSWORD": "strong-password",
  "SITE_NAME": "AZORG Slaapkliniek",
  "SITE_LANGUAGE": "nl",
  "MAX_UPLOAD_MB": 512,
  "RESULTS_PER_PAGE": 20
}
```

Environment variables (docker-compose.yml):
```yaml
PSGSCORING_LGBM_MODEL: ""   # Optional: path to LightGBM confidence model
MPLCONFIGDIR: /data/slaapkliniek/.mplconfig
NUMBA_CACHE_DIR: /data/slaapkliniek/.numba_cache
```

---

## Development

```bash
# Local dev (no Docker)
pip install -r requirements.txt
export FLASK_APP=myproject/app.py
export FLASK_ENV=development
flask run

# Run tests
cd myproject
python -m pytest psgscoring/tests/ -v

# Lint
flake8 myproject/psgscoring/ --max-line-length=100
```

### Project structure

```
YASAFlaskified/
├── myproject/
│   ├── psgscoring/         # Respiratory scoring library (also: github.com/bartromb/psgscoring)
│   │   ├── classify.py     # Apnoea type classification (7-rule + Hilbert phase)
│   │   ├── respiratory.py  # Apnoea/hypopnoea detection + 5 over-counting fixes
│   │   ├── signal.py       # Signal processing, dynamic baseline, anchoring
│   │   ├── pipeline.py     # Master analysis function
│   │   └── ...
│   ├── arousal_analysis.py # EEG arousal detection + K-complex + CVR
│   ├── generate_pdf_report.py
│   ├── generate_psg_report.py
│   └── ...
├── docker-compose.yml      # 8 workers + app + redis
├── Dockerfile
├── requirements.txt
├── deploy.sh               # One-command server install
└── config.json.example
```

---

## Version History

| Version | Milestone |
|---------|-----------|
| 0.8.0 | EDF browser, multi-site RBAC |
| 0.8.1 | Rolling arousal baseline, Rule 1B breath-cycle validation, FHIR R4 |
| 0.8.2–0.8.4 | Centralized i18n (NL/FR/EN/DE), redirect-loop fixes |
| 0.8.5 | Modular `psgscoring` package (10 submodules, 112 unit tests) |
| 0.8.6–0.8.9 | OAHI confidence stratification, threshold sensitivity table, AASM-conform OAHI |
| **0.8.10** | **Five over-counting corrections, O(n²)→O(n) event iteration** |
| **0.8.11** | **Hilbert phase-angle, K-complex exclusion, CVR arousal boost, baseline anchoring, LightGBM calibration** |

See [CHANGES.md](CHANGES.md) for full changelog.

---

## Citation

If you use YASAFlaskified or psgscoring in your research, please cite:

```bibtex
@software{rombaut2026yasaflaskified,
  author    = {Rombaut, Bart},
  title     = {{YASAFlaskified}: An open-source web platform for automated
               polysomnography analysis},
  year      = {2026},
  version   = {0.8.11},
  publisher = {GitHub},
  url       = {https://github.com/bartromb/YASAFlaskified}
}
```

**Please also cite YASA** — it is the scientific foundation of this platform's sleep staging:

```bibtex
@article{vallat2021,
  author  = {Vallat, Raphael and Walker, Matthew P.},
  title   = {An open-source, high-performance tool for automated sleep staging},
  journal = {eLife},
  year    = {2021},
  volume  = {10},
  pages   = {e70092},
  doi     = {10.7554/eLife.70092},
  url     = {https://github.com/raphaelvallat/yasa}
}
```

Also cite AASM 2.6 (Berry et al. 2020) for respiratory scoring rules,
and MNE-Python (Gramfort et al. 2013) for EDF signal processing.

---

## License

BSD 3-Clause License — Copyright (c) 2024–2026 Bart Rombaut / Slaapkliniek AZORG.
See [LICENSE](LICENSE) for full text.
