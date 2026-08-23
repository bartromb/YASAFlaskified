"""Het rapport moet de psgscoring noemen die het GEBRUIKT heeft.

`PSGSCORING_VERSION` stond in `version.py` als handmatig bijgehouden constante
en raakte twee releases achterop: hij zei 0.24.0 terwijl 0.26.0 draaide. Het
provenance-blok van een klinisch rapport noemde daarmee een scoringsbibliotheek
die het niet had gebruikt.

Handmatig bijhouden faalt op precies het moment dat het ertoe doet -- bij een
release, als er veel tegelijk verandert. Deze tests zorgen dat de waarde
uitgelezen blijft.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_the_version_matches_the_installed_package():
    import psgscoring
    from version import PSGSCORING_VERSION

    assert PSGSCORING_VERSION == psgscoring.__version__, (
        f"het rapport zou psgscoring {PSGSCORING_VERSION} vermelden terwijl "
        f"{psgscoring.__version__} geinstalleerd is")


def test_it_is_not_a_hardcoded_literal():
    """De regel mag geen versienummer als tekst bevatten.

    Zonder deze test kan iemand de constante terugzetten en blijft de eerste
    test slagen zolang hij toevallig klopt -- tot de volgende release.
    """
    import re

    src = (Path(__file__).resolve().parent.parent / "version.py").read_text(
        encoding="utf-8")
    toewijzing = [ln for ln in src.splitlines()
                  if ln.strip().startswith("PSGSCORING_VERSION")
                  and "=" in ln and not ln.strip().startswith("#")]
    assert toewijzing, "PSGSCORING_VERSION wordt nergens gezet"
    for ln in toewijzing:
        rechts = ln.split("=", 1)[1]
        assert not re.search(r'["\']\d+\.\d+', rechts), (
            f"PSGSCORING_VERSION staat weer hardgecodeerd: {ln.strip()!r}")


def test_an_unavailable_package_does_not_crash_the_report():
    """Een rapport zonder versie is beter dan geen rapport."""
    from version import _psgscoring_version

    got = _psgscoring_version()
    assert isinstance(got, str) and got, "levert geen bruikbare tekst op"


def test_the_report_prefers_the_version_that_actually_scored():
    """Een rapport kan later gerenderd worden dan de analyse draaide.

    Dan is de nu geinstalleerde versie de verkeerde herkomst: je stempelt een
    oude analyse met de software van vandaag. `tasks.py` legt de echte versie
    bij het scoren vast; het rapport hoort die te gebruiken.
    """
    from generate_pdf_report import provenance_rows

    results = {"comparison": {"_meta": {"psgscoring_version": "0.19.3"}}}
    tekst = " ".join(str(v) for _, v in provenance_rows(results))
    assert "0.19.3" in tekst, (
        f"het rapport negeert de opgeslagen scoringsversie: {tekst[:200]!r}")


def test_a_missing_stored_version_is_marked_as_an_approximation():
    """Oudere jobs hebben het veld niet; dan mag het getal niet als feit staan."""
    from generate_pdf_report import provenance_rows

    tekst = " ".join(str(v) for _, v in provenance_rows({}))
    assert "(?)" in tekst, (
        f"een teruggevallen versie wordt als zeker gepresenteerd: {tekst[:200]!r}")
