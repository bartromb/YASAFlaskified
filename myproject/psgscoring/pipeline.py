"""
psgscoring.pipeline
===================
MNE-facing master function that orchestrates the full pneumological analysis
on a single EDF recording.

This is the only module that imports MNE.  All signal-processing modules
below it work exclusively with NumPy arrays and sample rates.

Call graph
----------
run_pneumo_analysis
  ├─ utils.channel_map_from_user
  ├─ respiratory.detect_respiratory_events
  ├─ spo2.analyze_spo2
  ├─ ancillary.analyze_position / heart_rate / snore / detect_cheyne_stokes
  ├─ plm.analyze_plm
  ├─ [arousal_analysis.run_arousal_respiratory_analysis]   <- optional
  └─ respiratory.reinstate_rule1b_hypopneas
"""

from __future__ import annotations
import logging

import numpy as np

try:
    import mne
    _MNE_AVAILABLE = True
except ImportError:
    _MNE_AVAILABLE = False

from .utils import channel_map_from_user
from .signal import (
    compute_dynamic_baseline, preprocess_flow,
)
from .respiratory import (
    detect_respiratory_events, reinstate_rule1b_hypopneas, _compute_summary,
)
from .spo2 import analyze_spo2
from .ancillary import (
    analyze_position, analyze_heart_rate, analyze_snore, detect_cheyne_stokes,
)
from .plm import analyze_plm

# Optional arousal module (part of YASAFlaskified; not required for standalone use)
try:
    from arousal_analysis import run_arousal_respiratory_analysis
    _AROUSAL_AVAILABLE = True
except ImportError:
    _AROUSAL_AVAILABLE = False

logger = logging.getLogger("psgscoring.pipeline")


