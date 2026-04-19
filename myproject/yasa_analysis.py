"""
yasa_analysis.py — Uitgebreide slaapanalyse module voor YASAFlaskified v0.8.37
Compatibel met YASA 0.7.x (Hypnogram object) EN 0.6.x (numpy array).

Fixes t.o.v. v7.1:
  - hypno.tolist() → _hypno_to_list() helper voor YASA 0.7 Hypnogram object
  - run_full_analysis() gaat door met fallback indien staging mislukt
  - set_channel_types() voor EOG/EMG zodat YASA ze correct herkent
  - predict_proba() deprecated in 0.7 → probeer hypno.proba
"""

import numpy as np
import pandas as pd
import yasa
import mne
import traceback
import logging
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger("yasaflaskified")

# Mapping string → integer slaapstadia (YASA/AASM conventie)
_STAGE_TO_INT = {"W": 0, "N1": 1, "N2": 2, "N3": 3, "R": 4}


def _hypno_str_to_int(hypno_str: list) -> np.ndarray:
    """
    Converteer lijst van strings ['W','N1','N2','N3','R'] naar
    integer array [0,1,2,3,4] voor YASA detectiefuncties.

    YASA 0.7 functies (spindles_detect, sw_detect, bandpower)
    verwachten integer-hypnogrammen bij include=(1,2) etc.

    v0.8.40: Onbekende stadia (bv. 'ART', 'UNS', 'MVT') worden nog
    steeds naar W (0) gemapt voor backward compatibility, maar er
    wordt nu een warning gelogd zodat silent miscounts zichtbaar zijn.
    """
    unknown = Counter(s for s in hypno_str if s not in _STAGE_TO_INT)
    if unknown:
        logger.warning(
            "Hypnogram bevat %d onbekende stadia (gemapt naar W): %s",
            sum(unknown.values()),
            dict(unknown.most_common(5))
        )
    return np.array([_STAGE_TO_INT.get(s, 0) for s in hypno_str])


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def safe_round(val, decimals=2):
    """Veilig afronden — ook als val None of NaN is."""
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return round(float(val), decimals)
    except Exception:
        return None


def series_to_dict(series):
    """Converteer pandas Series naar JSON-serialiseerbaar dict."""
    return {k: safe_round(v) for k, v in series.items()}


def _hypno_to_list(hypno) -> list:
    """
    Converteer YASA hypnogram naar lijst van strings.
    Werkt met YASA 0.6 (numpy array) en YASA 0.7+ (Hypnogram object).

    YASA 0.7 .hypno.tolist() geeft lange namen: 'WAKE','N1','N2','N3','REM'.
    We normaliseren naar korte namen: 'W','N1','N2','N3','R'.

    LET OP: NIET itereren over het Hypnogram object zelf (for s in hypno)
    — dit hangt in YASA 0.7!  Altijd via .hypno attribuut.
    """
    _LONG_TO_SHORT = {"WAKE": "W", "REM": "R", "ART": "W", "UNS": "W",
                      "W": "W", "N1": "N1", "N2": "N2", "N3": "N3", "R": "R"}

    if hypno is None:
        return []

    # YASA 0.7+: Hypnogram object — gebruik .hypno (pandas Series)
    if hasattr(hypno, 'hypno'):
        try:
            raw_list = hypno.hypno.tolist()
            return [_LONG_TO_SHORT.get(s, "W") for s in raw_list]
        except Exception:
            pass

    # YASA 0.6: numpy array van strings
    if hasattr(hypno, 'tolist'):
        raw_list = hypno.tolist()
        return [_LONG_TO_SHORT.get(s, s) for s in raw_list]

    # Fallback: al een gewone lijst
    if isinstance(hypno, list):
        return [_LONG_TO_SHORT.get(s, s) for s in hypno]

    return []


