"""Het rapport moet zeggen welk kanaal welke analyse voedde.

Drie fouten van augustus 2026 waren dezelfde soort fout: het rapport beschreef
de methode in plaats van de uitvoering. Welk EMG de staging voedde stond
nergens — en week af van wat het kanaaloverzicht in de UI toonde; de sensornoot
volgde het profiel in plaats van de afgekeurde thermistor; en dat de vijf
afgeleide analyses een ander flowkanaal lezen dan de apneudetectie was
onzichtbaar. Twee runs van dezelfde nacht waren daardoor niet te vergelijken.
"""

import os
import sys

from generate_pdf_report import provenance_rows
from i18n import TRANSLATIONS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _results(**fc):
    return {
        "meta": {"eeg_channel": "C4:A1", "eog_channel": "EOG2:A1",
                 "emg_channel": "EMG3"},
        "pneumo": {"meta": {
            "scoring_profile": "aasm_v3_rec",
            "flow_channels": {
                "apnea_sensor":    fc.get("apnea", "Flow Th."),
                "hypopnea_sensor": fc.get("hypopnea", "Pressure Flow"),
                "reference_sensor": fc.get("reference"),
                "dual_sensor":     fc.get("dual", True),
                "thermistor_rejected": fc.get("rejected"),
                "thermistor_check": ({"agreement": fc["agreement"]}
                                     if "agreement" in fc else None),
            },
        }},
    }


def _as_dict(rows):
    return {label: value for label, value in rows}


def test_the_staging_channels_are_named():
    """De vraag 'welk EMG heeft hij gebruikt?' moet het rapport beantwoorden."""
    d = _as_dict(provenance_rows(_results()))
    assert d[TRANSLATIONS["prov_staging_eeg"]["nl"]] == "C4:A1"
    assert d[TRANSLATIONS["prov_staging_eog"]["nl"]] == "EOG2:A1"
    assert d[TRANSLATIONS["prov_staging_emg"]["nl"]] == "EMG3"


def test_a_missing_staging_emg_shows_a_dash_not_a_blank():
    results = _results()
    results["meta"]["emg_channel"] = None
    assert _as_dict(provenance_rows(results))[TRANSLATIONS["prov_staging_emg"]["nl"]] == "—"


def test_the_apnea_and_hypopnea_sensors_are_named_separately():
    d = _as_dict(provenance_rows(_results()))
    assert d[TRANSLATIONS["prov_apnea"]["nl"]] == "Flow Th."
    assert d[TRANSLATIONS["prov_hypopnea"]["nl"]] == "Pressure Flow"


def test_a_deviating_reference_sensor_is_shown():
    """aasm_v3_pressure laat vijf afgeleide analyses de neusdruk lezen."""
    d = _as_dict(provenance_rows(_results(reference="Pressure Flow")))
    assert d[TRANSLATIONS["prov_reference"]["nl"]] == "Pressure Flow"


def test_a_reference_equal_to_the_apnea_channel_is_not_repeated():
    """Ruis: standaard leest alles hetzelfde kanaal, dat hoeft geen regel."""
    rows = provenance_rows(_results(reference="Flow Th."))
    assert TRANSLATIONS["prov_reference"]["nl"] not in _as_dict(rows)


def test_a_rejected_thermistor_is_distinguished_from_an_absent_one():
    rejected = _as_dict(provenance_rows(
        _results(apnea="Pressure Flow", dual=False,
                 rejected="Flow Th.", agreement=0.32)
    ))[TRANSLATIONS["prov_thermistor"]["nl"]]
    absent = _as_dict(provenance_rows(
        _results(apnea="Pressure Flow", dual=False)
    ))[TRANSLATIONS["prov_thermistor"]["nl"]]

    assert "Flow Th." in rejected and "0.32" in rejected
    assert TRANSLATIONS["prov_therm_rejected"]["nl"] in rejected
    assert absent == TRANSLATIONS["prov_therm_absent"]["nl"]
    assert rejected != absent


def test_a_usable_thermistor_says_so():
    val = _as_dict(provenance_rows(_results(agreement=0.71)))[
        TRANSLATIONS["prov_thermistor"]["nl"]]
    assert TRANSLATIONS["prov_therm_usable"]["nl"] in val and "0.71" in val


def test_profile_and_software_versions_are_recorded():
    from version import PSGSCORING_VERSION, __version__
    d = _as_dict(provenance_rows(_results()))
    assert d[TRANSLATIONS["prov_profile"]["nl"]] == "aasm_v3_rec"
    sw = d[TRANSLATIONS["prov_software"]["nl"]]
    assert PSGSCORING_VERSION in sw and __version__ in sw


def test_an_empty_result_does_not_raise():
    """Het rapport mag nooit vallen over een ontbrekend herkomstveld."""
    rows = provenance_rows({})
    assert rows and all(len(r) == 2 and r[1] for r in rows)


def test_every_provenance_label_is_translated_in_all_four_languages():
    keys = ["rpt_sec_provenance", "prov_staging_eeg", "prov_staging_eog",
            "prov_staging_emg", "prov_apnea", "prov_hypopnea", "prov_reference",
            "prov_thermistor", "prov_therm_usable", "prov_therm_rejected",
            "prov_therm_absent", "prov_profile", "prov_software", "prov_note"]
    for key in keys:
        for lang in ("nl", "fr", "en", "de"):
            assert TRANSLATIONS[key][lang].strip(), f"{key}/{lang} ontbreekt"
