"""EDF/EDF+-headers anonimiseren — gedeelde logica voor beide GUI-routes.

De EDF-header is een vaste ASCII-blok van 256 bytes. Alleen twee velden dragen
identificerende gegevens:

    offset   8, 80 bytes  patiëntveld   — code, geslacht, geboortedatum, naam
    offset  88, 80 bytes  opnameveld    — startdatum, ziekenhuis, technicus

De signaaldata blijft byte voor byte ongemoeid: er wordt uitsluitend binnen
die 168 bytes geschreven, en de veldlengtes blijven exact gelijk, anders
verschuift elke sample-offset in het bestand.

Twee routes gebruiken dit, en ze moeten precies dezelfde regels volgen —
anders levert dezelfde opname twee verschillende pseudoniemen op:

  * de browser, vóór verzenden (`static/js/edf_anonymize.js`, dezelfde regels
    in JavaScript);
  * de server, na het opladen, wanneer de gebruiker dat ter plekke kiest.

Afgeleid van `anonymize_edf.py` in de repo-root, dat hetzelfde doet vanaf de
opdrachtregel.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

PATIENT_OFFSET, PATIENT_LEN = 8, 80
RECORDING_OFFSET, RECORDING_LEN = 88, 80
DATE_OFFSET, DATE_LEN = 168, 8
HEADER_LEN = 256

DATE_UNKNOWN = "01.01.85"
"""EDF-conventie voor een onbekende startdatum."""


class EdfAnonymizeError(Exception):
    pass


@dataclass
class HeaderIdentifiers:
    """Wat er nu in de header staat — om de gebruiker te tonen wat hij weggeeft."""

    patient: str
    recording: str
    startdate: str

    @property
    def has_identifiers(self) -> bool:
        """Heeft deze header nog de vorm van een niet-geanonimiseerd bestand?

        Wat hier te bepalen valt is de VORM, niet de inhoud: of de velden eruit
        zien zoals onze anonimisatie ze achterlaat (``code geslacht X X`` en
        ``Startdate datum X X X``). Of de code zelf een naam is, kan dit niet
        weten — daarom waarschuwt het hint-veld in de UI daarvoor.

        Bij twijfel luidt het antwoord "identificeerbaar". Een valse melding
        kost één overbodige klik op een idempotente knop; een gemiste melding
        laat een patiëntnaam op de server staan.
        """
        return not (_patient_is_anonymised(self.patient)
                    and _recording_is_anonymised(self.recording))


def _looks_like_a_code(token: str) -> bool:
    """Een pseudoniem of studienummer, geen vrije tekst.

    Heuristiek, en bewust een strenge: onze eigen output is hoofdletters,
    cijfers en `_-.`, terwijl namen vrijwel altijd kleine letters bevatten.
    Wie zijn studienummer "PieterJanssens" noemt krijgt hier terecht een
    waarschuwing.
    """
    return bool(token) and not any(c.islower() for c in token)


def _patient_is_anonymised(field: str) -> bool:
    parts = field.split()
    if not parts or field.strip().upper() == "X":
        return True
    if len(parts) == 1:
        return _looks_like_a_code(parts[0])
    if len(parts) >= 4:
        # code geslacht X X — geboortedatum en naam moeten plaatshouders zijn.
        return (_looks_like_a_code(parts[0])
                and all(p.upper() == "X" for p in parts[2:]))
    return False


def _recording_is_anonymised(field: str) -> bool:
    parts = field.split()
    if not parts or field.strip().upper() == "X":
        return True
    if parts[0].lower() == "startdate" and len(parts) >= 2:
        # Startdate datum X X X — ziekenhuis, technicus en admincode weg.
        return all(p.upper() == "X" for p in parts[2:])
    return False


def _read(data: bytes, offset: int, length: int) -> str:
    return data[offset:offset + length].decode("ascii", errors="replace").strip()


def _pad(value: str, length: int) -> bytes:
    return value.encode("ascii", errors="replace")[:length].ljust(length)


def pseudonym(original: str, prefix: str = "ANON") -> str:
    """Deterministisch pseudoniem: dezelfde opname geeft altijd dezelfde code.

    Deterministisch zijn is hier een eis, geen gemak: twee analyses van dezelfde
    nacht moeten aan elkaar te koppelen zijn zonder de naam terug te halen.
    """
    digest = hashlib.sha256(original.encode("utf-8", errors="replace")).hexdigest()
    return f"{prefix}_{digest[:8].upper()}"


STUDY_CODE_MAX = 40
"""Het patiëntveld is 80 bytes en moet ook geslacht en twee plaatshouders
dragen; een label langer dan dit past niet zonder de rest weg te duwen."""


def sanitize_study_code(code: str | None) -> str:
    """Alleen letters, cijfers en `_-.` — de rest is opmaak of, erger, een naam.

    Spaties eruit, want het patiëntveld is spatiegescheiden: een label met een
    spatie zou een extra subveld worden en de EDF+-structuur breken.
    """
    if not code:
        return ""
    cleaned = "".join(c for c in str(code).strip()
                      if c.isascii() and (c.isalnum() or c in "_-."))
    return cleaned[:STUDY_CODE_MAX]


def anonymize_patient_field(original: str, prefix: str = "ANON",
                            keep_sex: bool = True,
                            study_code: str | None = None) -> str:
    """EDF+ patiëntveld: 'code geslacht geboortedatum naam'.

    Geslacht mag blijven — het is geen identificator en het is een
    subgroepvariabele in het protocol. Geboortedatum en naam verdwijnen.

    ``study_code`` zet er een eigen nummer of label neer in plaats van het
    afgeleide pseudoniem. Dat is het gebruikelijke geval bij een studie: de
    koppeling naar de patiënt staat dan in het studieregister, niet in het
    bestand. Zonder code valt hij terug op het deterministische pseudoniem,
    zodat twee opnames van dezelfde nacht nog steeds aan elkaar te koppelen
    zijn.
    """
    code_override = sanitize_study_code(study_code)
    parts = original.split()
    if len(parts) >= 4:
        code = parts[0]
        sex = parts[1] if keep_sex and parts[1].upper() in ("M", "F", "X") else "X"
        if code_override:
            anon_code = code_override
        else:
            anon_code = pseudonym(code, prefix) if code.upper() != "X" else "X"
        return f"{anon_code} {sex.upper()} X X"
    if code_override:
        return code_override
    if original.strip() and original.strip().upper() != "X":
        return pseudonym(original, prefix)
    return "X"


def anonymize_recording_field(original: str, keep_startdate: bool = True) -> str:
    """EDF+ opnameveld: 'Startdate dd-MMM-yyyy admincode technicus apparatuur'.

    De startdatum mag blijven staan: zonder die datum is een opname niet meer
    aan het klinische dossier te koppelen, en hij staat sowieso al in het
    aparte datumveld op offset 168. Ziekenhuis, technicus en admincode gaan weg.
    """
    parts = original.split()
    if len(parts) >= 2 and parts[0].lower() == "startdate":
        startdate = parts[1] if keep_startdate else "X"
        return f"Startdate {startdate} X X X"
    return "X"


def read_identifiers(path_or_bytes) -> HeaderIdentifiers:
    """Lees de drie headervelden zonder het bestand te wijzigen."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        head = bytes(path_or_bytes[:HEADER_LEN])
    else:
        with open(path_or_bytes, "rb") as fh:
            head = fh.read(HEADER_LEN)
    if len(head) < HEADER_LEN:
        raise EdfAnonymizeError("bestand is korter dan een EDF-header (256 bytes)")
    return HeaderIdentifiers(
        patient=_read(head, PATIENT_OFFSET, PATIENT_LEN),
        recording=_read(head, RECORDING_OFFSET, RECORDING_LEN),
        startdate=_read(head, DATE_OFFSET, DATE_LEN),
    )


