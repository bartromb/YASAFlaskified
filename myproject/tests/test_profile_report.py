"""tests/test_profile_report.py — het profielrapport en de studiewachtrij.

Twee dingen worden hier bewaakt die geen van beide over opmaak gaan:

1. De **wachtrijverdeling**. Een profielvergelijking kost gemeten 45:59 en
   RQ kent geen prioriteit binnen één wachtrij. De bescherming van klinische
   doorlooptijd zit dus volledig in `docker-compose.yml`: zes workers luisteren
   alleen op `default`, twee ook op `study`. Dat is een configuratiebestand dat
   niemand test tenzij je het opschrijft, en als het stilletjes terugvalt naar
   acht workers op één wachtrij is er niets dat afgaat.

2. Dat het document **zegt wat het is**. Twee PDF's per opname betekent dat er
   één de verkeerde kant op kan.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_profile_report import _BANNER, generate_profile_report  # noqa: E402

# ── de wachtrijverdeling ────────────────────────────────────────────────
#
# Bewust ZONDER PyYAML gelezen. Die staat niet in requirements.txt, en hem daar
# zetten om een test te laten draaien zou een runtime-dependency toevoegen voor
# iets dat alleen de testsuite nodig heeft -- in een project waar zelfs
# PyWavelets een optionele extra is. De compose-structuur is klein en vast
# genoeg om regelgewijs te lezen; de prijs is dat een herformattering deze test
# breekt, en dat is de goede kant om te falen.

@pytest.fixture(scope="module")
def compose_workers():
    """{servicenaam: effectief rq-commando}, met de anchor-basis meegerekend."""
    with open(os.path.join(REPO, "docker-compose.yml")) as f:
        lines = f.read().splitlines()

    base = None
    for ln in lines:
        m = re.match(r"^\s*command:\s*(rq worker .*)$", ln)
        if m and base is None:
            base = m.group(1).strip()
            break
    assert base, "geen basiscommando in x-worker-base gevonden"

    workers, current = {}, None
    for ln in lines:
        m = re.match(r"^  (worker\d+):\s*$", ln)
        if m:
            current = m.group(1)
            workers[current] = base          # erft van *worker-base
            continue
        if current:
            if re.match(r"^  \S", ln):        # volgende service
                current = None
                continue
            m2 = re.match(r"^\s+command:\s*(rq worker .*)$", ln)
            if m2:
                workers[current] = m2.group(1).strip()
    assert len(workers) >= 8, f"verwachtte acht workers, vond {len(workers)}"
    return workers


def test_most_workers_never_touch_the_study_queue(compose_workers):
    """Klinisch werk mag niet achter een vergelijking van 46 minuten komen."""
    workers = compose_workers
    study = {k for k, v in workers.items() if "study" in v}
    clinical_only = set(workers) - study
    assert len(clinical_only) >= 6, (
        f"slechts {len(clinical_only)} workers zijn voorbehouden aan klinisch "
        f"werk; met minder kan een studievergelijking de wachtrij bezetten")
    assert 1 <= len(study) <= 2, (
        f"{len(study)} workers pakken studiewerk op; meer dan twee ondergraaft "
        f"de reservering hierboven")


def test_study_workers_drain_the_clinical_queue_first(compose_workers):
    """`default study` betekent: default eerst. De volgorde is de prioriteit."""
    for name, cmd in compose_workers.items():
        if "study" not in cmd:
            continue
        tail = cmd.split("6379", 1)[1].split()
        assert tail == ["default", "study"], (
            f"{name}: wachtrijvolgorde is {tail}; 'study' vóór 'default' zou "
            f"onderzoek voorrang geven op klinisch werk")


def test_no_worker_listens_only_to_study(compose_workers):
    """Een worker die alleen studiewerk doet staat 23 uur per dag stil."""
    for name, cmd in compose_workers.items():
        if "study" in cmd:
            assert "default" in cmd, name


# ── het document ────────────────────────────────────────────────────────

def _ev(o, d, t="obstructive"):
    return {"onset_s": float(o), "duration_s": float(d), "type": t}


@pytest.fixture
def rendered(tmp_path):
    from psgscoring.agreement import compare_event_sets
    a = [_ev(10, 15), _ev(100, 20, "hypopnea"), _ev(300, 12, "uncertain")]
    b = [_ev(10, 15), _ev(900, 20, "hypopnea"), _ev(300, 12, "central")]
    comparison = {
        "_meta": {"primary_profile": "aasm_v3_rec",
                  "profiles_compared": ["aasm_v3_rec", "aasm_v3_breath"],
                  "psgscoring_version": "0.20.0", "hypnogram_shared": True,
                  "wall_clock_s": {"aasm_v3_rec": 336.2,
                                   "aasm_v3_breath": 341.0},
                  "n_events": {"aasm_v3_rec": 3, "aasm_v3_breath": 3},
                  "flow_channels": {
                      "aasm_v3_rec": {"apnea_sensor": "Pres",
                                      "hypopnea_sensor": "Pres",
                                      "dual_sensor": False,
                                      "thermistor_rejected": "Therm",
                                      "thermistor_check": {
                                          "reason": "overeenstemming 0.39 < 0.40"}}}},
        "aasm_v3_rec": {"ahi_total": 19.6, "oahi": 16.7, "central_index": 1.4,
                        "n_ah_total": 3, "rdi": None, "severity": "Moderate"},
        "aasm_v3_breath": {"ahi_total": 14.2, "oahi": 11.2, "central_index": 1.1,
                           "n_ah_total": 3, "rdi": 41.0, "severity": "Mild",
                           "agreement_vs_primary": compare_event_sets(
                               a, b, label_a="aasm_v3_rec",
                               label_b="aasm_v3_breath")},
    }
    pneumo = {"meta": {"scoring_profile": "aasm_v3_rec"},
              "respiratory": {"summary": {"ahi_total": 19.6}}}
    out = str(tmp_path / "r.pdf")
    generate_profile_report(pneumo, comparison, out, job_id="abc12345")
    import subprocess
    txt = subprocess.run(["pdftotext", out, "-"], capture_output=True,
                         text=True).stdout
    return out, txt


def test_every_page_carries_the_research_marking(rendered):
    """Een banner op alleen pagina 1 beschermt pagina 2 niet."""
    out, txt = rendered
    pages = txt.split("\f")[:-1]
    assert len(pages) >= 2
    key = _BANNER.split("—")[0].strip()
    for i, page in enumerate(pages, 1):
        assert key in page, f"pagina {i} draagt de markering niet"


def test_the_four_sections_are_present(rendered):
    _out, txt = rendered
    for section in ("A. Indexmatrix", "B. Eventovereenkomst",
                    "C. Sensorherkomst", "D. Herkomst"):
        assert section in txt, section


def test_missing_values_are_dashes_never_zero(rendered):
    """RDI ontbreekt op het primaire profiel; dat is '—', geen 0,0."""
    _out, txt = rendered
    assert "—" in txt
    assert "0.0" not in txt.split("D. Herkomst")[0], (
        "een 0,0 in een rapport is een meting, geen ontbrekende waarde")


def test_both_uncertain_variants_are_shown(rendered):
    _out, txt = rendered
    assert "incl." in txt and "excl." in txt
    assert "uncertain" in txt


def test_the_primary_marker_actually_renders(rendered):
    """▶ bestaat niet in base-14 Helvetica en komt eruit als een blokje.

    Deze test faalt als iemand het merkteken terugzet naar een glyph die het
    lettertype niet heeft — een fout die je in de code niet ziet.
    """
    _out, txt = rendered
    assert "»" in txt, "merkteken van het primaire profiel ontbreekt"
    assert "■" not in txt, "een teken rendert als ontbrekende glyph"


def test_no_recommendation_is_made(rendered):
    """De matrix beschrijft; de onderzoeker kiest.

    Zoeken op het woord "aanbeveling" werkt niet: het rapport zegt zelf dat het
    er géén doet, en die zin bevat het woord. Dit is dezelfde valkuil als een
    test die struikelt over het commentaar dat uitlegt waarom iets verboden is.
    Getoetst wordt dus de bewéring — een profiel dat als beter wordt aangewezen
    — plus de aanwezigheid van de ontkenning zelf.
    """
    _out, txt = rendered
    low = txt.lower()
    claims = ("beste profiel is", "aanbevolen profiel is", "wij adviseren",
              "we adviseren", "voorkeursprofiel", "beter dan")
    for claim in claims:
        assert claim not in low, f"het rapport doet een uitspraak: {claim!r}"
    assert "de matrix beschrijft" in low, (
        "de expliciete ontkenning ontbreekt; zonder die zin is het aan de "
        "lezer om te raden of een rij een aanbeveling is")


def test_wall_clock_comes_from_the_run(rendered):
    _out, txt = rendered
    assert "336.2" in txt and "341.0" in txt


def test_a_comparison_without_agreement_says_so(tmp_path):
    """Ontbrekende overeenkomst mag niet lezen als 'geen verschillen'."""
    comparison = {
        "_meta": {"primary_profile": "aasm_v3_rec",
                  "profiles_compared": ["aasm_v3_rec"],
                  "psgscoring_version": "0.20.0"},
        "aasm_v3_rec": {"ahi_total": 19.6, "oahi": 16.7, "severity": "Moderate"},
    }
    out = str(tmp_path / "r2.pdf")
    generate_profile_report({"meta": {"scoring_profile": "aasm_v3_rec"}},
                            comparison, out, job_id="x")
    import subprocess
    txt = subprocess.run(["pdftotext", out, "-"], capture_output=True,
                         text=True).stdout
    assert "Geen overeenkomstgegevens" in txt
    assert "geen verschillen" in txt.lower()
