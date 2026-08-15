"""
tests/test_frontpage_invite.py — the invitation to other sleep centres.

v0.21.0 added a landing-page section inviting other sleep centres to adopt
the software, with the caveats attached to the invitation rather than to a
linked page. Three things can rot here, and each is silent:

  1. A translation is added for one language only. Jinja's `t()` falls back,
     so the page still renders — in the wrong language, on the one section
     whose whole point is to be read carefully. Asserting "HTTP 200" would
     not catch it; asserting the four languages differ does.

  2. A caveat is dropped while the invitation stays. The page then reads as a
     recommendation without its limits, which is the failure mode that
     matters clinically.

  3. The self-hosting command drifts from the one in DEPLOY_RUNBOOK.md, so a
     centre following the landing page runs something that no longer exists.
"""
import re
from pathlib import Path

import pytest
from app import app

LANGS = ("nl", "fr", "en", "de")
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    return app.test_client()


def _frontpage(client, lang):
    with client.session_transaction() as sess:
        sess["lang"] = lang
    resp = client.get("/")
    assert resp.status_code == 200, f"landing page {lang}: HTTP {resp.status_code}"
    return resp.get_data(as_text=True)


def _invite_section(html):
    """The markup from `id="invite"` up to the next section."""
    start = html.find('id="invite"')
    assert start != -1, "the invitation section is missing from the landing page"
    end = html.find("<section", start)
    return html[start:end if end != -1 else len(html)]


@pytest.mark.parametrize("lang", LANGS)
def test_invite_section_renders(client, lang):
    seg = _invite_section(_frontpage(client, lang))
    assert "route" in seg, f"{lang}: the three adoption routes are gone"
    assert len(re.findall(r"<li>", seg)) == 6, (
        f"{lang}: expected 6 caveats, found {len(re.findall(r'<li>', seg))}"
    )


def test_each_language_has_its_own_text(client):
    """A missing translation falls back silently; distinct titles prove it did not."""
    titles = {}
    for lang in LANGS:
        seg = _invite_section(_frontpage(client, lang))
        match = re.search(r'section-title reveal">([^<]+)<', seg)
        assert match, f"{lang}: no section title in the invitation"
        titles[lang] = match.group(1).strip()

    assert len(set(titles.values())) == len(LANGS), (
        f"two languages render the same invitation title, so at least one is "
        f"falling back instead of being translated: {titles}"
    )


def test_medical_device_caveat_is_present(client):
    """The invitation may never appear without this one."""
    for lang in LANGS:
        seg = _invite_section(_frontpage(client, lang))
        assert "MDR 2017/745" in seg, f"{lang}: the medical-device caveat is missing"
        assert "/disclaimer" in seg, f"{lang}: the disclaimer link is missing"


def test_stack_tile_shows_the_running_psgscoring_version(client):
    """
    The tile used to carry a hand-typed "psgscoring 0.12" and was five minor
    versions stale by the time anyone noticed. It now renders the value the
    app actually imports, so it cannot drift again.
    """
    from version import PSGSCORING_VERSION

    html = _frontpage(client, "en")
    assert f"psgscoring {PSGSCORING_VERSION}" in html, (
        "the stack tile does not show the psgscoring version the app is running"
    )


def test_self_host_command_matches_the_runbook(client):
    """
    The landing page hands visitors a one-line install command. If it drifts
    from DEPLOY_RUNBOOK.md, the page sends people to a script that the
    documented procedure no longer describes.
    """
    seg = _invite_section(_frontpage(client, "en"))
    on_page = re.findall(r"https://raw\.githubusercontent\.com/\S+?deploy\.sh", seg)
    assert on_page, "the landing page no longer shows the deploy.sh command"

    runbook = (REPO / "DEPLOY_RUNBOOK.md").read_text(encoding="utf-8")
    in_runbook = re.findall(r"https://raw\.githubusercontent\.com/\S+?deploy\.sh", runbook)
    assert in_runbook, "DEPLOY_RUNBOOK.md no longer documents the deploy.sh URL"

    assert on_page[0].lower() == in_runbook[0].lower(), (
        f"landing page offers {on_page[0]} but the runbook documents {in_runbook[0]}"
    )
