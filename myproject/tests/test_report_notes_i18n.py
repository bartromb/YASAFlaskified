"""Elke rapportnoot moet in vier talen bestaan en zijn placeholders waarmaken.

Een ontbrekende vertaling valt in het rapport terug op de sleutelnaam, en een
verkeerde placeholder klapt met een KeyError midden in de PDF-opbouw — beide
pas zichtbaar bij de patiënt die net die combinatie heeft.
"""

from i18n import TRANSLATIONS

LANGS = ("nl", "fr", "en", "de")

# sleutel -> placeholders die de aanroepplek meegeeft
NOTES = {
    "pdf_dual_sensor_note":         set(),
    "pdf_dual_sensor_no_corrob":    set(),
    "pdf_thermistor_rejected_note": {"therm", "apnea", "agreement"},
    "pdf_single_sensor_note":       {"apnea", "hypopnea"},
    "pdf_hr_unreliable":            {"reason"},
    "pdf_hb_sustained_hypoxemia":   set(),
    "prov_note":                    set(),
    "pdf_hr_p1":                    set(),
    "pdf_hr_p99":                   set(),
    "rpt_sec_provenance":           set(),
}


def test_every_note_exists_in_every_language():
    missing = [f"{k}/{lang}" for k in NOTES for lang in LANGS
               if not (TRANSLATIONS.get(k, {}).get(lang) or "").strip()]
    assert missing == []


def test_every_note_formats_with_the_arguments_the_caller_passes():
    for key, placeholders in NOTES.items():
        kwargs = {p: "X" for p in placeholders}
        for lang in LANGS:
            TRANSLATIONS[key][lang].format(**kwargs)


def test_no_note_expects_an_argument_the_caller_does_not_pass():
    """Een extra {veld} in één taal blijft onopgemerkt tot die taal gekozen wordt."""
    import string
    for key, placeholders in NOTES.items():
        for lang in LANGS:
            used = {f for _, f, _, _ in string.Formatter().parse(TRANSLATIONS[key][lang])
                    if f}
            assert used <= placeholders, f"{key}/{lang} verwacht {used - placeholders}"
