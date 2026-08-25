"""De kin-EMG moet de arousal-analyse bereiken — hij deed dat nooit.

WAAROM DEZE TESTS BESTAAN

De LightGBM-arousalclassifier van psgscoring splitst 486 keer op een
EMG-feature. Bereikt het kanaal hem niet, dan staat dat feature constant op
nul en degenereert de kansverdeling; op een vast werkpunt kost dat events.
De MESA-kalibratie die het werkpunt 0,80 koos laadde het EDF VOLLEDIG en had
de chin-EMG dus wél. De klinische keten hier had drie onafhankelijke gaten:

1. `pneumo_needed = pneumo_ch_list + [eeg_ch]` — de geconfigureerde `emg_ch`
   stond er niet bij, dus `raw_pneumo` bevatte het kanaal per constructie niet.
2. `run_pneumo_analysis(..., channel_map=pneumo_channels)` — de respiratoire
   map, zonder sleutel "emg".
3. Het foutpad (`raw_pneumo = raw_staging`) had de EMG juist wél, zodat de
   classifier alleen na een mislukte load EMG-features kreeg.

`channel_map_from_user` in psgscoring negeert stil elke naam die niet in
`raw.ch_names` zit. Punt 1 moet dus werken voordat punt 2 iets doet — vandaar
de test die beide samen controleert.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tasks  # noqa: E402


class _FakeRaw:
    def __init__(self, names):
        self.ch_names = list(names)
        self.info = {"sfreq": 256.0}

    def __contains__(self, item):
        return item in self.ch_names


EDF_CHANNELS = ["C3:A2", "C4:A1", "EMG1", "Pressure Flow", "Thorax",
                "Abdomen", "SpO2", "Pulse", "PLMl", "PLMr", "Pos."]
PNEUMO = {"flow_pressure": "Pressure Flow", "thorax": "Thorax",
          "abdomen": "Abdomen", "spo2": "SpO2", "leg_l": "PLMl",
          "leg_r": "PLMr"}


@pytest.fixture
def gevangen(monkeypatch):
    """Vang wat de pijplijn krijgt aangeleverd, zonder iets echt te draaien."""
    zicht = {}

    def fake_load(edf_path, needed, label="EDF"):
        zicht.setdefault("loads", []).append((label, list(needed)))
        return _FakeRaw([c for c in needed if c in EDF_CHANNELS])

    def fake_pneumo(raw=None, hypno=None, channel_map=None, **kw):
        zicht["channel_map"] = dict(channel_map or {})
        zicht["raw_ch_names"] = list(getattr(raw, "ch_names", []))
        return {"respiratory": {"events": [], "summary": {}}}

    monkeypatch.setattr(tasks, "_load_edf", fake_load)
    monkeypatch.setattr(tasks, "_detect_pneumo_channels",
                        lambda *a, **k: list(PNEUMO.values()))
    monkeypatch.setattr(tasks, "run_pneumo_analysis", fake_pneumo,
                        raising=False)
    import pneumo_analysis
    monkeypatch.setattr(pneumo_analysis, "run_pneumo_analysis", fake_pneumo)
    return zicht


# ══════════════════════════════════════════════════════════════
# T0f — het studievergelijkingspad
# ══════════════════════════════════════════════════════════════

def test_the_comparison_path_loads_the_eeg_and_emg_too(gevangen, tmp_path,
                                                       monkeypatch):
    """`run_profile_comparison` laadde alléén pneumo-kanalen. De arousal/RDI-arm
    van elk profielrapport draaide dus zonder EMG en zonder arousal-EEG — niet
    vergelijkbaar met de klinische run, terwijl dat het hele punt is."""
    monkeypatch.setattr(tasks, "run_pneumo_analysis",
                        lambda **kw: gevangen.__setitem__(
                            "channel_map", dict(kw.get("channel_map") or {}))
                        or {"respiratory": {"events": [], "summary": {}}},
                        raising=False)
    tasks.run_profile_comparison(
        "/x.edf", str(tmp_path), profiles=["aasm_v3_rec"],
        primary="aasm_v3_rec", hypno=["W"] * 100,
        eeg_ch="C3:A2", emg_ch="EMG1", pneumo_channels=PNEUMO)

    cmp_loads = [n for lbl, n in gevangen["loads"] if lbl.endswith("/cmp")]
    assert cmp_loads, "geen load in het vergelijkingspad"
    assert "C3:A2" in cmp_loads[-1], (
        "de vergelijkings-raw draagt geen arousal-EEG")
    assert "EMG1" in cmp_loads[-1], (
        "de vergelijkings-raw draagt geen kin-EMG")
    assert gevangen["channel_map"].get("emg") == "EMG1"


# ══════════════════════════════════════════════════════════════
# T0e — een ontbrekend kanaal is zichtbaar, niet alleen in de workerlog
# ══════════════════════════════════════════════════════════════

def test_a_missing_emg_becomes_an_analysis_warning():
    """Ontbrekend EEG gaf een ValueError, ontbrekend EMG/EOG alleen een
    logger.warning in de workerlog — niets in het rapport of de UI. De
    arousal-regressie was daardoor maandenlang onzichtbaar."""
    raw = _FakeRaw(["C3:A2", "C4:A1", "SpO2"])
    extra = []
    warnings = tasks._validate_channels(raw, "C3:A2", "EOG-L", "EMG1", extra)
    assert isinstance(warnings, list)
    codes = {w["code"] for w in warnings}
    assert "emg_channel_missing" in codes, codes
    assert "eog_channel_missing" in codes, codes
    emg = next(w for w in warnings if w["code"] == "emg_channel_missing")
    assert "EMG1" in emg["message"]
    assert emg["severity"] == "warning"


def test_channels_that_are_present_produce_no_warning():
    raw = _FakeRaw(["C3:A2", "EOG-L", "EMG1"])
    assert tasks._validate_channels(raw, "C3:A2", "EOG-L", "EMG1", []) == []


def test_a_missing_eeg_is_still_a_hard_error():
    raw = _FakeRaw(["EOG-L", "EMG1"])
    with pytest.raises(ValueError, match="EEG"):
        tasks._validate_channels(raw, "C3:A2", "EOG-L", "EMG1", [])


# ══════════════════════════════════════════════════════════════
# T0a / T0b — de klinische pneumo-raw en de channel_map
# ══════════════════════════════════════════════════════════════

def test_the_pneumo_raw_carries_the_configured_chin_emg():
    plan = tasks._pneumo_load_plan(list(PNEUMO.values()), "C3:A2", "EMG1")
    assert "EMG1" in plan, (
        "zonder het kanaal in de raw negeert channel_map_from_user de "
        "override stil — de map noemt dan een kanaal dat er niet is")
    assert "C3:A2" in plan
    assert plan.count("C3:A2") == 1, "dubbels laten MNE struikelen"


def test_the_load_plan_drops_nothing_and_keeps_order():
    plan = tasks._pneumo_load_plan(["Flow", "Thorax"], "C3:A2", None)
    assert plan == ["Flow", "Thorax", "C3:A2"]


def test_the_channel_map_carries_the_emg_key():
    raw = _FakeRaw(EDF_CHANNELS)
    m = tasks._pneumo_channel_map(PNEUMO, "EMG1", raw)
    assert m["emg"] == "EMG1"
    assert m["flow_pressure"] == "Pressure Flow", "de rest moet intact blijven"


def test_an_emg_that_did_not_make_it_into_the_raw_is_not_claimed():
    """Beweren dat "EMG1" gebruikt wordt terwijl het kanaal niet geladen is,
    is erger dan het weglaten: psgscoring valt dan terug op zijn eigen
    zoektocht en de provenance zou een ander kanaal noemen dan de map."""
    raw = _FakeRaw([c for c in EDF_CHANNELS if c != "EMG1"])
    assert "emg" not in tasks._pneumo_channel_map(PNEUMO, "EMG1", raw)


def test_no_emg_configured_leaves_the_map_untouched():
    raw = _FakeRaw(EDF_CHANNELS)
    assert tasks._pneumo_channel_map(PNEUMO, None, raw) == PNEUMO


# ══════════════════════════════════════════════════════════════
# T0g — kin-labels die nergens herkend werden
# ══════════════════════════════════════════════════════════════
#
# De nevenbevinding uit de analyse was dat `CH_TYPE_PATTERNS["emg"]` en
# `_identify_emg_channels` "LEG"/"TIBIAL" tot de EMG-patronen rekenen en dus
# een been-EMG als kin zouden kunnen classificeren. Nagetrokken klopt dat
# tweede deel niet: geen van beide paden kiest ooit EEN kin-kanaal. De lijst
# gaat naar een telling in de uploadlog en naar een metadataregel; de
# EMG-KEUZE komt uit channel_select.html, dat been-labels correct uitsluit,
# en de scoring kiest via psgscoring's _pick_emg (dat nu ook uitsluit).
# Een been-EMG als type "emg" tonen is bovendien juist: het signaalpaneel
# haalt er zijn µV-schaal uit.
#
# Wat er WEL misging: de kin-labels die het sjabloon kent -- Menton, Kinn,
# Submental -- stonden in geen van beide lijsten. Zo'n kanaal viel door naar
# type "other" met schaal 1,0 in plaats van 150 µV.

import edf_api  # noqa: E402


@pytest.mark.parametrize("naam", ["Chin1-Chin2", "Menton", "Kinn",
                                  "Submental", "EMG1"])
def test_the_chin_labels_from_the_template_are_recognised_everywhere(naam):
    assert edf_api._detect_ch_type(naam) == "emg", (
        f"{naam} valt door naar 'other' en krijgt schaal 1,0 in plaats van "
        f"150 µV in het signaalpaneel")


def test_a_leg_channel_is_still_typed_as_emg_for_display():
    """Bewust: het signaalpaneel haalt zijn amplitudeschaal uit het type."""
    assert edf_api._detect_ch_type("EMG Tib L") == "emg"
    assert edf_api._detect_ch_type("PLMl") != "eeg"


# ══════════════════════════════════════════════════════════════
# De arousal-afleidingen moeten de pneumo-raw halen
# ══════════════════════════════════════════════════════════════
#
# De pneumo-raw wordt gebouwd uit `detect_channels`, dat ÉÉN kanaal per rol
# teruggeeft. Op een klinische opname stonden daar C3 en C4 in -- twee kanalen
# uit DEZELFDE regio -- terwijl het EDF ook O1/O2 en F3/F4 droeg. De
# arousalstap kiest zijn afleidingen uit wat er ÍS, dus die zag nooit een
# frontale of occipitale afleiding.
#
# Gemeten op PSG-IPA (n=5, 12 scoorders): union van drie regio's geeft
# arousal-F1 0,514 tegen 0,439-0,442 voor de beste enkele. Van één naar twee
# regio's is +0,06. En geen regio wint overal -- op SN4 is occipitaal de
# sterkste waar hij gemiddeld de zwakste is. AASM V.A Note 1 schrijft alle
# drie voor.

KLINISCH_EDF = ["Snore", "Pressure Flow", "Flow Th.", "RIP Thora", "RIP Abdom",
                "Sum RIP", "SpO2", "PLMl", "PLMr", "EMG1", "Pos.", "Pleth",
                "C4:A1", "Pulse", "ECG II", "C3", "C4", "O1", "O2", "A1", "A2",
                "F3", "F4", "EOG1", "EOG2"]


def test_the_load_plan_carries_all_three_regions():
    plan = tasks._pneumo_load_plan(
        ["Pressure Flow", "RIP Thora", "SpO2"], "C4", "EMG1",
        eeg_all=KLINISCH_EDF)
    boven = " ".join(plan).upper()
    assert "O1" in boven or "O2" in boven, f"geen occipitale afleiding: {plan}"
    assert "F3" in boven or "F4" in boven, f"geen frontale afleiding: {plan}"
    assert "EMG1" in plan and "C4" in plan


def test_the_saturation_curve_does_not_sneak_in_as_an_eeg():
    plan = tasks._pneumo_load_plan(["Pressure Flow"], "C4", None,
                                   eeg_all=KLINISCH_EDF)
    assert "Pleth" not in plan
    assert plan.count("SpO2") == 0 or "SpO2" in ["Pressure Flow"]


def test_without_the_channel_list_the_plan_is_unchanged():
    """Aanroepers die de EDF-namen niet meegeven mogen niet stilzwijgend
    kanalen kwijtraken."""
    assert tasks._pneumo_load_plan(["Flow", "Thorax"], "C3:A2", None) == [
        "Flow", "Thorax", "C3:A2"]


def test_the_requested_channels_are_the_ones_psgscoring_will_use():
    """De plumbing en de detector moeten dezelfde set kiezen; anders vraagt de
    app kanalen op die de arousalstap niet gebruikt, of andersom."""
    from psgscoring.pipeline import arousal_derivation_channels
    plan = tasks._pneumo_load_plan(["Pressure Flow"], "C4", "EMG1",
                                   eeg_all=KLINISCH_EDF)
    wil = arousal_derivation_channels(KLINISCH_EDF, {"eeg": "C4"})
    for kanaal in wil:
        assert kanaal in plan, f"{kanaal} wordt niet ingeladen; plan={plan}"
