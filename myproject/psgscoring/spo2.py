"""
psgscoring.spo2
===============
SpO2 analysis: ODI, time-below thresholds, desaturation detection,
and per-event desaturation coupling (AASM 2.6 Rule 1A / Uddin 2021).

Dependencies: numpy, scipy, psgscoring.constants, psgscoring.utils
"""

from __future__ import annotations
import traceback

import numpy as np
from scipy.ndimage import label, maximum_filter1d

from .constants import EPOCH_LEN_S
from .utils import build_sleep_mask, fmt_time, hypno_to_numeric, is_nrem, is_rem, safe_r


# ---------------------------------------------------------------------------
# Per-event SpO2 coupling
# ---------------------------------------------------------------------------

def get_desaturation(
    spo2_data: np.ndarray | None,
    onset_s: float,
    dur_s: float,
    sf_spo2: float,
    global_spo2_baseline: float | None = None,
    post_win_s: float = 45,
) -> tuple[float | None, float | None]:
    """
    Compute SpO2 desaturation associated with a respiratory event.

    AASM criteria:
    - Baseline = 90th percentile of 120 s pre-event window
    - Nadir search window = event onset -> post_win_s after event end
    - Nadir must occur >= 3 s after event onset (circulatory delay)
    - Very early nadir with < 5 % drop -> rejected as coincidental

    For severe OSAS the pre-event window may already be desaturated; the
    *global_spo2_baseline* (95th pct of all sleep SpO2) is used when it
    exceeds the local baseline.

    Returns
    -------
    (desaturation_pct, min_spo2)  – both None if no valid SpO2 data.
    """
    if spo2_data is None:
        return None, None
    try:
        POST_WIN_S = post_win_s  # v0.8.15: configureerbaar via scoring profile
        s_start = max(0, int(onset_s * sf_spo2))
        s_end   = min(len(spo2_data),
                      int((onset_s + dur_s + POST_WIN_S) * sf_spo2))
        seg = spo2_data[s_start:s_end]
        seg = seg[(seg >= 50) & (seg <= 100)]
        if len(seg) < 3:
            return None, None

        pre_s   = max(0, int((onset_s - 120) * sf_spo2))
        pre_seg = spo2_data[pre_s:s_start]
        pre_seg = pre_seg[(pre_seg >= 50) & (pre_seg <= 100)]
        spo2_bl = (
            float(np.percentile(pre_seg, 90)) if len(pre_seg) > 3
            else float(np.percentile(seg, 90))
        )
        if global_spo2_baseline is not None and global_spo2_baseline > spo2_bl:
            spo2_bl = global_spo2_baseline

        min_spo2  = float(np.min(seg))
        desat     = spo2_bl - min_spo2
        nadir_idx = int(np.argmin(seg))

        # Reject very early nadirs with small desaturation
        if nadir_idx < int(3 * sf_spo2) and desat < 5:
            return None, safe_r(min_spo2)

        return safe_r(desat), safe_r(min_spo2)
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Full SpO2 analysis
# ---------------------------------------------------------------------------