def _get_confidence(sls_obj) -> dict:
    """Haal confidence scores op — compatibel met YASA 0.6 en 0.7."""
    try:
        # YASA 0.7: hypno.proba (via predict() return value)
        hypno_obj = sls_obj._last_hypno if hasattr(sls_obj, '_last_hypno') else None
        if hypno_obj is not None and hasattr(hypno_obj, 'proba'):
            proba = hypno_obj.proba
            return {col: [safe_round(v) for v in proba[col].tolist()]
                    for col in proba.columns}
    except Exception:
        pass

    try:
        # YASA 0.6: predict_proba() (deprecated in 0.7)
        confidence = sls_obj.predict_proba()
        return {col: [safe_round(v) for v in confidence[col].tolist()]
                for col in confidence.columns}
    except Exception:
        pass

    return {}


# ─────────────────────────────────────────────
# 1. SLEEP STAGING
# ─────────────────────────────────────────────

def run_sleep_staging(raw: mne.io.BaseRaw,
                      eeg_ch: str,
                      eog_ch: str = None,
                      emg_ch: str = None,
                      backend: str = "yasa") -> dict:
    """
    Automatische slaapfase-indeling via YASA SleepStaging of U-Sleep.

    Parameters
    ----------
    backend : str
        "yasa" (default) — YASA LightGBM staging
        "usleep" — U-Sleep deep learning staging (requires usleep package)
        "both" — run both and return comparison in result["staging_comparison"]

    Compatibel met YASA 0.6 en 0.7.
    """
    if backend == "usleep":
        return _run_usleep_staging(raw, eeg_ch, eog_ch)
    elif backend == "both":
        yasa_result = run_sleep_staging(raw, eeg_ch, eog_ch, emg_ch, backend="yasa")
        try:
            usleep_result = _run_usleep_staging(raw, eeg_ch, eog_ch)
            if yasa_result["success"] and usleep_result["success"]:
                from validation_metrics import compute_staging_metrics
                comp = compute_staging_metrics(
                    yasa_result["hypnogram"], usleep_result["hypnogram"])
                yasa_result["staging_comparison"] = {
                    "usleep_hypnogram": usleep_result["hypnogram"],
                    "agreement": comp,
                }
        except Exception as e:
            logger.warning("U-Sleep comparison failed: %s", e)
            yasa_result["staging_comparison"] = {"error": str(e)}
        return yasa_result
    # Default: YASA
    result = {"success": False, "hypnogram": [], "confidence": {}, "error": None}
    try:
        raw_stag = raw.copy()

        # Zet kanaaltypes correct zodat YASA EOG/EMG herkent
        ch_types = {}
        if eog_ch and eog_ch in raw_stag.ch_names:
            ch_types[eog_ch] = "eog"
        if emg_ch and emg_ch in raw_stag.ch_names:
            ch_types[emg_ch] = "emg"
        if ch_types:
            raw_stag.set_channel_types(ch_types)

        logger.info("SleepStaging starten: EEG=%s EOG=%s EMG=%s", eeg_ch, eog_ch, emg_ch)
        sls   = yasa.SleepStaging(raw_stag,
                                   eeg_name=eeg_ch,
                                   eog_name=eog_ch,
                                   emg_name=emg_ch)
        hypno = sls.predict()
        logger.info("predict() geslaagd, type=%s", type(hypno).__name__)

        # Converteer naar lijst van strings
        hypno_list = _hypno_to_list(hypno)
        logger.info("Hypnogram: %d epochs, stadia=%s",
                    len(hypno_list), dict(Counter(hypno_list)))

        # Confidence scores
        result["confidence"] = _get_confidence(sls)

        result["hypnogram"] = hypno_list
        result["n_epochs"]  = len(hypno_list)
        result["success"]   = True

    except Exception as e:
        logger.error("Staging fout: %s\n%s", e, traceback.format_exc())
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 2. SLEEP STATISTICS
# ─────────────────────────────────────────────

