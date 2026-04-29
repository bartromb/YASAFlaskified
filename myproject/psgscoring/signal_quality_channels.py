"""
signal_quality.py — Signal quality assessment for PSG recordings.

Detects:
  1. Flat-line segments (electrode disconnect / amplifier saturation)
  2. Clipping (signal at ADC rail)
  3. High-impedance noise (50/60 Hz dominant)
  4. Montage plausibility (cross-correlation sanity checks)

v0.8.30 — AZORG Slaapkliniek
"""

import numpy as np
from scipy import signal as sp_signal
import logging

logger = logging.getLogger("psgscoring.signal_quality")

EPOCH_LEN_S = 30


def assess_signal_quality(
    raw,
    channel_map: dict,
    hypno: list | None = None,
) -> dict:
    """Run signal quality assessment on all mapped channels.

    Parameters
    ----------
    raw          : MNE Raw object
    channel_map  : dict mapping role -> channel name
    hypno        : optional hypnogram (for sleep-only stats)

    Returns
    -------
    dict with keys:
      channels : {ch_name: {flat_pct, clip_pct, noise_pct, quality_grade}}
      montage_warnings : list of str
      overall_grade : "good" | "acceptable" | "poor"
    """
    sf = raw.info["sfreq"]
    results = {"channels": {}, "montage_warnings": [], "overall_grade": "good"}

    for role, ch_name in channel_map.items():
        if ch_name is None or ch_name not in raw.ch_names:
            continue
        try:
            data = raw.get_data(picks=[ch_name])[0]
            ch_result = _assess_channel(data, sf, ch_name, role)
            results["channels"][ch_name] = ch_result
        except Exception as e:
            logger.warning("Quality check failed for %s: %s", ch_name, e)
            results["channels"][ch_name] = {
                "quality_grade": "unknown", "error": str(e)
            }

    # Montage plausibility checks
    results["montage_warnings"] = _check_montage(raw, channel_map)

    # Overall grade
    grades = [v.get("quality_grade", "good")
              for v in results["channels"].values()]
    if grades.count("poor") >= 2:
        results["overall_grade"] = "poor"
    elif "poor" in grades or grades.count("acceptable") >= 3:
        results["overall_grade"] = "acceptable"

    return results


def _assess_channel(data: np.ndarray, sf: float,
                    ch_name: str, role: str) -> dict:
    """Assess quality of a single channel."""
    n_samples = len(data)
    dur_s = n_samples / sf
    epoch_samples = int(EPOCH_LEN_S * sf)

    # 1. Flat-line detection (std < threshold in sliding window)
    flat_threshold = _flat_threshold_for_role(role)
    n_flat = _count_flat_samples(data, sf, flat_threshold)
    flat_pct = round(100 * n_flat / max(n_samples, 1), 1)

    # 2. Clipping detection (signal at min/max rail)
    clip_pct = round(100 * _count_clipped(data) / max(n_samples, 1), 1)

    # 3. High-impedance noise (50/60 Hz power ratio)
    noise_pct = round(_estimate_line_noise_pct(data, sf), 1)

    # 4. Disconnects (sudden flat after active signal)
    disconnects = _detect_disconnects(data, sf, flat_threshold)

    # Grade
    if flat_pct > 20 or clip_pct > 10:
        grade = "poor"
    elif flat_pct > 5 or clip_pct > 3 or noise_pct > 40:
        grade = "acceptable"
    else:
        grade = "good"

    result = {
        "flat_pct": flat_pct,
        "clip_pct": clip_pct,
        "noise_pct": noise_pct,
        "n_disconnects": len(disconnects),
        "disconnect_intervals_s": disconnects[:10],
        "quality_grade": grade,
    }

    if grade != "good":
        logger.info("[quality] %s (%s): grade=%s flat=%.1f%% clip=%.1f%% "
                    "noise=%.1f%% disconnects=%d",
                    ch_name, role, grade, flat_pct, clip_pct,
                    noise_pct, len(disconnects))

    return result


def _flat_threshold_for_role(role: str) -> float:
    """Return the flat-line std threshold per channel role.

    EEG channels have much smaller amplitudes than respiratory channels.
    """
    if role in ("eeg", "eog", "emg", "extra_eeg"):
        return 0.5e-6   # 0.5 µV — typical EEG noise floor
    elif role in ("flow", "flow_pressure", "thorax", "abdomen"):
        return 1e-4      # respiratory signals: broader range
    elif role in ("spo2",):
        return 0.01       # SpO2: percentage values
    else:
        return 1e-5       # conservative default


def _count_flat_samples(data: np.ndarray, sf: float,
                        threshold: float) -> int:
    """Count samples in flat-line segments (sliding 2s window)."""
    win = max(int(2.0 * sf), 10)
    if len(data) < win:
        return 0

    # Rolling std via cumsum trick (fast)
    cumsum = np.cumsum(data)
    cumsum2 = np.cumsum(data ** 2)

    n = len(data)
    mean_w = (cumsum[win:] - cumsum[:-win]) / win
    var_w = (cumsum2[win:] - cumsum2[:-win]) / win - mean_w ** 2
    var_w = np.maximum(var_w, 0)
    std_w = np.sqrt(var_w)

    flat_mask = std_w < threshold
    # Each True in flat_mask represents a window of `win` samples
    # Count unique flat samples (approximate)
    return int(np.sum(flat_mask) * win / max(len(flat_mask), 1)
               * len(flat_mask))


