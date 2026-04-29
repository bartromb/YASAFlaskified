"""
psgscoring.types
================
TypedDict definitions for the main output structures.

These are for documentation and type-checking only (no runtime overhead).
Use with mypy or IDE type hints:

    from psgscoring.types import RespiratoryEvent, ScoringSummary

    def process(event: RespiratoryEvent) -> None:
        print(event["onset_s"])  # IDE autocomplete + type check
"""

from __future__ import annotations
from typing import TypedDict, Optional, List, Dict


class ClassifyDetail(TypedDict, total=False):
    """Detail dict from apnea type classification (classify.py)."""
    rule_index: int
    decision_reason: str
    effort_ratio: float
    raw_var_ratio: float
    paradox_correlation: float
    phase_angle_deg: float
    first_ratio: float
    second_ratio: float
    quarter_efforts: List[float]
    flattening_index: Optional[float]
    ecg_effort_present: Optional[bool]
    spectral_cardiac_pct: Optional[float]
    spectral_respiratory_pct: Optional[float]
    tecg_bursts_detected: Optional[bool]
    reclassify_as_central: Optional[bool]


class RespiratoryEvent(TypedDict, total=False):
    """A single scored respiratory event (apnea or hypopnea).

    Returned in results["respiratory"]["events"].
    """
    type: str                    # "obstructive", "central", "mixed", "hypopnea"
    onset_s: float               # seconds from recording start
    duration_s: float            # event duration in seconds
    stage: str                   # sleep stage at onset: "W","N1","N2","N3","R"
    desaturation_pct: Optional[float]  # SpO2 drop (Rule 1A), None if no desat
    min_spo2: Optional[float]    # SpO2 nadir during post-event window
    flow_nadir: float            # minimum normalised flow during event
    flow_reduction: Optional[float]     # flow reduction ratio (hypopneas)
    flow_reduction_pct: Optional[float] # flow reduction as percentage
    pre_baseline: float          # baseline amplitude at event onset
    confidence: float            # classification confidence 0.0–1.0
    classify_detail: ClassifyDetail
    epoch: int                   # 30-s epoch index at onset
    spo2_cross_contaminated: bool  # Fix 2: SpO2 possibly from prior event
    csr_flagged: bool            # Fix 3: part of Cheyne-Stokes cycle
    local_baseline_rejected: bool  # Fix 6: rejected by local validation
    _label: str                  # internal: selection reason for PDF examples


class OAHIThresholds(TypedDict):
    """OAHI at different confidence thresholds (Fix 4, legacy 4-point sweep)."""
    high: float      # ≥0.85
    moderate: float   # ≥0.60
    borderline: float # ≥0.40
    all: float        # all events (official)


class OAHISweep3pt(TypedDict):
    """v0.4.1: Clinically calibrated 3-point OAHI confidence sweep.

    Calibrated on PSG-IPA validation:
      - lenient (c≥0.30): mean OAHI 8.7/h
      - primary (c≥0.47): empirical best-fit (matches scorer mediaan)
      - strict  (c≥0.65): mean OAHI 4.7/h
    Mean sweep width on PSG-IPA: 3.9/h (matches AASM inter-scorer
    variability ~10-20%). Replaces the previous 4-point sweep
    (oahi_thresholds) which produced ~9.3/h widths considered
    too wide for clinical interpretation.
    """
    lenient: float    # c ≥ 0.30 — inclusief
    primary: float    # c ≥ 0.47 — best-fit
    strict:  float    # c ≥ 0.65 — conservatief


class ConfidenceBands(TypedDict):
    """Event counts per confidence tier."""
    high: int        # ≥0.85
    moderate: int    # 0.60–0.84
    borderline: int  # 0.40–0.59
    low: int         # <0.40


class ScoringSummary(TypedDict, total=False):
    """Summary statistics from respiratory scoring.

    Returned in results["respiratory"]["summary"].
    """
    # ── Primary indices ──
    n_ah_total: int
    ahi_total: float
    oahi: float
    oahi_all: float               # alias for backward compat
    oahi_thresholds: OAHIThresholds  # legacy 4-point sweep (deprecated)
    severity: str                 # "normal", "mild", "moderate", "severe"
    oahi_severity: str

    # ── v0.4.1: 3-point clinical sweep + robustness grade ──
    oahi_sweep: OAHISweep3pt      # clinically calibrated 3-point sweep
    oahi_sweep_width: float       # max - min, in /h
    robustness_grade: str         # "A" (robust), "B" (probable), "C" (uncertain)

    # ── Per-type indices ──
    obstructive_index: float
    central_index: float
    mixed_index: float
    hypopnea_index: float

    # ── Stage-specific ──
    ahi_rem: float
    ahi_nrem: float
    obstructive_rem: int
    obstructive_nrem: int
    central_rem: int
    central_nrem: int
    mixed_rem: int
    mixed_nrem: int
    hypopnea_rem: int
    hypopnea_nrem: int

    # ── Duration stats ──
    max_apnea_dur_s: float
    avg_apnea_dur_s: float
    max_hypopnea_dur_s: float
    avg_hypopnea_dur_s: float

    # ── Quality metrics ──
    avg_desaturation: float
    avg_classification_confidence: float
    n_low_confidence: int
    confidence_bands: ConfidenceBands

    # ── Sleep time ──
    tst_hours: float
    tst_minutes: float
    n_artifact_epochs_excluded: int

    # ── Correction counters (Table 4 in paper) ──
    n_csr_flagged: int
    ahi_csr_corrected: float
    n_spo2_cross_contaminated: int
    n_local_baseline_rejected: int
    n_gap_excluded: int
    n_low_conf_borderline: int
    n_low_conf_noise: int
    ahi_excl_noise: float


class SpO2Summary(TypedDict, total=False):
    """SpO2 analysis summary.

    Returned in results["spo2"]["summary"].
    """
    mean_spo2: float
    baseline_spo2: float          # 90th percentile
    min_spo2: float
    time_below_90_pct: float      # % of TST
    odi_3pct: float               # desaturations ≥3% per hour
    odi_4pct: float
    spo2_low_samplerate: bool     # warning: >3s averaging


class PLMSummary(TypedDict, total=False):
    """PLM analysis summary.

    Returned in results["plm"]["summary"].
    """
    n_lm_total: int
    n_lm_sleep: int
    n_respiratory_associated: int
    n_plm_series: int
    n_plm: int                    # PLMs in series
    plmi: float                   # PLM index (/h sleep)


class PositionSummary(TypedDict, total=False):
    """Position analysis summary."""
    pct_supine: float
    pct_left: float
    pct_right: float
    pct_prone: float
    pct_upright: float
    ahi_supine: float
    ahi_left: float
    ahi_right: float
    ahi_prone: float
    ahi_upright: float


class PneumoResults(TypedDict, total=False):
    """Top-level results from run_pneumo_analysis().

    Usage:
        results = run_pneumo_analysis(raw, hypno, channel_map)
        ahi = results["respiratory"]["summary"]["ahi_total"]
    """
    respiratory: Dict               # {"events": List[RespiratoryEvent], "summary": ScoringSummary}
    spo2: Dict                      # {"summary": SpO2Summary, ...}
    plm: Dict                       # {"summary": PLMSummary, ...}
    position: Dict                  # {"summary": PositionSummary, ...}
    snore: Dict
    heart_rate: Dict
    signal_quality: Dict
    arousals: Dict