def run_sleep_statistics(hypno: list, sf_hypno: float = 1/30) -> dict:
    """
    Volledige slaapstatistieken conform AASM-normen.
    """
    result = {"success": False, "stats": {}, "error": None}
    try:
        hypno_int = _hypno_str_to_int(hypno)
        logger.info("sleep_statistics: %d epochs, uniek=%s", len(hypno_int), np.unique(hypno_int).tolist())
        # YASA 0.7: parameter heet 'sf_hyp', YASA 0.6: 'sf_hypno'
        try:
            stats = yasa.sleep_statistics(hypno_int, sf_hyp=sf_hypno)
        except TypeError:
            stats = yasa.sleep_statistics(hypno_int, sf_hypno=sf_hypno)
        logger.info("sleep_statistics keys: %s", list(stats.keys()))
        result["stats"] = {k: safe_round(v) for k, v in stats.items()}

        n_epochs = len(hypno)
        result["stats"]["TRT_min"]      = safe_round(n_epochs * 0.5)
        result["stats"]["n_epochs_total"] = n_epochs

        counts = Counter(hypno)
        stage_map = {"W": "Wake", "N1": "N1", "N2": "N2", "N3": "N3", "R": "REM"}
        result["stage_counts"] = {stage_map.get(k, k): int(v) for k, v in counts.items()}
        result["success"] = True

    except Exception as e:
        logger.error("sleep_statistics FOUT: %s\n%s", e, traceback.format_exc())
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 3. SPINDLE DETECTIE
# ─────────────────────────────────────────────

def run_spindle_detection(raw: mne.io.BaseRaw, hypno: list,
                           eeg_channels: list,
                           freq_sp=(12, 15),
                           duration=(0.5, 2.0),
                           min_distance=500) -> dict:
    """Detecteer slaapspoelen per EEG-kanaal."""
    result = {"success": False, "spindles": [], "summary": [], "error": None}
    try:
        data     = raw.get_data(picks=eeg_channels, units="uV")
        sf       = raw.info["sfreq"]
        hypno_up = yasa.hypno_upsample_to_data(
            _hypno_str_to_int(hypno), sf_hypno=1/30, data=data, sf_data=sf)

        sp = yasa.spindles_detect(
            data=data, sf=sf, ch_names=eeg_channels,
            hypno=hypno_up, include=(1, 2),
            freq_sp=freq_sp, duration=duration, min_distance=min_distance,
        )

        if sp is not None:
            df = sp.summary(grp_chan=False, grp_stage=False)
            result["spindles"]       = df.to_dict(orient="records") if len(df) else []
            result["summary"]        = sp.summary(grp_chan=True, grp_stage=False).to_dict(orient="records")
            result["total_spindles"] = len(df)
        else:
            result["spindles"] = []
            result["summary"]  = []
            result["total_spindles"] = 0

        result["success"] = True
    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 4. SLOW-WAVE DETECTIE
# ─────────────────────────────────────────────

def run_sw_detection(raw: mne.io.BaseRaw, hypno: list,
                     eeg_channels: list,
                     freq_sw=(0.3, 1.5),
                     dur_neg=(0.3, 1.5),
                     dur_pos=(0.1, 1.0)) -> dict:
    """Detecteer trage golven in N3."""
    result = {"success": False, "slow_waves": [], "summary": [], "error": None}
    try:
        data     = raw.get_data(picks=eeg_channels, units="uV")
        sf       = raw.info["sfreq"]
        hypno_up = yasa.hypno_upsample_to_data(
            _hypno_str_to_int(hypno), sf_hypno=1/30, data=data, sf_data=sf)

        sw = yasa.sw_detect(
            data=data, sf=sf, ch_names=eeg_channels,
            hypno=hypno_up, include=(3,),
            freq_sw=freq_sw, dur_neg=dur_neg, dur_pos=dur_pos,
        )

        if sw is not None:
            df = sw.summary(grp_chan=False, grp_stage=False)
            result["slow_waves"]       = df.to_dict(orient="records") if len(df) else []
            result["summary"]          = sw.summary(grp_chan=True, grp_stage=False).to_dict(orient="records")
            result["total_slow_waves"] = len(df)
        else:
            result["slow_waves"]       = []
            result["summary"]          = []
            result["total_slow_waves"] = 0

        result["success"] = True
    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 5. REM DETECTIE
# ─────────────────────────────────────────────

