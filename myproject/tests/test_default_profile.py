"""Per-gebruiker voorgeselecteerd scoringsprofiel.

Aanleiding: de slaaptechnici testen profielen naast elkaar. Zonder dit moet
ieder van hen bij elke opname dezelfde dropdown opnieuw goed zetten, en één
vergeten klik maakt een vergelijking stil ongeldig.

Twee dingen die hier fout kunnen gaan en die deze tests afdwingen:

  * de kolom moet op een BESTAANDE database bijkomen zonder dat een gebruiker
    iets merkt — leeg betekent "applicatiestandaard", precies het gedrag van
    voor deze wijziging;
  * een site-manager mag alleen zijn eigen site-gebruikers aanraken, dezelfde
    regel als bij wachtwoord resetten en verwijderen.
"""

import os
import sys

import pytest
from app import Site, User, app, available_profile_choices, db
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def env(tmp_path):
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        a, b = Site(name="A"), Site(name="B")
        db.session.add_all([a, b])
        db.session.commit()

        def mk(name, role, site):
            u = User(username=name,
                     password=generate_password_hash("pw", method="pbkdf2:sha256"),
                     role=role, site_id=site)
            db.session.add(u)
            return u

        admin = mk("admin", "admin", None)
        mgr_a = mk("mgr_a", "site", a.id)
        tech_a = mk("tech_a", "user", a.id)
        tech_b = mk("tech_b", "user", b.id)
        db.session.commit()
        yield {"admin": admin.id, "mgr_a": mgr_a.id,
               "tech_a": tech_a.id, "tech_b": tech_b.id}
        db.session.remove()
        db.drop_all()


def _login(c, who):
    return c.post("/login", data={"username": who, "password": "pw"})


def _set(c, uid, prof):
    return c.post(f"/admin/users/{uid}/profile", data={"default_profile": prof})


# ─────────────────────────────────────────────────────────────
#  Het gedrag zelf
# ─────────────────────────────────────────────────────────────

def test_a_new_column_leaves_existing_users_untouched(env):
    """Leeg = applicatiestandaard. Dat is het gedrag van vóór deze wijziging."""
    with app.app_context():
        assert all(u.default_profile is None for u in User.query.all())


def test_an_admin_can_set_a_profile_per_user(env):
    with app.test_client() as c:
        _login(c, "admin")
        _set(c, env["tech_a"], "aasm_v3_dual")
        _set(c, env["tech_b"], "aasm_v3_prob")
    with app.app_context():
        assert User.query.get(env["tech_a"]).default_profile == "aasm_v3_dual"
        assert User.query.get(env["tech_b"]).default_profile == "aasm_v3_prob"


def test_clearing_it_returns_to_the_application_default(env):
    with app.test_client() as c:
        _login(c, "admin")
        _set(c, env["tech_a"], "aasm_v3_dual")
        _set(c, env["tech_a"], "")
    with app.app_context():
        assert User.query.get(env["tech_a"]).default_profile is None


def test_an_unknown_profile_is_refused(env):
    """Een profiel dat niet bestaat mag niet in de database landen — anders
    valt de dropdown later stil terug op niets."""
    with app.test_client() as c:
        _login(c, "admin")
        _set(c, env["tech_a"], "aasm_v3_dual")
        _set(c, env["tech_a"], "profiel_dat_niet_bestaat")
    with app.app_context():
        assert User.query.get(env["tech_a"]).default_profile == "aasm_v3_dual"


# ─────────────────────────────────────────────────────────────
#  Toegang
# ─────────────────────────────────────────────────────────────

def test_a_site_manager_may_set_it_for_his_own_site(env):
    with app.test_client() as c:
        _login(c, "mgr_a")
        _set(c, env["tech_a"], "aasm_v3_breath")
    with app.app_context():
        assert User.query.get(env["tech_a"]).default_profile == "aasm_v3_breath"


def test_a_site_manager_may_not_reach_another_site(env):
    """Zelfde regel als bij wachtwoord resetten en verwijderen.

    Geweigerd is hier niet per se 403: de errorhandler stuurt HTML-routes met
    een flash naar het dashboard. Beide betekenen "de view is niet
    uitgevoerd"; dat is wat we vastleggen. Zelfde conventie als
    test_job_access._assert_denied.
    """
    with app.test_client() as c:
        _login(c, "mgr_a")
        resp = _set(c, env["tech_b"], "aasm_v3_breath")
    assert resp.status_code == 403 or (
        resp.status_code in (301, 302)
        and "dashboard" in resp.headers.get("Location", ""))
    with app.app_context():
        assert User.query.get(env["tech_b"]).default_profile is None


def test_a_plain_user_may_not_set_it_at_all(env):
    with app.test_client() as c:
        _login(c, "tech_a")
        resp = _set(c, env["tech_a"], "aasm_v3_breath")
    assert resp.status_code in (302, 403)
    with app.app_context():
        assert User.query.get(env["tech_a"]).default_profile is None


