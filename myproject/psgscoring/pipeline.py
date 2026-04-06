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
    scoring_profile: str = "standard",
) -> dict:
    """
    Run the full pneumological analysis on a single PSG recording.

    Parameters
    ----------
    raw             : MNE Raw object (EDF already loaded)
    hypno           : string hypnogram list ['W','N1','N2','N3','R',...]
    channel_map     : optional manual channel overrides (UI selection)
    artifact_epochs : list of epoch indices with artefacts (from YASA)
    scoring_profile : 'strict', 'standard', or 'sensitive'

    Returns
    -------
    Nested dict with keys: meta, channel_availability, respiratory, spo2,
    position, heart_rate, snore, plm, arousal, cheyne_stokes.
    """
    from .constants import SCORING_PROFILES
    profile = SCORING_PROFILES.get(scoring_profile, SCORING_PROFILES["standard"])
    logger.info("[pneumo] Scoring profile: %s (%s)", scoring_profile, profile["label"])

    ch = channel_map_from_user(channel_map, raw.ch_names)

    output: dict = {
        "meta": {
            "channels_used": ch,
            "all_channels":  raw.ch_names,
            "sfreq":         raw.info["sfreq"],
            "duration_min":  round(raw.times[-1] / 60, 1),
            "scoring_profile": scoring_profile,
            "scoring_label":   profile["label"],
            "patient_info":  _parse_edf_patient_info(raw),
        },
        "channel_availability": {k: (v in raw.ch_names) for k, v in ch.items()},
    }

    def get(ch_type):
        """Haal een kanaal op uit de MNE raw data op basis van de kanaalmap."""
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
    # Extract ECG for effort-based apnea type classification (v0.8.23)
    ecg_data_resp, sf_ecg_resp = get("ecg")
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
            scoring_profile = profile,
            ecg_data     = ecg_data_resp,
            sf_ecg       = sf_ecg_resp,
        )
    else:
        resp = {
            "success": False,
            "error":   "No flow channel found",
            "events":  [], "summary": {},
        }
    output["respiratory"] = resp

    # ── Step 1b (v0.8.16): Signal quality assessment ─────────────────────
    logger.info("[pneumo 1b/11] Signal quality assessment...")
    try:
        from .signal_quality import assess_signal_quality
        output["signal_quality"] = assess_signal_quality(raw, ch, hypno)
        sq = output["signal_quality"]
        if sq.get("montage_warnings"):
            for w in sq["montage_warnings"]:
                logger.warning("[quality] MONTAGE: %s", w)
        if sq.get("overall_grade") == "poor":
            logger.warning("[quality] Overall signal quality: POOR")
    except Exception as e:
        logger.warning("Signal quality assessment failed: %s", e)
        output["signal_quality"] = {"overall_grade": "unknown", "error": str(e)}

    # ── Step 1c (v0.8.11): Baseline Anchoring ─────────────────────────────
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
    logger.info("[pneumo 2/11] SpO2 analysis...")
    if spo2_data is not None:
        output["spo2"] = analyze_spo2(spo2_data, sf_spo2, hypno)
        # v0.8.16: SpO2 samplerate check (AASM: max 3s averaging)
        if sf_spo2 is not None and sf_spo2 < 0.33:
            output["spo2"]["spo2_low_samplerate"] = True
            logger.warning("[pneumo] SpO2 samplerate %.2f Hz < 0.33 Hz "
                           "(>3s averaging — may underestimate ODI)", sf_spo2)
        output["spo2"]["spo2_samplerate"] = sf_spo2
    else:
        output["spo2"] = {"success": False, "error": "No SpO2 channel", "summary": {}}

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
    logger.info("[pneumo 8/10] Rule 1B reinstatement...")
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

    # ── Step 8b (v0.8.16): RERA index and RDI ─────────────────────────────
    logger.info("[pneumo 8b/10] RERA and RDI computation...")
    _compute_rera_rdi(output, hypno, arousals, artifact_epochs)

    # ── Step 9: Cheyne-Stokes ──────────────────────────────────────────────
    logger.info("[pneumo 9/10] Cheyne-Stokes detection...")
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
        # v0.8.4 FIX: Python 'or' crashes on numpy arrays ("truth value ambiguous").
        # Use explicit None-checks instead.
        apnea_flow = (flow_therm_data if flow_therm_data is not None
                       else flow_pressure_data if flow_pressure_data is not None
                       else flow_data)
        hypop_flow = (flow_pressure_data if flow_pressure_data is not None
                       else flow_therm_data if flow_therm_data is not None
                       else flow_data)
        sf_apnea   = sf_ft if flow_therm_data  is not None else (sf_fp or sf_flow)
        sf_hypop   = sf_fp if flow_pressure_data is not None else (sf_ft or sf_flow)
        if flow_data is None:
            flow_data = (flow_pressure_data if flow_pressure_data is not None
                         else flow_therm_data)
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
    """Selecteer het beste EEG-kanaal uit de beschikbare kanalen."""
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
    """Selecteer het beste EMG-kanaal (kin-EMG) uit de beschikbare kanalen."""
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
    """Normaliseer het flowsignaal voor amplitude-onafhankelijke analyse."""
    if flow_data is None:
        return None
    try:
        env = preprocess_flow(flow_data, sf_flow)
        bl  = compute_dynamic_baseline(env, sf_flow)
        return np.clip(env / bl, 0, 2)
    except Exception:
        return None


