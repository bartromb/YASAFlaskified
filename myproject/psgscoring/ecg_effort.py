"""
ECG-derived respiratory effort detection for apnea type classification.

Implements the Transformed ECG (TECG) method (Berry et al., JCSM 2019)
and a spectral effort classifier to distinguish cardiac pulsation
artefact from true respiratory effort on RIP bands during apnea events.

References
----------
Berry RB et al. Use of a Transformed ECG Signal to Detect Respiratory
    Effort During Apnea. J Clin Sleep Med. 2019;15(11):1653-1660.
Berry RB et al. Use of Chest Wall Electromyography to Detect Respiratory
    Effort during Polysomnography. J Clin Sleep Med. 2016;12(9):1239-1244.

v0.2.5 — April 2026
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks, welch

# ── Constants ────────────────────────────────────────────────────────────────

# QRS blanking
QRS_BLANKING_MS       = 80          # ms to blank around each R-peak
QRS_REFRACTORY_MS     = 200         # minimum R-R interval (300 bpm max)
QRS_SEARCH_WINDOW_S   = 0.15        # s window for R-peak refinement

# Spectral thresholds
CARDIAC_BAND_HZ       = (0.8, 2.5)  # cardiac pulsation band (default)
RESPIRATORY_BAND_HZ   = (0.1, 0.5)  # respiratory effort band
CARDIAC_DOMINANCE_THR = 0.75        # cardiac power fraction → central
RESPIRATORY_MIN_THR   = 0.20        # minimum respiratory power → not central
CARDIAC_BAND_MARGIN   = 0.3         # Hz margin around HR fundamental for adaptive band

# TECG inspiratory burst detection
TECG_HP_FREQ          = 30.0        # Hz — high-pass cutoff for TECG
TECG_BURST_MIN_AMP    = 0.20        # relative to pre-event burst amplitude
TECG_BURST_MIN_RATE   = 4           # minimum bursts/min for effort present
TECG_BURST_MAX_RATE   = 30          # maximum bursts/min (physiological)
TECG_INTEGRATION_S    = 0.10        # s — integration window for rectified signal


def detect_r_peaks(ecg: np.ndarray, sf: float) -> np.ndarray:
    """Detect R-peaks using a simple amplitude-threshold method.

    Parameters
    ----------
    ecg : array
        Raw ECG signal.
    sf : float
        Sampling frequency in Hz.

    Returns
    -------
    r_peaks : array of int
        Sample indices of detected R-peaks.
    """
    # Bandpass 5-30 Hz to isolate QRS
    sos_bp = butter(3, [5.0, 30.0], btype="bandpass", fs=sf, output="sos")
    ecg_filt = sosfiltfilt(sos_bp, ecg)

    # Squared signal for peak enhancement
    ecg_sq = ecg_filt ** 2

    # Adaptive threshold: 60% of rolling 2-second max
    win = int(2.0 * sf)
    if win < 2:
        win = 2
    # Use stride tricks for efficiency
    from numpy.lib.stride_tricks import sliding_window_view
    if len(ecg_sq) > win:
        rolling_max = np.max(sliding_window_view(ecg_sq, win), axis=1)
        # Pad to original length
        pad = len(ecg_sq) - len(rolling_max)
        rolling_max = np.concatenate([rolling_max, np.full(pad, rolling_max[-1])])
    else:
        rolling_max = np.full(len(ecg_sq), np.max(ecg_sq))

    threshold = 0.6 * rolling_max

    # Find peaks above threshold
    refractory_samples = int(QRS_REFRACTORY_MS / 1000.0 * sf)
    peaks, _ = find_peaks(ecg_sq, height=threshold,
                          distance=max(refractory_samples, 1))

    return peaks


def qrs_blanking(ecg: np.ndarray, sf: float,
                 r_peaks: np.ndarray | None = None) -> np.ndarray:
    """Apply QRS blanking to reveal underlying EMG/effort signal.

    Each QRS complex is replaced by a copy of the adjacent signal,
    following the method of Berry et al. (JCSM 2019).

    Parameters
    ----------
    ecg : array
        Raw ECG signal.
    sf : float
        Sampling frequency.
    r_peaks : array, optional
        Pre-detected R-peak indices. If None, detected automatically.

    Returns
    -------
    blanked : array
        ECG signal with QRS complexes replaced.
    """
    if r_peaks is None:
        r_peaks = detect_r_peaks(ecg, sf)

    blanked = ecg.copy()
    half_blank = int(QRS_BLANKING_MS / 1000.0 * sf / 2)

    for pk in r_peaks:
        start = max(0, pk - half_blank)
        end   = min(len(blanked), pk + half_blank)
        blank_len = end - start

        # Replace with adjacent signal (before the QRS if possible)
        src_start = max(0, start - blank_len)
        src_end   = src_start + blank_len
        if src_end <= start and src_end <= len(blanked):
            blanked[start:end] = blanked[src_start:src_end]
        elif end + blank_len <= len(blanked):
            blanked[start:end] = blanked[end:end + blank_len]
        else:
            blanked[start:end] = 0.0

    return blanked


def compute_tecg(ecg: np.ndarray, sf: float,
                 r_peaks: np.ndarray | None = None) -> np.ndarray:
    """Compute the Transformed ECG (TECG) signal.

    Steps: high-pass filter → QRS blanking → rectification → integration.

    Parameters
    ----------
    ecg : array
        Raw ECG signal.
    sf : float
        Sampling frequency.
    r_peaks : array, optional
        Pre-detected R-peak indices.

    Returns
    -------
    tecg : array
        Transformed ECG signal showing inspiratory EMG bursts.
    """
    # High-pass filter at 30 Hz to reduce ECG relative to EMG
    hp_freq = min(TECG_HP_FREQ, sf / 2 - 1)
    if hp_freq < 5.0:
        # Sampling rate too low for meaningful TECG
        return np.zeros(len(ecg))
    sos_hp = butter(3, hp_freq, btype="highpass", fs=sf, output="sos")
    ecg_hp = sosfiltfilt(sos_hp, ecg)

    # QRS blanking
    blanked = qrs_blanking(ecg_hp, sf, r_peaks)

    # Rectification
    rectified = np.abs(blanked)

    # Moving-average integration
    int_samples = max(1, int(TECG_INTEGRATION_S * sf))
    kernel = np.ones(int_samples) / int_samples
    tecg = np.convolve(rectified, kernel, mode="same")

    return tecg


def detect_inspiratory_bursts(tecg: np.ndarray, sf: float,
                              onset_idx: int, end_idx: int,
                              baseline_tecg_amp: float | None = None
                              ) -> dict:
    """Detect inspiratory EMG bursts in a TECG segment during an apnea.

    Parameters
    ----------
    tecg : array
        Full-recording TECG signal.
    sf : float
        Sampling frequency.
    onset_idx, end_idx : int
        Sample indices of the apnea event.
    baseline_tecg_amp : float, optional
        Mean TECG amplitude during stable breathing (pre-event).
        If None, estimated from the 30s before the event.

    Returns
    -------
    result : dict
        Keys: n_bursts, burst_rate_per_min, effort_present (bool),
        mean_burst_amp, baseline_amp.
    """
    seg = tecg[onset_idx:end_idx]
    dur_s = len(seg) / max(sf, 1)

    if dur_s < 3.0 or len(seg) < 10:
        return {"n_bursts": 0, "burst_rate_per_min": 0.0,
                "effort_present": False, "mean_burst_amp": 0.0,
                "baseline_amp": 0.0}

    # Estimate baseline from 30s before event
    if baseline_tecg_amp is None:
        pre_start = max(0, onset_idx - int(30 * sf))
        pre_seg = tecg[pre_start:onset_idx]
        if len(pre_seg) > 0:
            baseline_tecg_amp = float(np.percentile(pre_seg, 75))
        else:
            baseline_tecg_amp = float(np.mean(seg))

    baseline_tecg_amp = max(baseline_tecg_amp, 1e-9)

    # Detect peaks in TECG segment
    min_dist = int(60.0 / TECG_BURST_MAX_RATE * sf)  # minimum interval
    height_thr = TECG_BURST_MIN_AMP * baseline_tecg_amp
    peaks, props = find_peaks(seg, height=height_thr,
                              distance=max(min_dist, 1))

    n_bursts = len(peaks)
    burst_rate = n_bursts / dur_s * 60.0 if dur_s > 0 else 0.0

    # Effort is present if burst rate is physiologically plausible
    effort_present = TECG_BURST_MIN_RATE <= burst_rate <= TECG_BURST_MAX_RATE

    mean_amp = float(np.mean(props["peak_heights"])) if n_bursts > 0 else 0.0

    return {
        "n_bursts":          n_bursts,
        "burst_rate_per_min": round(burst_rate, 1),
        "effort_present":    effort_present,
        "mean_burst_amp":    round(mean_amp, 4),
        "baseline_amp":      round(baseline_tecg_amp, 4),
    }


def compute_adaptive_cardiac_band(
    r_peaks: np.ndarray | None,
    sf: float,
    onset_idx: int = 0,
    end_idx: int | None = None,
) -> tuple[float, float]:
    """Compute patient-adaptive cardiac frequency band from R-R intervals.

    In bradycardic patients (athletes, beta-blocker users) the cardiac
    fundamental can drop to 0.5–0.6 Hz, overlapping the respiratory band.
    This function derives the actual HR and centres the cardiac band around
    the fundamental and its first harmonic.

    Parameters
    ----------
    r_peaks : array or None
        R-peak sample indices.  Falls back to default band if None.
    sf : float
        Sampling frequency.
    onset_idx, end_idx : int
        Optional window to restrict R-peaks used for HR estimation.

    Returns
    -------
    (low_hz, high_hz) : tuple of float
        Adaptive cardiac band boundaries.
    """
    if r_peaks is None or len(r_peaks) < 3:
        return CARDIAC_BAND_HZ

    if end_idx is not None:
        mask = (r_peaks >= onset_idx) & (r_peaks <= end_idx)
        local_peaks = r_peaks[mask]
    else:
        local_peaks = r_peaks

    if len(local_peaks) < 3:
        return CARDIAC_BAND_HZ

    rr = np.diff(local_peaks) / sf            # R-R intervals in seconds
    rr = rr[(rr > 0.25) & (rr < 2.5)]        # reject artefact (24–240 bpm)
    if len(rr) < 2:
        return CARDIAC_BAND_HZ

    median_rr  = float(np.median(rr))
    hr_hz      = 1.0 / median_rr              # fundamental frequency

    low_hz  = max(0.55, hr_hz - CARDIAC_BAND_MARGIN)
    high_hz = min(3.5,  hr_hz * 2 + CARDIAC_BAND_MARGIN)   # up to 1st harmonic

    return (round(low_hz, 2), round(high_hz, 2))


def spectral_effort_classifier(effort_signal: np.ndarray, sf: float,
                                onset_idx: int, end_idx: int,
                                cardiac_band_hz: tuple[float, float] | None = None,
                                ) -> dict:
    """Classify effort signal as cardiac artefact vs respiratory effort.

    Compares power in cardiac and respiratory frequency bands during an
    apnea event.  When *cardiac_band_hz* is provided (from
    :func:`compute_adaptive_cardiac_band`), the cardiac band is adapted
    to the patient's actual heart rate, preventing misclassification in
    bradycardic patients.

    Parameters
    ----------
    effort_signal : array
        RIP thorax or abdomen signal (raw, not envelope).
    sf : float
        Sampling frequency.
    onset_idx, end_idx : int
        Sample indices of the apnea event.
    cardiac_band_hz : tuple, optional
        (low, high) Hz for cardiac band.  Defaults to module constant.

    Returns
    -------
    result : dict
        Keys: cardiac_fraction, respiratory_fraction,
        cardiac_dominant (bool), classification_hint (str),
        cardiac_band_hz (tuple).
    """
    if cardiac_band_hz is None:
        cardiac_band_hz = CARDIAC_BAND_HZ

    seg = effort_signal[onset_idx:end_idx]

    empty = {"cardiac_fraction": 0.0, "respiratory_fraction": 0.0,
             "cardiac_dominant": False, "classification_hint": "insufficient_data",
             "cardiac_band_hz": cardiac_band_hz}

    if len(seg) < int(4 * sf):
        return empty

    nperseg = min(len(seg), int(4 * sf))
    try:
        freqs, psd = welch(seg, fs=sf, nperseg=nperseg, noverlap=nperseg // 2)
    except Exception:
        empty["classification_hint"] = "welch_failed"
        return empty

    resp_mask    = (freqs >= RESPIRATORY_BAND_HZ[0]) & (freqs <= RESPIRATORY_BAND_HZ[1])
    cardiac_mask = (freqs >= cardiac_band_hz[0])      & (freqs <= cardiac_band_hz[1])

    resp_power    = float(np.sum(psd[resp_mask]))
    cardiac_power = float(np.sum(psd[cardiac_mask]))
    total_power   = resp_power + cardiac_power

    if total_power < 1e-12:
        empty["classification_hint"] = "no_signal"
        return empty

    cardiac_frac = cardiac_power / total_power
    resp_frac    = resp_power / total_power

    cardiac_dominant = (cardiac_frac > CARDIAC_DOMINANCE_THR and
                        resp_frac < RESPIRATORY_MIN_THR)

    if cardiac_dominant:
        hint = "probable_central"
    elif resp_frac > 0.5:
        hint = "effort_present"
    else:
        hint = "indeterminate"

    return {
        "cardiac_fraction":    round(cardiac_frac, 3),
        "respiratory_fraction": round(resp_frac, 3),
        "cardiac_dominant":    cardiac_dominant,
        "classification_hint": hint,
        "cardiac_band_hz":     cardiac_band_hz,
    }


def ecg_effort_assessment(ecg: np.ndarray | None,
                           thorax_raw: np.ndarray | None,
                           abdomen_raw: np.ndarray | None,
                           sf: float,
                           onset_idx: int, end_idx: int,
                           tecg: np.ndarray | None = None,
                           r_peaks: np.ndarray | None = None,
                           ) -> dict:
    """Combined ECG-derived effort assessment for a single apnea event.

    Runs both the TECG inspiratory-burst detector and the spectral
    effort classifier. Returns a combined assessment.

    Parameters
    ----------
    ecg : array or None
        Raw ECG signal (full recording). If None, only spectral analysis
        on effort bands is performed.
    thorax_raw, abdomen_raw : array or None
        Raw RIP signals.
    sf : float
        Sampling frequency.
    onset_idx, end_idx : int
        Sample indices of the apnea event.
    tecg : array, optional
        Pre-computed TECG (avoids recomputation per event).
    r_peaks : array, optional
        Pre-detected R-peaks.

    Returns
    -------
    assessment : dict
        Keys: ecg_effort_present (bool or None),
        spectral_cardiac_dominant (bool), reclassify_as_central (bool),
        tecg_detail (dict), spectral_detail (dict).
    """
    result = {
        "ecg_effort_present":       None,
        "spectral_cardiac_dominant": False,
        "reclassify_as_central":    False,
        "tecg_detail":              {},
        "spectral_detail":          {},
    }

    # ── TECG analysis (if ECG available) ─────────────────────────────────
    if ecg is not None and len(ecg) > end_idx:
        if tecg is None:
            tecg = compute_tecg(ecg, sf, r_peaks)

        burst_result = detect_inspiratory_bursts(tecg, sf, onset_idx, end_idx)
        result["tecg_detail"] = burst_result
        result["ecg_effort_present"] = burst_result["effort_present"]

    # ── Spectral analysis on effort bands ────────────────────────────────
    # v0.2.5: Use adaptive cardiac band based on actual heart rate
    adaptive_band = compute_adaptive_cardiac_band(r_peaks, sf, onset_idx, end_idx)

    effort_signal = None
    if thorax_raw is not None and len(thorax_raw) > end_idx:
        effort_signal = thorax_raw
    elif abdomen_raw is not None and len(abdomen_raw) > end_idx:
        effort_signal = abdomen_raw

    if effort_signal is not None:
        spectral = spectral_effort_classifier(effort_signal, sf,
                                               onset_idx, end_idx,
                                               cardiac_band_hz=adaptive_band)
        result["spectral_detail"] = spectral
        result["spectral_cardiac_dominant"] = spectral["cardiac_dominant"]

    # ── Combined decision ────────────────────────────────────────────────
    # Reclassify as central if BOTH indicators agree:
    # 1. TECG shows no inspiratory bursts (or ECG not available)
    # 2. Spectral analysis shows cardiac dominance
    ecg_says_no_effort = (result["ecg_effort_present"] is False)
    spectral_says_cardiac = result["spectral_cardiac_dominant"]

    if ecg_says_no_effort and spectral_says_cardiac:
        result["reclassify_as_central"] = True
    elif ecg is None and spectral_says_cardiac:
        # No ECG available, spectral alone with lower confidence
        result["reclassify_as_central"] = True

    return result
