"""
arousal_analysis.py — Arousal detectie & respiratoir-arousal koppeling
voor YASAFlaskified v0.8.37

Conform AASM 2.6 Adult Scoring Manual, Chapter 5 (Arousals):
  - Arousal: abrupte EEG-frequentieverandering ≥3s (α/θ/β in NREM; α in REM)
    voorafgegaan door ≥10s stabiele slaap
  - Respiratoire arousal: arousal binnen 15s na einde apnea/hypopnea
  - RERA: flow-limitatie + arousal ZONDER apnea/hypopnea drempel te bereiken
  - Arousal-index: aantal arousals per uur slaap (normaal < 10–15/u)

Klinisch verband:
  apnea/hypopnea → hypoxie/hypercapnie/mechanische load → cortical arousal
  → slaapfragmentatie → overmatige slaperigheid overdag (EDS)
  → cardiovasculaire stress (nachtelijke bloeddrukpieken)
"""

import logging
import os
import traceback
from pathlib import Path

import numpy as np
from scipy.ndimage import label
from scipy.signal import find_peaks  # v0.8.40: consolidated imports

logger = logging.getLogger("yasaflaskified.arousal")


# ═══════════════════════════════════════════════════════════════
# v0.9.8: LightGBM candidate-level re-classifier
# Enabled per request via env var YASAFLASKIFIED_AROUSAL_LGBM=1.
# When enabled, detect_arousals runs with permissive thresholds
# (ratio=1.2, abrupt=1.0) to maximise candidate recall, then
# filters surviving candidates with a LightGBM model trained on
# MESA q∈{5,6} (n_subj=653, ~562k candidates) at probability
# threshold AROUSAL_LGBM_THRESHOLD (default 0.60).
# Backward-compat: when the env var is absent or "0", behaviour is
# bit-identical to the v0.8.40 rule-based detector.
# ═══════════════════════════════════════════════════════════════

AROUSAL_LGBM_MODEL_PATH = str(
    Path(__file__).with_name("data") / "arousal_classifier_v3.txt"
)
AROUSAL_LGBM_THRESHOLD = float(
    os.environ.get("YASAFLASKIFIED_AROUSAL_LGBM_THRESHOLD", "0.60")
)
# Permissive candidate-stage thresholds used only in hybrid mode.
AROUSAL_LGBM_CAND_RATIO  = 1.2
AROUSAL_LGBM_CAND_ABRUPT = 1.0

# Feature column order — must match arousal_classifier_v3_report.json
# feature_names list. Changing this list invalidates the bundled model.
_AROUSAL_LGBM_FEATURE_ORDER: list[str] = [
    "duration_s", "stage_code", "stage_n1", "stage_n2", "stage_n3",
    "stage_rem", "dom_band_code", "alpha_ratio", "beta_ratio",
    "onset_ratio", "emg_confirmed", "cvr_boost",
    "bp_pre_delta", "bp_pre_theta", "bp_pre_alpha", "bp_pre_sigma", "bp_pre_beta",
    "bp_cand_delta", "bp_cand_theta", "bp_cand_alpha", "bp_cand_sigma", "bp_cand_beta",
    "bp_post_delta", "bp_post_theta", "bp_post_alpha", "bp_post_sigma", "bp_post_beta",
    "ratio_alpha_to_sigma", "ratio_beta_to_sigma", "ratio_arousal_to_sigma",
    "delta_alpha_pre_cand", "delta_beta_pre_cand", "delta_total_pre_cand",
    "hj_pre_act", "hj_pre_mob", "hj_pre_comp",
    "hj_cand_act", "hj_cand_mob", "hj_cand_comp",
    "hj_post_act", "hj_post_mob", "hj_post_comp",
    "spec_edge_95", "spec_edge_50",
    "td_cand_var", "td_cand_kurt", "td_cand_zcr",
    "emg_var_ratio", "hr_shift_rel", "pos_in_night",
]
_AROUSAL_LGBM_BOOSTER = None  # cached after first use


def _is_arousal_lgbm_enabled() -> bool:
    return os.environ.get("YASAFLASKIFIED_AROUSAL_LGBM", "0") == "1"


def _load_arousal_lgbm_booster():
    global _AROUSAL_LGBM_BOOSTER
    if _AROUSAL_LGBM_BOOSTER is not None:
        return _AROUSAL_LGBM_BOOSTER
    if not Path(AROUSAL_LGBM_MODEL_PATH).exists():
        raise FileNotFoundError(
            f"Arousal LGBM model not found at {AROUSAL_LGBM_MODEL_PATH}; "
            "ship arousal_classifier_v3.txt into myproject/data/."
        )
    import lightgbm as lgb  # noqa: WPS433
    _AROUSAL_LGBM_BOOSTER = lgb.Booster(model_file=AROUSAL_LGBM_MODEL_PATH)
    return _AROUSAL_LGBM_BOOSTER


def _bandpower_window(seg: np.ndarray, sf: float, lo: float, hi: float) -> float:
    """Welch-free FFT bandpower estimate over `seg` (µV)."""
    if seg.size < int(sf):
        return 0.0
    n = seg.size
    win = np.hanning(n)
    fx = np.fft.rfft(seg * win)
    f = np.fft.rfftfreq(n, 1.0 / sf)
    psd = (np.abs(fx) ** 2) / (sf * np.sum(win ** 2))
    if n % 2:
        psd[1:] *= 2
    else:
        psd[1:-1] *= 2
    band = (f >= lo) & (f < hi)
    if not np.any(band):
        return 0.0
    integrate = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    return float(integrate(psd[band], f[band]))


def _hjorth_window(seg: np.ndarray) -> tuple[float, float, float]:
    if seg.size < 3:
        return (0.0, 0.0, 0.0)
    var0 = float(np.var(seg))
    if var0 <= 0:
        return (0.0, 0.0, 0.0)
    d1 = np.diff(seg)
    var1 = float(np.var(d1))
    mob = float(np.sqrt(var1 / var0)) if var1 > 0 else 0.0
    if d1.size < 3 or mob <= 0:
        return (var0, mob, 0.0)
    d2 = np.diff(d1)
    var2 = float(np.var(d2))
    mob1 = float(np.sqrt(var2 / var1)) if var1 > 0 else 0.0
    return (var0, mob, mob1 / mob if mob > 0 else 0.0)


def _spectral_edge_window(seg: np.ndarray, sf: float, edge_pct: float) -> float:
    if seg.size < int(sf):
        return 0.0
    n = seg.size
    win = np.hanning(n)
    fx = np.fft.rfft(seg * win)
    f = np.fft.rfftfreq(n, 1.0 / sf)
    psd = (np.abs(fx) ** 2)
    if n % 2:
        psd[1:] *= 2
    else:
        psd[1:-1] *= 2
    band = (f >= 0.5) & (f <= 30.0)
    if not np.any(band):
        return 0.0
    p = psd[band]
    fb = f[band]
    cum = np.cumsum(p)
    if cum[-1] <= 0:
        return 0.0
    idx = int(np.searchsorted(cum, edge_pct * cum[-1]))
    return float(fb[min(idx, fb.size - 1)])


