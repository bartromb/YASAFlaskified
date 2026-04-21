"""
signal_quality.py — RIP sensor quality validation for psgscoring v0.2.96+

Motivation
----------
Respiratory event classification (obstructive/central/mixed) depends on
bilateral effort signals (thorax + abdomen RIP). When one channel fails
(sensor disconnect, calibration drift, movement artifact), paradoxical
phase detection becomes impossible and the classifier defaults to
obstructive. This module detects such failures BEFORE classification and
provides:

1. Per-channel quality assessment
2. Pair comparison (thorax vs abdomen)
3. Single-channel fallback classification
4. Clinical warning text for reports

Empirically validated
---------------------
Clinical case "Loos" (AZORG, April 2026):
- Thorax MAD: 0.0017, breath-band energy: 3e-04 → classified 'failed'
- Abdomen MAD: 0.046, breath-band energy: 2.0  → classified 'ok'
- Energy ratio: 6862× → pair flagged as unreliable
- Psgscoring v0.2.951 reported: OSAS, AHI 56.6, CAI 3.8
- With abdomen-only fallback: CSAS, CAI 45.1 (217 events reclassified)

References
----------
- AASM Manual 2.6, Chapter 2 (Respiratory signals)
- Kushida et al. 2005 — PSG sensor reliability
- Redline et al. 2004 — Inter-scorer variability due to signal quality
"""

from __future__ import annotations
import logging
from typing import Literal, TypedDict

import numpy as np
from scipy.signal import hilbert, welch

logger = logging.getLogger("psgscoring.signal_quality")


# ════════════════════════════════════════════════════════════════════
#  Type definitions
# ════════════════════════════════════════════════════════════════════

ChannelStatus = Literal["ok", "weak", "failed"]
EventClassification = Literal["obstructive", "central", "uncertain"]


class ChannelQuality(TypedDict):
    mad: float
    breath_energy: float
    peak_freq: float | None
    status: ChannelStatus
    reason: str


class PairQuality(TypedDict):
    thorax: ChannelQuality
    abdomen: ChannelQuality
    energy_ratio: float
    warnings: list[str]
    classification_reliable: bool
    recommended_mode: Literal["bilateral", "single-channel", "unreliable"]
    working_channel: Literal["thorax", "abdomen", "none"] | None


# ════════════════════════════════════════════════════════════════════
#  Thresholds (empirically calibrated)
# ════════════════════════════════════════════════════════════════════

# Per-channel thresholds
MAD_FAILED_BELOW      = 0.005   # Below this: sensor is dead
MAD_WEAK_BELOW        = 0.020   # Below this: sensor is weak
ENERGY_FAILED_BELOW   = 0.001   # Breath-band energy (Welch PSD sum)
ENERGY_WEAK_BELOW     = 0.050

# Pair thresholds
ENERGY_RATIO_WARN     = 10.0    # 10× asymmetry is suspicious
ENERGY_RATIO_FAIL     = 100.0   # 100× means one channel is ~dead

# Breathing band for energy computation
BREATH_FREQ_LOW       = 0.10    # Hz (6 breaths/min minimum)
BREATH_FREQ_HIGH      = 0.50    # Hz (30 breaths/min maximum)

# Single-channel fallback thresholds
FALLBACK_CENTRAL_RATIO      = 0.20   # Event envelope <20% baseline → central
FALLBACK_OBSTRUCTIVE_RATIO  = 0.50   # Event envelope >50% baseline → obstructive
FALLBACK_BASELINE_WINDOW_S  = 120.0  # Baseline = preceding 2 minutes
FALLBACK_BASELINE_PERCENTILE = 75    # Robust to event clusters


# ════════════════════════════════════════════════════════════════════
#  Core functions
# ════════════════════════════════════════════════════════════════════

