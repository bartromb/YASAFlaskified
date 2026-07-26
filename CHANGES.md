# Changelog — YASAFlaskified

## v0.16.4 — 2026-07-26  *(de-detail ML tooltip)*

Content-only. Removed the internal manuscript reference ("paper v35 §3.6.1") and model
version tag from the `ml_help` scoring-profile tooltip — now simply "LightGBM candidate
classifier (enabled by default only on mesa_shhs)". No scoring change.

## v0.16.3 — 2026-07-26  *(disclaimer fix + landing-page publication wording)*

Content-only. No scoring or pin change.

- **PDF disclaimer**: fixed "Vallat \& Walker" → "Vallat & Walker" (`\&` → `&amp;`, was
  rendering a literal backslash) and dropped the internal "(paper v35)" version tag.
- **Landing page**: the peer-reviewed-publication item no longer names the target journal,
  manuscript version, or co-authors — now simply "a peer-reviewed publication … is in
  preparation".
- **Landing page roadmap**: removed the "Update to AASM Manual v3.0" card — that work is
  done and already listed under "What's New".

## v0.16.2 — 2026-07-26  *(landing page refreshed with current feature set)*

Content-only (public landing page at `/`). No scoring or pin change.

- **"What's New" section rewritten** to the current clinical highlights: AASM v3-compliant
  scoring, dual AHI (Rule 1A vs 4 %/CMS), ventilatory + hypoxic burden, clinical phenotypes
  (POSA / REM-predominant), the clinician-focused report, and arousal aetiology + OSAS/CSAS
  typing. Removed the now-obsolete "OAHI 3-point sweep" item (that feature was dropped from
  the report in v0.15.0).
- Hero badge → "AASM v3 · …"; AASM stat pill → "AASM v3-compliant"; tech stack now shows
  `psgscoring 0.12` (was 0.6). All copy in NL/FR/EN/DE.

## v0.16.1 — 2026-07-26  *(ventilatory burden made breath-based)*

Requires **psgscoring 0.12.1** (pin bumped). No report-code change — VB already renders
as a bounded `%` with reference ≤ 25 %.

- **Ventilatory burden is now breath-based** (psgscoring 0.12.1): the proportion of
  breaths whose peak amplitude is < 50 % of the eupneic baseline. v0.16.0 showed the
  time-fraction over the flow envelope, which over-counted inter-breath troughs and gave
  implausible values (e.g. 82.9 % on a severe recording). The displayed `%` is now the
  correct, bounded metric.

## v0.16.0 — 2026-07-26  *(VB recalibration + saturation bands + arousal-aetiology fix)*

Requires **psgscoring 0.12.0** (pin bumped). Three fixes found while verifying a real
v0.15.0 report; no change to AHI/OSAS numerics.

- **Ventilatory burden** is now the validated metric — **% of sleep with airflow < 50%
  of the eupneic baseline** (proportion of "small breaths"; AJRCCM 2023) — shown as a
  bounded `%` with reference **≤ 25%** in the PDF + web report (was an unbounded
  `%·min/h` value marked *experimental*, which produced implausible numbers, e.g. ~1074).
- **Time-in-saturation-bands table is populated.** psgscoring 0.12.0 now emits the band
  keys the table reads (`time_95_100_min` … `time_below_70_min`); previously all rows
  showed 0.0%. No YF code change — the reader already expected these keys.
- **Arousal-aetiology indices reconcile with the arousal index** (psgscoring 0.12.0):
  respiratory + spontaneous arousal indices now sum to the arousal index (were computed
  against a different TST); PLM arousal index reported as a subset of spontaneous.

## v0.15.0 — 2026-07-26  *(clinician-focused PDF report; AASM v3 enrichments; removals)*

Requires **psgscoring 0.11.0** (pin bumped). PDF report reworked for the clinician;
no change to scoring numerics.

**Added (PDF report)**
- **Auto-generated conclusion** (informational; never overrides the physician's manual
  diagnosis) — one structured sentence: severity + syndrome + phenotype + burden qualifiers.
- **Dual AHI** table — AASM v3 Rule 1A (≥3% desat *or* arousal) vs Rule 1B / CMS (≥4% desat),
  side by side with per-rule severity (from psgscoring `summary["ahi_dual"]`).
- **AASM AHI severity reference scale** (&lt;5 / 5–15 / 15–30 / &gt;30) under the AHI bar.
- **Page-1 phenotype line** (POSA / REM-predominant) and a **"Aandachtspunten" box**
  (descriptive attention points — explicitly *not* medical advice).
- **Arousal aetiology** as per-hour indices (respiratory / spontaneous / PLM arousal index).
- **Ventilatory burden** now labelled *experimental — scale not yet calibrated*.

**Removed (from the clinical PDF, per site request)**
- **Signal-quality & confidence-review section** (7b) and the page-1 warning banners
  (near-constantly graded "unusable"; still available in the web app).
- **OSAS severity profile** — the strict/standard/sensitive scoring-profile comparison
  table, the AHI-robustness interval, the OAHI 3-point confidence sweep, and the O-S-A-S
  severity-score table (not validated as severity instruments). ESS is kept.

**Fixed**
- KPI syndrome label + apnea-type breakdown line resolved to an empty summary
  (`results["respiratory"]` never existed → generic "SAS"); now read the canonical
  `pneumo["respiratory"]["summary"]`, so the header shows OSAS/CSAS correctly.

## v0.14.0 — 2026-07-25  *(clinical phenotypes + ventilatory burden in the report)*

- **New clinical findings in the report** (from psgscoring 0.10.0; pin `0.9.0 → 0.10.0`):
  - **Positional OSA (POSA)** and **REM-predominant OSA** phenotype flags — shown in
    the PDF (a "Clinical phenotypes" block) and the web report, with the supine /
    non-supine and REM / NREM AHI and, for POSA, positional-therapy candidacy. POSA
    needs a body-position channel; both render only when the criteria are met.
  - **Ventilatory burden** (%·min/h) shown next to the hypoxic burden — a
    cardiovascular-risk pair beyond the AHI. ⚠️ Scale to be calibrated against
    Labarca 2023; no reference range shown yet.
