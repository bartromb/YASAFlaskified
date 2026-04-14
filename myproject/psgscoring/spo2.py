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
# Hypoxic burden  (Azarbarzin et al., Eur Heart J 2019; AJRCCM 2023)
# ---------------------------------------------------------------------------

def _ensemble_search_window(
    spo2: np.ndarray,
    sf_spo2: float,
    resp_events: list,
    pre_s: float = 60.0,
    post_s: float = 60.0,
) -> tuple:
    """
    Compute a subject-specific search window from the ensemble average
    of time-aligned SpO2 curves (Azarbarzin et al. 2019, Fig. 1).

    All SpO2 segments are synchronised at event termination ("time zero")
    and averaged.  The two peaks flanking the nadir of the ensemble curve
    define the search window: left peak → right peak.

    Returns
    -------
    (left_offset_s, right_offset_s, ensemble_curve, time_axis)
        Offsets are in seconds relative to event termination (negative =
        before termination).  Returns (None, None, None, None) if fewer
        than 3 events are available.
    """
    n_spo2 = len(spo2)
    pre_samp = int(pre_s * sf_spo2)
    post_samp = int(post_s * sf_spo2)
    total_samp = pre_samp + post_samp

    segments = []
    for ev in resp_events:
        onset_s = float(ev.get("onset_s", 0))
        dur_s = float(ev.get("duration_s", 0))
        if dur_s <= 0:
            continue
        # time zero = event termination
        t0 = int((onset_s + dur_s) * sf_spo2)
        seg_start = t0 - pre_samp
        seg_end = t0 + post_samp
        if seg_start < 0 or seg_end > n_spo2:
            continue
        seg = spo2[seg_start:seg_end].copy()
        # skip if >50% NaN
        if np.sum(np.isnan(seg)) > 0.5 * len(seg):
            continue
        # interpolate NaNs for averaging
        nans = np.isnan(seg)
        if np.any(nans) and not np.all(nans):
            seg[nans] = np.interp(
                np.flatnonzero(nans), np.flatnonzero(~nans), seg[~nans]
            )
        segments.append(seg)

    if len(segments) < 3:
        return None, None, None, None

    ensemble = np.nanmean(np.array(segments), axis=0)
    time_axis = np.arange(total_samp) / sf_spo2 - pre_s  # relative to t0

    # Smooth lightly (3s moving average) to suppress noise
    win = max(1, int(3 * sf_spo2))
    if win > 1 and len(ensemble) > win:
        kernel = np.ones(win) / win
        ensemble_sm = np.convolve(ensemble, kernel, mode="same")
    else:
        ensemble_sm = ensemble

    # Find nadir of ensemble
    nadir_idx = int(np.nanargmin(ensemble_sm))

    # Left peak: max of ensemble before nadir
    left_region = ensemble_sm[:nadir_idx] if nadir_idx > 0 else ensemble_sm[:1]
    left_peak_idx = int(np.nanargmax(left_region))

    # Right peak: max of ensemble after nadir
    right_region = ensemble_sm[nadir_idx:] if nadir_idx < len(ensemble_sm) else ensemble_sm[-1:]
    right_peak_idx = nadir_idx + int(np.nanargmax(right_region))

    # Convert to seconds relative to event termination
    left_offset_s = time_axis[left_peak_idx]
    right_offset_s = time_axis[min(right_peak_idx, len(time_axis) - 1)]

    # Sanity: left must be before right, window must be reasonable
    if left_offset_s >= right_offset_s or (right_offset_s - left_offset_s) < 5:
        # Fallback: -30s to +30s around termination
        left_offset_s = -30.0
        right_offset_s = 30.0

    return left_offset_s, right_offset_s, ensemble, time_axis


