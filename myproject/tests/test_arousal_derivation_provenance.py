"""De provenance moet de afleidingSSET tonen, niet één kanaal ervan.

Op een klinisch rapport (0.34.4) stond "Arousal-analyse — EEG: C3" terwijl de
analyse `C3 ∪ C4` draaide: twee afleidingen, allebei met events (C3: 142,
C4: 115). Het rapport onderrapporteerde dus wat de uitkomst gevoed heeft — en
dat is precies wat die tabel moet doen; er staat onder: "The channel selection
determines the result."

Niet cosmetisch. Legt iemand dit rapport naast het vorige, dan staat er twee
keer "C3" terwijl de arousal-index van 19,5 naar 24,5 ging. De verklaring van
dat verschil — een tweede afleiding die er eerst niet was — staat nergens.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import _arousal_eeg_label  # noqa: E402


def test_two_derivations_are_both_named():
    got = _arousal_eeg_label({"channels_used": {"eeg": "C3"}},
                             {"derivations": ["C3", "C4"]})
    assert got == "C3 ∪ C4", got


def test_three_derivations_are_all_named():
    got = _arousal_eeg_label({"channels_used": {"eeg": "EEG F4-M1"}},
                             {"derivations": ["EEG F4-M1", "EEG C4-M1",
                                              "EEG O2-M1"]})
    assert got == "EEG F4-M1 ∪ EEG C4-M1 ∪ EEG O2-M1", got


def test_a_single_derivation_stays_plain():
    """Geen unietekens op een run die er maar één had."""
    assert _arousal_eeg_label({"channels_used": {"eeg": "C3"}},
                              {"derivations": ["C3"]}) == "C3"


def test_without_a_derivation_list_it_falls_back_to_the_channel():
    """Resultaten van vóór dit veld, en het single-modus-pad dat geen lijst
    zet, mogen niet leeg worden."""
    assert _arousal_eeg_label({"channels_used": {"eeg": "C3"}}, {}) == "C3"
    assert _arousal_eeg_label({"channels_used": {"eeg": "C3"}}, None) == "C3"


def test_no_eeg_at_all_gives_nothing():
    assert _arousal_eeg_label({}, {}) is None
    assert _arousal_eeg_label(None, None) is None


def test_the_derivation_list_wins_over_the_single_channel():
    """`channels_used.eeg` is de element-0-pick; de lijst is wat er draaide."""
    got = _arousal_eeg_label({"channels_used": {"eeg": "C3"}},
                             {"derivations": ["C3", "C4", "O2-M1"]})
    assert "C4" in got and "O2-M1" in got


# ══════════════════════════════════════════════════════════════
# De rij verschijnt ook wanneer element 0 gelijk is aan het stagingkanaal
# ══════════════════════════════════════════════════════════════

def test_the_row_appears_when_a_union_ran_even_if_channel_zero_matches():
    """De rij stond er alleen als het arousal-EEG AFWEEK van het
    stagingkanaal. Draait er een union op C4 ∪ O2 terwijl de staging ook C4
    gebruikt, dan verdween de hele rij en zag niemand dat er twee afleidingen
    liepen."""
    from generate_pdf_report import _arousal_row_needed
    assert _arousal_row_needed("C4", {"channels_used": {"eeg": "C4"}},
                               {"derivations": ["C4", "O2-M1"]}) is True
    assert _arousal_row_needed("C4", {"channels_used": {"eeg": "C4"}},
                               {"derivations": ["C4"]}) is False
    assert _arousal_row_needed("C4", {"channels_used": {"eeg": "C3"}},
                               {}) is True
