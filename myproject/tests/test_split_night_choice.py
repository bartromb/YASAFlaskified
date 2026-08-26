"""Split-night is een KEUZE in YF, en die keuze moet de analyse bereiken.

Drie standen: uit (default), automatisch detecteren, of handmatig het tijdstip
van CPAP-start opgeven. De handmatige waarde wint van de detector — wie erbij
was, weet het beter.

De valkuil die deze testen bewaken is niet "werkt de knop" maar "komt de keuze
aan": een formulierveld dat de jobconfig niet haalt, of een config die de worker
niet doorgeeft, levert een rapport op dat er normaal uitziet en de hele nacht
als één geheel telt — precies de fout die dit moest oplossen.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MYPROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lees(pad):
    with open(os.path.join(MYPROJECT, pad), encoding="utf-8") as f:
        return f.read()


def test_het_formulier_biedt_de_drie_standen():
    html = _lees("templates/channel_select.html")
    assert 'name="split_night"' in html
    for waarde in ('value="off"', 'value="auto"', 'value="manual"'):
        assert waarde in html, waarde
    assert 'name="split_night_minutes"' in html


def test_uit_is_de_default():
    """Een analyse mag niet stilzwijgend in tweeën gaan."""
    html = _lees("templates/channel_select.html")
    m = re.search(r'<option value="off"([^>]*)>', html)
    assert m and "selected" in m.group(1), "'off' is niet voorgeselecteerd"


def test_de_keuze_belandt_in_de_jobconfig():
    app_py = _lees("app.py")
    assert '"split_night": request.form.get("split_night", "off")' in app_py
    assert '"split_night_breakpoint_s"' in app_py


def test_de_worker_geeft_de_keuze_door():
    taken = _lees("tasks.py")
    assert 'split_night      = cfg.get("split_night", "off")' in taken
    assert 'split_night_breakpoint_s = cfg.get("split_night_breakpoint_s")' in taken


def test_minuten_worden_seconden_en_onzin_wordt_genegeerd():
    """Liever geen breekpunt dan een verkeerd breekpunt."""
    from app import _split_breakpoint_s

    assert _split_breakpoint_s("135") == 135 * 60
    assert _split_breakpoint_s("135,5") == 135.5 * 60
    assert _split_breakpoint_s("") is None
    assert _split_breakpoint_s(None) is None
    assert _split_breakpoint_s("straks") is None
    assert _split_breakpoint_s("-10") is None
    assert _split_breakpoint_s("0") is None


def test_het_rapport_toont_het_breekpunt():
    from generate_pdf_report import provenance_rows

    res = {"meta": {"eeg_channel": "C3"},
           "pneumo": {"meta": {"channels_used": {"eeg": "C3"}, "flow_channels": {}},
                      "arousal": {"arousals": {"summary": {}}},
                      "split_night": {"detected": True, "breakpoint_s": 8100.0,
                                      "method": "flow_amplitude+spo2_baseline"}}}
    regel = [r for r in provenance_rows(res, "nl") if "Split-night" in r[0]]
    assert regel, [r[0] for r in provenance_rows(res, "nl")]
    assert "2:15" in regel[0][1], regel


def test_het_rapport_zwijgt_zonder_split():
    from generate_pdf_report import provenance_rows

    res = {"meta": {"eeg_channel": "C3"},
           "pneumo": {"meta": {"channels_used": {"eeg": "C3"}, "flow_channels": {}},
                      "arousal": {"arousals": {"summary": {}}},
                      "split_night": {"detected": False}}}
    assert not [r for r in provenance_rows(res, "nl") if "Split-night" in r[0]]


def test_de_teksten_bestaan_in_vier_talen():
    from i18n import TRANSLATIONS

    for sleutel in ("split_night_title", "split_night_off", "split_night_auto",
                    "split_night_manual", "split_night_help", "prov_split_night"):
        entry = TRANSLATIONS[sleutel]
        for taal in ("nl", "fr", "en", "de"):
            assert entry.get(taal), f"{sleutel}/{taal}"
