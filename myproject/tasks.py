"""
tasks.py — RQ worker voor YASAFlaskified v0.8.11
Integreert: YASA slaapanalyse + pneumologische scoring + PSG-rapport

Fixes t.o.v. v8.0:
  - STAGING gebruikt aparte raw met enkel EEG+EOG+EMG (3 kanalen max)
    YASA SleepStaging gebruikt intern enkel 1 EEG kanaal — extra kanalen
    in de raw vertragen de feature-berekening enorm (minuten ipv seconden)
  - ANALYSE gebruikt raw met alle extra EEG kanalen (spindles/bandpower)
  - PNEUMO gebruikt aparte raw met enkel respiratoire kanalen
  - Alle EDF-loads via exclude-parameter (geen resampling van onnodige kanalen)
  - prefetched_hypno parameter in run_full_analysis() om dubbele staging te vermijden
"""

import matplotlib
matplotlib.use("Agg")

import os
import json
import logging
import traceback
from datetime import datetime
from collections import Counter

import mne
import numpy as np
import pandas as pd

from yasa_analysis import run_sleep_staging, run_full_analysis
from pneumo_analysis import run_pneumo_analysis, detect_channels as pneumo_detect_channels
from generate_pdf_report import generate_pdf_report
from generate_excel_report import generate_excel_report
# from generate_psg_report import generate_psg_report  # PSG = PDF (portrait)
from generate_edfplus import generate_edfplus

