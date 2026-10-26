"""Analysevenster op signaalgeldigheid voor de polygrafieroute (waakpoort stap 1, 26-10-2026).

Een polygrafie heeft geen EEG, dus geen hypnogram; tot 0.38.12 gaf de app elke epoch "N2" en
deelde door de registratietijd. De hPG-simulatie in psgscoring (`docs/hpg_simulatie_20261026.md`)
liet zien dat die route 56 % van haar events in waak scoort, twee derde ná het laatste slaapepoch,
meestal op een losse sensor. psgscoring 0.37.0 levert `polygraphy_hypnogram_from_raw`: "N2" binnen
het venster op signaalgeldigheid, "W" daarbuiten, met provenance; de bestaande slaappoort en
TST-noemer van de keten doen de rest.

Deze module is de brug: het handmatige venster van de technoloog (minuten na opnamestart) wordt
geparset, de bibliotheekfunctie wordt aangeroepen als ze bestaat, en zonder haar (oudere pin) of
met `YASAFLASKIFIED_POLYGRAPHY_WINDOW=off` komt de oude route terug — altijd met de reden in de
provenance, nooit stil.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

ENV_FLAG = "YASAFLASKIFIED_POLYGRAPHY_WINDOW"


def analysis_window_s(van, tot):
    """Minuten na opnamestart (van, tot) -> (s0, s1), of None bij lege of onbruikbare invoer.

    Beide velden moeten ingevuld zijn en het einde moet na het begin liggen: liever geen venster
    dan een half venster, want een typefout zou stil een deel van de nacht wegknippen.
    """
    def _m(w):
        try:
            return float(str(w).strip().replace(",", "."))
        except (TypeError, ValueError):
            return None
    a, b = _m(van), _m(tot)
    if a is None or b is None:
        return None
    a = max(a, 0.0)
    if b <= a:
        return None
    return (a * 60.0, b * 60.0)


def _builder():
    """De bibliotheekfunctie, of None op een pin die haar niet heeft."""
    try:
        from psgscoring import polygraphy_hypnogram_from_raw
    except ImportError:
        return None
    return polygraphy_hypnogram_from_raw


def _leeg(n_epochs: int, method: str, reason: str) -> tuple[list, dict]:
    return ["N2"] * int(n_epochs), {"method": method, "reason": reason, "n_epochs": int(n_epochs),
                                    "analysed_min": int(n_epochs) * 0.5,
                                    "excluded_min": {"before_window": 0.0, "after_window": 0.0,
                                                     "inside_window": 0.0, "manual": 0.0, "total": 0.0},
                                    "manual_window_s": None}


def build_polygraphy_hypnogram(raw, channel_map: dict | None, *, n_epochs: int,
                               manual_window_s=None) -> tuple[list, dict]:
    """(hypnogram, provenance) voor de polygrafieroute.

    ``method`` in de provenance: "signal_validity_window" (venster gebouwd), "none" (bibliotheek
    vond geen bruikbaar flow/SpO2-kanaal), "off" (vlag), "unavailable" (pin zonder de functie),
    "error" (uitzondering; oude route, reden erbij).
    """
    if str(os.environ.get(ENV_FLAG, "")).strip().lower() in ("off", "0", "false", "uit"):
        return _leeg(n_epochs, "off", f"{ENV_FLAG}=off — oude polygrafieroute (alle epochs, registratietijd)")
    fn = _builder()
    if fn is None:
        return _leeg(n_epochs, "unavailable",
                     "psgscoring-pin zonder polygraphy_hypnogram_from_raw (< 0.37.0) — oude route")
    try:
        hypno, prov = fn(raw, channel_map=channel_map or None, n_epochs=int(n_epochs),
                         manual_window_s=manual_window_s)
    except Exception as e:  # noqa: BLE001 — het venster mag de analyse nooit tegenhouden
        logger.warning("[polygrafie] analysevenster mislukt (%s) — oude route", e)
        return _leeg(n_epochs, "error", f"analysevenster mislukt: {e!r} — oude route")
    if len(hypno) != int(n_epochs):
        hypno = (list(hypno) + ["N2"] * int(n_epochs))[: int(n_epochs)]
    return list(hypno), dict(prov)
