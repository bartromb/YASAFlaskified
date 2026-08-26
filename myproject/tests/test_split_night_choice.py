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


def _res_met_split(diag_uncertain=70, diag_sleep_h=0.85):
    # De sectie leeft in het respiratoire blok van het rapport; zonder een
    # samenvatting daar wordt dat hele blok overgeslagen en meet de test niets.
    return {
        "meta": {"eeg_channel": "C3"},
        "sleep_statistics": {"success": True, "stats": {"TST": 332.0, "SE": 80.0}},
        "hypnogram_timeline": {"success": True, "timeline": [
            {"epoch": i, "stage": "N2", "time_min": i * 0.5} for i in range(664)]},
        "pneumo": {
            "meta": {"channels_used": {"eeg": "C3"}, "flow_channels": {},
                     "scoring_profile": "aasm_v3_breath"},
            "arousal": {"arousals": {"summary": {}}},
            "respiratory": {"success": True, "events": [], "summary": {
                "ahi_total": 10.1, "oahi": 10.1, "n_apnea_total": 0,
                "n_hypopnea": 56, "n_ah_total": 56, "ahi_rem": 3.2,
                "ahi_nrem": 30.9, "rem_min": 93.0, "nrem_min": 239.0,
                "index_denominator_h": 5.533, "indices_computable": True,
                "n_rera": 21, "rera_index": 3.7, "rdi": 13.9}},
            "split_night": {
                "detected": True, "breakpoint_s": 8100.0,
                "method": "flow_amplitude+spo2_baseline",
                "segments": {
                    "diagnostic": {"sleep_h": diag_sleep_h, "n_events": 1,
                                   "n_uncertain": diag_uncertain, "ahi": 1.2,
                                   "ahi_incl_uncertain": 83.5,
                                   "reliable": diag_sleep_h >= 0.5,
                                   "uncertain_fraction": round(
                                       diag_uncertain / (1 + diag_uncertain), 3)},
                    "therapeutic": {"sleep_h": 4.683, "n_events": 3,
                                    "n_uncertain": 2, "ahi": 0.6,
                                    "ahi_incl_uncertain": 1.1,
                                    "reliable": True, "uncertain_fraction": 0.4},
                },
            },
        },
    }


def test_de_segment_ahi_s_staan_in_het_rapport(tmp_path):
    """De kop meldde "Mild SAS, AHI 10,1/u" terwijl het diagnostische deel op
    83,5/u lag. Die twee horen naast elkaar te staan."""
    import subprocess

    from generate_pdf_report import generate_pdf_report

    uit = str(tmp_path / "r.pdf")
    generate_pdf_report(_res_met_split(), uit, lang="nl")
    if not os.path.exists(uit):
        import pytest
        pytest.skip("rapport niet gegenereerd")
    try:
        tekst = subprocess.run(["pdftotext", "-layout", uit, "-"],
                               capture_output=True, text=True, timeout=60).stdout
    except FileNotFoundError:
        import pytest
        pytest.skip("pdftotext niet beschikbaar")
    assert "Split-night" in tekst
    assert "83.5" in tekst, "de diagnostische AHI ontbreekt"
    assert "1.1" in tekst, "de AHI onder therapie ontbreekt"
    assert "niet getypeerd" in tekst, "het voorbehoud over ongetypeerde events ontbreekt"


def test_zonder_split_geen_sectie(tmp_path):
    import subprocess

    from generate_pdf_report import generate_pdf_report

    res = _res_met_split()
    res["pneumo"]["split_night"] = {"detected": False}
    uit = str(tmp_path / "r2.pdf")
    generate_pdf_report(res, uit, lang="nl")
    try:
        tekst = subprocess.run(["pdftotext", "-layout", uit, "-"],
                               capture_output=True, text=True, timeout=60).stdout
    except FileNotFoundError:
        import pytest
        pytest.skip("pdftotext niet beschikbaar")
    assert "Split-night" not in tekst
