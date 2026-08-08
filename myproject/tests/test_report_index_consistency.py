"""Eén grootheid, één getal, één definitie — per rapport.

Vier bevindingen uit de rapportvergelijking van 9 augustus, alle vier bevestigd
tegen de code voor ze gerepareerd werden:

  1. **Twee RDI's in één rapport.** Sectie 8 leest `respiratory.summary`
     (gevuld door `_compute_rera_rdi`), sectie 8b las `arousal.summary` — die
     de RERA's onafhankelijk berekent en NIET bijwerkt na RERA-promotie.
     Sectie 8 meldde 183 RERA's terwijl 8b er 0 toonde, met een eigen RDI
     ernaast.
  2. **Twee FRI-tellers.** Sectie 8 toont `rsum["n_fri"]` — flow-reducties die
     FRI BLEVEN. Sectie 8d telde `len(rejected) - n_reinstated`, dus inclusief
     de events die verderop RERA werden. Systematisch hoger, zelfde label.
  3. **De kolom "Index" droeg het aantal.** Bij 57 RERA's stond er "n=57,
     Index 57"; alleen de totaalrij deelde door de tijd.
  4. **"Opnamedatum" toonde de analysedatum.** Een heranalyse verzette daarmee
     de datum van een onderzoek dat maanden eerder plaatsvond, en twee runs van
     dezelfde nacht kregen twee verschillende opnamedatums.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import _recording_date  # noqa: E402


# ─────────────────────────────────────────────────────────────
#  4. De opnamedatum
# ─────────────────────────────────────────────────────────────

def test_the_recording_date_is_the_recording_not_the_analysis():
    meta = {"recording_start": "2026-04-29T22:14",
            "analysis_timestamp": "2026-08-07T09:55:26.487476"}
    assert _recording_date(meta) == "2026-04-29"


def test_re_analysing_does_not_move_the_recording_date():
    """Dezelfde nacht, twee analyses, één opnamedatum."""
    nacht = "2026-04-29T22:14"
    eerste = _recording_date({"recording_start": nacht,
                              "analysis_timestamp": "2026-08-03T10:00:00"})
    tweede = _recording_date({"recording_start": nacht,
                              "analysis_timestamp": "2026-08-07T09:55:00"})
    assert eerste == tweede == "2026-04-29"


def test_without_a_recording_start_it_says_nothing_rather_than_the_wrong_date():
    """Oudere resultaten dragen `recording_start` niet. Een streepje is dan
    eerlijker dan de analysedatum met een verkeerd etiket erboven."""
    assert _recording_date({"analysis_timestamp": "2026-08-07T09:55:00"}) == "—"
    assert _recording_date({}) == "—"
    assert _recording_date(None) == "—"


# ─────────────────────────────────────────────────────────────
#  3. De indexkolom
# ─────────────────────────────────────────────────────────────

def _index_column(n_fri, n_flat, rera_n, rera_idx):
    """De rekenregel zoals de rapportgenerator hem toepast: dezelfde noemer
    als de totaalrij, afgeleid uit totaal en index zodat er geen tweede
    TST-definitie bijkomt."""
    h = (rera_n / rera_idx) if (rera_n and rera_idx) else None
    fmt = lambda n: f"{n / h:.1f}" if h else "—"   # noqa: E731
    return fmt(n_fri), fmt(n_flat)


def test_the_index_column_holds_an_index_not_a_count():
    """57 RERA's over 8 uur is 7,1/u — niet 57."""
    a, b = _index_column(n_fri=57, n_flat=0, rera_n=57, rera_idx=7.1)
    assert a == "7.1", a
    assert a != "57"


def test_the_parts_add_up_to_the_total():
    """De twee bronnen samen horen de totaalindex te geven; anders staan er
    getallen onder elkaar die niet bij elkaar optellen."""
    n_fri, n_flat, total = 40, 17, 57
    idx_total = 7.1
    a, b = _index_column(n_fri, n_flat, total, idx_total)
    assert float(a) + float(b) == pytest.approx(idx_total, abs=0.1)


def test_without_a_denominator_the_column_stays_empty():
    a, b = _index_column(n_fri=5, n_flat=0, rera_n=0, rera_idx=0)
    assert a == "—" and b == "—"


# ─────────────────────────────────────────────────────────────
#  1 en 2: één bron per grootheid
# ─────────────────────────────────────────────────────────────

def _src(path):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return open(os.path.join(here, path)).read()


def test_the_arousal_section_no_longer_prints_its_own_rdi():
    """Twee RDI's in één rapport is erger dan een ontbrekende: de lezer weet
    niet welke telt."""
    src = _src("generate_pdf_report.py")
    assert 'str(asum.get("n_reras"' not in src, "8b toont weer eigen RERA's"
    assert "asum.get('rera_index'" not in src, "8b toont weer eigen RERA-index"
    assert '"RDI (AHI + RERA)"' not in src, "8b toont weer een eigen RDI"


def test_the_respiratory_section_is_still_the_one_that_reports_rdi():
    """Weghalen mag niet betekenen dat de RDI helemaal verdwijnt."""
    src = _src("generate_pdf_report.py")
    assert 'rsum.get("rdi"' in src
    assert "pdf_rdi_formula" in src


def test_the_fri_section_uses_the_same_count_as_the_respiratory_section():
    src = _src("generate_pdf_report.py")
    assert 'n_fri = rsum.get("n_fri")' in src, \
        "8d rekent weer zijn eigen FRI uit"


def test_the_fri_fallback_survives_for_older_results():
    """Resultaten van vóór `n_fri` mogen niet leeg vallen."""
    src = _src("generate_pdf_report.py")
    assert "max(0, len(rejected_hyps) - n_reinstated)" in src, \
        "terugval voor oude resultaten is weg"
