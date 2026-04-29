"""
psgscoring.profiles
====================

Scoring profile definitions for psgscoring v0.4.0.

This module provides a unified framework for running PSG respiratory
event scoring under multiple historical and dataset-specific rule sets.

Profile families:
    - clinical : AASM-compliant profiles (v1/v2/v3 + CMS + exploratory)
    - dataset  : Faithful reproduction of NSRR scoring conventions
    - legacy   : Pre-AASM Chicago criteria

Usage:
    >>> from psgscoring.profiles import get_profile, list_profiles
    >>> profile = get_profile("aasm_v3_rec")
    >>> profile.hypopnea.flow_reduction_threshold
    0.30

    >>> list_profiles()
    ['aasm_v3_rec', 'aasm_v3_strict', 'aasm_v3_sensitive',
     'aasm_v2_rec', 'aasm_v1_rec', 'cms_medicare',
     'mesa_shhs', 'chicago_1999']

References:
    Iber et al. 2007 (v1) - AASM Manual 1st edition
    Berry et al. 2012 (v2.0) - Sleep Apnea Definitions Task Force update
    Berry et al. 2020 (v2.6) - Last v2 edition
    Troester et al. 2023 (v3) - Current mandated standard
    MESA Scoring Manual (Brigham Reading Center) - NSRR convention
    AASM Task Force 1999 - Chicago criteria (pre-AASM)

License: BSD-3-Clause
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

__all__ = [
    "HypopneaRules",
    "ApneaRules",
    "SpO2Rules",
    "PostProcessingRules",
    "Profile",
    "get_profile",
    "list_profiles",
    "list_profile_groups",
    "resolve_profile_name",
    "PROFILES",
    "PROFILE_GROUPS",
    "LEGACY_ALIASES",
]


# ============================================================
# Data classes
# ============================================================

@dataclass
class HypopneaRules:
    """Hypopnea detection parameters."""

    flow_reduction_threshold: float
    """Minimum flow amplitude reduction (0.30 = 30% drop)."""

    sensor: str
    """Primary sensor for flow reduction measurement.
    Values: 'nasal_pressure', 'rip_bands_primary', 'nasal_pressure_or_flow'
    """

    min_duration_s: float = 10.0
    max_duration_s: float = 60.0

    desat_threshold: Optional[float] = None
    """SpO2 desaturation threshold (0.03 = 3%). None = no desat coupling."""

    desat_required: bool = True
    """If True, desat is mandatory for event qualification."""

    arousal_required: bool = False
    """If True, arousal is mandatory for event qualification."""

    desat_or_arousal: bool = False
    """If True, desat OR arousal is sufficient (AASM Rule 1A behaviour)."""

    nasal_pressure_fallback: bool = False
    """For dataset profiles: fall back to nasal pressure if RIP unreliable."""

    square_root_linearisation: bool = True
    """Apply Bernoulli correction to nasal pressure (standard practice)."""

    output_variants: List[str] = field(default_factory=list)
    """For dataset profiles: emit multiple AHI variants per detection pass."""


@dataclass
class ApneaRules:
    """Apnea detection parameters."""

    flow_reduction_threshold: float = 0.90
    sensor: str = "thermistor"
    min_duration_s: float = 10.0
    max_duration_s: float = 90.0


@dataclass
class SpO2Rules:
    """SpO2 coupling and baseline parameters."""

    baseline_window_s: float = 120.0
    nadir_search_s: float = 45.0
    global_p95_fallback: bool = True


@dataclass
class PostProcessingRules:
    """Post-processing and bias-correction parameters."""

    stability_filter_enabled: bool = True
    stability_filter_cv: float = 0.45
    """Coefficient of variation threshold for rejecting normal variability."""

    csr_reclassification: bool = True
    """Reclassify events as central based on Cheyne-Stokes periodicity."""

    local_baseline_validation: bool = True
    """Reject candidates driven solely by inflated rolling baseline."""

    flow_smoothing_s: float = 0.0
    """Flow envelope smoothing window (0 = off, default since v0.2.8).
    Was 3.0 prior to v0.2.8; removed because it caused +54 false hypopneas
    in PSG-IPA SN1 (severity drift Mild → Moderate)."""

    breath_level_detection: bool = True
    """Enable peak-based breath-level hypopnea detection."""

    peak_min_consecutive_breaths: int = 3
    """Minimum consecutive low-amplitude breaths for peak-based detection.
    Lowered to 2 in sensitive profile for UARS sensitivity."""

    artefact_flank_exclusion: bool = True

    mixed_apnea_decomposition: bool = True
    """Split mixed apneas into central + obstructive components."""

    unsure_as_hypopnea: bool = False
    """NSRR-specific: 'Unsure' tag = hypopnea with >50% reduction."""

    local_baseline_cv_threshold: float = 0.30
    """v0.4.2: CV threshold below which local-baseline reduction is enforced strictly.

    The local baseline validation (`_validate_local_reduction` in respiratory.py)
    applies a stricter flow-reduction requirement when surrounding breathing is
    stable (low CV). At CV < this threshold, the stricter reduction kicks in.

    Default 0.30 matches the legacy hardcoded behaviour. Lower values (e.g. 0.20)
    relax the strictness — useful for sensitive profiles where borderline events
    should not be rejected.
    """

    local_baseline_strict_reduction: float = 25.0
    """v0.4.2: Flow-reduction percentage required when local CV < threshold.

    When breathing is stable (CV < local_baseline_cv_threshold), candidate events
    must show this percentage of flow reduction (vs the default 20%) to be
    accepted as hypopneas.

    - Strict profile: 30.0 (extra strict — reject more borderline events)
    - Standard:       25.0 (moderate)
    - Sensitive:      20.0 (no extra strictness — accept borderline events)
    """


@dataclass
class Profile:
    """Complete scoring profile specification."""

    name: str
    display_name: str
    family: str  # "clinical" | "dataset" | "legacy" | "exploratory"
    aasm_version: str
    aasm_rule: str
    description: str

    hypopnea: HypopneaRules
    apnea: ApneaRules = field(default_factory=ApneaRules)
    spo2: SpO2Rules = field(default_factory=SpO2Rules)
    post_processing: PostProcessingRules = field(default_factory=PostProcessingRules)

    citation: str = ""
    """Primary reference citation for this profile."""

    deprecated: bool = False
    deprecated_alias_for: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile to dict for audit metadata."""
        return asdict(self)

    def summary(self) -> str:
        """Human-readable one-line summary."""
        h = self.hypopnea
        rule = []
        rule.append(f"≥{int(h.flow_reduction_threshold * 100)}%")
        if h.desat_threshold:
            rule.append(f"≥{int(h.desat_threshold * 100)}%")
        if h.desat_or_arousal:
            rule.append("OR arousal")
        elif h.desat_required and h.desat_threshold:
            rule.append(f"desat ≥{int(h.desat_threshold * 100)}%")
        return f"{self.display_name} [{' '.join(rule)}]"


