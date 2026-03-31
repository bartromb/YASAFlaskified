"""
psgscoring.classify
===================
AASM 2.6 apnea-type classification: obstructive / central / mixed.

v0.8.11 additions
-----------------
- Phase angle (Hilbert transform) on thorax/abdomen instantaneous phase →
  continuous asynchrony in degrees. >45° during flow limitation → obstructive
  with high confidence, largely eliminating Rule-6 borderline defaults.
- LightGBM confidence calibration (optional): if a pre-trained model is
  available at ``LGBM_MODEL_PATH``, per-event features are fed to the model
  for a data-driven confidence score (0–1). Falls back to rule-based when the
  model is unavailable.

Dependencies: numpy, scipy, psgscoring.constants, psgscoring.utils
Optional:     lightgbm (confidence calibration only)
"""

from __future__ import annotations
import logging
import os
import numpy as np
from scipy.stats import pearsonr
from scipy.signal import hilbert

from .constants import EFFORT_ABSENT_RATIO, EFFORT_PRESENT_RATIO
from .utils import safe_r

logger = logging.getLogger("psgscoring.classify")

# ---------------------------------------------------------------------------
# LightGBM confidence calibration (optional)
# ---------------------------------------------------------------------------

# Set PSGSCORING_LGBM_MODEL to an absolute path to enable calibration.
# The model must accept 10 features in this order (see _extract_lgbm_features).
LGBM_MODEL_PATH: str | None = os.environ.get("PSGSCORING_LGBM_MODEL", None)
_lgbm_model = None   # loaded on first use


def _load_lgbm_model():
    """Load LightGBM model once, cache in module-level variable."""
    global _lgbm_model
    if _lgbm_model is not None or LGBM_MODEL_PATH is None:
        return _lgbm_model
    try:
        import lightgbm as lgb
        _lgbm_model = lgb.Booster(model_file=LGBM_MODEL_PATH)
        logger.info("LightGBM confidence model loaded from %s", LGBM_MODEL_PATH)
    except Exception as e:
        logger.warning("LightGBM model load failed (%s) — using rule-based confidence", e)
        _lgbm_model = None
    return _lgbm_model


def _extract_lgbm_features(
    effort_ratio: float,
    raw_var_ratio: float,
    paradox_corr: float | None,
    first_ratio: float,
    second_ratio: float,
    quarter_efforts: list[float],
    phase_angle_deg: float | None,
    duration_s: float,
    rule_idx: int,
) -> list[float]:
    """
    Extract 10 numeric features for the LightGBM confidence model.

    Feature order must match the training schema exactly.
    """
    return [
        float(effort_ratio),
        float(raw_var_ratio),
        float(paradox_corr) if paradox_corr is not None else 0.0,
        float(first_ratio),
        float(second_ratio),
        float(np.mean(quarter_efforts)) if quarter_efforts else 0.0,
        float(np.std(quarter_efforts))  if quarter_efforts else 0.0,
        float(phase_angle_deg) if phase_angle_deg is not None else 0.0,
        float(duration_s),
        float(rule_idx),   # which rule fired (1–6)
    ]


