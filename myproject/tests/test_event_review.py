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


# ──────────────────────────────────────────────────────────────
#  Telt dit event mee in de AHI?
# ──────────────────────────────────────────────────────────────
#
# Zonder dit label kan een beoordelaar niet zien of het event dat hij bekijkt
# in het hoofdgetal zit. Bij "uncertain" is dat contra-intuïtief: een apneu die
# de effort-classificatie niet kon onderverdelen valt BUITEN `ahi_total`
# (bewust conservatief), terwijl `hypopnea_uncertain` gewoon meetelt omdat de
# telling in psgscoring op de substring "hypopnea" matcht. Twee labels die
# allebei "uncertain" zeggen en zich tegengesteld gedragen.

from event_review import (COUNTED, NOT_COUNTED, NOT_SCORED,  # noqa: E402
                          UNCERTAIN_ONLY, ahi_membership)


@pytest.mark.parametrize("typ,verwacht", [
    ("obstructive", COUNTED),
    ("central", COUNTED),
    ("mixed", COUNTED),
    ("hypopnea", COUNTED),
    ("hypopnea_central", COUNTED),
    ("hypopnea_mixed", COUNTED),
    ("hypopnea_uncertain", COUNTED),      # substring "hypopnea" → telt mee
    ("uncertain", UNCERTAIN_ONLY),        # niet-onderverdeelde APNEU → niet
    ("rera", NOT_COUNTED),
    ("", NOT_COUNTED),
    (None, NOT_COUNTED),
])
def test_ahi_membership(typ, verwacht):
    assert ahi_membership(typ) == verwacht


def test_the_two_uncertain_labels_differ():
    """De kern van de vraag: ze lezen hetzelfde en tellen anders."""
    assert ahi_membership("uncertain") != ahi_membership("hypopnea_uncertain")


def test_ahi_membership_matches_psgscoring():
    """Pin de spiegel vast op psgscoring zelf.

    `ahi_membership` herhaalt een regel die in `_compute_summary` inline staat
    en niet als functie geëxporteerd wordt. Deze toets laat psgscoring ÉCHT
    tellen — één event per type — en controleert of `ahi_total` en
    `ahi_incl_uncertain` bewegen zoals het label belooft. Verandert psgscoring
    de regel, dan valt dit om in plaats van dat het rapport stil gaat liegen.
    """
    resp = pytest.importorskip("psgscoring.respiratory")
    hypno = ["N2"] * 240                       # 2 uur slaap
    leeg = resp._compute_summary([], hypno)
    basis_tot = leeg.get("ahi_total") or 0.0
    basis_unc = leeg.get("ahi_incl_uncertain") or 0.0

    for typ in ("obstructive", "central", "mixed", "hypopnea",
                "hypopnea_central", "hypopnea_uncertain", "uncertain"):
        ev = [{"type": typ, "onset_s": 100.0, "duration_s": 20.0,
               "stage": "N2", "epoch": 3, "confidence": 0.9}]
        s = resp._compute_summary(ev, hypno)
        in_tot = (s.get("ahi_total") or 0.0) > basis_tot
        in_unc = (s.get("ahi_incl_uncertain") or 0.0) > basis_unc
        label = ahi_membership(typ)
        assert (label == COUNTED) == in_tot, (
            f"{typ}: label zegt {label}, ahi_total beweegt={in_tot}")
        assert (label in (COUNTED, UNCERTAIN_ONLY)) == in_unc, (
            f"{typ}: label zegt {label}, ahi_incl_uncertain beweegt={in_unc}")


def test_a_rejected_candidate_is_marked_as_never_scored():
    """Onderscheid dat er voor de lezer toe doet: een afgewezen kandidaat is
    nooit een event geworden, terwijl een RERA WEL gescoord is en alleen niet
    in de AHI zit. Allebei "telt niet mee" noemen wist dat verschil."""
    rej = [{"type": "hypopnea", "onset_s": 300.0, "duration_s": 13.0,
            "reject_reason": "local_reduction_19pct<20pct"}]
    gekozen = select_review_events(_pneumo([], rej), n=2)
    assert gekozen[0]["_ahi"] == NOT_SCORED
    assert NOT_SCORED != NOT_COUNTED


def test_a_scored_rera_is_not_the_same_as_a_rejected_candidate():
    evs = [_ev(100, 0.5, "rera")]
    assert select_review_events(_pneumo(evs), n=2)[0]["_ahi"] == NOT_COUNTED


def test_scored_events_carry_their_membership():
    evs = [_ev(100, 0.5, "uncertain"), _ev(200, 0.5, "hypopnea_uncertain")]
    m = {e["type"]: e["_ahi"] for e in select_review_events(_pneumo(evs), n=4)}
    assert m["uncertain"] == UNCERTAIN_ONLY
    assert m["hypopnea_uncertain"] == COUNTED


# ──────────────────────────────────────────────────────────────
#  Regel B en makkelijke gevallen
# ──────────────────────────────────────────────────────────────

def test_rule_b_cases_get_their_own_category():
    """Hypopneeën die via een AROUSAL kwalificeerden in plaats van via
    desaturatie. Daar zit de meeste subjectiviteit, dus die wil je zien."""
    evs = [_ev(100, 0.8), _ev(200, 0.8, rule1a_arousal=True), _ev(300, 0.8)]
    soorten = {e["onset_s"]: e["_review_kind"]
               for e in select_review_events(_pneumo(evs), n=12)}
    assert soorten.get(200.0) == "rule_b"


def test_the_legacy_rule1b_flag_is_read_too():
    """Oudere resultaten dragen alleen de historische alias."""
    evs = [_ev(100, 0.8), _ev(200, 0.8, rule1b=True)]
    soorten = {e["onset_s"]: e["_review_kind"]
               for e in select_review_events(_pneumo(evs), n=12)}
    assert soorten.get(200.0) == "rule_b"


def test_clear_cut_cases_are_included_as_a_yardstick():
    """Niet om na te kijken maar om te ijken — en zonder deze categorie is de
    verzameling uitsluitend grensgevallen, en dus scheef."""
    evs = [_ev(i * 100, 0.30 + i * 0.05) for i in range(1, 13)]
    gekozen = select_review_events(_pneumo(evs), n=12)
    makkelijk = [e for e in gekozen if e["_review_kind"] == "easy"]
    assert makkelijk, "geen enkel duidelijk geval geselecteerd"
    assert max(e["confidence"] for e in makkelijk) == max(
        e["confidence"] for e in evs)


def test_hard_and_easy_are_both_present():
    evs = [_ev(i * 100, 0.20 + i * 0.06) for i in range(1, 13)]
    soorten = {e["_review_kind"] for e in select_review_events(_pneumo(evs), n=12)}
    assert {"borderline", "easy"} <= soorten, soorten


def test_a_clear_cut_case_is_not_relabelled_as_borderline():
    """Het event met de hoogste confidence mag niet als twijfelgeval eindigen."""
    evs = [_ev(i * 100, 0.20 + i * 0.06) for i in range(1, 13)]
    gekozen = select_review_events(_pneumo(evs), n=12)
    hoogste = max(gekozen, key=lambda e: e["confidence"])
    assert hoogste["_review_kind"] == "easy"
