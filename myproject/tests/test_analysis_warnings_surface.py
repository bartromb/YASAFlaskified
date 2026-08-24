"""`analysis_warnings` werd geschreven en door niemand gelezen.

`tasks.py` zet ze in de resultaten-JSON — de blokkerende
"alle epochs als artefact"-melding sinds v0.31, en sinds v0.34.1 ook de
ontbrekende EMG/EOG-kanalen. Een grep door de hele codebase levert precies één
schrijver en **nul lezers** op: geen PDF-sectie, geen sjabloon, geen route.

Dat is dezelfde fout als de bug die deze release repareert, één laag hoger. Een
waarschuwing die alleen in een JSON-bestand staat is geen waarschuwing; de
arousal-regressie bleef maanden onzichtbaar omdat de enige melding in de
workerlog stond.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import _clinical_flags  # noqa: E402


def _flags(warnings, lang="nl"):
    return _clinical_flags({}, {}, {}, {}, lang=lang, warnings=warnings)


def test_a_missing_chin_emg_reaches_the_attention_box():
    out = _flags([{"code": "emg_channel_missing", "severity": "warning",
                   "message": "Het opgegeven kin-EMG-kanaal 'EMG1' zit niet "
                              "in dit EDF-bestand."}])
    assert out, "de waarschuwing haalt het rapport niet"
    assert any("EMG" in ln for ln in out), out


def test_a_blocking_warning_is_shown_too():
    out = _flags([{"code": "all_epochs_artefact", "severity": "blocking",
                   "message": "Alle 1174 epochs zijn als artefact gemarkeerd."}])
    assert out and any("artefact" in ln.lower() for ln in out), out


@pytest.mark.parametrize("lang", ["nl", "fr", "en", "de"])
def test_every_language_renders_the_known_codes(lang):
    for code in ("emg_channel_missing", "eog_channel_missing"):
        out = _flags([{"code": code, "severity": "warning", "message": "x"}],
                     lang=lang)
        assert out, f"{code} in {lang} levert niets"
        assert "{" not in out[0], f"niet-ingevulde placeholder: {out[0]}"


def test_an_unknown_code_still_shows_its_message():
    """Een nieuwe code mag niet stil verdwijnen omdat er nog geen
    vertaalsleutel voor is."""
    out = _flags([{"code": "iets_nieuws", "severity": "warning",
                   "message": "Er is iets aan de hand."}])
    assert out == ["Er is iets aan de hand."]


def test_no_warnings_means_no_extra_flags():
    assert _flags([]) == []
    assert _flags(None) == []
