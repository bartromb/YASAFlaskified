"""Na een heranalyse moet de browser het NIEUWE rapport krijgen.

WAT ER MIS WAS
--------------
Een heranalyse draait op HETZELFDE job_id en herschrijft `_results.json`. De
downloadroute regenereert dan het PDF en stuurt no-cache-headers mee — maar de
URL blijft identiek, en Firefox serveert een bijlage van een identieke URL uit
zijn eigen cache zonder de server te vragen. Daarvoor bestaat `report_ver()`:
de mtime van results.json als `?v=`, zodat een heranalyse een URL oplevert die
de browser nog niet kent.

`results_extended.html` linkte als enige ZONDER die parameter. Wie vanaf die
pagina downloadde, kreeg na een heranalyse het oude rapport terug — de fout die
de gebruiker op 26-08-2026 meldde.

Deze test pint het patroon voor ALLE sjablonen, want de volgende die het vergeet
levert precies dezelfde stille fout op: een rapport dat er goed uitziet en van
de vorige analyse is.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "templates")

# Een downloadlink naar een rapport, in beide schrijfwijzen die hier voorkomen.
DIRECT = re.compile(r'href="(/results/\{\{[^}]*\}\}/(?:pdf|excel)[^"]*)"')
URLFOR = re.compile(r"url_for\('download_(?:pdf|excel)'[^)]*\)")


def _sjablonen():
    for naam in sorted(os.listdir(TEMPLATES)):
        if naam.endswith(".html"):
            with open(os.path.join(TEMPLATES, naam), encoding="utf-8") as f:
                yield naam, f.read()


def test_elke_rapportlink_draagt_een_cachebuster():
    fout = []
    for naam, html in _sjablonen():
        for m in DIRECT.finditer(html):
            url = m.group(1)
            if "?v=" not in url and "?t=" not in url:
                fout.append(f"{naam}: {url}")
        for m in URLFOR.finditer(html):
            if "v=" not in m.group(0):
                fout.append(f"{naam}: {m.group(0)}")
    assert not fout, ("rapportlinks zonder cachebuster — na een heranalyse "
                      "serveert de browser het oude rapport:\n  " + "\n  ".join(fout))


def test_de_cachebuster_volgt_de_resultaten_en_niet_de_klok():
    """`?v=` moet de mtime van results.json zijn.

    Een willekeurig getal zou ook cache omzeilen, maar dan is elke download een
    nieuwe URL en verliest de browser zijn cache voor rapporten die NIET
    veranderd zijn. De mtime verandert precies wanneer de inhoud verandert.
    """
    import inspect

    from app import _report_ver

    bron = inspect.getsource(_report_ver)
    assert "_results.json" in bron and "getmtime" in bron


def test_de_downloadroute_stuurt_geen_cache_headers():
    """Gordel én bretels: de bustende URL is de eerste verdediging, de headers
    de tweede. Beide zijn ooit apart tekortgeschoten."""
    import inspect

    import app as A

    bron = inspect.getsource(A)
    assert 'resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"' in bron
    assert 'resp.headers["Pragma"] = "no-cache"' in bron
