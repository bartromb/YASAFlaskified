"""De uploadgrens staat op ÉÉN plek, en die is groot genoeg voor BDF.

WAT ER MIS WAS
--------------
`upload.html` droeg zijn eigen `const MAX_SIZE_MB = 500`, los van
`MAX_CONTENT_LENGTH`. Twee getallen die hetzelfde horen te zijn maar apart
onderhouden worden, lopen uiteen — en dan weigert de browser een bestand dat de
server had aangenomen, of andersom. Een gebruiker liep er op 26-08-2026 tegenaan
met een BDF van 528 MB.

WAAROM 2 GB
-----------
BDF is 24-bit, EDF 16-bit: dezelfde nacht is in BDF ruwweg anderhalf keer zo
groot. Een opname van 11 uur met 27 kanalen op 250 Hz komt op ~550 MB, en die
werd geweigerd.

WAT DE GRENS NIET IS
--------------------
De gechunkte upload verstuurt 2 MB per verzoek, dus `MAX_CONTENT_LENGTH` en de
`client_max_body_size` van de proxy zien nooit het hele bestand. De enige echte
poort daar is de client-side controle. Op `index.html` (niet gechunkt) geldt
`MAX_CONTENT_LENGTH` wél — vandaar dat beide pagina's dezelfde waarde moeten
gebruiken.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "templates")


def _sjabloon(naam):
    with open(os.path.join(TEMPLATES, naam), encoding="utf-8") as f:
        return f.read()


def test_de_serverlimiet_is_twee_gigabyte():
    from app import app

    assert app.config["MAX_CONTENT_LENGTH"] == 2 * 1024 * 1024 * 1024


def test_geen_enkele_pagina_draagt_een_eigen_getal():
    """Een hardgecodeerd getal hier is precies wat de twee liet uiteenlopen."""
    for naam in ("upload.html", "index.html"):
        html = _sjabloon(naam)
        for m in re.finditer(r"MAX_SIZE_MB\s*=\s*([^;]+);", html):
            waarde = m.group(1).strip()
            assert "MAX_UPLOAD_MB" in waarde, \
                f"{naam} zet MAX_SIZE_MB op {waarde!r} in plaats van op de serverwaarde"


def test_beide_uploadpagina_s_controleren_de_grootte():
    """Zonder controle op index.html merkt de gebruiker de grens pas als 413."""
    for naam in ("upload.html", "index.html"):
        html = _sjabloon(naam)
        assert "MAX_SIZE_MB" in html, f"{naam} controleert de bestandsgrootte niet"


def test_de_context_levert_de_grens_in_megabyte():
    from app import app

    with app.test_request_context("/"):
        ctx = app.jinja_env.globals.copy()
        for proc in app.template_context_processors[None]:
            ctx.update(proc())
    assert ctx["MAX_UPLOAD_MB"] == 2048, ctx.get("MAX_UPLOAD_MB")


def test_een_typische_bdf_past_er_nu_in():
    """De opname die de grens blootlegde was 553 MB."""
    from app import app

    assert 553 * 1024 * 1024 < app.config["MAX_CONTENT_LENGTH"]
