# Changelog — YASAFlaskified

All notable changes documented per [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.28] — April 2026

### Fixed — Central and mixed apnea under-classification
- **Rule 5 (central) thresholds relaxed**: `raw_var_ratio` 0.15→0.25, `quarters_absent` 3→2, `phase_angle` 20°→30°, `paradox_corr` 0.0→−0.10 — accounts for cardiac pulsation artefact on RIP bands that inflates effort metrics without true respiratory effort
- **New Rule 5a (probable central)**: catches events with effort_ratio 0.20–0.40 (gray zone between absent and present) when no paradoxical breathing or phase signal is detected — previously these all defaulted to obstructive via Rule 6
- **Rule 5b (ECG reclassification) relaxed**: effort threshold from 1.5× to 2× EFFORT_PRESENT_RATIO, allowing reclassification of more borderline events
- **Rule 3 (mixed) relaxed**: first-half effort threshold 0.20→0.35 to detect mixed apneas with gradual (not binary) effort onset
- **Rule 6 (borderline default) split**: events with low effort + no obstructive evidence now classified as central (not obstructive); obstructive default only when effort is ambiguous or movement is present

## [0.8.27] — April 2026

### Fixed — PDF multilingual + breath snap fix + OAHI per profile
- **f-string syntax error fixed**: nested double quotes `f"{t("key")}"` → `f"{t('key')}"` (6 occurrences causing worker crash on v0.8.26)
- **Breath boundary snapping OFF by default**: `USE_BREATH_SNAP` added to scoring profiles — `False` for strict/standard, `True` for sensitive only. Fixes unintended OAHI drop (~4.5/h) caused by snapped boundaries shifting SpO₂ coupling and local baseline validation windows.
- **OAHI per profile in PDF table**: scoring profile comparison table now shows OAHI column — active profile marked with ▶, other profiles shown if comparison data available
- **36+ new i18n keys** for PDF: fix table (Fix 1–6 + ECG), apnea types, severity grades, signal quality, profile headers, RERA, disclaimers, spindle/slow wave counts
- **All hardcoded Dutch removed** from `generate_pdf_report.py` — all user-facing strings via `t()` calls
- **606 total i18n keys**, 100% NL/FR/EN/DE coverage

## [0.8.26] — April 2026

### Fixed — Multilingual & clinical display
- **German (DE) as language choice**: added to `SUPPORTED_LANGS`, `LANG_NAMES`, `LANG_FLAGS`, and all HTML dropdown selectors (`base.html`, `admin_sites.html`, `admin_users.html`)
- **Scoring profile in AHI classification bar**: PDF now shows `Profile: Standard (AASM 2.6)` alongside AHI/OAHI values
- **Severity labels multilingual**: `Normaal/Mild/Matig/Ernstig` → language-dependent via `_SEV_LABELS` dict (NL/FR/EN/DE)
- **Hardcoded Dutch in PDF report**: `Niet beschikbaar`, `Overschatting-correctie` replaced with `t()` i18n calls
- **5 new i18n keys**: `pdf_not_available`, `pdf_overcounting_corrections`, `pdf_correction`, `pdf_impact`, `pdf_explanation` (all 4 languages)
- **568 total i18n keys**, 100% coverage NL/FR/EN/DE

## [0.8.25] — April 2026

### Added — Platform improvements (items 9–18)

