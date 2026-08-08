"""Visuele controle van de gescoorde respiratoire events.

Waarvoor dit bestaat: een AHI is één getal en verbergt hoe het tot stand kwam.
Bij het beoordelen van een scoringsalgoritme wil je de signalen zien, en dan
vooral de gevallen waar het spannend was.

Twee keuzes die deze module anders maakt dan de epoch-voorbeelden in het PDF-
rapport:

1. **De selectie is omgedraaid.** `_select_example_events` in de
   rapportgenerator kiest de hoogste confidence, het langste event en de
   grootste desaturatie — de meest ÓVERTUIGENDE voorbeelden. Voor een rapport
   is dat juist; voor controle is het nutteloos. Wat het algoritme goed doet
   hoef je niet na te kijken. Hier krijgen de grensgevallen voorrang, plus de
   AFGEWEZEN kandidaten met de reden waarom ze het niet werden.

2. **Eén EDF-lezing voor de hele set.** Meten wees uit: header 1,0 s, vier
   kanalen laden 5,1 s en 194 MB voor een nacht van 6,6 uur, tegenover 0,18 s
   per paneel. Panelen per HTTP-verzoek renderen zou twintig events op twee
   minuten brengen; daarom bouwt één verzoek de volledige set.
"""

import base64
import glob
import json
import logging
import os

logger = logging.getLogger(__name__)

# Bovengrens op wat één weergave rendert. Niet willekeurig: bij ~0,18 s per
# paneel bovenop ~6 s laadtijd houdt 24 het verzoek onder de tien seconden.
MAX_PANELS = 24
DEFAULT_PANELS = 12


# ══════════════════════════════════════════════════════════════
#  Selectie — grensgevallen eerst
# ══════════════════════════════════════════════════════════════

def _confidence(ev):
    try:
        return float(ev.get("confidence"))
    except (TypeError, ValueError):
        return None


def _rejection_nearness(ev):
    """Hoe dicht kwam een afgewezen kandidaat bij scoren?

    `reject_reason` draagt de gemeten waarde en de drempel, bijvoorbeeld
    ``local_reduction_15pct<20pct`` of ``stable_breathing_cv_0.12<0.25``.
    De verhouding van die twee zegt hoe kritiek de afwijzing was; 0,95 is een
    grensgeval, 0,05 niet. Onleesbare of onbekende redenen krijgen 0,5 zodat
    ze niet stilletjes vooraan of achteraan belanden.
    """
    import re
    reason = str(ev.get("reject_reason") or "")
    m = re.search(r"([0-9]*\.?[0-9]+)\s*(?:pct)?\s*<\s*([0-9]*\.?[0-9]+)", reason)
    if not m:
        return 0.5
    try:
        gemeten, drempel = float(m.group(1)), float(m.group(2))
    except ValueError:
        return 0.5
    if drempel <= 0:
        return 0.5
    return max(0.0, min(1.0, gemeten / drempel))


