"""Split-night: de kop, het overzicht en de nachtgrafieken.

WAAROM DEZE TESTS BESTAAN
-------------------------
Eén AHI over een split-night middelt twee helften die niet vergelijkbaar zijn.
Op de casus die dit aanleiding gaf stond in de kop "Mild SAS, AHI 10,1/u"
terwijl het diagnostische deel op 83,5/u lag — wie alleen de eerste bladzijde
las, zag geen enkel teken dat de nacht in tweeën viel.

Het gemiddelde is daarom uit de kop gehaald: er staat nu AHI zonder en met
CPAP. Hetzelfde in de studielijst, en op elke nachtgrafiek een markering waar
het tweede deel begint — anders is een saturatie die halverwege herstelt niet
te onderscheiden van een patiënt die vanzelf beter wordt.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bron(naam):
    with open(os.path.join(MY, naam), encoding="utf-8") as f:
        return f.read()


# ── 1. De kop toont met/zonder CPAP, niet het nachtgemiddelde ──────────

def test_de_kopvlag_noemt_geen_nacht_ahi_meer():
    """De vlag droeg `{ahi}` = het nachtgemiddelde als eerste getal. Precies
    dat getal is hier misleidend."""
    from i18n import TRANSLATIONS

    for taal in ("nl", "fr", "en", "de"):
        tekst = TRANSLATIONS["pdf_flag_split_night"][taal]
        assert "{ahi}" not in tekst, f"{taal} draagt nog het nachtgemiddelde"
        assert "{diag}" in tekst and "{ther}" in tekst, taal


def test_de_kpi_tegel_toont_de_therapiewaarde():
    bron = _bron("generate_pdf_report.py")
    i_split = bron.index("if _split_kpi:")
    blok = bron[i_split:i_split + 900]
    assert "pdf_kpi_ahi_cpap" in blok, "de tegel 'met CPAP' ontbreekt"
    assert "pdf_kpi_ahi_night" not in blok, \
        "het nachtgemiddelde staat nog als tegel in de split-nightkop"


def test_de_nieuwe_sleutels_bestaan_in_vier_talen():
    from i18n import TRANSLATIONS

    for sleutel in ("pdf_kpi_ahi_no_cpap", "pdf_kpi_ahi_cpap",
                    "pdf_split_marker", "dash_split_cpap",
                    "dash_split_no_cpap", "dash_split_tooltip"):
        entry = TRANSLATIONS[sleutel]
        for taal in ("nl", "fr", "en", "de"):
            assert entry.get(taal), f"{sleutel}/{taal}"


# ── 2. De studielijst toont beide helften ──────────────────────────────

def test_dashboard_splitst_de_ahi_cel():
    sjabloon = _bron("templates/dashboard.html")
    i = sjabloon.index("{# AHI")
    cel = sjabloon[i:i + 1200]
    assert "s.split_night" in cel, "de cel splitst niet op split-night"
    assert "s.ahi_diag" in cel and "s.ahi_ther" in cel


def test_dashboard_kleurt_op_het_diagnostische_deel():
    """De ernstkleur van `rsum['severity']` slaat op de hele nacht. Op een
    split-night hoort de balk het deel zonder therapie te volgen."""
    bron = _bron("app.py")
    assert 'ahi_diag_sev' in bron
    i = bron.index("ahi_diag_sev = (")
    blok = bron[i:i + 300]
    for woord in ("normal", "mild", "moderate", "severe"):
        assert woord in blok, woord


# ── 3. De markering staat op ELKE nachtgrafiek ─────────────────────────

def test_ov_setup_tekent_een_verticale_markering():
    """Gedragstest, geen bronlezing: staat de lijn op het juiste uur?"""
    import matplotlib
    matplotlib.use("Agg")
    from generate_pdf_report import _ov_setup

    fig, ax = _ov_setup(2.0, dur_h=8.0, split_h=2.25, split_label="start CPAP")
    xs = [ln.get_xdata()[0] for ln in ax.lines
          if len(set(ln.get_xdata())) == 1]
    assert 2.25 in xs, f"geen markering op 2,25 u; verticale lijnen: {xs}"


def test_geen_markering_zonder_split_night():
    import matplotlib
    matplotlib.use("Agg")
    from generate_pdf_report import _ov_setup

    fig, ax = _ov_setup(2.0, dur_h=8.0)
    verticaal = [ln for ln in ax.lines if len(set(ln.get_xdata())) == 1]
    assert not verticaal, "er staat een markering op een gewone nacht"


def test_markering_buiten_de_nacht_wordt_genegeerd():
    """Een breekpunt van 9 u op een nacht van 8 u is een detectiefout; die
    hoort niet als lijn op de rand te belanden."""
    import matplotlib
    matplotlib.use("Agg")
    from generate_pdf_report import _ov_setup

    for slecht in (0.0, 9.0, -1.0):
        fig, ax = _ov_setup(2.0, dur_h=8.0, split_h=slecht, split_label="x")
        verticaal = [ln for ln in ax.lines if len(set(ln.get_xdata())) == 1]
        assert not verticaal, f"markering getekend voor split_h={slecht}"


def test_alle_vijf_de_panelen_krijgen_het_breekpunt():
    """Als één paneel de markering mist, lees je dat paneel los van de rest."""
    bron = _bron("generate_pdf_report.py")
    for bouwer in ("_hypno_ov(", "_events_ov(", "_pos_ov(",
                   "_snore_ov(", "_spo2_ov("):
        i = bron.index(f"def {bouwer}")
        kop = bron[i:i + 220]
        assert "split_h" in kop, f"{bouwer} accepteert geen breekpunt"
    # en de aanroepen geven het ook door
    assert bron.count("split_h=_ov_split_h") == 5, \
        "niet alle vijf de aanroepen geven het breekpunt door"


# ── 4. De studielijst, echt gerenderd ──────────────────────────────────
#
# De tests hierboven lezen de bron. Deze rendert de pagina, want een veld dat
# app.py berekent is niet geleverd tot het sjabloon het toont.

import json

import pytest
from app import Job, Site, User, app, db
from werkzeug.security import generate_password_hash

_JOB = "job-split-night"

#: Een nacht die MILD leest over het geheel en SEVERE in het diagnostische
#: deel — precies de casus waarop het gemiddelde de diagnose verborg.
_RESULTS = {
    "owner_username": "alice",
    "patient_info": {"patient_name": "SplitStudie", "patient_id": "S-2"},
    "meta": {"duration_min": 480, "eeg_channel": "C4-M1"},
    "sleep_statistics": {"stats": {"TST": 332, "SE": 80}},
    "pneumo": {
        "respiratory": {"summary": {
            "ahi_total": 13.7, "oahi": 7.8, "central_index": 5.2,
            "severity": "Mild",
        }},
        "split_night": {
            "detected": True,
            "breakpoint_s": 8100.0,
            "method": "flow_amplitude+spo2_baseline",
            "segments": {
                "diagnostic": {"sleep_h": 0.85, "ahi": 83.5,
                               "ahi_incl_uncertain": 83.5,
                               "reliable": True, "uncertain_fraction": 0.0},
                "therapeutic": {"sleep_h": 4.68, "ahi": 1.1,
                                "ahi_incl_uncertain": 1.1,
                                "reliable": True, "uncertain_fraction": 0.0},
            },
        },
    },
}


@pytest.fixture()
def split_env(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    prev = app.config["UPLOAD_FOLDER"]
    app.config["UPLOAD_FOLDER"] = str(upload_dir)
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    os.environ["YASAFLASKIFIED_JOB_ACCESS_STRICT"] = "0"

    with app.app_context():
        db.drop_all()
        db.create_all()
        site = Site(name="A")
        db.session.add(site)
        db.session.commit()
        user = User(username="alice",
                    password=generate_password_hash("pw", method="pbkdf2:sha256"),
                    role="user", site_id=site.id)
        db.session.add(user)
        db.session.commit()
        db.session.add(Job(job_id=_JOB, owner_id=user.id, owner_username="alice",
                           site_id=site.id, filename="a.bdf", status="done"))
        db.session.commit()
        with open(os.path.join(str(upload_dir), f"{_JOB}_results.json"), "w") as f:
            json.dump(dict(_RESULTS, site_id=site.id), f)
        yield
        db.session.remove()
        db.drop_all()

    app.config["UPLOAD_FOLDER"] = prev
    os.environ.pop("YASAFLASKIFIED_JOB_ACCESS_STRICT", None)


def _login(c):
    return c.post("/login", data={"username": "alice", "password": "pw"})


def test_de_lijst_toont_beide_helften(split_env):
    with app.test_client() as c:
        _login(c)
        html = c.get("/dashboard").data.decode()
    assert "83.5" in html, "het diagnostische deel staat niet in de lijst"
    assert "1.1" in html, "de waarde onder CPAP staat niet in de lijst"


def test_het_ernstfilter_volgt_het_getoonde_deel(split_env):
    """De balk toont severe (83,5). Zou `data-sev` op de hele nacht blijven
    staan, dan filtert 'severe' deze studie weg terwijl ze rood oplicht."""
    with app.test_client() as c:
        _login(c)
        html = c.get("/dashboard").data.decode()
    assert 'data-sev="severe"' in html, html[:0] or "data-sev volgt de hele nacht"
    assert 'data-sev="mild"' not in html
