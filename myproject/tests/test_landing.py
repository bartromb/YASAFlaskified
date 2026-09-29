"""
tests/test_landing.py — de tegelpagina van slaapkliniek.be (v0.38.7).

Wat hier stil kan rotten:
  1. De host-schakelaar: op slaapkliniek.be hoort een verwijzer de tegels te
     zien, op sleepai.be hoort een onderzoeker de productpagina met login te
     zien. Allebei geven HTTP 200, dus alleen de inhoud onderscheidt ze.
  2. De ingelogde gebruiker mag geen extra klik verliezen: "/" moet meteen
     naar /analyse, en /analyse moet de rolverdeling van de oude index houden.
  3. `next` na login volgde vroeger elke URL (open redirect); dat mag alleen
     nog een intern pad zijn.
  4. Een vertaling die in één taal ontbreekt valt stil terug op Engels.

De testclient bewaart cookies per host: sessie én verzoek dragen daarom
dezelfde base_url, anders verdwijnt de taal (en de login) tussen de twee.
"""
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from app import LANDING_HOSTS, VERWIJZERS_URL, User, _safe_next, app, db
from i18n import TRANSLATIONS
from werkzeug.security import generate_password_hash

LANGS = ("nl", "fr", "en", "de")
LANDING_HOST = sorted(LANDING_HOSTS)[0]          # slaapkliniek.be
OTHER_HOST = "sleepai.be"


