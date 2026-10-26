"""Analysevenster voor de polygrafieroute op het leveringsoppervlak (waakpoort stap 1).

psgscoring levert vanaf 0.37.0 `polygraphy_hypnogram_from_raw`: "N2" binnen het venster op
signaalgeldigheid, "W" daarbuiten, met provenance. De app moet (1) het venster bouwen in plaats van
"N2" × epochs, (2) het handmatige venster van de technoloog (minuten na start) doorgeven, (3) op de
oude pin (0.36.2) of met de vlag uit terugvallen op de oude route mét reden, en (4) het venster
tonen in PDF en resultatenpagina. Het provenance-label voor de arousaldetector moet ook `unet_v2`
kunnen noemen.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_pdf_review_fixes_20260907 import _render, _results  # noqa: E402


def test_parser_minuten_naar_seconden():
    from polygraphy_window import analysis_window_s
    assert analysis_window_s("10", "480") == (600.0, 28800.0)
    assert analysis_window_s("0", "7,5") == (0.0, 450.0)
    assert analysis_window_s(None, None) is None
    assert analysis_window_s("abc", "100") is None
    assert analysis_window_s("100", "50") is None          # einde vóór begin: geen venster
    assert analysis_window_s("", "") is None
    assert analysis_window_s("30", "") is None              # half ingevuld: geen venster


def _raw(minutes=60, head_dead_min=10, fs=32.0):
    import mne
    n = int(minutes * 60 * fs)
    t = np.arange(n) / fs
    flow = np.sin(2 * np.pi * 0.25 * t) + 0.02 * np.random.default_rng(1).normal(size=n)
    spo2 = np.full(n, 95.0)
    k = int(head_dead_min * 60 * fs)
    flow[:k] = 0.0; spo2[:k] = 0.0
    info = mne.create_info(["Nasal Pressure", "SpO2", "Thorax"], fs, ch_types=["misc"] * 3)
    return mne.io.RawArray(np.vstack([flow, spo2, np.sin(2 * np.pi * 0.25 * t)]), info, verbose=False)


def test_bouwt_het_venster_en_zet_de_kop_op_W(monkeypatch):
    pytest.importorskip("psgscoring.polygraphy")
    monkeypatch.delenv("YASAFLASKIFIED_POLYGRAPHY_WINDOW", raising=False)
    from polygraphy_window import build_polygraphy_hypnogram
    hyp, prov = build_polygraphy_hypnogram(_raw(), {"flow_pressure": "Nasal Pressure", "spo2": "SpO2"}, n_epochs=120)
    assert len(hyp) == 120 and hyp[:20] == ["W"] * 20 and hyp[30] == "N2"
    assert prov["method"] == "signal_validity_window" and prov["excluded_min"]["before_window"] == 10.0


def test_handmatig_venster_gaat_mee(monkeypatch):
    pytest.importorskip("psgscoring.polygraphy")
    monkeypatch.delenv("YASAFLASKIFIED_POLYGRAPHY_WINDOW", raising=False)
    from polygraphy_window import build_polygraphy_hypnogram
    hyp, prov = build_polygraphy_hypnogram(_raw(), {"flow_pressure": "Nasal Pressure", "spo2": "SpO2"},
                                           n_epochs=120, manual_window_s=(20 * 60, 50 * 60))
    assert hyp[:40] == ["W"] * 40 and hyp[100:] == ["W"] * 20 and hyp[50] == "N2"
    assert prov["manual_window_s"] == [1200.0, 3000.0]


def test_vlag_uit_geeft_de_oude_route_met_reden(monkeypatch):
    monkeypatch.setenv("YASAFLASKIFIED_POLYGRAPHY_WINDOW", "off")
    from polygraphy_window import build_polygraphy_hypnogram
    hyp, prov = build_polygraphy_hypnogram(_raw(), {}, n_epochs=120)
    assert hyp == ["N2"] * 120 and prov["method"] == "off"


def test_oude_pin_zonder_de_functie_valt_terug(monkeypatch):
    import polygraphy_window as pw
    monkeypatch.delenv("YASAFLASKIFIED_POLYGRAPHY_WINDOW", raising=False)
    monkeypatch.setattr(pw, "_builder", lambda: None)
    hyp, prov = pw.build_polygraphy_hypnogram(_raw(), {}, n_epochs=120)
    assert hyp == ["N2"] * 120 and prov["method"] == "unavailable" and "psgscoring" in prov["reason"]


def _polygrafie(res, venster=True):
    res["is_polygraphy"] = True
    res["meta"]["duration_min"] = 600.0
    res["pneumo"]["respiratory"]["summary"]["index_denominator_h"] = 7.4
    if venster:
        res["analysis_window"] = {
            "method": "signal_validity_window", "reason": None, "n_epochs": 1200, "epoch_s": 30.0,
            "window_start_s": 720.0, "window_end_s": 28080.0, "analysed_min": 441.0,
            "excluded_min": {"before_window": 12.0, "after_window": 132.0, "inside_window": 15.0,
                             "manual": 0.0, "total": 159.0},
            "excluded_runs_s": [[9000.0, 9900.0]], "manual_window_s": None,
            "channels": {"flow": ["flow_pressure"], "spo2": True, "effort": [], "ignored": []},
            "thresholds": {"dead_frac": 0.02, "min_valid_run": 4, "min_dead_run": 6}}
    return res


def test_pdf_toont_het_analysevenster_bij_polygrafie(tmp_path):
    txt = _render(_polygrafie(_results()), tmp_path)
    assert "Analysevenster" in txt
    assert "441" in txt and "132" in txt
    assert "sensor los" in txt


def test_pdf_zonder_venster_toont_niets_en_faalt_niet(tmp_path):
    txt = _render(_polygrafie(_results(), venster=False), tmp_path)
    assert "Analysevenster" not in txt


def test_pdf_label_noemt_unet_v2(tmp_path):
    res = _results()
    res["pneumo"]["arousal"] = {"success": True, "summary": {"detector": "unet_v2", "unet_threshold": 0.30}}
    txt = _render(res, tmp_path)
    assert "unet_v2" in txt and "0,30" in txt