# ============================================================
# Profile definitions
# ============================================================

# ---- AASM v3 RECOMMENDED (Rule 1A) ----
# This is THE DEFAULT for all clinical use in AASM-accredited labs
# since Dec 31, 2023. All shared post-processing comes from here.
_aasm_v3_rec = Profile(
    name="aasm_v3_rec",
    display_name="AASM v3 — Recommended (3%-or-arousal)",
    family="clinical",
    aasm_version="v3 (2023)",
    aasm_rule="1A (RECOMMENDED)",
    description=(
        "Current clinical standard per AASM Scoring Manual v3 (Troester "
        "2023). Mandatory for AASM-accredited facilities since Dec 31, "
        "2023. Hypopneas require ≥30% nasal pressure reduction for "
        "≥10 seconds associated with EITHER a ≥3% oxygen desaturation "
        "OR an arousal."
    ),
    citation="Troester MM, Quan SF, Berry RB, et al. AASM Manual v3. 2023.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.30,
        sensor="nasal_pressure",
        min_duration_s=10.0,
        max_duration_s=60.0,
        desat_threshold=0.03,
        desat_required=False,
        arousal_required=False,
        desat_or_arousal=True,
        square_root_linearisation=True,
    ),
)

# ---- AASM v2 RECOMMENDED (2012-2020) ----
# Functionally identical to v3 Rule 1A. Kept for explicit labeling
# of analyses performed during the v2 era.
_aasm_v2_rec = Profile(
    name="aasm_v2_rec",
    display_name="AASM v2 — Recommended (3%-or-arousal, legacy)",
    family="clinical",
    aasm_version="v2.0–v2.6 (2012–2020)",
    aasm_rule="1A (RECOMMENDED)",
    description=(
        "AASM Manual v2 Rule 1A, introduced by the Sleep Apnea Definitions "
        "Task Force (Berry 2012) and retained through v2.6 (Berry 2020). "
        "Functionally identical to v3 Rule 1A. This profile exists for "
        "explicit labeling of analyses performed under the v2 era; for "
        "current clinical use, prefer aasm_v3_rec."
    ),
    citation="Berry RB, et al. JCSM 2012;8:597-619; Berry RB, et al. AASM v2.6. 2020.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.30,
        sensor="nasal_pressure",
        min_duration_s=10.0,
        max_duration_s=60.0,
        desat_threshold=0.03,
        desat_required=False,
        arousal_required=False,
        desat_or_arousal=True,
        square_root_linearisation=True,
    ),
)

