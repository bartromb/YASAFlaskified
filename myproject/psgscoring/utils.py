"""
psgscoring.utils
================
Pure-Python helpers used across all other submodules.

Dependencies: numpy, psgscoring.constants
No imports from other psgscoring modules.
"""

from __future__ import annotations
import numpy as np
from .constants import CHANNEL_PATTERNS, EPOCH_LEN_S


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------

def safe_r(val, dec: int = 1):
    """Round *val* to *dec* decimal places; return None for None/NaN."""
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return round(float(val), dec)
    except Exception:
        return None


def fmt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS string."""
    if seconds is None:
        return "--:--:--"
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


# ---------------------------------------------------------------------------
# Hypnogram helpers
# ---------------------------------------------------------------------------

_HYPNO_MAP = {"W": 0, "N1": 1, "N2": 2, "N3": 3, "R": 4}


def hypno_to_numeric(hypno: list) -> np.ndarray:
    """Convert string hypnogram ['W','N1',...] to numeric array (W=0..R=4)."""
    return np.array([_HYPNO_MAP.get(s, -1) for s in hypno])


def is_nrem(stage) -> bool:
    """Controleer of een slaapstadium NREM is (N1, N2 of N3)."""
    return stage in (1, 2, 3, "N1", "N2", "N3")


def is_rem(stage) -> bool:
    """Controleer of een slaapstadium REM is."""
    return stage in (4, "R")


def is_sleep(stage) -> bool:
    """Controleer of een slaapstadium slaap is (niet Wake)."""
    return stage not in (0, -1, "W")


# ---------------------------------------------------------------------------
# Sleep / artifact mask
# ---------------------------------------------------------------------------

def build_sleep_mask(
    hypno: list,
    sf: float,
    total_samples: int,
    artifact_epochs: list | None = None,
) -> np.ndarray:
    """
    Build a sample-level boolean mask: True = valid sleep.

    Excludes Wake (stage 0) and artifact epochs supplied by YASA's artifact
    detector.

    Parameters
    ----------
    hypno           : string hypnogram list
    sf              : sample rate of the target signal
    total_samples   : length of the target signal
    artifact_epochs : list of epoch indices containing artefacts
    """
    hypno_num   = hypno_to_numeric(hypno)
    artifact_set = set(artifact_epochs or [])
    spe  = int(sf * EPOCH_LEN_S)
    mask = np.zeros(total_samples, dtype=bool)
    for ep_i, stage in enumerate(hypno_num):
        s = ep_i * spe
        e = min(s + spe, total_samples)
        if stage > 0 and ep_i not in artifact_set:
            mask[s:e] = True
    return mask


# ---------------------------------------------------------------------------
# Channel detection
# ---------------------------------------------------------------------------

def detect_channels(ch_names: list[str]) -> dict[str, str]:
    """
    Pattern-match EDF channel names to functional roles.

    Returns a dict mapping role -> original channel name for the first match
    found per role.  Matching is case-insensitive substring search.
    """
    ch_lower = {ch.lower(): ch for ch in ch_names}
    found: dict[str, str] = {}
    for ch_type, patterns in CHANNEL_PATTERNS.items():
        for pat in patterns:
            match = next(
                (orig for lc, orig in ch_lower.items() if pat in lc), None
            )
            if match:
                found[ch_type] = match
                break
    return found


def channel_map_from_user(
    user_map: dict | None,
    ch_names: list[str],
) -> dict[str, str]:
    """
    Merge auto-detected channel map with optional manual overrides.

    Manual overrides take precedence; invalid channel names are ignored.
    """
    auto   = detect_channels(ch_names)
    merged = {**auto}
    for k, v in (user_map or {}).items():
        if v and v in ch_names:
            merged[k] = v
    return merged
