"""Sectie 8d en de RERA-sectie tonen dezelfde FRI-index.

Eén klinisch rapport toonde **44,3/u** in de RERA-sectie en **43,2/u** in
sectie 8d, over dezelfde nacht en dezelfde teller. De RERA-sectie leidde de
uren af uit `n_rera / rera_index`, sectie 8d deelde door `stats["TST"]` uit de
YASA-slaapstatistiek. Twee definities van slaaptijd, één label.

psgscoring publiceert de index nu zelf (`fri_index`, met dezelfde noemer als
`rera_index` en `rdi`). Deze test bewaakt dat beide secties dat veld LEZEN in
plaats van opnieuw te delen.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import _fri_index  # noqa: E402

RSUM = {"n_fri": 100, "fri_index": 12.3, "n_rera": 40, "rera_index": 4.9,
        "index_denominator_h": 8.13}


def test_the_library_field_wins_over_any_local_division():
    """De TST uit de slaapstatistiek staat er bewust NAAST en wijkt af."""
    assert _fri_index(RSUM, stats={"TST": 500.0}) == 12.3


def test_a_result_from_before_this_field_still_renders():
    """Oude jobs hebben geen `fri_index`; die mogen niet leeg worden."""
    oud = {"n_fri": 100, "n_rera": 40, "rera_index": 4.9}
    got = _fri_index(oud, stats={"TST": 500.0})
    assert got == pytest.approx(100 / (40 / 4.9), abs=0.1), (
        "de terugval hoort de noemer van psgscoring te reconstrueren, niet "
        "die van de YASA-slaapstatistiek")


def test_the_last_resort_is_the_sleep_statistic():
    """Zonder RERA's valt er niets te reconstrueren; dan mag de TST."""
    kaal = {"n_fri": 100}
    assert _fri_index(kaal, stats={"TST": 600.0}) == pytest.approx(10.0)


def test_no_denominator_means_no_number():
    assert _fri_index({"n_fri": 100}, stats={}) is None
    assert _fri_index({"n_fri": 100}, stats={"TST": 0}) is None


def test_an_explicit_none_is_respected():
    """psgscoring geeft None wanneer er geen bruikbare slaaptijd is. Dat is
    een uitspraak, geen ontbrekende waarde -- niet stilzwijgend vervangen
    door een eigen berekening."""
    leeg = {"n_fri": 3, "fri_index": None, "index_denominator_h": 0.0}
    assert _fri_index(leeg, stats={"TST": 480.0}) is None
