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

# Zoals een echte klinische montage met ÉÉN druksensor eruitziet: de rollen
# `flow` en `flow_pressure` wijzen naar hetzelfde fysieke kanaal. Dit is de
# regel, niet de uitzondering — op productie gold het voor elke opname.
CH_MAP_GEDEELD = {"flow": "Flow", "flow_pressure": "Flow",
                  "thorax": "Thorax", "abdomen": "Abdomen", "spo2": "SpO2"}


def _panel(edf_path, onset=DROP_START, dur=DROP_END - DROP_START, ch_map=None):
    """Render en geef de assen terug, per kanaaltype."""
    grabbed = {}
    real_subplots = plt.subplots

    def spy(*a, **kw):
        fig, axes = real_subplots(*a, **kw)
        grabbed["fig"], grabbed["axes"] = fig, np.atleast_1d(axes)
        return fig, axes

    cm = CH_MAP if ch_map is None else ch_map
    real_close = plt.close
    plt.subplots, plt.close = spy, lambda *a, **k: None
    try:
        g._plot_epoch_example(edf_path, cm,
                              {"type": "obstructive", "onset_s": onset,
                               "duration_s": dur, "confidence": 0.9},
                              hypno=["N2"] * 20)
    finally:
        plt.subplots, plt.close = real_subplots, real_close

    if "axes" not in grabbed:
        return {}, None
    axes = grabbed["axes"]
    # Ontdubbeld op kanaalNAAM, in de volgorde van _EPOCH_CH_ORDER — dezelfde
    # regel die de tekenfunctie toepast.
    order, gezien = [], set()
    for ct, _, _ in g._EPOCH_CH_ORDER:
        naam = cm.get(ct)
        if naam and naam not in gezien:
            gezien.add(naam)
            order.append(ct)
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


# ──────────────────────────────────────────────────────────────
#  Twee rollen, één kanaal
# ──────────────────────────────────────────────────────────────
#
# In productie viel de hele weergave om met "Geen enkel paneel kon getekend
# worden". Oorzaak: op een montage met één druksensor wijzen `flow` en
# `flow_pressure` naar hetzelfde kanaal, en `raw.pick()` weigert een lijst met
# dubbels — "Found 6 / 7 unique names, sel is not unique". Dat was de regel op
# élke klinische opname, niet een randgeval; mijn fixture had toevallig
# uitsluitend unieke kanaalnamen en zag het dus niet.

def test_two_roles_sharing_one_channel_still_render(edf):
    axes, fig = _panel(edf, ch_map=CH_MAP_GEDEELD)
    assert fig is not None, "geen enkel paneel getekend bij een gedeeld kanaal"
    plt.close(fig)


def test_a_shared_channel_is_drawn_once(edf):
    """Dezelfde curve twee keer onder twee labels suggereert twee sensoren
    die het eens zijn — in een controle-instrument de verkeerde indruk."""
    axes, fig = _panel(edf, ch_map=CH_MAP_GEDEELD)
    assert len(fig.axes) == 4, (
        f"verwacht 4 rijen (Flow, Thorax, Abdomen, SpO2), kreeg {len(fig.axes)}")
    plt.close(fig)


def test_the_shared_channel_keeps_its_data(edf):
    """Ontdubbelen mag geen kanaal laten vallen dat wél getekend hoort."""
    axes, fig = _panel(edf, ch_map=CH_MAP_GEDEELD)
    x, y = _line(axes["flow"])
    binnen = (x >= DROP_START) & (x < DROP_END)
    assert np.abs(y[binnen]).max() < 0.1 * AMP
    assert np.abs(y[~binnen]).max() > 0.5 * AMP
    plt.close(fig)


def test_load_panel_raw_survives_duplicate_roles(edf):
    """De gedeelde EDF-lezing is waar het knapte, niet het tekenen."""
    raw = g.load_panel_raw(edf, CH_MAP_GEDEELD)
    assert raw is not None, "load_panel_raw geeft None bij een gedeeld kanaal"
    assert len(raw.ch_names) == len(set(raw.ch_names)), "dubbele kanalen geladen"
    assert "Flow" in raw.ch_names


# ──────────────────────────────────────────────────────────────
#  Buurevents: afwezigheid van blauw moet iets betekenen
# ──────────────────────────────────────────────────────────────
#
# De oude regel sloeg elk buurevent over waarvoor
# `oe_onset < t_start + 2 or oe_end > t_end - 2` gold — precies de
# half-zichtbare buren, de meest voorkomende soort. Aangetoond op PSG-IPA SN3:
# in het venster rond de obstructieve apneu bij t=316,6 s staat een tweede
# apneu op 359,4–371,1 s die 8,5 s over de rand loopt en dus onbemarkeerd bleef,
# terwijl hij in beeld stond. "Geen blauw" betekende daardoor niet "niet
# gescoord" maar "misschien wel". Dat is voor een controle-instrument fataal.

