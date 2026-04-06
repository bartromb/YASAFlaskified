# YASAFlaskified

**An open-source web platform for automated polysomnography (PSG) analysis.**

[![License: BSD-3](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.8.31-green.svg)](CHANGES.md)
[![psgscoring](https://img.shields.io/badge/psgscoring-v0.2.5-green.svg)](https://github.com/bartromb/psgscoring)
[![Tests](https://img.shields.io/badge/tests-47%20passed-brightgreen.svg)](myproject/psgscoring/tests/)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](requirements.txt)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](docker-compose.yml)
[![AASM](https://img.shields.io/badge/AASM-2.6-orange.svg)](https://aasm.org)
[![i18n](https://img.shields.io/badge/i18n-NL%20%7C%20FR%20%7C%20EN%20%7C%20DE-purple.svg)](myproject/i18n.py)

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
- **Multilingual** — Dutch, French, English, German — 619 translation keys
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
scp YASAFlaskified_v0_8_31.zip user@yourserver:/tmp/ && \
ssh -t user@yourserver "sudo bash -c '
  cd /tmp && rm -rf yasafix && unzip -o YASAFlaskified_v0_8_31.zip -d yasafix &&
  rsync -av --no-group --no-owner \
    --exclude=.env --exclude=instance/ --exclude=uploads/ \
    --exclude=processed/ --exclude=logs/ --exclude=users.db \
    --exclude=__pycache__/ \
    /tmp/yasafix/myproject/ /data/yasaflaskified/myproject/ &&
  cp /tmp/yasafix/CHANGES.md /tmp/yasafix/Dockerfile \
     /tmp/yasafix/docker-compose.yml /tmp/yasafix/README.md \
     /tmp/yasafix/DISCLAIMER.md /tmp/yasafix/ROADMAP.md \
     /data/yasaflaskified/ &&
  cd /data/yasaflaskified && docker compose build --no-cache &&
  docker compose down && docker compose up -d &&
  rm -rf /tmp/yasafix /tmp/YASAFlaskified_v0_8_31.zip'"
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

**PDF highlights (v0.8.31):**
- Executive summary: AHI (large font, severity-colored), OAHI, CAI, SpO2, arousal index, PLMI
- Sleep stage transition matrix (5×5)
- HR/ECG section with bradycardia/tachycardia detection
- Red warning banner for poor signal quality or low AI confidence
- Section 8e: epoch signal examples with stacked pneumo channels
- SpO2 with mean, baseline (P90), nadir, T90, ODI 3%/4%
- Scoring profile comparison table with OAHI per profile
- Over-counting correction transparency table (6 fixes)
- Compact layout with 40–60% reduced spacing

Languages: Dutch (NL), French (FR), English (EN), German (DE).

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
  "SITE_NAME": "Your Sleep Clinic",
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
│   ├── i18n.py                  # 619 keys (NL/FR/EN/DE)
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
| **0.8.31** | **PDF fixes (SpO2 subscript, transition matrix, signal quality), 18 algorithm references in README, 619 i18n keys** |
| **0.8.30** | **Clinical PDF layout: executive summary, stage transition matrix, HR/ECG section, spacing reduction** |
| **0.8.29** | **47 tests (regression + Hypothesis property-based), flattening index wired to classification** |
| **0.8.28** | **Central/mixed apnea under-classification fix: Rule 5/5a/5b/3/6 relaxed for cardiac pulsation** |
| **0.8.27** | **Complete PDF multilingual (NL/FR/EN/DE), breath snap off by default, OAHI per scoring profile** |
| **0.8.23** | **ECG-derived effort (TECG Berry 2019), spectral effort classifier, central apnea reclassification, psgscoring v0.2.5** |
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
  version   = {0.8.31},
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

## References

Algorithms and methods used in YASAFlaskified and psgscoring:

### Sleep staging
- **Vallat R, Walker MP.** An open-source, high-performance tool for automated sleep staging. *eLife*. 2021;10:e70092. [doi:10.7554/eLife.70092](https://doi.org/10.7554/eLife.70092) — *YASA LightGBM staging model*
- **Perslev M et al.** U-Sleep: resilient high-frequency sleep staging. *npj Digital Medicine*. 2021;4:72. [doi:10.1038/s41746-021-00440-5](https://doi.org/10.1038/s41746-021-00440-5) — *Alternative deep learning staging (U-Sleep stub)*

### Respiratory scoring
- **Berry RB et al.** The AASM Manual for the Scoring of Sleep and Associated Events, Version 2.6. AASM, 2020. — *Scoring rules (Rule 1A, 1B, apnea/hypopnea/RERA definitions)*
- **Thurnheer R, Xie X, Bloch KE.** Accuracy of nasal cannula pressure recordings. *Am J Respir Crit Care Med*. 2001;164(10):1914–1919. [doi:10.1164/ajrccm.164.10.2010113](https://doi.org/10.1164/ajrccm.164.10.2010113) — *Nasal pressure square-root linearisation (Bernoulli)*
- **Montserrat JM et al.** Evaluation of nasal prongs for estimating nasal flow. *Am J Respir Crit Care Med*. 1997;155(1):211–215. [doi:10.1164/ajrccm.155.1.9001310](https://doi.org/10.1164/ajrccm.155.1.9001310) — *Nasal pressure linearisation validation*
- **Lee H et al.** Detection of apneic events from single-channel nasal airflow using 2nd derivative method. *Physiol Meas*. 2008;29:N37–N45. [doi:10.1088/0967-3334/29/5/N01](https://doi.org/10.1088/0967-3334/29/5/N01) — *MMSD validation (artefact vs. true apnea)*
- **Hosselet J et al.** Detection of flow limitation with a nasal cannula/pressure transducer system. *Am J Respir Crit Care Med*. 1998;157(5):1461–1467. [doi:10.1164/ajrccm.157.5.9708008](https://doi.org/10.1164/ajrccm.157.5.9708008) — *Flattening index for inspiratory flow limitation / RERA detection*

### Apnea type classification (obstructive / central / mixed)
- **Berry RB et al.** Use of a transformed ECG signal to detect respiratory effort during apnea. *J Clin Sleep Med*. 2019;15(11):1653–1660. [doi:10.5664/jcsm.7880](https://doi.org/10.5664/jcsm.7880) — *TECG method: QRS blanking + high-pass filter reveals inspiratory EMG bursts*
- **Berry RB et al.** Use of chest wall electromyography to detect respiratory effort during polysomnography. *J Clin Sleep Med*. 2016;12(9):1239–1244. [doi:10.5664/jcsm.6122](https://doi.org/10.5664/jcsm.6122) — *Cardiac pulsation artefact on effort bands*

### PLM scoring
- **Zucconi M et al.** WASM standards for recording and scoring periodic leg movements in sleep. *Sleep Med*. 2006;7(2):175–183. [doi:10.1016/j.sleep.2006.01.001](https://doi.org/10.1016/j.sleep.2006.01.001) — *PLM detection criteria*

### Sleep cycles
- **Feinberg I, Floyd TC.** Systematic trends across the night in human sleep cycles. *Psychophysiology*. 1979;16(3):283–291. — *NREM/REM cycle detection criteria*

### Over-counting / scoring variability
- **Malhotra A et al.** Performance of an automated polysomnography scoring system versus computer-assisted manual scoring. *Sleep*. 2013;36(4):573–582. [doi:10.5665/sleep.2548](https://doi.org/10.5665/sleep.2548) — *Baseline definition challenges in automated scoring*
- **Parekh A et al.** Ventilatory burden as a measure of OSA severity is predictive of cardiovascular and all-cause mortality. *Am J Respir Crit Care Med*. 2023;208(11):1216–1226. [doi:10.1164/rccm.202301-0109OC](https://doi.org/10.1164/rccm.202301-0109OC) — *Alternative event-free metrics (ventilatory burden)*
- **Rosenberg RS, Van Hout S.** The AASM inter-scorer reliability program. *J Clin Sleep Med*. 2013;9(1):81–87. [doi:10.5664/jcsm.2350](https://doi.org/10.5664/jcsm.2350) — *Inter-scorer variability benchmarks*
- **Ruehland WR et al.** The new AASM criteria for scoring hypopneas: impact on the AHI. *Sleep*. 2009;32(2):150–157. [doi:10.1093/sleep/32.2.150](https://doi.org/10.1093/sleep/32.2.150) — *Hypopnea definition impact on AHI*

### Prevalence
- **Peppard PE et al.** Increased prevalence of sleep-disordered breathing in adults. *Am J Epidemiol*. 2013;177(9):1006–1014. — *936 million adults with OSA worldwide*

### Software dependencies
- **Gramfort A et al.** MNE software for processing MEG and EEG data. *NeuroImage*. 2014;86:446–460. [doi:10.1016/j.neuroimage.2013.10.027](https://doi.org/10.1016/j.neuroimage.2013.10.027) — *MNE-Python (EDF I/O, signal processing)*
- **Ke G et al.** LightGBM: A highly efficient gradient boosting decision tree. *NeurIPS*. 2017;30:3146–3154. — *LightGBM classifier (YASA staging + optional confidence calibration)*
- **Vallat R.** Pingouin: statistics in Python. *JOSS*. 2018;3(31):1026. — *Statistical analysis (ICC, correlation)*

---

## License

BSD 3-Clause — Copyright (c) 2024–2026 Bart Rombaut / Slaapkliniek AZORG.
See [LICENSE](LICENSE).
