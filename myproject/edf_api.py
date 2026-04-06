from __future__ import annotations
"""
edf_api.py — YASAFlaskified v0.8.27
================================
Server-side EDF-data API voor de browser-signaalviewer.

Routes (geregistreerd in app.py via register_edf_api(app)):
  GET /api/edf/<job_id>/info
      → { channels, sfreq, n_epochs, duration_s, epoch_len_s, ch_types }

  GET /api/edf/<job_id>/epoch/<int:epoch_idx>
      → { epoch, channels: { <name>: [floats] }, sfreq, epoch_len_s, t0_s }

  GET /api/edf/<job_id>/epochs/<int:start>/<int:end>
      → meerdere epochs in één request (max 10)
"""

import os
import json
import logging
import numpy as np

logger = logging.getLogger("yasaflaskified.edf_api")

# ── Kanaaltype-detectie ────────────────────────────────────────────────────
CH_TYPE_PATTERNS = {
    "eeg":   ["EEG","FP","F3","F4","C3","C4","P3","P4","O1","O2",
               "FZ","CZ","PZ","OZ","T3","T4","T5","T6","A1","A2","M1","M2"],
    "eog":   ["EOG","E1","E2","LOC","ROC"],
    "emg":   ["EMG","CHIN","CHIN1","CHIN2","LEG","TIBIAL"],
    "ecg":   ["ECG","EKG","CARDIAC"],
    "resp":  ["FLOW","NASAL","THERM","THOR","THORAX","ABD","ABDOMEN",
               "BELT","RESP","PFLOW","PTAF","CANNULA"],
    "spo2":  ["SPO2","SAO2","OX","OXIMETRY","PLETH"],
    "snore": ["SNORE","MIC","SOUND"],
    "pos":   ["POS","POSITION","BODY"],
}

CHANNEL_PRIORITY = ["eeg","eog","emg","resp","spo2","ecg","snore","pos"]

# Amplitude-schaling per kanaaltype (voor normalisatie)
SCALE_HINTS = {
    "eeg":   200.0,   # µV
    "eog":   400.0,   # µV
    "emg":   150.0,   # µV
    "ecg":   2.0,     # mV
    "resp":  1.0,     # genormaliseerd
    "spo2":  5.0,     # %
    "snore": 1.0,
    "pos":   1.0,
}


def _detect_ch_type(name: str) -> str:
    """Geeft kanaaltype terug op basis van naam."""
    u = name.upper().replace(" ", "").replace("-", "")
    for ch_type, patterns in CH_TYPE_PATTERNS.items():
        for p in patterns:
            if p in u:
                return ch_type
    return "other"