def run_pneumo_analysis(
    raw,                                 # mne.io.BaseRaw
    hypno: list,
    channel_map: dict | None = None,
    artifact_epochs: list | None = None,
) -> dict:
    """
    Run the full pneumological analysis on a single PSG recording.

    Parameters
    ----------
    raw             : MNE Raw object (EDF already loaded)
    hypno           : string hypnogram list ['W','N1','N2','N3','R',...]
    channel_map     : optional manual channel overrides (UI selection)
    artifact_epochs : list of epoch indices with artefacts (from YASA)

    Returns
    -------
    Nested dict with keys: meta, channel_availability, respiratory, spo2,
    position, heart_rate, snore, plm, arousal, cheyne_stokes.
    """
    ch = channel_map_from_user(channel_map, raw.ch_names)

    output: dict = {
        "meta": {
            "channels_used": ch,
            "all_channels":  raw.ch_names,
            "sfreq":         raw.info["sfreq"],
            "duration_min":  round(raw.times[-1] / 60, 1),
        },
        "channel_availability": {k: (v in raw.ch_names) for k, v in ch.items()},
    }

    def get(ch_type):
        name = ch.get(ch_type)
        if name and name in raw.ch_names:
            return raw.get_data(picks=[name])[0], raw.info["sfreq"]
        return None, None

    # ── Flow channels ──────────────────────────────────────────────────────
    flow_data,          sf_flow  = get("flow")
    flow_pressure_data, sf_fp    = get("flow_pressure")
    flow_therm_data,    sf_ft    = get("flow_thermistor")

    apnea_flow, hypop_flow, sf_apnea, sf_hypop = _resolve_flow_channels(
        flow_data, sf_flow,
        flow_pressure_data, sf_fp,
        flow_therm_data, sf_ft,
        ch, output,
    )

    # ── Other channels ─────────────────────────────────────────────────────
    thorax_data,  _        = get("thorax")
    abdomen_data, _        = get("abdomen")
    spo2_data,    sf_spo2  = get("spo2")
    pulse_data,   sf_pulse = get("pulse")
    pos_data,     sf_pos   = get("position")
    snore_data,   sf_snore = get("snore")
    leg_l_data,   sf_leg   = get("leg_l")
    leg_r_data,   _        = get("leg_r")

    eeg_data, sf_eeg = _pick_eeg(raw, ch)
    emg_data         = _pick_emg(raw, ch)

    # ── Step 1: Respiratory events ─────────────────────────────────────────
    logger.info("[pneumo 1/9] Apnea / hypopnea detection (AASM 2.6)...")
    if apnea_flow is not None:
        resp = detect_respiratory_events(
            flow_data    = apnea_flow,
            hypop_flow   = hypop_flow,
            sf_hypop     = sf_hypop,
            thorax_data  = thorax_data,
            abdomen_data = abdomen_data,
            spo2_data    = spo2_data,
            sf_flow      = sf_apnea,
            sf_spo2      = sf_spo2 or sf_flow or 1.0,
            hypno        = hypno,
            artifact_epochs = artifact_epochs,
            pos_data     = pos_data,
            sf_pos       = sf_pos,
        )
    else:
        resp = {
            "success": False,
            "error":   "No flow channel found",
            "events":  [], "summary": {},
        }
    output["respiratory"] = resp

    # ── Step 1b (v0.8.11): Baseline Anchoring ─────────────────────────────
    if apnea_flow is not None:
        try:
            from .signal import preprocess_flow as _pf, compute_anchor_baseline
            _anchor_env = _pf(apnea_flow, sf_apnea, is_nasal_pressure=False)
            anchor_info = compute_anchor_baseline(
                _anchor_env, sf_apnea, hypno,
                events=resp.get("events", []),
                artifact_epochs=artifact_epochs,
            )
            output["anchor_baseline"] = anchor_info
            if anchor_info.get("mouth_breathing_suspected"):
                logger.warning(
                    "Mond-ademen verdacht: anchor_ratio=%.2f — hypopnea-confidence mogelijk verlaagd",
                    anchor_info.get("anchor_ratio", 0),
                )
        except Exception as e:
            logger.debug("Anchor baseline failed: %s", e)
            output["anchor_baseline"] = {"anchor_reliable": False}
    else:
        output["anchor_baseline"] = {"anchor_reliable": False}

    # ── Step 2: SpO2 ───────────────────────────────────────────────────────
    logger.info("[pneumo 2/9] SpO2 analysis...")
    output["spo2"] = (
        analyze_spo2(spo2_data, sf_spo2, hypno)
        if spo2_data is not None
        else {"success": False, "error": "No SpO2 channel", "summary": {}}
    )

    # ── Step 3: Position ───────────────────────────────────────────────────
    logger.info("[pneumo 3/9] Position analysis...")
    output["position"] = (
        analyze_position(pos_data, sf_pos, hypno, resp.get("events", []))
        if pos_data is not None
        else {"success": False, "error": "No position channel", "summary": {}}
    )

    # ── Step 4: Heart rate ─────────────────────────────────────────────────
    logger.info("[pneumo 4/9] Heart rate...")
    hr_data, sf_hr = (pulse_data, sf_pulse) if pulse_data is not None else get("ecg")
    output["heart_rate"] = (
        analyze_heart_rate(hr_data, sf_hr, hypno)
        if hr_data is not None
        else {"success": False, "error": "No HR/ECG channel", "summary": {}}
    )

    # ── Step 5: Snore ──────────────────────────────────────────────────────
    logger.info("[pneumo 5/9] Snore analysis...")
    output["snore"] = (
        analyze_snore(snore_data, sf_snore, hypno)
        if snore_data is not None
        else {"success": False, "error": "No snore channel", "summary": {}}
    )

    # ── Step 6: PLM ────────────────────────────────────────────────────────
    logger.info("[pneumo 6/9] PLM detection...")
    if leg_l_data is not None or leg_r_data is not None:
        output["plm"] = analyze_plm(
            leg_l_data, leg_r_data,
            sf_leg or raw.info["sfreq"], hypno,
            resp_events=resp.get("events", []),
            artifact_epochs=artifact_epochs,
        )
    else:
        output["plm"] = {"success": False, "error": "No leg-EMG channels", "summary": {}}

    # ── Step 7: Arousal detection ──────────────────────────────────────────
    logger.info("[pneumo 7/9] Arousal detection & respiratory coupling...")
    if eeg_data is not None and _AROUSAL_AVAILABLE:
        flow_env_norm = _compute_flow_norm(apnea_flow, sf_apnea)
        output["arousal"] = run_arousal_respiratory_analysis(
            eeg_data    = eeg_data,
            sf_eeg      = sf_eeg,
            flow_data   = apnea_flow,
            flow_norm   = flow_env_norm,
            sf_flow     = sf_apnea,
            resp_events = resp.get("events", []),
            hypno       = hypno,
            emg_data    = emg_data,
            artifact_epochs = artifact_epochs,
            hr_data     = hr_data,
            sf_hr       = sf_hr or 1.0,
        )
    else:
        reason = "No EEG channel" if eeg_data is None else "arousal_analysis not loaded"
        output["arousal"] = _empty_arousal(reason)

    # ── Step 8: Rule 1B reinstatement ─────────────────────────────────────
    logger.info("[pneumo 8/9] Rule 1B reinstatement...")
    rejected  = resp.get("rejected_hypopneas", [])
    arousals  = output.get("arousal", {}).get("events", [])
    if rejected and arousals:
        reinstated, updated_events = reinstate_rule1b_hypopneas(
            rejected       = rejected,
            arousal_events = arousals,
            resp_events    = resp.get("events", []),
            hypno          = hypno,
            breaths        = resp.get("_breaths", []),
        )
        if reinstated:
            logger.info("[pneumo 8] Rule 1B: %d hypopneas reinstated", len(reinstated))
            output["respiratory"]["events"]           = updated_events
            output["respiratory"]["summary"]          = _compute_summary(
                updated_events, hypno, artifact_epochs
            )
            output["respiratory"]["rule1b_reinstated"] = len(reinstated)
    else:
        output["respiratory"].setdefault("rule1b_reinstated", 0)

    # ── Step 9: Cheyne-Stokes ──────────────────────────────────────────────
    logger.info("[pneumo 9/9] Cheyne-Stokes detection...")
    if apnea_flow is not None:
        try:
            flow_env_csr = preprocess_flow(apnea_flow, sf_apnea)
            output["cheyne_stokes"] = detect_cheyne_stokes(
                flow_env_csr, sf_apnea, hypno
            )
        except Exception as e:
            logger.warning("CSR detection failed: %s", e)
            output["cheyne_stokes"] = {"success": False, "csr_detected": False, "error": str(e)}
    else:
        output["cheyne_stokes"] = {"success": False, "csr_detected": False}

    # ── Fix 3: Retroactief CSR-event markering na CSR-detectie ────────────
    csr_info = output.get("cheyne_stokes", {})
    if csr_info.get("csr_detected") and output["respiratory"].get("success"):
        from .respiratory import _flag_csr_events, _compute_summary
        events_flagged = _flag_csr_events(
            output["respiratory"]["events"], csr_info
        )
        output["respiratory"]["events"] = events_flagged
        # Herbereken summary met CSR-info
        artifact_epochs_for_summary = output["respiratory"]["summary"].get(
            "_artifact_epochs", None
        )
        output["respiratory"]["summary"] = _compute_summary(
            events_flagged,
            hypno,
            artifact_epochs,
            csr_info=csr_info,
        )
        n_flagged = sum(1 for e in events_flagged if e.get("csr_flagged"))
        logger.info("Fix3 (pipeline): %d events gemarkeerd als CSR-gerelateerd", n_flagged)

    logger.info("Pneumo analysis complete.")
    return output


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_flow_channels(
    flow_data, sf_flow,
    flow_pressure_data, sf_fp,
    flow_therm_data, sf_ft,
    ch, output,
):
    """Assign apnea (thermistor) and hypopnea (pressure) channels per AASM 2.6."""
    if flow_pressure_data is not None or flow_therm_data is not None:
        apnea_flow = flow_therm_data   or flow_pressure_data or flow_data
        hypop_flow = flow_pressure_data or flow_therm_data   or flow_data
        sf_apnea   = sf_ft if flow_therm_data  is not None else (sf_fp or sf_flow)
        sf_hypop   = sf_fp if flow_pressure_data is not None else (sf_ft or sf_flow)
        if flow_data is None:
            flow_data = flow_pressure_data or flow_therm_data
        output["meta"]["flow_channels"] = {
            "apnea_sensor":    ch.get("flow_thermistor")  or ch.get("flow_pressure") or ch.get("flow"),
            "hypopnea_sensor": ch.get("flow_pressure") or ch.get("flow_thermistor") or ch.get("flow"),
            "dual_sensor":     flow_pressure_data is not None and flow_therm_data is not None,
        }
    else:
        apnea_flow = flow_data
        hypop_flow = flow_data
        sf_apnea   = sf_flow
        sf_hypop   = sf_flow
        output["meta"]["flow_channels"] = {
            "apnea_sensor":    ch.get("flow", "-"),
            "hypopnea_sensor": ch.get("flow", "-"),
            "dual_sensor":     False,
        }
    return apnea_flow, hypop_flow, sf_apnea, sf_hypop


