"""
psgscoring.ancillary
====================
Ancillary signal analyses: body position, heart rate, snoring,
and Cheyne-Stokes respiration detection.

Dependencies: numpy, scipy, psgscoring.constants, psgscoring.utils
"""

from __future__ import annotations
import numpy as np
from scipy import signal as sp_signal

from .constants import EPOCH_LEN_S
from .utils import (
    build_sleep_mask, fmt_time, hypno_to_numeric,
    is_nrem, is_rem, safe_r,
)


# ---------------------------------------------------------------------------
# Body position
# ---------------------------------------------------------------------------

def analyze_position(
    pos_data: np.ndarray,
    sf: float,
    hypno: list,
    resp_events: list,
) -> dict:
    """
    Compute sleep time and AHI per body position.

    Returns
    -------
    dict with keys: success, summary (sleep_time_min, sleep_pct,
    ahi_per_pos), pos_per_epoch, error.
    """
    result: dict = {"success": False, "summary": {}, "error": None}
    try:
        spe           = int(sf * EPOCH_LEN_S)
        n_epochs      = len(hypno)
        # v0.8.12: auto-map raw ADC/voltage to 0-4 codes
        pos_mapped    = _map_position_signal(pos_data)
        pos_per_epoch = [_modal_position(pos_mapped, ep, spe) for ep in range(n_epochs)]

        pos_names = {0: "Prone", 1: "Left", 2: "Supine", 3: "Right", 4: "Upright"}
        sleep_time: dict[str, float | None] = {}
        ahi_pos:    dict[str, float | None] = {}

        for code, name in pos_names.items():
            sleep_epochs = [
                i for i, (p, s) in enumerate(zip(pos_per_epoch, hypno))
                if p == code and s != "W"
            ]
            dur_min      = len(sleep_epochs) * (EPOCH_LEN_S / 60)
            sleep_time[name] = safe_r(dur_min)
            n_ev = sum(
                1 for ev in resp_events
                if pos_per_epoch[ev.get("epoch", 0)] == code
            )
            dur_h         = dur_min / 60
            ahi_pos[name] = safe_r(n_ev / dur_h) if dur_h > 0 else 0

        total_sleep_min = sum(v for v in sleep_time.values() if v)
        pct = {
            k: safe_r(v / total_sleep_min * 100) if total_sleep_min > 0 else 0
            for k, v in sleep_time.items()
        }

        result["summary"]       = {
            "sleep_time_min": sleep_time,
            "sleep_pct":      pct,
            "ahi_per_pos":    ahi_pos,
        }
        result["pos_per_epoch"] = pos_per_epoch
        result["success"]       = True
    except Exception as e:
        result["error"] = str(e)
    return result


def _map_position_signal(pos_data: np.ndarray) -> np.ndarray:
    """Map raw position signal to 0-4 codes (Prone/Left/Supine/Right/Upright).

    Handles both pre-coded (0-4) and raw ADC/voltage signals.
    """
    rounded = np.round(pos_data).astype(int)
    unique_vals = np.unique(rounded)

    # Already coded 0-4 → use as-is
    if len(unique_vals) <= 6 and np.all((unique_vals >= 0) & (unique_vals <= 5)):
        return np.clip(rounded, 0, 4)

    # Raw ADC/voltage signal → map clusters to 0-4 by rank order
    # Use percentile-based quantization
    valid = pos_data[~np.isnan(pos_data)]
    if len(valid) == 0:
        return np.zeros(len(pos_data), dtype=int)

    # Assign 5 bins based on signal range
    edges = np.percentile(valid, [0, 20, 40, 60, 80, 100])
    mapped = np.digitize(pos_data, edges[1:-1])  # 0-4
    return np.clip(mapped, 0, 4)


def _modal_position(pos_data: np.ndarray, ep: int, spe: int) -> int:
    """Bepaal de meest voorkomende slaappositie (modus) voor een epoch."""
    s   = ep * spe
    e   = min(s + spe, len(pos_data))
    seg = pos_data[s:e]
    if len(seg) == 0:
        return -1
    vals, cnts = np.unique(seg.astype(int), return_counts=True)
    return int(vals[np.argmax(cnts)])


# ---------------------------------------------------------------------------
# Heart rate
# ---------------------------------------------------------------------------

def analyze_heart_rate(
    hr_data: np.ndarray,
    sf: float,
    hypno: list,
) -> dict:
    """
    Basic heart-rate statistics during sleep.

    Physiologically implausible values (< 20 or > 250 bpm) are removed.
    """
    result: dict = {"success": False, "summary": {}, "error": None}
    try:
        hr = hr_data.copy().astype(float)
        hr[(hr < 20) | (hr > 250)] = np.nan

        sleep_mask = build_sleep_mask(hypno, sf, len(hr))
        hr_sleep   = hr[sleep_mask]
        hr_sleep   = hr_sleep[~np.isnan(hr_sleep)]

        if len(hr_sleep) == 0:
            result["error"] = "No HR data during sleep"
            return result

        result["summary"] = {
            "avg_hr":        safe_r(float(np.mean(hr_sleep))),
            "min_hr":        safe_r(float(np.min(hr_sleep))),
            "max_hr":        safe_r(float(np.max(hr_sleep))),
            "std_hr":        safe_r(float(np.std(hr_sleep))),
            "n_tachycardia": int(np.sum(hr_sleep > 100)),
            "n_bradycardia": int(np.sum(hr_sleep < 50)),
        }
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# Snoring
# ---------------------------------------------------------------------------

