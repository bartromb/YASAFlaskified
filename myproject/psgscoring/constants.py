"""
psgscoring.constants
====================
AASM 2.6 thresholds, channel-name patterns, and other shared constants.

Nothing in this module imports from other psgscoring submodules, so it is safe
to import from any layer of the package.
"""

# ---------------------------------------------------------------------------
# AASM 2.6 respiratory scoring thresholds
# ---------------------------------------------------------------------------
APNEA_THRESHOLD        = 0.10   # flow < 10% of baseline -> apnea
HYPOPNEA_THRESHOLD     = 0.70   # flow < 70% of baseline -> hypopnea candidate
HYPOPNEA_SMOOTH_S      = 3.0    # v0.8.12: smooth flow before thresholding (seconds)
                                 # Mimics human visual averaging; reduces false negatives
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
# Scoring profiles: strict → standard → sensitive
# ---------------------------------------------------------------------------
SCORING_PROFILES: dict[str, dict] = {
    "strict": {
        "label":                "Strict (machine)",
        "HYPOPNEA_THRESHOLD":   0.70,   # ≥30% reduction (AASM exact)
        "DESATURATION_DROP_PCT": 3.0,
        "POST_EVENT_WINDOW_S":  30,     # conservative window
        "HYPOPNEA_SMOOTH_S":    0.0,    # no smoothing
        "CROSS_CONTAM_WINDOW_S": 15.0,
        "USE_PEAK_DETECTION":   False,  # envelope only
        "HYPOPNEA_MAX_DUR_S":   60.0,   # v0.8.22
        "APNEA_MAX_DUR_S":      90.0,   # v0.8.22
    },
    "standard": {
        "label":                "Standard (AASM 2.6)",
        "HYPOPNEA_THRESHOLD":   0.70,
        "DESATURATION_DROP_PCT": 3.0,
        "POST_EVENT_WINDOW_S":  45,
        "HYPOPNEA_SMOOTH_S":    3.0,
        "CROSS_CONTAM_WINDOW_S": 15.0,
        "USE_PEAK_DETECTION":   True,   # peak + envelope
        "HYPOPNEA_MAX_DUR_S":   60.0,   # v0.8.22
        "APNEA_MAX_DUR_S":      90.0,   # v0.8.22
    },
    "sensitive": {
        "label":                "Sensitive (RPSGT-like)",
        "HYPOPNEA_THRESHOLD":   0.75,   # ≥25% reduction
        "DESATURATION_DROP_PCT": 3.0,
        "POST_EVENT_WINDOW_S":  45,
        "HYPOPNEA_SMOOTH_S":    5.0,    # more smoothing
        "CROSS_CONTAM_WINDOW_S": 0.0,   # no cross-contam check
        "USE_PEAK_DETECTION":   True,
        "HYPOPNEA_MAX_DUR_S":   90.0,   # v0.8.22: meer tolerant
        "APNEA_MAX_DUR_S":      120.0,  # v0.8.22
    },
}

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