**Clinical workflow:**
- **Batch analysis CLI** (`batch_analyse.py`): process entire directories of EDFs with parallel workers, outputs summary CSV with AHI, fix counters, staging stats per study. Supports multiple scoring profiles in one run.
- **Event-level comparison tool** (`validation_metrics.py`): `compare_respiratory_events()` performs temporal matching (±5s tolerance) between manual and automated events, reports TP/FP/FN, per-type confusion matrix, sensitivity, PPV, F1. `compute_event_type_confusion()` adds obstructive/central/mixed breakdown.
- **Scoring profile comparison** (`tasks.py`): `run_profile_comparison()` runs strict/standard/sensitive on the same EDF and outputs a comparison table with AHI, OAHI, severity per profile.
- **ECG reclassification in PDF fix table** (`generate_pdf_report.py`): `n_ecg_reclassified_central` now shown in the over-counting correction summary.
- **U-Sleep integration stub** (`yasa_analysis.py`): `run_sleep_staging(backend="usleep"|"both")` provides a clean integration point for U-Sleep. `backend="both"` runs YASA+U-Sleep and adds epoch-level agreement to the result dict.
- **Demo EDF generator** (`generate_demo_edf.py`): creates a synthetic 30-min PSG with visible OA/CA/hypopneas, desaturations, position changes, and stage-appropriate EEG — no patient data, GDPR-safe.

**Technical/infrastructure:**
- **VERSION constant** (`version.py`): single source of truth for version strings, imported by `app.py`.
- **German (DE) translations**: 563/563 i18n keys now have DE translations (auto-generated from EN with medical term mapping). Full NL/FR/EN/DE coverage.
- **LRU cache** (`edf_api.py`): already implemented as `_LRUCache` (max 3 EDF files per worker) — verified present.
- **ProxyFix** (`app.py`): already implemented at startup — verified present.

### Changed
- `README.md`: version badge, citation, deploy instructions updated to 0.8.25
- `CHANGES.md`: full changelog for v0.8.24 and v0.8.25
- `i18n.py`: 563 DE translation keys added via post-init `_DE_PATCH` block

## [0.8.24] — psgscoring v0.2.5

### Added — Scoring improvements (items 4–8)
- **Adaptive cardiac frequency band** (ecg_effort.py): `compute_adaptive_cardiac_band()` derives the patient's actual heart rate from R-R intervals and adjusts the spectral classifier's cardiac band accordingly. Prevents misclassification in bradycardic patients (athletes, beta-blocker users) where the cardiac fundamental overlaps the respiratory band.
- **Flattening index in apnea type classification** (classify.py): `classify_apnea_type()` now accepts an optional `flattening_index` parameter. High flattening (>0.30) boosts obstructive confidence; low flattening (<0.10) with absent effort supports central classification.
- **SpO₂ low baseline warning** (spo2.py): flags studies with baseline SpO₂ < 88% (`low_baseline_warning`, `low_baseline_note`), alerting to possible COPD/OHS overlap where the 3% desaturation criterion is less meaningful.
- **Breath boundary snapping** (respiratory.py): `_snap_to_breath_boundaries()` adjusts algorithmically detected event onset/end to the nearest zero-crossing of the bandpass-filtered flow signal, improving per-event concordance with manual scorers.
- **ECG effort test suite**: 13 new tests covering R-peak detection, TECG computation, adaptive cardiac band, spectral classifier, and combined assessment. Total test count: 37.

### Changed
- `spectral_effort_classifier()` now accepts optional `cardiac_band_hz` parameter
- `ecg_effort_assessment()` uses adaptive cardiac band by default
- `_detect_apneas()` and `_detect_hypopneas()` accept `flow_filt` for boundary snapping

### Verified — Items 1–3 already present
- Standalone psgscoring is byte-identical to embedded version (no divergence)
- Position-change baseline reset: `detect_position_changes()` + `reset_baseline_at_position_changes()` fully wired in respiratory.py
- Stage-specific baseline blending: `compute_stage_baseline()` with NREM/REM separation and 5s cosine-ramp smoothing fully operational

## [0.8.23]

