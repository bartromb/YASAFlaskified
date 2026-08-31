"""Het rapport en de bibliotheek moeten dezelfde veldnamen bedoelen.

WAAROM DEZE TEST BESTAAT
------------------------
De testfixture hiernaast (`test_split_night_all_indices_render.py`) bouwt het
`split_night`-blok met de hand. Zo'n fixture bewijst dat de PDF een veld TOONT,
maar niet dat psgscoring datzelfde veld ook zo NOEMT. Precies daar is het al
eerder misgegaan: `segment_spo2()` rekende sinds 0.29.0 keurig per segment en
geen enkele consument las het, en `min_spo2` in het rapport bleek het
nachtminimum in plaats van het event-minimum.

Deze test roept de segmentfuncties van psgscoring ECHT aan en voert hun uitvoer
ongewijzigd aan de rapportgenerator. Hernoemt de bibliotheek een veld, dan valt
hier een getal weg uit de PDF en faalt dit -- in plaats van dat er stilletjes
een streepje verschijnt.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_pdf_report import generate_pdf_report  # noqa: E402

BREUK = 2 * 3600.0
HYP = ["N2"] * (7 * 120)


def _pdf_text(path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("pdftotext niet beschikbaar")
    return out.stdout.decode("utf-8", "replace")


@pytest.fixture(scope="module")
def echt_split_blok():
    """`split_night` zoals psgscoring hem werkelijk oplevert."""
    sn = pytest.importorskip("psgscoring.split_night")

    events = [{"onset_s": 60.0 + 100 * i, "duration_s": 20.0,
               "type": "obstructive", "stage": "N2"} for i in range(70)]
    events += [{"onset_s": BREUK + 600.0 + 900 * i, "duration_s": 20.0,
                "type": "hypopnea", "stage": "N2"} for i in range(5)]
    arousals = [{"onset_s": 90.0 + 100 * i, "duration_s": 5.0,
                 "type": "respiratory" if i % 5 else "spontaneous"}
                for i in range(70)]
    plm = [{"onset_s": 120.0 + 60 * i, "duration_s": 2.0, "is_plm": True}
           for i in range(44)]
    reras = [30.0 + 300 * i for i in range(20)]

    return {
        "detected": True, "breakpoint_s": BREUK, "method": "manual",
        "segments": sn.segment_indices(events, HYP, BREUK),
        "arousal": sn.segment_arousals(arousals, HYP, BREUK),
        "rdi": sn.segment_rdi(events, reras, HYP, BREUK),
        "plm": sn.segment_plm(plm, HYP, BREUK),
    }


def _results(split_blok):
    return {
        "patient_info": {"lang": "nl"},
        "pneumo": {
            "split_night": split_blok,
            "respiratory": {
                "success": True, "events": [],
                "summary": {"ahi_total": 10.7, "n_ah_total": 75,
                            "n_obstructive": 70, "n_central": 0, "n_mixed": 0,
                            "n_hypopnea": 5, "obstructive_index": 10.0,
                            "central_index": 0.0, "mixed_index": 0.0,
                            "hypopnea_index": 0.7},
            },
            "spo2": {"success": True,
                     "summary": {"mean_spo2": 94, "baseline_spo2": 95,
                                 "min_spo2": 71, "pct_below_90": 4.4,
                                 "odi_3pct": 10.5, "odi_4pct": 7.0}},
        },
    }


def test_de_bibliotheekvelden_landen_in_de_pdf(echt_split_blok, tmp_path):
    """Elk getal dat psgscoring per segment oplevert, hoort in de PDF terug.

    Faalt dit met een streepje in plaats van een getal, dan heet het veld in de
    bibliotheek anders dan het rapport denkt.
    """
    out = tmp_path / "echt.pdf"
    generate_pdf_report(_results(echt_split_blok), str(out), lang="nl")
    txt = _pdf_text(out)

    verwacht = {
        "AHI diagnostisch": echt_split_blok["segments"]["diagnostic"]["ahi"],
        "arousalindex": echt_split_blok["arousal"]["diagnostic"]["arousal_index"],
        "RDI": echt_split_blok["rdi"]["diagnostic"]["rdi"],
        "PLM-index": echt_split_blok["plm"]["diagnostic"]["plm_index"],
    }
    ontbreekt = [f"{naam}={w}" for naam, w in verwacht.items()
                 if w is None or f"{float(w):.1f}" not in txt]
    assert not ontbreekt, (
        f"deze door psgscoring geleverde waarden staan niet in de PDF: "
        f"{ontbreekt} — veldnaam veranderd?")


def test_de_deelindices_van_de_arousals_landen_ook(echt_split_blok, tmp_path):
    out = tmp_path / "echt2.pdf"
    generate_pdf_report(_results(echt_split_blok), str(out), lang="nl")
    txt = _pdf_text(out)
    w = echt_split_blok["arousal"]["diagnostic"]["respiratory_arousal_index"]
    assert w is not None, "psgscoring levert geen respiratoire deelindex"
    assert f"{float(w):.1f}" in txt


def test_een_ontbrekende_familie_laat_de_rest_staan(echt_split_blok, tmp_path):
    """Draait een oudere psgscoring zonder `plm`, dan hoort de tabel er nog te
    zijn met de families die er wel zijn."""
    blok = dict(echt_split_blok)
    blok.pop("plm")
    out = tmp_path / "zonder_plm.pdf"
    generate_pdf_report(_results(blok), str(out), lang="nl")
    txt = _pdf_text(out)
    assert f"{echt_split_blok['rdi']['diagnostic']['rdi']:.1f}" in txt
    assert "PLMI" not in txt