@pytest.fixture(autouse=True)
def _db():
    """Lege gebruikerstabel per test (conftest wijst de DB naar een tmp-sqlite)."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app.test_client()


def _url(host):
    return f"http://{host}"


def _get(client, path, host, lang="nl"):
    with client.session_transaction(base_url=_url(host)) as sess:
        sess["lang"] = lang
    return client.get(path, base_url=_url(host))


def _make_user(name, role="user", password="x"):
    with app.app_context():
        u = User(username=name, password=generate_password_hash(password), role=role)
        db.session.add(u)
        db.session.commit()
        return u.id


def _login_as(client, role="user", host=LANDING_HOST):
    """Log in zoals de app het doet: POST /login met echte credentials (per client)."""
    _make_user(f"landing-test-{role}", role, "Geheim-123")
    resp = client.post("/login", data={"username": f"landing-test-{role}", "password": "Geheim-123"},
                       base_url=_url(host))
    assert resp.status_code == 302, resp.status_code


# ── 1. host-schakelaar ────────────────────────────────────────────────────────
def test_root_on_landing_host_shows_tiles(client):
    html = _get(client, "/", LANDING_HOST).get_data(as_text=True)
    assert 'id="tile-refer"' in html and 'id="tile-analyse"' in html
    assert f'href="{VERWIJZERS_URL}/nl/"' in html, "verwijzerstegel moet naar VERWIJZERS_URL/<taal>/ linken"
    assert 'name="password"' not in html, "de tegelpagina draagt geen loginformulier"


def test_root_on_other_host_keeps_product_page(client):
    html = _get(client, "/", OTHER_HOST).get_data(as_text=True)
    assert 'name="password"' in html, "sleepai.be: productpagina met ingebedde login zoals vroeger"
    assert 'id="tile-refer"' not in html


def test_www_host_counts_as_landing_host():
    assert "www.slaapkliniek.be" in LANDING_HOSTS


def test_start_shows_landing_on_any_host(client):
    for host in (LANDING_HOST, OTHER_HOST):
        html = _get(client, "/start", host).get_data(as_text=True)
        assert 'id="tile-refer"' in html, host


@pytest.mark.parametrize("lang", LANGS)
def test_tile_language_follows_session(client, lang):
    html = _get(client, "/", LANDING_HOST, lang=lang).get_data(as_text=True)
    assert f'href="{VERWIJZERS_URL}/{lang}/"' in html
    assert TRANSLATIONS["landing_refer_title"][lang] in html


def test_heading_comes_from_site_config_not_code(client, monkeypatch):
    """Geen instellingsnaam in de code: de kop is site.name uit config.json, anders neutraal."""
    import app as appmod
    monkeypatch.setitem(appmod.config, "site", {"name": "Testcentrum Slaap"})
    html = _get(client, "/", LANDING_HOST).get_data(as_text=True)
    assert "<h1>Testcentrum Slaap</h1>" in html
    monkeypatch.setitem(appmod.config, "site", {})
    html = _get(client, "/", LANDING_HOST).get_data(as_text=True)
    assert f"<h1>{TRANSLATIONS['landing_title']['nl']}</h1>" in html


def test_landing_has_no_external_scripts_or_fonts(client):
    html = _get(client, "/", LANDING_HOST).get_data(as_text=True)
    assert "<script" not in html
    assert "fonts.googleapis" not in html and "cdn.jsdelivr" not in html


def test_landing_disclaimer_is_the_report_disclaimer(client):
    html = _get(client, "/", LANDING_HOST, lang="nl").get_data(as_text=True)
    assert TRANSLATIONS["disc_header"]["nl"] in html


# ── 2. ingelogd: geen extra klik, rolverdeling behouden ───────────────────────
def test_logged_in_root_redirects_to_analyse(client):
    _login_as(client, "user")
    resp = client.get("/", base_url=_url(LANDING_HOST))
    assert resp.status_code == 302 and urlparse(resp.headers["Location"]).path == "/analyse"


def test_analyse_requires_login(client):
    resp = client.get("/analyse", base_url=_url(LANDING_HOST))
    assert resp.status_code == 302 and "/login" in resp.headers["Location"]
    assert "next=" in resp.headers["Location"]


def test_login_get_on_landing_host_renders_form(client):
    html = _get(client, "/login?next=/analyse", LANDING_HOST).get_data(as_text=True)
    assert 'name="password"' in html


def test_analyse_user_gets_upload_admin_gets_dashboard():
    with app.test_client() as c:
        _login_as(c, "user")
        resp = c.get("/analyse", base_url=_url(LANDING_HOST))
        assert resp.status_code == 200 and "upload" in resp.get_data(as_text=True).lower()
    with app.test_client() as c:
        _login_as(c, "admin")
        resp = c.get("/analyse", base_url=_url(LANDING_HOST))
        assert resp.status_code == 302 and urlparse(resp.headers["Location"]).path == "/dashboard", (
            resp.status_code, re.findall(r"landing-test-\w+", resp.get_data(as_text=True))[:3])


def test_logout_goes_to_root(client):
    _login_as(client, "user")
    resp = client.get("/logout", base_url=_url(LANDING_HOST))
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/", resp.headers["Location"]


# ── 3. veilige next ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("bad", ["//evil.example/x", "https://evil.example", "/\\evil.example", "", None, "evil"])
def test_unsafe_next_is_dropped(bad):
    assert _safe_next(bad) is None


def test_internal_next_is_kept():
    assert _safe_next("/analyse?x=1") == "/analyse?x=1"


def test_login_post_ignores_external_next(client):
    _make_user("landing-next", "user", "Geheim-123")
    resp = client.post("/login?next=//evil.example/",
                       data={"username": "landing-next", "password": "Geheim-123"},
                       base_url=_url(LANDING_HOST))
    assert resp.status_code == 302
    assert "evil" not in resp.headers["Location"]
    assert urlparse(resp.headers["Location"]).path == "/analyse"


def test_login_post_follows_internal_next(client):
    _make_user("landing-next2", "user", "Geheim-123")
    resp = client.post("/login?next=/dashboard",
                       data={"username": "landing-next2", "password": "Geheim-123"},
                       base_url=_url(LANDING_HOST))
    assert resp.status_code == 302 and urlparse(resp.headers["Location"]).path == "/dashboard"


# ── 4. vertalingen compleet en verschillend ───────────────────────────────────
def test_landing_keys_exist_in_all_languages():
    keys = [k for k in TRANSLATIONS if k.startswith("landing_")]
    assert len(keys) >= 10
    for k in keys:
        assert set(LANGS) <= set(TRANSLATIONS[k]), f"{k} mist een taal"
        if k != "landing_contact":                     # "Contact" is in drie talen hetzelfde woord
            assert len({TRANSLATIONS[k][lang] for lang in LANGS}) >= 3, f"{k}: vertalingen zijn kopieën"


def test_no_dead_links_to_old_root_in_app_templates():
    """In-app 'terug'-links horen naar /analyse, niet naar '/' (dat is nu de tegelpagina)."""
    tpl = Path(__file__).resolve().parents[1] / "templates"
    for name in ("channel_select.html", "job_status.html", "change_password.html", "base.html"):
        html = (tpl / name).read_text()
        assert not re.search(r'href="/"', html), f"{name} linkt nog naar '/'"
