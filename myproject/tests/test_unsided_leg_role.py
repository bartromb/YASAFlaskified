"""Een montage met één ongezijderd beenkanaal moet dat kunnen kiezen.

psgscoring kent sinds 0.27.3 een rol `leg` voor een kaal beenkanaal (MESA's
`Leg`, of een klinische montage met één tibialiskanaal). Zonder die rol in de
kanaalpagina moet de gebruiker het aan `leg_l` of `leg_r` toewijzen, en dat is
dezelfde onwaarheid die de rol juist vermijdt: `_merge_bilateral` ontdubbelt
bewegingen die beide benen zien, en die regel hoort niet te draaien alsof er
twee kanalen zijn.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SJABLOON = os.path.join(HIER, "templates", "channel_select.html")
APP_PY = os.path.join(HIER, "app.py")


def test_the_form_offers_the_unsided_leg_role():
    with open(SJABLOON, encoding="utf-8") as f:
        html = f.read()
    assert re.search(r'\(\s*"leg"\s*,', html), (
        "de kanaalpagina biedt leg_l en leg_r maar geen ongezijderd been")


def test_the_route_accepts_it():
    with open(APP_PY, encoding="utf-8") as f:
        src = f.read()
    # Anker op de lus die de pneumo_-formuliervelden uitleest; er staat
    # elders nog een `for ch_type in [...]` voor de metadataregel. Niet-gulzig
    # matchen, anders slokt de eerste lus de hele rest van het bestand op.
    blok = re.search(
        r'for ch_type in \[([^\]]*?)\]:\s*\n\s*val = request\.form\.get\(',
        src, re.S)
    assert blok, "de pneumo-rollenlijst van de route niet gevonden"
    assert '"leg"' in blok.group(1), (
        "een pneumo_leg uit het formulier wordt stil weggegooid")


@pytest.mark.parametrize("lang", ["nl", "fr", "en", "de"])
def test_the_label_exists_in_every_language(lang):
    from i18n import t
    for sleutel in ("ch_leg_label", "ch_leg_desc"):
        txt = t(sleutel, lang)
        assert txt and txt != sleutel, f"{sleutel} ontbreekt in {lang}"


def test_the_library_knows_the_role():
    """Een rol aanbieden die psgscoring niet kent zou stil genegeerd worden."""
    from psgscoring.constants import CHANNEL_PATTERNS
    assert "leg" in CHANNEL_PATTERNS
