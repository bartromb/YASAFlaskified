# Medical and Clinical Disclaimer

**YASAFlaskified** — Open-source web platform for automated polysomnography analysis  
Copyright (c) 2024–2026 Bart Rombaut / Slaapkliniek AZORG  
https://github.com/bartromb/YASAFlaskified

---

## 1. Research Software — Not a Medical Device

YASAFlaskified is **research software**. It is intended exclusively for use by
qualified professionals (physicians, researchers, registered polysomnographic
technologists, or biomedical engineers) in a **research or clinical research
context**.

This software has **not** been evaluated, cleared, or approved by any
regulatory authority as a medical device, including but not limited to:

- The European Union Medical Device Regulation (EU MDR 2017/745)
- The U.S. Food and Drug Administration (FDA 21 CFR Part 820 / 510(k))
- Any equivalent national or regional medical device framework

It does **not** carry a CE mark, FDA clearance, or any equivalent certification.

---

## 2. Not a Substitute for Clinical Judgement

The computed indices produced by this platform — including but not limited to
the Apnoea-Hypopnoea Index (AHI), Obstructive AHI (OAHI), Oxygen Desaturation
Index (ODI), Periodic Limb Movement Index (PLMI), arousal index, and
Respiratory Disturbance Index (RDI) — are **research-grade estimates**. They
must be:

- Reviewed by a qualified, licensed clinician before any diagnostic or
  therapeutic decision is made.
- Validated against manual polysomnographic scoring by a registered
  polysomnographic technologist (RPSGT) for any clinical application.
- Interpreted in the context of the full clinical picture, patient history,
  and concurrent PSG signals.

**Sleep staging** is performed by YASA's automated LightGBM model, which
achieves approximately 85% epoch-level agreement with RPSGT scoring in
validation datasets. This level of agreement is suitable for research
purposes but does not meet the standard for unsupervised clinical use.
All automated hypnograms should be reviewed and corrected by a qualified
scorer before generating clinical reports.

**This platform does not provide medical diagnoses, treatment
recommendations, or any form of clinical advice.**

---

## 3. Known Limitations

Users should be aware of the following limitations that may affect scoring
accuracy:

| Condition | Effect |
|-----------|--------|
| Mouth-breathing | Reduced nasal flow → hypopnoea under-detection or false positives |
| Poor RIP-belt contact | Unreliable effort signals → apnoea type misclassification |
| Very high AHI (> 60 /h) | SpO₂ cross-contamination between consecutive events |
| Cheyne-Stokes respiration | Decrescendo phases may be scored as hypopnoeas |
| Signal dropout / sensor displacement | Post-gap recovery ramp may be scored as event |
| Paediatric recordings | Not validated for patients under 18 years of age |
| Non-AASM sensor configurations | Results may deviate from manual AASM 2.6 scoring |
| Automated sleep staging | ~85% epoch agreement; REM misclassification possible in OSAS |
| Artefact-heavy recordings | Artefact detection is automated; manual review recommended |

A pilot validation study comparing YASAFlaskified output against consensus
RPSGT scoring (target n = 50) is in preparation. Until published, all results
should be treated as provisional research estimates.

---

## 4. Data Privacy and Security

- YASAFlaskified is designed for use with **anonymised or pseudonymised** EDF
  recordings. Do not upload identifiable patient data to any publicly
  accessible instance without appropriate institutional approval and patient
  consent in accordance with GDPR (EU) 2016/679 or applicable local law.
- The operators of any deployed instance are responsible for ensuring
  compliance with applicable data protection regulations.
- The live instance at [slaapkliniek.be](https://slaapkliniek.be) is operated
  by Slaapkliniek AZORG (Aalst, Belgium) under Belgian and EU privacy law.
  Access is restricted to registered researchers with accepted data processing
  agreements.

---

## 5. No Warranty

This software is provided **"as is"**, without warranty of any kind, express
or implied, including but not limited to the warranties of merchantability,
fitness for a particular purpose, and non-infringement.

---

## 6. Limitation of Liability

To the fullest extent permitted by applicable law, in no event shall the
authors, contributors, or Slaapkliniek AZORG be liable for any direct,
indirect, incidental, special, exemplary, or consequential damages, including
but not limited to:

- Patient harm or adverse clinical outcomes
- Diagnostic errors or missed diagnoses
- Loss of data or corrupted results
- Breach of patient privacy or data protection violations
- Business interruption or financial loss

arising from the use of, or inability to use, this software — even if advised
of the possibility of such damages.

---

## 7. User Responsibility

By deploying or using YASAFlaskified, the user confirms that they:

1. Are a qualified professional with appropriate training in sleep medicine,
   polysomnography, or biomedical engineering.
2. Will not use the output of this platform as the sole basis for any clinical
   decision without independent clinical review.
3. Accept full responsibility for validating the platform's output in their
   specific recording environment, patient population, and clinical workflow.
4. Will comply with all applicable local laws and regulations regarding the
   use of software in medical and research settings, including data protection
   regulations (GDPR or equivalent).
5. Will not deploy this platform as a standalone diagnostic tool without
   appropriate institutional oversight and ethical approval where required.

---

## 8. Third-Party Components

YASAFlaskified builds on the following open-source projects, each with their
own licences and disclaimers:

- **YASA** (Raphaël Vallat / Matthew P. Walker) — BSD 3-Clause —
  https://github.com/raphaelvallat/yasa
- **MNE-Python** — BSD 3-Clause — https://mne.tools
- **Flask** — BSD 3-Clause — https://flask.palletsprojects.com
- **NumPy / SciPy** — BSD — https://numpy.org / https://scipy.org
- **psgscoring** (Bart Rombaut) — BSD 3-Clause —
  https://github.com/bartromb/psgscoring

The authors of these upstream projects bear no responsibility for
YASAFlaskified's use in clinical or research settings.

---

## 9. Contact

For questions, bug reports, or validation data:

- GitHub Issues: https://github.com/bartromb/YASAFlaskified/issues
- Clinical context: Slaapkliniek AZORG, Aalst, Belgium
- Live instance: https://www.slaapkliniek.be

---

*Last updated: 2026 — YASAFlaskified v0.8.23*