def _spans(ax):
    """x-bereiken van de gearceerde vlakken (`axvspan`) op een as.

    Let op het patch-type: matplotlib 3.11 geeft een **Rectangle** terug,
    oudere versies een Polygon. Een helper die alleen Polygon herkende gaf hier
    een lege lijst, waardoor twee toetsen leeg slaagden — ze controleerden de
    AFWEZIGHEID van een markering en kregen die gratis. Vandaar dat elke
    buurtoets hieronder eerst `_assert_event_span` doet: valt deze helper stil,
    dan faalt álles in plaats van stilletjes groen te blijven.
    """
    from matplotlib.patches import Polygon, Rectangle
    uit = []
    for p in ax.patches:
        if isinstance(p, Rectangle):
            x, w = float(p.get_x()), float(p.get_width())
            uit.append((x, x + w))
        elif isinstance(p, Polygon):
            xy = np.asarray(p.get_xy())
            if xy.ndim == 2 and xy.shape[1] == 2:
                uit.append((float(xy[:, 0].min()), float(xy[:, 0].max())))
    return uit


def _assert_event_span(ax):
    """Het rode vlak van het event zelf moet altijd gevonden worden."""
    treffers = [s for s in _spans(ax)
                if abs(s[0] - DROP_START) < 1 and abs(s[1] - DROP_END) < 1]
    assert treffers, ("_spans() vindt het event-vlak niet — de helper is stuk "
                      "en de buurtoetsen meten niets meer")


def _panel_met_buren(edf_path, buren):
    grabbed = {}
    real_subplots, real_close = plt.subplots, plt.close

    def spy(*a, **kw):
        fig, axes = real_subplots(*a, **kw)
        grabbed["fig"], grabbed["axes"] = fig, np.atleast_1d(axes)
        return fig, axes

    plt.subplots, plt.close = spy, lambda *a, **k: None
    try:
        g._plot_epoch_example(
            edf_path, CH_MAP,
            {"type": "obstructive", "onset_s": DROP_START,
             "duration_s": DROP_END - DROP_START, "confidence": 0.9},
            hypno=["N2"] * 20, all_events=buren)
    finally:
        plt.subplots, plt.close = real_subplots, real_close
    return grabbed["axes"][0], grabbed["fig"]


def test_a_neighbour_crossing_the_window_edge_is_still_marked(edf):
    """Het geval uit SN3: een buur die over de rand loopt."""
    buren = [{"type": "obstructive", "onset_s": DROP_END + 25,
              "duration_s": 40.0}]          # loopt ruim voorbij t_end
    ax, fig = _panel_met_buren(edf, buren)
    _assert_event_span(ax)
    randen = [s for s in _spans(ax) if s[0] > DROP_END + 20]
    assert randen, "buurevent over de vensterrand wordt niet gemarkeerd"
    plt.close(fig)


def test_a_neighbour_starting_before_the_window_is_still_marked(edf):
    buren = [{"type": "hypopnea", "onset_s": DROP_START - 40,
              "duration_s": 35.0}]          # begint vóór t_start, loopt erin
    ax, fig = _panel_met_buren(edf, buren)
    _assert_event_span(ax)
    vroeg = [s for s in _spans(ax) if s[0] < DROP_START - 10]
    assert vroeg, "buurevent dat vóór het venster begint wordt niet gemarkeerd"
    plt.close(fig)


def test_the_marking_is_clipped_to_the_window(edf):
    """Niet buiten de as tekenen; anders herschaalt matplotlib de x-as en
    verandert het getoonde venster."""
    buren = [{"type": "obstructive", "onset_s": DROP_END + 25,
              "duration_s": 200.0}]
    ax, fig = _panel_met_buren(edf, buren)
    _assert_event_span(ax)
    lo, hi = ax.get_xlim()
    # t_end = 350; matplotlib zet daar zijn gebruikelijke marge omheen (~353).
    # Een niet-afgeknipte markering zou tot 545 lopen.
    assert hi <= DROP_END + 40, f"x-as opgerekt tot {hi:.0f}"
    plt.close(fig)


def test_a_neighbour_outside_the_window_is_not_marked(edf):
    """De markering moet nog steeds iets uitsluiten."""
    buren = [{"type": "obstructive", "onset_s": DROP_END + 500,
              "duration_s": 20.0}]
    ax, fig = _panel_met_buren(edf, buren)
    _assert_event_span(ax)
    assert not [s for s in _spans(ax) if s[0] > DROP_END + 40]
    plt.close(fig)


def test_rejected_candidates_are_not_marked_as_scored(edf):
    """Blauw betekent GESCOORD. Een afgewezen kandidaat hoort er niet in."""
    buren = [{"type": "rejected_hypopnea", "onset_s": DROP_END + 5,
              "duration_s": 10.0}]
    ax, fig = _panel_met_buren(edf, buren)
    _assert_event_span(ax)
    assert not [s for s in _spans(ax) if DROP_END + 3 < s[0] < DROP_END + 8]
    plt.close(fig)