logger = logging.getLogger("yasaflaskified.worker")
logging.basicConfig(
    force=True,
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

UPLOAD_FOLDER = os.environ.get(
    "YASAFLASKIFIED_UPLOAD_FOLDER",
    os.environ.get("UPLOAD_FOLDER", "/data/slaapkliniek/uploads")
)

# ── Redis voortgang ──────────────────────────────────────────
import redis as _redis
_progress_redis = None

def _get_progress_redis():
    global _progress_redis
    if _progress_redis is None:
        host = os.environ.get("YASAFLASKIFIED_REDIS_HOST", "redis")
        port = int(os.environ.get("YASAFLASKIFIED_REDIS_PORT", 6379))
        _progress_redis = _redis.Redis(host=host, port=port)
    return _progress_redis

def _set_progress(job_id: str, step: int, total: int, label: str):
    """Schrijf voortgang naar Redis zodat de frontend het kan tonen."""
    try:
        r = _get_progress_redis()
        r.hset(f"job:{job_id}:progress", mapping={
            "step": step, "total": total, "label": label
        })
        r.expire(f"job:{job_id}:progress", 3600)
    except Exception:
        pass  # niet-kritiek


# ─────────────────────────────────────────────
# EDF LADEN
# ─────────────────────────────────────────────

def _load_edf(edf_path: str, needed_channels: list,
              label: str = "EDF") -> mne.io.BaseRaw:
    """
    Laad EDF met enkel de benodigde kanalen via exclude-parameter.
    MNE leest uitgesloten kanalen nooit in en hersampled ze niet.
    """
    logger.info("[%s] laden: %s", label, needed_channels)
    try:
        raw_hdr   = mne.io.read_raw_edf(edf_path, preload=False, verbose=False)
        all_ch    = raw_hdr.ch_names
        available = set(all_ch)
        to_keep   = list(dict.fromkeys(
            ch for ch in needed_channels if ch and ch in available
        ))
        if not to_keep:
            raise ValueError(f"Geen kanalen gevonden van: {needed_channels[:5]}")
        to_exclude = [ch for ch in all_ch if ch not in set(to_keep)]
        logger.info("[%s] %d kanalen laden, %d uitsluiten",
                    label, len(to_keep), len(to_exclude))
        raw = mne.io.read_raw_edf(
            edf_path, exclude=to_exclude, preload=True, verbose=False)
        logger.info("[%s] geladen: sfreq=%.0f Hz", label, raw.info["sfreq"])
        return raw
    except Exception as e:
        logger.warning("[%s] mislukt (%s) — fallback: alles laden", label, e)
        return mne.io.read_raw_edf(edf_path, preload=True, verbose=False)


def _detect_pneumo_channels(edf_path: str, pneumo_channels: dict) -> list:
    """Detecteer respiratoire kanalen via header (geen data)."""
    try:
        raw_hdr  = mne.io.read_raw_edf(edf_path, preload=False, verbose=False)
        auto     = pneumo_detect_channels(raw_hdr.ch_names)
        merged   = {**auto, **{k: v for k, v in pneumo_channels.items() if v}}
        detected = list(dict.fromkeys(
            ch for ch in merged.values() if ch and ch in raw_hdr.ch_names
        ))
        logger.info("Pneumo kanalen: %s", detected)
        return detected
    except Exception as e:
        logger.warning("Pneumo detectie mislukt: %s", e)
        return []


# ─────────────────────────────────────────────
# HOOFD ANALYSETAAK
# ─────────────────────────────────────────────

def run_analysis_job(job_id: str) -> dict:
    """
    Volledige slaap + pneumo analyse pipeline.

    3-staps EDF-laadstrategie:
      raw_staging : EEG + EOG + EMG (3 kanalen) → YASA staging (snel!)
      raw_analyse : alle extra EEG kanalen       → spindles, SW, bandpower
      raw_pneumo  : respiratoire kanalen          → AHI, SpO2, PLM, snurk
    """
    started = datetime.utcnow()
    logger.info("▶ Job gestart: %s | UPLOAD_FOLDER: %s", job_id, UPLOAD_FOLDER)
    _set_progress(job_id, 1, 10, "Config laden...")

    # ── Config laden ──────────────────────────────────────────
    config_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config niet gevonden: {config_path}")

    with open(config_path) as f:
        cfg = json.load(f)

    edf_path        = cfg["edf_path"]
    eeg_ch          = cfg["eeg_ch"]
    eog_ch          = cfg.get("eog_ch")
    emg_ch          = cfg.get("emg_ch")
    extra_eeg       = cfg.get("extra_eeg_ch") or [eeg_ch]
    recording_start = cfg.get("recording_start")
    pneumo_channels = cfg.get("pneumo_channels", {})
    patient_info    = cfg.get("patient_info", {})

    logger.info("EEG=%s EOG=%s EMG=%s extra_eeg=%s",
                eeg_ch, eog_ch, emg_ch, extra_eeg)

    if not os.path.exists(edf_path):
        raise FileNotFoundError(f"EDF niet gevonden: {edf_path}")

    # ── Stap 1: Staging-raw laden (ENKEL primaire kanalen) ────
    _set_progress(job_id, 2, 10, "EDF laden voor staging...")
    staging_needed = list(dict.fromkeys(
        ch for ch in [eeg_ch, eog_ch, emg_ch] if ch
    ))
    logger.info("STAGING EDF laden (%d kanalen)...", len(staging_needed))
    raw_staging = _load_edf(edf_path, staging_needed, label="STAGING")

    # ── Stap 2: Staging uitvoeren (snel: 3 kanalen) ───────────
    _set_progress(job_id, 3, 10, "Slaapstaging (AI-model)...")
    logger.info("YASA staging starten...")
    staging_result = run_sleep_staging(raw_staging, eeg_ch, eog_ch, emg_ch)
    hypno          = staging_result.get("hypnogram", [])
    staging_ok     = bool(hypno) and any(s != "W" for s in hypno)

    if staging_ok:
        logger.info("Staging OK: %d epochs — %s",
                    len(hypno), dict(Counter(hypno)))
    else:
        logger.warning("Staging mislukt: %s — fallback N2", staging_result.get("error"))
        n_epochs = int(raw_staging.times[-1] / 30)
        hypno    = ["N2"] * n_epochs
        staging_result["hypnogram"] = hypno
        staging_result["fallback"]  = True

    # ── Stap 3: Analyse-raw laden (alle EEG kanalen) ──────────
    _set_progress(job_id, 4, 10, "EEG-kanalen laden voor analyse...")
    analyse_needed = list(dict.fromkeys(
        ch for ch in [eeg_ch, eog_ch, emg_ch] + extra_eeg if ch
    ))
    if set(analyse_needed) == set(staging_needed):
        logger.info("Analyse-raw = staging-raw")
        raw_analyse = raw_staging
    else:
        logger.info("ANALYSE EDF laden (%d kanalen)...", len(analyse_needed))
        raw_analyse = _load_edf(edf_path, analyse_needed, label="ANALYSE")

    _validate_channels(raw_analyse, eeg_ch, eog_ch, emg_ch, extra_eeg)

    # ── Stap 4: Volledige YASA analyse (met prefetched hypno) ─
    _set_progress(job_id, 5, 10, "Spindles, slow waves, bandpower...")
    logger.info("YASA volledige analyse starten...")
    yasa_results = run_full_analysis(
        raw              = raw_analyse,
        eeg_ch           = eeg_ch,
        eog_ch           = eog_ch,
        emg_ch           = emg_ch,
        all_eeg_channels = extra_eeg,
        recording_start  = recording_start,
        prefetched_hypno = hypno,
    )
    # Gebruik het reeds berekende staging-resultaat
    yasa_results["staging"] = staging_result

    # ── Stap 5: Pneumo-kanalen detecteren en laden ────────────
    _set_progress(job_id, 6, 10, "Pneumo-kanalen laden...")
    logger.info("Pneumo-kanalen detecteren...")
    pneumo_ch_list = _detect_pneumo_channels(edf_path, pneumo_channels)

    if pneumo_ch_list:
        pneumo_needed = list(dict.fromkeys(pneumo_ch_list + [eeg_ch]))
        logger.info("PNEUMO EDF laden (%d kanalen)...", len(pneumo_needed))
        try:
            raw_pneumo = _load_edf(edf_path, pneumo_needed, label="PNEUMO")
        except Exception as e:
            logger.warning("Pneumo EDF mislukt (%s) — gebruik staging-raw", e)
            raw_pneumo = raw_staging
    else:
        logger.info("Geen pneumo-kanalen — gebruik staging-raw")
        raw_pneumo = raw_staging

    # ── Stap 6: Pneumo-analyse ────────────────────────────────
    _set_progress(job_id, 7, 10, "Respiratoire analyse (AHI, SpO2)...")
    logger.info("Pneumo-analyse starten...")
    # Verzamel artefact-epoch nummers voor exclusie uit AHI/OAHI
    art_epochs = []
    art_data = yasa_results.get("artifacts", {})
    if art_data.get("success"):
        art_epochs = [e["epoch"] for e in art_data.get("artifact_epochs", [])]

    # v0.8.11 FIX 4: Clipping-detectie → artefact-masker terugkoppeling
    # Ref: Gemini review — "Epochs with saturated signals should be masked
    # for AHI calculation so TST is not contaminated."
    try:
        from signal_quality import check_channel_quality
        eeg_ch_name = cfg.get("eeg_ch", "")
        if eeg_ch_name and eeg_ch_name in raw_pneumo.ch_names:
            eeg_sq = check_channel_quality(
                raw_pneumo.get_data(picks=[eeg_ch_name])[0],
                raw_pneumo.info["sfreq"], "eeg")
            if eeg_sq.get("clipping_pct", 0) > 2.0:
                # Hoge clipping: markeer epochs met extreme waarden als artefact
                eeg_data_sq = raw_pneumo.get_data(picks=[eeg_ch_name])[0]
                sf_sq = raw_pneumo.info["sfreq"]
                spe_sq = int(sf_sq * 30)
                clip_hi = np.percentile(eeg_data_sq, 99.5)
                clip_lo = np.percentile(eeg_data_sq, 0.5)
                n_epochs_sq = len(eeg_data_sq) // spe_sq
                clipping_epochs = []
                for ep_i in range(n_epochs_sq):
                    seg = eeg_data_sq[ep_i*spe_sq:(ep_i+1)*spe_sq]
                    clip_frac = np.sum((seg >= clip_hi) | (seg <= clip_lo)) / len(seg)
                    if clip_frac > 0.05:  # >5% van epoch is geclipped
                        clipping_epochs.append(ep_i)
                if clipping_epochs:
                    art_epochs = sorted(set(art_epochs + clipping_epochs))
                    logger.info("v0.8.11: %d clipping-epochs toegevoegd aan artefactmasker "
                               "(totaal: %d)", len(clipping_epochs), len(art_epochs))
    except Exception as e:
        logger.debug("Clipping-check mislukt (niet-kritiek): %s", e)

    logger.info("Artefact-epochs voor pneumo exclusie: %d", len(art_epochs))

    pneumo_results = run_pneumo_analysis(
        raw              = raw_pneumo,
        hypno            = hypno,
        channel_map      = pneumo_channels,
        artifact_epochs  = art_epochs,
        scoring_profile  = cfg.get("scoring_profile", "standard"),
    )

    # ── Stap 7: Confidence review + signaal kwaliteit ────────
    _set_progress(job_id, 8, 10, "Kwaliteitscontrole...")

    # Confidence-based review stats
    try:
        from validation_metrics import compute_confidence_review_stats
        conf_review = compute_confidence_review_stats(
            hypno, staging_result.get("confidence", {}), threshold=0.70)
        logger.info("Confidence review: %d/%d low-confidence epochs (%.1f%%)",
                    conf_review["n_low_confidence"], conf_review["n_epochs"],
                    conf_review["pct_low_confidence"])
    except Exception as e:
        logger.warning("Confidence review mislukt: %s", e)
        conf_review = {"n_low_confidence": 0, "pct_low_confidence": 0}

    # Signaal kwaliteitscheck
    signal_quality = {}
    try:
        from signal_quality import check_signal_quality
        sq = check_signal_quality(raw_analyse)
        signal_quality = sq
        if sq.get("issues"):
            logger.warning("Signaal-kwaliteitsproblemen: %s", sq["issues"])
        else:
            logger.info("Signaal-kwaliteit: %s (%d goed, %d matig, %d slecht)",
                       sq["overall"], sq["n_good"], sq["n_moderate"], sq["n_poor"])
    except Exception as e:
        logger.warning("Signaal-kwaliteitscheck mislukt: %s", e)

    # ── Stap 8: Combineer en sla op ───────────────────────────
    _set_progress(job_id, 9, 10, "Resultaten opslaan...")
    combined = {
        **yasa_results,
        "pneumo":           pneumo_results,
        "patient_info":     patient_info,
        "job_id":           job_id,
        "confidence_review": conf_review,
        "signal_quality":    signal_quality,
        # v0.8.11: multi-site toegangscontrole
        "site_id":          cfg.get("site_id"),
        "owner_username":   cfg.get("owner_username", ""),
    }
    result_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_results.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, default=_json_serializer)
    logger.info("JSON opgeslagen")

    errors   = _collect_errors(combined)
    pdf_path = xlsx_path = psg_path = None

    _set_progress(job_id, 9, 10, "PDF & Excel rapporten genereren...")
    try:
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_rapport.pdf")
        _lang = cfg.get("language") or patient_info.get("lang") or "nl"
        generate_pdf_report(combined, pdf_path, lang=_lang)
        logger.info("PDF opgeslagen (%s)", _lang)
    except Exception as e:
        logger.error("PDF mislukt: %s", e)
        errors.append(f"pdf: {e}")

    try:
        xlsx_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_rapport.xlsx")
        generate_excel_report(combined, xlsx_path)
        logger.info("Excel opgeslagen")
    except Exception as e:
        logger.error("Excel mislukt: %s", e)
        errors.append(f"xlsx: {e}")

    # PSG-rapport: niet apart gegenereerd — /psg redirect naar /pdf (portrait AASM)
    psg_path = pdf_path  # zelfde bestand

    # EDF+ generatie: nu INLINE in pipeline (v14 — edfio, <10s)
    edfplus_path = None
    try:
        if os.path.exists(edf_path):
            edfplus_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_scored.edf")
            generate_edfplus(edf_path, combined, edfplus_path)
            logger.info("EDF+ opgeslagen: %s", edfplus_path)
    except Exception as e:
        logger.warning("EDF+ generatie mislukt (niet-blokkerend): %s", e)
        errors.append(f"edfplus: {e}")
        edfplus_path = None

    _set_progress(job_id, 10, 10, "Voltooid!")
    _send_email_notification(job_id, combined)
    elapsed = (datetime.utcnow() - started).total_seconds()
    logger.info("✅ Job voltooid: %s (%.1f sec)", job_id, elapsed)

    return {
        "status":       "done",
        "job_id":       job_id,
        "elapsed_sec":  round(elapsed, 1),
        "result_json":  result_path,
        "result_pdf":   pdf_path,
        "result_excel": xlsx_path,
        "result_psg":   psg_path,
        "result_edfplus": edfplus_path,
        "errors":       errors,
    }