### Added
- **ECG-derived effort classification (TECG)**: Transformed ECG method (Berry et al., JCSM 2019) for improved central vs. obstructive apnea differentiation
- **Spectral effort classifier**: cardiac (0.8–2.5 Hz) vs. respiratory (0.1–0.5 Hz) power analysis on RIP bands during apnea events
- **Combined reclassification logic**: events reclassified as central when both TECG (no inspiratory bursts) and spectral analysis (cardiac dominance) agree
- New output field `n_ecg_reclassified_central` in respiratory results
- New module `psgscoring/ecg_effort.py` with `compute_tecg()`, `detect_r_peaks()`, `qrs_blanking()`, `detect_inspiratory_bursts()`, `spectral_effort_classifier()`, `ecg_effort_assessment()`

### Changed
- `pipeline.py`: ECG channel now extracted and passed to respiratory scoring
- `respiratory.py`: TECG computed once per recording; ECG assessment passed to both apnea and hypopnea `classify_apnea_type()` calls
- `classify.py`: ECG-based reclassification integrated into 7-rule classification (Rule 5b)

## [0.8.22]

### Fixed — PDF rapport inconsistenties & klinische correctheid

**Lokale basislijn-validatie (klinisch kritiek — v0.8.22):**
- FIX: False-positive hypopneeën door opgeblazen rollende basislijn (post-apnea recovery hyperpnea)
- NIEUW: `_validate_local_reduction()` — vergelijkt event-amplitude met de directe pre-event ademhaling (30s venster), exact zoals een menselijke scorer doet
- Events met <20% lokale reductie worden afgewezen met reden `local_reduction_Xpct<20pct`
- Voorkomt 60–80+ seconden "hypopneeën" waar visueel geen flow-reductie zichtbaar is
- PDF: "Fix 6 — Lokale basislijn" in overschatting-correctie tabel toont aantal afgewezen events

**Hypopnea/Apnea max-duur splitting (klinisch kritiek):**
- FIX: Hypopneeën van 60–80+ seconden werden als één event gescoord — klinisch onrealistisch
- NIEUW: `HYPOPNEA_MAX_DUR_S = 60s`, `APNEA_MAX_DUR_S = 90s` (configureerbaar per scoring profiel)
- NIEUW: `_split_long_region()` splitst te lange events op het punt van maximale flow-recovery (partiële herstel-ademhaling)
- Recursief: sub-regio's die nog te lang zijn worden opnieuw gesplitst
- Elk sub-event krijgt eigen desaturatie-berekening, classificatie en confidence
- Profiel-afhankelijk: strict=60/90s, standard=60/90s, sensitive=90/120s

**SpO2 sectie (kritiek):**
- FIX: `mean_spo2` key mismatch — PDF gebruikte `mean_spo2` maar SpO2 module retourneerde `avg_spo2` → Gemiddelde SpO2 toonde altijd "—"
- FIX: ODI 3% en ODI 4% werden nooit berekend — PDF verwees naar `odi_3pct`/`odi_4pct` maar `analyze_spo2()` berekende deze niet → altijd "—"
- NIEUW: ODI 3% en ODI 4% worden nu correct berekend via `detect_desaturations()` met respectievelijk `drop_pct=3.0` en `drop_pct=4.0`
- NIEUW: Baseline SpO2 (P90) nu ook zichtbaar in SpO2-tabel
- NIEUW: `mean_spo2` alias toegevoegd voor backward-compatibiliteit
- NIEUW: `n_desat_3pct` en `n_desat_4pct` tellingen in summary dict

**Slaapcycli (klinisch misleidend):**
- FIX: Cycle-detectie herschreven — oude algoritme maakte nieuwe cyclus bij elke REM→NREM transitie, zonder minimale duur. Produceerde 33 micro-cycli (0.5–3.0 min) i.p.v. verwachte 4–6 cycli
- NIEUW: Feinberg & Floyd criteria: minimaal 15 min NREM (30 epochs) vereist voor geldige cyclus
- NIEUW: REM-consolidatie: korte N1/W onderbrekingen (≤2 min) breken REM-periode niet

