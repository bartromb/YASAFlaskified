"""Het breath-by-breath-paneel mag niet als referentie gelezen worden.

WAT ER MIS GING
---------------
Op de Thaise casus stond in dat paneel "190 apneus" naast NUL gescoorde
apneus. Dat werd gelezen als bewijs van onderdetectie — ook door de assistent
die eraan werkte, een dag lang, tot een meting op MESA liet zien dat de
verhouding tussen deze telling en de gescoorde events op dertig gewone opnames
van **0 % tot 173 %** loopt. Op één opname werden er méér events gescoord dan
hier geteld.

De twee tellers rekenen per ademteug tegen verschillende basislijnen. Ze meten
niet hetzelfde, en naast elkaar zonder uitleg nodigt het paneel uit tot een
conclusie die de cijfers niet dragen.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_de_waarschuwing_staat_in_vier_talen():
    from i18n import TRANSLATIONS

    entry = TRANSLATIONS["pdf_bb_not_a_reference"]
    for taal in ("nl", "fr", "en", "de"):
        assert entry.get(taal), taal
    assert len(set(entry[t] for t in ("nl", "fr", "en", "de"))) == 4


def test_de_waarschuwing_noemt_het_gemeten_bereik():
    """Een waarschuwing zonder getal is een mening; met 0-173 % is het een
    meting die de lezer zelf kan wegen."""
    from i18n import TRANSLATIONS

    en = TRANSLATIONS["pdf_bb_not_a_reference"]["en"]
    assert "0%" in en and "173%" in en, en
    assert "different instrument" in en.lower()


def test_het_paneel_toont_de_waarschuwing():
    with open(os.path.join(MY, "generate_pdf_report.py"), encoding="utf-8") as f:
        bron = f.read()
    i_tab = bron.index('t("pdf_bb_apneas", lang)')
    i_note = bron.index("pdf_bb_not_a_reference")
    assert i_note > i_tab, "de waarschuwing staat niet bij het paneel"
    # en binnen redelijke afstand, niet ergens anders in het bestand
    assert i_note - i_tab < 3000, "de waarschuwing staat te ver van de tabel"
