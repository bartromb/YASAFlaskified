"""Twee vlaggen die een montageprobleem zichtbaar maken.

F5 — EEG-TOPOGRAFIE. Spindels zijn frontocentraal maximaal, trage golven
frontaal dominant. Op de Thaise casus stond het dubbel omgekeerd: spindels
F4 804 / F3 521 tegen C3 14 / C4 36, en trage golven O1/O2 elk 276 tegen F3 3.
Dat is geen fysiologie maar een montage — en de slaapstadiëring draaide er wél
op. Alleen vlaggen, nooit corrigeren: welke twee kanalen verwisseld zijn, is van
buitenaf niet vast te stellen, en een gok verplaatst de fout.

F6 — POSITIECODES. `position_mapping_method == "levels"` betekent dat de
recorder codes gebruikt die wij niet kennen en dat de rangorde geraden is. Op
deze casus gaf dat vrijwel de hele nacht "PRO", met AHI Prone 18,8 tegen Left
8,2 — getallen die niet te weerleggen zijn. De tabel blijft staan, maar met een
voorbehoud eronder.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import (  # noqa: E402
    _position_mapping_is_coded,
    _position_rows,
    _topography_warning,
)


def _tel(paren):
    return {"summary": [{"Channel": c, "Count": n} for c, n in paren]}


def test_de_thaise_omkering_wordt_gevlagd():
    res = {"spindles": _tel([("F4", 804), ("F3", 521), ("C3", 14), ("C4", 36)]),
           "slow_waves": _tel([("O1", 276), ("O2", 276), ("F3", 3), ("F4", 0)])}
    w = _topography_warning(res)
    assert w, "de dubbele omkering werd niet gevlagd"
    assert w["sw_occipital"] == 552 and w["spindles_frontal"] == 1325


def test_een_normale_topografie_wordt_niet_gevlagd():
    res = {"spindles": _tel([("C3", 420), ("C4", 380), ("F3", 210), ("F4", 190)]),
           "slow_waves": _tel([("F3", 300), ("F4", 280), ("O1", 60), ("O2", 55)])}
    assert _topography_warning(res) is None


def test_een_enkele_omkering_is_niet_genoeg():
    """Eén omkering komt voor bij een slecht kanaal; samen zijn ze een patroon."""
    res = {"spindles": _tel([("C3", 420), ("C4", 380), ("F3", 210), ("F4", 190)]),
           "slow_waves": _tel([("O1", 276), ("O2", 276), ("F3", 3), ("F4", 0)])}
    assert _topography_warning(res) is None


def test_kanaalnamen_met_referentie_tellen_mee():
    """`EEG F3-A2` moet als F3 gelden, anders telt de check niets."""
    res = {"spindles": _tel([("EEG F4-A1", 804), ("EEG F3-A2", 521),
                             ("EEG C3-A2", 14), ("EEG C4-A1", 36)]),
           "slow_waves": _tel([("EEG O1-A2", 276), ("EEG O2-A1", 276),
                               ("EEG F3-A2", 3)])}
    assert _topography_warning(res) is not None


def test_zonder_gegevens_geen_bewering():
    assert _topography_warning({}) is None
    assert _topography_warning({"spindles": {"summary": []}}) is None


def test_herkende_codering_krijgt_geen_voorbehoud():
    assert _position_mapping_is_coded({"position_mapping_method": "coded"})
    assert not _position_mapping_is_coded({"position_mapping_method": "levels"})
    assert not _position_mapping_is_coded({})


def test_een_geraden_labelvolgorde_krijgt_een_voorbehoud_onder_de_tabel():
    pos = {"sleep_time_min": {"Prone": 393.5, "Left": 36.5},
           "sleep_pct": {"Prone": 91.5, "Left": 8.5},
           "ahi_per_pos": {"Prone": 18.8, "Left": 8.2},
           "n_events_per_pos": {"Prone": 123, "Left": 5},
           "min_minutes_for_index": 15.0,
           "position_mapping_method": "levels"}
    rijen = _position_rows(pos, "nl")
    assert rijen, "de tabel mag niet verdwijnen"
    laatste = rijen[-1][1]
    assert "aanname" in laatste and "POSA" in laatste, laatste


def test_een_herkende_codering_krijgt_dat_voorbehoud_niet():
    pos = {"sleep_time_min": {"Supine": 200.0, "Left": 100.0},
           "sleep_pct": {"Supine": 66.7, "Left": 33.3},
           "ahi_per_pos": {"Supine": 30.0, "Left": 8.0},
           "n_events_per_pos": {"Supine": 100, "Left": 13},
           "min_minutes_for_index": 15.0,
           "position_mapping_method": "coded"}
    assert not any("aanname" in str(r[1]) for r in _position_rows(pos, "nl"))
