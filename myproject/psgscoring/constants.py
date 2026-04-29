"""
psgscoring.constants
====================
AASM 2.6 thresholds, channel-name patterns, and other shared constants.

v0.4.0: SCORING_PROFILES is now derived from psgscoring.profiles. The
dataclass-based registry in profiles.py is the single source of truth.
This module renders those dataclasses into the legacy dict format that
respiratory.py expects, preserving backward compatibility.

All non-profile constants (CHANNEL_PATTERNS, EPOCH_LEN_S, etc.) remain
unchanged from v0.3.2.

Nothing in this module imports from other psgscoring submodules other
than .profiles, so it is safe to import from any layer of the package.
"""

# ---------------------------------------------------------------------------
# AASM 2.6 respiratory scoring thresholds (used by respiratory.py as fallback)
# ---------------------------------------------------------------------------
APNEA_THRESHOLD        = 0.10   # flow < 10% of baseline -> apnea
HYPOPNEA_THRESHOLD     = 0.70   # flow < 70% of baseline -> hypopnea candidate
HYPOPNEA_SMOOTH_S      = 0.0    # v0.2.8: removed (was 3.0, caused +54 false hyp)
APNEA_MIN_DUR_S        = 10.0   # seconds
HYPOPNEA_MIN_DUR_S     = 10.0   # seconds
APNEA_MAX_DUR_S        = 90.0   # v0.8.22: events >90s are split at partial recovery
HYPOPNEA_MAX_DUR_S     = 60.0   # v0.8.22: events >60s are split at partial recovery
DESATURATION_DROP_PCT  = 3.0    # >= 3% SpO2 drop required for Rule 1A
EFFORT_ABSENT_RATIO    = 0.20   # < 20% of baseline effort -> absent
EFFORT_PRESENT_RATIO   = 0.40   # > 40% of baseline effort -> present
MIXED_SPLIT_FRACTION   = 0.50   # first 50% = central portion of mixed apnea

EPOCH_LEN_S            = 30     # seconds per hypnogram epoch
BASELINE_WINDOW_S      = 300    # 5-minute dynamic baseline window

# Rule 1B coupling window
RULE1B_AROUSAL_WINDOW_S = 15.0  # arousal must follow event end within 15 s

# SpO2 nadir search window (seconds after event end)
POST_EVENT_WINDOW_S    = 45     # v0.8.14: was 30; finger oximetry delay 20-40s

# Cross-contamination window (seconds between events)
CROSS_CONTAM_WINDOW_S  = 15.0   # v0.8.14: was 30; flag only, not blocker

# ---------------------------------------------------------------------------
# Scoring profiles: derived from psgscoring.profiles registry (v0.4.0+)
# ---------------------------------------------------------------------------
# The dataclass-based Profile registry in profiles.py is now the single
# source of truth. This adapter renders them as dicts for backward
# compatibility with respiratory.py.

from .profiles import PROFILES as _PROFILES_REGISTRY


def _profile_to_legacy_dict(profile) -> dict:
    """Render a Profile dataclass into the dict format respiratory.py expects.

    Mappings:
      flow_reduction_threshold (0.30 = 30% drop)  -> HYPOPNEA_THRESHOLD = 1 - 0.30 = 0.70
        (respiratory.py uses HYPOPNEA_THRESHOLD as "flow must drop BELOW this fraction
         of baseline" — so a 30% reduction means flow <= 70% baseline)
      desat_threshold (0.03)                       -> DESATURATION_DROP_PCT = 3.0
      flow_smoothing_s                             -> HYPOPNEA_SMOOTH_S
      breath_level_detection                       -> USE_PEAK_DETECTION
      etc.
    """
    h = profile.hypopnea
    pp = profile.post_processing

    return {
        "label":                  profile.display_name,
        "HYPOPNEA_THRESHOLD":     round(1.0 - h.flow_reduction_threshold, 4),
        "DESATURATION_DROP_PCT":  round((h.desat_threshold or 0.03) * 100, 1),
        "POST_EVENT_WINDOW_S":    int(profile.spo2.nadir_search_s),
        "HYPOPNEA_SMOOTH_S":      pp.flow_smoothing_s,
        "CROSS_CONTAM_WINDOW_S":  15.0 if pp.artefact_flank_exclusion else 0.0,
        "USE_PEAK_DETECTION":     pp.breath_level_detection,
        "USE_BREATH_SNAP":        False,  # only enabled in legacy "sensitive" alias
        "PEAK_MIN_CONSECUTIVE_BREATHS": pp.peak_min_consecutive_breaths,
        "HYPOPNEA_MAX_DUR_S":     h.max_duration_s,
        "APNEA_MAX_DUR_S":        profile.apnea.max_duration_s,
        # NEW in v0.4.0 — exposed for v1/CMS/Chicago profiles
        "DESAT_OR_AROUSAL":       h.desat_or_arousal,
        "DESAT_REQUIRED":         h.desat_required,
        "STABILITY_FILTER_CV":    pp.stability_filter_cv,
        # v0.4.2: profile-aware local baseline validation
        "LOCAL_BL_CV_THRESHOLD":  pp.local_baseline_cv_threshold,
        "LOCAL_BL_STRICT_RED":    pp.local_baseline_strict_reduction,
        # Audit metadata — read by pipeline.py for output["meta"]["profile"]
        "_PROFILE_NAME":          profile.name,
        "_AASM_VERSION":          profile.aasm_version,
        "_AASM_RULE":             profile.aasm_rule,
    }


