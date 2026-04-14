"""
signal_quality.py — YASAFlaskified v0.8.36
========================================
Automatische signaal-kwaliteitscheck per kanaal.

Controleert:
  - Amplitude bereik (flat-line, clipping, fysiologisch bereik)
  - SNR (signal-to-noise ratio)
  - Artefact-percentage
  - Signaal-continuïteit (dropouts)

Gebruik:
    from signal_quality import check_signal_quality
    report = check_signal_quality(raw, channel_types)
"""

import numpy as np
import logging

logger = logging.getLogger("yasaflaskified.quality")


# ── Referentiewaarden per kanaaltype ──────────────────────────
EXPECTED_RANGES = {
    "eeg":   {"min_uv": 5,    "max_uv": 500,   "min_snr": 3.0},
    "eog":   {"min_uv": 10,   "max_uv": 500,   "min_snr": 2.5},
    "emg":   {"min_uv": 2,    "max_uv": 300,   "min_snr": 2.0},
    "resp":  {"min_uv": 0.1,  "max_uv": 50000, "min_snr": 1.5},
    "spo2":  {"min_uv": 50,   "max_uv": 100,   "min_snr": 1.0},
    "ecg":   {"min_uv": 50,   "max_uv": 5000,  "min_snr": 3.0},
    "other": {"min_uv": 0.1,  "max_uv": 50000, "min_snr": 1.0},
}

QUALITY_LABELS = {
    "good":     {"nl": "Goed",      "fr": "Bon",      "en": "Good"},
    "moderate":  {"nl": "Matig",     "fr": "Modéré",   "en": "Moderate"},
    "poor":     {"nl": "Slecht",    "fr": "Mauvais",  "en": "Poor"},
    "unusable": {"nl": "Onbruikbaar","fr": "Inutilisable","en": "Unusable"},
}


def _trimmed_std(data, pct=5):
    """Getrimde standaarddeviatie (verwijder extreme uitschieters)."""
    low  = np.percentile(data, pct)
    high = np.percentile(data, 100 - pct)
    trimmed = data[(data >= low) & (data <= high)]
    return float(np.std(trimmed)) if len(trimmed) > 10 else float(np.std(data))


def _compute_snr(data, sf, low_hz=0.5, high_hz=45):
    """Bereken SNR als ratio signaalband / ruisband vermogen."""
    from scipy.signal import welch
    freqs, psd = welch(data, fs=sf, nperseg=min(len(data), int(sf * 4)))

    # Signaalband
    sig_mask = (freqs >= low_hz) & (freqs <= high_hz)
    sig_power = np.sum(psd[sig_mask]) if np.any(sig_mask) else 1e-12

    # Ruisband (>50 Hz als beschikbaar, anders >high_hz)
    noise_freq = max(high_hz, 50)
    noise_mask = freqs > noise_freq
    noise_power = np.sum(psd[noise_mask]) if np.any(noise_mask) else 1e-12

    if noise_power < 1e-15:
        return 20.0  # Nauwelijks ruis → uitstekend

    return float(10 * np.log10(sig_power / noise_power))


def _check_flatline(data, sf, min_duration_s=5):
    """Detecteer flatline segmenten (identieke samples)."""
    diff = np.diff(data)
    flat = np.abs(diff) < 1e-10
    # Label aaneengesloten flatlines
    changes = np.diff(flat.astype(int))
    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]

    if len(starts) == 0:
        return 0.0

    # Zorg dat starts en ends even lang zijn
    if len(ends) < len(starts):
        ends = np.append(ends, len(flat) - 1)
    if len(starts) > len(ends):
        starts = starts[:len(ends)]

    durations = (ends - starts) / sf
    long_flats = durations[durations >= min_duration_s]
    total_flat_s = float(np.sum(long_flats))
    total_s = len(data) / sf
    return total_flat_s / total_s if total_s > 0 else 0.0


def _check_clipping(data, threshold_pct=99.5):
    """Detecteer clipping (signaal raakt plafond/vloer)."""
    high = np.percentile(data, threshold_pct)
    low = np.percentile(data, 100 - threshold_pct)
    n_clipped = np.sum((data >= high) | (data <= low))
    return float(n_clipped / len(data))


