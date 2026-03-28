# Changelog — YASAFlaskified

All notable changes documented per [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.8.11]

### Added — Signal processing and scoring improvements

**Phase-angle effort classification (`psgscoring/classify.py`):**
- New Rule 0: Hilbert instantaneous phase difference between thorax and abdomen
- Phase angle ≥45° → obstructive with confidence 0.75–0.97
- Fires before the 6 legacy rules; largely eliminates Rule-6 borderline defaults
  when RIP signals are adequate
- Minimum 5 s event duration required for reliable Hilbert estimate

**K-complex morphological exclusion (`arousal_analysis.py`):**
- Bipolar waveform check on first 1 s of each NREM arousal candidate
- Negative peak <−75 µV followed by positive peak >30 µV → K-complex suspected
- Local minimum arousal duration raised from 3.0 s to 5.0 s for that candidate
- Prevents K-complex trailing alpha-rebound from being scored as arousal

**CVR arousal confidence boost (`arousal_analysis.py`):**
- `_detect_cvr_confidence_boost()`: bradycardia (≥5 bpm dip) + tachycardia
  (≥10 bpm peak within 15 s) around borderline arousals → confidence +0.10–0.20
- No-op when no ECG/pulse channel is available
- Field `cvr_boost` stored per arousal event

**Patient-specific baseline anchoring (`psgscoring/signal.py`):**
- `compute_anchor_baseline()`: event-free N2 epochs → median RMS as
  patient-specific golden-standard baseline
- `mouth_breathing_suspected: True` when current signal RMS <60% of anchor
- Result in `output["anchor_baseline"]` via pipeline
- Requires ≥6 stable N2 epochs; `anchor_reliable: False` otherwise

**LightGBM confidence calibration (`psgscoring/classify.py`):**
- Optional 10-feature model via `PSGSCORING_LGBM_MODEL` environment variable
- Features: effort_ratio, raw_var_ratio, paradox_correlation, half/quarter efforts,
  phase_angle_deg, duration_s, rule_index
- Transparent fallback to rule-based confidence when model unavailable
- Field `lgbm_confidence` stored per event when model active

### Changed
- `detect_arousals()` now accepts `hr_data` and `sf_hr` parameters
- `run_arousal_respiratory_analysis()` passes `hr_data` through to `detect_arousals`
- `classify_apnea_type()` returns `phase_angle_deg` in detail dict
- Pipeline Step 7 passes `hr_data` and `sf_hr` to arousal analysis

---

## [0.8.10]

### Added — Five systematic over-counting corrections

**Fix 1 — Post-apnoea hyperpnoea baseline exclusion:**
- `_build_postapnea_recovery_mask()`: 30-s recovery window after each apnoea
- `_recompute_baseline_with_recovery_excluded()`: sparse cumsum loop (only recomputes
  anchor points where recovery mask covers >5% of 5-min window)
- Eliminates artificial baseline inflation from compensatory hyperventilation

**Fix 2 — SpO₂ cross-contamination:**
- `_spo2_cross_contaminated()`: checks if preceding event's 30-s post-event window
  is still active at candidate onset
- Suppresses SpO₂ coupling for contaminated candidates → field `spo2_cross_contaminated`
- Particularly relevant at AHI >60/h (inter-event interval <60 s)

**Fix 3 — Cheyne-Stokes AHI inflation:**
- `_flag_csr_events()`: after CSR detection, retroactively marks events whose
  inter-event interval matches detected periodicity (±12 s, up to 3× periodicity)
- Fields: `csr_flagged` per event, `n_csr_flagged`, `ahi_csr_corrected` in summary
- Applied in `pipeline.py` after Step 9 (CSR detection)

**Fix 4 — Borderline default confidence stratification:**
- Separate counts: `n_low_conf_borderline` (0.40–0.59), `n_low_conf_noise` (<0.40)
- Alternative index: `ahi_excl_noise` (AHI excluding confidence <0.40 events)
- Threshold sensitivity table in report: OAHI at ≥0.85 / ≥0.60 / ≥0.40 / all

**Fix 5 — Artefact-flank exclusion:**
- `_detect_signal_gaps()`: flatline/frozen segments ≥10 s → 15-s post-gap exclusion mask
- Applied to both apnoea and hypopnoea sleep masks
- Field `n_gap_excluded` in detection result