# ─────────────────────────────────────────────
# EDF+ GENERATIE (ON-DEMAND, ACHTERGRONDTAAK)
# ─────────────────────────────────────────────

def generate_edfplus_job(job_id: str) -> dict:
    """
    Genereer EDF+ bestand met annotaties als achtergrondtaak.
    Wordt getriggerd via /results/<job_id>/edfplus button.

    v0.8.11 FIX: zoek EDF-pad op via config.json (zelfde logica als run_analysis_job),
    niet via hardcoded {job_id}.edf dat niet bestaat.
    """
    logger.info("EDF+ job starten: %s", job_id)

    result_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_results.json")
    output_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_scored.edf")

    # Zoek origineel EDF-bestand: config -> glob fallback
    edf_path = None
    config_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                edf_path = json.load(f).get("edf_path")
        except Exception:
            pass

    if not edf_path or not os.path.exists(edf_path):
        import glob as _glob
        candidates = [c for c in _glob.glob(os.path.join(UPLOAD_FOLDER, f"{job_id}*.edf"))
                      if "_scored.edf" not in c]
        edf_path = candidates[0] if candidates else None

    if not edf_path or not os.path.exists(edf_path):
        logger.error("EDF niet gevonden voor job %s", job_id)
        return {"status": "error", "error": "EDF-bestand niet gevonden"}

    if not os.path.exists(result_path):
        logger.error("Results niet gevonden: %s", result_path)
        return {"status": "error", "error": "Analyseresultaten niet gevonden"}

    try:
        with open(result_path, "r") as f:
            results = json.load(f)

        generate_edfplus(edf_path, results, output_path)
        logger.info("EDF+ klaar: %s", output_path)

        return {
            "status": "done",
            "job_id": job_id,
            "output_path": output_path,
        }

    except Exception as e:
        logger.error("EDF+ generatie mislukt: %s\n%s", e, traceback.format_exc())
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────
# HULPFUNCTIES
# ─────────────────────────────────────────────

