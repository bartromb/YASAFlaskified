# YASAFlaskified — Roadmap

## Current: v0.8.37 (April 2026)

**Production-ready:**
- AASM 2.6 respiratory scoring with 6 over-counting + 6 under-counting corrections
- ECG-derived effort classification (TECG Berry 2019 + spectral classifier) for central/obstructive differentiation
- Hilbert phase-angle effort classification, K-complex exclusion
- CVR arousal confidence boost, patient-specific baseline anchoring
- Optional LightGBM confidence calibration (framework ready, model pending)
- 8 parallel RQ workers, multilingual reports (NL/FR/EN/DE)
- Interactive EDF browser, manual scoring editor
- psgscoring v0.2.951 (BSD-3, PyPI)

---

## v0.9 — Validation & Calibration (Q2 2026)

- [ ] Train LightGBM confidence model on AZORG cohort (target n=200)
- [ ] Formal pilot validation study (n=50, vs. RPSGT consensus)
- [ ] RERA scoring improvement: flow-limitation + phase-angle combined
- [ ] Ambulatory type III PSG: improved TST proxy via actigraphy fusion
- [ ] Expand unit tests to 200+
- [ ] Property-based testing (Hypothesis framework)
- [ ] External validation on SHHS/MESA

---

## v1.0 — Stable Release (Q3 2026)

- [ ] Stable public API with semantic versioning
- [ ] PyPI publication of `psgscoring`
- [ ] Zenodo DOI for academic citation
- [ ] CE-marking preparation documentation (MDR Class IIa)
- [ ] PostgreSQL migration (from SQLite) for production scale
- [ ] Kubernetes deployment option

---

## v1.x — Clinical Integration

- [ ] Bidirectional FHIR endpoint (receive orders, send results)
- [ ] HL7v2 ADT/ORU support for legacy EPD systems
- [ ] Customisable PDF templates per site
- [ ] Email notifications on analysis completion
- [ ] Population analytics dashboard (AHI trends, cohort statistics)

---

*© 2024–2026 Bart Rombaut — Slaapkliniek AZORG — www.slaapkliniek.be*