def _compute_rera_rdi(output: dict, hypno: list, arousals: list,
                      artifact_epochs: list | None = None) -> None:
    """Compute RERA index and RDI from FRI events + flattening + arousal coupling.

    Two RERA sources (v0.8.16):
      1. **FRI-RERA**: Flow-reduction events (≥30% amplitude drop, no ≥3% desat,
         not reinstated by Rule 1B) WITH arousal within 15s. These are the
         "classical" psgscoring RERAs from v0.8.16.
      2. **Flattening-RERA** (NEW): Breath sequences with flattening index >0.30
         (Hosselet et al., AJRCCM 1998), duration ≥10s, WITHOUT amplitude
         reduction meeting hypopnea threshold, terminated by arousal.
         These represent true upper-airway flow limitation — the "missing"
         RERA type that amplitude-only analysis cannot detect.

    RDI = AHI + RERA index.
    """
    resp = output.get("respiratory", {})
    if not resp.get("success"):
        return

    # ── Source 1: FRI-based RERAs (amplitude reduction + arousal) ──────
    rejected  = resp.get("rejected_hypopneas", [])
    events = resp.get("events", [])
    event_onsets = {round(float(e["onset_s"]), 1) for e in events}
    fri_events = [r for r in rejected
                  if round(float(r["onset_s"]), 1) not in event_onsets]

    fri_rera_count = 0
    if arousals and fri_events:
        arousal_times = [(float(a.get("onset_s", 0)), float(a.get("duration_s", 3)))
                         for a in arousals]
        for fri in fri_events:
            fri_end = float(fri["onset_s"]) + float(fri["duration_s"])
            has_arousal = any(
                fri["onset_s"] <= a_onset <= fri_end + 15.0
                for a_onset, _ in arousal_times
            )
            if has_arousal:
                fri_rera_count += 1

    # ── Source 2: Flattening-based RERAs (flow limitation + arousal) ───
    flat_rera_count = 0
    breaths = resp.get("_breaths", [])
    if arousals and breaths:
        arousal_times = [(float(a.get("onset_s", 0)), float(a.get("duration_s", 3)))
                         for a in arousals]
        flat_seqs = _find_flattening_sequences(breaths)
        for seq in flat_seqs:
            seq_end = seq["onset_s"] + seq["duration_s"]
            # Check arousal within 15s of sequence end
            has_arousal = any(
                seq["onset_s"] <= a_onset <= seq_end + 15.0
                for a_onset, _ in arousal_times
            )
            # Exclude sequences already counted as respiratory events or FRI
            overlaps_event = any(
                abs(float(e["onset_s"]) - seq["onset_s"]) < 5.0
                for e in events
            )
            overlaps_fri = any(
                abs(float(f["onset_s"]) - seq["onset_s"]) < 5.0
                for f in fri_events
            )
            if has_arousal and not overlaps_event and not overlaps_fri:
                flat_rera_count += 1

    rera_count = fri_rera_count + flat_rera_count

    # ── TST and indices ────────────────────────────────────────────────
    from .constants import EPOCH_LEN_S
    sleep_stages = {"N1", "N2", "N3", "R"}
    art_set = set(artifact_epochs or [])
    n_sleep = sum(1 for i, s in enumerate(hypno)
                  if s in sleep_stages and i not in art_set)
    tst_h = max(n_sleep * EPOCH_LEN_S / 3600, 0.001)

    ahi = float(resp.get("summary", {}).get("ahi_total", 0) or 0)
    rera_index = round(rera_count / tst_h, 1)
    rdi = round(ahi + rera_index, 1)

    # Store in respiratory summary
    resp["summary"]["n_rera"]          = rera_count
    resp["summary"]["n_rera_fri"]      = fri_rera_count
    resp["summary"]["n_rera_flattening"] = flat_rera_count
    resp["summary"]["rera_index"]      = rera_index
    resp["summary"]["rdi"]             = rdi
    resp["summary"]["n_fri"]           = len(fri_events) - fri_rera_count

    # REM vs NREM AHI (v0.8.16)
    rem_events  = [e for e in events if e.get("stage") == "R"]
    nrem_events = [e for e in events if e.get("stage") in {"N1","N2","N3"}]
    n_rem  = sum(1 for i, s in enumerate(hypno) if s == "R" and i not in art_set)
    n_nrem = sum(1 for i, s in enumerate(hypno) if s in {"N1","N2","N3"} and i not in art_set)
    rem_h  = max(n_rem * EPOCH_LEN_S / 3600, 0.001)
    nrem_h = max(n_nrem * EPOCH_LEN_S / 3600, 0.001)
    resp["summary"]["rem_ahi"]  = round(len(rem_events) / rem_h, 1) if n_rem > 0 else None
    resp["summary"]["nrem_ahi"] = round(len(nrem_events) / nrem_h, 1) if n_nrem > 0 else None

    logger.info("[pneumo] RERA: %d (FRI:%d + flattening:%d), index %.1f/h; "
                "RDI: %.1f/h; REM-AHI: %s, NREM-AHI: %s",
                rera_count, fri_rera_count, flat_rera_count,
                rera_index, rdi,
                resp["summary"]["rem_ahi"], resp["summary"]["nrem_ahi"])