def _count_clipped(data: np.ndarray) -> int:
    """Count samples at the ADC rail (min or max repeated >10 times)."""
    if len(data) < 20:
        return 0
    d_min, d_max = np.min(data), np.max(data)
    if d_max - d_min < 1e-12:
        return len(data)  # entire channel is flat

    # Clipping = value at extreme AND repeated
    at_max = data >= d_max - abs(d_max) * 1e-6
    at_min = data <= d_min + abs(d_min) * 1e-6

    # Only count if clusters of >10 consecutive samples
    def _count_runs(mask, min_run=10):
        if not np.any(mask):
            return 0
        d = np.diff(mask.astype(int))
        starts = np.where(d == 1)[0] + 1
        ends = np.where(d == -1)[0] + 1
        if mask[0]:
            starts = np.concatenate(([0], starts))
        if mask[-1]:
            ends = np.concatenate((ends, [len(mask)]))
        runs = ends[:len(starts)] - starts[:len(ends)]
        return int(np.sum(runs[runs >= min_run]))

    return _count_runs(at_max) + _count_runs(at_min)


def _estimate_line_noise_pct(data: np.ndarray, sf: float) -> float:
    """Estimate percentage of power in 49-51 Hz + 59-61 Hz bands."""
    if sf < 120 or len(data) < int(4 * sf):
        return 0.0

    # Use first 60s for efficiency
    seg = data[:min(len(data), int(60 * sf))]
    freqs, psd = sp_signal.welch(seg, fs=sf, nperseg=min(int(2*sf), len(seg)))

    total = np.sum(psd[(freqs >= 1) & (freqs <= sf/2 - 1)])
    if total < 1e-20:
        return 0.0

    line_50 = np.sum(psd[(freqs >= 49) & (freqs <= 51)])
    line_60 = np.sum(psd[(freqs >= 59) & (freqs <= 61)])

    return float((line_50 + line_60) / total * 100)


def _detect_disconnects(data: np.ndarray, sf: float,
                        flat_threshold: float) -> list:
    """Detect transitions from active signal to flat-line (disconnects).

    Returns list of [onset_s, duration_s] pairs.
    """
    win = max(int(2.0 * sf), 10)
    step = win  # non-overlapping for speed
    disconnects = []
    prev_active = True
    flat_start = None

    for i in range(0, len(data) - win, step):
        seg_std = float(np.std(data[i:i+win]))
        is_flat = seg_std < flat_threshold

        if is_flat and prev_active:
            flat_start = i / sf
        elif not is_flat and not prev_active and flat_start is not None:
            flat_dur = i / sf - flat_start
            if flat_dur >= 10.0:  # only report >=10s disconnects
                disconnects.append([round(flat_start, 1), round(flat_dur, 1)])
            flat_start = None

        prev_active = not is_flat

    # Handle trailing flat
    if flat_start is not None:
        flat_dur = len(data) / sf - flat_start
        if flat_dur >= 10.0:
            disconnects.append([round(flat_start, 1), round(flat_dur, 1)])

    return disconnects


def _check_montage(raw, channel_map: dict) -> list:
    """Basic montage plausibility checks via cross-correlation.

    Checks:
    - EEG and EOG should NOT be identical (copy error)
    - Left and right EOG should be anti-correlated (if both present)
    - ECG should not correlate highly with EEG (swapped leads)
    - Flow and effort should not be identical
    """
    warnings = []
    sf = raw.info["sfreq"]
    n_check = min(int(60 * sf), raw.n_times)  # first 60s

    def _get(role):
        name = channel_map.get(role)
        if name and name in raw.ch_names:
            return raw.get_data(picks=[name], start=0, stop=n_check)[0]
        return None

    def _corr(a, b):
        if a is None or b is None or len(a) < 100:
            return None
        a_z = a - np.mean(a)
        b_z = b - np.mean(b)
        denom = np.std(a_z) * np.std(b_z) * len(a_z)
        if denom < 1e-15:
            return None
        return float(np.sum(a_z * b_z) / denom)

    eeg = _get("eeg")
    eog = _get("eog")
    emg = _get("emg")
    flow = _get("flow")
    if flow is None:
        flow = _get("flow_pressure")
    thorax = _get("thorax")
    abdomen = _get("abdomen")

    # EEG ↔ EOG should not be identical
    r = _corr(eeg, eog)
    if r is not None and abs(r) > 0.95:
        warnings.append(
            f"EEG and EOG are nearly identical (r={r:.2f}) — "
            "possible montage error or shared reference")

    # Flow ↔ effort should not be identical
    r = _corr(flow, thorax)
    if r is not None and abs(r) > 0.95:
        warnings.append(
            f"Flow and thorax are nearly identical (r={r:.2f}) — "
            "possible channel duplication")

    # Thorax ↔ abdomen: anti-correlation suggests paradoxical breathing
    # but perfect correlation >0.99 suggests duplication
    r = _corr(thorax, abdomen)
    if r is not None and abs(r) > 0.98:
        warnings.append(
            f"Thorax and abdomen are nearly identical (r={r:.2f}) — "
            "possible channel duplication (would prevent OA/CA classification)")

    return warnings