def anonymize_header_bytes(head: bytes, prefix: str = "ANON",
                           keep_sex: bool = True,
                           keep_startdate: bool = True,
                           study_code: str | None = None) -> bytes:
    """Geef een nieuwe header van exact dezelfde lengte terug."""
    if len(head) < HEADER_LEN:
        raise EdfAnonymizeError("bestand is korter dan een EDF-header (256 bytes)")
    out = bytearray(head)
    patient = anonymize_patient_field(
        _read(head, PATIENT_OFFSET, PATIENT_LEN), prefix, keep_sex, study_code)
    recording = anonymize_recording_field(
        _read(head, RECORDING_OFFSET, RECORDING_LEN), keep_startdate)
    out[PATIENT_OFFSET:PATIENT_OFFSET + PATIENT_LEN] = _pad(patient, PATIENT_LEN)
    out[RECORDING_OFFSET:RECORDING_OFFSET + RECORDING_LEN] = _pad(recording, RECORDING_LEN)
    if not keep_startdate:
        out[DATE_OFFSET:DATE_OFFSET + DATE_LEN] = _pad(DATE_UNKNOWN, DATE_LEN)
    if len(out) != len(head):
        raise EdfAnonymizeError("header van lengte veranderd — geweigerd")
    return bytes(out)


def anonymize_file_in_place(path: str, prefix: str = "ANON",
                            keep_sex: bool = True,
                            keep_startdate: bool = True,
                            study_code: str | None = None) -> HeaderIdentifiers:
    """Herschrijf de header van een bestaand EDF. Retourneert de nieuwe velden.

    Schrijft precies 256 bytes op offset 0 — geen kopie, geen hernoemen, geen
    herschrijven van de signaaldata. Een half geslaagde kopieeractie op een
    bestand van enkele GB is een groter risico dan deze ene write.
    """
    if not os.path.exists(path):
        raise EdfAnonymizeError(f"bestand bestaat niet: {path}")
    with open(path, "r+b") as fh:
        head = fh.read(HEADER_LEN)
        new_head = anonymize_header_bytes(
            head, prefix, keep_sex, keep_startdate, study_code)
        if new_head != head:
            fh.seek(0)
            fh.write(new_head)
            fh.flush()
            os.fsync(fh.fileno())
    return read_identifiers(path)
