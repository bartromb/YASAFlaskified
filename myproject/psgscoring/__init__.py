"""
psgscoring
==========
Open-source Python library for AASM 2.6-compliant PSG respiratory scoring.

Quick start
-----------
>>> from psgscoring import run_pneumo_analysis
>>> results = run_pneumo_analysis(raw, hypno)
>>> ahi = results["respiratory"]["summary"]["ahi_total"]

Module layout
-------------
constants    – AASM thresholds and channel-name patterns
utils        – safe_r, hypno helpers, sleep mask, channel detection
signal       – preprocessing: linearize, MMSD, bandpass, envelope, baselines
breath       – breath segmentation, amplitude ratios, flattening index
classify     – apnea-type classification (obstructive / central / mixed)
spo2         – SpO2 coupling (Rule 1A) and full SpO2 analysis
plm          – PLM detection (AASM 2.6)
ancillary    – position, heart rate, snore, Cheyne-Stokes
respiratory  – apnea/hypopnea detection, Rule 1B, summary statistics
ecg_effort   – ECG-derived effort (TECG, spectral classifier) for central/obstructive differentiation
pipeline     – MNE-facing master function (run_pneumo_analysis)
"""

# Public API
from .pipeline import run_pneumo_analysis

from .respiratory import (
    detect_respiratory_events,
    reinstate_rule1b_hypopneas,
)
from .signal import (
    linearize_nasal_pressure,
    compute_mmsd,
    preprocess_flow,
    preprocess_effort,
    bandpass_flow,
    compute_dynamic_baseline,
    compute_stage_baseline,
    compute_anchor_baseline,
    detect_position_changes,
    reset_baseline_at_position_changes,
)
from .breath import (
    detect_breaths,
    compute_breath_amplitudes,
    compute_flattening_index,
    detect_breath_events,
)
from .classify import classify_apnea_type
from .ecg_effort import ecg_effort_assessment, compute_tecg, compute_adaptive_cardiac_band
from .spo2 import analyze_spo2, detect_desaturations, get_desaturation
from .plm import analyze_plm
from .ancillary import (
    analyze_position,
    analyze_heart_rate,
    analyze_snore,
    detect_cheyne_stokes,
)
from .utils import (
    detect_channels,
    channel_map_from_user,
    build_sleep_mask,
    hypno_to_numeric,
    is_nrem, is_rem, is_sleep,
    safe_r,
)

__version__ = "0.2.5"
__all__ = [
    # Master
    "run_pneumo_analysis",
    # Respiratory
    "detect_respiratory_events",
    "reinstate_rule1b_hypopneas",
    # Signal
    "linearize_nasal_pressure",
    "compute_mmsd",
    "preprocess_flow",
    "preprocess_effort",
    "bandpass_flow",
    "compute_dynamic_baseline",
    "compute_stage_baseline",
    "compute_anchor_baseline",
    "detect_position_changes",
    "reset_baseline_at_position_changes",
    # Breath
    "detect_breaths",
    "compute_breath_amplitudes",
    "compute_flattening_index",
    "detect_breath_events",
    # Classify
    "classify_apnea_type",
    # ECG effort
    "ecg_effort_assessment",
    "compute_adaptive_cardiac_band",
    "compute_tecg",
    # SpO2
    "analyze_spo2",
    "detect_desaturations",
    "get_desaturation",
    # PLM
    "analyze_plm",
    # Ancillary
    "analyze_position",
    "analyze_heart_rate",
    "analyze_snore",
    "detect_cheyne_stokes",
    # Utils
    "detect_channels",
    "channel_map_from_user",
    "build_sleep_mask",
    "hypno_to_numeric",
    "is_nrem", "is_rem", "is_sleep",
    "safe_r",
]
