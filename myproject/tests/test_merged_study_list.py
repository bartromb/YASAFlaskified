"""Eén lijst in plaats van twee views op dezelfde studies.

"Geschiedenis" (`/results`) en "Overzicht" (`/dashboard`) toonden dezelfde
studies met net andere kolommen: de geschiedenis had OAHI, centrale index en
het OSAS/CSAS-onderscheid, het overzicht had grade, ODI, PLMi,
signaalkwaliteit, archief en het site-filter. Wie een getal zocht moest weten
in welke van de twee het stond.

Deze tests renderen de echte pagina — een template dat niet rendert, faalt pas
op het scherm van de gebruiker.
"""

import json
import os
import sys

import pytest
from app import Job, Site, User, app, db
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JOB = "job-merged-list"


@pytest.fixture()
def env(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    prev_upload = app.config["UPLOAD_FOLDER"]
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

        # Een afgeronde studie met de getallen uit beide oude views.
        with open(os.path.join(str(upload_dir), f"{JOB}_results.json"), "w") as f:
            json.dump({
                "owner_username": "alice", "site_id": site.id,
                "patient_info": {"patient_name": "Studie", "patient_id": "S-1"},
                "meta": {"duration_min": 480, "eeg_channel": "C4-M1"},
                "sleep_statistics": {"stats": {"TST": 400, "SE": 88}},
                "pneumo": {"respiratory": {"summary": {
                    "ahi_total": 34.5, "oahi": 12.5, "central_index": 21.0,
                    "severity": "Severe",
                }}},
            }, f)

        yield {"site": site.id}

        db.session.remove()
        db.drop_all()

    app.config["UPLOAD_FOLDER"] = prev_upload
    os.environ.pop("YASAFLASKIFIED_JOB_ACCESS_STRICT", None)


def _login(client):
    return client.post("/login", data={"username": "alice", "password": "pw"})


def test_the_history_url_still_works(env):
    """Er staan bladwijzers naar /results en de sneltoets `g h` gaat erheen."""
    with app.test_client() as c:
        _login(c)
        resp = c.get("/results")
    assert resp.status_code in (301, 302)
    assert "dashboard" in resp.headers.get("Location", "")


def test_the_one_list_renders(env):
    with app.test_client() as c:
        _login(c)
        resp = c.get("/dashboard")
    assert resp.status_code == 200
    assert b"Studie" in resp.data


def test_the_columns_from_both_old_views_are_in_the_one_list(env):
    """De kolommen die alleen in de geschiedenis stonden, horen er nu ook bij."""
    with app.test_client() as c:
        _login(c)
        html = c.get("/dashboard").data.decode()
    assert "34.5" in html, "AHI (stond in beide)"
    assert "12.5" in html, "OAHI (stond alleen in de geschiedenis)"
    assert "CSAS" in html, "OSAS/CSAS (stond alleen in de geschiedenis)"


def test_the_navigation_offers_one_entry_not_two(env):
    """Twee knoppen naar dezelfde lijst is geen keuze maar een raadsel."""
    with app.test_client() as c:
        _login(c)
        html = c.get("/dashboard").data.decode()
    assert html.count('href="/dashboard"') == 1, "meer dan één ingang naar de lijst"
