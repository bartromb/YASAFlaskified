"""De visuele eventcontrole: selectie, poorten en gedrag bij ontbrekende data.

Twee dingen die deze weergave anders doen dan het PDF-rapport, en die daarom
vastliggen:

1. **De selectie is omgedraaid.** `_select_example_events` in de
   rapportgenerator kiest de hoogste confidence, het langste event en de
   grootste desaturatie — de meest overtuigende voorbeelden. Voor controle is
   dat waardeloos: wat het algoritme moeiteloos goed doet hoef je niet na te
   kijken. Hier krijgen de laagste confidence en de afgewezen kandidaten
   voorrang.

2. **Twee poorten.** `requires_role("admin")` én `job_access_required`. De
   eerste omdat ruwe signalen geen uitslag zijn; de tweede omdat de meta-toets
   in test_job_routes_protected elke route met <job_id> telt.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from event_review import (MAX_PANELS, _rejection_nearness,  # noqa: E402
                          channel_map_for, resolve_edf_path,
                          select_review_events)


def _ev(onset, conf, typ="hypopnea", **kw):
    return {"type": typ, "onset_s": float(onset), "duration_s": 20.0,
            "stage": "N2", "confidence": conf, **kw}


def _pneumo(events=None, rejected=None):
    return {"respiratory": {"events": events or [],
                            "rejected_hypopneas": rejected or []}}


# ──────────────────────────────────────────────────────────────
#  Selectie
# ──────────────────────────────────────────────────────────────

def test_the_least_certain_events_come_first():
    """Het omgekeerde van wat het rapport doet."""
    evs = [_ev(100, 0.95), _ev(200, 0.42), _ev(300, 0.88), _ev(400, 0.51)]
    gekozen = select_review_events(_pneumo(evs), n=2)
    onsets = {e["onset_s"] for e in gekozen}
    assert 200.0 in onsets, "het minst zekere event ontbreekt"
    assert 100.0 not in onsets, "het meest zekere event verdringt een twijfelgeval"


def test_rejected_candidates_are_shown_with_their_reason():
    rej = [{"type": "hypopnea", "onset_s": 500.0, "duration_s": 15.0,
            "reject_reason": "local_reduction_19pct<20pct"}]
    gekozen = select_review_events(_pneumo([_ev(100, 0.9)], rej), n=6)
    afgewezen = [e for e in gekozen if e["_review_kind"] == "rejected"]
    assert afgewezen, "afgewezen kandidaten komen niet in de selectie"
    assert "19pct<20pct" in afgewezen[0]["_review_note"]


def test_the_closest_rejection_wins():
    """19 van 20 procent is een grensgeval; 2 van 20 is dat niet."""
    rej = [{"type": "hypopnea", "onset_s": 100.0, "duration_s": 15.0,
            "reject_reason": "local_reduction_2pct<20pct"},
           {"type": "hypopnea", "onset_s": 200.0, "duration_s": 15.0,
            "reject_reason": "local_reduction_19pct<20pct"}]
    gekozen = select_review_events(_pneumo([], rej), n=1)
    assert gekozen[0]["onset_s"] == 200.0


@pytest.mark.parametrize("reason,verwacht", [
    ("local_reduction_19pct<20pct", 0.95),
    ("stable_breathing_cv_0.12<0.25", 0.48),
    ("pre_event_reduction_5pct<20pct", 0.25),
    ("iets_onbekends", 0.5),
    ("", 0.5),
])
def test_rejection_nearness_reads_the_reason(reason, verwacht):
    assert _rejection_nearness({"reject_reason": reason}) == pytest.approx(
        verwacht, abs=0.02)


def test_every_event_type_gets_a_representative():
    evs = [_ev(100, 0.9, "obstructive"), _ev(200, 0.9, "central"),
           _ev(300, 0.9, "hypopnea"), _ev(400, 0.9, "mixed")]
    typen = {e["type"] for e in select_review_events(_pneumo(evs), n=8)}
    assert typen == {"obstructive", "central", "hypopnea", "mixed"}


def test_the_selection_is_deterministic():
    """Twee weergaven van dezelfde job horen dezelfde panelen te tonen."""
    evs = [_ev(i * 100, 0.5) for i in range(1, 12)]
    a = [e["onset_s"] for e in select_review_events(_pneumo(evs), n=5)]
    b = [e["onset_s"] for e in select_review_events(_pneumo(evs), n=5)]
    assert a == b


def test_panels_are_returned_in_time_order():
    evs = [_ev(900, 0.2), _ev(100, 0.3), _ev(500, 0.1)]
    onsets = [e["onset_s"] for e in select_review_events(_pneumo(evs), n=3)]
    assert onsets == sorted(onsets)


def test_no_event_appears_twice():
    """Een event kan zowel het minst zekere als het eerste van zijn type zijn."""
    evs = [_ev(100, 0.2, "central"), _ev(200, 0.9, "hypopnea")]
    gekozen = select_review_events(_pneumo(evs), n=8)
    assert len({e["onset_s"] for e in gekozen}) == len(gekozen)


def test_the_count_is_bounded():
    """Elk paneel kost rendertijd; een job met 400 events mag geen
    verzoek van een minuut worden."""
    evs = [_ev(i * 30, 0.5) for i in range(400)]
    assert len(select_review_events(_pneumo(evs), n=9999)) <= MAX_PANELS


def test_events_without_an_onset_are_skipped():
    evs = [{"type": "hypopnea", "duration_s": 20.0, "confidence": 0.2},
           _ev(100, 0.3)]
    gekozen = select_review_events(_pneumo(evs), n=5)
    assert all(e.get("onset_s") is not None for e in gekozen)


def test_an_empty_analysis_yields_nothing_rather_than_raising():
    assert select_review_events({}, n=5) == []
    assert select_review_events(None, n=5) == []
    assert select_review_events(_pneumo([], []), n=5) == []


# ──────────────────────────────────────────────────────────────
#  Kanaalmap en EDF-pad
# ──────────────────────────────────────────────────────────────

def test_the_channel_map_comes_from_the_analysis_not_a_guess():
    data = {"pneumo": {"meta": {"channels_used": {"flow": "Resp nasal",
                                                  "thorax": "", "spo2": "SaO2"}}}}
    assert channel_map_for(data) == {"flow": "Resp nasal", "spo2": "SaO2"}


def test_the_scored_edf_is_not_mistaken_for_the_source(tmp_path):
    (tmp_path / "job1_scored.edf").write_bytes(b"x")
    (tmp_path / "job1.edf").write_bytes(b"x")
    assert resolve_edf_path("job1", str(tmp_path)).endswith("job1.edf")


def test_a_missing_edf_is_reported_as_absent(tmp_path):
    assert resolve_edf_path("weg", str(tmp_path)) is None


def test_the_config_path_wins_when_it_exists(tmp_path):
    import json
    echt = tmp_path / "elders.edf"
    echt.write_bytes(b"x")
    (tmp_path / "job2_config.json").write_text(json.dumps({"edf_path": str(echt)}))
    (tmp_path / "job2.edf").write_bytes(b"x")
    assert resolve_edf_path("job2", str(tmp_path)) == str(echt)


def test_a_config_pointing_at_a_deleted_file_falls_back(tmp_path):
    import json
    (tmp_path / "job3_config.json").write_text(
        json.dumps({"edf_path": "/bestaat/niet.edf"}))
    (tmp_path / "job3.edf").write_bytes(b"x")
    assert resolve_edf_path("job3", str(tmp_path)).endswith("job3.edf")


# ──────────────────────────────────────────────────────────────
#  Poorten
# ──────────────────────────────────────────────────────────────

def test_the_route_is_admin_only_and_job_gated():
    """Beide decorators, om twee verschillende redenen."""
    import app as appmod
    view = appmod.app.view_functions["event_review"]
    assert getattr(view, "_job_access", False), \
        "route telt niet mee in de job-toegangstoets"
    src = Path(appmod.__file__).with_suffix(".py").read_text()
    blok = src[src.index('@app.route("/review/<job_id>")'):]
    blok = blok[:blok.index("def event_review")]
    assert '@requires_role("admin")' in blok, "rolpoort ontbreekt"
    assert "@job_access_required" in blok, "job-poort ontbreekt"
