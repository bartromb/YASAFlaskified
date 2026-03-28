"""
psgscoring.breath
=================
Breath-by-breath segmentation and event detection (AASM-compliant).

All functions accept plain NumPy arrays; no MNE dependency.

Dependencies: numpy, psgscoring.constants, psgscoring.utils
"""

from __future__ import annotations
import numpy as np

from .constants import APNEA_THRESHOLD, HYPOPNEA_THRESHOLD, EPOCH_LEN_S
from .utils import safe_r


# ---------------------------------------------------------------------------
# Breath segmentation
# ---------------------------------------------------------------------------

def detect_breaths(
    flow_filtered: np.ndarray,
    sf: float,
    min_breath_s: float = 1.0,
    max_breath_s: float = 15.0,
) -> list[dict]:
    """
    Segment individual breaths via zero-crossings on the bandpass-filtered
    flow waveform.  Each breath = one inspiratory + one expiratory half-wave.

    The input signal should already be bandpass-filtered (0.05–3 Hz via
    ``signal.bandpass_flow``); snoring vibrations are therefore removed before
    this function is called.

    Returns
    -------
    list of dict, one per breath cycle:
        start, mid, end     – sample indices
        onset_s, duration_s – in seconds
        peak_insp           – peak inspiratory flow
        trough_exp          – trough expiratory flow
        amplitude           – peak-to-trough (AASM definition)
        insp_segment        – numpy array of the inspiratory phase
    """
    if len(flow_filtered) < int(sf * 2):
        return []

    sign  = np.sign(flow_filtered)
    sign[sign == 0] = 1                             # avoid stuck zeros
    crossings = np.where(np.diff(sign))[0]

    if len(crossings) < 3:
        return []

    min_samp = int(min_breath_s * sf)
    max_samp = int(max_breath_s * sf)
    breaths  = []
    i        = 0

    while i < len(crossings) - 1:
        if i + 2 >= len(crossings):
            break

        start     = crossings[i]
        cycle_end = crossings[i + 2]
        dur_samp  = cycle_end - start

        if dur_samp < min_samp or dur_samp > max_samp:
            i += 1
            continue

        seg  = flow_filtered[start:cycle_end]
        mid  = start + np.argmax(np.abs(seg[: len(seg) // 2 + 1]))

        first_half  = flow_filtered[start           : start + dur_samp // 2]
        second_half = flow_filtered[start + dur_samp // 2 : cycle_end]

        if np.mean(first_half) > np.mean(second_half):
            peak_insp  = float(np.max(first_half))
            trough_exp = float(np.min(second_half))
            insp_seg   = first_half
        else:
            peak_insp  = float(np.max(second_half))
            trough_exp = float(np.min(first_half))
            insp_seg   = second_half

        breaths.append({
            "start":        start,
            "mid":          mid,
            "end":          cycle_end,
            "onset_s":      start / sf,
            "duration_s":   dur_samp / sf,
            "peak_insp":    peak_insp,
            "trough_exp":   trough_exp,
            "amplitude":    abs(peak_insp - trough_exp),
            "insp_segment": insp_seg,
        })
        i += 2   # advance by a full breath cycle

    return breaths


# ---------------------------------------------------------------------------
# Breath amplitude ratios
# ---------------------------------------------------------------------------

def compute_breath_amplitudes(
    breaths: list[dict],
    sf: float,
    window_breaths: int = 10,
) -> np.ndarray:
    """
    Express each breath amplitude as a fraction of its local baseline.

    Baseline = median of the *window_breaths* preceding breaths (excluding
    those below the 25th percentile of that window to ignore artefacts).

    Returns
    -------
    np.ndarray of shape (len(breaths),), values: 1.0 = normal, 0.5 = 50 % reduction.
    """
    n    = len(breaths)
    if n == 0:
        return np.array([])

    amps   = np.array([b["amplitude"] for b in breaths])
    ratios = np.ones(n)

    for i in range(n):
        start  = max(0, i - window_breaths)
        bl_arr = amps[start:i] if i > 0 else amps[:1]
        good   = bl_arr[bl_arr > np.percentile(bl_arr, 25)] if len(bl_arr) > 0 else bl_arr
        if len(good) > 2:
            bl = float(np.median(good))
        elif len(bl_arr) > 0:
            bl = float(np.median(bl_arr))
        else:
            bl = float(amps[i])
        ratios[i] = amps[i] / bl if bl > 1e-9 else 1.0

    return ratios


# ---------------------------------------------------------------------------
# Flattening index  (RERA / flow limitation)
# ---------------------------------------------------------------------------

def compute_flattening_index(insp_segment: np.ndarray) -> float:
    """
    Fraction of the inspiratory segment whose absolute flow exceeds 80 % of peak.

    A triangular (normal) inspiratory profile scores ~0.10.
    A plateau indicating upper-airway flow limitation scores >0.30.
    A completely flat segment (no flow) scores ~1.0.

    Because ``insp_segment`` is derived from the 3 Hz bandpass-filtered
    signal, snoring artefacts (50–200 Hz) are already removed upstream.
    An additional low-pass filter is therefore unnecessary.

    Reference: Hosselet et al., AJRCCM 1998.
    """
    if len(insp_segment) < 5:
        return 0.0
    peak = np.max(np.abs(insp_segment))
    if peak < 1e-9:
        return 1.0
    n_above = np.sum(np.abs(insp_segment) > 0.80 * peak)
    return float(n_above / len(insp_segment))


# ---------------------------------------------------------------------------
# Event detection from breath-amplitude ratios
# ---------------------------------------------------------------------------

def detect_breath_events(
    breaths: list[dict],
    breath_ratios: np.ndarray,
    sf: float,
    hypno: list,
    apnea_thresh: float = APNEA_THRESHOLD,
    hypopnea_thresh: float = HYPOPNEA_THRESHOLD,
    min_dur_s: float = 10.0,
) -> tuple[list, list]:
    """
    Detect apnea and hypopnea events from per-breath amplitude ratios.

    An event starts at the first breath below *hypopnea_thresh* and ends at
    the first breath that recovers above it.  Within an event, any breath
    below *apnea_thresh* upgrades the event to an apnea.

    Returns
    -------
    (apnea_events, hypopnea_candidates) – each a list of event dicts.
    """
    if len(breaths) == 0:
        return [], []

    apneas    = []
    hypopneas = []
    n         = len(breaths)
    i         = 0

    while i < n:
        if breath_ratios[i] > hypopnea_thresh:
            i += 1
            continue

        event_start_idx = i
        event_start_s   = breaths[i]["onset_s"]
        is_apnea        = breath_ratios[i] < apnea_thresh
        min_ratio       = breath_ratios[i]

        j = i + 1
        while j < n and breath_ratios[j] < hypopnea_thresh:
            if breath_ratios[j] < apnea_thresh:
                is_apnea = True
            min_ratio = min(min_ratio, breath_ratios[j])
            j += 1

        event_end_s = (
            breaths[j - 1]["onset_s"] + breaths[j - 1]["duration_s"]
        )
        event_dur = event_end_s - event_start_s

        if event_dur >= min_dur_s:
            flat_vals = [
                compute_flattening_index(breaths[k]["insp_segment"])
                for k in range(event_start_idx, j)
                if breaths[k].get("insp_segment") is not None
                and len(breaths[k]["insp_segment"]) > 3
            ]
            avg_flat = float(np.mean(flat_vals)) if flat_vals else None
            ep_idx   = int(event_start_s // EPOCH_LEN_S)
            stage    = hypno[ep_idx] if ep_idx < len(hypno) else "W"

            ev = {
                "onset_s":        safe_r(event_start_s),
                "duration_s":     safe_r(event_dur),
                "stage":          stage,
                "epoch":          ep_idx,
                "min_ratio":      safe_r(min_ratio, 3),
                "n_breaths":      j - event_start_idx,
                "breath_start":   event_start_idx,
                "breath_end":     j,
                "avg_flattening": safe_r(avg_flat, 3),
                "sample_start":   breaths[event_start_idx]["start"],
                "sample_end":     breaths[j - 1]["end"],
            }
            (apneas if is_apnea else hypopneas).append(ev)

        i = j

    return apneas, hypopneas