def _find_flattening_sequences(breaths: list,
                                min_flat_index: float = 0.30,
                                min_dur_s: float = 10.0,
                                min_consecutive: int = 3) -> list:
    """Find consecutive breath sequences with elevated flattening index.

    AASM: flow limitation = inspiratory flattening ≥10s.
    Hosselet et al.: flattening index >0.30 indicates plateau.

    Parameters
    ----------
    breaths : list of breath dicts with 'flattening', 'onset_s', 'duration_s'
    min_flat_index : threshold for flattening (0.30 = plateau)
    min_dur_s : minimum sequence duration (AASM: ≥10s)
    min_consecutive : minimum consecutive flat breaths

    Returns
    -------
    list of {onset_s, duration_s, avg_flattening, n_breaths}
    """
    sequences = []
    run_start = None
    run_breaths = []

    for b in breaths:
        fi = b.get("flattening")
        if fi is not None and fi >= min_flat_index:
            if run_start is None:
                run_start = float(b["onset_s"])
            run_breaths.append(b)
        else:
            # End of run — check if it qualifies
            if run_breaths and len(run_breaths) >= min_consecutive:
                last = run_breaths[-1]
                dur = float(last["onset_s"]) + float(last["duration_s"]) - run_start
                if dur >= min_dur_s:
                    sequences.append({
                        "onset_s": run_start,
                        "duration_s": round(dur, 1),
                        "avg_flattening": round(float(np.mean([
                            b["flattening"] for b in run_breaths
                            if b.get("flattening") is not None
                        ])), 3),
                        "n_breaths": len(run_breaths),
                    })
            run_start = None
            run_breaths = []

    # Handle trailing run
    if run_breaths and len(run_breaths) >= min_consecutive:
        last = run_breaths[-1]
        dur = float(last["onset_s"]) + float(last["duration_s"]) - run_start
        if dur >= min_dur_s:
            sequences.append({
                "onset_s": run_start,
                "duration_s": round(dur, 1),
                "avg_flattening": round(float(np.mean([
                    b["flattening"] for b in run_breaths
                    if b.get("flattening") is not None
                ])), 3),
                "n_breaths": len(run_breaths),
            })

    return sequences


