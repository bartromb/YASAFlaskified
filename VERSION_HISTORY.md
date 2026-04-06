# YASAFlaskified — Version History

## v1.0–v5.0 — Prototype & Early Development
- Initial Flask webapp wrapping YASA sleep staging
- Basic EDF upload, hypnogram generation
- Single-user, local execution

---

## v6.0 — Production Baseline
- **Stack:** Flask + Gunicorn + Docker (single container)
- **Staging:** YASA 0.7 LightGBM classifier (EEG + EOG + EMG)
- **Output:** Basic PDF report with hypnogram, sleep statistics
- **Deployment:** Hetzner server, sleepai.be / sleepai.eu
- **Auth:** Single-user login with password hashing

---

## v7.0 — Pneumological Extension
- **Channel selection UI:** User chooses EEG, EOG, EMG, extra EEG channels
- **Respiratory analysis (AASM 2.6 basis):**
  - Apnea detection (obstructive/central/mixed classification)
  - Hypopnea detection (Rule 1A — ≥3% desaturation criterion)
  - AHI calculation with severity classification
- **Ancillary analyses:** SpO2, heart rate, body position, snoring, PLM (basic)
- **Docker Compose:** Redis + App + Worker architecture with RQ task queue
- **PDF report:** Expanded with respiratory, SpO2, PLM sections

## v7.5 — Performance & Compatibility
- **Critical fix:** `_hypno_to_list()` hang resolved
- **Performance:** `compute_dynamic_baseline()` optimized — 2500× speedup via `np.interp`
- **YASA 0.7 compat:** `sleep_statistics` parameter `sf_hypno` → `sf_hyp` with fallback
- **Stability:** Logging `force=True`, `matplotlib.use('Agg')` for headless rendering
- **Redis:** `decode_responses=True` disabled to prevent worker crashes on 2nd job

---

## v8.0 — Clinical Scoring & Multi-language
### Respiratory Scoring
- **Artifact exclusion from AHI/OAHI:** Artifact epochs removed from sleep mask and TST calculation
- **OAHI (Obstructive AHI):** Obstructive apneas + all hypopneas (excluding central/mixed)
- **Hypopnea Rule 1B (arousal criterion):** Two-pass approach — rejected hypopneas (no ≥3% desat) saved as candidates, reinstated after arousal detection if arousal within 15s window
- **AHI/OAHI recalculated** after Rule 1B reinstatement

### Arousal Module
- EEG-based arousal detection (alpha/theta/beta spectral bursts)
- Respiratory–arousal coupling (within 15s of respiratory event)
- RERA detection (flow limitation + arousal, no apnea/hypopnea criteria met)
- RDI calculation (AHI + RERA index)
- Arousal index, respiratory vs spontaneous classification

### PLM Rewrite (AASM 2.6)
- Amplitude threshold: ≥8 μV above resting EMG (was: 2× mean RMS)
- Band-pass filter: 10–100 Hz (was: 10 Hz highpass)
- Bilateral merge: L+R within 0.5s = 1 LM
- Wake exclusion: LMs during Wake not counted for PLMI
- Respiratory exclusion: LMs within ±0.5s of respiratory event end excluded
- Series criterion: ≥4 consecutive LMs, 5–90s interval
- Severity classification: normal/mild/moderate/severe

### EDF+ Export
- Annotated EDF+ with sleep stages, respiratory events, arousals, artifacts
- Data clipping for extreme values (±9999999) to prevent field overflow
- On-demand generation (not in pipeline — too slow)

### Patient Data & Reports
- EDF header parsing: sex, birthday, scorer, institution
- Patient info form with manual override
- Analysis history page (`/results`) scanning `*_results.json` files
- PSG report (landscape A4): clinical layout with standardized AASM conclusion