**REM-detectie (klinisch misleidend):**
- FIX: REM-perioden werden gefragmenteerd geteld — elke R→non-R transitie was een "periode"
- NIEUW: Geconsolideerde REM-perioden met gap-tolerantie (≤4 epochs N1/W)
- Realistische n_rem_periods, mean_rem_period_min, longest_rem_period_min

**Spindle & Slow Wave tabellen:**
- FIX: "Stadium" kolom toonde altijd "—" — YASA summary met `grp_chan=True, grp_stage=False` heeft `Channel` key, niet `Stage`
- FIX: Kolomheader veranderd van "Stadium" naar "Kanaal" (i18n: NL/FR/EN)
- FIX: Row lookup zoekt nu Channel→channel→Stage→stage fallback chain

**Signaal kwaliteit & confidence waarschuwing:**
- NIEUW: Rode banner bovenaan rapport wanneer signaalkwaliteit "poor" is met onbruikbare kanalen
- NIEUW: Rode banner wanneer ≥20% epochs AI-confidence <70% — "Manuele verificatie aanbevolen"
- Waarschuwingen verschijnen direct na de KPI-balk, vóór de slaaparchitectuur

**Signaalvoorbeelden in PDF (sectie 8e):**
- NIEUW: Tot 3 representatieve respiratoire events als gestapelde signaalplots
- Selectie: hoogste confidence, langste event, grootste desaturatie (gededupliceerd)
- Per event: 15s pre + event + 30s post, alle beschikbare pneumokanalen (Flow, Nasal P., Thorax, Abdomen, SpO₂, Snore)
- Rode band markeert event-duur, titel toont type/duur/desaturatie/confidence/slaapstadium
- i18n: sectieheader en intro-tekst in NL/FR/EN
- `edf_path` en `pneumo_channels` worden nu meegegeven via combined dict (tasks.py)

### Changed
- Versienummer: 0.8.19 → 0.8.22 in alle bestanden (app.py, i18n.py, generate_pdf_report.py, signal_quality.py, README.md, DISCLAIMER.md)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.19]

### Added — Study types, position legend, titration support

**Study type support (v0.8.19):**
- UI dropdown: Diagnostic PSG / Titration PSG CPAP / Titration PG CPAP / Titration PG MRA
- Study type flows through config → results → PDF
- PDF title: "Slaaprapport" vs "Titratierapport — CPAP" vs "Titratierapport — MRA"
- Titration: "Residueel AHI" / "Residueel OAHI" labels + therapy note
- Polygraphy: "REI" instead of "AHI", sections 2-7 + 8b arousals skipped
- Polygraphy: "Geen slaapstaging" notice in section 1
- 13 new i18n keys NL/FR/EN

**Position legend in visual overview (v0.8.19):**
- POS legend line added under EVENT/SpO2/PHONO legends

### Fixed

**EDF → header auto-fill (v0.8.18→0.8.19):**
- Eigen EDF parser bij kanaalkeuz (MNE subject_info onbetrouwbaar)
- EDF patient fields auto-populate PDF header + formulier
- Numerieke naam (patiëntcode) wordt vervangen door EDF-naam
- Duplicate "Patiëntgegevens (uit EDF)" tabel verwijderd
- Heranalyse: slimme merge detecteert code vs naam

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.17]

### Added — Signal quality, flattening RERA, montage checks

**Signal quality assessment (v0.8.19):**
- New module `psgscoring/signal_quality.py`
- Per-channel: flat-line %, clipping %, line-noise %, disconnect count
- Channel grade: good / acceptable / poor; overall recording grade
- PDF Section 7b: table per channel with quality metrics

**Montage plausibility checks (v0.8.19):**
- Cross-correlation EEG↔EOG (r>0.95 = shared reference warning)
- Cross-correlation thorax↔abdomen (r>0.98 = duplication warning)
- Cross-correlation flow↔effort (r>0.95 = duplication warning)
- Warnings displayed prominently in PDF report