- 7 new NL/FR/EN/DE translation keys. **No AHI / OSAS-CSAS-grade change**; the new
  fields render conditionally (graceful when absent).

## v0.13.0 — 2026-07-25  *(arousal & RERA detection moved to psgscoring; multi-derivation arousals by default)*

- **Arousal & RERA detection now live in `psgscoring` (v0.9.0), not in
  YASAFlaskified.** `myproject/arousal_analysis.py` is now a thin compatibility
  shim that re-exports `psgscoring.arousal`; the detector code moved to the library
  so it is self-contained and versioned. Pin bumped `psgscoring[ml]==0.7.6 → 0.9.0`.
- **Arousals are now scored multi-derivation by default** (central + occipital +
  frontal, event-level union + EOG-reject) for clinical scoring — a more sensitive,
  more human-like operating point (a scorer scans the whole montage). Set
  `PSGSCORING_AROUSAL_DERIVATION=single` to restore single-channel behaviour.
- **Clinical impact:** the **AHI / OSAS-CSAS grade is unchanged** (arousals
  contribute no arousal-only events on the validation cohort; psgscoring's golden
  regression passes). The **arousal index in reports rises** (multi is more
  sensitive) — a deliberate, validated sensitivity-first choice. Validated on
  PSG-IPA (5 recordings × 12 scorers).
- No UI change; PDF/Excel/FHIR reports unchanged in structure.

## v0.12.8 — 2026-07-22  *(analysis history now distinguishes OSAS vs CSAS)*

- **The analysis-history list (`/results`) now shows the apnea *type* and the
  central component, not just a bare AHI.** Two columns were added between OAHI
  and Severity:
  - **Centr.** — the central apnea index (CAI, `central_index`, /h), so a
    central-driven study is visible at a glance.
  - **Type** — an **OSAS** / **CSAS** badge. A study is labelled **CSAS**
    (central-predominant) when the central events make up **≥ 50 % of the AHI**
    (AASM convention), otherwise **OSAS**; below AHI 5 no type is shown. The
    badge carries a tooltip with the full syndrome name.
- The **Severity** badge is now localised (`Mild` / `Matig` / `Ernstig` in NL,
  with FR/EN equivalents) instead of the raw English word, so a row reads e.g.
  *AHI 51.3 · OAHI 6.9 · Centr. 44.5 · **CSAS** · **Ernstig*** — an *Ernstig
  CSAS* at a glance, no longer indistinguishable from an obstructive study.
- Classification is a list-level heuristic in `_sas_type()` (`app.py`); the PDF
  report remains the source of truth for the full event breakdown. No scoring
  change; new NL/FR/EN i18n keys (`resp_type`, `osas`, `csas`, `central_ahi_*`,
  `osas_full`, `csas_full`); NL `sev_mild` label aligned to "Mild".
- **Terminology harmonised:** the Dutch conclusion/diagnosis texts for mild OSAS
  now read **"Mild OSAS"** instead of "Licht OSAS" (`STANDARD_CONCLUSIONS`,
  `concl_mild_title`/`concl_mild_body`, `dx_mild_osas`, and the arousal-latency
  note), matching the new history badge. FR ("léger") / EN ("mild") / DE
  ("leichtes") were already correct and are unchanged; the N1 sleep-stage label
  "Licht" (= light sleep) is a different concept and stays.

## v0.12.7 — 2026-07-22  *(fix: browser served a stale report from cache after re-analysis)*

- Follow-up to v0.12.6. Even with `no-cache` response headers, a browser that
  had **already** cached `/results/<job_id>/pdf` (from an earlier, pre-fix visit)
  kept serving the old attachment — a re-analysis reuses the same `job_id`, so
  the download URL was unchanged and the browser never re-fetched. Users saw the
  pre-fix report (e.g. a Cheyne-Stokes study with RDI=0) despite the server
  holding the corrected one.
- **Fix:** the PDF/Excel download links now carry a `?v=<results.json mtime>`
  cache-buster (`report_ver()` Jinja global). A re-analysis rewrites
  `results.json`, so the link changes and the browser fetches the fresh report.
  Server-side content was already correct; this makes the client always request
  it. No scoring change.

## v0.12.6 — 2026-07-22  *(fix: re-analysis served a stale cached report)*

- **A re-analysis now always yields the up-to-date PDF/Excel.** After
  re-analysing an existing study, the download could still hand back the
  *previous* report: the download URL (`/results/<job_id>/pdf`) is identical
  across re-analyses, so the browser served its cached copy, and the on-the-fly
  fallback only regenerated when the file was *missing* — not when it was
  *older than the fresh results*. Concretely, a study re-scored on psgscoring
  0.7.6 (e.g. a Cheyne-Stokes patient whose RDI/REM-NREM AHI were restored)
  could still download the pre-fix PDF.
- **Fix** (`app.py`): report downloads now (a) regenerate the PDF/Excel when the
  artifact is older than `{job_id}_results.json`, and (b) send
  `Cache-Control: no-cache, no-store, must-revalidate` so the browser always
  fetches the current file. `/psg` redirects to `/pdf` and is covered too.
- No scoring change; server-side results were already correct after re-analysis.

## v0.12.5 — 2026-07-22  *(psgscoring 0.7.6 — RERA/CSR + hypoxic-burden fixes)*

Bumps the pinned scoring library to **psgscoring 0.7.6** (`requirements.txt`,
`version.py`). No YASAFlaskified code change.

- **RDI/RERA now appear on Cheyne-Stokes reports.** psgscoring 0.7.6 fixes a bug
  where the RERA index, RDI and REM/NREM AHI were silently dropped from the
  respiratory summary on CSR-positive recordings — so the PDF/Excel reports
  showed a blank RDI for those patients. They now render correctly.
