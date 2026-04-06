"""
psgscoring.respiratory
======================
AASM 2.6 apnea / hypopnea event detection and Rule 1B reinstatement.

This module orchestrates the signal-level primitives from ``signal``,
``breath``, ``classify``, and ``spo2`` into the full respiratory-event
detection pipeline.

Public API
----------
detect_respiratory_events(...)  -> dict
reinstate_rule1b_hypopneas(...) -> (reinstated, all_events)
"""

from __future__ import annotations
import traceback
import logging

import numpy as np
from scipy.ndimage import label, find_objects, uniform_filter1d

from .constants import (
    APNEA_THRESHOLD, HYPOPNEA_THRESHOLD, HYPOPNEA_SMOOTH_S,
    APNEA_MIN_DUR_S, HYPOPNEA_MIN_DUR_S,
    APNEA_MAX_DUR_S, HYPOPNEA_MAX_DUR_S,
    DESATURATION_DROP_PCT, EPOCH_LEN_S,
    MMSD_APNEA_THRESH, RULE1B_AROUSAL_WINDOW_S,
)
from .utils import build_sleep_mask, is_nrem, is_rem, safe_r
from .signal import (
    bandpass_flow, compute_dynamic_baseline, compute_mmsd,
    compute_stage_baseline, detect_position_changes, preprocess_effort,
    preprocess_flow, reset_baseline_at_position_changes,
)
from .breath import (
    compute_breath_amplitudes, compute_flattening_index,
    detect_breath_events, detect_breaths,
)
from .classify import classify_apnea_type
from .spo2 import get_desaturation

logger = logging.getLogger("psgscoring.respiratory")


# ---------------------------------------------------------------------------
# Overschatting-correcties (5 mechanismen)
# ---------------------------------------------------------------------------

def _detect_signal_gaps(
    flow_data: np.ndarray,
    sf: float,
    min_gap_s: float = 10.0,
    postgap_excl_s: float = 15.0,
    flatline_thresh: float = 1e-5,
) -> tuple[np.ndarray, int]:
    """
    Fix 5 — Artefact-flanken.

    Detecteer signaaluitval (vlakke lijn / bevroren signaal ≥ min_gap_s).
    Geef een bool-masker terug dat de eerste postgap_excl_s na elk gat als
    True markeert (= uitsluiten van event-detectie).
    Zo wordt de herstelramp na een dropout niet als event gescoord.

    Returns
    -------
    (gap_exclusion_mask, n_gaps_detected)
    """
    n = len(flow_data)
    excl = np.zeros(n, dtype=bool)
    min_samp = int(min_gap_s * sf)
    post_samp = int(postgap_excl_s * sf)

    is_flat   = np.abs(flow_data) < flatline_thresh
    diff      = np.diff(flow_data, prepend=flow_data[0] - 1)
    is_frozen = diff == 0
    flat_reg  = is_flat | is_frozen

    labeled, n_gaps = label(flat_reg)
    for i, sl in enumerate(find_objects(labeled)):
        if sl is None:
            continue
        sl0 = sl[0]
        seg_len = sl0.stop - sl0.start
        if seg_len >= min_samp:
            end = sl0.stop
            excl[end : end + post_samp] = True

    return excl, n_gaps


def _build_postapnea_recovery_mask(
    apnea_events: list,
    n_samples: int,
    sf: float,
    recovery_s: float = 30.0,
) -> np.ndarray:
    """
    Fix 1 — Post-apnea hyperpnea basislijnopblazing.

    Geef een bool-masker terug dat de eerste recovery_s na elke bevestigde
    apnea markeert als True (= uitsluiten uit basislijnberekening).
    Zo zorgen compensatoire hyperventilaties niet voor een kunstmatig hoge
    95e-percentiel basislijn, wat anders hypopnea-aantallen opblaast.
    """
    mask = np.zeros(n_samples, dtype=bool)
    rec  = int(recovery_s * sf)
    for ev in apnea_events:
        end = int((ev["onset_s"] + ev["duration_s"]) * sf)
        mask[end : end + rec] = True
    return mask


