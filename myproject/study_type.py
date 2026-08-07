"""Wat voor onderzoek is dit — één plek, want drie kopieën lopen uiteen.

De studietypes zijn `diagnostic_psg`, `diagnostic_pg`, `titration_psg_cpap`,
`titration_pg_cpap` en `titration_pg_mra`. Het verschil tussen polysomnografie
en polygrafie zit in één letter, en juist die letter bepaalt of er een EEG is,
of er gestageerd wordt, en of de index over slaaptijd of over registratietijd
gaat.

Er stond `"_pg_" in study_type` op drie plaatsen. Die toets mist
`diagnostic_pg` — geen sluitende underscore — waardoor een diagnostische
polygrafie stilzwijgend als polysomnografie behandeld zou worden: staging op
een kanaal dat geen EEG is, en een AHI-label boven een REI-getal. Splitsen op
underscore en op het hele woord toetsen doet dat niet.
"""

from __future__ import annotations

#: Alles wat in de studietype-keuzelijst kan staan.
STUDY_TYPES = (
    "diagnostic_psg",
    "diagnostic_pg",
    "titration_psg_cpap",
    "titration_pg_cpap",
    "titration_pg_mra",
)


def is_polygraphy(study_type: str | None) -> bool:
    """Polygrafie: geen EEG, dus geen slaapstaging en een index over TIB."""
    return "pg" in str(study_type or "").split("_")


def is_titration(study_type: str | None) -> bool:
    """Titratie: residuele events onder therapie."""
    return "titration" in str(study_type or "").split("_")


def requires_eeg_channel(study_type: str | None) -> bool:
    """Alleen een polysomnografie heeft een EEG-kanaal nodig.

    Zolang dit voor polygrafie ook gold, vulde de gebruiker er iets anders in
    om het formulier voorbij te komen — op een echte opname de neusdruk. YASA
    stageerde daarop, de artefactdetector keurde alle 1078 epochs af, en de
    noemer van elke index werd nul: 81 hypopnees kwamen als "REI 81000,0/u —
    Ernstig SAS" in het rapport.
    """
    return not is_polygraphy(study_type)