def _edf_path_for_job(job_id: str, upload_folder: str) -> str | None:
    """Zoek het EDF-bestand voor een job_id."""
    # 1. Uit config.json van de job
    cfg_path = os.path.join(upload_folder, f"{job_id}_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                cfg = json.load(f)
            edf = cfg.get("edf_path")
            if edf and os.path.exists(edf):
                return edf
        except Exception:
            pass

    # 2. Uit results.json
    res_path = os.path.join(upload_folder, f"{job_id}_results.json")
    if os.path.exists(res_path):
        try:
            with open(res_path) as f:
                data = json.load(f)
            edf = data.get("meta", {}).get("edf_path")
            if edf and os.path.exists(edf):
                return edf
        except Exception:
            pass

    return None


# ── Cache (LRU, max 3 EDF-bestanden per worker) ──────────────────────────────
from functools import lru_cache
from collections import OrderedDict

_MAX_CACHE = 3   # max RAM ~1.5 GB bij 3 × 500 MB PSG

class _LRUCache:
    """Eenvoudige LRU-cache met vaste grootte voor mne.io.BaseRaw objecten."""
    def __init__(self, maxsize: int = 3):
        self._cache: OrderedDict = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str):
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._maxsize:
                evicted = next(iter(self._cache))
                logger.info("EDF cache: evict job %s (RAM vrijgeven)", evicted)
                del self._cache[evicted]
        self._cache[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()

_raw_cache = _LRUCache(maxsize=_MAX_CACHE)


def _get_raw(job_id: str, upload_folder: str):
    """
    Laad (en cache) mne.io.BaseRaw voor job_id.
    LRU-cache max 3 bestanden — oudste wordt automatisch verwijderd.
    """
    cached = _raw_cache.get(job_id)
    if cached is not None:
        return cached

    edf_path = _edf_path_for_job(job_id, upload_folder)
    if not edf_path:
        raise FileNotFoundError(f"EDF niet gevonden voor job {job_id}")

    import mne
    logger.info("EDF laden voor viewer: %s", edf_path)
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    _raw_cache.set(job_id, raw)
    logger.info("EDF geladen: %d kanalen, %.0f Hz, %.0f s",
                len(raw.ch_names), raw.info["sfreq"], raw.times[-1])
    return raw


def _sort_channels(names: list[str]) -> list[str]:
    """Sorteer kanalen op type-prioriteit."""
    def key(n):
        t = _detect_ch_type(n)
        try:    return CHANNEL_PRIORITY.index(t)
        except: return len(CHANNEL_PRIORITY)
    return sorted(names, key=key)


# ── API-functies (aangeroepen vanuit Flask-routes) ────────────────────────

def edf_info(job_id: str, upload_folder: str) -> dict:
    """
    Geeft metadata van het EDF-bestand terug.
    Retourneert dict klaar voor jsonify().
    """
    raw       = _get_raw(job_id, upload_folder)
    sfreq     = raw.info["sfreq"]
    duration  = raw.times[-1]
    epoch_len = 30.0
    n_epochs  = int(duration // epoch_len)
    names     = _sort_channels(raw.ch_names)

    ch_types  = {n: _detect_ch_type(n) for n in names}
    ch_scales = {n: SCALE_HINTS.get(_detect_ch_type(n), 1.0) for n in names}

    return {
        "job_id":      job_id,
        "channels":    names,
        "ch_types":    ch_types,
        "ch_scales":   ch_scales,
        "sfreq":       float(sfreq),
        "duration_s":  float(duration),
        "n_epochs":    n_epochs,
        "epoch_len_s": epoch_len,
    }


def edf_epoch(job_id: str, epoch_idx: int,
              upload_folder: str,
              channels: list[str] | None = None) -> dict:
    """
    Geeft signaaldata voor één 30s-epoch terug.
    channels=None → alle kanalen.
    Data wordt gedecimeerd naar max 512 samples/kanaal voor snelle overdracht.
    """
    raw       = _get_raw(job_id, upload_folder)
    sfreq     = raw.info["sfreq"]
    epoch_len = 30.0
    t0        = epoch_idx * epoch_len
    t1        = t0 + epoch_len

    if t0 >= raw.times[-1]:
        raise IndexError(f"Epoch {epoch_idx} buiten bereik")

    t1 = min(t1, raw.times[-1])

    # Selecteer kanalen
    req_chs = channels if channels else raw.ch_names
    req_chs = [c for c in req_chs if c in raw.ch_names]
    if not req_chs:
        req_chs = raw.ch_names

    # Data ophalen (time-slice)
    start_s = int(t0 * sfreq)
    stop_s  = int(t1 * sfreq)
    data, _  = raw[req_chs, start_s:stop_s]   # shape: (n_ch, n_samples)

    # Decimeer naar max 512 samples per kanaal (snelheid)
    n_out = 512
    n_in  = data.shape[1]
    if n_in > n_out:
        step  = n_in // n_out
        data  = data[:, ::step]
        eff_sfreq = sfreq / step
    else:
        eff_sfreq = sfreq

    # Bouw response
    ch_data = {}
    for i, ch in enumerate(req_chs):
        sig = data[i].astype(float)
        # Vervang NaN/Inf door 0
        sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
        ch_data[ch] = sig.tolist()

    return {
        "epoch":      epoch_idx,
        "t0_s":       float(t0),
        "t1_s":       float(t1),
        "epoch_len_s":epoch_len,
        "sfreq":      float(eff_sfreq),
        "n_samples":  data.shape[1],
        "channels":   ch_data,
    }


def edf_multi_epoch(job_id: str, start: int, end: int,
                    upload_folder: str,
                    channels: list[str] | None = None) -> dict:
    """
    Meerdere epochs in één request (max 10).
    Gebruikt voor pre-fetch (volgende epoch alvast laden).
    """
    end   = min(end, start + 10)
    raw   = _get_raw(job_id, upload_folder)
    n_max = int(raw.times[-1] // 30)
    end   = min(end, n_max)

    epochs = []
    for idx in range(start, end):
        try:
            epochs.append(edf_epoch(job_id, idx, upload_folder, channels))
        except IndexError:
            break

    return {"start": start, "end": end, "epochs": epochs}


def clear_cache(job_id: str | None = None) -> None:
    """Verwijder EDF uit cache (bijv. na delete job). None = alles wissen."""
    if job_id is None:
        _raw_cache.clear()
        logger.info("EDF cache volledig gewist")
    elif job_id in _raw_cache:
        del _raw_cache._cache[job_id]
        logger.info("EDF cache gewist voor job %s", job_id)