**Flattening-based RERA detection (v0.8.19):**
- Dual-source RERA: FRI-RERA (amplitude) + Flattening-RERA (shape)
- Hosselet et al. (AJRCCM 1998) flattening index >0.30 = flow limitation
- ≥3 consecutive flat breaths, ≥10s, + arousal = flattening-RERA
- RDI = AHI + (FRI-RERA + Flattening-RERA) / TST
- PDF shows both RERA sources separately

### Changed
- Pipeline: 11 steps (added 1b: signal quality)
- RERA table in PDF: two rows (FRI vs flattening source)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.16]

### Added — RERA/RDI, REM/NREM AHI, clinical indices

**RERA index and RDI (v0.8.16):**
- RERA = flow-reduction events (≥30%, ≥10s) + arousal, without ≥3% desaturation
- Computed from remaining FRI events after Rule 1B reinstatement
- RDI = AHI + RERA index — clinically relevant for UARS diagnosis
- Displayed in PDF respiratory section with interpretation note

**REM vs NREM AHI (v0.8.16):**
- Stage-specific AHI (REM-AHI, NREM-AHI) in respiratory summary and PDF
- Clinically relevant for REM-dominant OSAS phenotype

**Positional AHI in PDF (v0.8.16):**
- AHI per body position (Supine, Left, Right, Prone, Upright) displayed
  in PDF alongside REM/NREM AHI
- Already computed in ancillary.py, now visible in report

**SpO2 samplerate check (v0.8.16):**
- Warning when SpO2 channel samplerate < 0.33 Hz (>3s averaging)
- AASM requires maximum 3-second signal averaging for pulse oximetry
- Flag `spo2_low_samplerate` stored in output; PDF shows warning banner

**Hypopnea subtype counts (v0.8.16):**
- `n_hypopnea_obstr`, `n_hypopnea_central`, `n_hypopnea_mixed` in summary
- Most commercial software does not differentiate hypopnea subtypes

**Cosmetisch (v0.8.16):**
- Logo: Concept C (EEG-trace + "YASAFlaskified" + slaapkliniek.be)
- Dubbele "Download PSG" knop verwijderd (was redirect naar PDF)
- Footer: referenties YASA, psgscoring, AASM 2.6
- EDF patient info (naam, geslacht, geboortedatum) in PDF

### Changed
- Pipeline step numbering: 9 → 10 steps (added Step 8b: RERA/RDI)

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.15]

### Added — Configurable scoring profiles

**Scoring profile system (strict / standard / sensitive):**
- Three predefined profiles controlling hypopnea threshold, SpO2 nadir
  window, flow smoothing, cross-contamination window, and peak detection
- `strict`: AASM exact (0.70 threshold, 30s window, no smoothing, envelope only)
- `standard`: recommended (0.70, 45s, 3s smoothing, peak+envelope) — default
- `sensitive`: RPSGT-like (0.75/25% reduction, 45s, 5s smoothing, no cross-contam)
- UI dropdown on channel-select page (NL/FR/EN translations)
- Profile label shown in PDF report subtitle
- Profile thresholds logged and stored in `result["scoring_thresholds"]`
- Pipeline parameter: `run_pneumo_analysis(..., scoring_profile="standard")`

### Changed
- `get_desaturation()` accepts `post_win_s` parameter (was hardcoded)
- `_detect_hypopneas()` accepts `desat_pct`, `contam_win_s`, `post_event_win_s`
- `constants.py`: `SCORING_PROFILES` dict, `POST_EVENT_WINDOW_S`, `CROSS_CONTAM_WINDOW_S`
- Version number updated to 0.8.15

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.14]

### Added — AASM-conforme peak-based hypopnea detection

**Peak signal excursion detection (AASM 2.6 conformiteit):**
- AASM 2.6 definieert hypopnea als "peak signal excursions drop by ≥30%"
  — dit verwijst naar **piek-amplitude per ademhaling**, niet naar de
  continue Hilbert-envelope
