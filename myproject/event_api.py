from __future__ import annotations
"""
event_api.py — YASAFlaskified v0.8.36
===================================
Server-side event beheer: laden, opslaan, herberekenen AHI.

Event-formaat (één event):
  {
    "id":       "uuid4-string",
    "type":     "OA" | "CA" | "MA" | "H" | "AR" | "RERA",
    "t_start":  float,   # seconden vanaf begin opname
    "t_end":    float,
    "duration": float,   # t_end - t_start
    "epoch":    int,     # 30s-epoch index
    "source":   "ai" | "manual",
    "scorer":   str,
    "modified_at": iso-str,
  }

Events worden opgeslagen in {job_id}_events.json.
Bij opslaan wordt AHI/OAHI automatisch herberekend.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("yasaflaskified.event_api")

# ── Event-types ────────────────────────────────────────────────────────────
EVENT_TYPES = {
    "OA":   {"label": "Obstructief apnea",  "color": "#e74c3c", "min_dur": 10.0},
    "CA":   {"label": "Centraal apnea",     "color": "#3498db", "min_dur": 10.0},
    "MA":   {"label": "Gemengd apnea",      "color": "#9b59b6", "min_dur": 10.0},
    "H":    {"label": "Hypopnea",           "color": "#f39c12", "min_dur": 10.0},
    "AR":   {"label": "Arousal",            "color": "#2ecc71", "min_dur":  3.0},
    "RERA": {"label": "RERA",               "color": "#1abc9c", "min_dur": 10.0},
}

# Apnea-types die meetellen voor AHI
AHI_TYPES  = {"OA", "CA", "MA", "H"}
# OAHI = obstructieve apneas + hypopneas (excl. centraal, gemengd)
OAHI_TYPES = {"OA", "H"}


# ── Hulpfuncties ─────────────────────────────────────────────────────────────

def _events_path(job_id: str, upload_folder: str) -> str:
    return os.path.join(upload_folder, f"{job_id}_events.json")


def _results_path(job_id: str, upload_folder: str) -> str:
    return os.path.join(upload_folder, f"{job_id}_results.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id() -> str:
    return str(uuid.uuid4())


# ── Laden ─────────────────────────────────────────────────────────────────────

def load_events(job_id: str, upload_folder: str) -> list[dict]:
    """
    Laad events voor job_id.
    1. Probeer {job_id}_events.json (manueel gecorrigeerd)
    2. Extraheer uit results.json (AI-gegenereerd)
    3. Geef lege lijst terug als niets gevonden
    """
    path = _events_path(job_id, upload_folder)
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return data.get("events", [])

    # Fallback: extraheer AI-events uit results.json
    return _extract_ai_events(job_id, upload_folder)


def _extract_ai_events(job_id: str, upload_folder: str) -> list[dict]:
    """
    Zet YASA pneumo-resultaten om naar event-lijst.
    Vult t_start/t_end op basis van epoch-index (30s rasters).
    """
    res_path = _results_path(job_id, upload_folder)
    if not os.path.exists(res_path):
        return []

    with open(res_path) as f:
        results = json.load(f)

    pneumo = results.get("pneumo", {})
    resp   = pneumo.get("respiratory", {})
    events = []

    # Respiratoire events (als gedetailleerde lijst aanwezig)
    for ev in resp.get("events", []):
        t_start = float(ev.get("t_start", ev.get("onset_s", 0)))
        dur     = float(ev.get("duration", ev.get("duration_s", 10)))
        ev_type = _map_yasa_type(ev.get("type", "OA"))
        events.append({
            "id":          _make_id(),
            "type":        ev_type,
            "t_start":     t_start,
            "t_end":       t_start + dur,
            "duration":    dur,
            "epoch":       int(t_start // 30),
            "source":      "ai",
            "scorer":      "YASA",
            "modified_at": _now_iso(),
        })

    # Arousals
    arous = pneumo.get("arousal", {})
    for ev in arous.get("events", []):
        t_start = float(ev.get("t_start", ev.get("onset_s", 0)))
        dur     = float(ev.get("duration", 5.0))
        events.append({
            "id":          _make_id(),
            "type":        "AR",
            "t_start":     t_start,
            "t_end":       t_start + dur,
            "duration":    dur,
            "epoch":       int(t_start // 30),
            "source":      "ai",
            "scorer":      "YASA",
            "modified_at": _now_iso(),
        })

    logger.info("AI-events geëxtraheerd voor %s: %d events", job_id, len(events))
    return events


def _map_yasa_type(yasa_type: str) -> str:
    """Zet YASA event-type om naar interne code."""
    m = {
        "obstructive": "OA", "central": "CA", "mixed": "MA",
        "hypopnea": "H", "apnea": "OA", "rera": "RERA",
        "arousal": "AR",
        # Directe codes (al in intern formaat)
        "oa": "OA", "ca": "CA", "ma": "MA", "h": "H",
        "ar": "AR",
    }
    key = str(yasa_type).strip().lower()
    return m.get(key, "OA")


# ── Opslaan ───────────────────────────────────────────────────────────────────

def save_events(job_id: str, upload_folder: str,
                events: list[dict], scorer: str = "manueel") -> dict:
    """
    Sla gecorrigeerde event-lijst op en herbereken AHI/OAHI/RDI.
    Retourneert bijgewerkte statistieken.
    """
    path = _events_path(job_id, upload_folder)

    # Bereken duur opname voor AHI-noemer
    tst_h = _get_tst_hours(job_id, upload_folder)

    stats = _calc_stats(events, tst_h)

    payload = {
        "job_id":       job_id,
        "events":       events,
        "stats":        stats,
        "scorer":       scorer,
        "n_manual":     sum(1 for e in events if e.get("source") == "manual"),
        "saved_at":     _now_iso(),
    }

    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

    # Sync naar results.json
    _sync_to_results(job_id, upload_folder, stats)

    logger.info("Events opgeslagen voor %s: %d events, AHI=%.1f",
                job_id, len(events), stats.get("ahi_total", 0))
    return stats


def _get_tst_hours(job_id: str, upload_folder: str) -> float:
    """Haal TST op uit results.json (voor AHI-noemer)."""
    try:
        with open(_results_path(job_id, upload_folder)) as f:
            data = json.load(f)
        tst_min = data.get("sleep_statistics", {}).get("stats", {}).get("TST")
        if tst_min:
            return float(tst_min) / 60.0
        # Fallback: duur opname uit meta
        dur_s = data.get("meta", {}).get("duration_s") or \
                data.get("meta", {}).get("duration_min", 0) * 60
        return float(dur_s) / 3600.0
    except Exception:
        return 1.0  # Noodgeval: 1u zodat deling niet crasht


def _calc_stats(events: list[dict], tst_h: float) -> dict:
    """Herbereken AHI, OAHI, arousal index en RDI vanuit event-lijst."""
    if tst_h <= 0:
        tst_h = 1.0

    counts = {t: 0 for t in EVENT_TYPES}
    for ev in events:
        t = ev.get("type", "OA")
        if t in counts:
            counts[t] += 1

    n_ahi  = sum(counts[t] for t in AHI_TYPES)
    n_oahi = sum(counts[t] for t in OAHI_TYPES)
    n_ar   = counts["AR"]
    n_rera = counts["RERA"]

    ahi  = round(n_ahi  / tst_h, 2)
    oahi = round(n_oahi / tst_h, 2)
    ai   = round(n_ar   / tst_h, 2)
    rdi  = round((n_ahi + n_rera) / tst_h, 2)

    def sev(v):
        if v < 5:  return "Normaal"
        if v < 15: return "Mild OSA"
        if v < 30: return "Matig OSA"
        return "Ernstig OSA"

    return {
        "n_oa":         counts["OA"],
        "n_ca":         counts["CA"],
        "n_ma":         counts["MA"],
        "n_hypopnea":   counts["H"],
        "n_arousal":    counts["AR"],
        "n_rera":       counts["RERA"],
        "n_ah_total":   n_ahi,
        "ahi_total":    ahi,
        "oahi":         oahi,
        "arousal_index":ai,
        "rdi":          rdi,
        "severity":     sev(ahi),
        "oahi_severity":sev(oahi),
        "tst_h":        round(tst_h, 2),
        "manually_corrected": True,
    }


def _sync_to_results(job_id: str, upload_folder: str, stats: dict):
    """Schrijf herberekende stats terug naar results.json."""
    try:
        res_path = _results_path(job_id, upload_folder)
        with open(res_path) as f:
            data = json.load(f)
        # Overschrijf respiratory summary
        if "pneumo" not in data:
            data["pneumo"] = {}
        if "respiratory" not in data["pneumo"]:
            data["pneumo"]["respiratory"] = {}
        data["pneumo"]["respiratory"]["summary"] = stats
        data["pneumo"]["respiratory"]["manually_corrected"] = True
        with open(res_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.warning("Sync naar results.json mislukt: %s", e)


# ── Event-operaties ───────────────────────────────────────────────────────────

def add_event(job_id: str, upload_folder: str,
              ev_type: str, t_start: float,
              duration: float, scorer: str = "manueel") -> dict:
    """Voeg één event toe en sla op."""
    if ev_type not in EVENT_TYPES:
        raise ValueError(f"Ongeldig event-type: {ev_type}")
    events = load_events(job_id, upload_folder)
    new_ev = {
        "id":          _make_id(),
        "type":        ev_type,
        "t_start":     round(t_start, 2),
        "t_end":       round(t_start + duration, 2),
        "duration":    round(duration, 2),
        "epoch":       int(t_start // 30),
        "source":      "manual",
        "scorer":      scorer,
        "modified_at": _now_iso(),
    }
    events.append(new_ev)
    events.sort(key=lambda e: e["t_start"])
    stats = save_events(job_id, upload_folder, events, scorer)
    return {"event": new_ev, "stats": stats}


def remove_event(job_id: str, upload_folder: str,
                 event_id: str, scorer: str = "manueel") -> dict:
    """Verwijder event op ID en sla op."""
    events = load_events(job_id, upload_folder)
    before = len(events)
    events = [e for e in events if e.get("id") != event_id]
    if len(events) == before:
        raise KeyError(f"Event {event_id} niet gevonden")
    stats = save_events(job_id, upload_folder, events, scorer)
    return {"removed": event_id, "stats": stats}


def toggle_event_at(job_id: str, upload_folder: str,
                    ev_type: str, t_click: float,
                    default_duration: float,
                    scorer: str = "manueel") -> dict:
    """
    Toggle: als er al een event van dit type binnen ±5s bestaat → verwijder het.
    Anders → voeg nieuw event toe op t_click.
    """
    events = load_events(job_id, upload_folder)
    TOLERANCE = 5.0  # seconden

    # Zoek bestaand event binnen tolerantie
    existing = None
    for ev in events:
        if ev.get("type") == ev_type:
            mid = (ev["t_start"] + ev["t_end"]) / 2
            if abs(mid - t_click) <= TOLERANCE:
                existing = ev
                break
            # Ook checken of klik binnen het event valt
            if ev["t_start"] - 1 <= t_click <= ev["t_end"] + 1:
                existing = ev
                break

    if existing:
        events = [e for e in events if e["id"] != existing["id"]]
        action = "removed"
        ev_ref = existing
    else:
        t_start_ev = max(0.0, round(t_click - default_duration / 2, 2))
        t_end_ev   = round(t_start_ev + default_duration, 2)
        ev_ref = {
            "id":          _make_id(),
            "type":        ev_type,
            "t_start":     t_start_ev,
            "t_end":       t_end_ev,
            "duration":    round(default_duration, 2),
            "epoch":       int(t_click // 30),
            "source":      "manual",
            "scorer":      scorer,
            "modified_at": _now_iso(),
        }
        events.append(ev_ref)
        events.sort(key=lambda e: e["t_start"])
        action = "added"

    stats = save_events(job_id, upload_folder, events, scorer)
    return {"action": action, "event": ev_ref, "stats": stats}


# ── Export voor FHIR/EDF+ ────────────────────────────────────────────────────

def events_for_epoch(job_id: str, upload_folder: str,
                     epoch_idx: int) -> list[dict]:
    """Geeft alle events terug die overlappen met een specifieke epoch."""
    t0 = epoch_idx * 30.0
    t1 = t0 + 30.0
    return [
        e for e in load_events(job_id, upload_folder)
        if e["t_start"] < t1 and e["t_end"] > t0
    ]