# ---- AASM v1 RECOMMENDED (2007) ----
# Historical 2007 rule. Note: 4% desaturation, NO arousal alternative.
_aasm_v1_rec = Profile(
    name="aasm_v1_rec",
    display_name="AASM v1 (2007) — Historical (4% desat, no arousal)",
    family="clinical",
    aasm_version="v1 (2007)",
    aasm_rule="Original Recommended",
    description=(
        "AASM Manual v1 original recommended rule (Iber 2007). Requires "
        "≥30% flow reduction with ≥4% oxygen desaturation; does NOT allow "
        "arousal as alternative qualifier. Use for re-analysis of pre-2012 "
        "research cohorts. Typically yields lower AHI than v2/v3 rules."
    ),
    citation="Iber C, Ancoli-Israel S, Chesson AL, Quan SF. AASM Manual v1. 2007.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.30,
        sensor="nasal_pressure",
        min_duration_s=10.0,
        max_duration_s=60.0,
        desat_threshold=0.04,
        desat_required=True,
        arousal_required=False,
        desat_or_arousal=False,
        square_root_linearisation=True,
    ),
)

# ---- CMS / Medicare (AASM v3 1B OPTIONAL) ----
# US insurance reimbursement criterion. Degraded from "acceptable" to
# "optional" in v3 (2023) but still widely used for coverage.
_cms_medicare = Profile(
    name="cms_medicare",
    display_name="CMS / Medicare (4% desat, no arousal)",
    family="clinical",
    aasm_version="v3 Rule 1B (OPTIONAL) / CMS",
    aasm_rule="1B (OPTIONAL)",
    description=(
        "CMS (Centers for Medicare & Medicaid Services) hypopnea criterion, "
        "corresponding to AASM Rule 1B. Requires ≥30% flow reduction with "
        "≥4% oxygen desaturation; arousals are not accepted as qualifier. "
        "Downgraded from 'acceptable' (v2) to 'optional' (v3) by AASM in "
        "2023 but retained for CMS reimbursement in the United States. "
        "Typically yields ~30% lower AHI than the v3 recommended rule."
    ),
    citation="CMS National Coverage Determination 240.4; Troester 2023 Rule 1B.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.30,
        sensor="nasal_pressure",
        min_duration_s=10.0,
        max_duration_s=60.0,
        desat_threshold=0.04,
        desat_required=True,
        arousal_required=False,
        desat_or_arousal=False,
        square_root_linearisation=True,
    ),
)