def compute_hypoxic_burden(
    spo2_data: np.ndarray,
    sf_spo2: float,
    resp_events: list,
    hypno: list,
    recovery_margin_pct: float = 1.0,
    max_recovery_s: float = 120.0,
    baseline_method: str = "percentile",
) -> dict:
    """
    Compute the hypoxic burden: total area of SpO2 desaturation
    associated with respiratory events, normalised per hour of sleep.

    Parameters
    ----------
    spo2_data : array
        Raw SpO2 signal.
    sf_spo2 : float
        Sampling frequency of the SpO2 signal (Hz).
    resp_events : list[dict]
        Respiratory events from detect_respiratory_events(), each with
        'onset_s', 'duration_s', 'desaturation_pct'.
    hypno : list
        Epoch-level sleep staging.
    recovery_margin_pct : float
        SpO2 must recover to baseline - margin to end integration (default 1%).
    max_recovery_s : float
        Maximum seconds after event end to search for recovery (default 120 s).
    baseline_method : str
        Method for computing the per-event SpO2 baseline:

        - ``"percentile"`` (default): 90th percentile of 120 s pre-event
          window with global 95th-percentile fallback.  Simple, robust,
          validated by He et al. (2023) as comparable to ensemble method.

        - ``"ensemble"`` (Azarbarzin original): Subject-specific search
          window derived from the ensemble average of all time-aligned
          SpO2 curves.  The pre-event baseline is the SpO2 at the left
          peak of the ensemble curve.  Area is integrated within the
          ensemble-derived search window.

    Returns
    -------
    dict with keys:
        hypoxic_burden       – total burden in %·min / h of sleep
        total_area_pct_s     – summed area in %·seconds (before normalisation)
        n_events_with_burden – number of events contributing
        mean_event_burden    – average burden per event (%·s)
        unit                 – '%·min/h'
        baseline_method      – which method was actually used
        ensemble_window_s    – (ensemble only) [left, right] offsets in s

    References
    ----------
    Azarbarzin A, et al. The hypoxic burden of sleep apnoea predicts
    cardiovascular disease-related mortality. Eur Heart J. 2019;40(14):
    1149-1157.

    He S, Cistulli PA, de Chazal P. Comparison of oximetry event
    desaturation transient area-based methods. IEEE EMBC 2024.
    """
    result = {
        "hypoxic_burden": None,
        "total_area_pct_s": 0.0,
        "n_events_with_burden": 0,
        "mean_event_burden": 0.0,
        "unit": "%·min/h",
        "baseline_method": baseline_method,
    }

    if spo2_data is None or len(resp_events) == 0 or sf_spo2 <= 0:
        return result

    try:
        spo2 = spo2_data.astype(float)
        spo2[(spo2 < 50) | (spo2 > 100)] = np.nan
        n_spo2 = len(spo2)

        # Total sleep time
        sleep_mask = build_sleep_mask(hypno, sf_spo2, n_spo2)
        tst_h = float(np.sum(sleep_mask)) / sf_spo2 / 3600
        if tst_h < 0.1:
            return result

        # Global baseline (95th pct of sleep SpO2)
        spo2_sleep = spo2[sleep_mask]
        spo2_sleep = spo2_sleep[~np.isnan(spo2_sleep)]
        if len(spo2_sleep) < 10:
            return result
        global_bl = float(np.percentile(spo2_sleep, 95))

        # ── Ensemble method: compute search window ────────────────
        use_ensemble = (baseline_method == "ensemble")
        ens_left_s, ens_right_s = None, None
        if use_ensemble:
            ens_left_s, ens_right_s, _, _ = _ensemble_search_window(
                spo2, sf_spo2, resp_events,
                pre_s=60.0, post_s=60.0,
            )
            if ens_left_s is None:
                # Not enough events for ensemble → fall back to percentile
                use_ensemble = False
                result["baseline_method"] = "percentile (ensemble fallback)"
            else:
                result["ensemble_window_s"] = [
                    safe_r(ens_left_s, 1), safe_r(ens_right_s, 1)
                ]

        total_area = 0.0
        n_burden = 0

        _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

        for ev in resp_events:
            onset_s = float(ev.get("onset_s", 0))
            dur_s = float(ev.get("duration_s", 0))
            if dur_s <= 0:
                continue

            event_end_s = onset_s + dur_s

            if use_ensemble:
                # ── Ensemble baseline + search window ─────────────
                # Search window: [event_end + left_offset, event_end + right_offset]
                win_start_s = event_end_s + ens_left_s
                win_end_s = event_end_s + ens_right_s

                win_start_idx = max(0, int(win_start_s * sf_spo2))
                win_end_idx = min(n_spo2, int(win_end_s * sf_spo2))
                if win_start_idx >= win_end_idx:
                    continue

                seg = spo2[win_start_idx:win_end_idx].copy()
                seg_valid = ~np.isnan(seg)
                if np.sum(seg_valid) < 2:
                    continue

                # Baseline: SpO2 at start of search window (first valid samples)
                bl_region = seg[:max(1, int(3 * sf_spo2))]
                bl_valid = bl_region[~np.isnan(bl_region)]
                if len(bl_valid) > 0:
                    baseline = float(np.max(bl_valid))
                else:
                    baseline = global_bl

                # Area: integral of (baseline - SpO2) within search window
                deficit = np.zeros(len(seg))
                deficit[seg_valid] = np.maximum(0, baseline - seg[seg_valid])
                area = float(_trapz(deficit, dx=1.0 / sf_spo2))

            else:
                # ── Percentile baseline + recovery window ─────────
                # Pre-event baseline: 90th pct of 120 s before event
                pre_start = max(0, int((onset_s - 120) * sf_spo2))
                pre_end = max(0, int(onset_s * sf_spo2))
                pre_seg = spo2[pre_start:pre_end]
                pre_seg = pre_seg[(~np.isnan(pre_seg)) & (pre_seg >= 50)]
                if len(pre_seg) > 3:
                    local_bl = float(np.percentile(pre_seg, 90))
                else:
                    local_bl = global_bl
                baseline = max(local_bl, global_bl)

                # Integration window: event onset → recovery or max_recovery_s
                int_start = int(onset_s * sf_spo2)
                int_end_max = min(n_spo2, int((event_end_s + max_recovery_s) * sf_spo2))
                if int_start >= int_end_max:
                    continue

                seg = spo2[int_start:int_end_max].copy()
                seg_valid = ~np.isnan(seg)

                # Find recovery point
                event_end_idx = int(dur_s * sf_spo2)
                recovery_idx = len(seg)
                recovery_thresh = baseline - recovery_margin_pct
                for k in range(min(event_end_idx, len(seg)), len(seg)):
                    if seg_valid[k] and seg[k] >= recovery_thresh:
                        recovery_idx = k + 1
                        break

                seg_area = seg[:recovery_idx].copy()
                valid = ~np.isnan(seg_area)
                if np.sum(valid) < 2:
                    continue

                deficit = np.zeros(len(seg_area))
                deficit[valid] = np.maximum(0, baseline - seg_area[valid])
                area = float(_trapz(deficit, dx=1.0 / sf_spo2))

            if area > 0:
                total_area += area
                n_burden += 1

        # Normalise: %·s → %·min/h
        burden_pct_min_h = (total_area / 60.0) / tst_h if tst_h > 0 else 0.0

        result["hypoxic_burden"] = safe_r(burden_pct_min_h, 2)
        result["total_area_pct_s"] = safe_r(total_area, 1)
        result["n_events_with_burden"] = n_burden
        result["mean_event_burden"] = (
            safe_r(total_area / n_burden, 1) if n_burden > 0 else 0.0
        )

    except Exception as e:
        result["error"] = str(e)

    return result


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
            # v0.2.5: Low baseline warning for COPD/OHS overlap
            "low_baseline_warning": baseline_spo2 < 88.0,
            "low_baseline_note": (
                "Baseline SpO₂ < 88%: consider COPD/OHS overlap. "
                "The 3% desaturation criterion may undercount events; "
                "absolute SpO₂ thresholds (T90, T80) are more informative."
            ) if baseline_spo2 < 88.0 else None,
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