def _lgbm_confidence(features: list[float]) -> float | None:
    """Return LightGBM confidence or None if model unavailable."""
    model = _load_lgbm_model()
    if model is None:
        return None
    try:
        import numpy as np
        X = np.array([features], dtype=np.float32)
        pred = model.predict(X)
        return float(np.clip(pred[0], 0.0, 1.0))
    except Exception as e:
        logger.debug("LightGBM predict failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Main classification entry point
# ---------------------------------------------------------------------------

def classify_apnea_type(
    onset_idx: int,
    end_idx: int,
    thorax_env:   np.ndarray | None,
    abdomen_env:  np.ndarray | None,
    thorax_raw:   np.ndarray | None,
    abdomen_raw:  np.ndarray | None,
    effort_baseline: float,
    sf: float,
) -> tuple[str, float, dict]:
    """
    Classify an apnea event as ``"obstructive"``, ``"central"``, or
    ``"mixed"`` per AASM 2.6 Adult Scoring Rules (section 3B).

    Decision logic (in priority order)
    -----------------------------------
    0. **Phase angle >45°** (v0.8.11) → obstructive with high confidence.
       Detects paradoxical movement even before amplitude drops.
    1. **Paradoxical thoraco-abdominal movement** → obstructive
    2. **Raw signal variability present, envelope low** → obstructive
    3. **Mixed pattern** – absent effort first half, present second half
    4. **Effort clearly present** → obstructive
    5. **Truly flat** – no raw movement, low envelope → central
    6. **Borderline default** → obstructive (low confidence)
       If LightGBM model available, confidence is calibrated by model.

    Returns
    -------
    (type_str, confidence_0_to_1, detail_dict)
    """
    seg_len  = end_idx - onset_idx
    dur_s    = seg_len / max(sf, 1)
    if seg_len < 2:
        return "obstructive", 0.5, {}

    effort_segs: dict[str, np.ndarray] = {}
    if thorax_env is not None:
        effort_segs["thorax"]  = thorax_env[onset_idx:end_idx]
    if abdomen_env is not None:
        effort_segs["abdomen"] = abdomen_env[onset_idx:end_idx]

    if not effort_segs:
        return "obstructive", 0.3, {"note": "no effort channels"}

    event_effort  = float(np.mean([np.mean(s) for s in effort_segs.values()]))
    effort_ratio  = event_effort / effort_baseline if effort_baseline > 1e-9 else 0.0
    raw_var_ratio = _compute_raw_variability(thorax_raw, abdomen_raw, onset_idx, end_idx, sf)
    paradox_corr  = _compute_paradox_correlation(thorax_raw, abdomen_raw, onset_idx, end_idx)

    # v0.8.11: Phase angle via Hilbert transform
    phase_angle_deg = _compute_phase_angle(thorax_raw, abdomen_raw, onset_idx, end_idx, sf)

    half         = seg_len // 2
    first_ratio  = _mean_effort_ratio(effort_segs, 0, half, effort_baseline)
    second_ratio = _mean_effort_ratio(effort_segs, half, seg_len, effort_baseline)
    quarter      = max(1, seg_len // 4)
    quarter_efforts = [
        _mean_effort_ratio(effort_segs, q * quarter,
                           min((q + 1) * quarter, seg_len), effort_baseline)
        for q in range(4)
    ]

    detail = {
        "effort_ratio":        safe_r(effort_ratio,    3),
        "raw_var_ratio":       safe_r(raw_var_ratio,   3),
        "first_half_effort":   safe_r(first_ratio,     3),
        "second_half_effort":  safe_r(second_ratio,    3),
        "quarter_efforts":     [safe_r(q, 3) for q in quarter_efforts],
        "paradox_correlation": safe_r(paradox_corr,    3),
        "phase_angle_deg":     safe_r(phase_angle_deg, 1),
    }

    is_paradox   = paradox_corr is not None and paradox_corr < -0.15
    has_raw_move = raw_var_ratio > 0.25

    # Helper to optionally replace rule-based confidence with LightGBM
    def _conf(rule_conf: float, rule_idx: int) -> float:
        """Bereken betrouwbaarheidsscore voor apnea-classificatie (0–1)."""
        features = _extract_lgbm_features(
            effort_ratio, raw_var_ratio, paradox_corr,
            first_ratio, second_ratio, quarter_efforts,
            phase_angle_deg, dur_s, rule_idx,
        )
        lgbm_c = _lgbm_confidence(features)
        if lgbm_c is not None:
            detail["lgbm_confidence"] = safe_r(lgbm_c, 3)
        return lgbm_c if lgbm_c is not None else rule_conf

    # ── Rule 0 (v0.8.11): Phase angle ≥45° during event ──────────────────
    if phase_angle_deg is not None and phase_angle_deg >= 45.0:
        conf = min(0.97, 0.75 + (phase_angle_deg - 45) / 180 * 0.2)
        detail["decision_reason"] = f"phase_angle={safe_r(phase_angle_deg,1)}deg"
        return "obstructive", safe_r(_conf(conf, 0), 2), detail

    # ── Rule 1: Paradox + raw movement ────────────────────────────────────
    if is_paradox and has_raw_move:
        conf = min(0.95, 0.70 + abs(paradox_corr) * 0.3)
        detail["decision_reason"] = f"paradox_corr={safe_r(paradox_corr,3)}"
        return "obstructive", safe_r(_conf(conf, 1), 2), detail

    # ── Rule 2: Raw movement, low envelope ───────────────────────────────
    if raw_var_ratio > 0.40 and effort_ratio < EFFORT_PRESENT_RATIO:
        if paradox_corr is None or paradox_corr < 0.3:
            conf = min(0.85, 0.50 + raw_var_ratio * 0.3)
            detail["decision_reason"] = f"raw_movement_var={safe_r(raw_var_ratio,3)}"
            return "obstructive", safe_r(_conf(conf, 2), 2), detail

    # ── Rule 3: Mixed ─────────────────────────────────────────────────────
    if first_ratio < EFFORT_ABSENT_RATIO and second_ratio > EFFORT_PRESENT_RATIO:
        conf = min(0.95, 0.6 + (second_ratio - first_ratio))
        detail["decision_reason"] = "first_absent_second_present"
        return "mixed", safe_r(_conf(conf, 3), 2), detail

    # ── Rule 4: Clear effort ──────────────────────────────────────────────
    if effort_ratio > EFFORT_PRESENT_RATIO:
        conf = min(0.95, 0.5 + (effort_ratio - EFFORT_PRESENT_RATIO))
        detail["decision_reason"] = f"effort_present={safe_r(effort_ratio,3)}"
        return "obstructive", safe_r(_conf(conf, 4), 2), detail

    # ── Rule 5: Truly flat → central ─────────────────────────────────────
    quarters_absent = sum(1 for q in quarter_efforts if q < EFFORT_ABSENT_RATIO)
    no_paradox      = paradox_corr is None or paradox_corr > 0.0
    no_phase_signal = phase_angle_deg is None or phase_angle_deg < 20.0
    if (
        raw_var_ratio < 0.15 and
        effort_ratio  < EFFORT_ABSENT_RATIO and
        quarters_absent >= 3 and
        no_paradox and
        no_phase_signal
    ):
        conf = min(0.90, 0.5 + (EFFORT_ABSENT_RATIO - effort_ratio) * 3)
        detail["decision_reason"] = (
            f"truly_flat_var={safe_r(raw_var_ratio,3)}_effort={safe_r(effort_ratio,3)}"
        )
        return "central", safe_r(_conf(conf, 5), 2), detail

    # ── Rule 6: Borderline default ────────────────────────────────────────
    detail["decision_reason"] = (
        f"borderline_default_var={safe_r(raw_var_ratio,3)}_effort={safe_r(effort_ratio,3)}"
    )
    return "obstructive", safe_r(_conf(0.40, 6), 2), detail


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _compute_phase_angle(
    thorax_raw:  np.ndarray | None,
    abdomen_raw: np.ndarray | None,
    onset_idx:   int,
    end_idx:     int,
    sf:          float,
    min_dur_s:   float = 5.0,
) -> float | None:
    """
    Bereken de gemiddelde instantane fasehoek (in graden) tussen thorax en
    abdomen via de Hilbert-transformatie.

    0°   = perfect synchroon (normaal)
    90°  = kwartslag fase-verschuiving
    180° = volledig paradoxaal

    Een waarde >= 45° bij een flow-limitatie is een betrouwbare indicator
    van obstructief effort, ook wanneer de amplitude-envelop laag is.

    Vereist minimaal min_dur_s seconden signaal voor betrouwbare Hilbert.
    """
    if thorax_raw is None or abdomen_raw is None:
        return None
    seg_len = end_idx - onset_idx
    if seg_len < int(sf * min_dur_s):
        return None

    t_seg = thorax_raw[onset_idx:end_idx].astype(float)
    a_seg = abdomen_raw[onset_idx:end_idx].astype(float)

    # Verwijder DC-offset
    t_seg = t_seg - np.mean(t_seg)
    a_seg = a_seg - np.mean(a_seg)

    if np.std(t_seg) < 1e-9 or np.std(a_seg) < 1e-9:
        return None

    try:
        # Instantane fase via Hilbert-transformatie
        phi_t = np.angle(hilbert(t_seg))
        phi_a = np.angle(hilbert(a_seg))

        # Fase-verschil (gewikkeld naar [-π, π])
        delta_phi = np.angle(np.exp(1j * (phi_t - phi_a)))

        # Gemiddelde absolute fasehoek in graden
        mean_angle_deg = float(np.degrees(np.mean(np.abs(delta_phi))))
        return safe_r(mean_angle_deg, 1)
    except Exception:
        return None


def _compute_raw_variability(
    thorax_raw: np.ndarray | None,
    abdomen_raw: np.ndarray | None,
    onset_idx: int,
    end_idx: int,
    sf: float,
) -> float:
    """Bereken ruwe signaalvariabiliteit (standaarddeviatie) van effort-kanaal."""
    if thorax_raw is None and abdomen_raw is None:
        return 0.0
    event_stds = []
    for raw in (thorax_raw, abdomen_raw):
        if raw is not None:
            event_stds.append(float(np.std(raw[onset_idx:end_idx])))
    raw_variability = float(np.mean(event_stds))
    pre_start = max(0, onset_idx - int(120 * sf))
    pre_end   = max(0, onset_idx - int(5   * sf))
    if pre_end <= pre_start:
        return 1.0
    bl_stds = []
    for raw in (thorax_raw, abdomen_raw):
        if raw is not None:
            bl_stds.append(float(np.std(raw[pre_start:pre_end])))
    bl_var = max(float(np.mean(bl_stds)), 1e-9) if bl_stds else 1e-9
    return raw_variability / bl_var


def _compute_paradox_correlation(
    thorax_raw: np.ndarray | None,
    abdomen_raw: np.ndarray | None,
    onset_idx: int,
    end_idx: int,
) -> float | None:
    """Bereken paradoxale ademhalingscorrelatie tussen thorax en abdomen."""
    if thorax_raw is None or abdomen_raw is None:
        return None
    t_seg = thorax_raw[onset_idx:end_idx]
    a_seg = abdomen_raw[onset_idx:end_idx]
    if len(t_seg) <= 10 or np.std(t_seg) < 1e-9 or np.std(a_seg) < 1e-9:
        return None
    try:
        corr, _ = pearsonr(t_seg, a_seg)
        return float(corr)
    except Exception:
        return None


def _mean_effort_ratio(
    effort_segs: dict[str, np.ndarray],
    start: int,
    end: int,
    effort_baseline: float,
) -> float:
    """Gemiddelde effort-ratio: event-amplitude / basislijn-amplitude."""
    if effort_baseline < 1e-9:
        return 0.0
    vals = [float(np.mean(seg[start:end])) for seg in effort_segs.values()]
    return float(np.mean(vals)) / effort_baseline if vals else 0.0
