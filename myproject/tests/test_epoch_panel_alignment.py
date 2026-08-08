"""Het signaalpaneel moet het JUISTE venster tonen, leesbaar geschaald.

Aanleiding. Sinds v0.8.36 stond de sectie signaalvoorbeelden uitgeschakeld met
één regel toelichting: *"epoch alignment nog niet correct"*. Bij het nameten
bleek die uitlijning wél te kloppen — op een synthetische mixed-rate EDF met
een dropout op een bekende plek, én op twee menselijk gescoorde events uit
PSG-IPA (SN3, obstructief t=316,6 s en centraal t=241,8 s). In alle gevallen
viel de rode band exact op het fysiologische event, met het effort-gedrag dat
bij het type hoort: thorax en abdomen lopen door bij obstructief, staan stil
bij centraal.

Wat wél stuk was, is de y-schaal. De regel was median ± 4·MAD over het hele
venster. Een respiratoir event is per definitie een stille periode, dus hoe
overtuigender het event, hoe kleiner de MAD en hoe strakker de schaal. Op de
gemengde apneu bij t=436 s bleef van het flowkanaal een streep over en stond
Abdomen op 20–40 terwijl de werkelijke excursies een veelvoud daarvan zijn.
Precies omgekeerd aan wat de lezer nodig heeft: je kunt een reductie niet
beoordelen als de ademhaling waartegen je vergelijkt buiten beeld valt.

Deze toets legt beide eigenschappen vast op een synthetische EDF, zodat de
waarheid bekend is en er geen detector in de lus zit.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

edfio = pytest.importorskip("edfio")

import matplotlib                                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402

import generate_pdf_report as g                          # noqa: E402

DUR_S, DROP_START, DROP_END = 600, 300.0, 320.0
AMP = 100.0


@pytest.fixture(scope="module")
def edf(tmp_path_factory):
    """Mixed-rate EDF: EEG 256 Hz, ademkanalen 32 Hz, SpO2 1 Hz.

    Het EEG staat er expres in: het bepaalt `raw.info['sfreq']` bij een
    volledige lezing, terwijl de analyse het uitsluit. Als dat verschil de
    tijdas zou verschuiven, valt deze toets om.
    """
    def sig(name, sf, fn):
        t = np.arange(DUR_S * sf) / sf
        return edfio.EdfSignal(fn(t).astype(np.float64),
                               sampling_frequency=sf, label=name)

    def adem(t, amp=AMP):
        """Piekerige ademhaling, niet sinusvormig.

        Dit is geen kosmetiek. Met een zuivere sinus is de MAD ongeveer de
        halve amplitude en klemt de oude regel niet — de fout reproduceert
        dan niet en de toets zou groen staan zonder iets te meten. Echte
        nasale druk is piekerig: smalle uitslagen boven een lange, rustige
        basis, dus MAD << piek. Zie test_the_old_rule_would_have_clipped_this.
        """
        s = np.sin(2 * np.pi * 0.25 * t)
        x = amp * np.sign(s) * np.abs(s) ** 5
        x[(t >= DROP_START) & (t < DROP_END)] = 0.0
        return x

    p = tmp_path_factory.mktemp("edf") / "align.edf"
    edfio.Edf([
        sig("EEG C4-M1", 256, lambda t: np.sin(2 * np.pi * 10 * t)),
        sig("Flow",      32,  adem),
        sig("Thorax",    32,  lambda t: adem(t, AMP * 0.8)),
        sig("Abdomen",   32,  lambda t: adem(t, AMP * 0.6)),
        sig("SpO2",      1,   lambda t: np.where(
            (t >= DROP_END) & (t < DROP_END + 15), 88.0, 96.0)),
    ]).write(p)
    return str(p)


CH_MAP = {"flow": "Flow", "thorax": "Thorax",
          "abdomen": "Abdomen", "spo2": "SpO2"}


def _panel(edf_path, onset=DROP_START, dur=DROP_END - DROP_START):
    """Render en geef de assen terug, per kanaaltype."""
    grabbed = {}
    real_subplots = plt.subplots

    def spy(*a, **kw):
        fig, axes = real_subplots(*a, **kw)
        grabbed["fig"], grabbed["axes"] = fig, np.atleast_1d(axes)
        return fig, axes

    real_close = plt.close
    plt.subplots, plt.close = spy, lambda *a, **k: None
    try:
        g._plot_epoch_example(edf_path, CH_MAP,
                              {"type": "obstructive", "onset_s": onset,
                               "duration_s": dur, "confidence": 0.9},
                              hypno=["N2"] * 20)
    finally:
        plt.subplots, plt.close = real_subplots, real_close

    axes = grabbed["axes"]
    order = [ct for ct, _, _ in g._EPOCH_CH_ORDER if ct in CH_MAP]
    out = {ct: axes[i] for i, ct in enumerate(order[:len(axes)])}
    return out, grabbed["fig"]


def _line(ax):
    ln = ax.get_lines()[0]
    return np.asarray(ln.get_xdata()), np.asarray(ln.get_ydata())


# ──────────────────────────────────────────────────────────────
#  Uitlijning
# ──────────────────────────────────────────────────────────────

def test_the_window_is_centred_on_the_event(edf):
    axes, fig = _panel(edf)
    x, _ = _line(axes["flow"])
    assert x[0] == pytest.approx(DROP_START - 15, abs=0.5), "venster begint verkeerd"
    assert x[-1] == pytest.approx(DROP_END + 30, abs=0.5), "venster eindigt verkeerd"
    plt.close(fig)


def test_the_silence_falls_inside_the_marked_band(edf):
    """De kern. Bij juiste uitlijning is het signaal stil BINNEN de band en
    niet erbuiten — dat onderscheidt een goed venster van een verschoven."""
    axes, fig = _panel(edf)
    x, y = _line(axes["flow"])
    binnen = (x >= DROP_START) & (x < DROP_END)
    buiten = ~binnen
    assert np.abs(y[binnen]).max() < 0.1 * AMP, "de band ligt niet op de stilte"
    assert np.abs(y[buiten]).max() > 0.5 * AMP, "buiten de band is het ook stil"
    plt.close(fig)


def test_a_deliberately_shifted_event_fails_the_same_check(edf):
    """Bewijst dat de toets hierboven iets meet: schuif het event 25 s op en
    de stilte zit niet meer in de band."""
    axes, fig = _panel(edf, onset=DROP_START + 25)
    x, y = _line(axes["flow"])
    binnen = (x >= DROP_START + 25) & (x < DROP_END + 25)
    assert np.abs(y[binnen]).max() > 0.5 * AMP
    plt.close(fig)


def test_mixed_sample_rates_do_not_shift_the_time_axis(edf):
    """Het EEG op 256 Hz bepaalt info['sfreq'] terwijl de ademkanalen op 32 Hz
    staan. Elke kanaal-as moet toch dezelfde seconden dragen."""
    axes, fig = _panel(edf)
    xf, _ = _line(axes["flow"])
    for ct in ("thorax", "abdomen", "spo2"):
        xo, _ = _line(axes[ct])
        assert xo[0] == pytest.approx(xf[0], abs=0.05), f"{ct} loopt uit de pas"
        assert xo[-1] == pytest.approx(xf[-1], abs=0.05), f"{ct} loopt uit de pas"
    plt.close(fig)


# ──────────────────────────────────────────────────────────────
#  Schaal
# ──────────────────────────────────────────────────────────────

def test_the_reference_breathing_is_not_clipped(edf):
    """Met median±4·MAD over het hele venster stortte de schaal in zodra het
    event stil genoeg was, en verdween juist de ademhaling waartegen de lezer
    de reductie beoordeelt."""
    axes, fig = _panel(edf)
    for ct, amp in (("flow", AMP), ("thorax", AMP * 0.8), ("abdomen", AMP * 0.6)):
        lo, hi = axes[ct].get_ylim()
        assert lo <= -amp and hi >= amp, (
            f"{ct}: referentie-ademhaling ±{amp:.0f} valt buiten de y-as "
            f"({lo:.0f}, {hi:.0f})")
    plt.close(fig)


def test_the_old_rule_would_have_clipped_this(edf):
    """Maakt de toets hierboven zelfbewijzend: pas de OUDE regel toe op exact
    dezelfde data en laat zien dat hij faalt. Zonder dit kan het fixture stil
    te braaf worden en meet er niets meer."""
    axes, fig = _panel(edf)
    _, y = _line(axes["flow"])
    med = np.median(y)
    mad = np.median(np.abs(y - med))
    assert mad > 0
    lo, hi = med - 4 * mad, med + 4 * mad
    marge = max((hi - lo) * 0.05, 1)
    lo, hi = lo - marge, hi + marge
    assert not (lo <= -AMP and hi >= AMP), (
        f"median±4·MAD klemt hier niet ({lo:.1f}, {hi:.1f}) — dit fixture "
        "reproduceert de fout niet meer en de schaaltoets meet niets")
    plt.close(fig)


def test_the_event_itself_stays_in_view(edf):
    axes, fig = _panel(edf)
    for ct in ("flow", "thorax", "abdomen"):
        lo, hi = axes[ct].get_ylim()
        assert lo < 0 < hi, f"{ct}: de nullijn van het event valt buiten beeld"
    plt.close(fig)


def test_a_flat_channel_does_not_collapse_the_axis(edf, tmp_path):
    """Een dood kanaal mag geen y-as van hoogte nul geven."""
    axes, fig = _panel(edf)
    for ct in ("flow", "thorax", "abdomen", "spo2"):
        lo, hi = axes[ct].get_ylim()
        assert hi > lo, f"{ct}: y-as heeft hoogte nul"
    plt.close(fig)