def _pick_eeg(raw, ch) -> tuple:
    name = ch.get("eeg")
    if not name:
        for c in raw.ch_names:
            if any(p in c.upper() for p in ("EEG", "C3", "C4", "F3", "F4", "CZ")):
                name = c
                break
    if name and name in raw.ch_names:
        return raw.get_data(picks=[name])[0], raw.info["sfreq"]
    return None, None


def _pick_emg(raw, ch) -> np.ndarray | None:
    name = ch.get("emg")
    if not name:
        for c in raw.ch_names:
            if any(p in c.upper() for p in ("EMG", "CHIN", "MENT")):
                name = c
                break
    if name and name in raw.ch_names:
        return raw.get_data(picks=[name])[0]
    return None


def _compute_flow_norm(flow_data, sf_flow) -> np.ndarray | None:
    if flow_data is None:
        return None
    try:
        env = preprocess_flow(flow_data, sf_flow)
        bl  = compute_dynamic_baseline(env, sf_flow)
        return np.clip(env / bl, 0, 2)
    except Exception:
        return None


def _empty_arousal(reason: str) -> dict:
    return {
        "success": False,
        "error":   reason,
        "summary": {
            "arousal_index": None,
            "n_respiratory_arousals": None,
            "n_spontaneous_arousals": None,
            "pct_respiratory_arousals": None,
            "n_reras": 0,
            "rera_index": 0,
            "rdi": None,
            "clinical_interpretation": [],
        },
    }