### Performance optimisations
- Replaced O(n×k) `np.where(labeled == i)` loops with O(n) `scipy.ndimage.find_objects()`
  (benchmark: 820 s extrapolated → 0.8 s for 350,000 candidate regions)
- `_setup_hypop_channel()`: reuses apnoea-channel baseline when sf equal, skipping
  duplicate `compute_dynamic_baseline()` call (+3–8 s saved)
- `compute_stage_baseline()`: vectorised epoch collection via `np.repeat()` instead of
  Python `list.extend()` loop; accepts `dynamic_baseline` parameter to avoid third call
- `_pre_event_baseline()`: replaced per-event `np.percentile` over 120-s window
  with O(1) lookup into precomputed dynamic baseline array
- Total overhead of 5 corrections: <1 s on 8-hour PSG at 256 Hz

### Report additions
- New section "Over-counting correction (v0.8.10)" in PDF and PSG reports
- Per-fix impact table + disclaimer that official AASM indices unchanged

---

## [0.8.9]

### Added
- OAHI = all obstructive + hypopnoeas (AASM-conform); `oahi_conf60` supplementary
- Threshold sensitivity table in PDF report: OAHI at 0.85 / 0.60 / 0.40 / 0.00
- PSG report converted from landscape to portrait layout (matches PDF report)
- Confidence column per apnoea type in event table

### Changed
- Removed Cheyne-Stokes from section 9c → only in Conclusions via `conclusions.py`
- Removed orphan workers (kliniek_worker, worker9–worker16) via `--remove-orphans`

---

## [0.8.8]

### Added
- OAHI confidence stratification: `oahi_conf60` (events with confidence >0.60)
- `confidence_bands` in summary: `{"high": N, "moderate": N, "borderline": N, "low": N}`
- Confidence breakdown table in PDF and PSG reports

---

## [0.8.7]

### Added
- 8 parallel RQ worker containers (`worker1`–`worker8`) via YAML anchor in docker-compose.yml
- Worker pool calibrated for Ryzen 9 5950X (16 real cores: 8 workers + OS headroom)

### Changed
- Single sequential worker replaced by parallel pool
- Estimated RAM usage: ~16 GB of 128 GB (2 GB per worker)

---

## [0.8.6]

### Fixed
- `_hypno_img()` in `generate_pdf_report.py`: `lang` was a free variable → `NameError`
- `build_hypnogram_figure()` in `generate_psg_report.py`: called before `lang` defined
- Hardcoded "Tijd (min)" → `t("pdf_time_axis", lang)`

---

## [0.8.5]

### Added — Modular `psgscoring` package

- Monolithic `pneumo_analysis.py` (2,439 lines) split into 10 domain-specific submodules
- Strict one-directional dependency graph
- 112 unit tests across 6 test files (Python 3.9–3.12 CI matrix)
- Backward-compatible 81-line shim preserving all existing application imports
- Public API: 33 exported symbols in `psgscoring/__init__.py`

**Submodules:**

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `constants.py` | 76 | Thresholds, band limits |
| `utils.py` | 134 | Sleep masks, helpers |
| `signal.py` | 307 | Linearisation, baseline, MMSD |
| `breath.py` | 254 | Breath-by-breath segmentation, flattening index |
| `classify.py` | 228 | Apnoea type classification |
| `spo2.py` | 218 | SpO₂ coupling, ODI |
| `plm.py` | 271 | PLM detection |
| `ancillary.py` | 277 | HR, snore, position, CSR |
| `respiratory.py` | 694 | Pipeline orchestration |
| `pipeline.py` | 334 | MNE-facing master function |

### Fixed
- PYTHONPATH guarantee: `ENV` in Dockerfile, `environment` in docker-compose.yml,
  `sys.path.insert()` guard in `wsgi.py` and `worker.py`

---

## [0.8.4]

### Fixed
- Language session/DB routing corrected for multi-language sites
- Redirect loop fixes (Flask `after_request` handler)

---

## [0.8.3]

### Added
- Full i18n coverage: 369 translation keys across NL/FR/EN/DE
- All UI, admin, and report text via `t(key, lang)` central function