- **Hypoxic burden corrected on sensor-dropout recordings** (invalid in-sleep
  SpO2 samples excluded from the TST denominator; de Chazal `calcHB.m` reference).
- **No AHI / OSAS-severity change for any patient.** Validated on a real MESA
  A/B (16 recordings): `ahi_total` byte-identical, RERA restored on 9 CSR
  recordings, HB raised on 5 dropout recordings. Also includes psgscoring's
  output-preserving robustness hardening (graceful per-channel degradation).

## v0.12.4 — 2026-06-07  *(PDF epoch-example efficiency — inert in current reports)*

Code efficiency only — no behaviour or output change.

### Changed
- `generate_pdf_report.py` — `_build_epoch_examples` / `_plot_epoch_example` now read +
  load the EDF **once** (only the needed channels) instead of once per example event
  (~2.4× faster for that routine in isolation: 27.9 s → 11.6 s on a full-night MESA
  recording; byte-identical — same channels / sfreq / full `load_data`). A
  partial/cropped read was rejected because it changes the mixed-sample-rate
  upsampled-channel values.

  **Note:** the epoch-example panels are currently **disabled** at the call site
  (commented out since v0.8.22), so `_build_epoch_examples` is not invoked during
  report generation. This change therefore does **not** reduce actual
  report-generation time — it only takes effect if the panels are re-enabled.
  (The real per-recording speed-up in this version range is the scoring engine:
  psgscoring 0.7.2, bumped in v0.12.3.)

## v0.12.3 — 2026-06-07  *(bump psgscoring to 0.7.2)*

Dependency bump only — no UI, route, or behavior changes in
YASAFlaskified itself.

### Changed
- `requirements.txt` — pin `psgscoring[ml]==0.7.2` (was 0.6.1).
  Brings in: v0.6.2 dual AHI reporting (`ahi_incl_uncertain`, additive),
  v0.7.0 Tier-1 scoring-accuracy fixes (validated byte-identical on the
  clinical AASM-v3 path), v0.7.1 docs, and v0.7.2 a ~1.8–2.0× speed-up of
  the respiratory analysis (shared preprocessing across the 3-profile AHI
  interval — validated byte-identical on the MESA q7 holdout + PSG-IPA).
  Clinical scoring output is unchanged.

## v0.12.2 — 2026-06-03  *(bump psgscoring to 0.6.1)*

Dependency bump only — no UI, route, or behavior changes in
YASAFlaskified itself.

### Changed
- `requirements.txt` — pin `psgscoring[ml]==0.6.1` (was 0.6.0).
  v0.6.1 fixes two POOR-quality scoring crashes that could abort a
  patient's analysis: the Rule 1B `KeyError: 'stage'` (any recording
  with EEG arousal detection, where a stable-breathing-rejected
  hypopnea coincides with an arousal) and the ML `KeyError: 'type'`.
  Clinical AASM profiles are unchanged. See the psgscoring v0.6.1
  changelog for details.
- `myproject/version.py` — `PSGSCORING_VERSION` 0.6.0 → 0.6.1.

## v0.12.1 — 2026-05-28  *(harden bulk maintenance)*

Robustness fixes for the v0.12.0 bulk-maintenance feature. Behavior
only — no new UI, routes, or settings.

### Fixed
- `myproject/app.py` `dashboard()` — the archived-study count behind the
  "Show archived" toggle is now site-filtered. Site-managers no longer
  see other sites' archived studies reflected in the badge. The 300-study
  display cap is now applied *after* the site filter, so a site-manager
  sees up to 300 of their own studies instead of 300 raw files that then
  get filtered down.
- `myproject/app.py` `studies_bulk()` — bulk delete now counts studies
  with leftover file-removal errors as *skipped* rather than reporting
  them as deleted, matching the per-row `delete_study` behavior.
- `myproject/app.py` `studies_bulk()` — bulk archive verifies the study's
  results file exists before writing the `.archived` marker, preventing
  stray marker files for non-existent studies.

### Changed
- `myproject/version.py` — `__version__ = "0.12.1"`.

## v0.12.0 — 2026-05-27  *(dashboard bulk maintenance + archiving)*

Multi-select maintenance on the dashboard so admins and site-managers can
archive or delete several studies at once. Archiving uses a lightweight
marker file (`{job_id}.archived`) — reversible and without moving large
EDF files.

### Added
- `myproject/app.py` — archiving helpers `_archive_marker_path`,
  `_is_archived`, `_can_modify_job`, `_delete_job_files`, and a new
  `POST /studies/bulk` route (`studies_bulk`) gated to admin + site-manager,
  enforcing `_can_modify_job` per study with path-safety filtering.
  Supported actions: `archive`, `unarchive`, `delete`.
- `myproject/templates/dashboard.html` — checkbox column + select-all,
  a floating bulk-action bar, hidden bulk-submit form, per-row
  archive/restore button, and an "Show archived / Back to active" toggle
  with an archived-count badge. Selection logic is filter-aware (ignores
  rows hidden by search/severity/status filters).
- `myproject/i18n.py` — 17 maintenance/archiving keys in NL / FR / EN / DE.

### Changed
- `myproject/app.py` `dashboard()` — splits studies on the archive marker;
  `?archived=1` shows the archived view.
- `myproject/app.py` `results()` — archived studies are hidden from the
  history list.
- `myproject/app.py` `delete_study()` — refactored onto the shared
  `_can_modify_job` + `_delete_job_files` helpers.
- `myproject/version.py` — `__version__ = "0.12.0"`.

## v0.11.7 — 2026-05-23  *(fix header Upload link)*

### Fixed
- `myproject/templates/base.html` — the header "Upload" link sent
  authenticated admin / site-manager users to `/dashboard` (because `/`
  redirects them there) instead of the upload page. It now uses
  `url_for('upload_file')`. The "New analysis" button was already
  correct, so only the header was affected.

