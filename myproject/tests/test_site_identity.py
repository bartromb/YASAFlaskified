"""Geen instellingsidentiteit in de code — die hoort in configuratie.

WAT ER MIS WAS
--------------
Tot v0.34.7 stond "Slaapkliniek AZORG" op TWEE plaatsen hardgecodeerd
(`generate_pdf_report._DSITE` en de institution-default van
`generate_psg_report`), én een derde keer in `config.json.example`, dat de
Dockerfile als `config.json` in het image zet. Gemeten in productie: het
site-blok werd gelezen, maar leverde exact de hardgecodeerde waarden op — het
kwam uit het VOORBEELDBESTAND in het image, niet uit configuratie van de
installatie. Elk centrum dat dit product draaide, kreeg dus het briefhoofd van
een ander centrum op zijn rapport.

WAAROM `instance/`
------------------
`instance/` is host-lokaal, bind-gemount in de container en staat in de
rsync-uitsluitingen. Het is de enige plek die een deploy én een image-rebuild
overleven. `config.json` in de app-root wordt bij elke rebuild uit het
voorbeeldbestand teruggezet.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MYPROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(MYPROJECT)          # de repo-root, niet myproject/


def test_de_code_draagt_geen_instellingsnaam():
    from generate_pdf_report import _DSITE

    assert _DSITE["name"] == ""
    assert _DSITE["logo_path"] == ""
    assert _DSITE["url"] == ""


def test_het_voorbeeldbestand_draagt_geen_instellingsnaam():
    """De Dockerfile kopieert dit bestand als config.json in het image."""
    with open(os.path.join(ROOT, "config.json.example"), encoding="utf-8") as f:
        cfg = json.load(f)
    site = cfg.get("site", {})
    assert site.get("name", "") == "", site
    assert site.get("logo_path", "") == "", site


def test_instance_config_gaat_voor_op_de_app_root(tmp_path, monkeypatch):
    """Een deploy of rebuild mag de identiteit van een centrum niet wissen."""
    import generate_pdf_report as G

    app = tmp_path / "app"
    (app / "myproject").mkdir(parents=True)
    (app / "instance").mkdir()
    (app / "config.json").write_text(json.dumps(
        {"site": {"name": "UIT HET IMAGE"}}), encoding="utf-8")
    (app / "instance" / "config.json").write_text(json.dumps(
        {"site": {"name": "Slaapcentrum Voorbeeld", "logo_path": "eigen.png"}}),
        encoding="utf-8")

    monkeypatch.setattr(G, "__file__", str(app / "myproject" / "x.py"))
    monkeypatch.chdir(app)
    site = G._load_site()
    assert site["name"] == "Slaapcentrum Voorbeeld", site
    assert site["logo_path"] == "eigen.png"


def test_zonder_configuratie_blijft_het_briefhoofd_leeg(tmp_path, monkeypatch):
    import generate_pdf_report as G

    app = tmp_path / "leeg"
    (app / "myproject").mkdir(parents=True)
    monkeypatch.setattr(G, "__file__", str(app / "myproject" / "x.py"))
    monkeypatch.chdir(app)
    site = G._load_site()
    assert site["name"] == ""
    assert site["logo_path"] == ""


def test_een_expliciete_override_wint_nog_steeds(tmp_path, monkeypatch):
    import generate_pdf_report as G

    monkeypatch.chdir(tmp_path)
    assert G._load_site({"name": "Direct meegegeven"})["name"] == "Direct meegegeven"


def _bronbestanden():
    for dirpath, dirnames, files in os.walk(MYPROJECT):
        dirnames[:] = [d for d in dirnames
                       if d not in ("tests", "static", "__pycache__")]
        for f in files:
            if f.endswith((".py", ".html")):
                yield os.path.join(dirpath, f)


def test_geen_instellingsnaam_in_zichtbare_tekst():
    """Auteursregels en toelichtende commentaren mogen; zichtbare tekst niet.

    De grens is wat een GEBRUIKER te zien krijgt. Een `Author:`-regel in een
    scriptkop is geen rapport, een default-logo of een placeholder wel.
    """
    patroon = re.compile(r"azorg", re.I)
    overtredingen = []
    for pad in _bronbestanden():
        with open(pad, encoding="utf-8", errors="replace") as f:
            for n, regel in enumerate(f, 1):
                if not patroon.search(regel):
                    continue
                kaal = regel.strip()
                if kaal.startswith(("#", "//", "*", '"""', "'''")):
                    continue                       # commentaar
                if "Author:" in regel or "Designed for" in regel:
                    continue                       # auteurschap
                overtredingen.append(f"{os.path.relpath(pad, ROOT)}:{n}: {kaal[:80]}")
    assert not overtredingen, "instellingsnaam in zichtbare tekst:\n" + \
        "\n".join(overtredingen)


def test_de_validatiecaveat_blijft_staan_zonder_studiecode():
    """De caveat bestaat om eerlijk te zijn over de validatiestand.

    Hem schrappen zou een gebruiker de indruk geven dat er méér bewijs is dan
    er is; de studiecode erin is wat weg moest.
    """
    from i18n import TRANSLATIONS

    for sleutel in TRANSLATIONS:
        for taal, tekst in TRANSLATIONS[sleutel].items():
            if isinstance(tekst, str) and "AZORG-YASA" in tekst:
                raise AssertionError(f"{sleutel}/{taal} noemt de studiecode nog")

    treffers = [k for k, v in TRANSLATIONS.items()
                if isinstance(v, dict) and isinstance(v.get("en"), str)
                and "validation study" in v["en"].lower()]
    assert treffers, "de validatiecaveat is helemaal verdwenen"
