"""De REM-kwalificatie moet in de GERENDERDE PDF staan, niet alleen in een veld.

Aanleiding, en de reden dat deze toets bestaat naast de eenheidstoetsen in
`test_report_index_consistency.py`:

psgscoring 0.15.1 voegde `ahi_rem_reliable` en `ahi_rem_caveat` toe. Dat werd
geverifieerd door de bibliotheek in de productiecontainer aan te roepen — en
daarmee "geverifieerd" gemeld. Het rapport las die velden echter nergens. Op
opname 62942a61 (22 min REM) stond daardoor "REM AHI 64.2 /u" naast
"NREM AHI 38.6 /u" zonder één woord over de 22 minuten waarop de eerste rustte.
Dat leest als REM-predominante OSA, een patroon met behandelconsequenties,
terwijl het om ongeveer 24 events gaat.

Een toets op de helper zou dat niet gevangen hebben: de helper wérkte. Alleen
riep niemand hem aan. Daarom rendert deze toets het rapport echt en leest de
tekstlaag terug.
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


def _results(rem_min, reliable):
    """Een opname met REM-AHI 64.2 naast NREM-AHI 38.6 — de verhouding uit
    62942a61, waar het misverstand zichtbaar werd."""
    events = [{"type": "hypopnea", "onset_s": 100.0 + 60 * i,
               "duration_s": 20.0, "stage": "R" if i < 24 else "N2",
               "epoch": int((100.0 + 60 * i) // 30), "confidence": 0.9,
               "desaturation_pct": 4.0, "flow_reduction": 55.0}
              for i in range(30)]
    return {
        "patient_info": {"lang": "nl"},
        "pneumo": {
            "respiratory": {
                "success": True,
                "events": events,
                "summary": {
                    "ahi_total": 40.7, "n_ah_total": len(events),
                    "n_obstructive": 0, "n_central": 0, "n_mixed": 0,
                    "n_hypopnea": len(events),
                    "obstructive_index": 0.0, "central_index": 0.0,
                    "mixed_index": 0.0, "hypopnea_index": 40.7,
                    "ahi_rem": 64.2, "ahi_nrem": 38.6,
                    "rem_min": rem_min, "nrem_min": 229.0,
                    "ahi_rem_reliable": reliable,
                },
            },
        },
    }


def test_a_rem_ahi_on_too_little_rem_says_so_in_the_pdf(tmp_path):
    out = tmp_path / "weinig_rem.pdf"
    generate_pdf_report(_results(rem_min=22.5, reliable=False), str(out),
                        lang="nl")
    txt = _pdf_text(out)
    assert "64.2" in txt, "de REM-AHI hoort er gewoon te staan"
    assert "22 min REM" in txt, \
        "de REM-AHI staat er zonder te zeggen op hoeveel REM hij rust"
    assert "30 min" in txt, "de drempel waaraan getoetst wordt ontbreekt"


def test_the_caveat_uses_no_glyph_the_font_lacks(tmp_path):
    """⚠ ontbreekt in het ingebedde lettertype en wordt een zwart blokje — dat
    is in dit rapport bovendien al de legenda-kleurmarkering, dus het las als
    een tweede betekenis van hetzelfde teken. Zelfde val als de ↳ in v0.17.2."""
    out = tmp_path / "glyph.pdf"
    generate_pdf_report(_results(rem_min=22.5, reliable=False), str(out),
                        lang="nl")
    for line in _pdf_text(out).splitlines():
        if "min REM (" in line:
            assert "■" not in line, f"font-fallback in de REM-noot: {line!r}"


def test_both_rem_ahi_rows_show_the_same_number(tmp_path):
    """psgscoring levert deze grootheid twee keer (`ahi_rem` uit respiratory.py,
    `rem_ahi` uit pipeline.py, elk met een eigen REM-definitie). Het rapport
    toont hem op twee plaatsen; twee verschillende getallen onder labels als
    "REM AHI" en "AHI REM" zijn voor de lezer niet te scheiden."""
    r = _results(rem_min=22.5, reliable=False)
    r["pneumo"]["respiratory"]["summary"]["rem_ahi"] = 11.1   # afwijkend dubbel
    r["pneumo"]["respiratory"]["summary"]["nrem_ahi"] = 22.2
    out = tmp_path / "dubbel.pdf"
    generate_pdf_report(r, str(out), lang="nl")
    txt = _pdf_text(out)
    assert "11.1" not in txt, "§8c toont nog de tweede berekening"
    assert "22.2" not in txt
    assert txt.count("64.2") >= 2, "beide REM-AHI-rijen horen dezelfde bron te lezen"


def test_enough_rem_leaves_the_report_clean(tmp_path):
    """Een waarschuwing op elk rapport is geen waarschuwing meer."""
    out = tmp_path / "genoeg_rem.pdf"
    generate_pdf_report(_results(rem_min=91.0, reliable=True), str(out),
                        lang="nl")
    txt = _pdf_text(out)
    assert "64.2" in txt
    assert "min REM (" not in txt, "kwalificatie verschijnt terwijl er genoeg REM is"


def test_older_results_render_without_a_caveat(tmp_path):
    """Resultaten van vóór psgscoring 0.15.1 dragen de velden niet. Het rapport
    hoort dan gewoon te renderen, zonder verzonnen kwalificatie."""
    r = _results(rem_min=22.5, reliable=False)
    s = r["pneumo"]["respiratory"]["summary"]
    del s["ahi_rem_reliable"], s["rem_min"]
    out = tmp_path / "oud.pdf"
    generate_pdf_report(r, str(out), lang="nl")
    txt = _pdf_text(out)
    assert "64.2" in txt
    assert "min REM (" not in txt
