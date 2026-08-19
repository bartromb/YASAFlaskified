"""tests/test_profile_comparison_wiring.py — draait de vergelijking werkelijk?

WAAROM DEZE TESTS BESTAAN

`run_profile_comparison` crashte op haar derde regel — `run_sleep_staging(raw)`
tegen een signatuur die `eeg_ch` eist — vanaf 6 april tot 19 augustus. In die
tijd kreeg ze 22 nieuwe tests en een release. Geen van die tests riep haar aan:
ze dekten `profile_matrix.py`, de pure module. Een groene suite boven een
kapotte ingang.

Deze tests roepen de functie zelf aan, met gemockte zware onderdelen. Ze zijn
niet bedoeld om scoring te toetsen — dat doet psgscoring — maar om te
garanderen dat het pad van EDF naar vergelijkings-JSON blijft lopen, inclusief
de eventvangst waar de overeenkomstanalyse op rust.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tasks  # noqa: E402


def _ev(onset, dur, typ="obstructive"):
    return {"onset_s": float(onset), "duration_s": float(dur), "type": typ}


# Twee profielen die 3 van 4 events delen: genoeg om een Jaccard te krijgen
# die noch 0 noch 1 is, zodat een implementatie die alles of niets paart faalt.
_EVENTS = {
    "aasm_v3_rec":      [_ev(10, 15), _ev(100, 20, "hypopnea"),
                         _ev(300, 12, "central"), _ev(500, 11)],
    "aasm_v3_pressure": [_ev(10, 15), _ev(100, 20, "hypopnea"),
                         _ev(300, 12, "central"), _ev(900, 11)],
}


@pytest.fixture
def stubbed(monkeypatch, tmp_path):
    """Alles wat traag of I/O-gebonden is vervangen; de bedrading blijft echt."""
    monkeypatch.setattr(tasks, "_load_edf", lambda *a, **k: object())
    monkeypatch.setattr(tasks, "_detect_pneumo_channels",
                        lambda *a, **k: ["Flow", "Thor", "SpO2"])

    def fake_pneumo(raw=None, hypno=None, channel_map=None,
                    scoring_profile=None, **kw):
        evs = _EVENTS[scoring_profile]
        return {"respiratory": {
            "events": evs,
            "summary": {
                "ahi_total": 12.5 if scoring_profile == "aasm_v3_rec" else 12.5,
                "oahi": 10.0, "central_index": 1.2,
                "n_apnea_total": 3, "n_hypopnea": 1, "n_ah_total": 4,
                "ahi_rem": 20.0, "ahi_nrem": 11.0,
                "rera_index": 0.0, "rdi": 12.5,
            },
        }}

    monkeypatch.setattr(tasks, "run_pneumo_analysis", fake_pneumo, raising=False)
    import pneumo_analysis
    monkeypatch.setattr(pneumo_analysis, "run_pneumo_analysis", fake_pneumo)
    return str(tmp_path)


def _run(results_dir, **kw):
    return tasks.run_profile_comparison(
        "/does/not/exist.edf", results_dir,
        profiles=list(_EVENTS), primary="aasm_v3_rec",
        hypno=["W"] * 100, **kw)


def test_the_function_runs_end_to_end(stubbed):
    """De test die april tot augustus had bespaard."""
    out = _run(stubbed)
    assert set(_EVENTS) <= set(out)
    assert out["_meta"]["primary_profile"] == "aasm_v3_rec"


def test_hypno_may_be_supplied_so_staging_is_not_repeated(stubbed, monkeypatch):
    """Het klinische pad heeft het hypnogram al; opnieuw stagen is 90 s weggooien.

    Faalt als de functie tóch stageert: de stub gooit dan.
    """
    def explode(*a, **k):
        raise AssertionError("run_sleep_staging aangeroepen terwijl hypno gegeven is")
    monkeypatch.setattr(tasks, "run_sleep_staging", explode, raising=False)
    import yasa_analysis
    monkeypatch.setattr(yasa_analysis, "run_sleep_staging", explode)
    out = _run(stubbed)
    assert out["_meta"]["hypnogram_shared"] is True


def test_staging_without_hypno_or_eeg_fails_loudly(stubbed):
    """Geen hypnogram én geen EEG-kanaal is een fout, geen stille aanname."""
    with pytest.raises(ValueError, match="eeg_ch"):
        tasks.run_profile_comparison("/x.edf", stubbed,
                                     profiles=list(_EVENTS),
                                     primary="aasm_v3_rec")


def test_events_are_captured_not_discarded(stubbed):
    out = _run(stubbed)
    assert out["_meta"]["n_events"] == {"aasm_v3_rec": 4, "aasm_v3_pressure": 4}
    with open(os.path.join(stubbed, "profile_events.json")) as f:
        stored = json.load(f)
    assert len(stored["aasm_v3_rec"]) == 4
    assert stored["aasm_v3_rec"][0]["onset_s"] == 10.0


def test_agreement_against_the_primary_is_computed(stubbed):
    pytest.importorskip(
        "psgscoring.agreement",
        reason="vereist psgscoring > 0.19.1; de pin in requirements.txt moet "
               "mee voordat deze functie in productie werkt")
    out = _run(stubbed)
    ag = out["aasm_v3_pressure"]["agreement_vs_primary"]
    assert ag["n_shared"] == 3
    assert ag["n_only_a"] == 1 and ag["n_only_b"] == 1
    assert ag["jaccard"] == 0.6
    assert ag["labels"] == {"a": "aasm_v3_rec", "b": "aasm_v3_pressure"}
    assert "excl_bare_uncertain" in ag
    assert out["_meta"]["agreement_error"] is None


def test_the_primary_row_carries_no_self_comparison(stubbed):
    """Een profiel met zichzelf vergelijken geeft altijd 1,0 en zegt niets."""
    out = _run(stubbed)
    assert "agreement_vs_primary" not in out["aasm_v3_rec"]


def test_unknown_profile_is_refused_rather_than_skipped(stubbed):
    """Een vergelijking met minder profielen dan de studie denkt is erger
    dan een fout."""
    with pytest.raises(ValueError, match="onbekend"):
        tasks.run_profile_comparison("/x.edf", stubbed,
                                     profiles=["aasm_v3_rec", "geen_profiel"],
                                     primary="aasm_v3_rec", hypno=["W"] * 100)


def test_summary_keys_that_are_read_actually_exist():
    """De sleutelfout van 19-08 in testvorm.

    `cahi`, `n_apneas` en `n_hypopneas` bestaan nergens in psgscoring. Ze
    kwamen maandenlang als None terug en renderden als "—", wat leest als
    "niet beschikbaar" terwijl het "verkeerde sleutel" betekent.

    De eerste versie van deze test keek alleen naar `_compute_summary` en
    verwierp daarmee `rdi` en `rera_index`, die op pipeline.py:1746-1747
    ná die functie aan dezelfde summary worden toegevoegd. De summary heeft
    dus meer dan één schrijver, en een test die er één kent geeft vals alarm.
    """
    import inspect
    import re

    import psgscoring.arousal as _ar
    import psgscoring.pipeline as _pl

    produced = set(re.findall(r'"([a-z_0-9]+)"\s*:',
                              inspect.getsource(_pl._compute_summary)))
    # Alles wat elders rechtstreeks in een summary wordt gezet.
    for mod in (_pl, _ar):
        src_mod = inspect.getsource(mod)
        produced |= set(re.findall(r'\["summary"\]\["([a-z_0-9]+)"\]', src_mod))
        produced |= set(re.findall(r'"summary":\s*\{[^}]*?"([a-z_0-9]+)"', src_mod))

    src = inspect.getsource(tasks.run_profile_comparison)
    read = set(re.findall(r'rsum\.get\("([a-z_0-9]+)"\)', src))
    assert read, "geen rsum.get(...) gevonden — is de vorm veranderd?"
    missing = sorted(read - produced)
    assert not missing, (
        f"gelezen uit summary maar door psgscoring niet geproduceerd: {missing}")


def test_the_key_guard_would_catch_the_bug_it_was_written_for():
    """Guard op de guard: de sleutels die 19-08 fout waren, bestaan echt niet.

    Zonder deze test kan de bovenstaande stilzwijgend te ruim worden en alles
    goedkeuren.
    """
    import inspect
    import re

    import psgscoring.arousal as _ar
    import psgscoring.pipeline as _pl

    produced = set(re.findall(r'"([a-z_0-9]+)"\s*:',
                              inspect.getsource(_pl._compute_summary)))
    for mod in (_pl, _ar):
        src_mod = inspect.getsource(mod)
        produced |= set(re.findall(r'\["summary"\]\["([a-z_0-9]+)"\]', src_mod))

    for dead in ("cahi", "n_apneas", "n_hypopneas"):
        assert dead not in produced, (
            f"{dead!r} bestaat nu wél — als psgscoring hem heeft toegevoegd, "
            f"mag tasks.py hem weer lezen en hoort deze test aangepast")


def test_a_missing_matcher_is_reported_not_swallowed(stubbed, monkeypatch):
    """Ontbreekt de matcher, dan hoort dat zichtbaar te zijn.

    Draait YF tegen een psgscoring zonder `agreement`, dan mag de vergelijking
    doorgaan — maar "geen overeenkomstdata" mag niet lezen als "geen
    verschillen". Dit is precies het pad dat afging toen deze test voor het
    eerst draaide tegen de gepinde 0.19.1.
    """
    import builtins
    real_import = builtins.__import__

    def no_agreement(name, *a, **k):
        if name == "psgscoring.agreement":
            raise ImportError("No module named 'psgscoring.agreement'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_agreement)
    out = _run(stubbed)
    assert out["_meta"]["agreement_error"] is not None
    assert "agreement" in out["_meta"]["agreement_error"]
    assert "agreement_vs_primary" not in out["aasm_v3_pressure"]
    # De vergelijking zelf blijft compleet.
    assert out["_meta"]["n_events"]["aasm_v3_rec"] == 4