## v0.11.6 — 2026-05-14  *(faster EDF viewer start-up)*

### Changed
- `myproject/edf_api.py` — open EDF recordings with `preload=False`
  instead of `preload=True`. The first `/api/edf/<job>/info` call
  previously blocked 20–60 s on long PSGs while 1–2 GB loaded into RAM;
  per-epoch reads now pull only the visible 30 s slice (~1 MB from
  disk), dropping time-to-first-signal from ~30 s to ~1–2 s. The
  per-worker LRU cache still holds the raw object across requests, so
  navigation within a job avoids repeated file opens.

## v0.11.5 — 2026-05-14  *(hotfix — viewer constant clash)*

### Fixed
- `myproject/static/edf_viewer_v12.js` — production had been broken
  since v0.11.3: both `scorer_v12.js` and `edf_viewer_v12.js` declared a
  top-level `const STAGE_COLORS`. Because sibling `<script>` tags share
  one lexical scope, the second declaration threw "Identifier already
  declared" at parse time, so `EdfViewer` was never defined and the
  viewer / event-sidebar never initialised. The viewer copy is renamed
  `EDF_STAGE_COLORS`.

## v0.11.4 — 2026-05-14  *(hypnogram navigation + render perf)*

### Added
- `myproject/static/scorer_v12.js`, `myproject/templates/scorer_v12.html`
  — hypnogram navigation for long recordings: mouse-wheel horizontal
  scroll (Shift = 4×), Shift+←/→ = ±10 epochs (5 min), Ctrl+←/→ = jump
  to previous / next stage transition, Home / End = first / last epoch,
  a jump-to-epoch input (# + Enter), and stage-jump buttons (→ W,
  → N3, → R).

### Changed
- `myproject/static/scorer_v12.js` — `_draw()` throttled via
  `requestAnimationFrame` to coalesce redraws per frame (was laggy
  during key-repeat and drag on long recordings).
- `myproject/i18n.py` — full German entry added (was falling back to
  NL); new keys `kbd_jump10`, `kbd_jump_transition`.

### Fixed
- `myproject/static/scorer_v12.js` — scorer no longer reacts to
  W / 1 / 2 / 3 / R keys while focus is inside an input (added a focus
  guard).

## v0.11.3 — 2026-05-14  *(EDF browser improvements)*