### Standardized Diagnostic Conclusion
| Condition | Conclusion | Treatment |
|-----------|-----------|-----------|
| AHI < 5, PLMI < 15, SE ≥ 85% | Normal PSG | None |
| AHI 5–15 (mild OSAS) | Mild OSAS | Positional therapy, MAD, sleep hygiene |
| AHI 15–30 (moderate OSAS) | Moderate OSAS | CPAP first-line, MAD alternative |
| AHI > 30 (severe OSAS) | Severe OSAS | CPAP urgent, ENT evaluation |
| PLMI ≥ 15 | Significant PLMs | Ferritin check, iron supplementation |
| SE < 85% or TST < 360 min | Insomnia indicators | CBT-I first-line |
| BMI > 28 + OSAS | Weight reduction recommended at all OSAS severities |

### Multi-language (NL/FR/EN)
- `i18n.py` translation module with 186+ keys
- Language selector in navbar (stored in session)
- `@app.context_processor` injects `t()` function into all templates
- All templates, flash messages, and UI elements translated

### Admin & User Management
- Admin dashboard (`/admin/users`): create, delete, reset password
- User self-service: `/change_password`
- Navbar user dropdown with role-based menu items

### Infrastructure
- Multi-site Docker architecture (isolated Redis/volumes/networks per site)
- Nginx Proxy Manager support with ProxyFix
- `docker-init.sh` auto-detects Gunicorn bind address
- Security: CSRF (Flask-WTF), rate limiting, password strength validation, UFW, fail2ban

---

## v9.0 — FHIR & Multi-site
- **FHIR R4 export:** DiagnosticReport resource (`/results/<job_id>/fhir`)
  - Patient, Performer, Observation resources for AHI/SpO2/PLM
  - Conformant with HL7 FHIR R4 specification
- **Multi-site configuration:** Site-specific settings (name, address, logo)
- **Admin dashboard:** Patient overview with search, filter by severity/status
- **Role-based access:** admin, site_manager, user roles
- **Site management:** `/admin/sites` for multi-tenant configuration

---

## v10.0 — Interactive Epoch Scorer
- **Hypnogram editor:** Click or keyboard shortcut (W/1/2/3/R) to reassign epoch stages
- **Server-side recalculation:** Sleep statistics, spindles, slow waves regenerated after manual changes
- **PDF regeneration:** Updated report reflects manual corrections
- **Scoring persistence:** Manual overrides saved to `_manual_hypno.json`

---

## v11.0 — EDF Signal Viewer
- **Browser-based EDF visualization:** Real-time signal display in browser
- **Server-side EDF API:**
  - `GET /api/edf/<job_id>/info` — channel list, sample rate, duration
  - `GET /api/edf/<job_id>/epoch/<idx>` — single epoch signal data
  - `GET /api/edf/<job_id>/epochs/<start>/<end>` — multi-epoch batch (max 10)
- **Viewer features:** Epoch navigation, channel selection, amplitude scaling, stage color overlay
- **Combined scorer + viewer:** `scorer_v11.html` with side-by-side hypnogram and signals

---

## v12.0 — Event Editor & Production Polish
### Event Overlay System
- **Respiratory event overlay:** OA/CA/MA/H/AR/RERA displayed as color-coded bars on signal traces
- **Click-to-toggle:** Add/remove events at specific timepoints in the viewer
- **Event types:** Obstructive Apnea, Central Apnea, Mixed Apnea, Hypopnea, Arousal, RERA
- **Server-side AHI recalculation:** Real-time index updates after event modifications
- **Event persistence:** Stored in `{job_id}_events.json` with source (ai/manual), scorer, timestamps
- **Event API:**
  - `GET /api/edf/<job_id>/events/<epoch>` — events for one epoch
  - `GET /api/edf/<job_id>/events/all` — all events
  - `POST /api/edf/<job_id>/events/toggle` — create/delete event

