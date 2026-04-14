# YASAFlaskified

**Open-source web platform for automated polysomnography analysis.**

AI-based sleep staging + AASM 2.6 respiratory scoring + multilingual clinical reports.

[![Live](https://img.shields.io/badge/live-slaapkliniek.be-blue)](https://slaapkliniek.be)
[![psgscoring](https://img.shields.io/pypi/v/psgscoring?label=psgscoring)](https://pypi.org/project/psgscoring/)
[![License](https://img.shields.io/badge/license-BSD--3-green)](LICENSE)

## Paper

> Rombaut B, Rombaut B, Rombaut C, Vallat R. **YASAFlaskified & psgscoring: An Open-Source Platform for Automated Polysomnography Analysis Using AI-Based Sleep Staging and AASM 2.6-Compliant Respiratory Scoring.** Manuscript in preparation (JCSM), 2026.

Technical supplement: **[psgscoring Technical Reference](https://github.com/bartromb/psgscoring/wiki/Technical-Reference)**

## What it does

Upload an anonymised EDF recording via browser → receive a complete PSG analysis within 5–10 minutes. No local Python, Docker, or GPU required.

**Try it:** [slaapkliniek.be](https://slaapkliniek.be) — request a free account via the corresponding author.

### Analysis pipeline (11 steps)

| Step | What | How |
|------|------|-----|
| 1 | Sleep staging | YASA LightGBM (Vallat & Walker, *eLife* 2021) |
| 2 | Respiratory scoring | psgscoring — AASM 2.6 with 12 bias corrections |
| 3 | Arousal detection | K-complex exclusion + CVR coupling |
| 4 | PLM scoring | AASM 2.6 + WASM criteria |
| 5 | SpO₂ analysis | ODI 3%/4%, baseline (P90), T90 |
| 6 | Hypoxic burden | Azarbarzin 2019 — per-event desaturation area (%·min/h) |
| 7 | Post-processing | CSR reclassification, mixed decomposition, CII |
| 8 | Signal quality | Per-channel grading (flat-line, clipping, disconnect) |
| 9 | OSAS severity score | Multi-dimensional O-S-A-S profile with modifiers |
| 10 | Clinical reports | PDF, Excel, EDF+, FHIR R4 — NL/FR/EN/DE |
| 11 | ECG-derived effort | TECG + spectral classifier for central/obstructive |

### Key features

- **Hypoxic burden** — per-event SpO₂ desaturation area with both percentile and ensemble-averaged baseline methods (Azarbarzin et al., Eur Heart J 2019)
- **OSAS severity profile** — O(xygen)-S(leep)-A(pnea)-S(ymptoms) score (0–12) with -p/-r/-c modifiers
- **AHI confidence interval** — every study scored at three stringency levels with robustness grade (A/B/C)
- **12 bias corrections** — systematic over- and under-counting correction with per-fix event counters
- **Configurable scoring profiles** — strict / standard / sensitive
- **PDF report with Medatec parity** — position×stage cross-table, snoring cross-table, stage latencies, saturation bands, ESS input, conclusion section
- **Interactive EDF browser** — event overlay with epoch navigation
- **Multi-site access control** — data isolation per clinical centre

## Validation

| Dataset | n | Key result | Status |
|---------|---|-----------|--------|
| PSG-IPA (PhysioNet) | 5 rec, 60 sessions | Bias +1.6/h, r=0.990 | Published |
| iSLEEPS (stroke) | 96 patients | MAE 3.3/h (normal/mild) | Complete |
| MESA (NSRR) | ~2,056 | DUA pending | Planned |
| AZORG (prospective) | ≥50 | Bland-Altman, κ | Protocol v6.2 EC-ready |

## Self-hosting

```bash
git clone https://github.com/bartromb/YASAFlaskified.git
cd YASAFlaskified
cp .env.example .env   # configure SECRET_KEY, database path
docker compose up -d
```

Requirements: Docker, 4+ GB RAM. The platform runs on CPU only (Hetzner Ryzen 9 5950X, 128 GB RAM in production).

## Stack

Python 3.11 · Flask/Gunicorn · Redis 7 + RQ · MNE-Python · YASA 0.7 · psgscoring v0.2.94 · ReportLab · Docker Compose

## Standalone library

The respiratory scoring algorithms are available as a standalone Python library:

```bash
pip install psgscoring
```

See [github.com/bartromb/psgscoring](https://github.com/bartromb/psgscoring) for documentation and the [Technical Reference](https://github.com/bartromb/psgscoring/wiki/Technical-Reference) for signal-processing details.

## Citation

```bibtex
@article{rombaut2026yasaflaskified,
  title     = {{YASAFlaskified} \& psgscoring: An Open-Source Platform for
               Automated Polysomnography Analysis Using {AI}-Based Sleep
               Staging and {AASM} 2.6-Compliant Respiratory Scoring},
  author    = {Rombaut, Bart and Rombaut, Briek and Rombaut, Cedric
               and Vallat, Rapha{\"e}l},
  year      = {2026},
  note      = {Manuscript in preparation}
}
```

## Disclaimer

**YASAFlaskified and psgscoring are research software — not medical devices.** Not CE-marked (MDR 2017/745) or FDA-cleared. All reports include an explicit disclaimer and require physician verification before clinical action. See **[DISCLAIMER.md](DISCLAIMER.md)** for the full text.

## License

BSD-3-Clause. See [LICENSE](LICENSE).

---

*Developed at Slaapkliniek AZORG, Aalst, Belgium.*
*Contact: bart.rombaut@azorg.be*
