"""Het rapport moet de per-event velden ook echt TONEN.

Aanleiding: v0.17.2 claimde dat `min_spo2` en de hypopnee-subtypering
"terugkomen in het rapport". Dat klopte niet — ze kwamen terug in de
event-records, maar de PDF-generator las `min_spo2` uit de
saturatiesamenvatting (het nachtminimum, een andere grootheid) en refereerde
`n_hypopnea_central` / `_mixed` nergens. Deze test rendert het rapport
daadwerkelijk en leest de tekst terug, zodat zo'n claim niet nog eens
ongetoetst kan blijven.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_pdf_report import generate_pdf_report  # noqa: E402
from i18n import get_translation as t  # noqa: E402


def _pdf_text(path: Path) -> str:
    """Tekstlaag van de PDF, of skip wanneer pdftotext ontbreekt."""
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("pdftotext niet beschikbaar")
    return out.stdout.decode("utf-8", "replace")


def _event(onset, etype, conf=0.9, nadir=None):
    e = {"type": etype, "onset_s": onset, "duration_s": 20.0,
         "stage": "N2", "epoch": int(onset // 30), "confidence": conf,
         "desaturation_pct": 4.0, "flow_reduction": 55.0}
    if nadir is not None:
        e["min_spo2"] = nadir
    return e


def _results(events, n_central=0, n_mixed=0):
    return {
        "patient_info": {"lang": "nl"},
        "pneumo": {
            "respiratory": {
                "success": True,
                "events": events,
                "summary": {
                    "ahi_total": 20.0, "n_ah_total": len(events),
                    "n_obstructive": 1, "n_central": 0, "n_mixed": 0,
                    "n_hypopnea": sum(1 for e in events
                                      if "hypopnea" in e["type"]),
                    "n_hypopnea_central": n_central,
                    "n_hypopnea_mixed": n_mixed,
                    "obstructive_index": 2.0, "central_index": 0.0,
                    "mixed_index": 0.0, "hypopnea_index": 18.0,
                },
            },
            "spo2": {
                "success": True,
                "summary": {"mean_spo2": 94, "baseline_spo2": 96,
                            "min_spo2": 71, "pct_below_90": 3.0,
                            "odi_3pct": 12.0, "odi_4pct": 8.0},
            },
        },
    }


def test_event_nadir_is_shown_and_differs_from_the_night_minimum(tmp_path):
    """Het nachtminimum kan van een artefact komen; dit getal hoort bij een event."""
    events = [_event(100.0, "obstructive", nadir=None),
              _event(200.0, "hypopnea", nadir=88.0),
              _event(300.0, "hypopnea", nadir=84.0)]
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results(events), str(out), lang="nl")
    txt = _pdf_text(out)

    label = t("pdf_event_spo2_nadir", "nl")
    assert label in txt, "de per-event nadir hoort in het rapport te staan"
    line = next(ln for ln in txt.splitlines() if label in ln)
    assert "84" in line, line
    assert "71" not in line, "dit is niet het nachtminimum"
    assert "71" in txt, "het nachtminimum blijft daarnaast staan"


def test_nadir_row_is_absent_when_no_event_carries_one(tmp_path):
    events = [_event(100.0, "hypopnea"), _event(200.0, "hypopnea")]
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results(events), str(out), lang="nl")
    assert t("pdf_event_spo2_nadir", "nl") not in _pdf_text(out)


def test_hypopnea_subtypes_appear_when_present(tmp_path):
    events = [_event(100.0, "hypopnea", nadir=90.0),
              _event(200.0, "hypopnea_central", conf=0.7, nadir=89.0),
              _event(300.0, "hypopnea_mixed", conf=0.5, nadir=88.0)]
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results(events, n_central=1, n_mixed=1), str(out),
                        lang="nl")
    txt = _pdf_text(out)
    assert t("pdf_hyp_sub_central", "nl") in txt
    assert t("pdf_hyp_sub_mixed", "nl") in txt


def test_subtype_rows_use_a_glyph_the_font_actually_has(tmp_path):
    """↳ ontbreekt in het lettertype en werd een zwart blokje in productie.

    Erger nog: ■ is in dit rapport de legenda-kleurmarkering (■ W ■ N1,
    ■ OA obstructief), dus het las als een derde betekenis van hetzelfde
    teken. Deze test vangt elke glyph die de font-fallback triggert.
    """
    events = [_event(100.0, "hypopnea", nadir=90.0),
              _event(200.0, "hypopnea_central", conf=0.7, nadir=89.0)]
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results(events, n_central=1), str(out), lang="nl")
    txt = _pdf_text(out)
    line = next(ln for ln in txt.splitlines()
                if t("pdf_hyp_sub_central", "nl") in ln)
    assert "■" not in line, f"font-fallback in de subtyperij: {line!r}"
    assert "↳" not in line
    assert "·" in line, line


def test_subtype_rows_stay_out_of_a_purely_obstructive_study(tmp_path):
    """Nulrijen zijn ruis in een rapport waarin alles obstructief is."""
    events = [_event(100.0, "hypopnea", nadir=90.0),
              _event(200.0, "hypopnea", nadir=89.0)]
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results(events), str(out), lang="nl")
    txt = _pdf_text(out)
    assert t("pdf_hyp_sub_central", "nl") not in txt
    assert t("pdf_hyp_sub_mixed", "nl") not in txt


def _results_with_sensors(dual, apnea_ch, hypop_ch):
    r = _results([_event(100.0, "hypopnea", nadir=90.0)])
    r["pneumo"]["respiratory"]["dual_sensor"] = dual
    # sectie 8c wordt alleen gerenderd bij een breath_analysis met ademteugen
    r["pneumo"]["respiratory"]["breath_analysis"] = {
        "n_breaths": 12000, "n_bb_apneas": 40, "n_bb_hypopneas": 120,
        "avg_flattening": 0.22}
    r["pneumo"]["meta"] = {"flow_channels": {
        "apnea_sensor": apnea_ch, "hypopnea_sensor": hypop_ch,
        "dual_sensor": dual}}
    return r


def test_two_sensors_state_that_aasm_was_followed(tmp_path):
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results_with_sensors(True, "Flow Th.", "Pressure Flow"),
                        str(out), lang="nl")
    txt = _pdf_text(out).replace("\n", " ")
    assert "Dual-sensor" in txt
    assert "Eén flowkanaal" not in txt


def test_one_sensor_says_so_and_names_the_channel(tmp_path):
    """Het geval dat zweeg is juist het geval dat iets moet melden.

    Apneus op nasale druk overdetecteren t.o.v. de thermistor; de AASM
    schrijft de thermistor daar juist om voor.
    """
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results_with_sensors(False, "Pressure Flow", "Pressure Flow"),
                        str(out), lang="nl")
    txt = _pdf_text(out).replace("\n", " ")
    assert "Eén flowkanaal" in txt
    assert "Pressure Flow" in txt
    assert "overdetectie" in txt
    assert "Dual-sensor" not in txt


def test_confidence_band_caption_is_present(tmp_path):
    """De sterrenkoppen zijn een rangschikking, geen kans — dat moet erbij staan."""
    events = [_event(100.0, "hypopnea", nadir=90.0)]
    out = tmp_path / "r.pdf"
    generate_pdf_report(_results(events), str(out), lang="nl")
    txt = _pdf_text(out).replace("\n", " ")
    assert "niet als kans" in txt


# ─────────────────────────────────────────────────────────────────
#  Dual-sensor: corroboratiekolommen en de terugvalmelding
# ─────────────────────────────────────────────────────────────────

def _dual_results(with_corrob=True, fallback=False):
    events = [
        {**_event(100.0, "obstructive", nadir=88.0), "corroboration": "both"},
        {**_event(200.0, "obstructive", nadir=87.0),
         "corroboration": "thermistor_only"},
        {**_event(300.0, "central", nadir=86.0), "corroboration": "pressure_only"},
        _event(400.0, "hypopnea", nadir=90.0),
    ]
    r = _results(events)
    rs = r["pneumo"]["respiratory"]
    rs["summary"].update({"n_obstructive": 2, "n_central": 1, "n_mixed": 0})
    rs["breath_analysis"] = {"n_breaths": 9000, "n_bb_apneas": 20,
                             "n_bb_hypopneas": 40, "avg_flattening": 0.2}
    if with_corrob:
        rs["dual_sensor_apnea"] = {"n_both": 1, "n_thermistor_only": 1,
                                   "n_pressure_only": 1, "n_kept": 3}
    r["pneumo"]["meta"] = {"dual_sensor_fallback": {
        "requested": True, "performed": not fallback,
        "channel": "Pressure Flow" if fallback else None}}
    return r


def test_corroboration_columns_appear_for_the_dual_profile(tmp_path):
    out = tmp_path / "r.pdf"
    generate_pdf_report(_dual_results(), str(out), lang="nl")
    txt = _pdf_text(out).replace("\n", " ")
    for key in ("pdf_corrob_both", "pdf_corrob_therm", "pdf_corrob_press"):
        head = t(key, "nl").replace("\n", " ")
        assert head.split()[0] in txt, key
    assert "niet afgewezen" in txt, "de noot onder de tabel hoort erbij"


def test_corroboration_columns_stay_away_for_a_single_sensor_run(tmp_path):
    """Bij een enkele sensor zouden het drie lege kolommen zijn."""
    out = tmp_path / "r.pdf"
    generate_pdf_report(_dual_results(with_corrob=False), str(out), lang="nl")
    assert "niet afgewezen" not in _pdf_text(out).replace("\n", " ")


def test_the_fallback_warning_lands_in_the_attention_box(tmp_path):
    """Gevraagd algoritme niet uitgevoerd mag niet stilzwijgend gebeuren."""
    out = tmp_path / "r.pdf"
    generate_pdf_report(_dual_results(with_corrob=False, fallback=True),
                        str(out), lang="nl")
    txt = _pdf_text(out).replace("\n", " ")
    assert "Dual-sensor scoring gevraagd maar niet uitgevoerd" in txt
    assert "Pressure Flow" in txt


def test_no_fallback_warning_when_the_dual_run_succeeded(tmp_path):
    out = tmp_path / "r.pdf"
    generate_pdf_report(_dual_results(fallback=False), str(out), lang="nl")
    assert "niet uitgevoerd" not in _pdf_text(out).replace("\n", " ")
