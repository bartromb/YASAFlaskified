"""De nginx-uploadgrens in deploy.sh moet de app-grens dekken.

WAT ER MIS GING
---------------
`deploy.sh` schreef `client_max_body_size 520M`, terwijl de app sinds 0.34.9
`MAX_CONTENT_LENGTH` op 2 GB heeft staan -- juist omdat een BDF ruim de helft
groter is dan dezelfde nacht in EDF.

Een verse installatie weigerde daardoor een BDF van 553 MB met een 413 voordat
de app hem ooit zag. De gebruiker krijgt dan een foutmelding die niets over zijn
bestand zegt, op precies het bestandstype waarvoor de grens verhoogd was.

Productie draaide er niet tegenaan omdat die geen host-nginx gebruikt maar
nginx-proxy-manager in een container -- wat de DEPLOY_RUNBOOK niet vermeldt.
Het gat bestond dus alleen voor NIEUWE installaties, en dat is precies de weg
waarlangs een ander slaapcentrum binnenkomt.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEPLOY = os.path.join(REPO, "deploy.sh")


def _naar_bytes(waarde: str) -> int:
    m = re.fullmatch(r"(\d+)([KMG]?)", waarde.strip().upper())
    assert m, waarde
    n = int(m.group(1))
    return n * {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}[m.group(2)]


def test_deploy_script_bestaat_nog():
    assert os.path.exists(DEPLOY), "deploy.sh is weg — de installatieweg voor een nieuw centrum"


def test_nginx_grens_dekt_de_app_grens():
    from app import app as flask_app

    with open(DEPLOY, encoding="utf-8") as f:
        bron = f.read()
    m = re.search(r"client_max_body_size\s+(\S+?);", bron)
    assert m, "deploy.sh zet geen client_max_body_size"
    nginx = _naar_bytes(m.group(1))
    app_grens = flask_app.config["MAX_CONTENT_LENGTH"]
    assert nginx >= app_grens, (
        f"nginx staat op {nginx} bytes, de app laat {app_grens} toe — "
        "een upload daartussen krijgt een 413 die niets over het bestand zegt")


def test_een_gewone_bdf_past():
    """553 MB is de opname die dit aan het licht bracht: één nacht, geen
    uitzonderlijk bestand."""
    with open(DEPLOY, encoding="utf-8") as f:
        bron = f.read()
    m = re.search(r"client_max_body_size\s+(\S+?);", bron)
    assert _naar_bytes(m.group(1)) >= 600 * 1024 ** 2, \
        "een BDF van één nacht past niet door de nginx-grens"