def _arousal_lgbm_features(
    cand: dict,
    eeg_uv: np.ndarray, sf: float,
    emg_uv: np.ndarray | None,
    n_epochs: int,
) -> dict:
    """Build the 50-feature vector for one candidate. Mirrors exactly
    the layout in build_arousal_dataset.py used to train v3."""
    onset_s = float(cand["onset_s"])
    end_s   = float(cand["end_s"])
    onset_i = int(onset_s * sf)
    end_i   = int(end_s * sf)
    pre_i   = max(0, onset_i - int(5.0 * sf))
    post_i  = min(eeg_uv.size, end_i + int(5.0 * sf))

    pre  = eeg_uv[pre_i:onset_i]
    cand_seg = eeg_uv[onset_i:end_i]
    post = eeg_uv[end_i:post_i]

    stage = cand.get("stage", "W")
    stage_codes = {"W": 0, "N1": 1, "N2": 2, "N3": 3, "R": 4}
    band_codes  = {"alpha": 0, "theta": 1, "beta": 2}
    ep_idx = int(cand.get("epoch", int(onset_s // 30)))

    eps = 1e-12
    out: dict[str, float] = {
        "duration_s":     float(cand.get("duration_s", end_s - onset_s)),
        "stage_code":     float(stage_codes.get(stage, 0)),
        "stage_n1":       float(stage == "N1"),
        "stage_n2":       float(stage == "N2"),
        "stage_n3":       float(stage == "N3"),
        "stage_rem":      float(stage == "R"),
        "dom_band_code":  float(band_codes.get(cand.get("dominant_band", "alpha"), 0)),
        "alpha_ratio":    float(cand.get("alpha_ratio", 0.0)),
        "beta_ratio":     float(cand.get("beta_ratio", 0.0)),
        "onset_ratio":    float(cand.get("onset_ratio", 0.0)),
        "emg_confirmed":  float(bool(cand.get("emg_confirmed", False))),
        "cvr_boost":      float(cand.get("cvr_boost", 0.0)),
    }

    for label_, seg in (("pre", pre), ("cand", cand_seg), ("post", post)):
        if seg.size < int(sf):
            for b in ("delta", "theta", "alpha", "sigma", "beta"):
                out[f"bp_{label_}_{b}"] = 0.0
            continue
        out[f"bp_{label_}_delta"] = _bandpower_window(seg, sf, 0.5, 4.0)
        out[f"bp_{label_}_theta"] = _bandpower_window(seg, sf, 4.0, 8.0)
        out[f"bp_{label_}_alpha"] = _bandpower_window(seg, sf, 8.0, 11.0)
        out[f"bp_{label_}_sigma"] = _bandpower_window(seg, sf, 12.0, 15.0)
        out[f"bp_{label_}_beta"]  = _bandpower_window(seg, sf, 16.0, 30.0)

    out["ratio_alpha_to_sigma"]   = out["bp_cand_alpha"] / (out["bp_cand_sigma"] + eps)
    out["ratio_beta_to_sigma"]    = out["bp_cand_beta"]  / (out["bp_cand_sigma"] + eps)
    out["ratio_arousal_to_sigma"] = (out["bp_cand_alpha"] + out["bp_cand_theta"]
                                     + out["bp_cand_beta"]) / (out["bp_cand_sigma"] + eps)
    out["delta_alpha_pre_cand"]   = (out["bp_cand_alpha"] - out["bp_pre_alpha"]) \
                                    / (out["bp_pre_alpha"] + eps)
    out["delta_beta_pre_cand"]    = (out["bp_cand_beta"]  - out["bp_pre_beta"]) \
                                    / (out["bp_pre_beta"]  + eps)
    out["delta_total_pre_cand"]   = ((out["bp_cand_alpha"] + out["bp_cand_theta"]
                                      + out["bp_cand_beta"])
                                     - (out["bp_pre_alpha"] + out["bp_pre_theta"]
                                        + out["bp_pre_beta"])) \
                                    / (out["bp_pre_alpha"] + out["bp_pre_theta"]
                                       + out["bp_pre_beta"] + eps)

    for label_, seg in (("pre", pre), ("cand", cand_seg), ("post", post)):
        a, m, c = _hjorth_window(seg)
        out[f"hj_{label_}_act"]  = a
        out[f"hj_{label_}_mob"]  = m
        out[f"hj_{label_}_comp"] = c

    out["spec_edge_95"] = _spectral_edge_window(cand_seg, sf, 0.95)
    out["spec_edge_50"] = _spectral_edge_window(cand_seg, sf, 0.50)

    if cand_seg.size >= 3:
        out["td_cand_var"] = float(np.var(cand_seg))
        m_  = float(np.mean(cand_seg))
        sd_ = float(np.std(cand_seg))
        out["td_cand_kurt"] = float(np.mean(((cand_seg - m_) / (sd_ + eps)) ** 4) - 3) if sd_ > 0 else 0.0
        out["td_cand_zcr"]  = float(np.mean(np.diff(np.signbit(cand_seg)) != 0))
    else:
        out["td_cand_var"]  = 0.0
        out["td_cand_kurt"] = 0.0
        out["td_cand_zcr"]  = 0.0

    if emg_uv is not None and emg_uv.size >= eeg_uv.size:
        emg_pre  = emg_uv[pre_i:onset_i]
        emg_cand = emg_uv[onset_i:end_i]
        v_pre  = float(np.var(emg_pre))  if emg_pre.size  >= 3 else 0.0
        v_cand = float(np.var(emg_cand)) if emg_cand.size >= 3 else 0.0
        out["emg_var_ratio"] = v_cand / (v_pre + eps)
    else:
        out["emg_var_ratio"] = 0.0

    out["hr_shift_rel"] = 0.0  # v3 trained without HR feature populated
    out["pos_in_night"] = ep_idx / max(1, n_epochs - 1)

    return out


def _filter_candidates_with_lgbm(
    events: list[dict],
    eeg_uv: np.ndarray, sf: float,
    emg_uv: np.ndarray | None,
    n_epochs: int,
    threshold: float = AROUSAL_LGBM_THRESHOLD,
) -> tuple[list[dict], list[float]]:
    """Score each candidate with the LGBM model and return the events
    with `proba >= threshold`, plus the per-candidate probabilities."""
    if not events:
        return [], []
    booster = _load_arousal_lgbm_booster()
    feat_rows = [_arousal_lgbm_features(c, eeg_uv, sf, emg_uv, n_epochs) for c in events]
    X = np.array([[r[c] for c in _AROUSAL_LGBM_FEATURE_ORDER] for r in feat_rows],
                 dtype=float)
    proba = booster.predict(X)
    kept = []
    for ev, p in zip(events, proba):
        if p >= threshold:
            ev = dict(ev)
            ev["lgbm_proba"] = round(float(p), 4)
            kept.append(ev)
    return kept, [float(p) for p in proba]


def _recompute_arousal_summary(
    arousals: list[dict], hypno: list, artifact_set: set,
) -> dict:
    """Rebuild the summary fields after LGBM filtering."""
    total_sleep_s = sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                        if _is_sleep(s) and i not in artifact_set)
    total_sleep_h = max(total_sleep_s / 3600, 0.001)
    rem_h  = max(sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                     if _is_rem(s) and i not in artifact_set) / 3600, 0.001)
    nrem_h = max(sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                     if _is_nrem(s) and i not in artifact_set) / 3600, 0.001)
    nrem_ar = [a for a in arousals if _is_nrem(a.get("stage", "W"))]
    rem_ar  = [a for a in arousals if _is_rem(a.get("stage", "W"))]
    ai = len(arousals) / total_sleep_h
    return {
        "n_arousals":         len(arousals),
        "arousal_index":      _safe(ai),
        "nrem_arousal_index": _safe(len(nrem_ar) / nrem_h),
        "rem_arousal_index":  _safe(len(rem_ar)  / rem_h),
        "avg_duration_s":     _safe(float(np.mean([a["duration_s"]
                                       for a in arousals]))) if arousals else None,
        "severity":           _classify_arousal_index(ai),
        "n_theta_dominant":   sum(1 for a in arousals if a.get("dominant_band") == "theta"),
        "n_alpha_dominant":   sum(1 for a in arousals if a.get("dominant_band") == "alpha"),
        "n_beta_dominant":    sum(1 for a in arousals if a.get("dominant_band") == "beta"),
        "n_emg_confirmed":    sum(1 for a in arousals if a.get("emg_confirmed")),
    }


# ═══════════════════════════════════════════════════════════════
# CONSTANTEN  (AASM 2.6, v0.8.11 — verbeterd)
# ═══════════════════════════════════════════════════════════════

AROUSAL_MIN_DUR_S     = 3.0     # ≥3s EEG-frequentieverandering
AROUSAL_MAX_DUR_S     = 30.0    # >30s = waarschijnlijk wakker
PRESLEEP_MIN_S        = 10.0    # ≥10s slaap vóór arousal vereist
POST_RESP_WINDOW_S    = 15.0    # arousal binnen 15s na resp. event = respiratoir
RERA_FLOW_LIMIT_THR   = 0.80    # flow 80–100% = flow-limitatie (plateau)
RERA_MIN_DUR_S        = 10.0    # ≥10s flow-limitatie voor RERA

