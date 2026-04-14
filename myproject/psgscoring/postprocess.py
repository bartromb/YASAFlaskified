"""
psgscoring.postprocess
======================
Post-processing module for refining respiratory event classification.

Implements:
1. CSR-aware central reclassification — events in CSR troughs are
   reclassified as central regardless of effort signal artifacts.
2. Mixed apnea decomposition — mixed events with central portion ≥10 s
   are reclassified as central.
3. Central instability index — quantifies profile-dependent uncertainty
   in obstructive vs. central classification.

Added in v0.3.0.

References
----------
Berry RB et al. AASM Manual v2.6, 2020.
Azarbarzin A et al. AJRCCM 2019;200(2):211-219.
"""

from __future__ import annotations

import logging
import numpy as np
from .utils import safe_r

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. CSR-aware central reclassification
# ---------------------------------------------------------------------------

def reclassify_csr_events(
    events: list,
    csr_info: dict,
) -> list:
    """
    Reclassify CSR-flagged events as central.

    When Cheyne-Stokes respiration is detected, events in the trough of
    the crescendo-decrescendo cycle are physiologically central — even if
    the effort signal shows apparent paradoxical breathing (often cardiac
    pulsation artifact in heart failure patients).

    Events with ``csr_flagged=True`` that are currently classified as
    ``"obstructive"`` or ``"mixed"`` are reclassified as ``"central"``
    with the original type preserved in ``original_type``.

    Parameters
    ----------
    events : list[dict]
        Respiratory events (already CSR-flagged by _flag_csr_events).
    csr_info : dict
        CSR detection result from detect_cheyne_stokes().

    Returns
    -------
    list[dict] — modified events with reclassifications applied.
    """
    if not csr_info or not csr_info.get("csr_detected"):
        return events

    n_reclassified = 0
    modified = []

    for ev in events:
        ev = dict(ev)
        if ev.get("csr_flagged") and ev.get("type") in ("obstructive", "mixed"):
            ev["original_type"] = ev["type"]
            ev["type"] = "central"
            ev["csr_reclassified"] = True
            # Adjust confidence — CSR context provides good evidence
            ev["confidence"] = max(ev.get("confidence", 0.5), 0.80)
            ev["classify_detail"] = ev.get("classify_detail", {})
            if isinstance(ev["classify_detail"], dict):
                ev["classify_detail"]["csr_reclassified"] = True
            n_reclassified += 1
        modified.append(ev)

    if n_reclassified > 0:
        logger.info(
            "CSR reclassification: %d events reclassified as central", n_reclassified
        )

    return modified


# ---------------------------------------------------------------------------
# 2. Mixed apnea decomposition
# ---------------------------------------------------------------------------

def decompose_mixed_apneas(
    events: list,
    thorax_data: np.ndarray | None,
    abdomen_data: np.ndarray | None,
    sf_effort: float,
    central_threshold_s: float = 10.0,
) -> list:
    """
    Decompose mixed apneas into central and obstructive portions.

    For each mixed apnea, the effort signal (thorax + abdomen) is analysed
    to determine the duration of the central portion (absent effort) and
    the obstructive portion (resumed effort against closed airway).

    If the central portion ≥ central_threshold_s, the event is
    reclassified as ``"central"`` with ``mixed_decomposed=True``.

    Parameters
    ----------
    events : list[dict]
        Respiratory events from the pipeline.
    thorax_data, abdomen_data : ndarray or None
        Raw effort signals.
    sf_effort : float
        Sampling frequency of effort signals.
    central_threshold_s : float
        Minimum central portion duration (seconds) to reclassify as
        central. Default 10.0 s (per AASM guideline).

    Returns
    -------
    list[dict] — modified events with decomposition metadata.
    """
    if thorax_data is None and abdomen_data is None:
        return events

    # Use sum of thorax + abdomen for effort detection
    if thorax_data is not None and abdomen_data is not None:
        # Align lengths
        min_len = min(len(thorax_data), len(abdomen_data))
        effort = np.abs(thorax_data[:min_len]) + np.abs(abdomen_data[:min_len])
    elif thorax_data is not None:
        effort = np.abs(thorax_data)
    else:
        effort = np.abs(abdomen_data)

    n_decomposed = 0
    n_reclassified = 0
    modified = []

    for ev in events:
        ev = dict(ev)

        if ev.get("type") != "mixed":
            modified.append(ev)
            continue

        onset_s = float(ev.get("onset_s", 0))
        dur_s = float(ev.get("duration_s", 0))
        if dur_s < 3:
            modified.append(ev)
            continue

        # Extract effort segment for this event
        idx_start = int(onset_s * sf_effort)
        idx_end = int((onset_s + dur_s) * sf_effort)
        idx_end = min(idx_end, len(effort))

        if idx_start >= idx_end:
            modified.append(ev)
            continue

        seg = effort[idx_start:idx_end]

        # Determine effort threshold: amplitude < 20% of segment max
        # indicates absent effort (central portion)
        seg_max = np.max(seg)
        if seg_max < 1e-10:
            # Entire event has no effort → pure central
            ev["central_duration_s"] = safe_r(dur_s)
            ev["obstructive_duration_s"] = 0.0
            ev["central_ratio"] = 1.0
            ev["mixed_decomposed"] = True
            ev["original_type"] = "mixed"
            ev["type"] = "central"
            ev["confidence"] = max(ev.get("confidence", 0.5), 0.85)
            n_reclassified += 1
            n_decomposed += 1
            modified.append(ev)
            continue

        effort_threshold = 0.20 * seg_max
        low_effort = seg < effort_threshold

        # Find the central portion: contiguous low-effort from event start
        # (AASM: mixed apnea starts central, transitions to obstructive)
        central_samples = 0
        for val in low_effort:
            if val:
                central_samples += 1
            else:
                break

        central_dur = central_samples / sf_effort
        obstr_dur = dur_s - central_dur

        ev["central_duration_s"] = safe_r(central_dur, 1)
        ev["obstructive_duration_s"] = safe_r(obstr_dur, 1)
        ev["central_ratio"] = safe_r(
            central_dur / dur_s if dur_s > 0 else 0, 2
        )
        ev["mixed_decomposed"] = True
        n_decomposed += 1

        # Reclassify if central portion dominates
        if central_dur >= central_threshold_s:
            ev["original_type"] = "mixed"
            ev["type"] = "central"
            ev["confidence"] = max(ev.get("confidence", 0.5), 0.80)
            n_reclassified += 1

        modified.append(ev)

    if n_decomposed > 0:
        logger.info(
            "Mixed decomposition: %d analysed, %d reclassified as central",
            n_decomposed, n_reclassified,
        )

    return modified


