"""Het overzicht (/dashboard) per 50, zonder bij elke weergave alle resultaten in te lezen.

Aanleiding (07-11-2026): 269 studies op slaapkliniek.be, samen 1,8 GB results.json (mediaan
6,5 MB); de lijst parste ze bij ELKE weergave allemaal (± 15 s), alleen om site, eigenaar en
een tiental getallen te kennen. Nu: per studie een klein overzichtsbestand `<job>_dash.json`,
vernieuwd zodra results.json verandert, en paginering per 50 met zoeken over alle studies.
"""
import json
import os
import re

import pytest
from app import Site, User, app, db
from werkzeug.security import generate_password_hash


def _schrijf(upload, job, site_id, owner, naam, ahi, mtime):
    p = os.path.join(upload, f"{job}_results.json")
    with open(p, "w") as f:
        json.dump({"owner_username": owner, "site_id": site_id,
                   "patient_info": {"patient_name": naam, "patient_id": f"ID-{job}"},
                   "meta": {"duration_min": 480}, "sleep_statistics": {"stats": {"TST": 400, "SE": 85}},
                   "pneumo": {"respiratory": {"summary": {"ahi_total": ahi, "severity": "x"}},
                              "padding": "x" * 2000}}, f)
    os.utime(p, (mtime, mtime))
    return p


@pytest.fixture()
def env(tmp_path):
    upload = tmp_path / "uploads"; upload.mkdir()
    prev = app.config["UPLOAD_FOLDER"]
    app.config.update(UPLOAD_FOLDER=str(upload), WTF_CSRF_ENABLED=False, TESTING=True)
    os.environ["YASAFLASKIFIED_JOB_ACCESS_STRICT"] = "0"
    with app.app_context():
        db.drop_all(); db.create_all()
        a, b = Site(name="A"), Site(name="B"); db.session.add_all([a, b]); db.session.commit()
        pw = generate_password_hash("pw", method="pbkdf2:sha256")
        db.session.add_all([User(username="root", password=pw, role="admin"),
                            User(username="sitea", password=pw, role="site", site_id=a.id)])
        db.session.commit()
        # 120 studies: 100 op site A, 20 op site B; nieuwste eerst = hoogste i
        for i in range(120):
            site = a.id if i < 100 else b.id
            _schrijf(str(upload), f"job{i:03d}", site, "x", f"Patient{i:03d}", 2.0 if i % 2 else 40.0, 1_700_000_000 + i)
        yield {"upload": str(upload), "a": a.id, "b": b.id}
        db.session.remove(); db.drop_all()
    app.config["UPLOAD_FOLDER"] = prev
    os.environ.pop("YASAFLASKIFIED_JOB_ACCESS_STRICT", None)


def _rijen(html):
    return re.findall(r'data-id="(id-job\d+)"', html)


def _login(c, wie):
    c.post("/login", data={"username": wie, "password": "pw"})


def test_vijftig_per_pagina_nieuwste_eerst(env):
    with app.test_client() as c:
        _login(c, "root")
        p1 = c.get("/dashboard").get_data(as_text=True)
        assert len(_rijen(p1)) == 50 and _rijen(p1)[0] == "id-job119"
        assert "p=2" in p1 and "p=3" in p1                       # paginalinks
        assert re.search(r">\s*120\s*<", p1)                      # totaal = alle studies, niet de pagina
        p3 = c.get("/dashboard?p=3").get_data(as_text=True)
        assert len(_rijen(p3)) == 20 and _rijen(p3)[-1] == "id-job000"
        assert len(_rijen(c.get("/dashboard?p=99").get_data(as_text=True))) == 20   # te ver = laatste pagina


def test_zoeken_over_alle_paginas(env):
    with app.test_client() as c:
        _login(c, "root")
        html = c.get("/dashboard?q=patient005").get_data(as_text=True)
        assert _rijen(html) == ["id-job005"]
        assert 'value="patient005"' in html                       # zoekterm blijft staan


def test_site_beheerder_ziet_alleen_eigen_site_ook_met_cache(env):
    with app.test_client() as c:
        _login(c, "sitea")
        c.get("/dashboard")                                       # bouwt de cache
        alle = []
        for p in (1, 2, 3):
            alle += _rijen(c.get(f"/dashboard?p={p}").get_data(as_text=True))
        assert len(set(alle)) == 100 and not any(int(j[6:]) >= 100 for j in alle)


def test_overzichtsbestand_vervangt_het_inlezen_en_volgt_wijzigingen(env, monkeypatch):
    with app.test_client() as c:
        _login(c, "root")
        c.get("/dashboard")
        assert os.path.exists(os.path.join(env["upload"], "job119_dash.json"))
        # tweede weergave: geen enkel results.json mag nog volledig ingelezen worden
        import builtins
        echte_open = builtins.open
        gelezen = []

        def tel_open(pad, *a, **kw):
            if str(pad).endswith("_results.json"):
                gelezen.append(pad)
            return echte_open(pad, *a, **kw)
        monkeypatch.setattr(builtins, "open", tel_open)
        assert len(_rijen(c.get("/dashboard").get_data(as_text=True))) == 50
        assert gelezen == []
        monkeypatch.setattr(builtins, "open", echte_open)
        # results.json herschreven (herrekening) → het overzicht volgt
        _schrijf(env["upload"], "job119", env["a"], "x", "Hernoemd", 99.0, 1_800_000_000)
        assert "hernoemd" in c.get("/dashboard").get_data(as_text=True).lower()


def test_archief_telt_en_pagineert_apart(env):
    for i in (119, 118):
        open(os.path.join(env["upload"], f"job{i}.archived"), "w").close()
    with app.test_client() as c:
        _login(c, "root")
        html = c.get("/dashboard").get_data(as_text=True)
        assert "id-job119" not in _rijen(html) and _rijen(html)[0] == "id-job117"
        assert _rijen(c.get("/dashboard?archived=1").get_data(as_text=True)) == ["id-job119", "id-job118"]


def test_osa_teller_telt_alle_studies(env):
    """De statistiekbalk telde de rijen op het scherm; met paginering moet hij over alles gaan."""
    with app.test_client() as c:
        _login(c, "root")
        html = c.get("/dashboard").get_data(as_text=True)
        assert re.search(r">\s*60\s*<", html)                     # 60 van de 120 hebben AHI 40
