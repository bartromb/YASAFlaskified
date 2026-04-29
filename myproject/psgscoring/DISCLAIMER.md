# Medical and Clinical Disclaimer

**psgscoring** — Open-source AASM 2.6-compliant respiratory scoring library
Copyright (c) 2024–2026 Bart Rombaut, Briek Rombaut, Cedric Rombaut
https://github.com/bartromb/psgscoring

---

## 1. Research Software — Not a Medical Device

`psgscoring` is **research software**. It is intended exclusively for use by
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

The computed indices produced by this library — including but not limited to
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

---

## 3. No Warranty

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 4. Intended Use

`psgscoring` is designed for:

- Academic sleep research
- Algorithm development and benchmarking
- Clinical research under ethics committee approval
- Educational purposes in sleep medicine training

It is **not** designed for:

- Standalone clinical diagnosis without expert review
- Automated treatment decisions
- Unsupervised patient screening programmes
- Any setting where the output directly determines patient care without
  clinician oversight

---

## 5. Validation Status

External validation on the PSG-IPA dataset (PhysioNet, 5 recordings,
47 independent scorer sessions) demonstrated mean |ΔAHI| = 1.9/h and
severity concordance of 4/5 (80%). A formal single-centre validation
study (AZORG-YASA-2026-001, n≥50) is in preparation. Until peer-reviewed
validation results are published, all outputs should be treated as
**preliminary** and verified by a qualified clinician.

---

*Last updated: April 2026 — psgscoring v0.2.951*