def analyze_spo2(
    spo2_data: np.ndarray,
    sf: float,
    hypno: list,
) -> dict:
    """
    Compute ODI, time-below thresholds, and individual desaturation events.

    Returns a result dict with keys: success, summary, desaturations, error.
    """
    result: dict = {"success": False, "summary": {}, "desaturations": [], "error": None}
    try:
        spo2_clean = spo2_data.copy().astype(float)
        spo2_clean[(spo2_clean < 50) | (spo2_clean > 100)] = np.nan

        sleep_mask  = build_sleep_mask(hypno, sf, len(spo2_clean))
        spo2_sleep  = spo2_clean[sleep_mask]
        spo2_sleep  = spo2_sleep[~np.isnan(spo2_sleep)]

        if len(spo2_sleep) == 0:
            result["error"] = "No usable SpO2 data during sleep"
            return result

        total_sleep_s = float(np.sum(sleep_mask)) / sf
        total_sleep_h = max(total_sleep_s / 3600, 0.001)
        baseline_spo2 = float(np.percentile(spo2_sleep, 90))

        def pct_below(thresh: float):
            """Bereken het percentage van de tijd dat SpO2 onder een drempel valt."""
            n_below = np.sum(spo2_sleep < thresh)
            t_s     = float(n_below) / sf
            pct     = t_s / total_sleep_s * 100 if total_sleep_s > 0 else 0.0
            return safe_r(pct), fmt_time(t_s)

        pct90, t90 = pct_below(90)
        pct80, t80 = pct_below(80)
        pct70, t70 = pct_below(70)

        desaturations_3pct = detect_desaturations(spo2_clean, sf, sleep_mask, drop_pct=3.0)
        desaturations_4pct = detect_desaturations(spo2_clean, sf, sleep_mask, drop_pct=4.0)
        desaturations = desaturations_3pct  # backward compat

        odi_3pct = safe_r(len(desaturations_3pct) / total_sleep_h)
        odi_4pct = safe_r(len(desaturations_4pct) / total_sleep_h)

        # REM / NREM split
        hypno_num = hypno_to_numeric(hypno)
        spe       = int(sf * EPOCH_LEN_S)
        rem_mask  = np.zeros(len(spo2_clean), dtype=bool)
        nrem_mask = np.zeros(len(spo2_clean), dtype=bool)
        for ep_i, stage in enumerate(hypno_num):
            s = ep_i * spe
            e = min(s + spe, len(rem_mask))
            if is_rem(stage):
                rem_mask[s:e]  = True
            elif is_nrem(stage):
                nrem_mask[s:e] = True

        def stage_spo2_stats(mask: np.ndarray):
            """Bereken SpO2-statistieken per slaapstadium (gemiddelde, nadir, ODI)."""
            seg = spo2_clean[mask]
            seg = seg[~np.isnan(seg)]
            if len(seg) == 0:
                return None, None, None
            dur   = float(np.sum(mask)) / sf
            t90_s = float(np.sum(seg < 90)) / sf
            pct   = t90_s / dur * 100 if dur > 0 else 0
            return safe_r(pct), fmt_time(t90_s), safe_r(float(np.min(seg)))

        rem_p90,  rem_t90,  rem_min  = stage_spo2_stats(rem_mask)
        nrem_p90, nrem_t90, nrem_min = stage_spo2_stats(nrem_mask)

        _avg = safe_r(float(np.nanmean(spo2_sleep)))
        result["summary"] = {
            "baseline_spo2":      safe_r(baseline_spo2),
            "min_spo2":           safe_r(float(np.nanmin(spo2_sleep))),
            "avg_spo2":           _avg,
            "mean_spo2":          _avg,           # v0.8.22: alias voor PDF
            "n_desaturations":    len(desaturations),
            "desat_index":        odi_3pct,
            "odi_3pct":           odi_3pct,       # v0.8.22: ODI ≥3%
            "odi_4pct":           odi_4pct,       # v0.8.22: ODI ≥4%
            "n_desat_3pct":       len(desaturations_3pct),
            "n_desat_4pct":       len(desaturations_4pct),
            "pct_below_90":       pct90,
            "time_below_90":      t90,
            "pct_below_80":       pct80,
            "time_below_80":      t80,
            "pct_below_70":       pct70,
            "time_below_70":      t70,
            "total_sleep_s":      safe_r(total_sleep_s),
            "rem_pct_below_90":   rem_p90,
            "rem_time_below_90":  rem_t90,
            "rem_min_spo2":       rem_min,
            "nrem_pct_below_90":  nrem_p90,
            "nrem_time_below_90": nrem_t90,
            "nrem_min_spo2":      nrem_min,
        }
        result["desaturations"] = desaturations[:200]
        # v0.8.12: 1-Hz timeseries for PDF overview plot
        step = max(1, int(sf))  # downsample to ~1 Hz
        result["timeseries"] = spo2_clean[::step].tolist()
        result["success"]       = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


def detect_desaturations(
    spo2: np.ndarray,
    sf: float,
    sleep_mask: np.ndarray,
    drop_pct: float = 3.0,
) -> list[dict]:
    """
    Identify contiguous desaturation episodes (>= *drop_pct* % below
    the 60 s rolling maximum) using vectorised rolling-max approximation.
    """
    win         = max(1, int(sf * 3))
    spo2_smooth = np.convolve(
        np.nan_to_num(spo2, nan=95.0),
        np.ones(win) / win, mode="same",
    )
    baseline_win  = int(sf * 60)
    rolling_peak  = maximum_filter1d(
        spo2_smooth, size=baseline_win, origin=-baseline_win // 2
    )
    desat_mask = (spo2_smooth <= rolling_peak - drop_pct) & sleep_mask

    events: list[dict] = []
    labeled, n_ev = label(desat_mask)
    for i in range(1, n_ev + 1):
        idx = np.where(labeled == i)[0]
        if len(idx) < int(sf * 3):
            continue
        nadir = float(np.min(spo2_smooth[idx[0] : idx[-1] + 1]))
        peak  = float(rolling_peak[idx[0]])
        drop  = peak - nadir
        if drop >= drop_pct:
            events.append({
                "onset_s":    safe_r(idx[0] / sf),
                "duration_s": safe_r(len(idx) / sf),
                "nadir_spo2": safe_r(nadir),
                "drop_pct":   safe_r(drop),
            })
    return events
