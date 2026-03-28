"""
psgscoring.plm
==============
Periodic Limb Movement (PLM) detection per AASM 2.6 criteria.

AASM criteria summary
---------------------
- Leg Movement (LM): EMG >= 8 µV above resting, duration 0.5–10 s
- Bilateral LMs within 0.5 s -> merged to one LM
- PLM series: >= 4 consecutive LMs, inter-movement interval 5–90 s
- Wake LMs excluded; respiratory-associated LMs excluded
- PLMI: PLMs per hour of sleep (significant >= 15/h)

Dependencies: numpy, scipy, psgscoring.constants, psgscoring.utils
"""

from __future__ import annotations
import numpy as np
from scipy import signal as sp_signal
from scipy.ndimage import label

from .constants import EPOCH_LEN_S
from .utils import safe_r

# AASM thresholds
LM_MIN_DUR_S       = 0.5
LM_MAX_DUR_S       = 10.0
LM_AMPLITUDE_UV    = 8.0     # µV above resting EMG
PLM_MIN_INTERVAL_S = 5.0
PLM_MAX_INTERVAL_S = 90.0
PLM_MIN_SERIES     = 4
BILATERAL_WIN_S    = 0.5
RESP_EXCLUSION_S   = 0.5     # LM within 0.5 s of resp event end -> excluded