# ---- MESA / NSRR convention ----
# Faithful reproduction of scoring as documented in the MESA scoring
# manual (Brigham Reading Center). Key differences from AASM:
#   1. Hypopneas use thoracoabdominal band amplitude as primary sensor
#   2. Events are marked independent of desaturation; multiple AHI
#      variants (3%, 3%+arousal, 4%) are generated post-hoc
#   3. "Unsure" tag = hypopnea with >50% reduction (not uncertainty)
_mesa_shhs = Profile(
    name="mesa_shhs",
    display_name="MESA / NSRR (band-based, multi-variant AHI)",
    family="dataset",
    aasm_version="NSRR convention (R&K staging era)",
    aasm_rule="mesa_shhs",
    description=(
        "Reproduction of scoring as documented in the MESA Sleep "
        "Polysomnography Scoring Manual (Brigham Reading Center). "
        "Hypopneas are identified from thoracoabdominal band amplitude "
        "reductions of ≥30%, independent of desaturation. Multiple AHI "
        "variants (AHI_3pct, AHI_3pct_arousal, AHI_4pct) are emitted "
        "post-hoc. The 'Unsure' tag in MESA XML denotes a hypopnea with "
        ">50% reduction, NOT uncertainty. Use for reproduction of "
        "NSRR-dataset analyses (MESA, SHHS, CFS, CHAT)."
    ),
    citation="MESA Sleep PSG Scoring Manual, NSRR / Brigham Reading Center.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.30,
        sensor="rip_bands_primary",
        min_duration_s=10.0,
        max_duration_s=60.0,
        desat_threshold=None,
        desat_required=False,
        arousal_required=False,
        desat_or_arousal=False,
        nasal_pressure_fallback=True,
        square_root_linearisation=True,
        output_variants=["ahi_3pct", "ahi_3pct_arousal", "ahi_4pct"],
    ),
    post_processing=PostProcessingRules(
        stability_filter_enabled=True,
        stability_filter_cv=0.45,
        csr_reclassification=True,
        local_baseline_validation=True,
        flow_smoothing_s=0.0,
        breath_level_detection=True,
        artefact_flank_exclusion=True,
        mixed_apnea_decomposition=True,
        unsure_as_hypopnea=True,  # ← NSRR-specific,
        local_baseline_cv_threshold=0.3,
        local_baseline_strict_reduction=25.0,
    ),
)

# ---- Chicago Criteria (1999, pre-AASM) ----
# Legacy criterion used in early epidemiological cohorts.
_chicago_1999 = Profile(
    name="chicago_1999",
    display_name="Chicago Criteria (1999, pre-AASM)",
    family="legacy",
    aasm_version="Chicago 1999 (pre-AASM)",
    aasm_rule="chicago",
    description=(
        "AASM Task Force 1999 'Chicago Criteria' for respiratory event "
        "scoring. Requires ≥50% flow reduction (stricter than modern "
        "AASM ≥30%), with ≥3% desaturation OR arousal. Used in the "
        "Wisconsin Sleep Cohort Study (WSCS) and other pre-2007 research "
        "cohorts. Use for historical re-analysis and cross-era cohort "
        "comparison."
    ),
    citation="AASM Task Force. Sleep 1999;22:667-689.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.50,
        sensor="nasal_pressure_or_flow",
        min_duration_s=10.0,
        max_duration_s=60.0,
        desat_threshold=0.03,
        desat_required=False,
        arousal_required=False,
        desat_or_arousal=True,
        square_root_linearisation=True,
    ),
)

