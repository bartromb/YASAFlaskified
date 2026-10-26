"""Het EOG moet de pneumo-raw bereiken, anders draait het U-Net nooit.

WAAROM DEZE TESTS BESTAAN

psgscoring 0.37.0 zet `unet_v1` als standaard-arousaldetector op de klinische
profielen. Het U-Net heeft EEG + EOG + kin-EMG nodig en valt zonder EOG terug
op de LGBM-keten met `summary["unet_fallback_reason"] = "geen EOG-kanaal (…)"`.
`_pneumo_load_plan` laadde het stagings-EEG, de kin-EMG en de
arousal-afleidingen, maar níét het geconfigureerde `eog_ch`; `_pneumo_channel_map`
gaf geen sleutel "eog" door. Gevolg: de nieuwe standaard kwam in productie niet
aan (klinische controle 26-10, psgscoring
docs/unet_klinische_controle_eigen_psg_20261026.md). Dezelfde fout als de
kin-EMG van 24-08 (test_emg_reaches_psgscoring.py), één kanaal verder.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tasks  # noqa: E402


class _FakeRaw:
    def __init__(self, names):
        self.ch_names = list(names)
        self.info = {"sfreq": 256.0}


PNEUMO = {"flow_pressure": "Pressure Flow", "thorax": "Thorax",
          "abdomen": "Abdomen", "spo2": "SpO2"}


def test_the_pneumo_raw_carries_the_configured_eog():
    plan = tasks._pneumo_load_plan(list(PNEUMO.values()), "C3:A2", "EMG1",
                                   eog_ch="EOG-L")
    assert "EOG-L" in plan, (
        "zonder EOG in de pneumo-raw valt het U-Net stil terug op de "
        f"LGBM-keten: {plan}")
    assert "EMG1" in plan and "C3:A2" in plan
    assert plan.count("EOG-L") == 1, "dubbels laten MNE struikelen"


def test_no_eog_configured_changes_nothing_in_the_plan():
    assert tasks._pneumo_load_plan(["Flow", "Thorax"], "C3:A2", "EMG1") == [
        "Flow", "Thorax", "C3:A2", "EMG1"]
    assert tasks._pneumo_load_plan(["Flow", "Thorax"], "C3:A2", "EMG1",
                                   eog_ch=None) == [
        "Flow", "Thorax", "C3:A2", "EMG1"]


def test_the_channel_map_carries_the_eog_key():
    raw = _FakeRaw(list(PNEUMO.values()) + ["C3:A2", "EMG1", "EOG-L"])
    m = tasks._pneumo_channel_map(PNEUMO, "EMG1", raw, eog_ch="EOG-L")
    assert m["eog"] == "EOG-L"
    assert m["emg"] == "EMG1"
    assert m["flow_pressure"] == "Pressure Flow", "de rest moet intact blijven"


def test_an_eog_that_did_not_make_it_into_the_raw_is_not_claimed():
    raw = _FakeRaw(list(PNEUMO.values()) + ["C3:A2", "EMG1"])
    m = tasks._pneumo_channel_map(PNEUMO, "EMG1", raw, eog_ch="EOG-L")
    assert "eog" not in m, (
        "een naam die niet in de raw zit laat psgscoring op patroon zoeken "
        "en de provenance een ander kanaal noemen dan de map")


def test_no_eog_configured_leaves_the_map_untouched():
    raw = _FakeRaw(list(PNEUMO.values()) + ["EMG1"])
    assert tasks._pneumo_channel_map(PNEUMO, "EMG1", raw) == {**PNEUMO, "emg": "EMG1"}


def test_the_clinical_path_hands_the_eog_to_the_pipeline(monkeypatch):
    """Het echte pad: `_pneumo_load_plan` en `_pneumo_channel_map` worden in
    `run_analysis` aangeroepen; hier wordt gecontroleerd dat beide aanroepen
    het `eog_ch` meekrijgen (anders helpt de parameter niets)."""
    import re
    src = open(tasks.__file__, encoding="utf-8").read()
    for naam, venster in (("_pneumo_load_plan", 400), ("_pneumo_channel_map", 300)):
        aanroepen = [m for m in re.finditer(naam + r"\(", src)
                     if not src[max(0, m.start() - 4):m.start()].endswith("def ")]
        assert aanroepen, f"geen aanroep van {naam} gevonden"
        # de aanroep mag over meerdere regels lopen: zoek het argument in het blok erna
        for m in aanroepen:
            blok = src[m.start():m.start() + venster]
            assert "eog_ch" in blok, f"aanroep zonder eog_ch: {blok[:120]!r}"
