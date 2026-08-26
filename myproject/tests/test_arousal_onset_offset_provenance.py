"""Een verschoven arousal-onset moet in het rapport STAAN.

psgscoring kreeg op 26-08-2026 de vlag `arousal_onset_offset_s` (default 0,0).
Staat die aan, dan liggen de arousal-onsets in het rapport ergens anders dan de
detector ze vond, en zijn AHI en RDI met die verschoven arousals berekend.

Dit is precies het patroon waar de REM-AHI-caveat op strandde: de bibliotheek
produceerde een veld, het rapport las het nooit, en niemand merkte het tot er
naar gevraagd werd. Twee rapporten van dezelfde nacht zouden verschillende
onsets tonen zonder dat er iets in staat dat het verschil verklaart.

De regel toont NIETS bij offset 0 -- de default. Een provenancetabel die op elk
rapport een regel "0,0 s" zet, verdrinkt de regels die er wel toe doen.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import provenance_rows  # noqa: E402


def _results(offset):
    """Minimaal resultaat met de arousal-samenvatting waar de vlag in landt."""
    summary = {"derivations": ["C3", "C4"]}
    if offset is not None:
        summary["onset_offset_s"] = offset
    return {
        "meta": {"eeg_channel": "C3"},
        "pneumo": {
            "meta": {"channels_used": {"eeg": "C3"}, "flow_channels": {}},
            "arousal": {"arousals": {"summary": summary}},
        },
    }


def _labels(rows):
    return [r[0] for r in rows]


def _value(rows, needle):
    for lab, val in rows:
        if needle in lab:
            return val
    return None


def test_een_verschuiving_verschijnt_met_teken_en_eenheid():
    rows = provenance_rows(_results(2.0), "nl")
    val = _value(rows, "verschoven")
    assert val == "+2.0 s", (val, _labels(rows))


def test_een_negatieve_verschuiving_toont_zijn_teken():
    assert _value(provenance_rows(_results(-1.5), "nl"), "verschoven") == "-1.5 s"


def test_default_nul_zet_geen_regel():
    """Anders staat er op elk rapport een regel die niets zegt."""
    assert _value(provenance_rows(_results(0.0), "nl"), "verschoven") is None


def test_ontbrekend_veld_zet_geen_regel():
    """Een oudere psgscoring levert de sleutel niet; dat mag niet knallen."""
    assert _value(provenance_rows(_results(None), "nl"), "verschoven") is None


def test_onleesbare_waarde_zet_geen_regel():
    """Liever geen regel dan een regel met onzin erin."""
    assert _value(provenance_rows(_results("twee"), "nl"), "verschoven") is None


def test_het_label_bestaat_in_vier_talen():
    """Het rapport gaat naar centra die het in hun eigen taal lezen."""
    from i18n import TRANSLATIONS

    entry = TRANSLATIONS["prov_arousal_onset_offset"]
    for taal in ("nl", "fr", "en", "de"):
        assert entry.get(taal), f"{taal} ontbreekt"
    assert len(set(entry[t] for t in ("nl", "fr", "en", "de"))) == 4, \
        "twee talen delen dezelfde tekst — waarschijnlijk een kopieerfout"