# ---- AASM v3 STRICT (exploratory) ----
# Conservative variant of v3_rec. Rejects borderline candidates.
_aasm_v3_strict = Profile(
    name="aasm_v3_strict",
    display_name="AASM v3 — Strict (conservative)",
    family="exploratory",
    aasm_version="v3 (2023), conservative variant",
    aasm_rule="1A strict",
    description=(
        "Conservative variant of AASM v3 Rule 1A. Retains the 3%-or-arousal "
        "qualifier but disables flow smoothing, breath-level detection, "
        "and uses a stricter stability filter (CV 0.30 instead of 0.45). "
        "Use for robustness-grade framework lower bound or for evaluators "
        "with a conservative manual scoring style."
    ),
    citation="Rombaut et al. 2026 (paper v31), §2.1.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.30,
        sensor="nasal_pressure",
        min_duration_s=10.0,
        max_duration_s=60.0,
        desat_threshold=0.03,
        desat_required=False,
        arousal_required=False,
        desat_or_arousal=True,
        square_root_linearisation=True,
    ),
    spo2=SpO2Rules(
        baseline_window_s=120.0,
        nadir_search_s=30.0,  # ← strict: conservative window (v0.3.2 behaviour)
        global_p95_fallback=True,
    ),
    post_processing=PostProcessingRules(
        stability_filter_enabled=True,
        stability_filter_cv=0.30,
        csr_reclassification=True,
        local_baseline_validation=True,
        flow_smoothing_s=0.0,
        breath_level_detection=False,
        artefact_flank_exclusion=True,
        mixed_apnea_decomposition=True,
        local_baseline_cv_threshold=0.3,
        local_baseline_strict_reduction=30.0,
    ),
)

# ---- AASM v3 SENSITIVE (exploratory, UARS) ----
# Permissive variant for UARS/borderline patients.
_aasm_v3_sensitive = Profile(
    name="aasm_v3_sensitive",
    display_name="AASM v3 — Sensitive (UARS)",
    family="exploratory",
    aasm_version="v3 (2023), sensitive variant",
    aasm_rule="1A sensitive",
    description=(
        "Sensitive variant of AASM v3 Rule 1A. Lowers the flow reduction "
        "threshold from 30% to 25%, extends flow smoothing to 5 s, "
        "and enables breath-level peak-based detection. Intended for "
        "use alongside aasm_v3_rec in symptomatic patients with "
        "borderline AHI where upper airway resistance syndrome (UARS) "
        "is suspected. Not for primary clinical scoring."
    ),
    citation="Rombaut et al. 2026 (paper v31), §2.1.",
    hypopnea=HypopneaRules(
        flow_reduction_threshold=0.25,  # ← key difference
        sensor="nasal_pressure",
        min_duration_s=10.0,
        max_duration_s=90.0,  # v0.2.8: extended for UARS
        desat_threshold=0.03,
        desat_required=False,
        arousal_required=False,
        desat_or_arousal=True,
        square_root_linearisation=True,
    ),
    apnea=ApneaRules(
        flow_reduction_threshold=0.90,
        sensor="thermistor",
        min_duration_s=10.0,
        max_duration_s=120.0,  # v0.2.8: extended for UARS
    ),
    post_processing=PostProcessingRules(
        stability_filter_enabled=True,
        stability_filter_cv=0.50,
        csr_reclassification=True,
        local_baseline_validation=True,
        flow_smoothing_s=5.0,
        breath_level_detection=True,
        peak_min_consecutive_breaths=2,  # ← v0.2.8: lower for UARS
        artefact_flank_exclusion=False,  # ← v0.3.2: CROSS_CONTAM_WINDOW_S = 0.0
        mixed_apnea_decomposition=True,
        local_baseline_cv_threshold=0.2,
        local_baseline_strict_reduction=20.0,
    ),
)


# ============================================================
# Registry
# ============================================================

PROFILES: Dict[str, Profile] = {
    # Clinical family
    "aasm_v3_rec":       _aasm_v3_rec,
    "aasm_v3_strict":    _aasm_v3_strict,
    "aasm_v3_sensitive": _aasm_v3_sensitive,
    "aasm_v2_rec":       _aasm_v2_rec,
    "aasm_v1_rec":       _aasm_v1_rec,
    "cms_medicare":      _cms_medicare,

    # Dataset family
    "mesa_shhs":         _mesa_shhs,

    # Legacy family
    "chicago_1999":      _chicago_1999,
}