def assess_rip_channel(
    signal: np.ndarray,
    sf: float,
    label: str = "",
) -> ChannelQuality:
    """
    Assess quality of a single RIP channel.

    Parameters
    ----------
    signal : np.ndarray
        Raw RIP signal (time domain)
    sf : float
        Sample rate in Hz
    label : str
        Optional label for logging

    Returns
    -------
    dict with keys: mad, breath_energy, peak_freq, status, reason
    """
    if signal is None or len(signal) == 0:
        return {
            "mad": 0.0,
            "breath_energy": 0.0,
            "peak_freq": None,
            "status": "failed",
            "reason": "Empty signal",
        }

    mad = float(np.median(np.abs(signal - np.median(signal))))

    # Welch PSD for breath-band energy
    nperseg = int(min(60 * sf, max(len(signal) // 4, 64)))
    try:
        f, psd = welch(signal, sf, nperseg=nperseg)
    except Exception as e:
        logger.debug(f"[{label}] Welch failed: {e}")
        return {
            "mad": mad,
            "breath_energy": 0.0,
            "peak_freq": None,
            "status": "failed",
            "reason": f"PSD computation failed: {e}",
        }

    breath_mask = (f >= BREATH_FREQ_LOW) & (f <= BREATH_FREQ_HIGH)
    breath_energy = float(np.sum(psd[breath_mask]))

    if np.any(breath_mask):
        peak_freq = float(f[breath_mask][np.argmax(psd[breath_mask])])
    else:
        peak_freq = None

    # Classification
    if mad < MAD_FAILED_BELOW or breath_energy < ENERGY_FAILED_BELOW:
        status = "failed"
        reason = (f"MAD={mad:.4f} (<{MAD_FAILED_BELOW}), "
                  f"energy={breath_energy:.2e} (<{ENERGY_FAILED_BELOW:.0e})")
    elif mad < MAD_WEAK_BELOW or breath_energy < ENERGY_WEAK_BELOW:
        status = "weak"
        reason = (f"MAD={mad:.4f}, energy={breath_energy:.2e} — "
                  f"below normal but above failure threshold")
    else:
        status = "ok"
        reason = (f"MAD={mad:.4f}, energy={breath_energy:.2e} — within normal range")

    if label:
        logger.debug(f"[{label}] quality: {status} — {reason}")

    return {
        "mad": mad,
        "breath_energy": breath_energy,
        "peak_freq": peak_freq,
        "status": status,
        "reason": reason,
    }


def compare_rip_pair(
    thorax: np.ndarray,
    abdomen: np.ndarray,
    sf: float,
) -> PairQuality:
    """
    Compare thorax + abdomen RIP pair to detect channel failure,
    inversion, or extreme asymmetry.

    Parameters
    ----------
    thorax, abdomen : np.ndarray
        Raw RIP signals (time domain, same length)
    sf : float
        Sample rate in Hz

    Returns
    -------
    dict with:
        thorax, abdomen: ChannelQuality
        energy_ratio: float (max/min of breath-band energies)
        warnings: list of clinical warning strings
        classification_reliable: bool
        recommended_mode: 'bilateral' | 'single-channel' | 'unreliable'
        working_channel: 'thorax' | 'abdomen' | 'none' (when single-channel)
    """
    thor_q = assess_rip_channel(thorax, sf, "thorax")
    abd_q = assess_rip_channel(abdomen, sf, "abdomen")

    # Energy ratio (max / min)
    thor_e = max(thor_q["breath_energy"], 1e-12)
    abd_e = max(abd_q["breath_energy"], 1e-12)
    ratio = max(thor_e, abd_e) / min(thor_e, abd_e)

    warnings_list: list[str] = []
    thor_ok = thor_q["status"] == "ok"
    abd_ok = abd_q["status"] == "ok"
    thor_failed = thor_q["status"] == "failed"
    abd_failed = abd_q["status"] == "failed"

    # Determine mode
    if thor_failed and abd_failed:
        mode = "unreliable"
        working_ch = "none"
        warnings_list.append(
            "Both RIP channels failed. No effort-based classification possible. "
            "Results should be treated as uninterpretable for central/obstructive typing."
        )
    elif thor_failed and not abd_failed:
        mode = "single-channel"
        working_ch = "abdomen"
        warnings_list.append(
            "Thorax RIP failed — abdomen-only classification. "
            "Paradoxical phase detection unavailable."
        )
    elif abd_failed and not thor_failed:
        mode = "single-channel"
        working_ch = "thorax"
        warnings_list.append(
            "Abdomen RIP failed — thorax-only classification. "
            "Paradoxical phase detection unavailable."
        )
    elif ratio > ENERGY_RATIO_FAIL:
        mode = "single-channel"
        weak = "thorax" if thor_e < abd_e else "abdomen"
        working_ch = "abdomen" if weak == "thorax" else "thorax"
        warnings_list.append(
            f"RIP energy ratio {ratio:.0f}× — {weak} likely disconnected. "
            f"Using {working_ch}-only classification."
        )
    elif ratio > ENERGY_RATIO_WARN:
        mode = "bilateral"
        working_ch = None
        warnings_list.append(
            f"RIP energy ratio {ratio:.1f}× — modest asymmetry. "
            f"Classification proceeds bilaterally but review recommended."
        )
    elif not thor_ok or not abd_ok:
        mode = "bilateral"
        working_ch = None
        warnings_list.append(
            f"One or both RIP channels weak (thorax={thor_q['status']}, "
            f"abdomen={abd_q['status']}). Effort classification may be less reliable."
        )
    else:
        mode = "bilateral"
        working_ch = None

    classification_reliable = (mode == "bilateral" and len(warnings_list) == 0)

    return {
        "thorax": thor_q,
        "abdomen": abd_q,
        "energy_ratio": float(ratio),
        "warnings": warnings_list,
        "classification_reliable": classification_reliable,
        "recommended_mode": mode,
        "working_channel": working_ch,
    }


def single_channel_fallback_classify(
    apnea_start_s: float,
    apnea_end_s: float,
    effort_signal: np.ndarray,
    sf: float,
    baseline_window_s: float = FALLBACK_BASELINE_WINDOW_S,
) -> EventClassification:
    """
    Classify event using only ONE effort signal (when bilateral fails).

    Parameters
    ----------
    apnea_start_s, apnea_end_s : event boundaries (seconds)
    effort_signal : array — the working (thorax OR abdomen) signal
    sf : sample rate
    baseline_window_s : pre-event baseline window (default 120s)

    Returns
    -------
    'central' | 'obstructive' | 'uncertain'

    Logic
    -----
    - Event envelope (Hilbert median) compared to baseline P75 envelope
    - <20% of baseline → central
    - >50% of baseline → obstructive
    - Between → uncertain (flagged for manual review)
    """
    i0 = int(apnea_start_s * sf)
    i1 = int(apnea_end_s * sf)
    bl_i0 = max(0, i0 - int(baseline_window_s * sf))

    if i1 - i0 < int(2 * sf):
        return "uncertain"
    if i0 - bl_i0 < int(10 * sf):
        return "uncertain"

    bl_seg = effort_signal[bl_i0:i0]
    ev_seg = effort_signal[i0:i1]

    try:
        bl_env = np.abs(hilbert(bl_seg))
        ev_env = np.abs(hilbert(ev_seg))
    except Exception:
        return "uncertain"

    bl_amp = float(np.percentile(bl_env, FALLBACK_BASELINE_PERCENTILE))
    ev_amp = float(np.median(ev_env))

    if bl_amp < 1e-9:
        return "uncertain"

    ratio = ev_amp / bl_amp

    if ratio < FALLBACK_CENTRAL_RATIO:
        return "central"
    elif ratio > FALLBACK_OBSTRUCTIVE_RATIO:
        return "obstructive"
    else:
        return "uncertain"


def quality_warning_text(quality: PairQuality, lang: str = "en") -> str | None:
    """
    Generate clinical warning text for PDF report / dashboard.
    Multilingual: en, nl, fr, de.

    Returns None if classification is reliable (no warning needed).
    """
    if quality["classification_reliable"]:
        return None

    I18N = {
        "en": {
            "header": "⚠ RESPIRATORY EFFORT SIGNAL QUALITY WARNING",
            "impact": "IMPACT ON SCORING:",
            "impact_items": [
                "Central/mixed apnea classification may be INCORRECT",
                "Obstructive classifications may be FALSE POSITIVES",
                "Manual review of effort signals strongly recommended",
            ],
            "recommendation": "RECOMMENDATION:",
            "rec_text": (
                "Verify sensor placement and calibration. If signal cannot be "
                "salvaged, consider re-study or expert scorer review."
            ),
        },
        "nl": {
            "header": "⚠ WAARSCHUWING — KWALITEIT RESPIRATOIRE EFFORT-SIGNALEN",
            "impact": "IMPACT OP SCORING:",
            "impact_items": [
                "Classificatie centraal/gemengde apneu mogelijk ONJUIST",
                "Obstructieve classificaties mogelijk VALS-POSITIEF",
                "Manuele review van effort-signalen sterk aanbevolen",
            ],
            "recommendation": "AANBEVELING:",
            "rec_text": (
                "Verifieer sensorplaatsing en kalibratie. Als signaal niet "
                "kan worden hersteld: overweeg herhaalstudie of expert-scoring."
            ),
        },
        "fr": {
            "header": "⚠ AVERTISSEMENT — QUALITÉ DES SIGNAUX D'EFFORT RESPIRATOIRE",
            "impact": "IMPACT SUR LE SCORING:",
            "impact_items": [
                "Classification apnée centrale/mixte possiblement INCORRECTE",
                "Classifications obstructives possiblement FAUX POSITIFS",
                "Révision manuelle des signaux d'effort fortement recommandée",
            ],
            "recommendation": "RECOMMANDATION:",
            "rec_text": (
                "Vérifier placement et calibration des capteurs. "
                "Envisager une nouvelle étude si le signal ne peut être récupéré."
            ),
        },
        "de": {
            "header": "⚠ WARNUNG — QUALITÄT DER ATEMANSTRENGUNGSSIGNALE",
            "impact": "AUSWIRKUNG AUF SCORING:",
            "impact_items": [
                "Klassifikation zentraler/gemischter Apnoen möglicherweise FALSCH",
                "Obstruktive Klassifikationen möglicherweise FALSCH-POSITIV",
                "Manuelle Überprüfung der Effort-Signale dringend empfohlen",
            ],
            "recommendation": "EMPFEHLUNG:",
            "rec_text": (
                "Sensorpositionierung und Kalibrierung überprüfen. "
                "Bei irreparablem Signal: Wiederholung oder Experten-Scoring erwägen."
            ),
        },
    }

    t = I18N.get(lang, I18N["en"])

    parts = [t["header"], ""]
    for w in quality["warnings"]:
        parts.append(f"  • {w}")
    parts.extend([
        "",
        t["impact"],
        *(f"  - {item}" for item in t["impact_items"]),
        "",
        t["recommendation"],
        f"  {t['rec_text']}",
    ])
    return "\n".join(parts)


def quality_badge_summary(quality: PairQuality) -> dict:
    """
    Compact badge info for dashboard UI.

    Returns
    -------
    dict with:
        level: 'ok' | 'warning' | 'danger'  — for color coding
        label: short label (single word)
        tooltip: detailed explanation
    """
    mode = quality["recommended_mode"]
    if mode == "bilateral" and quality["classification_reliable"]:
        return {
            "level": "ok",
            "label": "OK",
            "tooltip": "Both RIP channels functioning normally.",
        }
    elif mode == "bilateral":
        return {
            "level": "warning",
            "label": "Weak",
            "tooltip": (quality["warnings"][0]
                        if quality["warnings"]
                        else "One or both effort channels weak."),
        }
    elif mode == "single-channel":
        working = quality["working_channel"] or "unknown"
        return {
            "level": "warning",
            "label": f"{working.capitalize()}-only",
            "tooltip": (quality["warnings"][0]
                        if quality["warnings"]
                        else f"Single-channel fallback using {working}."),
        }
    else:  # unreliable
        return {
            "level": "danger",
            "label": "Failed",
            "tooltip": (quality["warnings"][0]
                        if quality["warnings"]
                        else "Both RIP channels failed — classification unreliable."),
        }


# ════════════════════════════════════════════════════════════════════
#  Public API
# ════════════════════════════════════════════════════════════════════

__all__ = [
    "assess_rip_channel",
    "compare_rip_pair",
    "single_channel_fallback_classify",
    "quality_warning_text",
    "quality_badge_summary",
    "ChannelQuality",
    "PairQuality",
    "ChannelStatus",
    "EventClassification",
]
