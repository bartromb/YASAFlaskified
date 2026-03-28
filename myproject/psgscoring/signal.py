"""
psgscoring.signal
=================
Signal preprocessing and baseline estimation for respiratory channels.

Functions in this module accept plain NumPy arrays and a sample rate; they do
NOT depend on MNE or the rest of the YASAFlaskified stack.

Dependencies: numpy, scipy, psgscoring.constants, psgscoring.utils
"""

from __future__ import annotations
import numpy as np
from scipy import signal as sp_signal
from scipy.ndimage import median_filter

from .constants import BASELINE_WINDOW_S, EPOCH_LEN_S
from .utils import is_nrem, is_rem, safe_r


# ---------------------------------------------------------------------------
# Nasal pressure linearization  (AASM 2.6 Rule 3)
# ---------------------------------------------------------------------------

def linearize_nasal_pressure(data: np.ndarray) -> np.ndarray:
    """
    Square-root transformation of a nasal pressure signal.

    Nasal pressure is proportional to flow² (Bernoulli).  Without correction
    a true 50 % flow reduction appears as a 75 % amplitude reduction, leading
    to systematic hypopnea over-scoring.

    Formula: sign(x) * sqrt(|x|)  — sign-preserving, maintains
    inspiration-positive / expiration-negative polarity.

    References
    ----------
    Montserrat et al., AJRCCM 2001 (r²=0.88–0.96 vs pneumotachography).
    Thurnheer et al., AJRCCM 2001.
    AASM Scoring Manual 2.6 Rule 3.
    """
    return np.sign(data) * np.sqrt(np.abs(data))


# ---------------------------------------------------------------------------
# MMSD  — Mean Magnitude of Second Derivative
# ---------------------------------------------------------------------------

def compute_mmsd(
    flow_data: np.ndarray,
    sf: float,
    window_s: float = 1.0,
) -> np.ndarray:
    """
    Drift-independent measure of respiratory effort.

    The second derivative amplifies rapid oscillations (breathing) while
    suppressing slow baseline drift.  Useful to reject false-positive apneas
    caused by sensor drift rather than true airflow cessation.

    References
    ----------
    Lee et al., Physiol Meas 2008 — 92 % agreement, κ=0.78 on 24 PSGs.
    """
    d2  = np.diff(flow_data, n=2)
    d2  = np.concatenate([[0], d2, [0]])          # restore original length
    win = max(1, int(sf * window_s))
    return np.convolve(np.abs(d2), np.ones(win) / win, mode="same")


# ---------------------------------------------------------------------------
# Flow preprocessing pipeline
# ---------------------------------------------------------------------------

def bandpass_flow(flow_data: np.ndarray, sf: float) -> np.ndarray:
    """
    3rd-order Butterworth bandpass 0.05–3 Hz, zero-phase.

    Retains the raw waveform (no envelope) for zero-crossing breath
    segmentation.  The 3 Hz upper cutoff removes snoring vibrations
    (50–200 Hz) before any downstream flattening-index computation.
    """
    nyq = sf / 2
    lo  = max(0.05 / nyq, 0.001)
    hi  = min(3.0  / nyq, 0.99)
    b, a = sp_signal.butter(3, [lo, hi], btype="band")
    return sp_signal.filtfilt(b, a, flow_data)


def preprocess_flow(
    flow_data: np.ndarray,
    sf: float,
    is_nasal_pressure: bool = False,
) -> np.ndarray:
    """
    Full flow preprocessing: [linearize ->] bandpass -> Hilbert envelope -> 1 s smooth.

    Parameters
    ----------
    flow_data         : raw signal array
    sf                : sample rate (Hz)
    is_nasal_pressure : if True, apply sqrt-linearization before filtering
                        (AASM 2.6 Rule 3; use for hypopnea channel only)
    """
    if is_nasal_pressure:
        flow_data = linearize_nasal_pressure(flow_data)
    filtered = bandpass_flow(flow_data, sf)
    envelope = np.abs(sp_signal.hilbert(filtered))
    win      = max(1, int(sf))                        # 1-second smoothing
    return np.convolve(envelope, np.ones(win) / win, mode="same")


def preprocess_effort(effort_data: np.ndarray, sf: float) -> np.ndarray:
    """
    Thorax / abdomen RIP preprocessing: bandpass 0.05–2 Hz -> amplitude envelope.
    """
    nyq = sf / 2
    lo  = max(0.03 / nyq, 0.001)
    hi  = min(2.0  / nyq, 0.99)
    b, a = sp_signal.butter(3, [lo, hi], btype="band")
    filtered = sp_signal.filtfilt(b, a, effort_data)
    envelope = np.abs(sp_signal.hilbert(filtered))
    win      = max(1, int(sf * 2))
    return np.convolve(envelope, np.ones(win) / win, mode="same")


# ---------------------------------------------------------------------------
# Baseline estimation
# ---------------------------------------------------------------------------

