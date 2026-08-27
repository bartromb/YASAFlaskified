"""De eenheid van een index per uur hoort bij de taal van het rapport.

WAT ER MIS GING
---------------
`/u` is Nederlands voor "per uur". Het stond op 37 plaatsen hardgecodeerd in de
rapportcode, dus ook in Engelse, Franse en Duitse rapporten. Vertaalde strings
deden het wél goed (`"nl": "< 10-15/u", "fr": "< 10-15/h"`), zodat één Engels
rapport beide vormen droeg.

Het viel op toen een zin die ik zelf toevoegde eruit kwam als:

    Severe OSAS without CPAP (AHI 83.5/u ...). On CPAP 1.1/h ...

Twee eenheden in één zin. Een lezer moet dan raden of dat twee grootheden zijn.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TALEN = (("nl", "/u"), ("fr", "/h"), ("en", "/h"), ("de", "/h"))


def test_de_sleutel_bestaat_en_nederlands_wijkt_af():
    from i18n import TRANSLATIONS

    entry = TRANSLATIONS["unit_per_hour"]
    for taal, eenheid in TALEN:
        assert entry[taal] == eenheid, f"{taal}: {entry[taal]}"


def test_de_rapportcode_codeert_de_eenheid_niet_meer_hard():
    """Alleen tekst die het rapport UITSCHRIJFT telt; commentaar en docstrings
    zijn Nederlands en blijven dat."""
    pad = os.path.join(MY, "generate_pdf_report.py")
    with open(pad, encoding="utf-8") as f:
        regels = f.read().split("\n")

    overtreders = []
    for n, regel in enumerate(regels, 1):
        kaal = regel.strip()
        if kaal.startswith("#") or not re.search(r"/u(?![a-zA-Z])", regel):
            continue
        # binnen een string die naar het rapport gaat?
        if re.search(r'["\'][^"\']*/u(?![a-zA-Z])', regel):
            overtreders.append((n, kaal[:70]))
    assert not overtreders, (
        "hardgecodeerde eenheid in uitvoertekst:\n" +
        "\n".join(f"  regel {n}: {t}" for n, t in overtreders))


def test_geen_enkele_vertaling_mengt_de_twee_vormen():
    from i18n import TRANSLATIONS

    fout = []
    for sleutel, entry in TRANSLATIONS.items():
        if not isinstance(entry, dict):
            continue
        for taal, eenheid in TALEN:
            tekst = entry.get(taal)
            if not isinstance(tekst, str):
                continue
            andere = "/h" if eenheid == "/u" else "/u"
            if re.search(re.escape(andere) + r"(?![a-zA-Z])", tekst):
                fout.append(f"{sleutel}/{taal}: {tekst[:60]}")
    assert not fout, "verkeerde eenheid:\n" + "\n".join(fout)


def test_een_engels_rapport_draagt_geen_nederlandse_eenheid():
    """De eigenlijke toets: render de zinnen die het vaakst gelezen worden."""
    from generate_pdf_report import _auto_conclusion

    for taal, eenheid in TALEN:
        tekst = _auto_conclusion({"ahi_total": 22.0}, {}, {}, lang=taal)
        andere = "/h" if eenheid == "/u" else "/u"
        assert eenheid in tekst, f"{taal}: {tekst}"
        assert andere not in tekst, f"{taal} draagt {andere}: {tekst}"


def test_het_nederlandstalige_psg_rapport_blijft_ongemoeid():
    """`generate_psg_report.py` is één Nederlands rapport met hardgecodeerde
    labels ("Drempel", "Ernst", "Bespreking PLM"). Daar is `/u` juist; alleen
    de eenheid vertalen zou het inconsistent maken."""
    pad = os.path.join(MY, "generate_psg_report.py")
    with open(pad, encoding="utf-8") as f:
        bron = f.read()
    assert "Bespreking PLM" in bron and "Drempel" in bron
    assert "unit_per_hour" not in bron


def test_een_ontbrekende_waarde_wordt_geen_letterlijke_None():
    """`ss.get(k, "—")` geeft de default NIET terug als de sleutel bestaat met
    waarde None -- en dat is precies wat het hypoxic-burden-plafond doet boven
    150. Er stond letterlijk "None %·min/u" in een klinisch rapport."""
    pad = os.path.join(MY, "generate_pdf_report.py")
    with open(pad, encoding="utf-8") as f:
        bron = f.read()
    # anker op de CODE, niet op de eerste "%·min" -- die staat in commentaar
    i = bron.index('%·min{_UH}')
    blok = bron[max(0, i - 400):i + 120]
    assert 'ss.get("hypoxic_burden") is not None' in blok, \
        "de burden-regel test niet op None"
    assert "ss.get('hypoxic_burden','—')" not in bron, \
        "de get-met-default staat er nog"
