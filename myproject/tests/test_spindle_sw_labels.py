"""De kanaalkolom van de spindel- en SW-tabel was leeg — en dat kwam niet uit
de rapportlaag.

`sp.summary(grp_chan=True, grp_stage=False)` geeft een DataFrame met het
KANAAL als index, niet als kolom. `to_dict(orient="records")` gooit de index
weg. Het label was dus al verdwenen voordat het rapport ernaar kon kijken; de
kolom toonde "—" op elke rij en de tabel was niet te interpreteren — zes rijen
zonder te kunnen zien waar ze bij horen.

Zelfde patroon in `run_slow_wave_detection`.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def raw_en_hypno():
    mne = pytest.importorskip("mne")
    pytest.importorskip("yasa")
    sf, minuten = 200.0, 20
    n = int(sf * 60 * minuten)
    t = np.arange(n) / sf
    rng = np.random.default_rng(1)
    kanalen = []
    for _ in range(2):
        x = rng.normal(0, 15e-6, n) + 20e-6 * np.sin(2 * np.pi * 1.0 * t)
        for st in range(30, minuten * 60 - 40, 20):
            a, b = int(st * sf), int((st + 1.0) * sf)
            x[a:b] += 40e-6 * np.sin(2 * np.pi * 13.0 * t[a:b])
        kanalen.append(x)
    info = mne.create_info(["C3-M2", "C4-M1"], sf, "eeg")
    raw = mne.io.RawArray(np.vstack(kanalen), info, verbose=False)
    return raw, ["N2"] * int(n / (sf * 30))


def test_the_spindle_summary_names_its_channel(raw_en_hypno):
    from yasa_analysis import run_spindle_detection
    raw, hypno = raw_en_hypno
    out = run_spindle_detection(raw, hypno, ["C3-M2", "C4-M1"])
    if not out.get("success") or not out.get("summary"):
        pytest.skip("geen spindels in deze fixture")
    for rij in out["summary"]:
        assert rij.get("Channel") in ("C3-M2", "C4-M1"), rij


def test_the_slow_wave_summary_names_its_channel():
    """Eigen fixture: trage golven vragen 0,75 Hz met ruime amplitude in N3.
    Op de spindelfixture vindt de detector er geen, en dan meet deze test
    niets."""
    mne = pytest.importorskip("mne")
    pytest.importorskip("yasa")
    from yasa_analysis import run_sw_detection

    sf, minuten = 200.0, 20
    n = int(sf * 60 * minuten)
    t = np.arange(n) / sf
    rng = np.random.default_rng(4)
    kanalen = [100e-6 * np.sin(2 * np.pi * 0.75 * t)
               + rng.normal(0, 5e-6, n) for _ in range(2)]
    info = mne.create_info(["C3-M2", "C4-M1"], sf, "eeg")
    raw = mne.io.RawArray(np.vstack(kanalen), info, verbose=False)
    hypno = ["N3"] * int(n / (sf * 30))

    out = run_sw_detection(raw, hypno, ["C3-M2", "C4-M1"])
    assert out.get("summary"), (
        f"geen trage golven — deze fixture meet niets ({out.get('error')})")
    for rij in out["summary"]:
        assert rij.get("Channel") in ("C3-M2", "C4-M1"), rij


# ══════════════════════════════════════════════════════════════
# De rapportlaag: label uit alle indexkolommen die er zijn
# ══════════════════════════════════════════════════════════════

def test_the_report_labels_a_channel_row():
    from generate_pdf_report import _detector_row_label
    assert _detector_row_label({"Channel": "C4-M1", "Count": 62}) == "C4-M1"


def test_the_report_labels_a_channel_and_stage_row():
    """Bij grp_stage=True horen kanaal én stadium in het label; anders staan
    er twee rijen 'C4-M1' onder elkaar met verschillende getallen."""
    from generate_pdf_report import _detector_row_label
    assert _detector_row_label(
        {"Channel": "C4-M1", "Stage": "N2", "Count": 62}) == "C4-M1 · N2"


def test_a_row_without_any_label_is_still_marked():
    from generate_pdf_report import _detector_row_label
    assert _detector_row_label({"Count": 62}) == "—"
