# YASAFlaskified

**An open-source web platform for automated polysomnography (PSG) analysis.**

[![License: BSD-3](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.8.22-green.svg)](CHANGES.md)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](requirements.txt)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](docker-compose.yml)
[![AASM](https://img.shields.io/badge/AASM-2.6-orange.svg)](https://aasm.org)
[![i18n](https://img.shields.io/badge/i18n-NL%20%7C%20FR%20%7C%20EN-purple.svg)](myproject/i18n.py)

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
- [Over-counting Corrections](#over-counting-corrections)
- [Signal Processing Improvements](#signal-processing-improvements)
- [Report Generation](#report-generation)
- [Multi-site Access Control](#multi-site-access-control)
- [Configuration](#configuration)
- [Development](#development)
- [Version History](#version-history)
- [Citation](#citation)
- [License](#license)

---

## Features

### Clinical Analysis
- **AI sleep staging** via YASA LightGBM (~85% epoch agreement with RPSGT)
- **AASM 2.6 respiratory scoring** — apneas, hypopneas (Rule 1A + 1B), RERAs
- **Dual-sensor scoring** — apnea on thermistor, hypopnea on nasal pressure (AASM 2.6)
- **Apnea type classification** — obstructive / central / mixed via 7-rule decision tree with Hilbert phase-angle
- **Two-phase arousal detection** with spindle exclusion, K-complex filter, and CVR coupling
- **PLM scoring** per AASM 2.6 + WASM criteria
- **SpO₂ analysis** — ODI 3%/4%, baseline (P90), time below 90%, nadir distribution
- **Cheyne-Stokes detection** via autocorrelation
- **Snoring index** and position-dependent AHI breakdown (supine, left, right, prone, upright)
- **REM/NREM AHI** — stage-specific respiratory indices
- **Signal quality assessment** per channel with artifact epoch flagging and confidence review
- **Study type support** — diagnostic PSG, titration (CPAP/MRA), polygraphy (REI)

### Scoring Quality
- **Six systematic over-counting corrections** with transparency table in PDF: post-apnoea baseline exclusion, SpO₂ cross-contamination filtering, Cheyne-Stokes flagging, confidence stratification, artefact-flank masking, local baseline validation
- **Local baseline validation** (v0.8.22) — rejects false-positive hypopneas where flow reduction <20% vs. pre-event breathing
- **Maximum event duration** (v0.8.21) — hypopnea max 60s, apnea max 90s; splits at partial recovery point
- **Threshold sensitivity table** — OAHI at confidence ≥0.85 / ≥0.60 / ≥0.40 / all
- **Three scoring profiles** — strict (machine), standard (AASM 2.6), sensitive (RPSGT-like)
- **Phase-angle effort classification** via Hilbert transform
- **Patient-specific baseline anchoring** — mouth-breathing detection
- **CVR arousal confidence boost** — bradycardia/tachycardia coupling

### Platform
- **Interactive EDF browser** — channel-group filters, event overlay, multi-epoch zoom
- **Manual scoring editor** — epoch-by-epoch review, event add/delete/modify
- **Automated reports** — PDF (portrait A4) with epoch signal examples, Excel, EDF+ annotations, FHIR R4
- **Multilingual** — Dutch, French, English (449+ translation keys)
- **Multi-site** — data isolation per clinical centre, role-based access
- **EDF patient info** — auto-populate from EDF header (name, DOB, sex, equipment)
- **Signal quality warnings** — red banner in PDF when channels unusable or AI confidence low
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

### Upgrade

```bash
scp YASAFlaskified_v0_8_22.zip bart@yourserver:/tmp/ && \
ssh -t bart@yourserver "sudo bash -c '
  cd /tmp && rm -rf yasafix && unzip -o YASAFlaskified_v0_8_22.zip -d yasafix &&
  rsync -av --no-group --no-owner \
    --exclude=.env --exclude=instance/ --exclude=uploads/ \
    --exclude=processed/ --exclude=logs/ --exclude=users.db \
    --exclude=__pycache__/ \
    /tmp/yasafix/myproject/ /data/slaapkliniek/myproject/ &&
  cp /tmp/yasafix/CHANGES.md /tmp/yasafix/Dockerfile \
     /tmp/yasafix/docker-compose.yml /tmp/yasafix/README.md \
     /tmp/yasafix/DISCLAIMER.md /tmp/yasafix/ROADMAP.md \
     /data/slaapkliniek/ &&
  cd /data/slaapkliniek && docker compose build --no-cache &&
  docker compose down && docker compose up -d &&
  rm -rf /tmp/yasafix /tmp/YASAFlaskified_v0_8_22.zip'"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (HTTPS)                   │
└──────────────────────┬──────────────────────────────┘
                       │ Nginx Proxy Manager
┌──────────────────────▼──────────────────────────────┐
│           Flask / Gunicorn  (kliniek_app)            │
│           SQLite · Flask-Login · Flask-Limiter       │
└──────────────────────┬──────────────────────────────┘
                       │ RQ jobs
┌──────────────────────▼──────────────────────────────┐
│        Redis Queue  (kliniek_redis)                  │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬───────┘
   W1    W2    W3    W4    W5    W6    W7    W8
   (8 parallel RQ workers)
   │
   ▼
┌──────────────────────────────────────────────────────┐
│  Analysis pipeline (11 steps)                        │
│  1.  EDF load + channel mapping                      │
│  1b. Signal quality assessment                       │
│  1c. Baseline anchoring                              │
│  2.  Sleep staging (YASA LightGBM)                   │
│  3.  Respiratory events (apnea + hypopnea)           │
│  4.  SpO₂ coupling + ODI 3%/4%                       │
│  5.  Snore / position / heart rate                   │
│  6.  PLM detection                                   │
│  7.  Arousal detection + Rule 1B coupling             │
│  8.  Rule 1B reinstatement + RERA/RDI                │
│  9.  Cheyne-Stokes detection + CSR flagging           │
│  10. PDF + Excel + EDF+ report generation             │
└──────────────────────────────────────────────────────┘
```

**Hardware:** Hetzner AX52 — AMD Ryzen 9 5950X (16 cores), 128 GB ECC RAM, 2×3.84 TB NVMe (ZFS mirror).

---

## Clinical Pipeline

| Step | Module | Description |
|------|--------|-------------|
| 1 | `psgscoring/pipeline.py` | EDF load, channel mapping, unit validation |
| 1b | `psgscoring/signal_quality.py` | Per-channel quality: flat-line, clipping, disconnect, amplitude |
| 1c | `psgscoring/signal.py` | Baseline anchoring, mouth-breathing detection |
| 2 | `yasa_analysis.py` | Sleep staging + confidence review + sleep cycles (Feinberg & Floyd) |
| 3 | `psgscoring/respiratory.py` | Apnoea + hypopnoea detection, local baseline validation, max duration split |
| 4 | `psgscoring/spo2.py` | SpO₂ coupling, ODI 3%/4%, baseline (P90), time below thresholds |
| 5 | `psgscoring/ancillary.py` | Snoring, position, heart rate |
| 6 | `psgscoring/plm.py` | PLM detection (tibialis EMG) |
| 7 | `arousal_analysis.py` | Two-phase arousal detection + RERA + respiratory coupling |
| 8 | `psgscoring/respiratory.py` | Rule 1B reinstatement |
| 8b | `psgscoring/pipeline.py` | RERA index + RDI (FRI-RERA + flattening-RERA) |
| 9 | `psgscoring/ancillary.py` | Cheyne-Stokes detection + CSR event flagging |
| 10 | `generate_pdf_report.py` | PDF with epoch examples, Excel, EDF+ annotations |

---

## Scoring Algorithms

### Respiratory Scoring

**Signal processing:** square-root linearisation of nasal pressure (Thurnheer et al. 2001), Butterworth bandpass 0.05–3 Hz, Hilbert envelope, dynamic 5-minute sliding baseline (95th percentile), MMSD validation (Lee et al. 2008).

**Apnoea detection:** oronasal thermistor, ≥90% flow reduction, ≥10 s, max 90 s (split at recovery), sleep epochs only.

**Hypopnoea detection:** nasal pressure transducer, ≥30% reduction, ≥10 s, max 60 s (split at partial recovery), Rule 1A (SpO₂ ≥3% drop) or Rule 1B (arousal within 3 s). Local baseline validation (v0.8.22): rejects events with <20% reduction vs. pre-event breathing.

**Apnoea type classification** — 7-rule decision tree with Hilbert phase-angle, paradoxical thoraco-abdominal correlation, effort envelope ratio, and raw signal variability. Optional LightGBM confidence calibration.

**Scoring profiles:**

| Profile | Hypopnea | SpO₂ window | Smoothing | Peak detection | Max hyp. | Max apnea |
|---------|----------|-------------|-----------|----------------|----------|-----------|
| Strict | ≥30% | 30 s | None | Envelope only | 60 s | 90 s |
| Standard | ≥30% | 45 s | 3 s | Peak + envelope | 60 s | 90 s |
| Sensitive | ≥25% | 45 s | 5 s | Peak + envelope | 90 s | 120 s |

### Sleep Staging — powered by YASA

LightGBM model by Raphaël Vallat and Matthew P. Walker (eLife 2021, doi:[10.7554/eLife.70092](https://doi.org/10.7554/eLife.70092)), ~85% epoch-level agreement with certified RPSGT technologists.

### Sleep Cycles (v0.8.22)

Feinberg & Floyd criteria: minimum 15 min NREM required per cycle. REM consolidation with 2-min gap tolerance. Produces physiologically realistic 4–6 cycles.

---

## Over-counting Corrections

Six systematic bias mechanisms identified and corrected. Official AHI/OAHI unchanged; corrections are supplementary and displayed in the PDF.

| Fix | Mechanism | Correction |
|-----|-----------|------------|
| 1 | Post-apnoea hyperpnoea inflates baseline | 30-s recovery mask excluded from baseline |
| 2 | SpO₂ nadir of event N attributed to N+1 | Cross-contamination flag (informative) |
| 3 | Cheyne-Stokes decrescendo scored as hypopnoea | Retroactive CSR flagging via IEI matching |
| 4 | Borderline defaults at poor RIP quality | Separate noise (<0.40) and borderline (0.40–0.59) counts |
| 5 | Post-gap recovery ramp scored as event | 15-s exclusion mask after ≥10-s flatline gaps |
| **6** | **Inflated rolling baseline → false-positive hypopneas** | **Local baseline validation: <20% reduction vs. pre-event → rejected (v0.8.22)** |

---

## Signal Processing Improvements

| Feature | Version | Description |
|---------|---------|-------------|
| Phase-angle classification | v0.8.11 | Hilbert phase difference; ≥45° → obstructive |
| K-complex exclusion | v0.8.11 | Bipolar waveform check; 5 s min-duration |
| CVR arousal boost | v0.8.11 | Brady → tachycardia ≥10 bpm: confidence +0.10–0.20 |
| Baseline anchoring | v0.8.11 | Event-free N2 median RMS as patient-specific anchor |
| Signal quality assessment | v0.8.17 | Per-channel flat-line, clipping, disconnect, quality grade |
| Montage plausibility | v0.8.17 | Cross-correlation checks |
| Flattening-based RERA | v0.8.17 | Hosselet flattening index >0.30 + arousal |
| RERA/RDI index | v0.8.16 | RDI = AHI + RERA-index |
| Study type support | v0.8.19 | Diagnostic PSG / titration / polygraphy |
| EDF header auto-fill | v0.8.19 | Patient info from EDF header |
| **Max event duration + split** | **v0.8.21** | **Hyp. max 60s / apnea max 90s, split at recovery** |
| **Local baseline validation** | **v0.8.22** | **Rejects false-positive hypopneas** |

---

## Report Generation

| Format | Module | Contents |
|--------|--------|----------|
| PDF (A4) | `generate_pdf_report.py` | Full clinical report with epoch signal examples |
| Excel | `generate_excel_report.py` | All indices, event list, raw summary |
| EDF+ | `generate_edfplus.py` | Annotations for each scored event (pyedflib) |
| FHIR R4 | `fhir_export.py` | Observation + DiagnosticReport + CarePlan |

**PDF highlights (v0.8.22):**
- Red warning banner for poor signal quality or low AI confidence
- Section 8e: epoch signal examples with stacked pneumo channels
- SpO₂ with mean, baseline (P90), nadir, T90, ODI 3%/4%
- Spindle/slow wave tables per channel (not "—")
- Realistic 4–6 sleep cycles (Feinberg & Floyd)
- Over-counting correction transparency table (6 fixes)

Languages: Dutch (NL), French (FR), English (EN).

---

## Multi-site Access Control

| Role | Permissions |
|------|-------------|
| `admin` | All sites, user management, system config |
| `site_admin` | Own site — manage users, view all studies |
| `user` | Upload, analyse, view own studies |

---

## Configuration

Copy `config.json.example` to `config.json`:

```json
{
  "SECRET_KEY": "change-me-to-random-64-chars",
  "ADMIN_PASSWORD": "strong-password",
  "SITE_NAME": "AZORG Slaapkliniek",
  "SITE_LANGUAGE": "nl",
  "MAX_UPLOAD_MB": 512
}
```

---

## Development

```bash
pip install -r requirements.txt
export FLASK_APP=myproject/app.py
flask run

# Tests
cd myproject && python -m pytest psgscoring/tests/ -v
```

### Project structure

```
YASAFlaskified/
├── myproject/
│   ├── psgscoring/              # Respiratory scoring library
│   │   ├── pipeline.py          # 11-step analysis pipeline
│   │   ├── respiratory.py       # Apnea/hypopnea + 6 corrections
│   │   ├── classify.py          # 7-rule classification + Hilbert
│   │   ├── signal.py            # Signal processing, baseline
│   │   ├── spo2.py              # SpO₂, ODI 3%/4%
│   │   ├── signal_quality.py    # Per-channel quality
│   │   ├── constants.py         # AASM thresholds, scoring profiles
│   │   └── ...
│   ├── arousal_analysis.py      # Arousal + K-complex + CVR
│   ├── yasa_analysis.py         # Staging, cycles, spindles, SW
│   ├── generate_pdf_report.py   # PDF with epoch examples
│   ├── i18n.py                  # 449+ keys (NL/FR/EN)
│   ├── app.py                   # Flask (~2900 LOC)
│   └── templates/               # 22 Jinja2 templates
├── docker-compose.yml           # 8 workers + app + redis
├── Dockerfile
├── deploy.sh
└── CHANGES.md
```

---

## Version History

| Version | Milestone |
|---------|-----------|
| 0.8.0–0.8.4 | EDF browser, multi-site RBAC, centralized i18n |
| 0.8.5 | Modular `psgscoring` package |
| 0.8.6–0.8.9 | OAHI confidence stratification, sensitivity table |
| 0.8.10 | Five over-counting corrections |
| 0.8.11 | Hilbert phase-angle, K-complex, CVR, baseline anchoring |
| 0.8.12–0.8.15 | SpO₂ speedup, peak-based hypopnea, scoring profiles |
| 0.8.16 | RERA/RDI, REM/NREM AHI, positional AHI |
| 0.8.17 | Signal quality, flattening-RERA, montage checks |
| 0.8.19 | Study types, EDF header auto-fill, position legend |
| **0.8.22** | **ODI 3%/4%, Feinberg & Floyd cycles, REM consolidation, channel fix, quality banners, epoch examples, max duration split, local baseline validation** |

See [CHANGES.md](CHANGES.md) for full changelog.

---

## Citation

```bibtex
@software{rombaut2026yasaflaskified,
  author    = {Rombaut, Bart},
  title     = {{YASAFlaskified}: An open-source web platform for automated
               polysomnography analysis},
  year      = {2026},
  version   = {0.8.22},
  publisher = {GitHub},
  url       = {https://github.com/bartromb/YASAFlaskified}
}
```

**Please also cite YASA:**

```bibtex
@article{vallat2021,
  author  = {Vallat, Raphael and Walker, Matthew P.},
  title   = {An open-source, high-performance tool for automated sleep staging},
  journal = {eLife},
  year    = {2021},
  volume  = {10},
  pages   = {e70092},
  doi     = {10.7554/eLife.70092}
}
```

---

## Disclaimer

YASAFlaskified is **research software**, not a cleared medical device. It carries no CE mark, FDA clearance, or equivalent certification. All computed indices (AHI, OAHI, ODI, PLMI, RDI) are research-grade estimates that must be reviewed by a qualified clinician before any diagnostic or therapeutic decision. See [DISCLAIMER.md](DISCLAIMER.md) for full terms.

---

## License

BSD 3-Clause — Copyright (c) 2024–2026 Bart Rombaut / Slaapkliniek AZORG.
See [LICENSE](LICENSE).
