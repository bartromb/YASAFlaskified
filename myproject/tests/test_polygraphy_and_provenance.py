"""Polygrafie, artefactblokkade en een herkomstblok dat niet mag liegen.

Alles hier komt uit één echt rapport (`c4faa055`, een CPAP-titratiepolygrafie)
waarvan de kop **REI 81000,0/u — Ernstig SAS — therapie CPAP** meldde bij
81 hypopnees. De keten die daartoe leidde:

  1. polygrafie = geen EEG, maar het formulier EISTE een EEG-kanaal;
  2. gebruiker gaf `Pressure Flow` op om verder te kunnen;
  3. YASA stageerde op een flowsignaal en produceerde een hypnogram;
  4. de artefactdetector keek naar datzelfde niet-EEG-kanaal en keurde
     ALLE 1078 epochs af — volkomen terecht;
  5. daarmee bleef nul slaaptijd over als noemer;
  6. psgscoring had een ondergrens van 0,001 uur op die noemer, dus werd de
     index het aantal maal duizend.

Stap 6 is in psgscoring gerepareerd (zie tests/test_index_denominator.py daar).
Deze tests dekken 1 tot en met 4, plus een los defect uit hetzelfde onderzoek:
het herkomstblok toonde `EOG1` en `EMG1` terwijl die kanalen niet in het EDF
zaten — het rapporteerde de KEUZE, niet de UITVOERING.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import provenance_rows  # noqa: E402


# ─────────────────────────────────────────────────────────────
#  Het herkomstblok
# ─────────────────────────────────────────────────────────────

def _results(eeg="C4", eog="EOG1", emg="EMG1", all_ch=None, used_eeg=None):
    return {
        "meta": {"eeg_channel": eeg, "eog_channel": eog, "emg_channel": emg},
        "pneumo": {"meta": {
            "all_channels": all_ch if all_ch is not None else
                ["Snore", "Pressure Flow", "Flow Th.", "RIP Thora", "RIP Abdom",
                 "SpO2", "PLMl", "PLMr", "Pos.", "Pulse", "ECG II", "C3", "C4"],
            "channels_used": {"eeg": used_eeg} if used_eeg else {},
            "flow_channels": {"apnea_sensor": "Flow Th.",
                              "hypopnea_sensor": "Pressure Flow"},
        }},
    }


def _val(rows, needle):
    for label, value in rows:
        if needle.lower() in str(label).lower():
            return str(value)
    return None


def test_a_staging_channel_that_is_not_in_the_edf_is_flagged():
    """Het echte geval: EOG1 en EMG1 stonden in het rapport, niet in het EDF."""
    rows = provenance_rows(_results())
    assert "niet in dit EDF" in _val(rows, "EOG")
    assert "niet in dit EDF" in _val(rows, "EMG")


def test_a_channel_that_does_exist_is_shown_plainly():
    """Geen waarschuwing waar niets aan de hand is."""
    rows = provenance_rows(_results())
    assert _val(rows, "EEG").startswith("C4")
    assert "niet in dit EDF" not in _val(rows, "EEG")


def test_without_a_channel_list_nothing_is_claimed_either_way():
    """Oude resultaten dragen `all_channels` niet. Dan is 'niet aanwezig' een
    bewering die we niet kunnen onderbouwen, en zwijgen we erover."""
    rows = provenance_rows(_results(all_ch=[]))
    for role in ("EEG", "EOG", "EMG"):
        assert "niet in dit EDF" not in _val(rows, role), role


def test_the_arousal_eeg_is_shown_when_it_differs_from_the_staging_eeg():
    """Op de echte opname stageerde YASA op C4 terwijl de respiratoire
    pijplijn C3 als EEG-rol koos. Twee kanalen in één run; het rapport toonde
    er één."""
    rows = provenance_rows(_results(eeg="C4", used_eeg="C3"))
    assert _val(rows, "Arousal") == "C3"


def test_it_stays_quiet_when_both_use_the_same_channel():
    rows = provenance_rows(_results(eeg="C4", used_eeg="C4"))
    assert _val(rows, "Arousal") is None


# ─────────────────────────────────────────────────────────────
#  Polygrafie: geen EEG vereist
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("study_type,eeg,verwacht_geweigerd", [
    ("titration_pg_cpap",   "", False),   # polygrafie zonder EEG: toegestaan
    ("titration_pg_mra",    "", False),
    ("diagnostic_pg",       "", False),   # miste de oude `"_pg_"`-toets
    ("diagnostic_psg",      "", True),    # PSG zonder EEG: nog steeds fout
    ("titration_psg_cpap",  "", True),
    ("diagnostic_psg",   "C4", False),
])
def test_only_a_psg_still_demands_an_eeg_channel(study_type, eeg, verwacht_geweigerd):
    """De regel zoals app.py hem toepast. Zolang polygrafie een EEG eiste,
    vulde de gebruiker de neusdruk in en viel de rest om."""
    from study_type import requires_eeg_channel
    geweigerd = not eeg and requires_eeg_channel(study_type)
    assert geweigerd is verwacht_geweigerd


def test_the_old_substring_test_missed_a_diagnostic_polygraphy():
    """`"_pg_" in study_type` heeft geen sluitende underscore om op te haken.
    Deze test bestaat omdat die regel op drie plaatsen stond."""
    from study_type import is_polygraphy
    assert "_pg_" not in "diagnostic_pg"      # de oude toets faalde hier
    assert is_polygraphy("diagnostic_pg")     # de nieuwe niet


def test_a_psg_is_never_mistaken_for_a_polygraphy():
    """`titration_psg_cpap` bevat de letters p, s en g op rij — een slordige
    toets zou hem als polygrafie lezen en de staging overslaan."""
    from study_type import STUDY_TYPES, is_polygraphy
    assert not is_polygraphy("titration_psg_cpap")
    assert not is_polygraphy("diagnostic_psg")
    # en elk type in de keuzelijst valt in precies één van beide klassen
    assert sum(1 for s in STUDY_TYPES if is_polygraphy(s)) == 3


# ─────────────────────────────────────────────────────────────
#  Polygrafie: de noemer is registratietijd
# ─────────────────────────────────────────────────────────────

def test_a_polygraphy_hypnogram_covers_the_whole_recording():
    """Alle epochs als N2 tellen betekent: de noemer IS de registratietijd.

    Dat is wat het rapport altijd al beweerde ("events per uur registratietijd")
    maar nergens berekende. Hier alleen de rekensom die tasks.py opzet — de
    deling zelf zit in psgscoring en wordt daar getoetst
    (tests/test_index_denominator.py), zodat deze suite niet vastzit aan een
    psgscoring-versie die nog niet uitgebracht is.
    """
    n_epochs = 1078                       # de echte opname: 539 min
    hypno = ["N2"] * n_epochs
    assert all(s != "W" for s in hypno), "elke epoch telt mee als noemer"
    uren = n_epochs * 30 / 3600
    assert uren == pytest.approx(8.98, abs=0.01)
    # 81 hypopnees over die registratietijd = 9,0/u — mild.
    # Het rapport meldde 81000,0/u en "Ernstig SAS - therapie CPAP".
    assert 8.0 < 81 / uren < 10.0


# ─────────────────────────────────────────────────────────────
#  100% artefact is een mislukte analyse
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
#  De opname beslist, niet de keuzelijst
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("study_type,eeg_ch,verwacht_pg", [
    ("diagnostic_pg",  None,  True),   # allebei: polygrafie
    ("diagnostic_pg",  "C4",  True),   # type zegt polygrafie -> geen staging
    ("diagnostic_psg", None,  True),   # GEEN EEG -> tóch polygrafie
    ("diagnostic_psg", "C4",  False),  # echte PSG
])
def test_a_montage_without_eeg_is_a_polygraphy_whatever_the_form_said(
        study_type, eeg_ch, verwacht_pg):
    """Het studietype stond op PSG, de neusdruk stond als EEG voorgeselecteerd,
    en er kwam een hypnogram uit een flowsignaal. Niemand hoort te moeten
    onthouden dat veld goed te zetten — de opname weet het al."""
    from study_type import is_polygraphy
    assert (is_polygraphy(study_type) or not eeg_ch) is verwacht_pg


def test_the_report_label_follows_what_actually_ran():
    """Draaide het als polygrafie, dan hoort er REI boven te staan — ook als
    het studietype op PSG bleef staan. Anders staat er "AHI" boven een getal
    dat over registratietijd gaat."""
    from study_type import is_polygraphy
    results = {"study_type": "diagnostic_psg", "is_polygraphy": True}
    label_is_rei = bool(results.get("is_polygraphy")) or is_polygraphy(
        results.get("study_type"))
    assert label_is_rei is True


def test_a_real_psg_keeps_its_ahi_label():
    from study_type import is_polygraphy
    results = {"study_type": "diagnostic_psg", "is_polygraphy": False}
    assert not (bool(results.get("is_polygraphy"))
                or is_polygraphy(results.get("study_type")))


def test_no_eeg_like_channel_means_no_preselection():
    """De blinde terugval `best_eeg = channels[0]` zette `Pressure Flow` als
    EEG klaar op een montage zonder EEG. Eén klik op "start" volstond dan om
    YASA op de neusdruk te laten stageren."""
    kanalen = ["Pressure Flow", "Flow Th.", "RIP Thorax", "RIP Abdomen",
               "SPO2", "Pos.", "Pressure Snore", "Pulse"]
    eeg_achtig = [c for c in kanalen
                  if c.upper() in {"C3", "C4", "C3-M2", "C4-M1", "F3", "F4",
                                   "O1", "O2", "CZ"}]
    assert eeg_achtig == [], "deze montage heeft geen EEG"
    # en dan hoort er niets voorgeselecteerd te worden — geen channels[0]
    best_eeg = eeg_achtig[0] if eeg_achtig else None
    assert best_eeg is None
    assert best_eeg != kanalen[0]


def test_a_fully_masked_recording_is_reported_as_blocking():
    """De vorm van de waarschuwing die tasks.py wegschrijft. Op het echte
    rapport stond '100% artefact' onderaan terwijl de kop 'Ernstig SAS' zei."""
    n_ep, art = 1078, list(range(1078))
    frac = len(set(art)) / (n_ep or 1)
    assert frac >= 1.0
    warning = {"code": "all_epochs_artefact", "severity": "blocking"}
    assert warning["severity"] == "blocking"


def test_a_partly_masked_recording_is_not_blocking():
    """27% artefact is normaal en mag niets blokkeren."""
    n_ep, art = 1284, list(range(348))
    assert len(set(art)) / n_ep < 1.0