def select_review_events(pneumo, n=DEFAULT_PANELS):
    """Kies de events die een beoordelaar het meest zeggen.

    Volgorde van belang, niet van tijd:

    1. gescoorde events met de LAAGSTE confidence — daar zit de twijfel;
    2. afgewezen kandidaten die het DICHTST bij de drempel kwamen;
    3. per eventtype één representant, zodat geen categorie ontbreekt.

    De uitkomst is deterministisch: bij gelijke sleutel beslist de onsettijd,
    zodat twee weergaven van dezelfde job dezelfde panelen tonen.
    """
    resp = (pneumo or {}).get("respiratory", {}) or {}
    events = [e for e in (resp.get("events") or [])
              if e.get("onset_s") is not None]
    rejected = [e for e in (resp.get("rejected_hypopneas") or [])
                if e.get("onset_s") is not None]

    n = max(1, min(int(n or DEFAULT_PANELS), MAX_PANELS))
    gekozen, gezien = [], set()

    def voeg_toe(ev, soort, toelichting=""):
        sleutel = round(float(ev["onset_s"]), 1)
        if sleutel in gezien or len(gekozen) >= n:
            return
        gezien.add(sleutel)
        gekozen.append({**ev, "_review_kind": soort,
                        "_review_note": toelichting})

    # 1. Twijfelgevallen: de laagste confidence eerst.
    met_conf = [(c, e) for e in events if (c := _confidence(e)) is not None]
    met_conf.sort(key=lambda p: (p[0], p[1]["onset_s"]))
    for c, ev in met_conf[:max(1, n // 2)]:
        voeg_toe(ev, "borderline", f"laagste confidence ({c:.2f})")

    # 2. Bijna-scores: afgewezen kandidaten dicht bij de drempel.
    bijna = sorted(rejected,
                   key=lambda e: (-_rejection_nearness(e), e["onset_s"]))
    for ev in bijna[:max(1, n // 3)]:
        voeg_toe(ev, "rejected", str(ev.get("reject_reason") or "afgewezen"))

    # 3. Dekking: één representant per type dat nog ontbreekt.
    getoond = {e.get("type") for e in gekozen}
    for ev in sorted(events, key=lambda e: e["onset_s"]):
        if ev.get("type") not in getoond:
            getoond.add(ev.get("type"))
            voeg_toe(ev, "typical", "eerste van dit type")

    # 4. Aanvullen tot n met de resterende laagste confidence.
    for c, ev in met_conf:
        if len(gekozen) >= n:
            break
        voeg_toe(ev, "borderline", f"confidence {c:.2f}")

    gekozen.sort(key=lambda e: e["onset_s"])
    return gekozen


# ══════════════════════════════════════════════════════════════
#  Panelen
# ══════════════════════════════════════════════════════════════

def channel_map_for(results):
    """Kanaalmap zoals de analyse hem gebruikte, niet opnieuw geraden."""
    pneumo = (results or {}).get("pneumo", {}) or {}
    ch_map = (results or {}).get("pneumo_channels") or {}
    if not ch_map:
        ch_map = (pneumo.get("meta", {}) or {}).get("channels_used", {}) or {}
    return {k: v for k, v in ch_map.items() if v}


def resolve_edf_path(job_id, upload_folder):
    """Zoek het originele EDF-bestand van een job.

    Config-JSON eerst (die draagt het pad zoals de analyse het gebruikte),
    daarna naamgeving. `_scored.edf` is de uitvoer, niet de bron.
    """
    cfg = os.path.join(upload_folder, f"{job_id}_config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg) as f:
                pad = (json.load(f) or {}).get("edf_path")
            if pad and os.path.exists(pad):
                return pad
        except Exception:
            pass
    kandidaten = [c for c in glob.glob(os.path.join(upload_folder, f"{job_id}*.edf"))
                  if "_scored.edf" not in c]
    return kandidaten[0] if kandidaten else None


def build_review_panels(edf_path, channel_map, events, hypno=None,
                        all_events=None):
    """Render de panelen in één EDF-lezing.

    Geeft een lijst (event, data-URI) terug. Een paneel dat niet lukt wordt
    overgeslagen in plaats van de hele weergave te laten vallen: bij een
    controle-instrument is achttien van de twintig panelen bruikbaar en nul
    panelen dat niet.
    """
    from generate_pdf_report import epoch_panel_png, load_panel_raw

    raw = load_panel_raw(edf_path, channel_map)
    if raw is None:
        logger.warning("eventcontrole: geen bruikbare kanalen in de EDF")
        return []

    panelen = []
    try:
        for ev in events:
            try:
                uit = epoch_panel_png(edf_path, channel_map, ev, hypno=hypno,
                                      pre_s=15, post_s=30, wc=16.2,
                                      all_events=all_events, raw=raw)
                if uit is None:
                    continue
                buf, _ = uit
                uri = ("data:image/png;base64,"
                       + base64.b64encode(buf.getvalue()).decode("ascii"))
                panelen.append((ev, uri))
            except Exception:
                logger.exception("eventcontrole: paneel op %.1f s mislukt",
                                 float(ev.get("onset_s") or -1))
    finally:
        # 194 MB per nacht; niet laten rondslingeren tussen verzoeken.
        del raw
    return panelen