### PDF Report Unified (Portrait A4)
- **Single AASM-compliant report** — portrait A4, replaces separate landscape PSG
- All 12 sections in one document:
  1. Sleep architecture with AASM reference values
  2. Hypnogram visualization
  3. Sleep cycles (NREM–REM)
  4. Sleep spindles
  5. Slow waves
  6. REM detection
  7. Spectral band power
  8. Artifact detection
  9. Respiratory analysis (AHI/OAHI/RDI, Rule 1A+1B, arousal/RERA)
  10. SpO2 analysis with timeseries graph
  11. PLM (AASM 2.6)
  12. Standardized diagnosis with treatment suggestions
- **Institutional header:** Configurable clinic name, address, contact
- **Scorer + physician signature line**
- **Clinical disclaimer**

### EDF Browser Integrated Everywhere
- Dashboard: 📡 EDF button per study
- Results page: 📡 EDF Browser button
- Job status (after analysis): 📡 EDF Browser & Scorer button
- History page: 📡 per study

### Code Quality & Cleanup
- **ProxyFix** added for reverse proxy (NPM/Nginx) support
- **All flash messages translated** (NL/FR/EN) via `get_translation()`
- **Dashboard fully translated** (NL/FR/EN)
- **Version updated to v12** in all footers, headers, docker-compose
- **Old files removed:** `app_v9/10/11/12_patches.py`, `scorer_v10/11.js`, `edf_viewer_v11.js`
- **`.dockerignore`** added for clean builds
- **15 Python files, 25 templates** — all syntax-verified

### E-mail Notification
- Optional SMTP notification when analysis completes
- Configurable via environment variables (`YASAFLASKIFIED_SMTP_*`)

---

## Architecture (v12)

```
┌──────────────────────────────────────────────┐
│              Nginx Proxy Manager              │
│         (SSL, domain routing, headers)        │
└──────────────┬───────────────────────────────┘
               │ http://127.0.0.1:8071
┌──────────────▼───────────────────────────────┐
│           Docker Compose Stack                │
│                                               │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐ │
│  │  Redis   │  │   App    │  │   Worker     │ │
│  │  (queue) │◄─│ (Flask + │  │ (RQ + YASA  │ │
│  │          │  │ Gunicorn)│─►│ + pneumo)   │ │
│  └─────────┘  └──────────┘  └─────────────┘ │
│                    │                │         │
│              ┌─────▼────────────────▼───┐     │
│              │   Shared Volumes         │     │
│              │ uploads/ processed/      │     │
│              │ logs/ instance/ (SQLite) │     │
│              └──────────────────────────┘     │
└──────────────────────────────────────────────┘
```

## Tech Stack (v12)

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11, Flask 3.x, Gunicorn |
| Task Queue | Redis 7 + RQ |
| Sleep Staging | YASA 0.7 (LightGBM) |
| Signal Processing | MNE-Python, SciPy, NumPy |
| Arousal Detection | Custom spectral analysis |
| PDF Reports | ReportLab |
| Excel Export | OpenPyXL |
| EDF+ Export | edfio |
| FHIR Export | Custom HL7 FHIR R4 |
| Database | SQLite (users, sites) |
| Containerization | Docker Compose |
| Reverse Proxy | Nginx Proxy Manager |
| SSL | Let's Encrypt (via NPM) |
| Frontend | Bootstrap 5, Chart.js, vanilla JS |

---

## File Manifest (v12)

### Python Modules (15 files)
| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 2200 | Flask application, routes, auth, API endpoints |
| `tasks.py` | 600 | RQ worker pipeline, job orchestration |
| `yasa_analysis.py` | 630 | YASA staging + EEG microstructure analysis |
| `pneumo_analysis.py` | 1500 | Respiratory, SpO2, PLM, arousal detection |
| `arousal_analysis.py` | 770 | EEG arousal detection module |
| `generate_pdf_report.py` | 550 | Portrait A4 AASM clinical report |
| `generate_psg_report.py` | 980 | Legacy landscape PSG report (archived) |
| `generate_excel_report.py` | 430 | Excel data export |
| `generate_edfplus.py` | 180 | EDF+ with scoring annotations |
| `edf_api.py` | 280 | Server-side EDF data API for browser viewer |
| `event_api.py` | 370 | Event CRUD + AHI recalculation |
| `fhir_export.py` | 200 | FHIR R4 DiagnosticReport export |
| `i18n.py` | 310 | 186+ translation keys (NL/FR/EN) |
| `worker.py` | 50 | RQ worker entry point |
| `wsgi.py` | 20 | WSGI entry point |

