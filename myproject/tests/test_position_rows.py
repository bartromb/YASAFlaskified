"""Een houding waar te kort in geslapen is, verdwijnt niet stilzwijgend.

psgscoring geeft sinds 0.27.1 `None` voor een positie-AHI onder de 15 minuten
— de tabel toonde daarvoor "AHI Supine 120,0/u" uit één event in 0,5 min. De
rapportlaag sloeg elke `None` over, en dan staat er niets: de arts ziet niet
dat de patiënt wél op de rug lag, alleen te kort om iets over te zeggen.

Onderscheid dus drie gevallen:
  genoeg tijd   → het getal
  te kort       → "— (< 15 min)" mét de minuten
  nooit gelegen → helemaal geen rij
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import _position_rows  # noqa: E402

POS = {
    "ahi_per_pos":    {"Supine": None, "Left": 12.4, "Right": None,
                       "Prone": None, "Upright": None},
    "sleep_time_min": {"Supine": 0.5, "Left": 300.0, "Right": 8.0,
                       "Prone": 0.0, "Upright": None},
    "min_minutes_for_index": 15.0,
}


def _rows(lang="nl"):
    return {r[0]: r[1] for r in _position_rows(POS, lang)}


def test_a_position_with_enough_sleep_shows_its_index():
    assert _rows()["AHI Left"] == "12.4 /u"


def test_a_position_slept_in_too_briefly_says_so_with_the_minutes():
    r = _rows()
    assert "AHI Supine" in r, "de rij verdwijnt en de arts ziet niets"
    assert "0.5" in r["AHI Supine"] and "15" in r["AHI Supine"], r["AHI Supine"]
    assert "120" not in r["AHI Supine"]


def test_a_position_never_slept_in_gets_no_row():
    r = _rows()
    assert "AHI Prone" not in r
    assert "AHI Upright" not in r


@pytest.mark.parametrize("lang", ["nl", "fr", "en", "de"])
def test_every_language_renders_the_short_marker(lang):
    txt = {r[0]: r[1] for r in _position_rows(POS, lang)}["AHI Right"]
    assert "{" not in txt, txt
    assert "8" in txt


def test_an_old_result_without_the_minutes_still_renders():
    """Jobs van vóór dit veld dragen geen `min_minutes_for_index`."""
    oud = {"ahi_per_pos": {"Supine": 9.9, "Left": None},
           "sleep_time_min": {"Supine": 200.0, "Left": 3.0}}
    r = {x[0]: x[1] for x in _position_rows(oud, "nl")}
    assert r["AHI Supine"] == "9.9 /u"
    assert "AHI Left" in r


def test_no_position_analysis_means_no_rows():
    assert _position_rows({}, "nl") == []
    assert _position_rows(None, "nl") == []