# ─────────────────────────────────────────────────────────────
#  De keuzelijst
# ─────────────────────────────────────────────────────────────

def test_the_choices_come_from_the_registry_not_a_hard_coded_list():
    """Een nieuw profiel moet vanzelf verschijnen, een verdwenen profiel
    vanzelf wegvallen."""
    names = [n for n, _ in available_profile_choices()]
    assert "aasm_v3_rec" in names
    assert "aasm_v3_prob" in names, "nieuw profiel ontbreekt in de keuzelijst"


def test_reproduction_profiles_are_not_offered():
    """`mesa_shhs` en `chicago_1999` bestaan om gepubliceerde cijfers te
    reproduceren, niet om patiënten mee te scoren."""
    names = [n for n, _ in available_profile_choices()]
    assert "mesa_shhs" not in names
    assert "chicago_1999" not in names


def test_the_admin_page_renders_the_column(env):
    with app.test_client() as c:
        _login(c, "admin")
        _set(c, env["tech_a"], "aasm_v3_dual")
        html = c.get("/admin/users").data.decode()
    assert "aasm_v3_dual" in html


# ─────────────────────────────────────────────────────────────
#  De dropdown blijft een dropdown
# ─────────────────────────────────────────────────────────────

try:
    from psgscoring.profiles import PROFILES as _REGISTRY
except Exception:                                            # pragma: no cover
    _REGISTRY = {}


def _render_channel_select(user_profile):
    """Render het echte template met een gebruiker die een profiel heeft."""
    import os as _os

    from jinja2 import ChainableUndefined, ChoiceLoader, DictLoader, Environment, FileSystemLoader
    tpl_dir = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "templates")
    env = Environment(
        loader=ChoiceLoader([DictLoader({"base.html": "{% block content %}{% endblock %}"}),
                             FileSystemLoader(tpl_dir)]),
        autoescape=True, undefined=ChainableUndefined)
    env.filters["channel_type_badge"] = lambda ch: ""

    class _U:
        is_authenticated = True
        default_profile = user_profile

    return env.get_template("channel_select.html").render(
        t=lambda k, *a, **kw: k, csrf_token=lambda: "x",
        job_id="j", filename="f.edf", sfreq=256, channels=["C4:A1", "SpO2"],
        best_eeg="C4:A1", pneumo_auto={}, pneumo_channels={},
        # v0.22.0: de template groepeert op FAMILIE, dus de fixture moet die
        # meegeven. Uit de registry zelf en niet hardgecodeerd: een fixture die
        # elk profiel "v3 (2023)" en "clinical" noemt zou de groepering testen
        # die de test zelf verzint in plaats van die van de pagina.
        available_profiles=[
            (n, p.display_name, p.aasm_version, p.family)
            for n, p in _REGISTRY.items()],
        current_user=_U())


def _profile_select(html):
    """Alleen het scoring_profile-menu. De pagina heeft meer keuzemenu's met
    een voorselectie; zonder deze afbakening meet je het verkeerde."""
    import re
    m = re.search(r'<select[^>]*name="scoring_profile".*?</select>', html, re.S)
    assert m, "scoring_profile-menu niet gevonden"
    return m.group(0)


def _selected(html):
    import re
    for tag in re.findall(r"<option[^>]*>", _profile_select(html)):
        if "selected" in tag:
            m = re.search(r'value="([^"]*)"', tag)
            if m:
                return m.group(1)
    return None


def test_the_users_profile_is_preselected():
    assert _selected(_render_channel_select("aasm_v3_dual")) == "aasm_v3_dual"
    assert _selected(_render_channel_select("aasm_v3_prob")) == "aasm_v3_prob"


def test_without_a_user_profile_the_application_default_is_preselected():
    assert _selected(_render_channel_select(None)) == "aasm_v3_rec"


def test_every_other_profile_stays_selectable():
    """Voorgeselecteerd is niet vastgezet: de technicus moet per opname nog
    altijd een ander profiel kunnen kiezen."""
    import re
    html = _profile_select(_render_channel_select("aasm_v3_dual"))
    options = set(re.findall(r'<option value="([^"]+)"', html))
    for name, _ in available_profile_choices():
        assert name in options, f"{name} niet meer kiesbaar"
    assert len(options) > 1


def test_exactly_one_option_is_preselected():
    """Meerdere `selected` in één select is stil gedrag — de browser houdt de
    laatste. Dat was precies de radiogroep-bug van 4 augustus."""
    import re
    html = _profile_select(_render_channel_select("aasm_v3_prob"))
    assert sum(1 for tag in re.findall(r"<option[^>]*>", html)
               if "selected" in tag) == 1


def test_a_profile_that_no_longer_exists_falls_back_to_the_default():
    """Verdwijnt een profiel uit de registry, dan mag de selectie niet leeg
    blijven — dan zou de eerste optie stilzwijgend winnen."""
    assert _selected(_render_channel_select("profiel_van_vroeger")) == "aasm_v3_rec"