def compute_dynamic_baseline(
    flow_env: np.ndarray,
    sf: float,
    window_s: int = BASELINE_WINDOW_S,
) -> np.ndarray:
    """
    Per-sample dynamic baseline via a 5-minute sliding window (95th pct).

    Sampled every 10 s then linearly interpolated: ~2 500× faster than
    per-sample computation (2 880 vs 7.4 M iterations for 8 h @ 256 Hz).

    Segments at or below 30 % of the local 95th percentile are excluded from
    the baseline computation to prevent apnea periods from suppressing it.
    """
    win  = int(window_s * sf)
    n    = len(flow_env)
    step = max(1, int(sf * 10))          # anchor every 10 s

    sample_points   = np.arange(0, n, step)
    baseline_sparse = np.empty(len(sample_points))

    for idx, center in enumerate(sample_points):
        start = max(0, center - win // 2)
        end   = min(n, center + win // 2)
        seg   = flow_env[start:end]
        p95   = np.percentile(seg, 95)
        stable = seg[seg > 0.30 * p95]
        baseline_sparse[idx] = (
            np.percentile(stable, 95) if len(stable) > 10 else p95
        )

    baseline = np.interp(np.arange(n), sample_points, baseline_sparse)
    return np.maximum(baseline, 1e-6)



def compute_anchor_baseline(
    flow_env: np.ndarray,
    sf: float,
    hypno: list,
    events: list | None = None,
    artifact_epochs: list | None = None,
    min_stable_epochs: int = 6,
) -> dict:
    """
    v0.8.11 — Baseline Anchoring.

    Zoek periodes van stabiele, event-vrije N2-slaap en bereken het
    absolute RMS-vermogen als "Gouden Standaard Basislijn" voor deze
    specifieke patiënt.

    Dit lost het probleem op van de mond-ademer: als de neusbril-flow
    structureel lager ligt dan de anker-basislijn (>40% daling), geeft
    dit een waarschuwing en verlaagt het de hypopnea-confidence.

    Parameters
    ----------
    flow_env        : preprocessed flow envelope
    sf              : sample rate
    hypno           : slaapstadia per epoch
    events          : gedetecteerde events (voor event-vrij masker)
    artifact_epochs : te vermijden epochs

    Returns
    -------
    dict met:
        anchor_value        : float — absolute RMS anker-basislijn
        anchor_epochs_used  : int   — aantal N2 epochs gebruikt
        anchor_reliable     : bool  — True als >= min_stable_epochs
        anchor_ratio        : float — verhouding huidig signaal / anker
        mouth_breathing_suspected : bool
    """
    artifact_set  = set(artifact_epochs or [])
    spe           = int(sf * EPOCH_LEN_S)
    n             = len(flow_env)

    # Bouw event-masker: samples binnen 30s van een event worden uitgesloten
    event_mask = np.zeros(n, dtype=bool)
    for ev in (events or []):
        onset  = int(ev.get("onset_s", 0) * sf)
        end    = int((ev.get("onset_s", 0) + ev.get("duration_s", 0)) * sf)
        margin = int(30 * sf)
        event_mask[max(0, onset - margin) : min(n, end + margin)] = True

    # Zoek stabiele N2-epochs zonder events en artefacten
    anchor_rms_values: list[float] = []
    for ep_i, stage in enumerate(hypno):
        if stage not in ("N2", 2):
            continue
        if ep_i in artifact_set:
            continue
        sl = ep_i * spe
        el = min(sl + spe, n)
        if np.any(event_mask[sl:el]):
            continue
        seg = flow_env[sl:el]
        if len(seg) < spe // 2:
            continue
        rms = float(np.sqrt(np.mean(seg ** 2)))
        if rms > 1e-6:
            anchor_rms_values.append(rms)

    if len(anchor_rms_values) < min_stable_epochs:
        return {
            "anchor_value":             None,
            "anchor_epochs_used":       len(anchor_rms_values),
            "anchor_reliable":          False,
            "anchor_ratio":             None,
            "mouth_breathing_suspected": False,
        }

    # Gebruik mediaan (robuust tegen uitschieters)
    anchor_val = float(np.median(anchor_rms_values))

    # Huidig gemiddeld signaalvermogen over gehele opname
    valid = flow_env[flow_env > 1e-6]
    current_rms = float(np.sqrt(np.mean(valid ** 2))) if len(valid) > 0 else anchor_val
    anchor_ratio = current_rms / max(anchor_val, 1e-9)

    # Mond-ademer: signaal structureel >40% lager dan anker
    mouth_breathing_suspected = anchor_ratio < 0.60

    return {
        "anchor_value":              safe_r(anchor_val, 4),
        "anchor_epochs_used":        len(anchor_rms_values),
        "anchor_reliable":           True,
        "anchor_ratio":              safe_r(anchor_ratio, 3),
        "mouth_breathing_suspected": mouth_breathing_suspected,
    }

def compute_stage_baseline(
    flow_env: np.ndarray,
    sf: float,
    hypno: list,
    artifact_epochs: list | None = None,
    dynamic_baseline: np.ndarray | None = None,
) -> np.ndarray:
    """
    Stage-specific baseline: separate 90th-percentile estimates for
    NREM and REM (REM is physiologically more variable).

    Falls back to the dynamic baseline when insufficient stage data exist.
    A 5 s cosine-ramp smooths transitions between adjacent stage epochs.

    Parameters
    ----------
    dynamic_baseline : voorberekende dynamische basislijn (optioneel).
        Als opgegeven wordt compute_dynamic_baseline() niet opnieuw aangeroepen.
    """
    artifact_set = set(artifact_epochs or [])
    spe = int(sf * EPOCH_LEN_S)
    n   = len(flow_env)
    n_epochs = len(hypno)
    hypno_arr = np.array(hypno)
    ep_indices = np.arange(n_epochs)

    artifact_mask_ep = np.zeros(n_epochs, dtype=bool)
    if artifact_set:
        valid_art = [i for i in artifact_set if i < n_epochs]
        if valid_art:
            artifact_mask_ep[valid_art] = True

    stage_bl: dict[str, float] = {}
    for stage in ("N1", "N2", "N3", "R"):
        stage_ep = (hypno_arr == stage) & ~artifact_mask_ep
        if not stage_ep.any():
            continue
        sample_mask = np.repeat(stage_ep, spe)[:n]
        samples = flow_env[sample_mask]
        if len(samples) > int(sf * 30):
            p30    = float(np.percentile(samples, 30))
            stable = samples[samples > p30]
            if len(stable) > 10:
                stage_bl[stage] = float(np.percentile(stable, 90))

    global_bl = dynamic_baseline if dynamic_baseline is not None else compute_dynamic_baseline(flow_env, sf)

    if not stage_bl:
        return global_bl.copy()

    ep_values   = np.empty(n_epochs)
    use_global  = np.ones(n_epochs, dtype=bool)
    for stage, val in stage_bl.items():
        mask = hypno_arr == stage
        ep_values[mask] = val
        use_global[mask] = False

    if use_global.any():
        ug_idx = ep_indices[use_global]
        ep_values[use_global] = np.array([
            float(np.median(global_bl[i*spe : min((i+1)*spe, n)]))
            for i in ug_idx
        ])

    baseline = np.repeat(ep_values, spe)[:n]
    win      = max(1, int(sf * 5))
    baseline = np.convolve(baseline, np.ones(win) / win, mode="same")
    return np.maximum(baseline, 1e-6)


# ---------------------------------------------------------------------------
# Position-aware baseline reset
# ---------------------------------------------------------------------------

def detect_position_changes(
    pos_data: np.ndarray,
    sf: float,
    min_stable_s: float = 30.0,
) -> list[dict]:
    """
    Detect body-position changes in the position channel.

    Uses a median filter to remove momentary flicker, then requires that the
    new position be stable for at least *min_stable_s* seconds before the
    change is recorded.

    Returns
    -------
    list of dicts: {sample, time_s, from, to}
    """
    if pos_data is None or len(pos_data) < int(sf * 60):
        return []

    pos_q      = np.round(pos_data).astype(int)
    win        = max(3, int(sf * 5)) | 1           # odd window for median
    pos_smooth = median_filter(pos_q, size=win)

    changes  = []
    prev_pos = pos_smooth[0]

    for i in range(1, len(pos_smooth)):
        if pos_smooth[i] != prev_pos:
            check_end   = min(i + int(min_stable_s * sf), len(pos_smooth))
            stable_seg  = pos_smooth[i:check_end]
            if (
                len(stable_seg) > int(sf * 10) and
                np.sum(stable_seg == pos_smooth[i]) > 0.8 * len(stable_seg)
            ):
                changes.append({
                    "sample": i,
                    "time_s": i / sf,
                    "from":   int(prev_pos),
                    "to":     int(pos_smooth[i]),
                })
                prev_pos = pos_smooth[i]

    return changes


def reset_baseline_at_position_changes(
    baseline: np.ndarray,
    flow_env: np.ndarray,
    sf: float,
    pos_changes: list[dict],
    recalc_window_s: float = 60.0,
) -> np.ndarray:
    """
    After a body-position change, recompute the local baseline from the
    first *recalc_window_s* seconds in the new position.

    A 10 s linear ramp smooths the transition to prevent artefactual
    step-changes in the normalised flow signal.
    """
    if not pos_changes:
        return baseline

    result = baseline.copy()
    n      = len(flow_env)

    for change in pos_changes:
        sample      = change["sample"]
        recalc_end  = min(sample + int(recalc_window_s * sf), n)
        seg         = flow_env[sample:recalc_end]
        if len(seg) < int(sf * 10):
            continue

        stable   = seg[seg > np.percentile(seg, 30)]
        new_bl   = float(
            np.percentile(stable, 90) if len(stable) > 10
            else np.percentile(seg, 90)
        )

        ramp_samp = min(int(sf * 10), recalc_end - sample)
        for i in range(ramp_samp):
            idx = sample + i
            if idx < n:
                alpha       = i / ramp_samp
                result[idx] = (1 - alpha) * result[idx] + alpha * new_bl

        result[sample + ramp_samp : recalc_end] = new_bl

    return result
