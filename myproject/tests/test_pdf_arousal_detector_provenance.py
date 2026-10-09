"""Welke detector de arousals leverde hoort in de Herkomst-tabel.

Sinds psgscoring 0.35.0 kan de arousalstap op het bevroren U-Net draaien
(`arousal_detector="unet_v1"`, opt-in) en valt hij zonder EOG/kin-EMG of
onnxruntime terug op de LGBM-keten mét reden. De bibliotheek levert
`summary["detector"]`, `summary["unet_threshold"]` en
`summary["unet_fallback_reason"]`; zonder deze rij leest niemand ze.
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


def _results(extra=None):
    s = {"ahi_total": 12.0, "n_ah_total": 10, "n_obstructive": 10,
         "n_central": 0, "n_mixed": 0, "n_hypopnea": 0,
         "obstructive_index": 12.0, "central_index": 0.0,
         "mixed_index": 0.0, "hypopnea_index": 0.0,
         "ahi_rem": 10.0, "ahi_nrem": 12.5, "rem_min": 90.0,
         "nrem_min": 300.0, "ahi_rem_reliable": True}
    asum = {"arousal_index": 20.0}
    asum.update(extra or {})
    ev = [{"type": "obstructive", "onset_s": 100.0 + 60 * i,
           "duration_s": 15.0, "stage": "N2", "epoch": 3 + 2 * i,
           "confidence": 0.8} for i in range(10)]
    return {"patient_info": {"lang": "nl"},
            "pneumo": {"respiratory": {"success": True, "events": ev,
                                       "summary": s},
                       "arousal": {"success": True, "summary": asum}}}


def test_unet_detector_staat_in_de_herkomst_met_werkpunt(tmp_path):
    out = tmp_path / "unet.pdf"
    generate_pdf_report(_results({"detector": "unet_v1", "unet_threshold": 0.35,
                                  "unet_onnx_sha256": "6fbea2857567f950"}), str(out), lang="nl")
    txt = _pdf_text(out)
    assert "unet_v1" in txt
    assert "0,35" in txt or "0.35" in txt


def test_terugval_toont_de_reden(tmp_path):
    out = tmp_path / "terugval.pdf"
    generate_pdf_report(_results({"detector": "lgbm",
                                  "unet_fallback_reason": "geen EOG-kanaal"}), str(out), lang="nl")
    txt = _pdf_text(out)
    assert "geen EOG-kanaal" in txt
    assert "lgbm" in txt.lower()


def test_zonder_detectorveld_geen_rij(tmp_path):
    """Oudere resultaten (psgscoring < 0.35.0) dragen het veld niet."""
    out = tmp_path / "oud.pdf"
    generate_pdf_report(_results(), str(out), lang="nl")
    txt = _pdf_text(out)
    assert "unet_v1" not in txt and "Arousal-detector" not in txt
