"""De route zelf: wie mag erbij, en wat gebeurt er zonder signalen.

De rolpoort is de kern. Deze weergave toont ruwe patiëntsignalen om de
SCORING te beoordelen; dat is iets anders dan een uitslag lezen. Een
site-manager of technicus met toegang tot de job heeft daarmee nog geen
reden om de EDF-curves te zien, dus `job_access_required` alleen is hier
niet genoeg.
"""
import json
import os
import sys
from pathlib import Path

import pytest
from app import Site, User, app, db
from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

JOB = "reviewjob"


@pytest.fixture()
def env():
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    up = app.config["UPLOAD_FOLDER"]
    os.makedirs(up, exist_ok=True)
    with open(os.path.join(up, f"{JOB}_results.json"), "w") as f:
        json.dump({
            "owner_username": "tech",
            "site_id": 1,
            "pneumo": {
                "meta": {"scoring_profile": "aasm_v3_prob",
                         "channels_used": {"flow": "Resp nasal"}},
                "respiratory": {
                    "summary": {"ahi_total": 20.0},
                    "events": [{"type": "hypopnea", "onset_s": 100.0,
                                "duration_s": 20.0, "stage": "N2",
                                "confidence": 0.4}],
                    "rejected_hypopneas": [],
                },
            },
        }, f)
    with app.app_context():
        db.drop_all()
        db.create_all()
        s = Site(name="A")
        db.session.add(s)
        db.session.commit()

        def mk(name, role, site):
            u = User(username=name,
                     password=generate_password_hash("pw", method="pbkdf2:sha256"),
                     role=role, site_id=site)
            db.session.add(u)
            return u

        mk("admin", "admin", None)
        mk("mgr", "site", s.id)
        mk("tech", "user", s.id)
        db.session.commit()
        yield
        db.session.remove()
        db.drop_all()
    try:
        os.remove(os.path.join(up, f"{JOB}_results.json"))
    except OSError:
        pass


def _login(c, who):
    return c.post("/login", data={"username": who, "password": "pw"})


# ──────────────────────────────────────────────────────────────
#  Poorten
# ──────────────────────────────────────────────────────────────

def test_an_admin_reaches_the_page(env):
    with app.test_client() as c:
        _login(c, "admin")
        r = c.get(f"/review/{JOB}")
        assert r.status_code == 200


def test_a_technician_who_owns_the_job_is_still_refused(env):
    """Toegang tot de uitslag is niet hetzelfde als toegang tot de signalen."""
    with app.test_client() as c:
        _login(c, "tech")
        r = c.get(f"/review/{JOB}", follow_redirects=False)
        assert r.status_code in (302, 303), r.status_code
        assert "/review/" not in r.headers.get("Location", "")


def test_a_site_manager_is_refused(env):
    with app.test_client() as c:
        _login(c, "mgr")
        r = c.get(f"/review/{JOB}", follow_redirects=False)
        assert r.status_code in (302, 303)


def test_an_anonymous_visitor_is_sent_to_login(env):
    with app.test_client() as c:
        r = c.get(f"/review/{JOB}", follow_redirects=False)
        assert r.status_code in (301, 302, 303)
        assert "login" in r.headers.get("Location", "").lower()


# ──────────────────────────────────────────────────────────────
#  Gedrag zonder signalen
# ──────────────────────────────────────────────────────────────

def test_a_missing_edf_says_so_instead_of_failing(env):
    """Na anonimisering of opruiming blijven de resultaten en verdwijnt de
    EDF. De pagina hoort dat te melden, niet met een 500 te komen."""
    with app.test_client() as c:
        _login(c, "admin")
        r = c.get(f"/review/{JOB}")
        assert r.status_code == 200
        assert b"EDF" in r.data


def test_an_unknown_job_does_not_render_the_page(env):
    """Zonder JOB_ACCESS_STRICT=1 leidt de toegangslaag om in plaats van 404
    te geven — een bewuste terugval voor jobs van vóór de Job-tabel. Wat hier
    telt is dat er geen weergave verschijnt; welke van de twee het wordt hangt
    af van die instelling, niet van deze route."""
    with app.test_client() as c:
        _login(c, "admin")
        r = c.get("/review/bestaatniet", follow_redirects=False)
        assert r.status_code in (302, 303, 404), r.status_code


def test_the_panel_count_is_clamped(env):
    """?n=9999 mag geen verzoek van een minuut worden."""
    from event_review import MAX_PANELS
    with app.test_client() as c:
        _login(c, "admin")
        r = c.get(f"/review/{JOB}?n=9999")
        assert r.status_code == 200
    assert MAX_PANELS <= 24


def test_a_nonsense_count_does_not_break_the_page(env):
    with app.test_client() as c:
        _login(c, "admin")
        assert c.get(f"/review/{JOB}?n=abc").status_code == 200
