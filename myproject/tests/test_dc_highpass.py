"""Gelijkspanning-gekoppelde opnames: automatisch hoogdoorlaten, met melding.

WAT HET PROBLEEM WAS
--------------------
Een BioSemi-achtige versterker neemt gelijkspanning mee op. Op de opname die
dit aan het licht bracht droeg F3 een staande offset van 145 mV met het EEG er
in microvolts bovenop:

    F3  ruw p95 144.571 µV  ->  na 0,3 Hz hoogdoorlaat  25,2 µV
    C4  ruw p95  20.403 µV  ->                         203,3 µV

Eén feit verklaarde drie klachten: vlakke lijnen in de viewer (de schaal volgde
de offset; gain hielp niet), een "discontinuous" EDF na conversie (16-bit kan
145 mV en microvoltdetail niet tegelijk dragen), en 100 % van de samples boven
de 500 µV-artefactregel -- dus geen bruikbare uitkomst.

Herrefereren op A1/A2 werkt NIET: F3-A2 bleef 136.088 µV, want elk kanaal
draagt zijn eigen onafhankelijke offset.

WAAROM DIT AUTOMATISCH MAG
--------------------------
De drempel is dezelfde 500 µV als de artefactregel. Een kanaal met een offset
daarboven wordt nu al volledig weggegooid, dus er is geen bestaande bruikbare
uitkomst om te breken. `test_een_gewone_opname_wordt_niet_aangeraakt` bewaakt
precies dat.

DE GEVAARLIJKSTE FOUT die deze code kan maken is niet "te weinig filteren" maar
"het verkeerde kanaal filteren": een ademhaling van 12/min is 0,2 Hz, en een
hoogdoorlaat op 0,3 Hz zou daar dwars doorheen gaan. `EMG/Piezo` draagt "EMG"
in de naam maar meet ademhaling. Vandaar dat de uitsluitlijst vóórgaat.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_io import (  # noqa: E402
    DC_OFFSET_THRESHOLD_UV,
    _is_ac_channel,
    apply_dc_highpass,
    dc_coupled_channels,
    read_raw_signal,
    strip_window_offset,
)

FS = 100
DUUR_S = 120
OFFSET_UV = 145_000.0


def _schrijf(path, offsets_uv):
    """Een opname waarin elk kanaal zijn eigen offset draagt."""
    import pyedflib

    n = FS * DUUR_S
    t = np.arange(n) / FS
    w = pyedflib.EdfWriter(str(path), len(offsets_uv),
                           file_type=pyedflib.FILETYPE_EDFPLUS)
    w.setSignalHeaders([
        {"label": lab, "dimension": "uV", "sample_frequency": FS,
         "physical_max": 500_000.0, "physical_min": -500_000.0,
         "digital_max": 32767, "digital_min": -32768,
         "transducer": "", "prefilter": ""}
        for lab in offsets_uv
    ])
    w.writeSamples([40.0 * np.sin(2 * np.pi * 10 * t) + off
                    for off in offsets_uv.values()])
    w.close()
    return str(path)


@pytest.fixture
def dc_opname(tmp_path):
    """F3 en C3 met offset, O1 schoon, SAO2 hoog maar legitiem."""
    return _schrijf(tmp_path / "dc.edf",
                    {"F3": -OFFSET_UV, "C3": 20_000.0, "O1": 0.0,
                     "SAO2": 96_000.0})


@pytest.fixture
def gewone_opname(tmp_path):
    return _schrijf(tmp_path / "gewoon.edf",
                    {"F3": 0.0, "C3": 5.0, "O1": -3.0, "SAO2": 96_000.0})


def test_rolherkenning_kiest_de_juiste_kanalen():
    for naam in ("F3", "C4", "A1", "LEOG", "Chin", "ECG", "Lt Leg",
                 "EEG C3-A2", "Tib Left"):
        assert _is_ac_channel(naam), naam
    for naam in ("SAO2_4", "Pulse_4", "Pos", "Flow", "Thermal", "Chest",
                 "Abd", "AC Snore", "DC-Snore", "Nasal Pressure"):
        assert not _is_ac_channel(naam), naam


def test_de_uitsluitlijst_gaat_voor_op_de_naam():
    """`EMG/Piezo` draagt "EMG" maar meet ademhaling op ~0,2 Hz.

    Filteren op 0,3 Hz zou dat signaal wegnemen. Stille schade is hier erger
    dan een gemist kanaal, dus bij twijfel niet filteren.
    """
    assert not _is_ac_channel("EMG/Piezo")
    assert not _is_ac_channel("Resp Belt")
    assert not _is_ac_channel("EMG Effort")


def test_offsets_worden_gevonden_en_de_schone_kanalen_niet(dc_opname):
    raw = read_raw_signal(dc_opname, preload=False, verbose=False)
    gevonden = dc_coupled_channels(raw)
    assert set(gevonden) == {"F3", "C3"}, gevonden
    assert gevonden["F3"] == pytest.approx(-OFFSET_UV, rel=0.01)


def test_spo2_wordt_nooit_gefilterd_hoe_hoog_ook(dc_opname):
    """Bij SpO2 IS het gelijkspanningsniveau de meting."""
    raw = read_raw_signal(dc_opname, preload=False, verbose=False)
    assert "SAO2" not in dc_coupled_channels(raw)


def test_de_hoogdoorlaat_brengt_het_eeg_terug_in_bereik(dc_opname):
    raw = read_raw_signal(dc_opname, preload=True, verbose=False)
    voor = float(np.percentile(np.abs(raw.get_data(picks=["F3"])[0]) * 1e6, 95))
    assert voor > 100_000, voor

    verslag = apply_dc_highpass(raw)
    assert verslag["applied"] is True
    assert set(verslag["channels"]) == {"F3", "C3"}
    assert verslag["cutoff_hz"] == pytest.approx(0.3)

    na = float(np.percentile(np.abs(raw.get_data(picks=["F3"])[0]) * 1e6, 95))
    assert na < 500, na


def test_na_de_hoogdoorlaat_haalt_niets_meer_de_artefactdrempel(dc_opname):
    """Vóór: 100 % van de samples boven 500 µV. Dat is geen uitkomst."""
    raw = read_raw_signal(dc_opname, preload=True, verbose=False)
    ruw = raw.get_data(picks=["F3"])[0] * 1e6
    assert np.mean(np.abs(ruw) > 500) == pytest.approx(1.0)

    apply_dc_highpass(raw)
    na = raw.get_data(picks=["F3"])[0] * 1e6
    assert np.mean(np.abs(na) > 500) == 0.0


def test_een_gewone_opname_wordt_niet_aangeraakt(gewone_opname):
    """De hele rechtvaardiging om dit automatisch te doen, staat of valt hier."""
    raw = read_raw_signal(gewone_opname, preload=True, verbose=False)
    voor = raw.get_data().copy()
    verslag = apply_dc_highpass(raw)
    assert verslag["applied"] is False
    assert verslag["channels"] == {}
    assert np.array_equal(voor, raw.get_data()), "signalen zijn toch bewerkt"


def test_de_viewer_haalt_alleen_grote_offsets_weg():
    """Onder de drempel toont de viewer wat er in het bestand staat."""
    data = np.zeros((3, 100))
    data[0] = 1e-6 * (np.random.default_rng(0).normal(size=100) * 30 - 145_000)
    data[1] = 1e-6 * (np.random.default_rng(1).normal(size=100) * 30)
    data[2] = 1e-6 * (np.random.default_rng(2).normal(size=100) + 96_000)
    voor2 = data[2].copy()
    aangepast = strip_window_offset(data, ["F3", "C3", "SAO2"])
    assert aangepast == ["F3"], aangepast
    assert abs(float(np.median(data[0])) * 1e6) < DC_OFFSET_THRESHOLD_UV
    assert np.array_equal(data[2], voor2), "SpO2 mag de viewer niet verschuiven"


def test_het_rapport_toont_de_hoogdoorlaat():
    from generate_pdf_report import _WARNING_KEYS, provenance_rows

    assert _WARNING_KEYS["dc_highpass_applied"] == "pdf_warn_dc_highpass"

    res = {"meta": {"eeg_channel": "C3"},
           "pneumo": {"meta": {"channels_used": {"eeg": "C3"},
                               "flow_channels": {}},
                      "arousal": {"arousals": {"summary": {}}}},
           "dc_highpass": {"applied": True, "cutoff_hz": 0.3,
                           "n_channels": 13, "max_offset_uv": 164627.0,
                           "channels": {"F3": -144576.0}}}
    rijen = provenance_rows(res, "nl")
    regel = [r for r in rijen if "Gelijkspanning" in r[0]]
    assert regel, [r[0] for r in rijen]
    assert "0.30 Hz" in regel[0][1] and "13" in regel[0][1]


def test_het_rapport_zwijgt_als_er_niets_gefilterd_is():
    from generate_pdf_report import provenance_rows

    res = {"meta": {"eeg_channel": "C3"},
           "pneumo": {"meta": {"channels_used": {"eeg": "C3"},
                               "flow_channels": {}},
                      "arousal": {"arousals": {"summary": {}}}},
           "dc_highpass": {"applied": False, "channels": {}}}
    assert not [r for r in provenance_rows(res, "nl") if "Gelijkspanning" in r[0]]


def test_de_waarschuwing_bestaat_in_vier_talen():
    from i18n import TRANSLATIONS

    entry = TRANSLATIONS["pdf_warn_dc_highpass"]
    for taal in ("nl", "fr", "en", "de"):
        assert entry.get(taal), taal
    assert len(set(entry[t] for t in ("nl", "fr", "en", "de"))) == 4