- Nieuwe detectielogica: per ademhaling (via `detect_breaths()` +
  `compute_breath_amplitudes()`) wordt de piek-dal-amplitude vergeleken
  met de lokale basislijn (mediaan voorgaande 10 ademhalingen)
- Ademhalingen met amplitude <70% baseline worden gemarkeerd als "reduced"
- Sample-level peak-mask wordt gecombineerd met envelope-mask via OR:
  events gevonden door **peak-methode óf envelope-methode** worden gescoord
- Verwacht effect: hogere sensitiviteit (minder onderschatting vs technicus),
  betere concordantie met menselijke RPSGT-scoring
- Toegepast op beide detectiepasses (initieel + post-recovery gecorrigeerd)
- Configureerbaar: `HYPOPNEA_THRESHOLD = 0.70` in `constants.py`

### Fixed — Hypopnea undercounting root causes

**SpO2 cross-contamination fix was too aggressive (CRITICAL):**
- Previous behavior: if next event starts within 30s of previous event end,
  SpO2 desaturation was set to `None` → Rule 1A always fails → event rejected
- At moderate OSAS (events 20–40s apart), this rejected **nearly all hypopneas**
- Fix: desaturation is ALWAYS computed; contamination flag is informational only
- Cross-contamination window reduced from 30s to 15s
- Expected impact: **major increase in OAHI** for patients with cluster events

**SpO2 nadir search window too short:**
- Increased POST_WIN_S from 30s to 45s in `get_desaturation()`
- Finger oximetry has 20–40s circulatory delay; nadirs at 30–45s were missed
- AASM inter-scorer reliability study recommends scoring desaturation
  within 30s of event end — but this is measured from the *oximeter reading*,
  not accounting for probe-to-finger delay

### Fixed — PDF visueel overzicht

**X-as uitlijning:**
- `bbox_inches="tight"` verwijderd uit `_ov_finish()` — dit verschoof marges
  per grafiek afhankelijk van y-label breedte
- Alle plots gebruiken nu vaste `subplots_adjust(left=0.09, right=0.98)`
- X-tick labels alleen op laatste plot (SpO2) — tussenliggende plots
  tonen alleen gridlijnen (compacter, beter uitgelijnd)

**Legende onderaan visueel overzicht:**
- Kleurcodering EVENT (OA/CA/MA/HYP/FR), SpO2 drempels, PHONO drempel

### Changed
- Version number updated to 0.8.14

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.13]

### Added — Signal improvements and PDF fixes

**SpO2 timeseries in visual overview:**
- `analyze_spo2()` now saves 1 Hz downsampled timeseries in `result["timeseries"]`
- SpO2 curve renders in PDF section 0b alongside HYPNO, EVENT, POS, PHONO

**Position signal auto-mapping (`_map_position_signal()`):**
- Auto-detects whether position channel contains pre-coded 0–4 values
  or raw ADC/voltage data (e.g., 0–255 from SomnoMedics, Embla)
- Raw values → percentile-based quantization to 5 positions
- Fixes flat-line position plots on non-standard EDF recordings

**Hypopnea sensitivity improvement:**
- 3-second rolling mean (`uniform_filter1d`) applied to normalized flow
  before thresholding (`HYPOPNEA_SMOOTH_S = 3.0` in `constants.py`)
- Mimics human visual averaging: small oscillations above threshold
  no longer break events into fragments
- Reduces false negatives vs. technician scoring without lowering
  the AASM ≥30% amplitude criterion
- Applied to both initial detection and post-recovery corrected pass

### Changed
- Version number updated to 0.8.13

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.12]

### Added — PSG overview page and clinical report improvements

**Visual overview page (PDF report):**
- Section 0a: EDF channel inventory table (all channels in recording)
- Section 0b: Stacked synced timeline plots — HYPNO, EVENT, POS, PHONO, SpO₂
- New plot functions: `_pos_img()` (body position), `_snore_img()` (snoring RMS),
  `_events_img()` (respiratory events timeline)
