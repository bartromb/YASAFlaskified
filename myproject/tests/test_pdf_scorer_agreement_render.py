"""De scoordersverwachting moet in de GERENDERDE PDF staan, niet alleen in een veld.

psgscoring 0.31.x levert `summary["scorer_agreement_expectation"]`: de
verwachte overeenstemming tussen twee menselijke scoorders bij deze
ziektelast (330 scoorderparen, PSG-IPA). Het veld beschrijft de OPNAME, niet
de detector — en het rapport las het nergens. Dat is exact de
`ahi_rem_caveat`-fout van v0.15.1: een geverifieerd bibliotheekveld zonder
lezer. Daarom rendert deze toets het rapport echt en leest de tekstlaag terug.
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
    return out.stdout.decode("utf-8", "replace")


def _results(expectation):
    events = [{"type": "hypopnea", "onset_s": 100.0 + 60 * i,
               "duration_s": 20.0, "stage": "N2",
               "epoch": int((100.0 + 60 * i) // 30), "confidence": 0.9,
               "desaturation_pct": 4.0, "flow_reduction": 55.0}
              for i in range(30)]
    s = {"ahi_total": 12.4, "n_ah_total": len(events),
         "n_obstructive": 0, "n_central": 0, "n_mixed": 0,
         "n_hypopnea": len(events), "obstructive_index": 0.0,
         "central_index": 0.0, "mixed_index": 0.0, "hypopnea_index": 12.4,
         "ahi_rem": 10.0, "ahi_nrem": 12.9, "rem_min": 95.0,
         "nrem_min": 229.0, "ahi_rem_reliable": True}
    if expectation is not None:
        s["scorer_agreement_expectation"] = expectation
    return {"patient_info": {"lang": "nl"},
            "pneumo": {"respiratory": {"success": True, "events": events,
                                       "summary": s}}}


VERW = {"what": ("verwachte overeenstemming tussen twee menselijke scoorders "
                 "bij deze ziektelast; beschrijft de OPNAME, niet de detector"),
        "source": "PSG-IPA, 5 opnames, 12 scoorders, event-F1 met IoU 0,20",
        "n_scorer_pairs": 330, "f1_human": 0.61, "band": "matig"}


def test_de_verwachting_staat_in_de_pdf(tmp_path):
    out = tmp_path / "verwachting.pdf"
    generate_pdf_report(_results(VERW), str(out), lang="nl")
    txt = _pdf_text(out)
    assert "0.61" in txt or "0,61" in txt, (
        "het verwachte menselijke overeenstemmingsniveau ontbreekt")
    assert "330" in txt, (
        "de bron (330 scoorderparen) hoort erbij — zonder herkomst leest het "
        "getal als een eigenschap van de software")


def test_de_noot_beschrijft_de_opname_niet_de_detector(tmp_path):
    """De formulering moet de kant van het veld kiezen: dit zegt hoe eens
    MENSEN het zouden zijn over deze nacht — niet hoe goed de detector is."""
    out = tmp_path / "kant.pdf"
    generate_pdf_report(_results(VERW), str(out), lang="nl")
    txt = _pdf_text(out).lower()
    assert "scoorders" in txt or "scorers" in txt


def test_zonder_veld_geen_noot(tmp_path):
    """Oudere psgscoring-uitvoer heeft het veld niet; het rapport mag dan
    niets verzinnen."""
    out = tmp_path / "zonder.pdf"
    generate_pdf_report(_results(None), str(out), lang="nl")
    assert "330" not in _pdf_text(out)


def test_geen_glyph_die_het_font_mist(tmp_path):
    out = tmp_path / "glyph.pdf"
    generate_pdf_report(_results(VERW), str(out), lang="nl")
    for line in _pdf_text(out).splitlines():
        if "330" in line:
            assert "■" not in line, f"font-fallback in de noot: {line!r}"