### Added
- `myproject/static/edf_viewer_v12.js`,
  `myproject/templates/scorer_v12.html` — sleep-stage colour strip above
  the signal traces, jump-to-epoch input (# + Enter), N / P hotkeys for
  next / previous event in the active sidebar filter, and event-count
  badges on the sidebar filter buttons (auto-refreshed via a new
  `onEventsChanged` hook).

### Fixed
- `myproject/static/edf_viewer_v12.js` — multi-epoch time-axis tick
  labels now scale with the visible span (were hardcoded 0–30 s
  regardless of 2× / 5× / 10× zoom).

### Changed
- `myproject/i18n.py` — channel-panel strings (previously hardcoded
  Dutch) moved into the language dict; full German entry added; new key
  `kbd_next_prev_event` (NL / FR / EN / DE).

## v0.11.2 — 2026-05-12  *(frontpage content refresh)*

### Changed
- `myproject/templates/frontpage.html` — dropped the hard "AASM"
  claim in the hero (now generic "AASM-compliant scoring"), since the
  PDF generator still cites Berry 2020 / Manual 2.6 while v3.0 is the
  current edition; v3.0 work moved to a new roadmap section. Added a
  "What's new in v0.11" section (6 cards) and an "On the roadmap"
  section (6 cards: AZORG-YASA-2026-001 validation study, paper v36 at
  *Physiological Measurement*, MESA-SHHS external validation, FHIR
  export, AASM Manual v3.0, browser scorer / viewer), a work-in-progress
  chip in the hero, and nav links to both sections.
- `myproject/i18n.py` — +33 keys (1007 → 1040), all four languages.

## v0.11.1 — 2026-05-12  *(login redirect + credits trim)*

### Changed
- `myproject/app.py` — `GET /login` now redirects to `/` (the landing
  page already embeds the login form), so old bookmarks land on the new
  page; `POST /login` is unchanged.
- `myproject/templates/frontpage.html` — removed the "thanks to Raphael
  Vallat" box from the credits section.

## v0.11.0 — 2026-05-12  *(light-themed frontpage with embedded login)*

### Changed
- `myproject/templates/frontpage.html` — replaced the dark `/about`
  marketing page plus separate `/login` screen with a single
  light-themed landing page at `/`: hero with brand / tagline / stats
  beside an inline login card (flash messages render above the form), a
  language picker (NL / FR / EN / DE) in the top nav, 9 feature cards
  reflecting v0.10.x capabilities (per-channel signal quality, staging
  confidence, OAHI 3-point sweep / robustness grade), and tech-stack
  pills (psgscoring v0.6, LightGBM, ReportLab).
- `myproject/app.py` — `/` renders `frontpage.html` for unauthenticated
  visitors instead of redirecting to `/login`.
- `myproject/i18n.py` — +14 keys for the new hero copy and feature cards
  (991 → 1007), all four languages.

## v0.10.5 — 2026-05-12  *(template translation sweep)*

### Changed
- `myproject/i18n.py` plus six templates (`dashboard.html`, `index.html`,
  `report_editor.html`, `results_extended.html`, `scorer_v12.html`,
  `upload.html`) — final sweep of all 24 templates: 21 remaining
  hardcoded Dutch strings replaced with `t()` calls (upload-landing
  feature cards, "Mislukt" status badge, institution-name placeholder,
  partial-save warning, "no events" empty state, upload-flow JS
  messages). `i18n.py` 970 → 991 keys, all four languages. A focused
  Dutch-string detector then reported zero hits across every template.

## v0.10.4 — 2026-05-12  *(translate edit-report page)*

### Changed
- `myproject/templates/report_editor.html`, `myproject/i18n.py` —
  remaining Dutch in the edit-report page routed through `t()`:
  verification card, report-header card, logo upload / remove, diagnosis
  quick-add buttons, and the save-flow JS messages. `i18n.py` 942 → 970
  keys, all four languages.

## v0.10.3 — 2026-05-12  *(translate analysis workflow)*

### Changed
- `myproject/i18n.py` plus templates (`channel_select.html`, `index.html`,
  `job_status.html`, `report_editor.html`, `results_extended.html`,
  `scorer_v12.html`, `upload.html`) — channel-selection labels and
  adjacent screens (leg / position / snore / pulse / ECG channel labels
  and descriptions, upload card, job-status retry / timeout, the 15
  keyboard-shortcut rows, artifact-table headers) now flow through
  `t()`. `i18n.py` 887 → 942 keys, all four languages.

## v0.10.2 — 2026-05-12  *(full 4-language coverage; default English)*

### Changed
- `myproject/i18n.py` — 707 → 887 keys, now complete in NL / FR / EN / DE
  (one DE entry was missing). New keys cover error pages, admin-sites
  columns, dashboard buttons, channel-select ML help, base footer +
  session warning, the full `disclaimer.html` and `frontpage.html`
  marketing copy, and the PDF-report hardcoded NL strings.
- `myproject/app.py` — `DEFAULT_LANG` changed `"nl"` → `"en"` (affects
  new user / site defaults and the `session.get("lang", ...)` fallbacks
  in 50+ flash sites); `STANDARD_CONCLUSIONS` gains German entries;
  flash messages and the 413 "file too large" response routed through
  i18n instead of mixing Dutch fragments.
- `myproject/generate_pdf_report.py`, `myproject/generate_psg_report.py`,
  `myproject/tasks.py`, and templates (`404`, `500`, `admin_sites`,
  `base`, `channel_select`, `dashboard`, `disclaimer`, `frontpage`) —
  hardcoded strings moved into the language dict.

## v0.10.1 — 2026-05-11  *(fix config.json load path)*

### Fixed
- `myproject/app.py` — on a fresh deploy the admin login was always
  `admin/admin` instead of the random password `deploy.sh` prints:
  `deploy.sh` writes the generated SECRET_KEY / ADMIN_PASSWORD to
  `/data/slaapkliniek/instance/config.json`, but `app.py` opened a
  relative `config.json` from the working dir and only saw the baked-in
  template with `VERANDER_DIT_*` placeholders, silently falling through
  to defaults. `config.json` is now resolved in order:
  (1) `/data/slaapkliniek/instance/config.json`,
  (2) `instance/config.json` (local dev),
  (3) the baked-in template — and a template whose `ADMIN_PASSWORD`
  still starts with `VERANDER_DIT_` is discarded in favour of env vars /
  safe defaults. Existing installs keep their current admin password
  (the bcrypt hash in `users.db` is not reset).

## v0.10.0 — 2026-05-10  *(UI overhaul)*

End-to-end visual / interaction refresh aimed at clinical density.
Five interlocking changes; backward-compatible with all v0.9.x routes
and JSON contracts. Backup of pre-v0.10.0 source tree:
`/home/bart/CODE/YASAFlaskified.backup-pre-v010-…`.

### Added
- `myproject/static/styles_v010.css` — typographic + density layer
  loaded on top of Bootstrap 5. Defines:
  * Display font Newsreader (serif), body IBM Plex Sans, mono IBM Plex
    Mono for tabular numerics.
  * `card-quiet` variant: hairline border + 2 px accent rule, no
    shadow, in navy / ochre / claret / teal.
  * `mono-letter` chip used in card headers in place of emoji.
  * `sev-strip` component: 64 px AASM severity strip (Normal / Mild /
    Moderate / Severe) with cut-off ticks at 5 / 15 / 30 /h and a
    triangular marker on the patient value.
  * Auto-detect summary table (channel-select page).
  * Visual focus ring (a11y).
  * `@media print` stylesheet for clinical paper print-out.
  * `.presentation-mode` body class for projected meetings.

### Changed
- `myproject/templates/base.html` — Newsreader / Plex Sans / Plex Mono
  font imports; navbar emoji 🌐 replaced by `bi-globe2`; new
  presentation-toggle button (`bi-display`) + keyboard-help button
  (`bi-question-circle`) in the navbar; global keyboard handler
  (`n`, `g d`, `g h`, `/`, `j` / `k`, `Enter`, `p`, `?`, `Esc`);
  full-screen kbd-help overlay.
- `myproject/templates/dashboard.html` — header gets a monogram
  letter `D`; stat-cards collapsed from 4 to 3 quiet cards with
  monogram letters; AHI / ODI / PLMi pills replaced by `sev_strip`
  macro (severity bar + tabular-numeric value); table tagged
  `kbd-nav-table` for j / k navigation.
- `myproject/templates/channel_select.html` — auto-detected channel
  summary added at the top; existing EEG / EOG / EMG / Extra-EEG /
  Pneumo cards collapsed under a single "Override manually" toggle;
  card-headers use `mono-letter` instead of emoji; `card-quiet`
  variants in navy / ochre / claret / teal; submit button uses
  `bi-play-fill`.
- `myproject/i18n.py` — keys for the keyboard-help overlay
  (NL / FR / EN / DE), the auto-detect summary labels, and the
  dashboard stat-card labels.
- `myproject/version.py` — `__version__ = "0.10.0"`.

### Visual deltas a clinical user notices
1. Numerics in the dashboard table are now monospaced and aligned —
   AHI 8.1 vs 53.98 line up correctly.
2. Each AHI / ODI / PLMi cell is a coloured strip with the value
   marker at the patient's position; severity is visible at-a-glance
   without reading any pill.
3. Channel-select shows one auto-detected summary instead of four
   colourful cards; one click on "Override manually" opens the old
   per-channel layout when needed.
4. `Ctrl/Cmd-P` (browser print) now produces a clinical-dossier
   layout (no nav, A4 margins, B/W badges, severity prefixes).
5. `?` from any list page shows the shortcut help; `j`/`k` navigates
   table rows, `Enter` opens the selected study.

## v0.9.9 — 2026-05-10

UI exposure of the ML arousal re-classifier shipped in v0.9.8.

### Added
- Checkbox "Use ML arousal re-classifier (preview)" on the
  channel-select page (NL/FR/EN/DE), right under the scoring
  profile dropdown. Decoupled from the scoring profile because
  arousal detection is a separate concern from respiratory event
  scoring.

### Changed
- `myproject/templates/channel_select.html` — added the checkbox
  block + i18n hint string.
- `myproject/i18n.py` — `arousal_lgbm_label` and
  `arousal_lgbm_hint` keys (NL/FR/EN/DE).
- `myproject/app.py` — channel-select POST handler stores
  `arousal_lgbm` boolean in the per-job config.
- `myproject/tasks.py` — RQ worker reads `cfg["arousal_lgbm"]`
  and sets the `YASAFLASKIFIED_AROUSAL_LGBM` env var around the
  `run_pneumo_analysis` call (with try/finally restore so the
  flag does not leak across jobs in the same worker process).
- `myproject/version.py` — `__version__ = "0.9.9"`.

## v0.9.8 — 2026-05-10

Optional candidate-level LightGBM EEG-arousal re-classifier shipped
behind the `YASAFLASKIFIED_AROUSAL_LGBM` env-var feature flag. With
the flag unset the detector behaves bit-identically to v0.8.40
rule-based; with the flag set to `1` the candidate stage runs at
permissive thresholds (ratio=1.2, abrupt=1.0) and surviving
candidates are filtered by a LightGBM model trained on MESA
q∈{5,6} (n_subj=653, n_candidates=562k) at probability threshold
`AROUSAL_LGBM_THRESHOLD` (default `0.60`). On the q=7 honest
holdout the hybrid achieves Pearson r 0.66 between automatic and
NSRR-scored arousal-indices (vs 0.08 rule-based) and reduces
|Δn_arousals| from 71 to 45. Cross-cohort validation on PSG-IPA
(no retraining) gives Pearson r 0.84 between algorithmic and
scorer-mean AI across 60 (recording, scorer) cells. See paper v37
§5.5 + Online Supplement §S7.5 for full results.

### Changed
- `myproject/arousal_analysis.py` — added LGBM helper block,
  feature extraction (50 features per candidate), filter wrapper,
  summary recomputation, and dispatch in `detect_arousals`.
  Backward-compat preserved: env var unset = bit-identical to
  v0.8.40 rule-based output.
- `myproject/version.py` — `__version__ = "0.9.8"`.

### Added
- `myproject/data/arousal_classifier_v3.txt` — bundled MESA-trained
  LightGBM model (1.7 MB).

## v0.9.7 — 2026-05-05

i18n strings updated to reflect the v0.6.0 architecture: the
`analysis_description` and `pdf_disc_auto` keys (NL/FR/EN/DE) now
distinguish between YASA AI sleep staging (the historical
"LightGBM, ~85% epoch agreement" credit, attributed to
Vallat \& Walker 2021) and the new v0.6.0 LightGBM
candidate-classifier on `mesa_shhs` (psgscoring v0.6, paper v35).
The fixed `5–10 min` analysis-duration claim was relaxed to
`3–10 min` since the actual time depends on profile choice.
HETZNER_CURRENT_STATE.md cleaned of stale `APP_VERSION=0.8.39`
follow-up (resolved since 2026-05-03 deploys) and updated to
reflect `psgscoring[ml]==0.6.0` pin.

### Changed
- `myproject/i18n.py` — NL/FR/EN/DE for `analysis_description`,
  `analysis_duration`, `pdf_disc_auto`. Header version banner
  updated to v0.9.6 → v0.9.7.
- `HETZNER_CURRENT_STATE.md` — current-state table cleanup,
  stale APP_VERSION follow-up moved to Resolved section,
  example deploy commands updated to v0.9.6+.

## v0.9.6 — 2026-05-05

UI annotation for ML-augmented profiles. The scoring-profile
dropdown on the channel-select page now appends a "🤖 ML" suffix to
profile labels whose `post_processing.ml_classifier_path` is set,
making it visible at a glance which profiles run the
`psgscoring`~v0.6.0 candidate-level LightGBM re-classifier (default
only `mesa_shhs`). A short legend below the dropdown explains the
marker. No changes to scoring behaviour or routine clinical output.

### Changed
- `myproject/app.py` — appends `🤖 ML` to `display_name` for profiles
  with an ML classifier configured.
- `myproject/templates/channel_select.html` — added one-line legend
  beneath the profile select.

## v0.9.5 — 2026-05-05

Bumped `psgscoring` pin from 0.5.1 to **0.6.0** with the new `[ml]`
extra (installs `lightgbm>=3.0`). The 0.6.0 release adds an optional
LightGBM candidate-level re-classifier that ships in the package and
is consumed by the `mesa_shhs` profile by default; clinical profiles
(used by every routine YASAFlaskified analysis) leave the
classifier disabled and remain bit-identical to v0.5.x output.

### Changed
- `requirements.txt` — `psgscoring==0.5.1` → `psgscoring[ml]==0.6.0`
- `myproject/version.py` — `__version__` 0.9.4 → 0.9.5;
  `PSGSCORING_VERSION` 0.5.1 → 0.6.0
- `INSTALL.md`, `HETZNER_CURRENT_STATE.md` — version references updated

## v0.9.4 — 2026-05-03

Bumped `psgscoring` pin from 0.4.3 to **0.5.1**. The 0.5.x series adds
profile-tunable thresholds and metadata corrections to the `mesa_shhs`
profile (paper v34 §S5.6 + research-driven additions); see the
`psgscoring` CHANGELOG for details. PSG-IPA reproducibility 10/10 pass
on both versions; clinical AHI for routine recordings is unchanged
because clinical profiles (`aasm_v3_*`, `aasm_v2_rec`, `aasm_v1_rec`,
`cms_medicare`, `chicago_1999`) keep their released defaults.

### Changed
- `requirements.txt` — `psgscoring==0.4.3` → `psgscoring==0.5.1`
- `myproject/version.py` — `__version__` 0.9.3 → 0.9.4;
  `PSGSCORING_VERSION` 0.4.3 → 0.5.1
- `INSTALL.md`, `HETZNER_CURRENT_STATE.md` — version references updated

## v0.9.3 — 2026-05-01

### Changed
- Bumped `psgscoring` pin from `0.4.2` (bundled patch) to `0.4.3` from PyPI.
  No public-API changes; psgscoring v0.4.3 ships the paper-faithful
  `validate_psgipa.py` rewrite and a reproducibility regression test.
- `version.py` updated to `0.9.3` and `PSGSCORING_VERSION = "0.4.3"`
  (was missed in the v0.9.2 and earlier v0.9.3 git tags; v0.9.3 tag
  re-pointed at this commit).

### Notes
- INSTALL.md: 4 references to `psgscoring 0.4.2` updated to `0.4.3`.
- Production deployed to Hetzner on 2026-05-01.

---

## v0.9.2 — 2026-05-01

### Removed
- **Bundled `myproject/psgscoring/`** (8.1k LOC, 20 files). psgscoring
  is now installed from PyPI via `requirements.txt`. Bumps to newer
  psgscoring releases are now a one-line change.

### Fixed
- **CI on `main` was red since 2026-04-12** because ruff flagged 429
  issues in `myproject/`. Three were real bugs:
  - `generate_psg_report.py:985,1001` — undefined `site` and `pneumo`
    should be `institution` and `pneumo_results`; would crash code
    paths that hit them
  - `generate_pdf_report.py:116,123` — loop variable `t` shadowed the
    imported translation function `t` in `_sev` and `_sev_clr`,
    silently breaking translations in those branches
- The remaining 426 issues were stylistic / import-sort / whitespace;
  ruff `--fix` handled 90, the rest are now suppressed by a pragmatic
  ruff config (`select = ["F", "W", "I"]`, ignoring opinionated
  pycodestyle / bugbear / pyupgrade rules on this established
  scientific-Flask codebase).

### Added
- New smoke test `myproject/tests/test_psgscoring_from_pypi.py` that
  asserts `import psgscoring` does not resolve under `myproject/psgscoring/`
  and that the loaded version meets the requirements.txt minimum.
- CI workflow (`.github/workflows/ci.yml`): ruff lint + pytest +
  Docker build smoke.
- Repo hygiene: `.env.example`, `Makefile`, `pyproject.toml` with
  ruff/pytest config.
- `pythonpath = ["myproject"]` in pytest config so top-level imports
  resolve when pytest runs from the repo root.

### Deferred
- 27 duplicate translation keys (F601) in `myproject/i18n.py` silently
  shadow earlier values; deferred with per-file ignore + TODO comment.
  Deduplication needs care to preserve the right variant.

---

## v0.9.1 — 2026-04-29

### Fixed
- **Blank page in PDF** between "Visueel overzicht" and "1. Slaaparchitectuur"
  caused by an explicit `PageBreak()` after the position legend. With short
  recordings (e.g., PSG-IPA SN3 ~6h) section 1 fits on the visual overview
  page, and the explicit page break forced an empty intermediate page.
  Replaced with `sp(0.3)` to let ReportLab handle pagination naturally.

### Changed
- Bundled psgscoring 0.3.1 → 0.4.2 (profile-aware local baseline validation)
- Removed confidence-sweep card from results page (clinically misleading)
- Removed confidence-sweep table from PDF report

### Notes
- AHI Interval banner on page 1 retained (profile-comparison sweep)
- PSG-IPA aggregate validation: r=0.994, κ=0.800, F1 SN3=0.860

## v0.9.0 — April 2026 (transitional)

### Added
- **3-point confidence-sweep card** on results page (DEPRECATED in v0.9.1):
  showed clinically misleading discrete values for borderline patients.
- Bundled psgscoring 0.3.1 → 0.4.1 (parameter integration fix)

# Changelog — YASAFlaskified

## v0.8.39 (2026-04-19)

### Dashboard
- Added 3 new columns after AHI in Patiëntenoverzicht:
  - **Grade** (A/B/C): AHI robustness from confidence interval
  - **ODI₃**: Oxygen Desaturation Index 3%
  - **PLMi**: Periodic Limb Movement Index
- FHD-compatible 12-column layout with compact padding
- Backward compatible: shows "—" if backend data unavailable
- Backend wiring for s.grade/s.odi/s.plmi: TBD separate commit

### i18n
- Added 4 new keys × 4 languages (NL/FR/EN/DE):
  - grade, grade_tooltip, odi_tooltip, plmi_tooltip
- Uses _DASHBOARD_V0839 sub-dict pattern consistent with _PDF_KEYS

All notable changes documented per [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.8.37] — April 2026

### Added — Page 1 robustness + OSAS score fix
- **AHI Robustness grade on page 1**: compact coloured banner showing `AHI Interval: [strict – standard – sensitive] /u · Robustness: A/B/C` directly below the confidence warning. Green (A), amber (B), red (C). Clinician sees at a glance whether diagnosis is robust.
- **OSAS code without ESS**: when ESS is not provided, the OSAS code now shows `O0S2A0S— (subtotaal: 2/9, ESS niet ingevuld)` instead of the misleading `(totaal: 2/12)`. New i18n key `ESS not provided` in NL/FR/EN/DE.
- Epoch signal examples (section 8e) remain disabled pending alignment fix.

### Changed
- psgscoring bumped to v0.2.951
- All version strings updated to v0.8.37

## [0.8.36] — April 2026

### Added — PDF report Medatec parity + OSAS severity score
- **Position × stage cross-table**: respiratory events by NREM/REM × supine/non-supine with sleep time, event count, mean duration, and AHI per cell; auto-detects supine-dominant and REM-dominant OSA
- **Snoring cross-table**: snoring percentage by position × stage (NREM-rug, NREM-zij, REM-rug, REM-zij)
- **Stage-specific sleep latencies**: N1, N2, N3, REM latency table in sleep architecture section
- **SpO₂ saturation bands**: time in 95–100%, 90–95%, 80–90%, 70–80%, <70% ranges
- **OSAS severity profile**: multi-dimensional O-S-A-S score (Oxygen deficit / Sleep disruption / Apnea frequency / Symptoms) with modifiers (p=positional, r=REM-dominant, c=central component). ESS input for symptom dimension.
- **`pdf_report_additions.py`** (748 lines, 14 functions): standalone module, also usable outside PDF (`compute_osas_score()`, `compute_position_stage_crosstab()`, `compute_stage_latencies()`)
- ~37 new i18n keys (NL/FR/EN/DE)

### Changed
- psgscoring bumped to v0.2.93
- All version strings updated to v0.8.36

## [0.8.35] — April 2026

### Added — Hypoxic burden + post-processing
- **Hypoxic burden** (Azarbarzin et al., AJRCCM 2019): per-event SpO₂ desaturation area, normalised %·min/h — displayed in PDF SpO₂ section
- **CSR-aware central reclassification**: CSR-flagged obstructive/mixed events → reclassified as central (addresses cardiac pulsation artifact in heart failure)
- **Mixed apnea decomposition**: central portion ≥10 s → reclassified as central; reports `cai_decomposed`
- **Central instability index**: quantifies profile-dependent O/C uncertainty (0–1 scale)
- **Bundled psgscoring v0.2.92** with 42 public exports (was 38)
- **New postprocess.py module** in psgscoring (CSR reclassification + mixed decomposition + CII)

### Changed
- Pipeline: 11 steps (was 9) — added step 10 (hypoxic burden) and step 11 (post-processing)
- PDF report: SpO₂ table now includes hypoxic burden row with clinical reference (<20 %·min/h)
- PDF report: corrections table shows CSR reclassification and mixed decomposition counts
- All version strings updated to v0.8.35 across all files

## [0.8.34] — April 2026

### Added — External validation + AHI confidence interval
- **PSG-IPA validation**: bias +1.6/h, r=0.990, 60 scorer sessions
- **iSLEEPS validation**: n=39 stroke patients, MAE 3.3/h normal/mild
- **ECG-derived effort**: TECG method (Berry 2019) + spectral classifier
- **Calibration module**: scorer-adaptive parameter optimisation (experimental)
- Bundled psgscoring v0.2.91

## [0.8.33] — April 2026

### Fixed — FHIR export + PDF event plots
- **FHIR: sleep stage values were minutes, not percentages** — N1/N2/N3/REM observations now correctly exported as % of TST (e.g., REM=140.5 min → 39.9%)
- **PDF event plots: SpO2 label** — was literal HTML `SpO<sub>2</sub>` in matplotlib; now uses LaTeX `$SpO_2$`
- **PDF event plots: artefact-resistant scaling** — replaced P1/P99 with median ± 4×MAD; prevents artefact spikes from hiding flow reductions
- **PDF event plots: detection channel highlighted** — thicker line + ◀ marker on the channel where the event was actually detected (thermistor for apnea, nasal pressure for hypopnea); detection channel name shown in title
- 47 tests passing, 619 i18n keys

## [0.8.31] — April 2026

### Fixed — PDF report bugs
- **Removed duplicate executive summary** that overlapped with existing KPI boxes on page 1
- **Fixed SpO2 subscript rendering**: Unicode ₂ → ReportLab `<sub>2</sub>` (was rendering as black boxes ■)
- **Fixed stage transition matrix**: was showing all dots — now correctly reads `timeline[i]["stage"]` instead of the raw dict
- **Fixed signal quality table**: field name mismatch (`quality_grade` vs `quality`, `flat_pct` vs `flatline_pct`) — was showing "?" for all channels
- 619 i18n keys, 47 tests passing

## [0.8.30] — April 2026

### Improved — Clinical PDF report layout (AASM-compliant)
- **Executive Summary box** on page 1: AHI (large font, severity-colored), OAHI, CAI, SpO₂ baseline/nadir, arousal index, PLMI — all critical numbers visible at a glance
- **Sleep stage transition matrix**: compact 5×5 table (W/N1/N2/N3/R) with transition counts after sleep architecture
- **HR/ECG summary section** (§10c): mean/min/max HR, bradycardia/tachycardia episodes
- **Spacing reduction**: 40–60% less whitespace for denser clinician-friendly layout

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
- **Scoring profile in AHI classification bar**: PDF now shows `Profile: Standard (AASM)` alongside AHI/OAHI values
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
- Footer: referenties YASA, psgscoring, AASM
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

**Peak signal excursion detection (AASM conformiteit):**
- AASM definieert hypopnea als "peak signal excursions drop by ≥30%"
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
- **PLM:** full AASM rewrite (amplitude threshold, bilateral merge, respiratory exclusion)
- **EDF+** export with scoring annotations
- Multi-language (NL/FR/EN) with 186+ translation keys via `i18n.py`
- Admin dashboard: user management, role-based menus
- Multi-site Docker architecture with Nginx Proxy Manager support

### [0.3.0] — v7: Pneumological Extension

- Channel selection UI (EEG, EOG, EMG)
- Apnoea/hypopnoea detection (AASM basis), AHI severity classification
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
