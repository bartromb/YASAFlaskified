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


# ─────────────────────────────────────────────────────────────
#  5. Afwijkende omgevingsparameters horen zichtbaar te zijn
# ─────────────────────────────────────────────────────────────
#
# `PSGSCORING_BREATH_*` overrulet profielwaarden. Dat bestaat om te kunnen
# meten zonder profielen te muteren, maar het betekent dat dezelfde
# profielnaam op twee machines iets anders kan betekenen. Juist het
# herkomstblok bestaat om de UITVOERING te tonen in plaats van de keuze.

def _rows(env_overrides):
    from generate_pdf_report import provenance_rows
    return provenance_rows({
        "meta": {"eeg_channel": "C4", "eog_channel": "EOG1", "emg_channel": "EMG1"},
        "pneumo": {"meta": {
            "all_channels": ["C4", "EOG1", "EMG1", "Pressure Flow"],
            "channels_used": {}, "flow_channels": {},
            "env_overrides": env_overrides,
        }},
    })


def _find(rows, needle):
    for label, value in rows:
        if needle.lower() in str(label).lower():
            return str(value)
    return None


def test_an_active_override_shows_up_in_the_provenance_block():
    v = _find(_rows({"arousal_latency_grading": True}), "omgeving")
    assert v is not None, "afwijkende parameter wordt niet gemeld"
    assert "arousal_latency_grading" in v


def test_several_overrides_are_all_listed():
    v = _find(_rows({"arousal_latency_grading": True,
                     "candidate_min_duration_s": 8.0}), "omgeving")
    assert "arousal_latency_grading" in v
    assert "candidate_min_duration_s" in v


def test_the_normal_case_adds_no_row():
    """Leeg is het normale geval; een lege regel op elk rapport is ruis."""
    for leeg in ({}, None):
        assert _find(_rows(leeg), "omgeving") is None


def test_older_results_without_the_field_do_not_break_the_block():
    from generate_pdf_report import provenance_rows
    rows = provenance_rows({"meta": {"eeg_channel": "C4"},
                            "pneumo": {"meta": {"all_channels": ["C4"]}}})
    assert rows and _find(rows, "omgeving") is None


# ─────────────────────────────────────────────────────────────
#  6. De REM-AHI zegt op hoeveel REM hij rust
# ─────────────────────────────────────────────────────────────
#
# psgscoring 0.15.1 voegde `ahi_rem_reliable` en `ahi_rem_caveat` toe, maar het
# rapport las die velden niet. Op recording 62942a61 (22 min REM) stond
# daardoor "REM AHI 64.2 /u" naast "NREM AHI 38.6 /u" zonder vermelding dat de
# eerste op ~24 events rust. Dat leest als REM-predominante OSA.
#
# Deze toetsen kijken naar de RAPPORTGENERATOR, niet naar de bibliotheek. De
# oorspronkelijke fout was juist dat de bibliotheek geverifieerd werd en het
# rapport niet.

from generate_pdf_report import rem_ahi_caveat  # noqa: E402


def test_too_little_rem_is_qualified_in_the_report():
    txt = rem_ahi_caveat({"ahi_rem": 64.2, "ahi_rem_reliable": False,
                          "rem_min": 22.5})
    assert txt and "22" in txt


def test_enough_rem_says_nothing():
    assert rem_ahi_caveat({"ahi_rem": 38.6, "ahi_rem_reliable": True,
                           "rem_min": 91.0}) is None


def test_older_results_without_the_field_are_not_qualified():
    """Resultaten van vóór 0.15.1 dragen het veld niet. Geen kwalificatie is
    beter dan een verzonnen kwalificatie."""
    assert rem_ahi_caveat({"ahi_rem": 64.2}) is None
    assert rem_ahi_caveat({}) is None
    assert rem_ahi_caveat(None) is None


def test_no_rem_ahi_means_no_caveat_about_it():
    assert rem_ahi_caveat({"ahi_rem": None, "ahi_rem_reliable": False,
                           "rem_min": 0.0}) is None


@pytest.mark.parametrize("lang", ["nl", "fr", "en", "de"])
def test_the_caveat_is_translated(lang):
    txt = rem_ahi_caveat({"ahi_rem": 64.2, "ahi_rem_reliable": False,
                          "rem_min": 22.5}, lang)
    assert txt and "{" not in txt, txt
    assert "22" in txt and "30" in txt


def test_a_missing_rem_duration_does_not_print_a_placeholder():
    txt = rem_ahi_caveat({"ahi_rem": 64.2, "ahi_rem_reliable": False})
    assert txt and "None" not in txt


def test_both_sections_that_print_rem_ahi_consult_the_caveat():
    """De kern van de fout: het veld bestond, het rapport las het niet.
    §8c toont "REM AHI", §8e toont "AHI REM" — allebei moeten ze vragen."""
    src = _src("generate_pdf_report.py")
    calls = [ln for ln in src.splitlines()
             if "rem_ahi_caveat(rsum" in ln and not ln.lstrip().startswith("def ")]
    assert len(calls) >= 2, (
        "een van de twee REM-AHI-secties raadpleegt de kwalificatie niet; "
        f"gevonden aanroepen: {calls}")


# ─────────────────────────────────────────────────────────────
#  7. De REM-tegels dragen twee definities
# ─────────────────────────────────────────────────────────────

def test_the_rem_threshold_matches_the_library_when_it_is_available():
    """`_MIN_REM_MIN` valt terug op 30.0 als psgscoring te oud is. Die terugval
    is er voor oudere installaties, maar hij mag niet stilletjes afwijken van
    de bibliotheek zodra die de constante wél levert."""
    lib = pytest.importorskip("psgscoring.respiratory")
    drempel = getattr(lib, "MIN_STAGE_MIN_FOR_INDEX", None)
    if drempel is None:
        pytest.skip("psgscoring < 0.15.1 — terugval is dan het juiste gedrag")
    from generate_pdf_report import _MIN_REM_MIN
    assert _MIN_REM_MIN == drempel


def test_the_report_gap_tolerance_matches_the_analysis():
    """`REM_GAP_TOLERANCE_MIN` in het rapport spiegelt `rem_gap_tolerance` in
    yasa_analysis.py. Lopen ze uiteen, dan legt de voetnoot iets anders uit dan
    de code doet."""
    import re

    from generate_pdf_report import REM_GAP_TOLERANCE_MIN
    src = _src("yasa_analysis.py")
    m = re.search(r"gap_tolerance: int = (\d+)", src)
    assert m, "gap_tolerance niet gevonden in yasa_analysis.py"
    assert REM_GAP_TOLERANCE_MIN == int(m.group(1)) * 0.5