# ---------------------------------------------------------------------------
# 3. Central instability index
# ---------------------------------------------------------------------------

def compute_central_instability_index(
    ahi_strict: float | None,
    ahi_standard: float | None,
    ahi_sensitive: float | None,
    oahi_strict: float | None = None,
    oahi_standard: float | None = None,
    oahi_sensitive: float | None = None,
) -> dict:
    """
    Quantify the uncertainty in obstructive vs. central classification
    by comparing OAHI across scoring profiles.

    A high instability index indicates many ambiguous events where the
    central vs. obstructive nature depends on scoring stringency.

    Parameters
    ----------
    ahi_* : float or None
        Total AHI for each profile.
    oahi_* : float or None
        Obstructive AHI for each profile (if available).

    Returns
    -------
    dict with keys:
        central_instability_index : float (0-1 scale)
        interpretation : str
        ahi_range : float (max - min AHI across profiles)
    """
    result = {
        "central_instability_index": None,
        "interpretation": "insufficient data",
        "ahi_range": None,
    }

    # Use OAHI if available, otherwise AHI
    vals = []
    if oahi_strict is not None and oahi_sensitive is not None:
        vals = [v for v in [oahi_strict, oahi_standard, oahi_sensitive] if v is not None]
    elif ahi_strict is not None and ahi_sensitive is not None:
        vals = [v for v in [ahi_strict, ahi_standard, ahi_sensitive] if v is not None]

    if len(vals) < 2:
        return result

    val_range = max(vals) - min(vals)
    val_mean = np.mean(vals)
    # Normalise: range / mean → coefficient of variation-like metric
    cii = val_range / val_mean if val_mean > 1.0 else val_range / 5.0

    # Clip to [0, 1]
    cii = min(1.0, max(0.0, cii))

    if cii < 0.15:
        interp = "low — classification stable across profiles"
    elif cii < 0.40:
        interp = "moderate — some events are profile-sensitive"
    else:
        interp = "high — many ambiguous events, consider manual review"

    result["central_instability_index"] = safe_r(cii, 3)
    result["interpretation"] = interp
    result["ahi_range"] = safe_r(val_range, 1)

    return result


# ---------------------------------------------------------------------------
# 4. Master post-processing function
# ---------------------------------------------------------------------------

def postprocess_respiratory_events(
    events: list,
    csr_info: dict | None = None,
    thorax_data: np.ndarray | None = None,
    abdomen_data: np.ndarray | None = None,
    sf_effort: float = 0,
    ahi_interval: dict | None = None,
) -> dict:
    """
    Run all post-processing refinements on respiratory events.

    Call this after the main pipeline has completed CSR flagging.

    Returns
    -------
    dict with keys:
        events : list — refined events
        n_csr_reclassified : int
        n_mixed_decomposed : int
        n_mixed_to_central : int
        central_instability : dict
        cai_standard : float — standard CAI
        cai_decomposed : float — CAI after decomposition
    """
    result = {
        "events": events,
        "n_csr_reclassified": 0,
        "n_mixed_decomposed": 0,
        "n_mixed_to_central": 0,
        "central_instability": {},
    }

    original_events = events

    # Count original central events
    n_central_before = sum(
        1 for e in events if e.get("type") == "central"
    )

    # Step 1: CSR-aware reclassification
    if csr_info:
        events = reclassify_csr_events(events, csr_info)
        result["n_csr_reclassified"] = sum(
            1 for e in events if e.get("csr_reclassified")
        )

    # Step 2: Mixed apnea decomposition
    if sf_effort > 0:
        events = decompose_mixed_apneas(
            events, thorax_data, abdomen_data, sf_effort,
        )
        result["n_mixed_decomposed"] = sum(
            1 for e in events if e.get("mixed_decomposed")
        )
        result["n_mixed_to_central"] = sum(
            1 for e in events
            if e.get("mixed_decomposed") and e.get("type") == "central"
        )

    # Step 3: Central instability index
    if ahi_interval:
        std = ahi_interval.get("standard", {})
        strict = ahi_interval.get("strict", {})
        sensitive = ahi_interval.get("sensitive", {})
        result["central_instability"] = compute_central_instability_index(
            ahi_strict=strict.get("ahi"),
            ahi_standard=std.get("ahi"),
            ahi_sensitive=sensitive.get("ahi"),
        )

    # Count final central events
    n_central_after = sum(
        1 for e in events if e.get("type") == "central"
    )

    result["events"] = events
    result["cai_change"] = n_central_after - n_central_before

    logger.info(
        "Post-processing: CAI change %+d (CSR: %d, mixed decomp: %d)",
        result["cai_change"],
        result["n_csr_reclassified"],
        result["n_mixed_to_central"],
    )

    return result