def _validate_channels(raw, eeg_ch, eog_ch, emg_ch, extra_eeg):
    available = set(raw.ch_names)
    if eeg_ch not in available:
        raise ValueError(f"EEG '{eeg_ch}' niet gevonden. Beschikbaar: {sorted(available)}")
    if eog_ch and eog_ch not in available:
        logger.warning("EOG '%s' niet gevonden", eog_ch)
    if emg_ch and emg_ch not in available:
        logger.warning("EMG '%s' niet gevonden", emg_ch)
    missing = [ch for ch in extra_eeg if ch not in available]
    if missing:
        logger.warning("Extra EEG overgeslagen: %s", missing)
        extra_eeg[:] = [ch for ch in extra_eeg if ch in available]
    if eeg_ch not in extra_eeg:
        extra_eeg.insert(0, eeg_ch)


def _collect_errors(results: dict) -> list:
    errors = []
    for mod in ["staging", "sleep_statistics", "spindles", "slow_waves",
                "rem", "bandpower", "sleep_cycles", "artifacts"]:
        d = results.get(mod, {})
        if not d.get("success", True) and d.get("error"):
            errors.append(f"{mod}: {d['error']}")
    for mod in ["respiratory", "spo2", "position", "heart_rate", "snore", "plm"]:
        d = results.get("pneumo", {}).get(mod, {})
        if not d.get("success", True) and d.get("error"):
            errors.append(f"pneumo.{mod}: {d['error']}")
    return errors