def _parse_edf_patient_info(raw) -> dict:
    """Extract patient info from EDF/EDF+ header via MNE Raw object.

    EDF+ Patient ID (80 bytes at offset 8):
      patient_code  sex  birthdate  patient_name
      e.g.: "MCH-0234567 F 02-MAY-1951 Haagse_Harry"

    EDF+ Recording ID (80 bytes at offset 88):
      Startdate dd-MMM-yyyy admincode techniciancode equipmentcode

    Fields NOT in EDF: weight, height, BMI (require manual entry).
    """
    from datetime import datetime

    info = {
        "patient_code": None, "sex": None, "birthdate": None,
        "birthday_str": None, "name": None, "recording_date": None,
        "admin_code": None, "technician": None, "equipment": None,
    }

    # Get file path from MNE raw
    fpath = None
    if hasattr(raw, "filenames") and raw.filenames:
        fpath = raw.filenames[0]
    elif hasattr(raw, "_filenames") and raw._filenames:
        fpath = raw._filenames[0]
    if not fpath:
        return info

    try:
        with open(fpath, "rb") as f:
            f.seek(8)
            patient_raw = f.read(80).decode("latin-1").strip()
            recording_raw = f.read(80).decode("latin-1").strip()
    except (OSError, UnicodeDecodeError):
        return info

    # Parse EDF+ patient ID
    parts = patient_raw.split()
    if len(parts) >= 4:
        info["patient_code"] = parts[0] if parts[0] != "X" else None
        info["sex"] = parts[1] if parts[1] in ("M", "F") else None
        if parts[2] != "X":
            try:
                info["birthdate"] = datetime.strptime(parts[2], "%d-%b-%Y").isoformat()
                info["birthday_str"] = parts[2]
            except ValueError:
                info["birthday_str"] = parts[2]
        name_parts = parts[3:]
        raw_name = " ".join(name_parts).replace("_", " ")
        info["name"] = raw_name if raw_name and raw_name != "X" else None
    elif len(parts) >= 1 and patient_raw and patient_raw != "X":
        info["name"] = patient_raw.replace("_", " ")

    # Parse EDF+ recording ID
    rparts = recording_raw.split()
    if len(rparts) >= 2 and rparts[0] == "Startdate":
        try:
            info["recording_date"] = datetime.strptime(rparts[1], "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
        if len(rparts) >= 3:
            info["admin_code"] = rparts[2] if rparts[2] != "X" else None
        if len(rparts) >= 4:
            info["technician"] = rparts[3].replace("_", " ") if rparts[3] != "X" else None
        if len(rparts) >= 5:
            info["equipment"] = rparts[4].replace("_", " ") if rparts[4] != "X" else None

    logger.info("[pneumo] EDF patient: %s, sex=%s, dob=%s, equipment=%s",
                info.get("name"), info.get("sex"),
                info.get("birthday_str"), info.get("equipment"))
    return info


def _empty_arousal(reason: str) -> dict:
    """Geeft een leeg arousal-resultaat terug met foutmelding."""
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
