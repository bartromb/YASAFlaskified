"""
psgscoring.pipeline — v0.4.0 profile-aware integration
=======================================================

This module shows the integration pattern for profile-based scoring.
It replaces the v0.3.x hardcoded `strict`/`standard`/`sensitive` logic
with a unified profile dispatcher.

For v0.4.0, the only changes needed in the existing pipeline.py are:
    1. Import from psgscoring.profiles
    2. Replace internal parameter constants with profile lookups
    3. Add profile metadata to audit output
    4. Support profile_group for confidence-interval runs

All existing single-profile API calls continue to work unchanged.
"""

from __future__ import annotations

import uuid
import datetime
from typing import Any, Dict, List, Optional, Union

from psgscoring.profiles import (
    Profile,
    get_profile,
    resolve_profile_name,
    profile_metadata,
    PROFILE_GROUPS,
    list_profiles,
)

# Assume these exist in existing psgscoring code
# from psgscoring.respiratory import detect_events
# from psgscoring.postprocess import apply_corrections
# from psgscoring.spo2 import compute_hypoxic_burden


def run_pneumo_analysis(
    edf_path: str,
    profile: Union[str, Profile] = "aasm_v3_rec",
    profile_group: Optional[str] = None,
    hypnogram: Optional[Any] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Run respiratory event analysis under one or more scoring profiles.

    Parameters
    ----------
    edf_path : str
        Path to EDF recording.
    profile : str or Profile, default "aasm_v3_rec"
        Single scoring profile. Ignored if profile_group is given.
    profile_group : str, optional
        Named group of profiles (runs all and returns confidence interval).
        One of: "clinical", "aasm_era", "coverage", "dataset", "full_6", "all".
    hypnogram : array-like, optional
        Pre-computed hypnogram; if None, YASA staging is performed.
    **kwargs
        Passed to internal detection stages (sampling rates, channel names, etc.).

    Returns
    -------
    dict
        If single profile:
            {
                "profile": <metadata>,
                "events": [...],
                "summary": {"ahi": ..., "oahi": ..., ...},
                "audit": {"analysis_id": ..., "profile_name": ...},
            }
        If profile group:
            {
                "profile_group": "clinical",
                "profiles_run": ["aasm_v3_strict", "aasm_v3_rec", "aasm_v3_sensitive"],
                "results": {
                    "aasm_v3_strict":    {...},
                    "aasm_v3_rec":       {...},
                    "aasm_v3_sensitive": {...},
                },
                "confidence_interval": {
                    "ahi_range": (4.0, 8.1),
                    "severity_classes": ["Normal", "Mild", "Mild"],
                    "robustness_grade": "B",
                },
            }
    """
    analysis_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if profile_group is not None:
        return _run_profile_group(
            edf_path=edf_path,
            group_name=profile_group,
            hypnogram=hypnogram,
            analysis_id=analysis_id,
            timestamp=timestamp,
            **kwargs,
        )

    # Single profile run
    if isinstance(profile, str):
        profile_obj = get_profile(profile)
    elif isinstance(profile, Profile):
        profile_obj = profile
    else:
        raise TypeError(
            f"profile must be str or Profile, got {type(profile).__name__}"
        )

    return _run_single_profile(
        edf_path=edf_path,
        profile=profile_obj,
        hypnogram=hypnogram,
        analysis_id=analysis_id,
        timestamp=timestamp,
        **kwargs,
    )


def _run_single_profile(
    edf_path: str,
    profile: Profile,
    hypnogram: Optional[Any],
    analysis_id: str,
    timestamp: str,
    **kwargs,
) -> Dict[str, Any]:
    """Core single-profile analysis."""

    # --- Load signals ---
    # signals, sampling_rates = load_edf_signals(edf_path, **kwargs)
    signals = {}  # placeholder

    # --- Hypnogram ---
    if hypnogram is None:
        # hypnogram = run_yasa_staging(signals)
        hypnogram = None  # placeholder

    # --- Event detection per profile parameters ---
    # The existing detect_events() function gains one new argument:
    # the Profile object. Internally it reads:
    #   profile.hypopnea.flow_reduction_threshold
    #   profile.hypopnea.sensor
    #   profile.hypopnea.desat_threshold
    #   profile.hypopnea.desat_or_arousal
    #   profile.apnea.flow_reduction_threshold
    #   profile.spo2.baseline_window_s
    #   profile.post_processing.stability_filter_cv
    #   ...etc
    events = _detect_events_for_profile(signals, hypnogram, profile)

    # --- Compute summary AHI/OAHI/RDI ---
    summary = _compute_summary(events, hypnogram, profile)

    # --- Dataset profiles: emit multiple AHI variants ---
    if profile.hypopnea.output_variants:
        summary["ahi_variants"] = _compute_ahi_variants(
            events, hypnogram, profile.hypopnea.output_variants
        )

    return {
        "profile":  profile_metadata(profile.name),
        "events":   events,
        "summary":  summary,
        "audit": {
            "analysis_id":       analysis_id,
            "timestamp":         timestamp,
            "psgscoring_version": "0.4.0",
            "profile_name":       profile.name,
            "profile_config":     profile.to_dict(),
        },
    }


def _run_profile_group(
    edf_path: str,
    group_name: str,
    hypnogram: Optional[Any],
    analysis_id: str,
    timestamp: str,
    **kwargs,
) -> Dict[str, Any]:
    """Run multiple profiles and produce confidence-interval output."""

    if group_name not in PROFILE_GROUPS:
        raise KeyError(
            f"Unknown profile group '{group_name}'. "
            f"Available: {', '.join(PROFILE_GROUPS.keys())}"
        )

    profile_names = PROFILE_GROUPS[group_name]
    results: Dict[str, Any] = {}

    for pname in profile_names:
        results[pname] = _run_single_profile(
            edf_path=edf_path,
            profile=get_profile(pname),
            hypnogram=hypnogram,
            analysis_id=f"{analysis_id}-{pname}",
            timestamp=timestamp,
            **kwargs,
        )

    # Compute confidence interval across profiles
    ahis = [r["summary"].get("ahi", 0.0) for r in results.values()]
    severities = [_ahi_to_severity(a) for a in ahis]
    grade = _robustness_grade(severities)

    return {
        "profile_group":  group_name,
        "profiles_run":   profile_names,
        "results":        results,
        "confidence_interval": {
            "ahi_range":        (min(ahis), max(ahis)),
            "ahis":             dict(zip(profile_names, ahis)),
            "severity_classes": severities,
            "robustness_grade": grade,
        },
        "audit": {
            "analysis_id":        analysis_id,
            "timestamp":          timestamp,
            "psgscoring_version": "0.4.0",
            "profile_group":      group_name,
        },
    }


# ============================================================
# Helpers
# ============================================================

def _ahi_to_severity(ahi: float) -> str:
    """AASM severity classification (same for all profiles)."""
    if ahi < 5:
        return "Normal"
    elif ahi < 15:
        return "Mild"
    elif ahi < 30:
        return "Moderate"
    else:
        return "Severe"


def _robustness_grade(severities: List[str]) -> str:
    """
    A = all profiles agree on severity class
    B = two of three agree
    C = all discordant
    """
    unique = set(severities)
    if len(unique) == 1:
        return "A"
    elif len(unique) == 2:
        return "B"
    else:
        return "C"


# ------- Placeholder integration points -------
# These stubs show WHERE existing psgscoring code reads profile parameters.
# In the actual integration, the existing detect_events / apply_corrections
# functions gain a `profile: Profile` parameter and replace their hardcoded
# constants with profile.hypopnea.* / profile.apnea.* / etc.

def _detect_events_for_profile(signals, hypnogram, profile: Profile):
    """
    Integration pattern for event detection.

    In the real pipeline:
        from psgscoring.respiratory import detect_events
        events = detect_events(
            signals=signals,
            hypnogram=hypnogram,
            flow_reduction=profile.hypopnea.flow_reduction_threshold,
            sensor=profile.hypopnea.sensor,
            min_dur=profile.hypopnea.min_duration_s,
            max_dur=profile.hypopnea.max_duration_s,
            desat_thresh=profile.hypopnea.desat_threshold,
            desat_or_arousal=profile.hypopnea.desat_or_arousal,
            apnea_thresh=profile.apnea.flow_reduction_threshold,
            spo2_baseline_s=profile.spo2.baseline_window_s,
            nadir_search_s=profile.spo2.nadir_search_s,
            stability_cv=profile.post_processing.stability_filter_cv,
            flow_smoothing_s=profile.post_processing.flow_smoothing_s,
            breath_level=profile.post_processing.breath_level_detection,
            unsure_as_hypopnea=profile.post_processing.unsure_as_hypopnea,
        )
        return events
    """
    return []  # placeholder


def _compute_summary(events, hypnogram, profile: Profile) -> Dict[str, Any]:
    """Compute AHI and related indices."""
    return {
        "ahi":  0.0,
        "oahi": 0.0,
        "cahi": 0.0,
        "rdi":  0.0,
        "n_events": len(events),
    }


def _compute_ahi_variants(events, hypnogram, variants: List[str]) -> Dict[str, float]:
    """
    Compute multiple AHI variants (NSRR MESA convention).

    variants example: ["ahi_3pct", "ahi_3pct_arousal", "ahi_4pct"]
    """
    out = {}
    for v in variants:
        # Filter events by variant-specific desaturation/arousal criteria
        out[v] = 0.0  # placeholder
    return out