### Templates (25 files)
| File | Purpose |
|------|---------|
| `base.html` | Base template: navbar, language selector, user menu, footer |
| `login.html` | Login page |
| `dashboard.html` | Admin/manager patient overview with search/filter |
| `upload.html` | EDF upload with client-side validation |
| `channel_select.html` | Channel selection + patient info form |
| `job_status.html` | Analysis progress with live updates |
| `results_extended.html` | Full results with 12 tabs |
| `results_history.html` | Analysis history list |
| `scorer_v12.html` | EDF browser + event overlay + hypnogram editor |
| `score_editor.html` | Epoch-only hypnogram editor |
| `admin_users.html` | User management (admin) |
| `admin_sites.html` | Site configuration (admin) |
| `change_password.html` | Password change (self-service) |
| `frontpage.html` | Public landing page |

### Static Assets
| File | Purpose |
|------|---------|
| `scorer_v12.js` | Hypnogram editor + keyboard shortcuts |
| `edf_viewer_v12.js` | Browser-based EDF signal viewer |
| `styles.css` | Custom styles |
| `logo.png` | Application logo |

---

*© 2024–2026 Bart Rombaut — Slaapkliniek AZORG — www.slaapkliniek.be*

---

> **Note:** From v0.8.11 onwards, the monolithic `pneumo_analysis.py` was refactored into the modular `psgscoring` package. Detailed changelogs for the v0.8.x series are maintained in [CHANGES.md](CHANGES.md).

## v0.8.11–v0.8.19 — Modular psgscoring & Over-counting Corrections

- Extracted `psgscoring` as standalone pip-installable library (BSD-3)
- 5 over-counting corrections (Fix 1–5): baseline inflation, SpO₂ cross-contamination, CSR flagging, borderline classification, artefact-flank exclusion
- 5 under-counting corrections: peak-based detection, SpO₂ de-blocking, extended nadir window, flow smoothing, position auto-mapping
- Hilbert phase-angle effort classification for apnea typing
- Configurable scoring profiles (strict, standard, sensitive)
- Dual-sensor flow detection (thermistor + nasal pressure per AASM 2.6)
- Full i18n system (NL/FR/EN/DE) with 449+ translation keys
- EDF+ export via pyedflib
- Report editor page with diagnosis editing and PDF regeneration

## v0.8.22 — Local Baseline Validation & Clinical Polish

- **Fix 6:** Local baseline validation — rejects false-positive hypopneas where flow reduction <20% vs. pre-event breathing
- Maximum event duration: hypopnea ≤60 s, apnea ≤90 s, with splitting at partial flow recovery
- ODI at 3% and 4% thresholds, mean SpO₂
- Sleep cycle detection (Feinberg & Floyd criteria)
- REM consolidation (merge gaps ≤2 epochs)
- Signal quality assessment with confidence banners
- Epoch signal examples in PDF report
- Spindle/slow wave channel fix

## v0.8.23 — ECG-Derived Effort & Central Apnea Reclassification (Current)

- **ECG-derived effort classification (TECG):** Transformed ECG method (Berry et al., JCSM 2019) — high-pass filter + QRS blanking reveals inspiratory EMG bursts from routinely recorded ECG
- **Spectral effort classifier:** cardiac (0.8–2.5 Hz) vs. respiratory (0.1–0.5 Hz) power analysis on RIP bands
- **Combined reclassification:** events reclassified as central when both TECG and spectral analysis agree on absent effort (confidence 0.85)
- New output field: `n_ecg_reclassified_central`
- **psgscoring v0.2.4** with `ecg_effort` module
- All version references updated to v0.8.23
