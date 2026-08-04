"""De EDF-header anonimiseren mag nooit één byte signaaldata verzetten.

Twee routes gebruiken dezelfde regels: de browser vóór verzenden
(`static/edf_anonymize.js`) en de server na het opladen (`edf_anonymize.py`).
Lopen ze uiteen, dan levert dezelfde opname twee verschillende codes op en zijn
de analyses niet meer aan elkaar te koppelen.

De harde eis zit in test_the_signal_data_is_untouched: de header is een blok van
vaste lengte, en één byte erbij verschuift elke sample-offset in het bestand.
"""

import os
import sys

from edf_anonymize import (
    HEADER_LEN,
    EdfAnonymizeError,
    anonymize_file_in_place,
    anonymize_header_bytes,
    anonymize_patient_field,
    anonymize_recording_field,
    pseudonym,
    read_identifiers,
    sanitize_study_code,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _header(patient: str, recording: str, date: str = "04.08.26") -> bytes:
    """Een EDF-header van precies 256 bytes met de drie velden ingevuld."""
    h = bytearray(b" " * HEADER_LEN)
    h[0:8] = b"0       "
    h[8:88] = patient.encode("ascii").ljust(80)
    h[88:168] = recording.encode("ascii").ljust(80)
    h[168:176] = date.encode("ascii").ljust(8)
    h[176:184] = b"22.15.00"
    return bytes(h)


EDF_PLUS = _header(
    "MRN12345 M 03-MAR-1971 Janssens_Pieter",
    "Startdate 29-APR-2026 AZORG_SLAAP TECH_LV SOMNO_eco_0775",
)


# ─────────────────────────────────────────────────────────────
#  De velden
# ─────────────────────────────────────────────────────────────

def test_the_patient_name_and_birthdate_are_gone():
    out = anonymize_patient_field("MRN12345 M 03-MAR-1971 Janssens_Pieter")
    assert "Janssens" not in out
    assert "1971" not in out
    assert "MRN12345" not in out


def test_sex_survives_because_it_is_a_subgroup_variable():
    assert anonymize_patient_field("MRN1 M 03-MAR-1971 X").split()[1] == "M"
    assert anonymize_patient_field("MRN1 F 03-MAR-1971 X").split()[1] == "F"
    assert anonymize_patient_field("MRN1 M 03-MAR-1971 X", keep_sex=False).split()[1] == "X"


def test_hospital_and_technician_are_gone_but_the_startdate_stays():
    out = anonymize_recording_field(
        "Startdate 29-APR-2026 AZORG_SLAAP TECH_LV SOMNO_eco_0775")
    assert "AZORG" not in out and "TECH_LV" not in out and "SOMNO" not in out
    assert "29-APR-2026" in out


def test_the_same_recording_always_gets_the_same_code():
    """Deterministisch zijn is een eis: twee analyses van dezelfde nacht moeten
    koppelbaar blijven zonder de naam terug te halen."""
    a = anonymize_patient_field("MRN12345 M 03-MAR-1971 X")
    b = anonymize_patient_field("MRN12345 M 03-MAR-1971 X")
    assert a == b
    assert a != anonymize_patient_field("MRN99999 M 03-MAR-1971 X")


def test_a_classic_edf_free_text_field_is_replaced_wholesale():
    """Zonder EDF+-subvelden is het hele veld vrije tekst en dus verdacht."""
    out = anonymize_patient_field("Pieter Janssens 03/03/1971")
    assert "Janssens" not in out and out.startswith("ANON_")


# ─────────────────────────────────────────────────────────────
#  Eigen studienummer
# ─────────────────────────────────────────────────────────────

def test_an_explicit_study_code_replaces_the_derived_one():
    out = anonymize_patient_field("MRN12345 M 03-MAR-1971 X",
                                  study_code="AZORG-2026-014")
    assert out.split()[0] == "AZORG-2026-014"
    assert "MRN12345" not in out


def test_a_study_code_with_spaces_cannot_break_the_field_structure():
    """Het patiëntveld is spatiegescheiden; een spatie zou een extra subveld
    worden en de EDF+-structuur breken."""
    out = anonymize_patient_field("MRN1 M 03-MAR-1971 X",
                                  study_code="AZORG 2026 014")
    assert len(out.split()) == 4
    assert out.split()[0] == "AZORG2026014"


def test_a_study_code_is_stripped_of_anything_that_is_not_a_code():
    assert sanitize_study_code("  AZORG/2026#014  ") == "AZORG2026014"
    assert sanitize_study_code("Pieter Janssens") == "PieterJanssens"  # blijft fout van de gebruiker
    assert sanitize_study_code("x" * 100) == "x" * 40
    assert sanitize_study_code(None) == ""


def test_an_empty_study_code_falls_back_to_the_derived_pseudonym():
    out = anonymize_patient_field("MRN12345 M 03-MAR-1971 X", study_code="   ")
    assert out.split()[0] == pseudonym("MRN12345")


# ─────────────────────────────────────────────────────────────
#  De header als geheel
# ─────────────────────────────────────────────────────────────

def test_the_header_keeps_its_exact_length():
    out = anonymize_header_bytes(EDF_PLUS)
    assert len(out) == len(EDF_PLUS) == HEADER_LEN


def test_the_bytes_outside_the_two_fields_are_untouched():
    """Alleen 8..168 mag bewegen; versie, datum, tijd en de rest niet."""
    out = anonymize_header_bytes(EDF_PLUS)
    assert out[0:8] == EDF_PLUS[0:8]
    assert out[168:] == EDF_PLUS[168:]


def test_the_startdate_field_can_be_cleared_on_request():
    out = anonymize_header_bytes(EDF_PLUS, keep_startdate=False)
    assert out[168:176].decode().strip() == "01.01.85"


def test_a_truncated_file_is_refused_rather_than_half_written():
    try:
        anonymize_header_bytes(b"0       short")
    except EdfAnonymizeError:
        return
    raise AssertionError("een te korte header hoort geweigerd te worden")


# ─────────────────────────────────────────────────────────────
#  Het bestand
# ─────────────────────────────────────────────────────────────

def test_the_signal_data_is_untouched(tmp_path):
    """De harde eis: één byte verschil verschuift elke sample-offset."""
    payload = bytes(range(256)) * 500          # herkenbare 'signaaldata'
    p = tmp_path / "rec.edf"
    p.write_bytes(EDF_PLUS + payload)

    anonymize_file_in_place(str(p), study_code="AZORG-2026-014")

    data = p.read_bytes()
    assert len(data) == HEADER_LEN + len(payload)
    assert data[HEADER_LEN:] == payload


def test_the_identifiers_are_actually_gone_from_the_file(tmp_path):
    p = tmp_path / "rec.edf"
    p.write_bytes(EDF_PLUS + b"\x00" * 1024)
    after = anonymize_file_in_place(str(p), study_code="AZORG-2026-014")

    raw = p.read_bytes()[:HEADER_LEN].decode("ascii", errors="replace")
    for identifier in ("Janssens", "1971", "MRN12345", "AZORG_SLAAP", "TECH_LV"):
        assert identifier not in raw, identifier
    assert after.patient.startswith("AZORG-2026-014")


def test_reading_identifiers_does_not_change_the_file(tmp_path):
    p = tmp_path / "rec.edf"
    p.write_bytes(EDF_PLUS + b"\x00" * 128)
    before = p.read_bytes()
    ids = read_identifiers(str(p))
    assert p.read_bytes() == before
    assert "Janssens_Pieter" in ids.patient


def test_a_header_that_still_carries_identifiers_says_so():
    assert read_identifiers(EDF_PLUS).has_identifiers is True


def test_an_already_anonymous_header_is_recognised():
    clean = _header("ANON_1A2B3C4D M X X", "Startdate 29-APR-2026 X X X")
    assert read_identifiers(clean).has_identifiers is False


def test_anonymising_twice_is_a_no_op(tmp_path):
    """Idempotent: de tweede keer mag er niets meer veranderen."""
    p = tmp_path / "rec.edf"
    p.write_bytes(EDF_PLUS + b"\x01" * 512)
    anonymize_file_in_place(str(p), study_code="AZORG-2026-014")
    once = p.read_bytes()
    anonymize_file_in_place(str(p), study_code="AZORG-2026-014")
    assert p.read_bytes() == once


def test_a_lowercase_free_text_code_is_still_flagged():
    """Wie zijn 'studienummer' een naam noemt, hoort de waarschuwing te houden."""
    ids = read_identifiers(_header("PieterJanssens M X X",
                                   "Startdate 29-APR-2026 X X X"))
    assert ids.has_identifiers is True


def test_a_leftover_hospital_field_is_flagged_even_with_a_clean_patient():
    ids = read_identifiers(_header("ANON_1A2B3C4D M X X",
                                   "Startdate 29-APR-2026 AZORG_SLAAP X X"))
    assert ids.has_identifiers is True


def test_a_birthdate_left_in_place_is_flagged():
    ids = read_identifiers(_header("ANON_1A2B3C4D M 03-MAR-1971 X",
                                   "Startdate 29-APR-2026 X X X"))
    assert ids.has_identifiers is True


def test_our_own_output_reads_as_clean(tmp_path):
    """De ronde moet sluiten: wat wij schrijven, herkennen wij als anoniem."""
    p = tmp_path / "rec.edf"
    p.write_bytes(EDF_PLUS + b"\x00" * 64)
    anonymize_file_in_place(str(p))
    assert read_identifiers(str(p)).has_identifiers is False

    p2 = tmp_path / "rec2.edf"
    p2.write_bytes(EDF_PLUS + b"\x00" * 64)
    anonymize_file_in_place(str(p2), study_code="AZORG-2026-014")
    assert read_identifiers(str(p2)).has_identifiers is False
