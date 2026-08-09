"""
tests/test_job_access.py — DB-backed toegangscontrole op job-routes (IDOR).

Autorisatie hing aan JSON-bestanden op schijf, waarbij een stille
`except Exception: pass` None teruggaf; acht routes misten de check
volledig. Nu is de Job-tabel de bron en draagt élke <job_id>-route
@job_access_required.

Regel (bevestigd door Bart, 2026-07-28):
    admin → toegang
    eigenaar (owner_username) → toegang, ook cross-site
    zelfde site (site_id niet None) → toegang
    anders → geen toegang

Run:
    pytest myproject/tests/test_job_access.py -v
"""
import json
import os

import pytest
from app import Job, Site, User, app, db
from flask_login import login_user
from werkzeug.security import generate_password_hash

# Alle 30 job-routes, met een concrete URL per route. Blijft bewust
# handmatig: de meta-test onderaan bewaakt dat er niets bijkomt.
JOB_ROUTES = [
    ("GET", "/channel-select/{jid}"),
    ("GET", "/status/{jid}"),
    ("GET", "/api/status/{jid}"),
    ("GET", "/results/{jid}"),
    # Visuele eventcontrole. Staat hier omdat de route een <job_id> draagt;
    # daarnaast geldt requires_role("admin") — toegang tot de uitslag geeft
    # nog geen toegang tot de ruwe signalen. Zie test_event_review_route.py.
    ("GET", "/review/{jid}"),
    # Oordeel van de beoordelaar. Schrijft naar {job}_review.json en raakt de
    # AHI niet; corrigeren gebeurt in de PSG Editor.
    ("POST", "/review/{jid}/verdict"),
    ("GET", "/results/{jid}/pdf"),
    ("GET", "/results/{jid}/excel"),
    ("GET", "/results/{jid}/psg"),
    ("POST", "/results/{jid}/delete"),
    ("GET", "/results/{jid}/reanalyze"),
    ("GET", "/results/{jid}/edfplus"),
    ("GET", "/api/edfplus/{jid}/status"),
    ("GET", "/api/results/{jid}/conclusion"),
    ("POST", "/api/results/{jid}/conclusion"),
    ("GET", "/results/{jid}/edit"),
    ("GET", "/api/results/{jid}/report"),
    ("POST", "/api/results/{jid}/report"),
    ("GET", "/api/results/{jid}/pneumo"),
    ("GET", "/api/results/{jid}/channels"),
    ("GET", "/api/results/{jid}"),
    ("GET", "/results/{jid}/fhir"),
    ("GET", "/score/{jid}"),
    ("GET", "/score_v12/{jid}"),
    ("POST", "/api/scoring/{jid}/save"),
    ("GET", "/api/scoring/{jid}/status"),
    ("GET", "/api/edf/{jid}/info"),
    ("GET", "/api/edf/{jid}/epoch/0"),
    ("GET", "/api/edf/{jid}/epochs/0/1"),
    ("GET", "/api/edf/{jid}/events/0"),
    ("GET", "/api/edf/{jid}/events/all"),
    ("POST", "/api/edf/{jid}/events/toggle"),
    # v0.18.3: herschrijft de EDF-header van andermans opname als hij niet
    # afgeschermd is — dat is de PHI zelf, niet alleen een resultaat.
    ("POST", "/anonymize/{jid}"),
]

JOB_A = "job-of-alice"


