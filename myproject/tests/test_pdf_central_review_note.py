"""Centrale apneus krijgen een handmatige-bevestigingsnoot in het rapport.

Overgenomen uit de productstance van FDA-gecleardee autoscoring (EnsoSleep
K210034: "CSA should be manually reviewed and modified as appropriate by a
clinician") en gemotiveerd door ons eigen basiskansdossier
(gegradeerde_subtypering_basiskans_20260902.md): onder ~5 % centrale
prevalentie telt de automaat een veelvoud van wat de mens ziet, en géén
gemeten drempel repareert dat. De telling is bruikbaar, het individuele
label niet — dat hoort de lezer te zien op de plek waar de telling staat.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_pdf_report import generate_pdf_report  # noqa: E402


def _pdf_text(path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("pdftotext niet beschikbaar")
    # Witruimte normaliseren: pdftotext breekt zinnen midden in een frase
    # af ("handmatige\nbevestiging"), en de toetsen zoeken frasen.
    return " ".join(out.stdout.decode("utf-8", "replace").split())


def _results(n_central=0, n_obstructive=20):
    n = n_central + n_obstructive
    events = ([{"type": "central", "onset_s": 100.0 + 45 * i,
                "duration_s": 15.0, "stage": "N2", "epoch": 3 + i,
                "confidence": 0.7} for i in range(n_central)] +
              [{"type": "obstructive", "onset_s": 2000.0 + 45 * i,
                "duration_s": 15.0, "stage": "N2", "epoch": 70 + i,
                "confidence": 0.8} for i in range(n_obstructive)])
    s = {"ahi_total": 10.0, "n_ah_total": n, "n_obstructive": n_obstructive,
         "n_central": n_central, "n_mixed": 0, "n_hypopnea": 0,
         "obstructive_index": 8.0,
         "central_index": 2.0 if n_central else 0.0,
         "mixed_index": 0.0, "hypopnea_index": 0.0,
         "ahi_rem": 9.0, "ahi_nrem": 11.0, "rem_min": 90.0,
         "nrem_min": 300.0, "ahi_rem_reliable": True}
    return {"patient_info": {"lang": "nl"},
            "pneumo": {"respiratory": {"success": True, "events": events,
                                       "summary": s}}}


def test_centrale_apneus_krijgen_bevestigingsnoot(tmp_path):
    out = tmp_path / "centraal.pdf"
    generate_pdf_report(_results(n_central=6), str(out), lang="nl")
    txt = _pdf_text(out)
    assert "handmatige bevestiging" in txt.lower()
    assert "centrale apneus" in txt.lower()


def test_zonder_centrale_apneus_geen_noot(tmp_path):
    """Een noot op elk rapport is geen noot (zelfde regel als de
    REM-caveat): zonder centrale events geen bevestigingsadvies."""
    out = tmp_path / "obstructief.pdf"
    generate_pdf_report(_results(n_central=0), str(out), lang="nl")
    assert "handmatige bevestiging" not in _pdf_text(out).lower()


def test_noot_in_rapporttaal(tmp_path):
    out = tmp_path / "centraal_en.pdf"
    generate_pdf_report(_results(n_central=6), str(out), lang="en")
    txt = _pdf_text(out)
    assert "manual confirmation" in txt.lower()
    assert "handmatige bevestiging" not in txt.lower()