def run_rem_detection(raw: mne.io.BaseRaw, hypno: list,
                      eog_channel: str,
                      eeg_channel: str = None,
                      gap_tolerance: int = 4) -> dict:
    """Detecteer REM-episodes en oogbewegingen (v0.8.22: geconsolideerd).

    gap_tolerance : int
        Max epochs N1/W die een REM-periode niet onderbreken (default 4 = 2 min).
    """
    result = {"success": False, "rem_events": [], "summary": {}, "transitions": [], "error": None}
    try:
        hypno_arr    = np.array(hypno)
        rem_mask     = hypno_arr == "R"
        n_rem_epochs = int(np.sum(rem_mask))
        n = len(hypno_arr)

        # ── Geconsolideerde REM-perioden (v0.8.22) ──────────────
        rem_durations = []
        i = 0
        while i < n:
            if hypno_arr[i] == "R":
                start = i
                end = i
                while end < n - 1:
                    if hypno_arr[end + 1] == "R":
                        end += 1
                    else:
                        gap = 0
                        j = end + 1
                        while j < n and hypno_arr[j] != "R" and gap < gap_tolerance:
                            gap += 1
                            j += 1
                        if j < n and hypno_arr[j] == "R" and gap <= gap_tolerance:
                            end = j
                        else:
                            break
                rem_durations.append((end - start + 1) * 0.5)
                i = end + 1
            else:
                i += 1

        # NREM→REM transities
        transitions = []
        for i in range(1, len(hypno_arr)):
            if hypno_arr[i - 1] != "R" and hypno_arr[i] == "R":
                transitions.append({
                    "epoch": i,
                    "from_stage": hypno_arr[i - 1],
                    "to_REM_min": safe_round(i * 0.5),
                })

        result["summary"] = {
            "n_rem_epochs":          n_rem_epochs,
            "rem_duration_min":      safe_round(n_rem_epochs * 0.5),
            "n_rem_periods":         len(rem_durations),
            "mean_rem_period_min":   safe_round(np.mean(rem_durations)) if rem_durations else None,
            "longest_rem_period_min": safe_round(max(rem_durations)) if rem_durations else None,
        }
        result["transitions"] = transitions
        result["success"]     = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 6. BANDVERMOGEN ANALYSE
# ─────────────────────────────────────────────