- Snore analysis now exposes `rms_1s` timeseries for plotting

**Ronchopathy section (10b):**
- Snoring duration (min), snoring % of TST, snoring index (/h)
- Always visible — shows "no snoring channel" if not available

**Flow Reduction Index — FRI (section 8d):**
- Counts rejected hypopneas (≥30% flow reduction, ≥10s) that meet neither
  ≥3% desaturation nor arousal criteria
- FRI = flow reductions per hour of sleep
- Clinically relevant for UARS / RDI evaluation
- Part of respiratory section (8d)

**Conclusion section (11) — manual only:**
- Auto-generated conclusions removed (`generate_conclusions()` no longer called)
- Empty conclusion shows: "To be completed by the treating physician"
- Manual diagnosis via report editor still works as before

**DISCLAIMER.md:**
- Full medical/clinical disclaimer (9 sections)
- Not a medical device, no CE/FDA, known limitations, data privacy,
  user responsibility, third-party components

### Changed
- Hypnogram moved into visual overview (0b) — separate section 2 removed
- All sections renumbered: 1–11 (was 1–12)
- Version number updated to 0.8.12 in app.py, PDF footer, i18n, DISCLAIMER
- NL docstrings added to all 80 functions in embedded `psgscoring/`

### Fixed
- **Numpy-unsafe `or` in `_resolve_flow_channels()`** — `flow_therm_data or
  flow_pressure_data` crashes with `ValueError: The truth value of an array
  with more than one element is ambiguous`. Replaced with explicit
  `is not None` ternary checks (3 lines in `psgscoring/pipeline.py`).

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


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
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


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

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


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

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.8]

### Added
- OAHI confidence stratification: `oahi_conf60` (events with confidence >0.60)
- `confidence_bands` in summary: `{"high": N, "moderate": N, "borderline": N, "low": N}`
- Confidence breakdown table in PDF and PSG reports

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.7]

### Added
- 8 parallel RQ worker containers (`worker1`–`worker8`) via YAML anchor in docker-compose.yml
- Worker pool calibrated for Ryzen 9 5950X (16 real cores: 8 workers + OS headroom)

### Changed
- Single sequential worker replaced by parallel pool
- Estimated RAM usage: ~16 GB of 128 GB (2 GB per worker)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.6]

### Fixed
- `_hypno_img()` in `generate_pdf_report.py`: `lang` was a free variable → `NameError`
- `build_hypnogram_figure()` in `generate_psg_report.py`: called before `lang` defined
- Hardcoded "Tijd (min)" → `t("pdf_time_axis", lang)`

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


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
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.4]

### Fixed
- Language session/DB routing corrected for multi-language sites
- Redirect loop fixes (Flask `after_request` handler)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.3]

### Added
- Full i18n coverage: 369 translation keys across NL/FR/EN/DE
- All UI, admin, and report text via `t(key, lang)` central function

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.2]

### Added
- Centralized `conclusions.py`: shared NL/FR/EN diagnostic text for PDF and PSG reports
- 7 standardised diagnostic conclusion templates per severity/type

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.1]

### Added
- Rolling 2-minute arousal baseline (replaces global baseline)
- Ratio-based spindle exclusion (sigma vs alpha+beta ratio)
- Rule 1B breath-cycle validation (reject if >1 complete breath between event and arousal)
- Clipping-to-artifact feedback: epochs with >5% clipped EEG → artifact mask
- FHIR R4 DiagnosticReport + Observation + CarePlan export

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.0]

### Added — First public release

- EDF browser with channel-group filters (Neuro / Pneumo / Cardio)
- Role-based multi-site access control (admin / site_admin / user)
- Score editor: epoch-by-epoch manual correction
- Study deletion with full data cleanup
- Editable conclusions with PDF regeneration
- Interactive event list with jump-to-event navigation

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


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