@pytest.fixture()
def env(tmp_path):
    """Twee sites, twee users + admin, en één studie van alice."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    prev_upload = app.config["UPLOAD_FOLDER"]
    prev_strict = app.config.get("_TEST_STRICT")
    app.config["UPLOAD_FOLDER"] = str(upload_dir)
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    os.environ["YASAFLASKIFIED_JOB_ACCESS_STRICT"] = "0"

    with app.app_context():
        db.drop_all()
        db.create_all()

        site_a, site_b = Site(name="A"), Site(name="B")
        db.session.add_all([site_a, site_b])
        db.session.commit()

        def _mk(username, role, site_id):
            u = User(username=username,
                     password=generate_password_hash("pw", method="pbkdf2:sha256"),
                     role=role, site_id=site_id)
            db.session.add(u)
            return u

        alice = _mk("alice", "user", site_a.id)     # eigenaar
        bob = _mk("bob", "user", site_b.id)         # andere site
        carol = _mk("carol", "user", site_a.id)     # zelfde site als alice
        admin = _mk("admin", "admin", None)
        db.session.commit()

        db.session.add(Job(job_id=JOB_A, owner_id=alice.id, owner_username="alice",
                           site_id=site_a.id, filename="a.edf", status="submitted"))
        db.session.commit()

        results_path = os.path.join(str(upload_dir), f"{JOB_A}_results.json")
        with open(results_path, "w") as f:
            json.dump({"owner_username": "alice", "site_id": site_a.id,
                       "patient_info": {}, "conclusion": "origineel"}, f)

        yield {
            "upload_dir": str(upload_dir),
            "results_path": results_path,
            "site_a": site_a.id,
            "site_b": site_b.id,
            "users": {"alice": alice, "bob": bob, "carol": carol, "admin": admin},
        }

        db.session.remove()
        db.drop_all()

    app.config["UPLOAD_FOLDER"] = prev_upload
    app.config["_TEST_STRICT"] = prev_strict
    os.environ.pop("YASAFLASKIFIED_JOB_ACCESS_STRICT", None)


def _login(client, username):
    return client.post("/login", data={"username": username, "password": "pw"},
                       follow_redirects=False)


def _request(client, method, url):
    return client.post(url) if method == "POST" else client.get(url)


def _assert_denied(resp, what):
    """
    Geweigerd betekent niet overal 403: de errorhandler geeft JSON-403 voor
    /api/-paden en flash+redirect naar het dashboard voor HTML-routes. Beide
    zijn "de view is niet uitgevoerd"; dat is wat we hier vastleggen.
    """
    if resp.status_code == 403:
        return
    location = resp.headers.get("Location", "")
    assert resp.status_code in (301, 302) and "dashboard" in location, (
        f"{what} gaf {resp.status_code} (Location={location!r}) voor een user "
        f"van een andere site — verwacht 403 of een redirect naar /dashboard"
    )


# ══════════════════════════════════════════════════════════════
#  1. Andere site → geweigerd op élke route
# ══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("method,template", JOB_ROUTES,
                         ids=[t for _, t in JOB_ROUTES])
def test_other_site_user_is_denied_on_every_job_route(env, method, template):
    with app.test_client() as client:
        _login(client, "bob")
        resp = _request(client, method, template.format(jid=JOB_A))

    _assert_denied(resp, f"{method} {template}")


# ══════════════════════════════════════════════════════════════
#  2. Geen regressie voor wie wél toegang heeft
# ══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("username", ["alice", "carol", "admin"])
def test_authorised_users_are_not_blocked(env, username):
    """
    Eigenaar, zelfde site en admin komen voorbij de toegangscontrole.

    Getest op /api/results/<job_id>: die geeft de opgeslagen JSON terug,
    zonder de zware rapporttemplates die volledige resultaatdata eisen.
    """
    with app.test_client() as client:
        _login(client, username)
        resp = client.get(f"/api/results/{JOB_A}")

    assert resp.status_code == 200, f"{username} werd onterecht geweigerd"
    assert resp.get_json()["owner_username"] == "alice"


def test_owner_keeps_access_after_moving_site(env):
    """
    Bevestigde regel: de eigenaar behoudt toegang, ook als de job op een
    andere site staat dan waar de user nu zit.
    """
    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        alice.site_id = env["site_b"]
        db.session.commit()

    with app.test_client() as client:
        _login(client, "alice")
        resp = client.get(f"/api/results/{JOB_A}")
    assert resp.status_code == 200


def test_not_logged_in_redirects_to_login(env):
    with app.test_client() as client:
        resp = client.get(f"/results/{JOB_A}")
    assert resp.status_code in (301, 302)
    assert "/login" in resp.headers.get("Location", "")


# ══════════════════════════════════════════════════════════════
#  3. Geen schrijfactie door een niet-gemachtigde user
# ══════════════════════════════════════════════════════════════

def test_denied_post_leaves_results_json_byte_identical(env):
    before = open(env["results_path"], "rb").read()

    with app.test_client() as client:
        _login(client, "bob")
        resp = client.post(f"/api/results/{JOB_A}/conclusion",
                           json={"conclusion": "INGEBROKEN"})

    after = open(env["results_path"], "rb").read()
    assert resp.status_code == 403
    assert before == after, "_results.json is gewijzigd door een geweigerde POST"


def test_denied_scoring_post_leaves_results_json_byte_identical(env):
    before = open(env["results_path"], "rb").read()

    with app.test_client() as client:
        _login(client, "bob")
        resp = client.post(f"/api/scoring/{JOB_A}/save",
                           json={"hypnogram": ["W", "N1"]})

    assert resp.status_code == 403
    assert open(env["results_path"], "rb").read() == before


# ══════════════════════════════════════════════════════════════
#  4. JOB_ACCESS_STRICT
# ══════════════════════════════════════════════════════════════

def _write_legacy(env, job_id, owner="alice", site=None):
    """Legacy studie: wel JSON op schijf, geen Job-rij."""
    site = env["site_a"] if site is None else site
    with open(os.path.join(env["upload_dir"], f"{job_id}_results.json"), "w") as f:
        json.dump({"owner_username": owner, "site_id": site}, f)


def test_unknown_job_is_404_when_strict(env):
    os.environ["YASAFLASKIFIED_JOB_ACCESS_STRICT"] = "1"
    try:
        with app.test_client() as client:
            _login(client, "alice")
            resp = client.get("/api/results/does-not-exist")
        assert resp.status_code == 404
    finally:
        os.environ["YASAFLASKIFIED_JOB_ACCESS_STRICT"] = "0"


def test_legacy_job_without_row_falls_back_when_not_strict(env, caplog):
    """
    Overgang: geen Job-rij maar wél JSON op schijf → toegang volgens de
    JSON, mét waarschuwing zodat de resterende legacy jobs zichtbaar zijn.
    """
    legacy = "legacy-job"
    _write_legacy(env, legacy)

    with caplog.at_level("WARNING"):
        with app.test_client() as client:
            _login(client, "alice")
            resp = client.get(f"/api/results/{legacy}")

    assert resp.status_code == 200
    assert any("job access fallback" in r.getMessage() for r in caplog.records), \
        "fallback moet een 'job access fallback'-waarschuwing loggen"


def test_legacy_job_fallback_still_denies_other_site(env):
    """De fallback gebruikt dezelfde regel — geen gat in de overgang."""
    legacy = "legacy-job-2"
    _write_legacy(env, legacy)

    with app.test_client() as client:
        _login(client, "bob")
        resp = client.get(f"/api/results/{legacy}")
    assert resp.status_code == 403


def test_legacy_job_without_row_is_404_when_strict(env):
    legacy = "legacy-job-3"
    _write_legacy(env, legacy)

    os.environ["YASAFLASKIFIED_JOB_ACCESS_STRICT"] = "1"
    try:
        with app.test_client() as client:
            _login(client, "alice")
            resp = client.get(f"/api/results/{legacy}")
        assert resp.status_code == 404
    finally:
        os.environ["YASAFLASKIFIED_JOB_ACCESS_STRICT"] = "0"


def test_backfilled_row_stops_the_fallback_warning(env, caplog):
    """Na de backfill mag er geen fallback meer nodig zijn."""
    legacy = "legacy-job-4"
    _write_legacy(env, legacy)

    from backfill_jobs import backfill
    with app.app_context():
        backfill(upload_folder=env["upload_dir"], verbose=False)

    with caplog.at_level("WARNING"):
        with app.test_client() as client:
            _login(client, "alice")
            resp = client.get(f"/api/results/{legacy}")

    assert resp.status_code == 200
    assert not any("job access fallback" in r.getMessage() for r in caplog.records), \
        "na de backfill mag de JSON-fallback niet meer aangesproken worden"


# ══════════════════════════════════════════════════════════════
#  5. Regressie: de upload-flow zelf mag niet breken
# ══════════════════════════════════════════════════════════════

def test_owner_has_access_right_after_parse_before_any_json_exists(env):
    """
    Na parse_file bestaat alleen de Job-rij: de config-JSON wordt pas bij
    /analyze geschreven. /channel-select/<job_id> zit daartussen en draagt
    nu de decorator, dus de eigenaar moet op dat moment al door de
    toegangscontrole komen — anders breekt elke normale upload.

    (De route zelf leest Redis; hier testen we de toegangsbeslissing.)
    """
    from app import _check_job_access, _register_job

    fresh = "freshly-parsed-job"
    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        bob = User.query.filter_by(username="bob").first()
        _register_job(fresh, alice, filename="new.edf", status="parsed")

        assert not os.path.exists(
            os.path.join(env["upload_dir"], f"{fresh}_config.json")
        ), "voorwaarde: er is nog geen JSON op schijf"

        with app.test_request_context():
            login_user(alice)
            assert _check_job_access(fresh) is True, \
                "eigenaar moet na parse_file al toegang hebben"

        with app.test_request_context():
            login_user(bob)
            assert _check_job_access(fresh) is False, \
                "andere site mag ook een net-geparste job niet openen"


# ══════════════════════════════════════════════════════════════
#  6. Meta-test — bewaakt nieuwe routes
# ══════════════════════════════════════════════════════════════

def test_every_job_id_route_carries_the_decorator():
    """
    Faalt automatisch zodra iemand een <job_id>-route toevoegt zonder
    @job_access_required. Dit is de vangrail, niet de losse tests hierboven.
    """
    unprotected = []
    for rule in app.url_map.iter_rules():
        if "<job_id>" not in str(rule):
            continue
        view = app.view_functions[rule.endpoint]
        if not getattr(view, "_job_access", False):
            unprotected.append(f"{rule.endpoint} ({rule})")

    assert not unprotected, (
        "job-routes zonder @job_access_required:\n  " + "\n  ".join(unprotected)
    )


def test_route_list_in_this_file_is_complete():
    """De lijst hierboven moet alle job-routes dekken, anders test hij te weinig."""
    in_app = {str(r) for r in app.url_map.iter_rules() if "<job_id>" in str(r)}
    covered = set()
    for _, template in JOB_ROUTES:
        # /api/edf/{jid}/epoch/0 → /api/edf/<job_id>/epoch/<int:epoch_idx>
        covered.add(template.format(jid="<job_id>"))

    missing = set()
    for rule in in_app:
        normalised = rule
        for conv in ("<int:epoch_idx>", "<int:start>", "<int:end>"):
            normalised = normalised.replace(conv, "N")
        hit = any(
            c.replace("/0/1", "/N/N").replace("/0", "/N") == normalised
            for c in covered
        )
        if not hit:
            missing.add(rule)

    assert not missing, f"niet gedekt door JOB_ROUTES: {sorted(missing)}"