def analyze_plm(
    leg_l: np.ndarray | None,
    leg_r: np.ndarray | None,
    sf: float,
    hypno: list,
    resp_events: list | None = None,
    artifact_epochs: list | None = None,
) -> dict:
    """
    Detect PLMs on left and/or right tibialis anterior EMG channels.

    Parameters
    ----------
    leg_l / leg_r   : raw EMG arrays (Volt or µV; auto-converted)
    sf              : sample rate
    hypno           : string hypnogram
    resp_events     : respiratory events (used for resp-associated exclusion)
    artifact_epochs : epochs to exclude from TST denominator

    Returns
    -------
    dict with keys: success, summary, events, series, error
    """
    result: dict = {"success": False, "summary": {}, "events": [], "error": None}
    try:
        if leg_l is None and leg_r is None:
            result["error"] = "No leg-EMG channels available"
            return result

        lms_l = _detect_lm_channel(leg_l, sf) if leg_l is not None else []
        lms_r = _detect_lm_channel(leg_r, sf) if leg_r is not None else []
        all_lms = _merge_bilateral(lms_l, lms_r)
        all_lms.sort(key=lambda x: x["onset_s"])

        # Tag with sleep stage; filter wake
        sleep_lms: list[dict] = []
        for lm in all_lms:
            ep_idx  = int(lm["onset_s"] // EPOCH_LEN_S)
            stage   = hypno[ep_idx] if ep_idx < len(hypno) else "W"
            lm["stage"] = stage
            lm["epoch"] = ep_idx
            if stage != "W":
                sleep_lms.append(lm)

        # Respiratory-associated exclusion
        resp_ends = [
            float(e["onset_s"]) + float(e["duration_s"])
            for e in (resp_events or [])
            if "onset_s" in e and "duration_s" in e
        ]
        plm_eligible, n_resp = _exclude_resp_associated(sleep_lms, resp_ends)

        # PLM series detection
        plm_series, plm_count = _detect_series(plm_eligible)

        # Mark PLM membership
        for lm in plm_eligible:
            lm["is_plm"] = False
        for series in plm_series:
            for lm in plm_eligible:
                if series["start_s"] <= lm["onset_s"] <= series["end_s"]:
                    lm["is_plm"] = True

        artifact_set  = set(artifact_epochs or [])
        total_sleep_s = sum(
            EPOCH_LEN_S for i, s in enumerate(hypno)
            if s != "W" and i not in artifact_set
        )
        total_sleep_h = max(total_sleep_s / 3600, 0.001)

        plmi = safe_r(plm_count / total_sleep_h)
        lmi  = safe_r(len(sleep_lms) / total_sleep_h)

        result["events"]  = plm_eligible[:200]
        result["series"]  = plm_series
        result["summary"] = {
            "n_lm_total":        len(all_lms),
            "n_lm_sleep":        len(sleep_lms),
            "n_lm_wake":         len(all_lms) - len(sleep_lms),
            "n_resp_associated": n_resp,
            "n_plm_eligible":    len(plm_eligible),
            "n_plm":             plm_count,
            "n_plm_series":      len(plm_series),
            "lm_index":          lmi,
            "plm_index":         plmi,
            "plm_severity":      _classify_plmi(plmi),
            "total_sleep_h":     safe_r(total_sleep_h),
        }
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _detect_lm_channel(data: np.ndarray, sf: float) -> list[dict]:
    """Detect LM events on a single EMG channel (AASM 2.6)."""
    # Auto-convert Volt -> µV if signal is clearly in Volt
    data_uv = data.copy()
    if np.max(np.abs(data_uv)) < 0.1:
        data_uv = data_uv * 1e6

    nyq = sf / 2
    lo  = min(10.0 / nyq, 0.99)
    hi  = min(100.0 / nyq, 0.99)
    if lo >= hi:
        lo, hi = 0.1, 0.99
    b, a = sp_signal.butter(4, [lo, hi], btype="band")
    filt = sp_signal.filtfilt(b, a, data_uv)

    win = max(1, int(sf * 0.1))
    n_w = len(filt) // win
    rms = np.array([
        np.sqrt(np.mean(filt[i * win : (i + 1) * win] ** 2))
        for i in range(n_w)
    ])

    resting   = float(np.percentile(rms, 10))
    threshold = resting + LM_AMPLITUDE_UV

    labeled, n_bursts = label(rms > threshold)
    lms: list[dict] = []
    for i in range(1, n_bursts + 1):
        idx   = np.where(labeled == i)[0]
        dur_s = len(idx) * 0.1
        if LM_MIN_DUR_S <= dur_s <= LM_MAX_DUR_S:
            lms.append({
                "onset_s":     idx[0] * 0.1,
                "duration_s":  round(dur_s, 2),
                "amplitude_uv": round(float(np.max(rms[idx])), 1),
            })
    return lms


def _merge_bilateral(
    lms_l: list[dict],
    lms_r: list[dict],
) -> list[dict]:
    """Merge bilateral LMs (within 0.5 s) into a single LM."""
    used_r: set[int] = set()
    merged: list[dict] = []

    for lm in lms_l:
        found = False
        for j, rlm in enumerate(lms_r):
            if j in used_r:
                continue
            if abs(lm["onset_s"] - rlm["onset_s"]) <= BILATERAL_WIN_S:
                merged.append({
                    "onset_s":      min(lm["onset_s"],     rlm["onset_s"]),
                    "duration_s":   max(lm["duration_s"],  rlm["duration_s"]),
                    "amplitude_uv": max(lm["amplitude_uv"], rlm["amplitude_uv"]),
                    "bilateral":    True,
                })
                used_r.add(j)
                found = True
                break
        if not found:
            merged.append({**lm, "bilateral": False})

    for j, rlm in enumerate(lms_r):
        if j not in used_r:
            merged.append({**rlm, "bilateral": False})

    return merged


def _exclude_resp_associated(
    sleep_lms: list[dict],
    resp_ends: list[float],
) -> tuple[list[dict], int]:
    """Remove LMs within 0.5 s of a respiratory-event end."""
    eligible: list[dict] = []
    n_resp = 0
    for lm in sleep_lms:
        onset   = lm["onset_s"]
        is_resp = any(
            (re - RESP_EXCLUSION_S) <= onset <= (re + RESP_EXCLUSION_S)
            for re in resp_ends
        )
        lm["resp_associated"] = is_resp
        if is_resp:
            n_resp += 1
        else:
            eligible.append(lm)
    return eligible, n_resp


def _detect_series(
    plm_eligible: list[dict],
) -> tuple[list[dict], int]:
    """Identify PLM series (>= 4 LMs with 5–90 s intervals)."""
    series: list[dict] = []
    count = 0
    if len(plm_eligible) < PLM_MIN_SERIES:
        return series, count

    seq = [plm_eligible[0]]
    for j in range(1, len(plm_eligible)):
        interval = plm_eligible[j]["onset_s"] - plm_eligible[j - 1]["onset_s"]
        if PLM_MIN_INTERVAL_S <= interval <= PLM_MAX_INTERVAL_S:
            seq.append(plm_eligible[j])
        else:
            if len(seq) >= PLM_MIN_SERIES:
                count += len(seq)
                series.append(_series_dict(seq))
            seq = [plm_eligible[j]]
    if len(seq) >= PLM_MIN_SERIES:
        count += len(seq)
        series.append(_series_dict(seq))

    return series, count


def _series_dict(seq: list[dict]) -> dict:
    return {
        "start_s": seq[0]["onset_s"],
        "end_s":   seq[-1]["onset_s"] + seq[-1]["duration_s"],
        "n_lms":   len(seq),
    }


def _classify_plmi(plmi: float | None) -> str:
    if plmi is None or plmi == 0:
        return "normal"
    if plmi < 5:
        return "normal"
    if plmi < 15:
        return "mild"
    if plmi < 25:
        return "moderate"
    return "severe"