---

## [0.8.2]

### Added
- Centralized `conclusions.py`: shared NL/FR/EN diagnostic text for PDF and PSG reports
- 7 standardised diagnostic conclusion templates per severity/type

---

## [0.8.1]

### Added
- Rolling 2-minute arousal baseline (replaces global baseline)
- Ratio-based spindle exclusion (sigma vs alpha+beta ratio)
- Rule 1B breath-cycle validation (reject if >1 complete breath between event and arousal)
- Clipping-to-artifact feedback: epochs with >5% clipped EEG → artifact mask
- FHIR R4 DiagnosticReport + Observation + CarePlan export

---

## [0.8.0]

### Added — First public release

- EDF browser with channel-group filters (Neuro / Pneumo / Cardio)
- Role-based multi-site access control (admin / site_admin / user)
- Score editor: epoch-by-epoch manual correction
- Study deletion with full data cleanup
- Editable conclusions with PDF regeneration
- Interactive event list with jump-to-event navigation

---

## [0.7.x] — Pre-public versions (internal)

> These versions were not published on GitHub. Documented here for completeness.

### [0.7.5] — v12: Event Editor & Production Polish

- Respiratory event overlay in EDF browser (OA/CA/MA/H/AR/RERA as colour-coded bars)
- Click-to-toggle event editor with real-time AHI recalculation
- Unified portrait A4 PDF report (12 sections, replaces separate landscape PSG report)
- EDF browser integrated across all result pages
- E-mail notification on analysis completion (optional SMTP)
- ProxyFix for Nginx Proxy Manager; all flash messages translated (NL/FR/EN)

### [0.7.0] — v11: EDF Signal Viewer

- Browser-based EDF visualisation with server-side epoch API
- Combined scorer + viewer (`scorer_v11.html`)
- Multi-epoch batch loading, channel selection, amplitude scaling

### [0.6.0] — v10: Interactive Epoch Scorer

- Click/keyboard (W/1/2/3/R) hypnogram editor
- Server-side sleep statistics recalculation after manual corrections
- PDF regeneration reflecting manual overrides

### [0.5.0] — v9: FHIR & Multi-site

- FHIR R4 DiagnosticReport export
- Multi-site configuration with site-specific settings
- Role-based access: admin / site_manager / user
- `/admin/sites` multi-tenant management

### [0.4.0] — v8: Clinical Scoring & Multi-language

- **Respiratory:** artifact exclusion from AHI/OAHI; OAHI definition; Rule 1B two-pass
- **Arousal:** EEG-based (alpha/theta/beta); respiratory coupling; RERA; RDI
- **PLM:** full AASM 2.6 rewrite (amplitude threshold, bilateral merge, respiratory exclusion)
- **EDF+** export with scoring annotations
- Multi-language (NL/FR/EN) with 186+ translation keys via `i18n.py`
- Admin dashboard: user management, role-based menus
- Multi-site Docker architecture with Nginx Proxy Manager support

### [0.3.0] — v7: Pneumological Extension

- Channel selection UI (EEG, EOG, EMG)
- Apnoea/hypopnoea detection (AASM 2.6 basis), AHI severity classification
- SpO₂, heart rate, body position, snoring, PLM (basic)
- Docker Compose: Redis + App + Worker (RQ task queue)
- PDF report expanded with respiratory, SpO₂, PLM sections

### [0.2.0] — v7.5: Performance & Compatibility

- `_hypno_to_list()` hang resolved
- `compute_dynamic_baseline()` optimised — 2500× speedup via `np.interp`
- YASA 0.7 compatibility fix (`sf_hypno` → `sf_hyp`)
- Headless rendering (`matplotlib.use('Agg')`), Redis `decode_responses` fix

### [0.1.0] — v6: Production Baseline

- Flask + Gunicorn + Docker (single container)
- YASA 0.7 LightGBM sleep staging (EEG + EOG + EMG)
- Basic PDF report with hypnogram and sleep statistics
- Deployment on Hetzner server (sleepai.be / sleepai.eu)
- Single-user login with password hashing

### [0.0.x] — v1–v5: Prototype

- Initial Flask webapp wrapping YASA
- Basic EDF upload and hypnogram generation
- Single-user, local execution
