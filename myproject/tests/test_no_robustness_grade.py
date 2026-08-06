"""De A/B/C-robuustheidsgraad is weg, en hoort weg te blijven.

Waarom hij weg is: de graad telde hoeveel van `strict`, `standard` en
`sensitive` dezelfde ernstklasse gaven, en veronderstelde daarmee dat die drie
een ordening vormen — strict <= standard <= sensitive. Gemeten op PSG-IPA met
een manueel hypnogram geeft `sensitive` op 5 van de 5 opnames MINDER events dan
`standard`, en `strict` op 2 van de 5 MEER (SN2: 17,1 tegen 9,3). De namen
beschrijven de bedoeling, niet het gedrag.

Uit het PDF-rapport verdween hij al in v0.15.0. Hij bleef staan in de
studielijst en in de FHIR-export — de twee plekken waar een lezer hem niet kan
wegen. Een gekleurd A/B/C-bolletje leest als een kwaliteitsoordeel.

psgscoring blijft het veld gewoon berekenen. Deze tests gaan er alleen over dat
YASAFlaskified het niet meer TOONT. Het AHI-interval zelf blijft wel: dat is
min/max van drie getallen en veronderstelt geen volgorde.
"""

import json
import os
import sys

import pytest
from app import Job, Site, User, app, db
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JOB = "job-abc-removed"

#: Een resultaat dat de graad WEL bevat — zoals psgscoring hem nog steeds
#: aanlevert. Zonder dat zouden deze tests ook slagen als het veld er niet was.
RESULTS = {
    "owner_username": "alice",
    "patient_info": {"patient_name": "Studie", "patient_id": "S-1"},
    "meta": {"duration_min": 480, "eeg_channel": "C4-M1"},
    "sleep_statistics": {"stats": {"TST": 400, "SE": 88}},
    "pneumo": {
        "respiratory": {"summary": {
            "ahi_total": 34.5, "oahi": 12.5, "central_index": 2.0,
            "severity": "Severe",
        }},
        "ahi_interval": {
            "interval": [21.3, 38.7],
            "robustness_grade": "C",
            "robustness_label": "Uncertain — profiles discordant",
            "strict": {"ahi": 38.7}, "standard": {"ahi": 34.5},
            "sensitive": {"ahi": 21.3},
        },
    },
}


@pytest.fixture()
def env(tmp_path):
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
        db.session.add(Job(job_id=JOB, owner_id=user.id, owner_username="alice",
                           site_id=site.id, filename="a.edf", status="done"))
        db.session.commit()

        payload = dict(RESULTS, site_id=site.id)
        with open(os.path.join(str(upload_dir), f"{JOB}_results.json"), "w") as f:
            json.dump(payload, f)

        yield {"site": site.id, "payload": payload}

        db.session.remove()
        db.drop_all()

    app.config["UPLOAD_FOLDER"] = prev
    os.environ.pop("YASAFLASKIFIED_JOB_ACCESS_STRICT", None)


def _login(c):
    return c.post("/login", data={"username": "alice", "password": "pw"})


# ─────────────────────────────────────────────────────────────
#  De studielijst
# ─────────────────────────────────────────────────────────────

def test_the_study_list_still_renders(env):
    with app.test_client() as c:
        _login(c)
        resp = c.get("/dashboard")
    assert resp.status_code == 200
    assert b"Studie" in resp.data


def test_the_study_list_shows_no_grade_badge(env):
    """De invoer bevat grade "C". Zou de kolom er nog zijn, dan stond hier een
    rode badge."""
    with app.test_client() as c:
        _login(c)
        html = c.get("/dashboard").data.decode()
    assert "grade" not in html.lower(), "de A/B/C-kolom is terug"
    assert "robustness" not in html.lower()


def test_the_numbers_that_should_stay_are_still_there(env):
    """Verwijderen mag niet per ongeluk de buurkolommen meenemen."""
    with app.test_client() as c:
        _login(c)
        html = c.get("/dashboard").data.decode()
    assert "34.5" in html, "AHI"
    assert "12.5" in html, "OAHI"


def test_the_row_data_carries_no_grade_key(env):
    """Niet alleen onzichtbaar in de HTML — ook niet meer in de gegevens, want
    een template dat het veld weer oppikt is één regel werk."""
    import app as app_module
    assert not hasattr(app_module, "_compute_ahi_grade"), (
        "_compute_ahi_grade is terug; dan komt de kolom ook terug")


# ─────────────────────────────────────────────────────────────
#  De FHIR-export
# ─────────────────────────────────────────────────────────────

def _bundle(payload):
    from fhir_export import results_to_fhir
    return json.dumps(results_to_fhir(payload, job_id=JOB))


def test_the_fhir_conclusion_does_not_mention_robustness(env):
    """Een letter die een ontvangend systeem als kwaliteitsoordeel kan lezen,
    mag niet op een niet-bestaande ordening rusten."""
    txt = _bundle(env["payload"])
    assert "robustness" not in txt.lower()


def test_the_fhir_export_keeps_the_ahi_interval(env):
    """Het interval blijft: min/max van drie getallen veronderstelt geen
    volgorde en blijft dus een eerlijke spreidingsmaat."""
    txt = _bundle(env["payload"])
    assert "AHI interval" in txt
    assert "21.3" in txt and "38.7" in txt


def test_the_fhir_export_still_carries_the_ahi_itself(env):
    txt = _bundle(env["payload"])
    assert "34.5" in txt


# ─────────────────────────────────────────────────────────────
#  De vertalingen
# ─────────────────────────────────────────────────────────────

def test_the_translation_keys_are_gone_too(env):
    """Dode vertaalsleutels zijn hoe een verwijderde kolom stilletjes
    terugkeert: het label staat er nog, dus iemand hangt er weer een kolom aan."""
    from i18n import TRANSLATIONS
    assert "grade" not in TRANSLATIONS
    assert "grade_tooltip" not in TRANSLATIONS


def test_the_neighbouring_tooltips_survived(env):
    from i18n import TRANSLATIONS
    for k in ("odi_tooltip", "plmi_tooltip"):
        assert k in TRANSLATIONS, k
        assert set(TRANSLATIONS[k]) >= {"nl", "fr", "en", "de"}, k
