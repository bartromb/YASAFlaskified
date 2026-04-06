"""
pneumo_analysis.py — YASAFlaskified v0.8.25
===========================================
Backward-compatibility shim.

In v0.8.11 the monolithic pneumo_analysis module (2 439 lines) has been split
into the modular ``psgscoring`` package:

    psgscoring/
        constants.py   – AASM thresholds, channel patterns
        utils.py       – helpers, sleep mask, channel detection
        signal.py      – preprocessing, baselines, MMSD, linearisation
        breath.py      – breath-by-breath segmentation and events
        classify.py    – apnea-type classification
        spo2.py        – SpO2 coupling and ODI analysis
        plm.py         – PLM detection (AASM 2.6)
        ancillary.py   – position, heart rate, snoring, Cheyne-Stokes
        respiratory.py – event detection, Rule 1B, summary
        pipeline.py    – MNE-facing master function

This file re-exports every name that the rest of the application imports so
that tasks.py, app.py, and any other modules continue to work without change.

All logic now lives in psgscoring.  This file contains NO signal-processing
code.
"""

# Re-export everything from the modular package
from psgscoring.constants import (                    # noqa: F401
    APNEA_THRESHOLD, HYPOPNEA_THRESHOLD,
    APNEA_MIN_DUR_S, HYPOPNEA_MIN_DUR_S,
    DESATURATION_DROP_PCT,
    EFFORT_ABSENT_RATIO, EFFORT_PRESENT_RATIO,
    MIXED_SPLIT_FRACTION, EPOCH_LEN_S, BASELINE_WINDOW_S,
    CHANNEL_PATTERNS, POSITION_MAP, RULE1B_AROUSAL_WINDOW_S,
)
from psgscoring.utils import (                        # noqa: F401
    safe_r,
    fmt_time as _fmt_time,
    hypno_to_numeric,
    is_nrem, is_rem, is_sleep,
    build_sleep_mask,
    detect_channels,
    channel_map_from_user,
)
from psgscoring.signal import (                       # noqa: F401
    linearize_nasal_pressure,
    compute_mmsd,
    bandpass_flow,
    preprocess_flow,
    preprocess_effort,
    compute_dynamic_baseline,
    compute_stage_baseline,
    detect_position_changes,
    reset_baseline_at_position_changes,
)
from psgscoring.breath import (                       # noqa: F401
    detect_breaths,
    compute_breath_amplitudes,
    compute_flattening_index,
    detect_breath_events,
)
from psgscoring.classify import classify_apnea_type   # noqa: F401
from psgscoring.spo2 import (                         # noqa: F401
    analyze_spo2,
    detect_desaturations as _detect_desaturations,
    get_desaturation as _get_desaturation,
)
from psgscoring.respiratory import (                  # noqa: F401
    detect_respiratory_events,
    reinstate_rule1b_hypopneas,
    _compute_summary as _compute_respiratory_summary,
)
from psgscoring.ancillary import (                    # noqa: F401
    analyze_position,
    analyze_heart_rate,
    analyze_snore,
    detect_cheyne_stokes,
)
from psgscoring.plm import analyze_plm                # noqa: F401
from psgscoring.pipeline import run_pneumo_analysis   # noqa: F401