def _extract_patient_info(raw, config_pat: dict,
                           recording_start: str = None) -> dict:
    """
    Extraheer patiëntgegevens uit EDF header + handmatige invoer.
    raw mag None zijn (bijv. bij regenerate_with_corrections).
    """
    subject_info = {}
    meas_date    = None
    dur_str      = "—"
    if raw is not None:
        subject_info = raw.info.get("subject_info") or {}
        meas_date    = raw.info.get("meas_date")
        dur_s        = raw.times[-1]
        dur_str      = f"{int(dur_s//3600):02d}:{int((dur_s%3600)//60):02d}:00"
    tib_start    = meas_date.strftime("%d-%m-%Y %H:%M:%S") if meas_date else "—"
    rec_date     = recording_start or (
        meas_date.strftime("%d-%m-%Y") if meas_date else "—")

    # EDF patiëntgegevens: MNE slaat op in subject_info
    edf_name = subject_info.get("his_id", "")
    edf_id   = str(subject_info.get("id", ""))
    edf_sex  = subject_info.get("sex", None)  # 1=male, 2=female in MNE
    edf_bday = subject_info.get("birthday", None)
    edf_hand = subject_info.get("hand", None)

    # Geslacht mapping
    sex_map = {1: "M", 2: "V", None: "—"}
    sex_str = sex_map.get(edf_sex, "—")

    # Geboortedatum
    dob_str = "—"
    if edf_bday:
        try:
            from datetime import date
            if isinstance(edf_bday, date):
                dob_str = edf_bday.strftime("%d-%m-%Y")
            else:
                dob_str = str(edf_bday)
        except Exception:
            dob_str = str(edf_bday)

    # Handmatige invoer overschrijft EDF (als niet leeg)
    def pick(manual_key, edf_val, default="—"):
        manual = config_pat.get(manual_key, "").strip()
        if manual:
            return manual
        return edf_val if edf_val else default

    return {
        "patient_name":      pick("patient_name", edf_name, "Unknown"),
        "dob":               pick("dob", dob_str),
        "sex":               pick("sex", sex_str),
        "patient_id":        pick("patient_id", edf_id),
        "bmi":               config_pat.get("bmi", "—"),
        "weight_kg":         config_pat.get("weight_kg", "—"),
        "height_cm":         config_pat.get("height_cm", "—"),
        "recording_date":    rec_date,
        "recording_start":   tib_start,
        "recording_end":     "—",
        "tib_start":         tib_start,
        "tib_end":           "—",
        "tib_artefact":      "—",
        "tib_duration":      dur_str,
        "duration_recorded": dur_str,
        "diagnosis":         config_pat.get("diagnosis", ""),
        "comments":          config_pat.get("comments", ""),
        "scorer":            config_pat.get("scorer", ""),
        "institution":       config_pat.get("institution", ""),
    }