BANDS = {
    "delta": (0.5, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "sigma": (12, 16),
    "beta":  (16, 30),
    "gamma": (30, 50),
}


def run_bandpower(raw: mne.io.BaseRaw, hypno: list,
                  eeg_channels: list) -> dict:
    """Spectrale vermogensdichtheid per band, per fase."""
    result = {"success": False, "per_epoch": [], "per_stage": {}, "band_ratios": {}, "error": None}
    try:
        data     = raw.get_data(picks=eeg_channels, units="uV")
        sf       = raw.info["sfreq"]
        hypno_int = _hypno_str_to_int(hypno)
        hypno_up = yasa.hypno_upsample_to_data(
            hypno_int, sf_hypno=1/30, data=data, sf_data=sf)

        # YASA 0.7: bands als lijst van (lo, hi, label) tuples
        bands_tuples = [(lo, hi, name) for name, (lo, hi) in BANDS.items()]

        bp = yasa.bandpower(
            data=data, sf=sf, ch_names=eeg_channels,
            hypno=hypno_up, include=(0, 1, 2, 3, 4),
            bands=bands_tuples,
            relative=True,
        )

        # Map integer stages terug naar string labels voor output
        _INT_TO_STAGE = {0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "R"}
        if "Stage" in bp.columns:
            bp["Stage"] = bp["Stage"].map(lambda x: _INT_TO_STAGE.get(x, str(x)))

        per_stage = bp.groupby("Stage")[list(BANDS.keys())].mean()
        result["per_stage"] = {
            stage: series_to_dict(row)
            for stage, row in per_stage.iterrows()
        }

        avg = bp[list(BANDS.keys())].mean()
        # v0.8.40: Guard tegen KeyError bij lege/corrupte bandpower data
        if avg.empty or avg.isna().all():
            logger.warning("Bandpower: geen geldige epochs — band_ratios=None")
            result["band_ratios"] = {
                "delta_theta": None,
                "theta_alpha": None,
                "sigma_delta": None,
            }
        else:
            result["band_ratios"] = {
                "delta_theta": safe_round(avg["delta"] / avg["theta"]) if avg.get("theta", 0) > 0 else None,
                "theta_alpha": safe_round(avg["theta"] / avg["alpha"]) if avg.get("alpha", 0) > 0 else None,
                "sigma_delta": safe_round(avg["sigma"] / avg["delta"]) if avg.get("delta", 0) > 0 else None,
            }
        result["per_epoch"] = bp.reset_index().to_dict(orient="records")[:500]
        result["success"]   = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 7. SLAAPCYCLI DETECTIE
# ─────────────────────────────────────────────

def run_sleep_cycles(hypno: list,
                     min_nrem_epochs: int = 30,
                     rem_gap_tolerance: int = 4) -> dict:
    """Identificeer NREM/REM-cycli (v0.8.22 — Feinberg & Floyd criteria).

    Parameters
    ----------
    min_nrem_epochs : int
        Minimaal aantal NREM-epochs (excl. W) om als NREM-periode te tellen.
        Default 30 = 15 min.
    rem_gap_tolerance : int
        Maximaal aantal N1/W-epochs die een REM-periode niet onderbreken.
        Default 4 = 2 min (korte arousal / N1 tijdens REM).
    """
    result = {"success": False, "cycles": [], "n_cycles": 0, "error": None}
    try:
        hypno_arr = np.array(hypno)
        n = len(hypno_arr)

        # ── Stap 1: Consolideer REM-blokken ──────────────────────
        # Merge aaneengesloten REM-epochs, met tolerantie voor korte
        # N1/W onderbrekingen (≤ rem_gap_tolerance epochs).
        is_rem_arr = (hypno_arr == "R")
        rem_blocks = []  # [(start, end), ...]
        i = 0
        while i < n:
            if is_rem_arr[i]:
                start = i
                end = i
                while end < n - 1:
                    if is_rem_arr[end + 1]:
                        end += 1
                    else:
                        # Kijk of er binnen gap_tolerance weer REM komt
                        gap = 0
                        j = end + 1
                        while j < n and not is_rem_arr[j] and gap < rem_gap_tolerance:
                            gap += 1
                            j += 1
                        if j < n and is_rem_arr[j] and gap <= rem_gap_tolerance:
                            end = j
                        else:
                            break
                rem_blocks.append((start, end))
                i = end + 1
            else:
                i += 1

        # ── Stap 2: Bouw cycli (NREM-periode → REM-blok) ─────────
        cycles = []
        cycle_num = 1
        nrem_start = None
        # Zoek het eerste slaap-epoch als NREM-start
        for idx, s in enumerate(hypno_arr):
            if s in ("N1", "N2", "N3"):
                nrem_start = idx
                break

        if nrem_start is None:
            result["cycles"] = []
            result["n_cycles"] = 0
            result["success"] = True
            return result

        for rb_start, rb_end in rem_blocks:
            if nrem_start is None or rb_start <= nrem_start:
                continue

            # Tel NREM-epochs in het segment vóór dit REM-blok
            seg = hypno_arr[nrem_start:rb_start]
            n_nrem = int(np.sum((seg == "N1") | (seg == "N2") | (seg == "N3")))

            if n_nrem < min_nrem_epochs:
                # Te kort NREM — geen echte cyclus, skip dit REM-blok
                continue

            # Cyclus gevonden
            cycle_seg = hypno_arr[nrem_start:rb_end + 1]
            counts = Counter(cycle_seg.tolist())
            duration_min = safe_round(len(cycle_seg) * 0.5)
            cycles.append({
                "cycle":      cycle_num,
                "start_epoch": nrem_start,
                "end_epoch":   rb_end,
                "duration_min": duration_min,
                "stage_distribution": {
                    k: safe_round(v / len(cycle_seg) * 100)
                    for k, v in counts.items()
                },
            })
            cycle_num += 1
            # Volgende NREM-start = eerste NREM na dit REM-blok
            nrem_start = None
            for idx in range(rb_end + 1, n):
                if hypno_arr[idx] in ("N1", "N2", "N3"):
                    nrem_start = idx
                    break

        result["cycles"]   = cycles
        result["n_cycles"] = len(cycles)
        result["success"]  = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 8. ARTEFACTDETECTIE
# ─────────────────────────────────────────────

def run_artifact_detection(raw: mne.io.BaseRaw, eeg_channels: list) -> dict:
    """Basisartefactdetectie: hoge amplitude, platte segmenten."""
    result = {"success": False, "artifact_epochs": [], "summary": {}, "error": None}
    try:
        data      = raw.get_data(picks=eeg_channels, units="uV")
        sf        = raw.info["sfreq"]
        epoch_len = int(30 * sf)
        n_epochs  = data.shape[1] // epoch_len

        artifact_flags = []
        for ep in range(n_epochs):
            seg      = data[:, ep * epoch_len:(ep + 1) * epoch_len]
            amp_max  = float(np.max(np.abs(seg)))
            is_flat  = bool(np.max(np.abs(np.diff(seg, axis=1))) < 0.5)
            is_high  = amp_max > 500
            artifact_flags.append({
                "epoch":            ep,
                "max_amplitude_uV": safe_round(amp_max),
                "flat_signal":      is_flat,
                "high_amplitude":   is_high,
                "artifact":         is_flat or is_high,
            })

        n_artifacts = sum(1 for f in artifact_flags if f["artifact"])
        result["artifact_epochs"] = [f for f in artifact_flags if f["artifact"]]
        result["summary"] = {
            "n_total_epochs":   n_epochs,
            "n_artifact_epochs": n_artifacts,
            "artifact_percent": safe_round(n_artifacts / n_epochs * 100) if n_epochs > 0 else 0,
        }
        result["success"] = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# 9. HYPNOGRAM TIJDLIJN
# ─────────────────────────────────────────────

def build_hypnogram_timeline(hypno: list, recording_start: str = None) -> dict:
    """Tijdlijn met absolute tijden per epoch."""
    result = {"success": False, "timeline": [], "error": None}
    try:
        try:
            start_dt = (datetime.fromisoformat(recording_start)
                        if recording_start else datetime(2000, 1, 1, 22, 0))
        except Exception:
            start_dt = datetime(2000, 1, 1, 22, 0)

        stage_colors = {
            "W": "#e74c3c", "N1": "#f39c12", "N2": "#3498db",
            "N3": "#2c3e50", "R": "#9b59b6",
        }
        timeline = []
        for i, stage in enumerate(hypno):
            epoch_start = start_dt + timedelta(seconds=i * 30)
            timeline.append({
                "epoch":    i,
                "stage":    stage,
                "time":     epoch_start.strftime("%H:%M:%S"),
                "time_min": safe_round(i * 0.5),
                "color":    stage_colors.get(stage, "#95a5a6"),
            })

        result["timeline"] = timeline
        result["success"]  = True

    except Exception as e:
        result["error"]     = str(e)
        result["traceback"] = traceback.format_exc()
    return result


# ─────────────────────────────────────────────
# MASTER FUNCTIE
# ─────────────────────────────────────────────

def run_full_analysis(raw: mne.io.BaseRaw,
                      eeg_ch: str,
                      eog_ch: str = None,
                      emg_ch: str = None,
                      all_eeg_channels: list = None,
                      recording_start: str = None,
                      prefetched_hypno: list = None) -> dict:
    """
    Voert alle beschikbare analyses uit op één EDF-opname.

    Parameters
    ----------
    raw              : geladen MNE raw object (analyse-raw met alle EEG kanalen)
    eeg_ch           : primair EEG-kanaal (bv. 'C3')
    eog_ch           : EOG-kanaal (bv. 'EOG1')
    emg_ch           : EMG-kanaal (optioneel)
    all_eeg_channels : alle EEG-kanalen voor spindle/SW/bandpower
    recording_start  : ISO-tijdstip opnamestart
    prefetched_hypno : reeds berekend hypnogram (overslaat staging in deze raw)
                       Gebruik dit wanneer staging al apart uitgevoerd werd
                       op een kleinere staging-raw (enkel EEG+EOG+EMG).
    """
    if all_eeg_channels is None:
        all_eeg_channels = [eeg_ch]

    # Filter kanalen die effectief aanwezig zijn
    available        = set(raw.ch_names)
    all_eeg_channels = [ch for ch in all_eeg_channels if ch in available]
    if not all_eeg_channels:
        all_eeg_channels = [eeg_ch]

    output = {
        "meta": {
            "eeg_channel":      eeg_ch,
            "eog_channel":      eog_ch,
            "emg_channel":      emg_ch,
            "all_eeg_channels": all_eeg_channels,
            "sfreq":            raw.info["sfreq"],
            "duration_min":     safe_round(raw.times[-1] / 60),
            "recording_start":  recording_start,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "yasa_version":     yasa.__version__,
        }
    }

    # ── 1. Slaapstaging ──────────────────────────────────────
    if prefetched_hypno is not None:
        # Staging al uitgevoerd op staging-raw — overslaan hier
        logger.info("[1/8] Slaapstaging... (overgeslagen — prefetched hypnogram gebruikt)")
        staging = {
            "success":   True,
            "hypnogram": prefetched_hypno,
            "n_epochs":  len(prefetched_hypno),
            "prefetched": True,
        }
        hypno = prefetched_hypno
    else:
        logger.info("[1/8] Slaapstaging...")
        staging = run_sleep_staging(raw, eeg_ch, eog_ch, emg_ch)
        hypno   = staging.get("hypnogram", [])
        if not hypno or not any(s != "W" for s in hypno):
            logger.warning(
                "Staging mislukt — fallback naar N2 hypnogram. "
                "Alle downstream metrics (AHI, arousal index, PLM) "
                "gebruiken een fictieve slaapstructuur; interpretatie "
                "moet voorzichtig zijn."
            )
            n_epochs = int(raw.times[-1] / 30)
            hypno    = ["N2"] * n_epochs
            staging["hypnogram"]      = hypno
            staging["fallback"]       = True
            staging["staging_failed"] = True   # v0.8.40: explicit flag
            staging["warning"] = (
                "Staging failed — N2 fallback used. "
                "Clinical interpretation requires manual verification."
            )

    output["staging"] = staging

    # ── 2. Slaapstatistieken ─────────────────────────────────
    logger.info("[2/8] Slaapstatistieken...")
    output["sleep_statistics"] = run_sleep_statistics(hypno)

    # ── 3. Spindle detectie ──────────────────────────────────
    logger.info("[3/8] Spindle detectie...")
    output["spindles"] = run_spindle_detection(raw, hypno, all_eeg_channels)

    # ── 4. Slow-wave detectie ────────────────────────────────
    logger.info("[4/8] Slow-wave detectie...")
    output["slow_waves"] = run_sw_detection(raw, hypno, all_eeg_channels)

    # ── 5. REM detectie ──────────────────────────────────────
    logger.info("[5/8] REM detectie...")
    eog_for_rem = eog_ch if eog_ch and eog_ch in available else all_eeg_channels[0]
    output["rem"] = run_rem_detection(raw, hypno, eog_for_rem, eeg_ch)

    # ── 6. Bandvermogen ──────────────────────────────────────
    logger.info("[6/8] Bandvermogen...")
    output["bandpower"] = run_bandpower(raw, hypno, all_eeg_channels)

    # ── 7. Slaapcycli ────────────────────────────────────────
    logger.info("[7/8] Slaapcycli...")
    output["sleep_cycles"] = run_sleep_cycles(hypno)

    # ── 8. Artefacten + tijdlijn ─────────────────────────────
    logger.info("[8/8] Artefacten & tijdlijn...")
    output["artifacts"]          = run_artifact_detection(raw, all_eeg_channels)
    output["hypnogram_timeline"] = build_hypnogram_timeline(hypno, recording_start)

    logger.info("✅ Alle analyses voltooid.")
    return output


# ═══════════════════════════════════════════════════════════════════════════
# v0.8.37: U-Sleep integration stub (Perslev et al., npj Digital Med 2021)
# ═══════════════════════════════════════════════════════════════════════════

def _run_usleep_staging(raw, eeg_ch: str, eog_ch: str = None) -> dict:
    """Run U-Sleep staging via the cloud API (sleep.ai.ku.dk).

    Requirements
    ------------
    1. pip install git+https://github.com/perslev/U-Sleep-API-Python-Bindings.git
    2. API token in environment: USLEEP_API_TOKEN=eyJ0eXAi...
       (create at https://sleep.ai.ku.dk)

    The function saves the raw to a temporary EDF, uploads it to the
    U-Sleep webserver, waits for the result, and returns the hypnogram
    in the same format as run_sleep_staging().
    """
    import os
    import tempfile

    result = {"success": False, "hypnogram": [], "confidence": {}, "error": None,
              "backend": "usleep"}

    api_token = os.environ.get("USLEEP_API_TOKEN")
    if not api_token:
        result["error"] = (
            "USLEEP_API_TOKEN not set. Create a free account at "
            "https://sleep.ai.ku.dk and add the token to your .env file."
        )
        return result

    try:
        from usleep_api import USleepAPI
    except ImportError:
        result["error"] = (
            "usleep-api not installed. Run:\n"
            "  pip install git+https://github.com/perslev/U-Sleep-API-Python-Bindings.git"
        )
        return result

    try:
        # ── Save raw to temporary EDF ────────────────────────────────
        with tempfile.NamedTemporaryFile(suffix=".edf", delete=False) as tmp:
            tmp_path = tmp.name
        raw.save(tmp_path, overwrite=True, verbose=False)
        logger.info("U-Sleep: saved temp EDF (%d channels, %.0f s)",
                     len(raw.ch_names), raw.times[-1])

        # ── Create API session ───────────────────────────────────────
        api = USleepAPI(api_token=api_token)
        session = api.new_session(session_name="yasaflaskified_staging")
        session.set_model("U-Sleep v1.0")

        # ── Upload EDF (anonymized) ──────────────────────────────────
        logger.info("U-Sleep: uploading EDF to sleep.ai.ku.dk ...")
        session.upload_file(tmp_path, anonymize_before_upload=True)

        # ── Define channel groups ────────────────────────────────────
        # U-Sleep works with pairs: [EEG, EOG] or just [EEG]
        channel_groups = []
        if eog_ch and eog_ch in raw.ch_names:
            channel_groups.append([eeg_ch, eog_ch])
        else:
            channel_groups.append([eeg_ch])

        # ── Run prediction ───────────────────────────────────────────
        logger.info("U-Sleep: predicting (channels: %s) ...", channel_groups)
        session.predict(
            data_per_prediction=128 * 30,  # 30s epochs at 128 Hz
            channel_groups=channel_groups,
        )

        success = session.wait_for_completion()
        if not success:
            result["error"] = "U-Sleep prediction failed on server"
            return result

        # ── Fetch hypnogram ──────────────────────────────────────────
        hyp_data = session.get_hypnogram()
        hypno_raw = hyp_data.get("hypnogram", [])

        # U-Sleep returns: 0=W, 1=N1, 2=N2, 3=N3, 4=REM
        stage_map = {0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "R"}
        hypno_list = [stage_map.get(int(s), "W") for s in hypno_raw]

        result["hypnogram"] = hypno_list
        result["n_epochs"] = len(hypno_list)
        result["success"] = True
        logger.info("U-Sleep: %d epochs scored, stages=%s",
                     len(hypno_list), dict(Counter(hypno_list)))

    except Exception as e:
        result["error"] = f"U-Sleep failed: {e}"
        logger.error("U-Sleep staging failed: %s", e, exc_info=True)
    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return result
