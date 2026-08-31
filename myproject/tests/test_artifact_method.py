"""De artefactmethode is een keuze geworden, en de default mag niet schuiven.

De eigen regel vlagt een epoch bij een piek boven 500 uV. Dat is
amplitudedetectie, geen artefactdetectie: een arousal gaat samen met
spieractiviteit, dus de regel selecteert juist de epochs waar arousals zitten.
Gemeten op PSG-IPA kost dat arousal-F1 0,505 -> 0,484, slechter op 5 van 5,
terwijl de precisie niet beweegt.

`yasa.art_detect` staat er als alternatief naast, achter een schakelaar met de
huidige regel als default. Deze tests bewaken twee dingen: dat de default niet
verschuift, en dat de aanroep het hypnogram meegeeft -- zonder dat normaliseert
de yasa-methode niet per stadium en vervalt haar hele voordeel.
"""
from pathlib import Path

import numpy as np
import pytest

mne = pytest.importorskip("mne")


def _raw(n_ep=60, sf=100.0, spikes=(5, 22, 41)):
    n = int(sf * 30 * n_ep)
    rng = np.random.default_rng(1)
    d = rng.normal(0, 20e-6, (2, n))
    for ep in spikes:
        d[:, int(sf * 30 * ep):int(sf * 30 * (ep + 1))] *= 60
    return mne.io.RawArray(
        d, mne.create_info(["EEG1", "EEG2"], sf, ["eeg", "eeg"]), verbose=False)


def test_the_default_is_still_the_amplitude_rule():
    from yasa_analysis import ARTIFACT_METHOD_DEFAULT
    assert ARTIFACT_METHOD_DEFAULT == "amplitude", (
        "de default artefactmethode is verschoven; dat verandert TST, "
        "n_artifact_epochs en de arousaldetectie in een klap")


def test_both_methods_flag_a_gross_artefact():
    from yasa_analysis import run_artifact_detection

    raw = _raw()
    amp = run_artifact_detection(raw, ["EEG1", "EEG2"])
    ya = run_artifact_detection(raw, ["EEG1", "EEG2"], method="yasa",
                                hypno=["N2"] * 60)
    assert amp["success"] and ya["success"], (amp.get("error"), ya.get("error"))
    for r in (amp, ya):
        got = {e["epoch"] for e in r["artifact_epochs"]}
        assert {5, 22, 41} <= got, f"grof artefact gemist: {sorted(got)}"


def test_an_unknown_method_falls_back_to_the_default_without_crashing():
    from yasa_analysis import run_artifact_detection

    r = run_artifact_detection(_raw(), ["EEG1", "EEG2"], method="onzin")
    assert r["success"]
    assert {e["epoch"] for e in r["artifact_epochs"]} == {5, 22, 41}


def test_the_env_switches_the_method(monkeypatch):
    from yasa_analysis import run_artifact_detection

    monkeypatch.setenv("YASAFLASKIFIED_ARTIFACT_METHOD", "yasa")
    r = run_artifact_detection(_raw(), ["EEG1", "EEG2"], hypno=["N2"] * 60)
    assert r["success"], r.get("error")
    assert r["summary"].get("method") == "yasa", (
        "env schakelde de methode niet om; een meting zou dan stil de oude "
        "regel meten")


def test_the_call_site_passes_the_hypnogram():
    """Zonder hypnogram normaliseert de yasa-methode niet per stadium.

    Dit grept de aanroep, want een unittest op de functie zelf blijft groen
    terwijl de pipeline het hypnogram weglaat -- precies de fout die elders al
    een meting ongeldig maakte.
    """
    src = (Path(__file__).resolve().parent.parent
           / "yasa_analysis.py").read_text(encoding="utf-8")
    blok = src.split('output["artifacts"]')[1][:200]
    assert "hypno=hypno" in blok, (
        f"de aanroep geeft het hypnogram niet mee: {blok.strip()[:120]!r}")


def test_the_yasa_path_reports_whether_it_had_a_hypnogram():
    from yasa_analysis import run_artifact_detection

    met = run_artifact_detection(_raw(), ["EEG1", "EEG2"], method="yasa",
                                 hypno=["N2"] * 60)
    zonder = run_artifact_detection(_raw(), ["EEG1", "EEG2"], method="yasa")
    assert met["summary"]["hypno_used"] is True
    assert zonder["summary"]["hypno_used"] is False, (
        "zonder hypnogram draait de detectie over de nacht als geheel; dat "
        "mag, maar het hoort afleesbaar te zijn")
