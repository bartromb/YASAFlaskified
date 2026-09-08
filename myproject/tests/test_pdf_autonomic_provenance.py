"""De rerank-status hoort in de Herkomst-tabel van het rapport.

Sinds psgscoring 0.34.0 staat de autonome re-ranker AAN op aasm_v3_rec:
de arousalselectie hangt dan mede af van Pleth/hartslag. "De kanaalkeuze
bepaalt het resultaat" is precies waar de Herkomst-tabel voor bestaat —
een lezer moet kunnen zien of de herordening draaide, en zo nee waarom.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_pdf_report import generate_pdf_report  # noqa: E402


def _pdf_text(path):
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("pdftotext niet beschikbaar")
    return " ".join(out.stdout.decode("utf-8", "replace").split())


def _results(prov=None):
    s = {"ahi_total": 12.0, "n_ah_total": 10, "n_obstructive": 10,
         "n_central": 0, "n_mixed": 0, "n_hypopnea": 0,
         "obstructive_index": 12.0, "central_index": 0.0,
         "mixed_index": 0.0, "hypopnea_index": 0.0,
         "ahi_rem": 10.0, "ahi_nrem": 12.5, "rem_min": 90.0,
         "nrem_min": 300.0, "ahi_rem_reliable": True}
    asum = {"arousal_index": 20.0}
    if prov is not None:
        asum["autonomic_rerank"] = prov
    ev = [{"type": "obstructive", "onset_s": 100.0 + 60 * i,
           "duration_s": 15.0, "stage": "N2", "epoch": 3 + 2 * i,
           "confidence": 0.8} for i in range(10)]
    return {"patient_info": {"lang": "nl"},
            "pneumo": {"respiratory": {"success": True, "events": ev,
                                       "summary": s},
                       "arousal": {"success": True, "summary": asum}}}


def test_actieve_rerank_staat_in_de_herkomst(tmp_path):
    out = tmp_path / "aan.pdf"
    generate_pdf_report(_results(
        {"active": True, "model": "autonomic_rerank_v1", "k": 226,
         "n_candidates": 1425, "n_selected": 212, "threshold": 0.7,
         "n_pwa_drops": 174}), str(out), lang="nl")
    txt = _pdf_text(out)
    assert "autonom" in txt.lower()
    assert "autonomic_rerank_v1" in txt


def test_geweigerde_rerank_toont_de_reden(tmp_path):
    out = tmp_path / "reden.pdf"
    generate_pdf_report(_results(
        {"active": False, "model": "autonomic_rerank_v1",
         "reason": "pleth ontbreekt"}), str(out), lang="nl")
    txt = _pdf_text(out)
    assert "pleth ontbreekt" in txt


def test_zonder_veld_geen_rij(tmp_path):
    """Oudere resultaten (pre-0.34.0) dragen het veld niet; het rapport
    mag dan niets verzinnen."""
    out = tmp_path / "zonder.pdf"
    generate_pdf_report(_results(None), str(out), lang="nl")
    assert "autonomic_rerank_v1" not in _pdf_text(out)
