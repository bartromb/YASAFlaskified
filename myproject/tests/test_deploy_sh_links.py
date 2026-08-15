"""
tests/test_deploy_sh_links.py — the one-command install URL must agree everywhere.

`deploy.sh` is offered in four places: README.md, DEPLOY_RUNBOOK.md, the
script's own usage header, and the landing page. Before v0.21.0 the script
header spelled the repository `bartromb/yasaflaskified` while every document
spelled it `bartromb/YASAFlaskified`. Both happen to resolve today because
GitHub redirects raw requests case-insensitively — which is exactly why the
divergence survived: nothing broke, so nothing flagged it.

That is a thin guarantee to rest on. It is undocumented behaviour of a third
party, and a reader comparing the header against the repository name sees two
different answers. This test fixes one spelling and keeps the four copies
identical.

Reachability is deliberately not asserted: CI has no network guarantee, and a
test that fails on a GitHub outage teaches people to ignore it.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# `/deploy\.sh`, not `deploy\.sh` — the latter also matches redeploy.sh, which
# is a different script with its own URL.
URL = re.compile(r"https://raw\.githubusercontent\.com/[^\s|)'\"]+?/deploy\.sh")

SOURCES = {
    "README.md": REPO / "README.md",
    "DEPLOY_RUNBOOK.md": REPO / "DEPLOY_RUNBOOK.md",
    "deploy.sh": REPO / "deploy.sh",
    "frontpage.html": REPO / "myproject" / "templates" / "frontpage.html",
}

CANONICAL = "https://raw.githubusercontent.com/bartromb/YASAFlaskified/main/deploy.sh"


def test_every_source_offers_the_install_url():
    """A document that stops mentioning it has quietly dropped the install route."""
    for name, path in SOURCES.items():
        assert path.exists(), f"{name} is missing"
        assert URL.search(path.read_text(encoding="utf-8")), (
            f"{name} no longer offers the deploy.sh install URL"
        )


def test_all_copies_are_byte_identical():
    found = {}
    for name, path in SOURCES.items():
        hits = set(URL.findall(path.read_text(encoding="utf-8")))
        found[name] = hits

    everything = set().union(*found.values())
    assert everything == {CANONICAL}, (
        "the deploy.sh URL is spelled more than one way: "
        + "; ".join(f"{n}={sorted(h)}" for n, h in found.items() if h != {CANONICAL})
    )


def test_the_url_points_at_a_file_that_exists_here():
    """
    The URL serves whatever is on `main`. If the path in the URL and the path
    in the repository ever diverge, the command 404s for every new centre while
    every local check still passes.
    """
    path_in_url = CANONICAL.split("/main/", 1)[1]
    assert (REPO / path_in_url).is_file(), (
        f"the install URL serves /main/{path_in_url}, which does not exist in this repository"
    )