def _recompute_baseline_with_recovery_excluded(
    flow_env: np.ndarray,
    sf: float,
    recovery_mask: np.ndarray,
    original_baseline: np.ndarray,
    min_recovery_fraction: float = 0.05,
) -> np.ndarray:
    """
    Pas de dynamische basislijn aan op plekken waar de recovery mask een
    significante fractie van het venster bedekt.

    Alleen de ~4% van ankerposities waar recovery-samples aanwezig zijn
    worden herberekend — geen volledige tweede basislijnberekening.
    """
    step       = int(sf * 10)
    win        = int(sf * 300)
    min_stable = int(sf * 30)
    n          = len(flow_env)

    # Start met kopie van originele basislijn
    bl = original_baseline.copy()

    # Bouw sparse recovery-fractie vooraf (vectorized) om dure loop te vermijden
    sample_points = np.arange(0, n, step)
    # Gebruik rolling sum via cumsum voor snelle vensterfractie
    rm_cumsum = np.concatenate([[0], np.cumsum(recovery_mask)])

    for idx, center in enumerate(sample_points):
        start = max(0, center - win // 2)
        end   = min(n, center + win // 2)
        win_len = end - start

        # Snel controleren: hoeveel recovery-samples in dit venster?
        n_recovery = int(rm_cumsum[end] - rm_cumsum[start])
        if n_recovery < win_len * min_recovery_fraction:
            continue  # venster nauwelijks beïnvloed — sla over

        # Herbereken alleen voor dit anker
        seg    = flow_env[start:end]
        rm     = recovery_mask[start:end]
        stable = seg[~rm & (seg > 0)]
        if len(stable) < min_stable:
            continue

        p95    = float(np.percentile(stable, 95))
        thresh = 0.3 * p95
        above  = stable[stable > thresh]
        if len(above) > 0:
            bl[center : min(n, center + step)] = float(np.percentile(above, 95))

    return bl


def _spo2_cross_contaminated(
    onset_s: float,
    events_so_far: list,
    post_event_window_s: float = 15.0,
) -> bool:
    """
    Fix 2 — SpO2 kruiscontaminatie (v0.8.14: minder agressief).

    Controleer of het post-event SpO2-venster van het vorige event nog actief
    is bij het begin van het huidige event.

    v0.8.14: window verkleind van 30s naar 15s. Bij 30s werden bijna alle
    events bij matig OSAS geflagd → massale ondertelling van hypopnees.
    De flag is nu INFORMATIEF — de desaturatie wordt nog steeds berekend.

    Returns True als de SpO2-koppeling mogelijk contaminated is.
    """
    if not events_so_far:
        return False
    last = events_so_far[-1]
    last_end = last["onset_s"] + last["duration_s"]
    return (onset_s - last_end) < post_event_window_s


def _flag_csr_events(
    events: list,
    csr_info: dict,
    tolerance_s: float = 12.0,
) -> list:
    """
    Fix 3 — Cheyne-Stokes AHI-inflatie.

    Markeer events waarvan het inter-event interval overeenkomt met de
    CSR-periodiciteit (±tolerance_s). Deze events vertegenwoordigen de
    hypopneu-fase van een CSR-cyclus, niet zelfstandige obstructieve events.

    Voegt veld ``csr_flagged: True`` toe aan overeenkomende events.
    Geeft de gemodificeerde eventlijst terug.
    """
    if not csr_info or not csr_info.get("csr_detected"):
        return events

    periodicity_s = float(csr_info.get("periodicity_s", 0) or 0)
    if periodicity_s < 20:  # onwaarschijnlijk / niet ingesteld
        return events

    modified = [dict(e) for e in events]

    # Bereken inter-event intervallen
    for i in range(1, len(modified)):
        prev_end = modified[i-1]["onset_s"] + modified[i-1]["duration_s"]
        iei      = modified[i]["onset_s"] - prev_end  # inter-event interval

        # Controleer of IEI overeenkomt met CSR-periodiciteit (of meervoud)
        for k in range(1, 4):  # tot 3 cycli
            if abs(iei - k * periodicity_s) < tolerance_s:
                modified[i]["csr_flagged"] = True
                modified[i-1]["csr_flagged"] = True
                break

    return modified


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def _get_ecg_assessment(ecg_data, tecg, r_peaks, thorax_raw, abdomen_raw,
                        sf_flow, sf_ecg, onset_idx, end_idx):
    """Compute ECG-derived effort assessment for one event.

    Handles sample-rate conversion between flow and ECG signals.
    """
    try:
        from .ecg_effort import ecg_effort_assessment
        # Convert flow-signal indices to ECG-signal indices
        ratio = sf_ecg / sf_flow if sf_flow > 0 else 1.0
        ecg_onset = int(onset_idx * ratio)
        ecg_end   = int(end_idx * ratio)
        ecg_end   = min(ecg_end, len(ecg_data) if ecg_data is not None else ecg_end)
        return ecg_effort_assessment(
            ecg=ecg_data, thorax_raw=thorax_raw, abdomen_raw=abdomen_raw,
            sf=sf_ecg, onset_idx=ecg_onset, end_idx=ecg_end,
            tecg=tecg, r_peaks=r_peaks,
        )
    except Exception as exc:
        logger.debug("ECG effort assessment failed for event %d-%d: %s",
                     onset_idx, end_idx, exc)
        return None


def detect_respiratory_events(
    flow_data:    np.ndarray,
    thorax_data:  np.ndarray | None,
    abdomen_data: np.ndarray | None,
    spo2_data:    np.ndarray | None,
    sf_flow:      float,
    sf_spo2:      float,
    hypno:        list,
    only_during_sleep: bool = True,
    artifact_epochs:   list | None = None,
    hypop_flow:        np.ndarray | None = None,
    sf_hypop:          float | None = None,
    pos_data:          np.ndarray | None = None,
    sf_pos:            float | None = None,
    csr_info:          dict | None = None,
    scoring_profile:   dict | None = None,
    ecg_data:          np.ndarray | None = None,
    sf_ecg:            float | None = None,
) -> dict:
    """
    Detect and classify apneas and hypopneas per AASM 2.6.

    Sensor assignment (AASM 2.6)
    ----------------------------
    ``flow_data``  : oronasal thermistor  -> apnea detection (cessation)
    ``hypop_flow`` : nasal pressure transducer -> hypopnea detection (more sensitive)
    If *hypop_flow* is None, *flow_data* is used for both (backward-compatible).

    Overschatting-correcties (v0.8.11)
    ------------------------------------
    1. Post-apnea hyperpnea basislijn: recovery-window uitgesloten uit basislijn.
    2. SpO₂ kruiscontaminatie: nadir niet toegewezen als vorig post-event venster actief.
    3. Cheyne-Stokes: events gemarkeerd als ``csr_flagged`` via ``csr_info``.
    4. Borderline default: conf<0.40 events geteld als ``n_low_conf_borderline``.
    5. Artefact-flanken: post-gap exclusiemasker (15 s na uitval ≥10 s).

    Parameters
    ----------
    csr_info : dict, optional
        Output van ``detect_cheyne_stokes()``. Wordt gebruikt om events
        te markeren als onderdeel van een CSR-cyclus.

    Returns
    -------
    dict with keys: success, events, rejected_hypopneas, summary,
    breath_analysis, dual_sensor, _breaths, error,
    n_gap_excluded, n_posthyperpnea_recovery_s.
    """
    result: dict = {"success": False, "events": [], "summary": {}, "error": None,
                    "n_gap_excluded": 0, "n_posthyperpnea_recovery_s": 30}
    try:
        # ── v0.8.15: Scoring profile → lokale drempels ────────────────────
        sp = scoring_profile or {}
        _HYPOP_THRESH  = sp.get("HYPOPNEA_THRESHOLD", HYPOPNEA_THRESHOLD)
        _DESAT_PCT     = sp.get("DESATURATION_DROP_PCT", DESATURATION_DROP_PCT)
        _POST_WIN      = sp.get("POST_EVENT_WINDOW_S", 45)
        _SMOOTH_S      = sp.get("HYPOPNEA_SMOOTH_S", HYPOPNEA_SMOOTH_S)
        _CONTAM_WIN    = sp.get("CROSS_CONTAM_WINDOW_S", 15.0)
        _USE_PEAK      = sp.get("USE_PEAK_DETECTION", True)
        _APNEA_MAX     = sp.get("APNEA_MAX_DUR_S", APNEA_MAX_DUR_S)
        _HYPOP_MAX     = sp.get("HYPOPNEA_MAX_DUR_S", HYPOPNEA_MAX_DUR_S)
        result["scoring_thresholds"] = {
            "hypopnea_threshold": _HYPOP_THRESH,
            "desaturation_pct":   _DESAT_PCT,
            "post_event_win_s":   _POST_WIN,
            "smooth_s":           _SMOOTH_S,
            "cross_contam_win_s": _CONTAM_WIN,
            "use_peak_detection": _USE_PEAK,
        }

        # ── Fix 5: Artefact-flanken — post-gap exclusiemasker ─────────────
        gap_mask_ap, n_gaps = _detect_signal_gaps(flow_data, sf_flow)
        result["n_gap_excluded"] = n_gaps
        if n_gaps > 0:
            logger.info("Fix5: %d signaaluitvalgaten gedetecteerd → post-gap masker actief", n_gaps)

        # ── v0.8.23: ECG-derived effort (TECG) — compute once ────────────
        _tecg = None
        _r_peaks = None
        _sf_ecg_local = sf_ecg or sf_flow
        if ecg_data is not None and len(ecg_data) > 0:
            try:
                from .ecg_effort import compute_tecg, detect_r_peaks
                _r_peaks = detect_r_peaks(ecg_data, _sf_ecg_local)
                _tecg = compute_tecg(ecg_data, _sf_ecg_local, _r_peaks)
                logger.info("TECG computed: %d R-peaks detected, signal length %d",
                            len(_r_peaks), len(_tecg))
            except Exception as exc:
                logger.warning("TECG computation failed: %s", exc)
                _tecg = None

        # ── Apnea-channel preprocessing (thermistor, no sqrt) ──────────────
        flow_env = preprocess_flow(flow_data, sf_flow, is_nasal_pressure=False)
        baseline = compute_dynamic_baseline(flow_env, sf_flow)
        pos_changes: list[dict] = []

        # MMSD – drift-independent apnea validation
        mmsd_norm = _compute_mmsd_norm(flow_data, sf_flow, result)

        # Stage-specific baseline
        baseline = _apply_stage_baseline(flow_env, sf_flow, hypno,
                                          artifact_epochs, baseline, result)

        # Position-reset baseline
        if pos_data is not None and sf_pos is not None:
            baseline, pos_changes = _apply_position_reset(
                baseline, flow_env, sf_flow, pos_data, sf_pos, result
            )

        flow_norm = np.clip(flow_env / baseline, 0, 2)

        # ── Hypopnea-channel preprocessing (nasal pressure, with sqrt) ─────
        hypop_env, hypop_norm, hypop_baseline, sf_hy = _setup_hypop_channel(
            hypop_flow, sf_hypop, flow_env, baseline, flow_norm, sf_flow,
            hypno, artifact_epochs, pos_changes, pos_data, sf_pos, result,
            precomputed_hypop_baseline=baseline,  # hergebruik apnea-basislijn als sf gelijk
        )

        # ── Breath-by-breath analysis ────────────────────────────────────
        breaths, bb_apneas, bb_hypopneas = _run_breath_analysis(
            hypop_flow if hypop_flow is not None else flow_data,
            sf_hy, hypno, result,
        )

        # ── Effort envelopes ─────────────────────────────────────────────
        thorax_env  = preprocess_effort(thorax_data, sf_flow) if thorax_data  is not None else None
        abdomen_env = preprocess_effort(abdomen_data, sf_flow) if abdomen_data is not None else None
        effort_bl   = _compute_effort_baseline(thorax_env, abdomen_env, flow_norm, sf_flow)

        # ── Global SpO2 baseline ─────────────────────────────────────────
        global_spo2_bl = _global_spo2_baseline(spo2_data, sf_spo2, hypno, artifact_epochs)

        # ── Event masks ──────────────────────────────────────────────────
        sleep_mask_ap = build_sleep_mask(hypno, sf_flow, len(flow_norm),  artifact_epochs)
        sleep_mask_hy = build_sleep_mask(hypno, sf_hy,   len(hypop_norm), artifact_epochs)

        # Incorporate Fix 5 gap mask
        sleep_mask_ap = sleep_mask_ap & ~gap_mask_ap
        # Hypop gap mask: hergebruik flow gap mask als zelfde kanaal, anders apart berekenen
        if hypop_flow is None:
            gap_mask_hy = gap_mask_ap  # zelfde signaal, geen herberekening
        else:
            gap_mask_hy, _ = _detect_signal_gaps(hypop_flow, sf_hy)
        sleep_mask_hy = sleep_mask_hy & ~gap_mask_hy

        apnea_raw    = flow_norm  < APNEA_THRESHOLD

        # ── v0.8.14: AASM-conforme peak-gebaseerde hypopnea-detectie ─────
        # AASM 2.6: "peak signal excursions drop by ≥30%"
        # = per-ademhaling piek-amplitude, NIET continue envelope.
        # We combineren peak-mask met envelope-mask (OR) voor max. sensitiviteit.
        _smooth_win = max(1, int(_SMOOTH_S * sf_hy)) if _SMOOTH_S > 0 else 1

        # Peak-based mask from breath-by-breath analysis
        peak_mask_hy = np.zeros(len(hypop_norm), dtype=bool)
        if _USE_PEAK and breaths and len(breaths) > 10:
            ratios = compute_breath_amplitudes(breaths, sf_hy)
            for bi, br in enumerate(breaths):
                if ratios[bi] < _HYPOP_THRESH and ratios[bi] >= APNEA_THRESHOLD:
                    s_idx = int(br["onset_s"] * sf_hy)
                    e_idx = int((br["onset_s"] + br["duration_s"]) * sf_hy)
                    peak_mask_hy[max(0,s_idx):min(len(peak_mask_hy),e_idx)] = True
            n_peak = int(peak_mask_hy.sum())
            logger.info("[pneumo] Peak-based hypopnea mask: %d samples (%.1f s)",
                        n_peak, n_peak / sf_hy)

        # Envelope-based mask (smoothed, originele methode)
        hypop_norm_smooth = uniform_filter1d(hypop_norm, _smooth_win)
        envelope_mask_hy = (hypop_norm_smooth < _HYPOP_THRESH) & ~(hypop_norm_smooth < APNEA_THRESHOLD)

        # Combineer: event gevonden door PEAK óf ENVELOPE → scoren
        hypopnea_raw = peak_mask_hy | envelope_mask_hy

        events: list[dict]    = []
        rejected: list[dict] = []

        # ── Detect apneas ─────────────────────────────────────────────────
        events = _detect_apneas(
            apnea_raw, sleep_mask_ap, flow_env, flow_norm, baseline,
            sf_flow, sf_spo2, hypno,
            thorax_env, abdomen_env, thorax_data, abdomen_data, effort_bl,
            spo2_data, global_spo2_bl, mmsd_norm,
            max_dur_s=_APNEA_MAX,
            ecg_data=ecg_data, tecg=_tecg, r_peaks=_r_peaks,
            sf_ecg=_sf_ecg_local,
        )

        # ── Fix 1: Herbereken hypopnea-basislijn zonder post-apnea recovery ─
        RECOVERY_S = 30.0
        result["n_posthyperpnea_recovery_s"] = RECOVERY_S
        if events:
            recovery_mask = _build_postapnea_recovery_mask(
                events, len(hypop_env), sf_hy, recovery_s=RECOVERY_S
            )
            # Geef bestaande basislijn mee — geen dubbele berekening
            hypop_baseline_corrected = _recompute_baseline_with_recovery_excluded(
                hypop_env, sf_hy, recovery_mask,
                original_baseline=hypop_baseline,
            )
            n_recovery_samples = int(recovery_mask.sum())
            logger.info("Fix1: post-apnea recovery mask: %d samples uitgesloten uit basislijn "
                        "(%.1f%% van totaal)", n_recovery_samples,
                        100 * n_recovery_samples / max(len(hypop_env), 1))
        else:
            hypop_baseline_corrected = hypop_baseline

        # Herbereken hypop_norm met gecorrigeerde basislijn
        hypop_norm_corrected = np.clip(hypop_env / hypop_baseline_corrected, 0, 2)
        hypop_norm_corrected_smooth = uniform_filter1d(hypop_norm_corrected, _smooth_win)
        envelope_mask_corrected = (
            (hypop_norm_corrected_smooth < _HYPOP_THRESH)
            & ~(hypop_norm_corrected_smooth < APNEA_THRESHOLD)
        )
        # v0.8.14: peak + envelope merge voor gecorrigeerde pass
        # Peak-mask herberekenen met gecorrigeerde basislijn
        peak_mask_corrected = np.zeros(len(hypop_norm_corrected), dtype=bool)
        if _USE_PEAK and breaths and len(breaths) > 10:
            amps = np.array([b["amplitude"] for b in breaths])
            # Herbereken ratios met gecorrigeerde basislijn per ademhaling
            for bi, br in enumerate(breaths):
                mid_idx = int((br["onset_s"] + br["duration_s"]/2) * sf_hy)
                mid_idx = min(mid_idx, len(hypop_baseline_corrected) - 1)
                local_bl = float(hypop_baseline_corrected[max(0,mid_idx)])
                ratio_c = amps[bi] / local_bl if local_bl > 1e-9 else 1.0
                if ratio_c < _HYPOP_THRESH and ratio_c >= APNEA_THRESHOLD:
                    s_idx = int(br["onset_s"] * sf_hy)
                    e_idx = int((br["onset_s"] + br["duration_s"]) * sf_hy)
                    peak_mask_corrected[max(0,s_idx):min(len(peak_mask_corrected),e_idx)] = True
        hypopnea_raw_corrected = peak_mask_corrected | envelope_mask_corrected

        # ── Detect hypopneas (met gecorrigeerde basislijn + Fix 2 SpO₂) ───
        new_events, rejected = _detect_hypopneas(
            hypopnea_raw_corrected, sleep_mask_hy, hypop_env,
            hypop_norm_corrected, hypop_baseline_corrected,
            sf_hy, sf_flow, sf_spo2, hypno,
            thorax_env, abdomen_env, thorax_data, abdomen_data, effort_bl,
            spo2_data, global_spo2_bl, events,
            apply_spo2_crosscontam_fix=True,
            desat_pct=_DESAT_PCT,
            contam_win_s=_CONTAM_WIN,
            post_event_win_s=_POST_WIN,
            max_dur_s=_HYPOP_MAX,
            ecg_data=ecg_data, tecg=_tecg, r_peaks=_r_peaks,
            sf_ecg=_sf_ecg_local,
        )
        events = new_events

        # v0.8.22: log lokale basislijn-rejecties
        n_local_rejected = sum(1 for r in rejected if "local_reduction" in str(r.get("reject_reason","")))
        if n_local_rejected:
            logger.info("v0.8.22: %d hypopnea-kandidaten afgewezen door lokale basislijn-validatie "
                        "(flow-reductie <20%% t.o.v. pre-event ademhaling)", n_local_rejected)
        result["n_local_baseline_rejected"] = n_local_rejected

        events.sort(key=lambda x: x["onset_s"])

        # ── Fix 3: CSR event markering ─────────────────────────────────────
        if csr_info and csr_info.get("csr_detected"):
            events = _flag_csr_events(events, csr_info)
            n_csr_flagged = sum(1 for e in events if e.get("csr_flagged"))
            logger.info("Fix3: %d events gemarkeerd als mogelijk CSR-gerelateerd", n_csr_flagged)

        result["events"]             = events
        result["rejected_hypopneas"] = rejected
        result["summary"]            = _compute_summary(events, hypno, artifact_epochs,
                                                         csr_info=csr_info)
        # v0.8.23: count ECG-reclassified events
        n_ecg_reclass = sum(
            1 for e in events
            if e.get("classify_detail", {}).get("ecg_assessment", {}).get("reclassify_as_central", False)
        )
        result["n_ecg_reclassified_central"] = n_ecg_reclass
        if n_ecg_reclass > 0:
            logger.info("ECG-TECG: %d events reclassified as central", n_ecg_reclass)
        result["success"]            = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ---------------------------------------------------------------------------
# Rule 1B – arousal-coupled hypopnea reinstatement
# ---------------------------------------------------------------------------

def reinstate_rule1b_hypopneas(
    rejected:       list,
    arousal_events: list,
    resp_events:    list,
    hypno:          list,
    breaths:        list | None = None,
) -> tuple[list, list]:
    """
    Reinstate hypopnea candidates that are coupled to an arousal
    (AASM 2.6 Rule 1B).

    v0.8.1 improvement: if more than one complete breath cycle occurs between
    event termination and arousal onset, the coupling is classified as
    coincidental and the candidate is *not* reinstated.

    Parameters
    ----------
    rejected       : candidates from detect_respiratory_events
    arousal_events : detected arousals (from arousal_analysis module)
    resp_events    : existing Rule 1A events (list to extend)
    hypno          : string hypnogram
    breaths        : breath dicts from the respiratory analysis (optional)

    Returns
    -------
    (reinstated_events, all_events_sorted)
    """
    if not rejected or not arousal_events:
        return [], resp_events

    arousal_times = [
        (float(a.get("onset_s", 0)), float(a.get("duration_s", 3)))
        for a in arousal_events
    ]
    breath_onsets = (
        sorted(b["onset_s"] for b in breaths if b.get("amplitude", 0) > 0)
        if breaths else None
    )

    reinstated: list[dict] = []
    for cand in rejected:
        onset = float(cand["onset_s"])
        dur   = float(cand["duration_s"])
        end   = onset + dur

        matched_arousal = next(
            (a_onset for a_onset, _ in arousal_times
             if onset <= a_onset <= end + RULE1B_AROUSAL_WINDOW_S),
            None,
        )
        if matched_arousal is None:
            continue

        # Breath-cycle gap check (v0.8.1)
        if breath_onsets and matched_arousal > end + 2.0:
            n_in_gap = sum(1 for bo in breath_onsets if end <= bo < matched_arousal)
            if n_in_gap > 1:
                continue

        reinstated.append({
            "type":             "hypopnea",
            "onset_s":          cand["onset_s"],
            "duration_s":       cand["duration_s"],
            "stage":            cand["stage"],
            "desaturation_pct": cand.get("desat"),
            "min_spo2":         cand.get("min_spo2"),
            "flow_reduction":   None,
            "confidence":       0.7,
            "classify_detail":  {"rule": "1B_arousal"},
            "epoch":            cand["epoch"],
            "rule1b":           True,
        })

    if reinstated:
        all_ev = resp_events + reinstated
        all_ev.sort(key=lambda x: float(x["onset_s"]))
        return reinstated, all_ev

    return [], resp_events


# ---------------------------------------------------------------------------
# Private pipeline helpers
# ---------------------------------------------------------------------------

def _compute_mmsd_norm(
    flow_data: np.ndarray,
    sf_flow: float,
    result: dict,
) -> np.ndarray | None:
    """Bereken genormaliseerde MMSD (Mean Magnitude Second Derivative) van flowsignaal."""
    try:
        filt       = bandpass_flow(flow_data, sf_flow)
        mmsd       = compute_mmsd(filt, sf_flow, window_s=1.0)
        stable     = mmsd[mmsd > np.percentile(mmsd, 10)]
        mmsd_bl    = float(np.median(stable)) if len(stable) > 100 else 1.0
        result["mmsd_available"] = True
        return mmsd / max(mmsd_bl, 1e-9)
    except Exception as e:
        result["mmsd_available"] = False
        logger.debug("MMSD failed: %s", e)
        return None


def _apply_stage_baseline(
    flow_env, sf_flow, hypno, artifact_epochs, baseline, result
):
    """Pas stadium-specifieke basislijn toe (REM vs NREM ademhalingspatroon)."""
    try:
        stage_bl = compute_stage_baseline(
            flow_env, sf_flow, hypno, artifact_epochs,
            dynamic_baseline=baseline,  # hergebruik — geen extra berekening
        )
        result["stage_baseline_used"] = True
        return (baseline + stage_bl) / 2
    except Exception as e:
        logger.debug("Stage baseline fallback: %s", e)
        result["stage_baseline_used"] = False
        return baseline


def _apply_position_reset(
    baseline, flow_env, sf_flow, pos_data, sf_pos, result
):
    """Herbereken basislijn na positieverandering (eerste 60s van nieuw segment)."""
    try:
        pos_changes = detect_position_changes(pos_data, sf_pos)
        if pos_changes:
            pc_flow = [
                {**pc, "sample": int(pc["time_s"] * sf_flow)}
                for pc in pos_changes
            ]
            baseline = reset_baseline_at_position_changes(
                baseline, flow_env, sf_flow, pc_flow
            )
            result["n_position_changes"] = len(pos_changes)
        return baseline, pos_changes
    except Exception as e:
        logger.debug("Position reset fallback: %s", e)
        return baseline, []


def _setup_hypop_channel(
    hypop_flow, sf_hypop, flow_env, baseline, flow_norm,
    sf_flow, hypno, artifact_epochs, pos_changes, pos_data, sf_pos, result,
    precomputed_hypop_baseline=None,
):
    """Return (hypop_env, hypop_norm, hypop_baseline, sf_hy)."""
    if hypop_flow is not None and sf_hypop is not None:
        # Als hypop zelfde signaal is als flow (zelfde array-object of zelfde sf+lengte):
        # sla herberekening over, gebruik flow_env direct maar met √-normalisatie markering
        same_signal = (
            precomputed_hypop_baseline is not None
            and sf_hypop == sf_flow
            and len(hypop_flow) == len(flow_env)
        )
        if same_signal:
            # Hergebruik flow_env envelope (al berekend), sla preprocess opnieuw over
            hypop_env = flow_env
        else:
            hypop_env = preprocess_flow(hypop_flow, sf_hypop, is_nasal_pressure=True)

        # Als sf gelijk: gebruik voorberekende basislijn volledig (incl. stage-blend).
        # De basislijn is al berekend + stage-gecorrigeerd in de apnea-channel stap.
        if precomputed_hypop_baseline is not None and sf_hypop == sf_flow:
            hypop_bl = precomputed_hypop_baseline
        else:
            # Andere sf (bv. 2Hz SpO₂ vs 256Hz flow): apart berekenen
            hypop_bl = compute_dynamic_baseline(hypop_env, sf_hypop)
            try:
                hyp_stage_bl = compute_stage_baseline(
                    hypop_env, sf_hypop, hypno, artifact_epochs
                )
                hypop_bl = (hypop_bl + hyp_stage_bl) / 2
            except Exception:
                pass

        if pos_data is not None and sf_pos is not None and pos_changes:
            try:
                pc_hy = [
                    {**pc, "sample": int(pc["time_s"] * sf_hypop)}
                    for pc in pos_changes
                ]
                hypop_bl = reset_baseline_at_position_changes(
                    hypop_bl, hypop_env, sf_hypop, pc_hy
                )
            except Exception:
                pass
        result["dual_sensor"] = True
        return hypop_env, np.clip(hypop_env / hypop_bl, 0, 2), hypop_bl, sf_hypop
    else:
        result["dual_sensor"] = False
        return flow_env, flow_norm, baseline, sf_flow


def _run_breath_analysis(hypop_raw, hypop_sf, hypno, result):
    """Voer breath-by-breath analyse uit: detecteer ademhalingen en bereken amplitudes."""
    try:
        filt   = bandpass_flow(hypop_raw, hypop_sf)
        breaths = detect_breaths(filt, hypop_sf)
        if len(breaths) > 10:
            ratios = compute_breath_amplitudes(breaths, hypop_sf)
            for b_i, br in enumerate(breaths):
                seg = br.get("insp_segment")
                breaths[b_i]["flattening"] = (
                    compute_flattening_index(seg)
                    if seg is not None and len(seg) > 3 else None
                )
            bb_ap, bb_hy = detect_breath_events(breaths, ratios, hypop_sf, hypno)
            result["breath_analysis"] = {
                "n_breaths":      len(breaths),
                "n_bb_apneas":    len(bb_ap),
                "n_bb_hypopneas": len(bb_hy),
                "avg_flattening": safe_r(float(np.mean([
                    b["flattening"] for b in breaths
                    if b.get("flattening") is not None
                ])), 3) if any(b.get("flattening") is not None for b in breaths) else None,
            }
            result["_breaths"] = [
                {"onset_s": b["onset_s"], "duration_s": b["duration_s"],
                 "amplitude": b["amplitude"],
                 "flattening": b.get("flattening")}
                for b in breaths
            ]
            return breaths, bb_ap, bb_hy
        else:
            result["breath_analysis"] = {"n_breaths": len(breaths), "fallback": True}
            return breaths, [], []
    except Exception as e:
        result["breath_analysis"] = {"error": str(e), "fallback": True}
        return [], [], []


def _compute_effort_baseline(thorax_env, abdomen_env, flow_norm, sf):
    """Bereken effort-basislijn op stabiele ademhalingsperiodes (niet tijdens events)."""
    stable_mask = (flow_norm > 0.60) & (flow_norm < 1.30)
    bl: list[float] = []
    for env in (thorax_env, abdomen_env):
        if env is not None:
            seg = env[stable_mask]
            if len(seg) > int(sf * 30):
                bl.append(float(np.percentile(seg, 75)))
    return float(np.mean(bl)) if bl else 1.0


def _global_spo2_baseline(spo2_data, sf_spo2, hypno, artifact_epochs):
    """Bereken globale SpO2-basislijn: 95e percentiel over stabiele slaapperiodes."""
    if spo2_data is None:
        return None
    spo2_mask  = build_sleep_mask(hypno, sf_spo2, len(spo2_data), artifact_epochs)
    spo2_clean = spo2_data[(spo2_data >= 50) & (spo2_data <= 100) & spo2_mask]
    return float(np.percentile(spo2_clean, 95)) if len(spo2_clean) > 100 else None


# ---------------------------------------------------------------------------
# v0.8.22: Split overly long events at partial recovery points
# ---------------------------------------------------------------------------

def _split_long_region(
    idx: np.ndarray,
    flow_env: np.ndarray,
    sf: float,
    max_dur_s: float,
    min_dur_s: float = 10.0,
) -> list[np.ndarray]:
    """Split een contiguous index-regio als die > max_dur_s duurt.

    Zoekt het punt met de hoogste flow-amplitude (= beste partiële recovery)
    en splitst daar. Recursief als sub-regio's nog te lang zijn.

    Parameters
    ----------
    idx : np.ndarray        Indices in de flow-array (aaneengesloten)
    flow_env : np.ndarray   Flow-envelope voor recovery-detectie
    sf : float              Samplerate
    max_dur_s : float       Maximale event-duur in seconden
    min_dur_s : float       Minimale event-duur in seconden

    Returns
    -------
    list[np.ndarray]  — Lijst van (sub-)regio indices, elk ≥ min_dur_s
    """
    dur_s = len(idx) / sf
    if dur_s <= max_dur_s:
        return [idx]

    min_samples = int(min_dur_s * sf)
    seg = flow_env[idx[0]:idx[-1] + 1]

    if len(seg) < 2 * min_samples:
        # Te kort om te splitsen in twee geldige events → neem hele regio
        return [idx]

    # Zoek de partiële recovery: hoogste flow in het midden
    # (niet in de eerste/laatste min_dur_s samples — die moeten elk event vormen)
    search_start = min_samples
    search_end   = len(seg) - min_samples
    if search_start >= search_end:
        return [idx]

    search_seg = seg[search_start:search_end]
    split_local = int(np.argmax(search_seg))
    split_abs   = search_start + split_local

    left_idx  = idx[:split_abs]
    right_idx = idx[split_abs:]

    # Recursief splitsen als nog te lang
    result = []
    for sub in [left_idx, right_idx]:
        if len(sub) / sf >= min_dur_s:
            result.extend(_split_long_region(sub, flow_env, sf, max_dur_s, min_dur_s))
    return result if result else [idx]


def _detect_apneas(
    apnea_raw, sleep_mask_ap, flow_env, flow_norm, baseline,
    sf_flow, sf_spo2, hypno,
    thorax_env, abdomen_env, thorax_raw, abdomen_raw, effort_bl,
    spo2_data, global_spo2_bl, mmsd_norm,
    max_dur_s: float = APNEA_MAX_DUR_S,
    ecg_data=None, tecg=None, r_peaks=None, sf_ecg=None,
) -> list[dict]:
    """Detecteer apnea-events: ≥90% flow-reductie gedurende ≥10s (AASM 2.6)."""
    events: list[dict] = []
    labeled, n_ap = label(apnea_raw & sleep_mask_ap)
    slices_ap = find_objects(labeled)
    for i, sl in enumerate(slices_ap):
        if sl is None:
            continue
        sl0  = sl[0]
        idx  = np.where(labeled[sl0] == (i + 1))[0] + sl0.start
        dur_s = len(idx) / sf_flow
        if dur_s < APNEA_MIN_DUR_S:
            continue
        # MMSD validation
        if mmsd_norm is not None:
            if float(np.mean(mmsd_norm[idx[0] : idx[-1] + 1])) > MMSD_APNEA_THRESH:
                continue

        # v0.8.22: split events die te lang zijn
        sub_regions = _split_long_region(idx, flow_env, sf_flow, max_dur_s, APNEA_MIN_DUR_S)
        for sub_idx in sub_regions:
            sub_dur = len(sub_idx) / sf_flow
            onset_s    = sub_idx[0] / sf_flow
            ep_idx     = int(onset_s // EPOCH_LEN_S)
            stage      = hypno[ep_idx] if ep_idx < len(hypno) else "W"
            pre_bl     = _pre_event_baseline(flow_env, sub_idx[0], sf_flow, baseline)
            flow_mean  = float(np.mean(flow_env[sub_idx[0] : sub_idx[-1] + 1]))
            flow_red   = safe_r((1 - flow_mean / pre_bl) * 100) if pre_bl > 0 else None

            ev_type, conf, detail = classify_apnea_type(
                onset_idx=sub_idx[0], end_idx=sub_idx[-1] + 1,
                thorax_env=thorax_env, abdomen_env=abdomen_env,
                thorax_raw=thorax_raw, abdomen_raw=abdomen_raw,
                effort_baseline=effort_bl, sf=sf_flow,
                ecg_assessment=_get_ecg_assessment(
                    ecg_data, tecg, r_peaks, thorax_raw, abdomen_raw,
                    sf_flow, sf_ecg or sf_flow, sub_idx[0], sub_idx[-1] + 1
                ) if tecg is not None else None,
            )
            desat, min_spo2 = get_desaturation(
                spo2_data, onset_s, sub_dur, sf_spo2, global_spo2_bl
            )
            events.append({
                "type":               ev_type,
                "onset_s":            safe_r(onset_s),
                "duration_s":         safe_r(sub_dur),
                "stage":              stage,
                "desaturation_pct":   desat,
                "min_spo2":           min_spo2,
                "flow_nadir":         safe_r(float(np.min(flow_norm[sub_idx[0] : sub_idx[-1] + 1])), 3),
                "flow_reduction_pct": flow_red,
                "pre_baseline":       safe_r(pre_bl, 2),
                "confidence":         conf,
                "classify_detail":    detail,
                "epoch":              ep_idx,
            })
    return events


def _detect_hypopneas(
    hypopnea_raw, sleep_mask_hy, hypop_env, hypop_norm, hypop_baseline,
    sf_hy, sf_flow, sf_spo2, hypno,
    thorax_env, abdomen_env, thorax_raw, abdomen_raw, effort_bl,
    spo2_data, global_spo2_bl, existing_events,
    apply_spo2_crosscontam_fix: bool = True,
    desat_pct: float = 3.0,
    contam_win_s: float = 15.0,
    post_event_win_s: float = 45,
    max_dur_s: float = HYPOPNEA_MAX_DUR_S,
    ecg_data=None, tecg=None, r_peaks=None, sf_ecg=None,
) -> tuple[list[dict], list[dict]]:
    """Return (all_events_including_new_hypopneas, rejected_candidates)."""
    # Build apnea exclusion mask (±5 s around each confirmed apnea)
    excl = np.zeros(len(hypop_norm), dtype=bool)
    for ev in existing_events:
        margin  = int(5 * sf_hy)
        eo      = int(ev["onset_s"] * sf_hy)
        ee      = int((ev["onset_s"] + ev["duration_s"]) * sf_hy)
        excl[max(0, eo - margin) : min(len(excl), ee + margin)] = True

    labeled, n_hy = label(hypopnea_raw & sleep_mask_hy & ~excl)
    new_events = list(existing_events)
    rejected:  list[dict] = []
    slices_hy = find_objects(labeled)

    for i, sl in enumerate(slices_hy):
        if sl is None:
            continue
        sl0  = sl[0]
        idx  = np.where(labeled[sl0] == (i + 1))[0] + sl0.start
        dur_s = len(idx) / sf_hy
        if dur_s < HYPOPNEA_MIN_DUR_S:
            continue

        # v0.8.22: split events die te lang zijn
        sub_regions = _split_long_region(idx, hypop_env, sf_hy, max_dur_s, HYPOPNEA_MIN_DUR_S)
        for sub_idx in sub_regions:
            sub_dur   = len(sub_idx) / sf_hy
            onset_s   = sub_idx[0] / sf_hy
            ep_idx    = int(onset_s // EPOCH_LEN_S)
            stage     = hypno[ep_idx] if ep_idx < len(hypno) else "W"
            pre_bl    = _pre_event_baseline(hypop_env, sub_idx[0], sf_hy, hypop_baseline)
            flow_mean = float(np.mean(hypop_env[sub_idx[0] : sub_idx[-1] + 1]))
            flow_red  = safe_r((1 - flow_mean / pre_bl) * 100) if pre_bl > 0 else None

            # v0.8.22: Lokale basislijn-validatie — vergelijk met directe
            # pre-event ademhaling. Voorkomt false positives door opgeblazen
            # rollende basislijn (post-apnea recovery hyperpnea).
            local_valid, local_red = _validate_local_reduction(
                hypop_env, sub_idx[0], sub_idx[-1] + 1, sf_hy)
            if not local_valid:
                rejected.append({
                    "onset_s":    safe_r(onset_s),
                    "duration_s": safe_r(sub_dur),
                    "stage":      stage,
                    "desat":      None,
                    "min_spo2":   None,
                    "indices":    (sub_idx[0], sub_idx[-1] + 1),
                    "epoch":      ep_idx,
                    "reject_reason": f"local_reduction_{local_red}pct<20pct",
                })
                continue

            # Fix 2 — SpO2 kruiscontaminatie (v0.8.14: flag only, niet blokkeren)
            contaminated = (
                apply_spo2_crosscontam_fix
                and contam_win_s > 0 and _spo2_cross_contaminated(onset_s, new_events, post_event_window_s=contam_win_s)
            )
            desat, min_spo2 = get_desaturation(
                spo2_data, onset_s, sub_dur, sf_spo2, global_spo2_bl,
                post_win_s=post_event_win_s,
            )
            rule1a = desat is not None and desat >= desat_pct

            if not rule1a:
                rejected.append({
                    "onset_s":    safe_r(onset_s),
                    "duration_s": safe_r(sub_dur),
                    "stage":      stage,
                    "desat":      desat,
                    "min_spo2":   min_spo2,
                    "indices":    (sub_idx[0], sub_idx[-1] + 1),
                    "epoch":      ep_idx,
                })
                continue

            # Subtype classification
            if sf_hy != sf_flow:
                hy_oi = int(onset_s * sf_flow)
                hy_ei = int((onset_s + sub_dur) * sf_flow)
            else:
                hy_oi, hy_ei = sub_idx[0], sub_idx[-1] + 1

            hy_sub, hy_conf, hy_det = classify_apnea_type(
                onset_idx=hy_oi, end_idx=hy_ei,
                thorax_env=thorax_env, abdomen_env=abdomen_env,
                thorax_raw=thorax_raw, abdomen_raw=abdomen_raw,
                effort_baseline=effort_bl, sf=sf_flow,
                ecg_assessment=_get_ecg_assessment(
                    ecg_data, tecg, r_peaks, thorax_raw, abdomen_raw,
                    sf_flow, sf_ecg or sf_flow, hy_oi, hy_ei
                ) if tecg is not None else None,
            )
            hy_label = f"hypopnea_{hy_sub}" if hy_sub != "obstructive" else "hypopnea"
            flow_red_ratio = safe_r(
                1.0 - float(np.mean(hypop_norm[sub_idx[0] : sub_idx[-1] + 1])), 3
            )
            new_events.append({
                "type":                   hy_label,
                "onset_s":                safe_r(onset_s),
                "duration_s":             safe_r(sub_dur),
                "stage":                  stage,
                "desaturation_pct":       desat,
                "min_spo2":               min_spo2,
                "flow_reduction":         flow_red_ratio,
                "flow_reduction_pct":     flow_red,
                "pre_baseline":           safe_r(pre_bl, 2),
                "confidence":             hy_conf,
                "classify_detail":        hy_det,
                "epoch":                  ep_idx,
                "spo2_cross_contaminated": contaminated,
            })

    return new_events, rejected


def _pre_event_baseline(
    env: np.ndarray,
    onset_idx: int,
    sf: float,
    fallback_bl: np.ndarray,
) -> float:
    """
    Geef de lokale basislijn op het tijdstip van het event.

    Gebruikt een directe opzoeking in de voorberekende dynamische basislijn
    (O(1)) in plaats van een apart percentiel over een 120s venster per event.
    De dynamische basislijn is al berekend met een 5 min glijdend venster en
    95e percentiel, wat nauwkeuriger is dan een eenvoudige 75e percentiel over
    120 s.
    """
    if np.ndim(fallback_bl) > 0 and onset_idx < len(fallback_bl):
        val = float(fallback_bl[onset_idx])
        return max(val, 1e-6)
    return float(fallback_bl) if np.ndim(fallback_bl) == 0 else 1.0


def _validate_local_reduction(
    env: np.ndarray,
    event_start: int,
    event_end: int,
    sf: float,
    min_reduction_pct: float = 20.0,
    pre_win_s: float = 30.0,
) -> tuple[bool, float]:
    """v0.8.22: Valideer dat een event een echte flow-reductie toont t.o.v.
    de directe pre-event ademhaling (zoals een menselijke scorer doet).

    Vergelijkt de gemiddelde flow-envelope tijdens het event met de gemiddelde
    flow-envelope in een venster vlak vóór het event. Als het verschil
    < min_reduction_pct is, is de "reductie" een artefact van een opgeblazen
    rollende basislijn (bv. door post-apnea recovery hyperpnea).

    Parameters
    ----------
    env : np.ndarray         Flow-envelope
    event_start, event_end : int  Sample-indices van het event
    sf : float               Samplerate
    min_reduction_pct : float  Minimale reductie (default 20%)
    pre_win_s : float        Pre-event venster in seconden (default 30s)

    Returns
    -------
    (is_valid, local_reduction_pct)
    """
    pre_samples = int(pre_win_s * sf)
    pre_start   = max(0, event_start - pre_samples)

    # Minimaal 3s pre-event signaal nodig
    if event_start - pre_start < int(3 * sf):
        return True, 100.0   # te weinig data → niet afwijzen

    pre_seg   = env[pre_start:event_start]
    event_seg = env[event_start:event_end]

    if len(pre_seg) == 0 or len(event_seg) == 0:
        return True, 100.0

    pre_mean   = float(np.mean(pre_seg))
    event_mean = float(np.mean(event_seg))

    if pre_mean < 1e-9:
        return True, 100.0   # pre-event ook plat → niet afwijzen

    local_reduction = (1.0 - event_mean / pre_mean) * 100.0
    return local_reduction >= min_reduction_pct, safe_r(local_reduction)


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def _compute_summary(
    events: list,
    hypno: list,
    artifact_epochs: list | None = None,
    csr_info: dict | None = None,
) -> dict:
    """Compute all AHI-family indices from the event list."""
    artifact_set  = set(artifact_epochs or [])
    total_sleep_s = sum(
        EPOCH_LEN_S for i, s in enumerate(hypno)
        if s != "W" and i not in artifact_set
    )
    total_sleep_h = max(total_sleep_s / 3600, 0.001)
    rem_h  = max(sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                     if is_rem(s) and i not in artifact_set) / 3600, 0.001)
    nrem_h = max(sum(EPOCH_LEN_S for i, s in enumerate(hypno)
                     if is_nrem(s) and i not in artifact_set) / 3600, 0.001)

    apneas    = [e for e in events if e["type"] in ("obstructive", "central", "mixed")]
    hypopneas = [e for e in events if "hypopnea" in e["type"]]
    obstr     = [e for e in events if e["type"] == "obstructive"]
    central   = [e for e in events if e["type"] == "central"]
    mixed     = [e for e in events if e["type"] == "mixed"]

    def idx(n, h):
        """Bereken index (events/uur) met veilige deling."""
        return safe_r(n / h) if h > 0 else 0

    def split_rn(lst):
        """Splits events in REM- en NREM-subgroepen."""
        return (
            [e for e in lst if is_rem(e["stage"])],
            [e for e in lst if is_nrem(e["stage"])],
        )

    obstr_r,   obstr_n   = split_rn(obstr)
    central_r, central_n = split_rn(central)
    mixed_r,   mixed_n   = split_rn(mixed)
    hyp_r,     hyp_n     = split_rn(hypopneas)

    ahi        = idx(len(apneas) + len(hypopneas), total_sleep_h)
    confs      = [e.get("confidence", 0.5) for e in apneas if e.get("confidence")]
    avg_conf   = safe_r(float(np.mean(confs))) if confs else None

    # ── Confidence-gestratificeerde OAHI (conf > 0.60) ─────────────────
    # OAHI_CONF60 is de officiële OAHI: enkel obstructieve apneas + hypopneas
    # met betrouwbaarheid > 0.60. Dit is de klinisch relevante index.
    # oahi_all = alle events ongeacht confidence (voor vergelijking).
    # Hypopneas krijgen altijd conf=0.70 (gescoord op desaturatie, Rule 1A)
    # en tellen dus altijd mee.
    CONF_THRESHOLD = 0.60
    obstr_conf = [e for e in obstr     if (e.get("confidence") or 0) >  CONF_THRESHOLD]
    hyp_conf   = [e for e in hypopneas if (e.get("confidence") or 0) >= CONF_THRESHOLD]
    oahi_conf60 = idx(len(obstr_conf) + len(hyp_conf), total_sleep_h)
    oahi_all    = idx(len(obstr) + len(hypopneas), total_sleep_h)

    # Confidence-verdeling per categorie (apneas only; hypopneas fixed at 0.70)
    def _conf_band(events_list):
        """Tel events per confidence-band (hoog/matig/grens/laag)."""
        bands = {"high": 0, "moderate": 0, "borderline": 0, "low": 0}
        for e in events_list:
            c = e.get("confidence") or 0
            if   c >= 0.85: bands["high"]       += 1
            elif c >= 0.60: bands["moderate"]   += 1
            elif c >= 0.40: bands["borderline"] += 1
            else:           bands["low"]        += 1
        return bands

    conf_bands = _conf_band(apneas)

    # OAHI per drempel (voor drempelgevoeligheidstabel in rapport)
    def _oahi_at(threshold):
        """Bereken OAHI bij een gegeven confidence-drempel."""
        ob = [e for e in obstr     if (e.get("confidence") or 0) >  threshold]
        hy = [e for e in hypopneas if (e.get("confidence") or 0) >= threshold]
        return idx(len(ob) + len(hy), total_sleep_h)

    oahi_thresholds = {
        "0.85": _oahi_at(0.85),   # alleen hoge zekerheid
        "0.60": oahi_conf60,       # officieel (matige + hoge zekerheid)
        "0.40": _oahi_at(0.40),   # incl. grensgebied
        "0.00": oahi_all,          # alle events
    }

    return {
        "n_obstructive":   len(obstr),
        "n_central":       len(central),
        "n_mixed":         len(mixed),
        "n_apnea_total":   len(apneas),
        "n_hypopnea":      len(hypopneas),
        "n_hypopnea_obstr":  len([e for e in hypopneas if e["type"] == "hypopnea"]),
        "n_hypopnea_central": len([e for e in hypopneas if e["type"] == "hypopnea_central"]),
        "n_hypopnea_mixed":  len([e for e in hypopneas if e["type"] == "hypopnea_mixed"]),
        "n_ah_total":      len(apneas) + len(hypopneas),

        "ahi_total":       ahi,
        "oahi":            oahi_all,      # officieel: ALLE obstructief + hypopneas (AASM-conform)
        "oahi_conf60":     oahi_conf60,   # supplementair: enkel conf > 0.60 (informatief)
        "oahi_all":        oahi_all,      # alias voor backward compat
        "oahi_thresholds": oahi_thresholds,  # {"0.85":x, "0.60":x, "0.40":x, "0.00":x}
        "ahi_rem":         idx(len([e for e in events if is_rem(e["stage"])]),  rem_h),
        "ahi_nrem":        idx(len([e for e in events if is_nrem(e["stage"])]), nrem_h),
        "obstructive_index": idx(len(obstr),   total_sleep_h),
        "central_index":   idx(len(central),   total_sleep_h),
        "mixed_index":     idx(len(mixed),     total_sleep_h),
        "hypopnea_index":  idx(len(hypopneas), total_sleep_h),

        "obstructive_rem":  len(obstr_r),   "obstructive_nrem": len(obstr_n),
        "central_rem":      len(central_r), "central_nrem":     len(central_n),
        "mixed_rem":        len(mixed_r),   "mixed_nrem":       len(mixed_n),
        "hypopnea_rem":     len(hyp_r),     "hypopnea_nrem":    len(hyp_n),

        "max_apnea_dur_s":
            safe_r(max((e["duration_s"] for e in apneas), default=0)),
        "avg_apnea_dur_s":
            safe_r(float(np.mean([e["duration_s"] for e in apneas]))) if apneas else None,
        "max_hypopnea_dur_s":
            safe_r(max((e["duration_s"] for e in hypopneas), default=0)),
        "avg_hypopnea_dur_s":
            safe_r(float(np.mean([e["duration_s"] for e in hypopneas]))) if hypopneas else None,

        "avg_desaturation": safe_r(float(np.mean([
            e["desaturation_pct"] for e in events
            if e.get("desaturation_pct") is not None
        ]))) if any(e.get("desaturation_pct") for e in events) else None,

        "avg_classification_confidence": avg_conf,
        "n_low_confidence": sum(
            1 for e in apneas if (e.get("confidence") or 1) < 0.5
        ),
        "confidence_bands": conf_bands,  # {"high":N, "moderate":N, "borderline":N, "low":N}

        "severity":       _classify_ahi(ahi),
        "oahi_severity":  _classify_ahi(idx(len(obstr) + len(hypopneas), total_sleep_h)),

        "tst_hours":   safe_r(total_sleep_h),
        "tst_minutes": safe_r(total_sleep_s / 60),
        "n_artifact_epochs_excluded": len(artifact_set),

        # ── Overschatting-correctie indices (v0.8.11) ──────────────────
        # Fix 2: SpO₂ kruiscontaminatie
        "n_spo2_cross_contaminated": sum(
            1 for e in events if e.get("spo2_cross_contaminated")
        ),
        # Fix 3: CSR-gerelateerde events
        "n_csr_flagged": sum(1 for e in events if e.get("csr_flagged")),
        "ahi_csr_corrected": idx(
            len([e for e in events if not e.get("csr_flagged")]),
            total_sleep_h,
        ),
        "oahi_csr_corrected": idx(
            len([e for e in (obstr + hypopneas) if not e.get("csr_flagged")]),
            total_sleep_h,
        ),
        # Fix 4: Lage confidence (borderline default obstructief)
        "n_low_conf_borderline": sum(
            1 for e in apneas if 0.40 <= (e.get("confidence") or 0) < 0.60
        ),
        "n_low_conf_noise": sum(
            1 for e in apneas if (e.get("confidence") or 0) < 0.40
        ),
        "ahi_excl_noise": idx(
            len([e for e in events if (e.get("confidence") or 1) >= 0.40]),
            total_sleep_h,
        ),

        "warnings": _generate_warnings(
            len(central), len(obstr), len(mixed), ahi, avg_conf, total_sleep_h
        ),
    }


def _classify_ahi(ahi: float | None) -> str:
    """Classificeer AHI-ernst: normaal (<5), licht (5-15), matig (15-30), ernstig (>30)."""
    if ahi is None:
        return "unknown"
    if ahi < 5:   return "normal"
    if ahi < 15:  return "mild"
    if ahi < 30:  return "moderate"
    return "severe"


def _generate_warnings(
    n_central, n_obstr, n_mixed, ahi, avg_conf, sleep_h
) -> list[dict]:
    """Genereer klinische waarschuwingen op basis van event-patronen en AHI-ernst."""
    warnings: list[dict] = []
    total_ap = n_central + n_obstr + n_mixed

    if total_ap > 0:
        central_pct = n_central / total_ap * 100
        if central_pct > 50:
            warnings.append({
                "level": "warning", "code": "CENTRAL_DOMINANT",
                "msg": (
                    f"Central apneas predominate ({central_pct:.0f}%). "
                    "Consider CSA / Cheyne-Stokes. Cardiology / neurology workup recommended."
                ),
            })
        elif central_pct > 25:
            warnings.append({
                "level": "info", "code": "CENTRAL_SIGNIFICANT",
                "msg": (
                    f"Significant central apneas ({central_pct:.0f}%). "
                    "nCPAP may worsen centrals — consider ASV."
                ),
            })

    if n_mixed > 5:
        warnings.append({
            "level": "info", "code": "MIXED_APNEAS",
            "msg": (
                f"{n_mixed} mixed apneas. Classic pattern in severe OSAS. "
                "Good CPAP response expected."
            ),
        })

    if avg_conf is not None and avg_conf < 0.5:
        warnings.append({
            "level": "warning", "code": "LOW_CONFIDENCE",
            "msg": (
                "Low classification confidence. Possible causes: poor effort-signal quality, "
                "movement artefacts, or missing thorax/abdomen channels. Manual review advised."
            ),
        })

    if sleep_h < 2:
        warnings.append({
            "level": "warning", "code": "SHORT_SLEEP",
            "msg": f"Short sleep time ({sleep_h:.1f} h). AHI estimate less reliable.",
        })

    return warnings
