"""Drie aandachtspunten die de motiverende rapporten hadden moeten dragen.

**Rapport 1** toonde AHI 3,1 naast ODI3 14,1, T90 28 % en hypoxic burden
17 %·min/u. De hypoxemie werd gevlagd, de DISCREPANTIE niet — en die is de
klinische boodschap: er is veel meer desaturatie dan er events gescoord zijn,
dus de ruwe tracing hoort bekeken te worden.

**Rapport 2** toonde AI 3,5/u bij AHI 42 met 217 respiratoire events. Dat kan
fysiologisch niet, en er stond geen enkele vlag bij. Deze regel had de
EMG-regressie in één oogopslag zichtbaar gemaakt.

**Beide** toonden een gemiddelde hartfrequentie van 43,8 bpm naast hun eigen
referentie "60–100", zonder vlag — terwijl er verderop in hetzelfde rapport
al een bradycardie-telling staat.

Beschrijvend, geen advies: dezelfde stijl als de bestaande vlaggen.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import _clinical_flags  # noqa: E402


def _flags(rsum=None, ss=None, asum=None, pneumo=None, lang="nl"):
    return _clinical_flags(rsum or {}, pneumo or {}, ss or {}, asum or {},
                           lang=lang)


# ══════════════════════════════════════════════════════════════
# 1. desaturatielast disproportioneel t.o.v. de gescoorde events
# ══════════════════════════════════════════════════════════════

def test_case_one_gets_the_discrepancy_flag():
    out = _flags(rsum={"ahi_total": 3.1},
                 ss={"odi_3pct": 14.1, "pct_below_90": 28.0})
    assert any("disproportion" in f.lower() or "ruwe tracing" in f.lower()
               for f in out), out


def test_an_odi_three_times_the_ahi_is_enough_on_its_own():
    out = _flags(rsum={"ahi_total": 10.0}, ss={"odi_3pct": 31.0})
    assert len(out) >= 1, out


def test_a_matching_odi_and_ahi_raise_nothing():
    assert _flags(rsum={"ahi_total": 20.0},
                  ss={"odi_3pct": 22.0, "pct_below_90": 2.0}) == []


def test_a_high_t90_with_a_normal_ahi_is_enough_on_its_own():
    """De combinatie uit rapport 1: nauwelijks events, veel tijd onder 90 %."""
    out = _flags(rsum={"ahi_total": 3.1}, ss={"pct_below_90": 28.0})
    assert len(out) >= 2, ("verwacht zowel de hypoxemie- als de "
                           f"discrepantievlag: {out}")


def test_a_high_t90_with_a_high_ahi_is_explained_by_the_events():
    """Bij AHI 40 verklaart de eventlast de desaturatie; dan is er geen
    discrepantie, alleen hypoxemie."""
    out = _flags(rsum={"ahi_total": 40.0},
                 ss={"odi_3pct": 42.0, "pct_below_90": 28.0})
    assert not any("ruwe tracing" in f.lower() for f in out), out


# ══════════════════════════════════════════════════════════════
# 2. arousal-index onwaarschijnlijk laag
# ══════════════════════════════════════════════════════════════

def test_case_two_gets_the_arousal_flag():
    out = _flags(rsum={"ahi_total": 42.0}, asum={"arousal_index": 3.5})
    assert any("arousal" in f.lower() for f in out), out


def test_a_plausible_arousal_index_raises_nothing():
    out = _flags(rsum={"ahi_total": 42.0}, asum={"arousal_index": 24.0})
    assert not any("onwaarschijnlijk" in f.lower() for f in out), out


def test_a_low_arousal_index_at_a_low_ahi_is_not_flagged():
    """Zonder eventlast is een lage arousal-index gewoon een lage index."""
    assert _flags(rsum={"ahi_total": 4.0}, asum={"arousal_index": 2.0}) == []


def test_a_missing_arousal_index_is_not_a_zero():
    assert _flags(rsum={"ahi_total": 42.0}, asum={}) == []


# ══════════════════════════════════════════════════════════════
# 3. bradycardie
# ══════════════════════════════════════════════════════════════

def test_a_mean_heart_rate_under_fifty_is_flagged():
    out = _flags(pneumo={"heart_rate": {"summary": {"avg_hr": 43.8}}})
    assert any("43" in f or "bradycard" in f.lower() for f in out), out


def test_a_normal_heart_rate_is_not_flagged():
    assert _flags(pneumo={"heart_rate": {"summary": {"avg_hr": 68.0}}}) == []


# ══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("lang", ["nl", "fr", "en", "de"])
def test_all_three_render_in_every_language(lang):
    out = _flags(rsum={"ahi_total": 42.0},
                 ss={"odi_3pct": 200.0, "pct_below_90": 30.0},
                 asum={"arousal_index": 3.5},
                 pneumo={"heart_rate": {"summary": {"avg_hr": 43.8}}},
                 lang=lang)
    assert len(out) >= 3, out
    for f in out:
        assert "{" not in f, f