def _build_legacy_profiles() -> dict:
    """Build the legacy SCORING_PROFILES dict from the new Profile registry.

    Includes legacy aliases (strict/standard/sensitive) pointing to the
    canonical v0.4.0 names (aasm_v3_strict/aasm_v3_rec/aasm_v3_sensitive).
    """
    profiles: dict[str, dict] = {}
    for name, p in _PROFILES_REGISTRY.items():
        d = _profile_to_legacy_dict(p)
        # Preserve legacy quirk: only the historical "sensitive" enabled snapping
        if name == "aasm_v3_sensitive":
            d["USE_BREATH_SNAP"] = True
        profiles[name] = d

    # Legacy aliases (same dict content as canonical names; respiratory.py
    # never sees these unless an old caller passes scoring_profile="standard")
    profiles["strict"]    = profiles["aasm_v3_strict"]
    profiles["standard"]  = profiles["aasm_v3_rec"]
    profiles["sensitive"] = profiles["aasm_v3_sensitive"]
    return profiles


SCORING_PROFILES: dict[str, dict] = _build_legacy_profiles()

# MMSD apnea-validation threshold (fraction of baseline)
MMSD_APNEA_THRESH      = 0.40   # MMSD > 40% of baseline -> residual breathing
MMSD_CONFIRM_THRESH    = 0.15   # MMSD < 15% -> breathing truly absent

# ---------------------------------------------------------------------------
# EDF channel-name patterns  (multilingual: EN / NL / DE / FR)
# ---------------------------------------------------------------------------
CHANNEL_PATTERNS: dict[str, list[str]] = {
    # AASM 2.6: nasal pressure transducer -> hypopnea (more sensitive)
    "flow_pressure": [
        "nasal pressure", "nasalpressure", "ptaf", "pnasale",
        "cannula", "npt", "nasal pres", "pflow", "np ",
        "naf", "nasal flow",
    ],
    # AASM 2.6: oronasal thermistor -> apnea (detects cessation)
    "flow_thermistor": [
        "thermistor", "therm", "thermist", "oronasal",
        "oro-nasal", "airflow", "air flow",
    ],
    # Generic fallback
    "flow":     ["flow", "nasal", "resp flow"],
    "thorax":   ["thorax", "thor", "chest", "thoracic", "ribcage",
                 "effort thor", "rc", "rib", "chest belt", "rcg"],
    "abdomen":  ["abdom", "abd", "belly", "effort abd", "ab",
                 "abdominal", "effort abdom", "abd belt", "abdo"],
    "spo2":     ["spo2", "sao2", "saturation", "o2", "oximetry",
                 "puls spo2", "pulse ox"],
    "pulse":    ["pulse", "pr", "heart rate", "hr", "puls rate"],
    "ecg":      ["ecg", "ekg", "cardiac", "einthoven", "ii", "ecg ii"],
    "position": ["position", "positie", "pos", "body pos", "lage",
                 "body position", "bpos"],
    "snore":    ["snore", "snoring", "ronfle", "ronchus", "micro",
                 "snurk", "snore mic", "microphone"],
    "leg_l":    ["leg l", "lleg", "emg leg l", "tibial l", "left leg",
                 "plo", "pla", "plg l", "lat l", "lats l",
                 "bein l", "bein li", "jambe g", "tib ant l",
                 "emg tib l", "emg tibant l", "plm l", "plm-l",
                 "emg la", "ta l", "ta li"],
    "leg_r":    ["leg r", "rleg", "emg leg r", "tibial r", "right leg",
                 "pro", "pra", "plg r", "lat r", "lats r",
                 "bein r", "bein re", "jambe d", "tib ant r",
                 "emg tib r", "emg tibant r", "plm r", "plm-r",
                 "emg ra", "ta r", "ta re"],
    "eeg":      ["eeg", "c3", "c4", "f3", "f4", "o1", "o2"],
}

POSITION_MAP: dict[int, str] = {
    0: "Prone", 1: "Left", 2: "Supine", 3: "Right", 4: "Upright",
}