# v0.8.11: Correcte frequentiebanden conform AASM
ALPHA_NARROW_BAND     = (8, 11)    # Alpha ZONDER spindle-overlap (was 8-13)
SIGMA_BAND            = (12, 15)   # Slaapspindels — UITSLUITEN uit arousal
THETA_BAND            = (4, 8)     # v0.8.11: NIEUW — theta-shift arousals
BETA_BAND             = (16, 30)   # >16 Hz (AASM definitie)
DELTA_BAND            = (0.5, 4)
ALPHA_BAND            = (8, 13)    # Breed alpha (voor backward compat in stats)

# v0.8.11: Drempels
AROUSAL_RATIO_THRESH  = 2.0     # v0.8.11: verlaagd van 3.0 → 2.0 (v0.8.11: verder verlaagd)
ABRUPT_RATIO_THRESH   = 1.5     # v0.8.11: verlaagd van 2.0 → 1.5 (2s FFT-vensters smoothen te veel)
EPOCH_LEN_S           = 30


# ═══════════════════════════════════════════════════════════════
# HULPFUNCTIES
# ═══════════════════════════════════════════════════════════════

def _safe(val, dec=1):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return round(float(val), dec)
    except Exception:
        return None


def _bandpower_instant(eeg: np.ndarray, sf: float,
                        band: tuple, win_s: float = 2.0) -> np.ndarray:
    """
    Bereken instantaan bandvermogen via glijdend Welch-venster.
    Geeft een tijdreeks terug (één waarde per sample via interpolatie).
    """
    win   = int(win_s * sf)
    step  = max(1, win // 4)
    freqs = np.fft.rfftfreq(win, 1 / sf)
    lo, hi = band
    band_idx = (freqs >= lo) & (freqs <= hi)

    n_steps  = (len(eeg) - win) // step + 1
    powers   = np.zeros(n_steps)
    centers  = np.zeros(n_steps, dtype=int)

    for i in range(n_steps):
        s   = i * step
        e   = s + win
        seg = eeg[s:e] * np.hanning(win)
        psd = np.abs(np.fft.rfft(seg)) ** 2 / win
        powers[i]  = float(np.sum(psd[band_idx]))
        centers[i] = s + win // 2

    # Interpoleer terug naar sample-resolutie
    t_full  = np.arange(len(eeg))
    power_full = np.interp(t_full, centers, powers)
    return power_full


def _is_nrem(stage) -> bool:
    return stage in (1, 2, 3, "N1", "N2", "N3")


def _is_rem(stage) -> bool:
    return stage in (4, "R")


def _is_sleep(stage) -> bool:
    return stage not in (0, -1, "W")


def _build_stage_mask(hypno: list, sf: float,
                       total_samples: int, stages) -> np.ndarray:
    spe  = int(sf * EPOCH_LEN_S)
    mask = np.zeros(total_samples, dtype=bool)
    for ep_i, stage in enumerate(hypno):
        if stage in stages:
            s = ep_i * spe
            e = min(s + spe, total_samples)
            mask[s:e] = True
    return mask


# ═══════════════════════════════════════════════════════════════
# AROUSAL DETECTIE  (AASM spectrale methode)
# ═══════════════════════════════════════════════════════════════


def _is_kcomplex(
    eeg_uv: np.ndarray,
    onset_idx: int,
    sf: float,
    neg_thresh_uv: float = 75.0,
    window_s: float = 1.0,
) -> bool:
    """
    v0.8.11 — K-complex morfologische check.

    Een K-complex is een bipolaire golf: grote negatieve piek (<-75 µV)
    gevolgd door een positieve piek, alles binnen ~1 seconde.
    Als een arousal-kandidaat begint met zo\'n morfologie, is het
    waarschijnlijk een K-complex, geen echte arousal.

    Verhoog de min-duur lokaal naar 5.0 s om false positives te vermijden.
    Returns True als K-complex morfologie aanwezig is.
    """
    win = int(sf * window_s)
    end = min(onset_idx + win, len(eeg_uv))
    seg = eeg_uv[onset_idx:end]
    if len(seg) < int(sf * 0.3):
        return False
    min_val = float(np.min(seg))
    max_val = float(np.max(seg))
    min_idx = int(np.argmin(seg))
    max_idx = int(np.argmax(seg))
    # Typisch K-complex: negatieve piek gevolgd door positieve piek
    bipolaire_vorm = (
        min_val < -neg_thresh_uv and
        max_val > 30.0 and
        min_idx < max_idx       # negatief VOOR positief
    )
    return bipolaire_vorm


def _detect_cvr_confidence_boost(
    hr_data: np.ndarray | None,
    sf_hr: float,
    onset_s: float,
    pre_window_s: float = 10.0,
    post_window_s: float = 15.0,
    brady_delta_bpm: float = 5.0,
    tachy_delta_bpm: float = 10.0,
) -> float:
    """
    v0.8.11 — Autonome arousal confidence boost via Cyclical Variation of
    Heart Rate (CVR).

    Bij een respiratoir of corticaal event:
    - bradycardie tijdens het event (parasympathische activatie)
    - gevolgd door plotse tachycardie bij het einde (sympathische rebound)

    Als dit patroon aanwezig is naast een borderline EEG-arousal, verhogen
    we de confidence met 0.10–0.20.

    Returns
    -------
    boost : float (0.0 = geen patroon, 0.10–0.20 = aanwezig)
    """
    if hr_data is None or len(hr_data) == 0:
        return 0.0
    try:
        pre_start  = max(0, int((onset_s - pre_window_s) * sf_hr))
        pre_end    = max(0, int(onset_s * sf_hr))
        post_start = int(onset_s * sf_hr)
        post_end   = min(len(hr_data), int((onset_s + post_window_s) * sf_hr))

        if pre_end <= pre_start or post_end <= post_start:
            return 0.0

        hr_pre  = hr_data[pre_start:pre_end]
        hr_post = hr_data[post_start:post_end]

        # Verwijder fysiologisch onmogelijke waarden
        hr_pre  = hr_pre[(hr_pre > 20) & (hr_pre < 250)]
        hr_post = hr_post[(hr_post > 20) & (hr_post < 250)]

        if len(hr_pre) < 3 or len(hr_post) < 3:
            return 0.0

        mean_pre  = float(np.mean(hr_pre))
        mean_post = float(np.max(hr_post[:max(1, len(hr_post)//3)]))
        # Minimum van pre-venster (bradycardie)
        min_pre   = float(np.min(hr_pre))

        brady_present = (mean_pre - min_pre) >= brady_delta_bpm
        tachy_present = (mean_post - mean_pre) >= tachy_delta_bpm

        if brady_present and tachy_present:
            strength = min(1.0, (mean_post - min_pre) / 30.0)
            return round(0.10 + 0.10 * strength, 2)
        if tachy_present:
            return 0.10
        return 0.0
    except Exception:
        return 0.0

def detect_arousals(eeg_data: np.ndarray, sf: float,
                    hypno: list,
                    emg_data: np.ndarray = None,
                    artifact_epochs: list = None,
                    hr_data: np.ndarray = None,
                    sf_hr: float = 1.0) -> dict:
    """
    Detecteer EEG-arousals conform AASM 2.6, Sectie 5.

    v0.8.11 verbeteringen:
    1. Theta band (4-8 Hz) toegevoegd — veel arousals bij ouderen
    2. Alpha ingeperkt tot 8-11 Hz — voorkomt spindle vals-positieven
    3. Sigma band (12-15 Hz) apart gedetecteerd en UITGESLOTEN
    4. Abruptheid-criterium: vermogen moet >2× toenemen t.o.v. 3s ervoor
    5. Pre-sleep check valideert hypnogram (niet alleen arousal-vrij)
    6. Robuustere basislijn (mediaan van laagste 50% periodes)

    AASM definitie: "abrupte verschuiving van EEG-frequentie met inbegrip
    van alpha, theta en/of frequenties >16 Hz (maar niet slaapspindels),
    gedurende ≥3s, met ≥10s stabiele slaap voorafgaand."

    In REM: + EMG toename ≥1s.

    v0.9.8: when YASAFLASKIFIED_AROUSAL_LGBM=1 is set, the candidate
    stage runs with permissive thresholds (ratio=1.2, abrupt=1.0) and
    surviving candidates are filtered post-hoc by a LightGBM
    re-classifier at threshold AROUSAL_LGBM_THRESHOLD (default 0.60).
    Backward-compat: with the env var unset the function is
    bit-identical to the rule-based v0.8.40 detector.
    """
    # v0.9.8: hybrid mode dispatch — swap the candidate thresholds in
    # the module globals while the rule-based body runs, then filter
    # via LGBM after the function completes. The swap is restored in a
    # try/finally below so concurrent callers see the original values.
    _hybrid = _is_arousal_lgbm_enabled()
    global AROUSAL_RATIO_THRESH, ABRUPT_RATIO_THRESH
    _saved_ratio  = AROUSAL_RATIO_THRESH
    _saved_abrupt = ABRUPT_RATIO_THRESH
    if _hybrid:
        AROUSAL_RATIO_THRESH = AROUSAL_LGBM_CAND_RATIO
        ABRUPT_RATIO_THRESH  = AROUSAL_LGBM_CAND_ABRUPT
        logger.info(
            "[arousal] LGBM hybrid mode enabled "
            "(candidate ratio=%.2f, abrupt=%.2f, threshold=%.2f)",
            AROUSAL_RATIO_THRESH, ABRUPT_RATIO_THRESH, AROUSAL_LGBM_THRESHOLD,
        )

    result = {"success": False, "events": [], "summary": {}, "error": None}
    try:
        n_samples = len(eeg_data)
        spe       = int(sf * EPOCH_LEN_S)

        # v0.8.11 FIX: Converteer EEG naar µV als het in Volt lijkt te zijn
        # raw.get_data() geeft Volt (bijv. 50 µV = 5e-5 V)
        # Bandpower in Volt² geeft ~1e-10 waarden → numerieke problemen
        eeg_uv = eeg_data.copy()
        if np.max(np.abs(eeg_uv)) < 0.01:  # max < 10 mV → waarschijnlijk Volt
            eeg_uv = eeg_uv * 1e6
            logger.debug("Arousal EEG: V→µV conversie (max=%.1f µV)", np.max(np.abs(eeg_uv)))

        # ── Bandvermogen tijdreeksen (v0.8.11: theta + alpha_narrow + beta) ──
        alpha_pow = _bandpower_instant(eeg_uv, sf, ALPHA_NARROW_BAND, win_s=2.0)
        theta_pow = _bandpower_instant(eeg_uv, sf, THETA_BAND, win_s=2.0)
        beta_pow  = _bandpower_instant(eeg_uv, sf, BETA_BAND,  win_s=2.0)
        sigma_pow = _bandpower_instant(eeg_uv, sf, SIGMA_BAND, win_s=2.0)
        delta_pow = _bandpower_instant(eeg_uv, sf, DELTA_BAND, win_s=2.0)

        # Gecombineerd arousal-vermogen: alpha_narrow + theta + beta
        # (AASM: "alpha, theta en/of >16 Hz")
        arousal_pow = alpha_pow + theta_pow + beta_pow

        # ── Baseline per slaapfase (v0.8.11: rolling 2-min venster) ────
        nrem_mask = _build_stage_mask(hypno, sf, n_samples,
                                       {"N1","N2","N3",1,2,3})
        rem_mask  = _build_stage_mask(hypno, sf, n_samples, {"R",4})

        def _robust_baseline(power_arr, mask):
            """Robuuste basislijn: mediaan van laagste 50% periodes.
            Voorkomt dat arousals zelf de basislijn verhogen."""
            seg = power_arr[mask]
            if len(seg) < int(sf * 60):
                seg = power_arr[power_arr > 0] if np.any(power_arr > 0) else power_arr
            if len(seg) == 0:
                return 1.0
            cutoff = np.percentile(seg, 50)
            quiet = seg[seg <= cutoff]
            if len(quiet) > 10:
                return max(float(np.median(quiet)), 1e-9)
            return max(float(np.percentile(seg, 25)), 1e-9)

        def _rolling_baseline(power_arr, stage_mask, window_s=120):
            """v0.8.11: Rolling basislijn over 2 min stabiele slaap.

            Bij ernstig gefragmenteerde slaap is een nacht-gemiddelde misleidend
            — de basislijn is al verhoogd door de vele arousals zelf.
            Een rolling venster van 120s stabiele slaap adapteert lokaal.

            Ref: Gemini review — "rolling baseline of the preceding 2 minutes
            of stable sleep to prevent habituation to the average power."
            """
            n = len(power_arr)
            win = int(window_s * sf)
            step = max(1, int(10 * sf))  # Bereken elke 10s
            anchors_x = []
            anchors_y = []

            for pos in range(0, n, step):
                start = max(0, pos - win)
                seg = power_arr[start:pos]
                seg_mask = stage_mask[start:pos]
                stable = seg[seg_mask]
                if len(stable) > int(sf * 10):
                    # Laagste 50% = stabiele slaap (excl. arousals)
                    cutoff = np.percentile(stable, 50)
                    quiet = stable[stable <= cutoff]
                    bl = float(np.median(quiet)) if len(quiet) > 5 else float(np.median(stable))
                else:
                    bl = None  # Niet genoeg data — wordt geïnterpoleerd
                if bl is not None and bl > 1e-9:
                    anchors_x.append(pos)
                    anchors_y.append(bl)

            if len(anchors_x) < 2:
                # v0.8.40: Fallback naar globale basislijn, maar met
                # noise-floor veiligheidsvloer om te voorkomen dat
                # arousal-inflated globale basislijn de drempel opdrijft.
                global_bl = _robust_baseline(power_arr, stage_mask)
                positive = power_arr[power_arr > 0]
                noise_floor = (float(np.percentile(positive, 5))
                               if positive.size > 0 else 1e-9)
                # Gebruik max van globale baseline en 2× noise floor:
                # bij zware fragmentatie trekt noise floor de drempel
                # realistisch omlaag.
                safe_bl = max(global_bl, noise_floor * 2.0)
                return np.full(n, safe_bl)

            baseline = np.interp(np.arange(n), anchors_x, anchors_y)
            return np.maximum(baseline, 1e-9)

        # Gebruik rolling baseline per sample (v0.8.11)
        arousal_bl_nrem_arr = _rolling_baseline(arousal_pow, nrem_mask)
        arousal_bl_rem_arr  = _rolling_baseline(arousal_pow, rem_mask)
        sigma_bl_nrem_arr   = _rolling_baseline(sigma_pow, nrem_mask)

        # Globale baselines voor statistiek (backward compat)
        arousal_bl_nrem = _robust_baseline(arousal_pow, nrem_mask)
        arousal_bl_rem  = _robust_baseline(arousal_pow, rem_mask)
        sigma_bl_nrem   = _robust_baseline(sigma_pow, nrem_mask)

        # Per-band baselines (voor detail-stats)
        alpha_bl_nrem = _robust_baseline(alpha_pow, nrem_mask)
        alpha_bl_rem  = _robust_baseline(alpha_pow, rem_mask)
        beta_bl_nrem  = _robust_baseline(beta_pow, nrem_mask)

        # ── EMG verwerking voor REM arousal criterium (AASM) ─────
        emg_rms = None
        emg_bl_rem = None
        EMG_WINDOW_S = 0.25
        EMG_RISE_FACTOR = 2.0
        EMG_MIN_DUR_S = 1.0

        if emg_data is not None and len(emg_data) >= n_samples:
            from scipy.signal import butter, filtfilt  # local import for backward compat
            try:
                # v0.8.11 FIX: converteer EMG naar µV (zelfde issue als EEG/PLM)
                emg_work = emg_data[:n_samples].copy()
                if np.max(np.abs(emg_work)) < 0.01:
                    emg_work = emg_work * 1e6
                    logger.debug("Arousal EMG: V→µV conversie")
                # v0.8.40: Guard tegen ongeldige bandpass bij lage sf
                nyq = sf / 2.0
                high = min(100.0, nyq - 1.0)
                if nyq > 10.0 and high > 10.0:
                    b, a = butter(4, [10, high], btype="band", fs=sf)
                    emg_filt = filtfilt(b, a, emg_work)
                else:
                    logger.warning(
                        "EMG: sample rate %.1f Hz te laag voor 10-100 Hz "
                        "bandpass — ongefilterd gebruikt", sf
                    )
                    emg_filt = emg_work
            except Exception:
                emg_filt = emg_data[:n_samples]

            win = max(int(sf * EMG_WINDOW_S), 1)
            emg_sq = emg_filt ** 2
            kernel = np.ones(win) / win
            emg_rms = np.sqrt(np.convolve(emg_sq, kernel, mode="same"))

            rem_emg = emg_rms[rem_mask] if np.any(rem_mask) else emg_rms
            emg_bl_rem = max(float(np.percentile(rem_emg, 25)), 1e-9) if len(rem_emg) > 0 else 1e-9

        # ── v0.8.11: TWO-PHASE AROUSAL DETECTION ─────────────────
        # PROBLEEM v14.7-14.8: per-sample conjunctie (elevated & abrupt
        # & ~sigma) vereist ALLE voorwaarden gelijktijdig True op elke
        # sample voor >=3s. De abruptheidsratio (rolling 3s pre-average)
        # volgt het signaal → na ~1s stijgt pre-average mee → nooit 3s True.
        #
        # OPLOSSING v0.8.11: twee fasen (zoals een menselijke scorer):
        #   Fase 1: vind regio's met verhoogd vermogen (>=3s, enkel power)
        #   Fase 2: valideer elk event op onset-abruptheid en spindle
        #           (event-niveau, niet per-sample)

        arousal_mask = np.zeros(n_samples, dtype=bool)
        artifact_set = set(artifact_epochs or [])

        # Slaap-mask per sample
        sleep_sample_mask = np.zeros(n_samples, dtype=bool)
        for ep_i, stage in enumerate(hypno):
            if _is_sleep(stage) and ep_i not in artifact_set:
                s2 = ep_i * spe
                e2 = min(s2 + spe, n_samples)
                sleep_sample_mask[s2:e2] = True

        # ── FASE 1: Vind verhoogd-vermogen regio's (rolling baseline) ──
        for ep_i, stage in enumerate(hypno):
            if ep_i in artifact_set:
                continue
            s = ep_i * spe
            e = min(s + spe, n_samples)
            if _is_nrem(stage):
                # v0.8.11: vergelijk met rolling baseline i.p.v. globaal
                local_bl = arousal_bl_nrem_arr[s:e]
                arousal_mask[s:e] = arousal_pow[s:e] > AROUSAL_RATIO_THRESH * local_bl
            elif _is_rem(stage):
                local_bl = arousal_bl_rem_arr[s:e]
                arousal_mask[s:e] = alpha_pow[s:e] > AROUSAL_RATIO_THRESH * local_bl

        # ── FASE 2: Label, valideer per event ──
        labeled, n_events = label(arousal_mask)
        arousals = []

        for i in range(1, n_events + 1):
            indices = np.where(labeled == i)[0]
            dur_s   = len(indices) / sf

            if dur_s < AROUSAL_MIN_DUR_S or dur_s > AROUSAL_MAX_DUR_S:
                continue

            onset_s = float(indices[0]) / sf
            end_s   = float(indices[-1]) / sf
            ep_idx  = int(onset_s // EPOCH_LEN_S)
            stage   = hypno[ep_idx] if ep_idx < len(hypno) else "W"

            # Check A: Pre-sleep (>=10s slaap, >=60%)
            pre_start = max(0, indices[0] - int(PRESLEEP_MIN_S * sf))
            pre_end   = indices[0]
            if pre_end > pre_start:
                sleep_frac = np.sum(sleep_sample_mask[pre_start:pre_end]) / (pre_end - pre_start)
                if sleep_frac < 0.6:
                    continue

            # Check B: Onset-abruptheid (event-niveau)
            onset_idx = indices[0]
            pre_3s_start = max(0, onset_idx - int(3.0 * sf))
            onset_1s_end = min(onset_idx + int(1.0 * sf), indices[-1] + 1)
            pre_power  = float(np.mean(arousal_pow[pre_3s_start:onset_idx])) if onset_idx > pre_3s_start else 1e-12
            onset_power = float(np.mean(arousal_pow[onset_idx:onset_1s_end]))
            onset_ratio = onset_power / max(pre_power, 1e-12)
            if onset_ratio < ABRUPT_RATIO_THRESH:
                continue

            # Check C: Spindle-exclusie (v0.8.11: ratio-check)
            # Bij het ontwaken uit N2 valt de arousal-burst vaak samen met een
            # afbrekende spindle. De oude logica (arousal < sigma) verwierp dit
            # onterecht. Nu: reject ENKEL als sigma >2× rolling baseline EN
            # alpha+beta samen MINDER dan 50% van sigma zijn.
            # → Een arousal met bijkomende spindle-activiteit wordt geaccepteerd
            #   zolang alpha+beta de event domineren.
            if _is_nrem(stage):
                ev_sigma = float(np.mean(sigma_pow[indices[0]:indices[-1]+1]))
                ev_alpha_beta = float(np.mean(
                    alpha_pow[indices[0]:indices[-1]+1] +
                    beta_pow[indices[0]:indices[-1]+1]))
                local_sigma_bl = float(np.mean(sigma_bl_nrem_arr[indices[0]:indices[-1]+1]))
                sigma_elevated = ev_sigma > 2.0 * local_sigma_bl
                # Reject: sigma dominant EN alpha+beta < 50% van sigma
                if sigma_elevated and ev_alpha_beta < 0.5 * ev_sigma:
                    continue

            # Check D: REM EMG
            emg_confirmed = True
            if _is_rem(stage):
                if emg_rms is not None and emg_bl_rem:
                    emg_seg = emg_rms[indices[0]:indices[-1]+1]
                    emg_dur = np.sum(emg_seg > EMG_RISE_FACTOR * emg_bl_rem) / sf
                    emg_confirmed = emg_dur >= EMG_MIN_DUR_S
                    if not emg_confirmed:
                        continue
                # Geen EMG → accepteer toch (alleen alpha+abrupt)

            # Check E (v0.8.11): K-complex morfologische check
            # Bipolaire golf (>75 µV neg + pos) in eerste 1s → verhoog min-duur
            kcomplex_min_dur_s = AROUSAL_MIN_DUR_S  # standaard 3.0 s
            if _is_nrem(stage):
                if _is_kcomplex(eeg_uv, indices[0], sf):
                    kcomplex_min_dur_s = 5.0  # conservatiever bij K-complex morfologie
                if dur_s < kcomplex_min_dur_s:
                    continue

            # Check F (v0.8.11): CVR confidence boost
            cvr_boost = 0.0
            if hr_data is not None and len(hr_data) > 0:
                cvr_boost = _detect_cvr_confidence_boost(
                    hr_data, sf_hr, onset_s
                )

            seg_alpha = float(np.mean(alpha_pow[indices[0]:indices[-1]+1]))
            seg_theta = float(np.mean(theta_pow[indices[0]:indices[-1]+1]))
            seg_beta  = float(np.mean(beta_pow[indices[0]:indices[-1]+1]))
            seg_delta = float(np.mean(delta_pow[indices[0]:indices[-1]+1]))
            alpha_ratio = seg_alpha / alpha_bl_nrem if alpha_bl_nrem > 0 else 0
            beta_ratio  = seg_beta  / beta_bl_nrem  if beta_bl_nrem  > 0 else 0
            band_powers = {"alpha": seg_alpha, "theta": seg_theta, "beta": seg_beta}
            dominant_band = max(band_powers, key=band_powers.get)
            if _is_rem(stage):
                dominant_band = "alpha"

            arousals.append({
                "onset_s":       _safe(onset_s),
                "end_s":         _safe(end_s),
                "duration_s":    _safe(dur_s),
                "stage":         stage,
                "epoch":         ep_idx,
                "dominant_band": dominant_band,
                "alpha_ratio":   _safe(alpha_ratio, 2),
                "beta_ratio":    _safe(beta_ratio, 2),
                "onset_ratio":   _safe(onset_ratio, 2),
                "emg_confirmed": emg_confirmed,
                "cvr_boost":     _safe(cvr_boost, 2),
                "type":          "spontaneous",
            })

        # ── Statistieken ─────────────────────────────────────────
        total_sleep_s = sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                            if _is_sleep(s) and i not in artifact_set)
        total_sleep_h = max(total_sleep_s / 3600, 0.001)
        rem_h  = max(sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                         if _is_rem(s) and i not in artifact_set) / 3600, 0.001)
        nrem_h = max(sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                         if _is_nrem(s) and i not in artifact_set) / 3600, 0.001)

        nrem_ar = [a for a in arousals if _is_nrem(a["stage"])]
        rem_ar  = [a for a in arousals if _is_rem(a["stage"])]

        result["events"]  = arousals
        result["summary"] = {
            "n_arousals":          len(arousals),
            "arousal_index":       _safe(len(arousals) / total_sleep_h),
            "nrem_arousal_index":  _safe(len(nrem_ar) / nrem_h),
            "rem_arousal_index":   _safe(len(rem_ar)  / rem_h),
            "avg_duration_s":      _safe(float(np.mean([a["duration_s"]
                                          for a in arousals]))) if arousals else None,
            "severity":            _classify_arousal_index(
                                       len(arousals) / total_sleep_h),
            # v0.8.11: extra stats
            "n_theta_dominant":    sum(1 for a in arousals if a["dominant_band"] == "theta"),
            "n_alpha_dominant":    sum(1 for a in arousals if a["dominant_band"] == "alpha"),
            "n_beta_dominant":     sum(1 for a in arousals if a["dominant_band"] == "beta"),
            "n_emg_confirmed":     sum(1 for a in arousals if a["emg_confirmed"]),
        }
        result["success"] = True

        # v0.9.8: LGBM filter applied after the rule-based body has
        # populated result["events"] / result["summary"]. We post-filter
        # with the model and recompute the summary; the rule-based output
        # is still available under result["pre_lgbm_n_arousals"] for
        # diagnostics.
        if _hybrid and result.get("events"):
            try:
                eeg_uv_for_lgbm = eeg_data.copy()
                if np.max(np.abs(eeg_uv_for_lgbm)) < 0.01:
                    eeg_uv_for_lgbm = eeg_uv_for_lgbm * 1e6
                emg_uv_for_lgbm = None
                if emg_data is not None:
                    emg_uv_for_lgbm = emg_data[:n_samples].copy()
                    if np.max(np.abs(emg_uv_for_lgbm)) < 0.01:
                        emg_uv_for_lgbm = emg_uv_for_lgbm * 1e6
                kept, proba = _filter_candidates_with_lgbm(
                    result["events"], eeg_uv_for_lgbm, sf,
                    emg_uv_for_lgbm, len(hypno),
                    threshold=AROUSAL_LGBM_THRESHOLD,
                )
                n_pre = len(result["events"])
                result["pre_lgbm_n_arousals"] = n_pre
                result["events"] = kept
                result["summary"] = _recompute_arousal_summary(
                    kept, hypno, set(artifact_epochs or []),
                )
                result["summary"]["lgbm_threshold"] = AROUSAL_LGBM_THRESHOLD
                result["summary"]["lgbm_n_pre"]     = n_pre
                result["summary"]["lgbm_n_post"]    = len(kept)
                logger.info(
                    "[arousal] LGBM filter: %d candidates → %d kept "
                    "(threshold %.2f)", n_pre, len(kept), AROUSAL_LGBM_THRESHOLD,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("[arousal] LGBM filter failed: %s; "
                               "falling back to rule-based output", e)
                result["lgbm_error"] = str(e)

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    finally:
        # Always restore the module globals so concurrent / subsequent
        # callers see the original rule-based values.
        AROUSAL_RATIO_THRESH = _saved_ratio
        ABRUPT_RATIO_THRESH  = _saved_abrupt
    return result


def _classify_arousal_index(ai: float) -> str:
    if ai is None:
        return "unknown"
    if ai < 10:   return "normal"
    if ai < 20:   return "mildly_elevated"
    if ai < 40:   return "moderately_elevated"
    return "severely_elevated"


# ═══════════════════════════════════════════════════════════════
# RESPIRATOIR-AROUSAL KOPPELING
# ═══════════════════════════════════════════════════════════════

def correlate_arousals_to_respiratory(
    arousals:       list,
    resp_events:    list,
    window_pre_s:   float = 5.0,
    window_post_s:  float = POST_RESP_WINDOW_S,
) -> dict:
    """
    Koppel arousals aan voorafgaande respiratoire events.

    AASM definitie respiratoire arousal:
      Arousal die optreedt binnen 15s na het EINDE van een apnea of hypopnea.

    Geeft terug:
      - Respiratoire arousals (gekoppeld aan event)
      - Spontane arousals (geen respiratoir verband)
      - Per respiratoir event: had het een arousal? Latentie?
      - Statistieken: % events met arousal, gemiddelde arousal-latentie
    """
    result = {
        "success":            False,
        "respiratory_arousals": [],
        "spontaneous_arousals": [],
        "resp_events_with_arousal": [],
        "summary":            {},
        "error":              None,
    }
    try:
        if not arousals or not resp_events:
            result["success"] = True
            result["summary"] = _empty_correlation_summary()
            return result

        # Markeer arousals als respiratoir indien ze binnen venster vallen
        ar_annotated = []
        for ar in arousals:
            ar_copy = dict(ar)
            ar_copy["linked_event"] = None
            ar_copy["arousal_latency_s"] = None

            ar_onset = ar["onset_s"] or 0

            # Zoek respiratoir event dat eindigde in [onset - window_pre ... onset + window_post]
            best_match = None
            best_latency = float("inf")

            for ev in resp_events:
                ev_end = (ev.get("onset_s") or 0) + (ev.get("duration_s") or 0)
                # Latentie = arousal_onset - event_end (positief = na event)
                latency = ar_onset - ev_end

                if -window_pre_s <= latency <= window_post_s:
                    if abs(latency) < abs(best_latency):
                        best_latency = latency
                        best_match   = ev

            if best_match is not None:
                ar_copy["type"]               = "respiratory"
                ar_copy["linked_event_type"]  = best_match.get("type")
                ar_copy["linked_event_onset"] = best_match.get("onset_s")
                ar_copy["linked_event_dur"]   = best_match.get("duration_s")
                ar_copy["arousal_latency_s"]  = _safe(best_latency)
                result["respiratory_arousals"].append(ar_copy)
            else:
                ar_copy["type"] = "spontaneous"
                result["spontaneous_arousals"].append(ar_copy)

            ar_annotated.append(ar_copy)

        # Update originele events: had elk respiratoir event een arousal?
        for ev in resp_events:
            ev_end     = (ev.get("onset_s") or 0) + (ev.get("duration_s") or 0)
            ev_annotated = dict(ev)
            ev_annotated["had_arousal"] = False
            ev_annotated["arousal_latency_s"] = None

            for ar in result["respiratory_arousals"]:
                if ar.get("linked_event_onset") == ev.get("onset_s"):
                    ev_annotated["had_arousal"]        = True
                    ev_annotated["arousal_latency_s"]  = ar.get("arousal_latency_s")
                    break

            result["resp_events_with_arousal"].append(ev_annotated)

        # ── Statistieken ─────────────────────────────────────────
        n_resp_ar = len(result["respiratory_arousals"])
        n_spont   = len(result["spontaneous_arousals"])
        n_total   = n_resp_ar + n_spont
        n_resp_ev = len(resp_events)
        n_ev_with_ar = sum(1 for ev in result["resp_events_with_arousal"]
                           if ev["had_arousal"])

        latencies = [ar["arousal_latency_s"]
                     for ar in result["respiratory_arousals"]
                     if ar.get("arousal_latency_s") is not None]

        # Per event-type
        type_stats = {}
        for ev_type in ("obstructive","central","mixed","hypopnea",
                        "hypopnea_central"):
            ev_of_type = [e for e in resp_events if e.get("type") == ev_type]
            ar_for_type = [e for e in result["resp_events_with_arousal"]
                           if e.get("type") == ev_type and e.get("had_arousal")]
            if ev_of_type:
                type_stats[ev_type] = {
                    "n_events":      len(ev_of_type),
                    "n_with_arousal": len(ar_for_type),
                    "arousal_rate":   _safe(len(ar_for_type) /
                                           len(ev_of_type) * 100),
                }

        result["summary"] = {
            "n_respiratory_arousals":   n_resp_ar,
            "n_spontaneous_arousals":   n_spont,
            "n_total_arousals":         n_total,
            "pct_respiratory":          _safe(n_resp_ar / n_total * 100) if n_total > 0 else 0,
            "pct_spontaneous":          _safe(n_spont   / n_total * 100) if n_total > 0 else 0,
            # Koppeling met respiratoire events
            "n_resp_events_total":      n_resp_ev,
            "n_resp_events_with_arousal": n_ev_with_ar,
            "pct_events_with_arousal":  _safe(n_ev_with_ar / n_resp_ev * 100) if n_resp_ev > 0 else 0,
            # Latentie (seconden na event-einde)
            "avg_arousal_latency_s":    _safe(float(np.mean(latencies))) if latencies else None,
            "min_arousal_latency_s":    _safe(float(np.min(latencies)))  if latencies else None,
            "max_arousal_latency_s":    _safe(float(np.max(latencies)))  if latencies else None,
            # Per event-type
            "by_event_type":            type_stats,
            # Klinische interpretatie
            "clinical_interpretation":  _interpret_arousal_coupling(
                n_resp_ar, n_spont, n_ev_with_ar, n_resp_ev,
                float(np.mean(latencies)) if latencies else None),
        }
        result["arousals_annotated"] = ar_annotated
        result["success"] = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


def _empty_correlation_summary() -> dict:
    return {
        "n_respiratory_arousals": 0, "n_spontaneous_arousals": 0,
        "n_total_arousals": 0, "pct_respiratory": 0,
        "n_resp_events_total": 0, "n_resp_events_with_arousal": 0,
        "pct_events_with_arousal": 0, "by_event_type": {},
        "clinical_interpretation": [],
    }


def _interpret_arousal_coupling(
    n_resp: int, n_spont: int,
    n_ev_with_ar: int, n_ev_total: int,
    avg_latency: float | None,
) -> list:
    """
    Genereer klinische interpretatie van het arousal-respiratoir verband.
    """
    msgs = []
    total = n_resp + n_spont

    if total == 0:
        return [{"level":"info","msg":"Geen arousals gedetecteerd."}]

    resp_pct   = n_resp / total * 100 if total > 0 else 0
    ev_ar_pct  = n_ev_with_ar / n_ev_total * 100 if n_ev_total > 0 else 0

    # Overheersend respiratoir
    if resp_pct >= 70:
        msgs.append({
            "level": "warning",
            "code":  "PREDOMINANTLY_RESPIRATORY",
            "msg":   f"{resp_pct:.0f}% van alle arousals is respiratoir van origine. "
                     "Slaapfragmentatie wordt gedomineerd door apnea/hypopnea-gerelateerde "
                     "ontwakingen — sterk argument voor nCPAP-therapie.",
        })
    elif resp_pct >= 40:
        msgs.append({
            "level": "info",
            "code":  "SIGNIFICANT_RESPIRATORY",
            "msg":   f"{resp_pct:.0f}% van de arousals is respiratoir. "
                     "Respiratoire events dragen significant bij aan slaapfragmentatie.",
        })
    else:
        msgs.append({
            "level": "info",
            "code":  "PREDOMINANTLY_SPONTANEOUS",
            "msg":   f"Meerderheid arousals ({100-resp_pct:.0f}%) is spontaan "
                     "(niet direct respiratoir). Overweeg andere oorzaken: "
                     "PLM, pijn, licht/geluid, medicatie.",
        })

    # Hoog percentage events met arousal
    if ev_ar_pct >= 60:
        msgs.append({
            "level": "warning",
            "code":  "HIGH_EVENT_AROUSAL_RATE",
            "msg":   f"{ev_ar_pct:.0f}% van de respiratoire events gaat gepaard met "
                     "een arousal. Ernstige slaapfragmentatie — hoge kans op "
                     "overmatige slaperigheid overdag (EDS/ESS).",
        })

    # Korte latentie = directe arousal = goede corticale respons
    if avg_latency is not None:
        if avg_latency < 5:
            msgs.append({
                "level": "info",
                "code":  "SHORT_AROUSAL_LATENCY",
                "msg":   f"Gemiddelde arousal-latentie {avg_latency:.1f}s — "
                         "snelle corticale respons op respiratoire stress. "
                         "Typisch bij licht-tot-matig OSAS.",
            })
        elif avg_latency > 12:
            msgs.append({
                "level": "warning",
                "code":  "LONG_AROUSAL_LATENCY",
                "msg":   f"Verlengde arousal-latentie ({avg_latency:.1f}s). "
                         "Vertraagde corticale arousal kan wijzen op verminderd "
                         "arousability — risicofactor bij ernstig OSAS.",
            })

    return msgs


# ═══════════════════════════════════════════════════════════════
# RERA DETECTIE  (Respiratory Effort Related Arousals)
# ═══════════════════════════════════════════════════════════════

def detect_reras(
    flow_data:    np.ndarray,
    flow_norm:    np.ndarray,
    sf_flow:      float,
    arousals:     list,
    resp_events:  list,
    hypno:        list,
    artifact_epochs: list = None,
) -> dict:
    """
    Detecteer RERAs conform AASM 2.6, Sectie 3E.

    RERA = sequentie van ademhalingen met:
      1. Toenemende inspiratoire inspanning (flow plateau of crescendo-effort)
      2. ZONDER apnea of hypopnea drempel te bereiken (flow > 70% basislijn)
      3. Eindigend met een arousal
      4. Duur ≥10s

    Flow-limitatie criterium (plateau):
      Normaal: sinusvormige inspiratoire flow
      Gelimiteerd: afgeplatte top (plateau) = hogere bovenste luchtweg-weerstand
      Detectie: top-flatness ratio < 0.85 (verhouding piek/gemiddelde van inspiratie)
    """
    result = {"success": False, "events": [], "summary": {}, "error": None}
    try:
        # ── Detecteer flow-limitatie periodes ──
        flow_limited_mask = _detect_flow_limitation(flow_norm, sf_flow)

        # ── Verbind met slaap ──
        sleep_stages = {"N1","N2","N3","R",1,2,3,4}
        spe = int(sf_flow * EPOCH_LEN_S)
        sleep_mask = np.zeros(len(flow_norm), dtype=bool)
        for ep_i, stage in enumerate(hypno):
            if stage in sleep_stages:
                s = ep_i * spe
                e = min(s + spe, len(sleep_mask))
                sleep_mask[s:e] = True

        # ── Label flow-limitatie segmenten ──
        labeled, n_seg = label(flow_limited_mask & sleep_mask)
        rera_candidates = []

        for i in range(1, n_seg + 1):
            indices = np.where(labeled == i)[0]
            dur_s   = len(indices) / sf_flow
            if dur_s < RERA_MIN_DUR_S:
                continue

            onset_s = float(indices[0])  / sf_flow
            end_s   = float(indices[-1]) / sf_flow
            ep_idx  = int(onset_s // EPOCH_LEN_S)
            stage   = hypno[ep_idx] if ep_idx < len(hypno) else "W"

            rera_candidates.append({
                "onset_s":   _safe(onset_s),
                "end_s":     _safe(end_s),
                "duration_s": _safe(dur_s),
                "stage":     stage,
                "epoch":     ep_idx,
            })

        # ── Filter: alleen kandidaten die NIET overlappen met apnea/hypopnea ──
        confirmed_reras = []
        for cand in rera_candidates:
            overlap = False
            for ev in resp_events:
                ev_start = ev.get("onset_s", 0)
                ev_end   = ev_start + (ev.get("duration_s", 0))
                c_start  = cand["onset_s"] or 0
                c_end    = cand["end_s"]   or 0
                # Overlapping check
                if c_start < ev_end and c_end > ev_start:
                    overlap = True
                    break
            if overlap:
                continue

            # ── Vereiste: eindigend met arousal (binnen 10s) ──
            c_end = cand["end_s"] or 0
            has_arousal = False
            linked_arousal = None
            for ar in arousals:
                ar_onset = ar.get("onset_s", 0)
                if 0 <= ar_onset - c_end <= 10.0:
                    has_arousal    = True
                    linked_arousal = ar_onset
                    break

            if has_arousal:
                cand["linked_arousal_onset"] = linked_arousal
                confirmed_reras.append(cand)

        # ── Statistieken ──
        _art_set = set(artifact_epochs or [])
        total_sleep_s = sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                            if _is_sleep(s) and i not in _art_set)
        total_sleep_h = max(total_sleep_s / 3600, 0.001)

        result["events"]  = confirmed_reras
        result["summary"] = {
            "n_reras":     len(confirmed_reras),
            "rera_index":  _safe(len(confirmed_reras) / total_sleep_h),
            "rdi":         _safe((len(resp_events) + len(confirmed_reras))
                                  / total_sleep_h),  # RDI = AHI + RERA-index
        }
        result["success"] = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


def _detect_flow_limitation(flow_norm: np.ndarray, sf: float) -> np.ndarray:
    """
    Detecteer flow-limitatie (plateau-vormige inspiratoire flow).

    Methode:
      Per ademhaling (0.5–4s periodes):
        - Piek flow bepalen
        - Top-flatness: verhouding gemiddelde van bovenste 50% / piek
        - Als flatness > 0.85 = normale top
        - Als flatness < 0.75 = afgeplatte top = flow-limitatie
    """
    limited = np.zeros(len(flow_norm), dtype=bool)

    # Splits in vermoedelijke inspiratoire cycli via pieken
    min_cycle_samples = int(0.5 * sf)
    max_cycle_samples = int(4.0 * sf)

    # Smooth signaal voor piekdetectie
    win = max(1, int(sf * 0.5))
    smooth = np.convolve(flow_norm, np.ones(win)/win, mode="same")

    # Vind lokale maxima (inspiratoire pieken)
    # (find_peaks geïmporteerd bovenaan module — v0.8.40)
    peaks, _ = find_peaks(smooth,
                          distance=min_cycle_samples,
                          height=0.40)  # minimale flow = 40% basislijn

    for pk in peaks:
        # Zoek het omringende inspiratoire segment (van dal naar dal)
        # v0.8.40: Bounded search voorkomt oneindige lus bij
        # monotoon stijgend/dalend signaal (slecht gekalibreerde sensor)
        max_extend = int(2.0 * sf)  # max 2s aan elke kant zoeken
        left  = pk
        right = pk
        steps = 0
        while left > 0 and smooth[left-1] < smooth[left] and steps < max_extend:
            left -= 1
            steps += 1
        steps = 0
        while right < len(smooth)-1 and smooth[right+1] < smooth[right] and steps < max_extend:
            right += 1
            steps += 1

        seg_len = right - left
        if seg_len < min_cycle_samples or seg_len > max_cycle_samples:
            continue

        seg = smooth[left:right+1]
        piek = float(np.max(seg))
        if piek < 0.40:
            continue

        # Top-flatness: gemiddelde van stalen > 75% van piek
        top_mask = seg > 0.75 * piek
        if not np.any(top_mask):
            continue

        flatness = float(np.mean(seg[top_mask])) / piek

        # Plateau = flatness < 0.80 (top is afgeplat)
        if flatness < 0.80:
            limited[left:right+1] = True

    # Smooth de mask (verwijder korte artefacten)
    from scipy.ndimage import binary_closing, binary_opening
    limited = binary_closing(limited,  structure=np.ones(int(sf)))
    limited = binary_opening(limited, structure=np.ones(int(sf * 2)))

    # Zorg dat flow-limitatie niet optreedt tijdens diepe apnea
    limited[flow_norm < 0.40] = False

    return limited


# ═══════════════════════════════════════════════════════════════
# GECOMBINEERDE ANALYSE + SAMENVATTING
# ═══════════════════════════════════════════════════════════════

def run_arousal_respiratory_analysis(
    eeg_data:    np.ndarray,
    sf_eeg:      float,
    flow_data:   np.ndarray | None,
    flow_norm:   np.ndarray | None,
    sf_flow:     float | None,
    resp_events: list,
    hypno:       list,
    emg_data:    np.ndarray | None = None,
    artifact_epochs: list = None,
    hr_data:     np.ndarray | None = None,
    sf_hr:       float = 1.0,
) -> dict:
    """
    Master-functie: detecteer arousals, RERAs en koppel aan respiratoire events.

    Parameters
    ----------
    eeg_data    : primair EEG-kanaal (al geselecteerd, in μV)
    sf_eeg      : samplefrequentie EEG
    flow_data   : luchtstroom-signaal (voor RERA)
    flow_norm   : genormaliseerde luchtstroom (0–1, voor RERA)
    sf_flow     : samplefrequentie luchtstroom
    resp_events : lijst van respiratoire events uit detect_respiratory_events()
    hypno       : slaapfase-lijst
    emg_data    : optioneel chin-EMG signaal voor REM arousal criterium
    artifact_epochs : epoch-indices met artefacten (uitgesloten uit detectie + indices)

    Returns
    -------
    dict met arousals, koppeling, RERAs en samenvatting
    """
    output = {"success": False, "error": None}

    # ── Stap 1: Arousals detecteren ──────────────────────────────
    logger.info("[arousal 1/3] EEG-arousal detectie...")
    ar_result = detect_arousals(eeg_data, sf_eeg, hypno, emg_data=emg_data,
                                artifact_epochs=artifact_epochs,
                                hr_data=hr_data, sf_hr=sf_hr)
    output["arousals"] = ar_result

    arousals = ar_result.get("events", [])

    # ── Stap 2: Koppeling met respiratoire events ─────────────────
    logger.info("[arousal 2/3] Respiratoir-arousal koppeling...")
    corr_result = correlate_arousals_to_respiratory(arousals, resp_events)
    output["coupling"] = corr_result

    # Update arousal-events met type-annotaties
    if corr_result.get("arousals_annotated"):
        output["arousals"]["events"] = corr_result["arousals_annotated"]

    # ── Stap 3: RERA detectie ─────────────────────────────────────
    logger.info("[arousal 3/3] RERA detectie...")
    if flow_data is not None and flow_norm is not None and sf_flow is not None:
        rera_result = detect_reras(
            flow_data, flow_norm, sf_flow,
            arousals, resp_events, hypno,
            artifact_epochs=artifact_epochs)
        output["reras"] = rera_result
    else:
        output["reras"] = {
            "success": False,
            "error": "Geen luchtstroom-data voor RERA",
            "events": [], "summary": {"n_reras": 0, "rera_index": 0, "rdi": None},
        }

    # ── Gecombineerde samenvatting ────────────────────────────────
    ar_sum   = ar_result.get("summary",   {})
    cor_sum  = corr_result.get("summary", {})
    rera_sum = output["reras"].get("summary", {})

    output["summary"] = {
        # Arousal totalen
        "arousal_index":              ar_sum.get("arousal_index"),
        "nrem_arousal_index":         ar_sum.get("nrem_arousal_index"),
        "rem_arousal_index":          ar_sum.get("rem_arousal_index"),
        "arousal_severity":           ar_sum.get("severity"),

        # Respiratoir-arousal verband
        "n_respiratory_arousals":     cor_sum.get("n_respiratory_arousals"),
        "n_spontaneous_arousals":     cor_sum.get("n_spontaneous_arousals"),
        "pct_respiratory_arousals":   cor_sum.get("pct_respiratory"),
        "pct_events_with_arousal":    cor_sum.get("pct_events_with_arousal"),
        "avg_arousal_latency_s":      cor_sum.get("avg_arousal_latency_s"),
        "by_event_type":              cor_sum.get("by_event_type", {}),

        # RERAs
        "n_reras":                    rera_sum.get("n_reras", 0),
        "rera_index":                 rera_sum.get("rera_index", 0),
        "rdi":                        rera_sum.get("rdi"),

        # Klinische interpretatie
        "clinical_interpretation":    cor_sum.get("clinical_interpretation", []),
    }

    output["success"] = True
    logger.info("Arousal-analyse voltooid.")
    return output