def _json_serializer(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return str(obj)


# ═══════════════════════════════════════════════════════════════
# v10: HERBEREKENING NA MANUELE STAGING-CORRECTIES
# ═══════════════════════════════════════════════════════════════

def regenerate_with_corrections(job_id: str) -> dict:
    """
    Herbereken slaapstatistieken en rapporten na manueel gecorrigeerd hypnogram.
    1. Laad corrections.json (manueel hypnogram)
    2. Herbereken YASA sleep_statistics
    3. Overschrijf results.json
    4. Regenereer PDF, Excel, PSG
    """
    logger.info("▶ Herberekening gestart: %s", job_id)
    _set_progress(job_id, 1, 6, "Correcties laden...")

    corr_path   = os.path.join(UPLOAD_FOLDER, f"{job_id}_corrections.json")
    result_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_results.json")

    if not os.path.exists(corr_path):
        raise FileNotFoundError(f"Corrections niet gevonden: {corr_path}")
    if not os.path.exists(result_path):
        raise FileNotFoundError(f"Results niet gevonden: {result_path}")

    with open(corr_path)   as f: corr    = json.load(f)
    with open(result_path) as f: results = json.load(f)

    hypno_str = corr["hypnogram"]
    n_changes = corr.get("n_changes", 0)
    scorer    = corr.get("scorer", "manueel")

    _set_progress(job_id, 2, 6, "Slaapstatistieken herberekenen...")

    import yasa, numpy as np
    try:
        hypno_int = yasa.hypno_str_to_int(hypno_str)
        sf_hyp    = 1 / 30
        new_stats = yasa.sleep_statistics(hypno_int, sf_hyp=sf_hyp)
        results["sleep_statistics"] = {
            "success": True,
            "stats": {k: (float(v) if v is not None else None)
                      for k, v in new_stats.items()},
        }
    except Exception as e:
        logger.error("Herberekening sleep_statistics mislukt: %s", e)

    # Hypnogram timeline bijwerken
    results["hypnogram_timeline"] = {
        "timeline": [{"epoch": i, "stage": s, "onset_s": i*30}
                     for i, s in enumerate(hypno_str)]
    }
    results["staging"]["hypnogram"]              = hypno_str
    results["staging"]["manual_scorer"]          = scorer
    results["staging"]["n_corrections"]          = n_changes
    results["staging"]["is_manually_corrected"]  = True

    _set_progress(job_id, 3, 6, "Resultaten opslaan...")
    with open(result_path, "w") as f:
        json.dump(results, f, indent=2, default=_json_serializer)

    errors = []

    _set_progress(job_id, 4, 6, "PDF hergeneren...")
    try:
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_rapport.pdf")
        from generate_pdf_report import generate_pdf_report
        _lang = results.get("patient_info", {}).get("lang") or "nl"
        generate_pdf_report(results, pdf_path, lang=_lang)
        logger.info("PDF hergenereert (%s)", _lang)
    except Exception as e:
        logger.error("PDF herberekening mislukt: %s", e)
        errors.append(f"pdf: {e}")

    _set_progress(job_id, 5, 6, "Excel hergeneren...")
    try:
        from generate_excel_report import generate_excel_report
        generate_excel_report(results,
            os.path.join(UPLOAD_FOLDER, f"{job_id}_rapport.xlsx"))
    except Exception as e:
        errors.append(f"excel: {e}")

    _set_progress(job_id, 6, 6, "Voltooid!")
    logger.info("✅ Herberekening klaar: %s (%d correcties, %d fouten)",
                job_id, n_changes, len(errors))
    return {"status": "done", "job_id": job_id, "errors": errors}


# ═══════════════════════════════════════════════════════════════
# v10: E-MAIL NOTIFICATIE BIJ KLAAR ANALYSE
# ═══════════════════════════════════════════════════════════════

def _send_email_notification(job_id: str, results: dict):
    """
    Stuur e-mail bij klaar analyse.
    Configureer in config.json:
      "email": {
        "enabled": true,
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "noreply@sleepai.be",
        "smtp_pass": "...",
        "from":      "SleepAI <noreply@sleepai.be>",
        "notify_to": ["slaaplabo@uzgent.be"]
      }
    """
    try:
        import smtplib
        from email.mime.text      import MIMEText
        from email.mime.multipart import MIMEMultipart

        cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        if not os.path.exists(cfg_path):
            cfg_path = "config.json"
        with open(cfg_path) as f:
            cfg = json.load(f)
        ecfg = cfg.get("email", {})
        if not ecfg.get("enabled"):
            return

        pat   = results.get("patient_info", {})
        pname = " ".join(filter(None, [pat.get("patient_name", ""),
                                        pat.get("patient_firstname", "")])) or "—"
        to_list = list(set(ecfg.get("notify_to", [])))
        if not to_list:
            return

        site_url   = cfg.get("site", {}).get("url", "https://sleepai.be")
        report_url = f"{site_url}/results/{job_id}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"YASAFlaskified — Analyse klaar: {pname}"
        msg["From"]    = ecfg.get("from", "SleepAI <noreply@sleepai.be>")
        msg["To"]      = ", ".join(to_list)

        html = f"""<html><body style="font-family:sans-serif">
        <h3 style="color:#1a3a8f">✅ Analyse voltooid</h3>
        <table><tr><td style="padding:4px 12px 4px 0;color:#666">Patiënt:</td>
        <td><b>{pname}</b></td></tr>
        <tr><td style="padding:4px 12px 4px 0;color:#666">Job:</td>
        <td>{job_id[:8]}…</td></tr></table>
        <p style="margin-top:16px">
        <a href="{report_url}"
           style="background:#1a3a8f;color:white;padding:8px 18px;
                  border-radius:4px;text-decoration:none">Bekijk rapport</a></p>
        <p style="color:#999;font-size:12px">YASAFlaskified v0.8.11 · {site_url}<br>
        Screening-tool — geen medische diagnose.</p>
        </body></html>"""

        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(ecfg["smtp_host"], int(ecfg.get("smtp_port", 587))) as s:
            s.ehlo(); s.starttls(); s.ehlo()
            s.login(ecfg["smtp_user"], ecfg["smtp_pass"])
            s.sendmail(msg["From"], to_list, msg.as_string())
        logger.info("E-mail verstuurd naar: %s", to_list)
    except Exception as e:
        logger.warning("E-mail mislukt: %s", e)