def analyze_snore(
    snore_data: np.ndarray,
    sf: float,
    hypno: list,
) -> dict:
    """
    Estimate snoring duration and index from a microphone / snore channel.

    Uses 1-second RMS windows; the 60th percentile of the RMS distribution
    is used as the snoring threshold.
    """
    result: dict = {"success": False, "summary": {}, "error": None}
    try:
        win        = int(sf)
        n_windows  = len(snore_data) // win
        rms        = np.array([
            np.sqrt(np.mean(snore_data[i * win : (i + 1) * win] ** 2))
            for i in range(n_windows)
        ])
        threshold  = float(np.percentile(rms, 60))
        snore_mask = rms > threshold

        # Build 1-s sleep mask
        hypno_num      = hypno_to_numeric(hypno)
        sleep_mask_1s  = np.zeros(n_windows, dtype=bool)
        for ep_i, stage in enumerate(hypno_num):
            s = ep_i * EPOCH_LEN_S
            e = min(s + EPOCH_LEN_S, n_windows)
            if stage > 0:
                sleep_mask_1s[s:e] = True

        snore_sleep    = snore_mask & sleep_mask_1s
        total_sleep_s  = float(np.sum(sleep_mask_1s))
        snore_s        = float(np.sum(snore_sleep))
        total_sleep_h  = total_sleep_s / 3600

        result["summary"] = {
            "snore_min":     safe_r(snore_s / 60),
            "snore_pct_tst": (
                safe_r(snore_s / total_sleep_s * 100) if total_sleep_s > 0 else 0
            ),
            "snore_index":   (
                safe_r((snore_s / 60) / total_sleep_h) if total_sleep_h > 0 else 0
            ),
        }
        # v0.8.12: expose RMS timeseries for PDF overview plot
        result["rms_1s"] = rms.tolist()
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# Cheyne-Stokes Respiration
# ---------------------------------------------------------------------------

def detect_cheyne_stokes(
    flow_env: np.ndarray,
    sf: float,
    hypno: list,
    min_cycle_s: float = 40.0,
    max_cycle_s: float = 120.0,
) -> dict:
    """
    Detect Cheyne-Stokes Respiration (CSR) via autocorrelation of the
    very-low-frequency flow envelope (0.005–0.05 Hz = 20–200 s periods).

    A normalised autocorrelation peak > 0.3 in the 40–120 s lag range
    indicates a significant crescendo-decrescendo pattern.

    Returns
    -------
    dict: success, csr_detected, periodicity_s, csr_minutes,
    csr_pct_sleep, error.
    """
    out = {
        "success":      False,
        "csr_detected": False,
        "periodicity_s": None,
        "csr_minutes":  0,
    }
    try:
        n = len(flow_env)
        if n < int(sf * min_cycle_s * 3):
            out["success"] = True
            return out

        nyq = sf / 2
        lo  = max(0.005 / nyq, 0.0001)
        hi  = min(0.05  / nyq, 0.49)
        if lo >= hi:
            out["success"] = True
            return out

        b, a      = sp_signal.butter(2, [lo, hi], btype="band")
        slow_env  = np.abs(sp_signal.filtfilt(b, a, flow_env))

        min_lag = int(min_cycle_s * sf)
        max_lag = min(int(max_cycle_s * sf), n // 2)
        if max_lag <= min_lag:
            out["success"] = True
            return out

        centered = slow_env - np.mean(slow_env)
        var      = np.var(centered)
        if var < 1e-12:
            out["success"] = True
            return out

        lags  = np.arange(min_lag, max_lag, max(1, int(sf * 2)))
        acorr = np.array([
            np.mean(centered[: n - lag] * centered[lag:]) / var
            for lag in lags
        ])

        if len(acorr) > 2:
            peak_idx = int(np.argmax(acorr))
            peak_val = float(acorr[peak_idx])

            if peak_val > 0.3:
                period_s = lags[peak_idx] / sf
                out["periodicity_s"] = safe_r(period_s)
                out["csr_detected"]  = True

                # Count 2-minute CSR segments
                seg_len    = int(120 * sf)
                csr_min    = 0
                for seg_start in range(0, n - seg_len, seg_len):
                    if np.var(centered[seg_start : seg_start + seg_len]) > 0.5 * var:
                        csr_min += 2
                out["csr_minutes"] = csr_min

                sleep_min = sum(
                    EPOCH_LEN_S for s in hypno if s != "W"
                ) / 60
                out["csr_pct_sleep"] = safe_r(
                    csr_min / max(sleep_min, 1) * 100
                )

        out["success"] = True
    except Exception as e:
        out["error"] = str(e)
    return out