# ---- Profile groups (for confidence-interval / robustness-grade output) ----
PROFILE_GROUPS: Dict[str, List[str]] = {
    # Clinical robustness-grade: current paper v31 behaviour
    "clinical": ["aasm_v3_strict", "aasm_v3_rec", "aasm_v3_sensitive"],

    # Historical era comparison
    "aasm_era": ["aasm_v1_rec", "aasm_v2_rec", "aasm_v3_rec"],

    # Insurance / coverage awareness (US)
    "coverage": ["aasm_v3_rec", "cms_medicare"],

    # Dataset reproduction check (e.g., compare our v3_rec to NSRR-conv)
    "dataset":  ["aasm_v3_rec", "mesa_shhs"],

    # Maximum coverage: all 6 "standard" profiles
    "full_6":   ["aasm_v3_rec", "aasm_v2_rec", "aasm_v1_rec",
                 "cms_medicare", "mesa_shhs", "chicago_1999"],

    # Everything (research-grade sensitivity analysis)
    "all":      list(PROFILES.keys()),
}

# ---- Legacy name mapping (v0.3.x → v0.4.0) ----
LEGACY_ALIASES: Dict[str, str] = {
    "strict":    "aasm_v3_strict",
    "standard":  "aasm_v3_rec",
    "sensitive": "aasm_v3_sensitive",
}


# ============================================================
# Public API
# ============================================================

def get_profile(name: str) -> Profile:
    """
    Retrieve a scoring profile by name.

    Accepts legacy names (strict/standard/sensitive) with deprecation
    warning.

    Parameters
    ----------
    name : str
        Profile name. See list_profiles() for available options.

    Returns
    -------
    Profile
        Complete profile specification.

    Raises
    ------
    KeyError
        If the profile name is not recognised.

    Examples
    --------
    >>> profile = get_profile("aasm_v3_rec")
    >>> profile.hypopnea.flow_reduction_threshold
    0.3
    >>> profile = get_profile("standard")  # legacy alias → v3_rec
    >>> profile.name
    'aasm_v3_rec'
    """
    resolved = resolve_profile_name(name)
    if resolved not in PROFILES:
        raise KeyError(
            f"Unknown profile '{name}'. "
            f"Available: {', '.join(sorted(PROFILES.keys()))}"
        )
    return PROFILES[resolved]


def resolve_profile_name(name: str) -> str:
    """
    Resolve a profile name, handling legacy aliases.

    Emits a DeprecationWarning if a legacy name is used.
    """
    if name in LEGACY_ALIASES:
        new_name = LEGACY_ALIASES[name]
        warnings.warn(
            f"Profile name '{name}' is deprecated in psgscoring v0.4.0 "
            f"and will be removed in v0.5.0. Use '{new_name}' instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return new_name
    return name


def list_profiles(family: Optional[str] = None) -> List[str]:
    """
    List available profile names.

    Parameters
    ----------
    family : str, optional
        Filter by family: 'clinical', 'dataset', 'legacy', 'exploratory'.
        If None, return all profiles.

    Returns
    -------
    list of str
        Profile names, sorted.
    """
    if family is None:
        return sorted(PROFILES.keys())
    return sorted(
        name for name, p in PROFILES.items() if p.family == family
    )


def list_profile_groups() -> Dict[str, List[str]]:
    """Return all predefined profile groups."""
    return {k: list(v) for k, v in PROFILE_GROUPS.items()}


def profile_metadata(name: str) -> Dict[str, Any]:
    """
    Return audit-ready metadata dict for a profile.

    Used by pipeline.py to attach profile information to every analysis
    output for full traceability.
    """
    p = get_profile(name)
    return {
        "profile_name":       p.name,
        "profile_display":    p.display_name,
        "profile_family":     p.family,
        "aasm_version":       p.aasm_version,
        "aasm_rule":          p.aasm_rule,
        "flow_threshold_pct": int(p.hypopnea.flow_reduction_threshold * 100),
        "desat_threshold_pct": (
            int(p.hypopnea.desat_threshold * 100)
            if p.hypopnea.desat_threshold else None
        ),
        "desat_or_arousal":   p.hypopnea.desat_or_arousal,
        "citation":           p.citation,
    }