def check_channel_quality(data, sf, ch_type="eeg"):
    """
    Check kwaliteit van één kanaal.

    Returns
    -------
    dict met:
        quality: 'good' | 'moderate' | 'poor' | 'unusable'
        snr_db: float
        trimmed_std: float
        flatline_pct: float
        clipping_pct: float
        issues: list[str]
    """
    ref = EXPECTED_RANGES.get(ch_type, EXPECTED_RANGES["other"])
    issues = []

    # Amplitude check
    trimmed = _trimmed_std(data)
    if trimmed < ref["min_uv"]:
        issues.append(f"amplitude_too_low ({trimmed:.1f} uV, min {ref['min_uv']})")
    elif trimmed > ref["max_uv"]:
        issues.append(f"amplitude_too_high ({trimmed:.0f} uV, max {ref['max_uv']})")

    # SNR
    if ch_type in ("eeg", "eog", "emg", "ecg"):
        snr = _compute_snr(data, sf)
    else:
        snr = 10.0  # Skip voor niet-EEG kanalen

    if snr < ref["min_snr"]:
        issues.append(f"low_snr ({snr:.1f} dB, min {ref['min_snr']})")

    # Flatline
    flatline_pct = _check_flatline(data, sf)
    if flatline_pct > 0.10:
        issues.append(f"flatline ({flatline_pct*100:.1f}%)")
    elif flatline_pct > 0.02:
        issues.append(f"some_flatline ({flatline_pct*100:.1f}%)")

    # Clipping
    clipping_pct = _check_clipping(data)
    if clipping_pct > 0.05:
        issues.append(f"clipping ({clipping_pct*100:.1f}%)")

    # Bepaal overall kwaliteit
    n_issues = len(issues)
    severe = any("unusable" in i or "too_low" in i or "flatline" in i
                 for i in issues if "some_" not in i)

    if n_issues == 0:
        quality = "good"
    elif n_issues == 1 and not severe:
        quality = "moderate"
    elif severe or n_issues >= 3:
        quality = "unusable"
    else:
        quality = "poor"

    return {
        "quality":      quality,
        "snr_db":       round(snr, 1),
        "trimmed_std":  round(trimmed, 2),
        "flatline_pct": round(flatline_pct * 100, 1),
        "clipping_pct": round(clipping_pct * 100, 2),
        "issues":       issues,
    }


def check_signal_quality(raw, ch_types=None):
    """
    Check kwaliteit van alle kanalen in een MNE Raw object.

    Parameters
    ----------
    raw      : mne.io.BaseRaw
    ch_types : dict {channel_name: type} — bv. {"C3": "eeg", "EOG1": "eog"}
               Als None, probeert automatisch te detecteren.

    Returns
    -------
    dict {channel_name: quality_report}
    """
    if ch_types is None:
        ch_types = {}
        for ch in raw.ch_names:
            cu = ch.upper()
            if any(p in cu for p in ["EEG", "C3", "C4", "F3", "F4", "O1", "O2", "CZ"]):
                ch_types[ch] = "eeg"
            elif "EOG" in cu:
                ch_types[ch] = "eog"
            elif "EMG" in cu or "CHIN" in cu:
                ch_types[ch] = "emg"
            elif "ECG" in cu or "EKG" in cu:
                ch_types[ch] = "ecg"
            elif "SPO2" in cu or "SAO2" in cu:
                ch_types[ch] = "spo2"
            elif any(p in cu for p in ["FLOW", "PRESS", "THORA", "ABDOM", "RIP", "NASAL"]):
                ch_types[ch] = "resp"
            else:
                ch_types[ch] = "other"

    sf = raw.info["sfreq"]
    results = {}
    overall_issues = []

    for ch_name in raw.ch_names:
        ct = ch_types.get(ch_name, "other")
        try:
            data = raw.get_data(picks=[ch_name])[0]
            qr = check_channel_quality(data, sf, ct)
            results[ch_name] = qr
            if qr["quality"] in ("poor", "unusable"):
                overall_issues.append(f"{ch_name}: {qr['quality']} ({', '.join(qr['issues'])})")
        except Exception as e:
            results[ch_name] = {
                "quality": "unusable",
                "snr_db": 0, "trimmed_std": 0,
                "flatline_pct": 0, "clipping_pct": 0,
                "issues": [f"error: {e}"],
            }
            overall_issues.append(f"{ch_name}: error ({e})")

    # Overall kwaliteitsscore
    qualities = [r["quality"] for r in results.values()]
    if "unusable" in qualities:
        overall = "poor"
    elif qualities.count("poor") > len(qualities) * 0.3:
        overall = "poor"
    elif qualities.count("good") > len(qualities) * 0.7:
        overall = "good"
    else:
        overall = "moderate"

    return {
        "channels": results,
        "overall": overall,
        "n_channels": len(results),
        "n_good": qualities.count("good"),
        "n_moderate": qualities.count("moderate"),
        "n_poor": qualities.count("poor"),
        "n_unusable": qualities.count("unusable"),
        "issues": overall_issues,
    }
