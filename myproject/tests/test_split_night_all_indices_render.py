"""Bij een split-night hoort ELKE index over het juiste stuk nacht te gaan.

WAAROM DEZE TESTS BESTAAN
-------------------------
v0.36.0 splitste de AHI en liet de rest staan. In het rapport kwam daardoor een
diagnostische AHI te staan, en een paar centimeter lager een arousalindex, een
RDI, een ODI en een PLM-index over de HELE nacht -- inclusief de uren onder
CPAP. Ze lezen als getallen over dezelfde meting, en dat zijn ze niet.

De fout heeft een richting. De therapie werkt, dus het tweede deel drukt elk
van die indices omlaag; wat overblijft laat het diagnostische deel milder lijken
dan het is. Bij een arousalindex van 36/u diagnostisch en 0/u onder therapie
stond er 18/u.

En één laag dieper: psgscoring rekende de saturatie al sinds 0.29.0 per
segment, en geen enkele consument las het. Een index die het rapport niet
haalt, bestaat klinisch niet -- dezelfde klasse als `analysis_warnings` zonder
lezer en de topografiecheck op een niet-bestaande variabele.

Daarom rendert deze test de PDF en leest hem terug.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_pdf_report import generate_pdf_report  # noqa: E402
from i18n import get_translation as t  # noqa: E402

BREUK = 2 * 3600.0


def _pdf_text(path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("pdftotext niet beschikbaar")
    return out.stdout.decode("utf-8", "replace")


def _results(*, met_arousal=True, met_plm=True, met_spo2=True):
    """Een split-night waarin de therapie werkt: alles zakt na het breekpunt."""
    ev = [{"type": "obstructive", "onset_s": 60.0 + 100 * i, "duration_s": 20.0,
           "stage": "N2", "epoch": int((60 + 100 * i) // 30), "confidence": 0.9,
           "desaturation_pct": 5.0, "flow_reduction": 90.0} for i in range(70)]
    ev += [{"type": "hypopnea", "onset_s": BREUK + 300.0 + 600 * i,
            "duration_s": 20.0, "stage": "N2",
            "epoch": int((BREUK + 300 + 600 * i) // 30), "confidence": 0.8,
            "desaturation_pct": 4.0, "flow_reduction": 50.0} for i in range(5)]

    sn = {
        "detected": True, "breakpoint_s": BREUK, "method": "manual",
        "segments": {
            "diagnostic": {"sleep_h": 2.0, "n_events": 70, "n_uncertain": 0,
                           "ahi": 35.0, "ahi_incl_uncertain": 35.0,
                           "reliable": True, "uncertain_fraction": 0.0},
            "therapeutic": {"sleep_h": 5.0, "n_events": 5, "n_uncertain": 0,
                            "ahi": 1.0, "ahi_incl_uncertain": 1.0,
                            "reliable": True, "uncertain_fraction": 0.0},
        },
        "rdi": {
            "diagnostic": {"sleep_h": 2.0, "n_rera": 10, "rera_index": 5.0,
                           "rdi": 40.0, "reliable": True},
            "therapeutic": {"sleep_h": 5.0, "n_rera": 1, "rera_index": 0.2,
                            "rdi": 1.2, "reliable": True},
        },
    }
    if met_arousal:
        sn["arousal"] = {
            "diagnostic": {"sleep_h": 2.0, "n_arousals": 72,
                           "arousal_index": 36.0, "n_respiratory": 60,
                           "n_spontaneous": 12,
                           "respiratory_arousal_index": 30.0,
                           "spontaneous_arousal_index": 6.0, "reliable": True},
            "therapeutic": {"sleep_h": 5.0, "n_arousals": 0,
                            "arousal_index": 0.0, "n_respiratory": 0,
                            "n_spontaneous": 0,
                            "respiratory_arousal_index": 0.0,
                            "spontaneous_arousal_index": 0.0, "reliable": True},
        }
    if met_plm:
        sn["plm"] = {
            "diagnostic": {"sleep_h": 2.0, "n_plm": 44, "plm_index": 22.0,
                           "reliable": True},
            "therapeutic": {"sleep_h": 5.0, "n_plm": 10, "plm_index": 2.0,
                            "reliable": True},
        }
    sn["snore"] = {"diagnostic": {"snore_index": 41.0},
                   "therapeutic": {"snore_index": 2.0}}
    sn["position"] = {
        "diagnostic": {"ahi_per_pos": {"supine": 52.0, "left": 8.0},
                       "sleep_time_min": {"supine": 100.0, "left": 20.0}},
        "therapeutic": {"ahi_per_pos": {"supine": 2.0, "left": 0.5},
                        "sleep_time_min": {"supine": 60.0, "left": 240.0}},
    }
    if met_spo2:
        sn["spo2"] = {
            "diagnostic": {"odi_3pct": 33.0, "pct_below_90": 14.0,
                           "min_spo2": 71, "baseline_spo2": 92},
            "therapeutic": {"odi_3pct": 1.5, "pct_below_90": 0.4,
                            "min_spo2": 89, "baseline_spo2": 96},
        }

    return {
        "patient_info": {"lang": "nl"},
        "pneumo": {
            "split_night": sn,
            "respiratory": {
                "success": True, "events": ev,
                "summary": {
                    "ahi_total": 10.7, "n_ah_total": len(ev),
                    "n_obstructive": 70, "n_central": 0, "n_mixed": 0,
                    "n_hypopnea": 5, "obstructive_index": 10.0,
                    "central_index": 0.0, "mixed_index": 0.0,
                    "hypopnea_index": 0.7, "rdi": 12.3, "rera_index": 1.6,
                    "n_rera": 11,
                },
            },
            "spo2": {"success": True,
                     "summary": {"mean_spo2": 94, "baseline_spo2": 95,
                                 "min_spo2": 71, "pct_below_90": 4.4,
                                 "odi_3pct": 10.5, "odi_4pct": 7.0}},
            "arousal": {"success": True,
                        "summary": {"arousal_index": 18.0,
                                    "respiratory_arousal_index": 15.0,
                                    "spontaneous_arousal_index": 3.0}},
            "plm": {"success": True,
                    "summary": {"plm_index": 7.7, "lm_index": 12.0,
                                "n_plm": 54}},
        },
    }


@pytest.fixture(scope="module")
def tekst(tmp_path_factory):
    out = tmp_path_factory.mktemp("pdf") / "split.pdf"
    generate_pdf_report(_results(), str(out), lang="nl")
    return _pdf_text(out)


# ── De getallen zelf ──────────────────────────────────────────────────────

@pytest.mark.parametrize("waarde,wat", [
    ("36.0", "arousalindex diagnostisch"),
    ("30.0", "respiratoire arousalindex diagnostisch"),
    ("40.0", "RDI diagnostisch"),
    ("33.0", "ODI3 diagnostisch"),
    ("22.0", "PLM-index diagnostisch"),
    ("41.0", "snurkindex diagnostisch"),
    ("52.0", "positie-AHI rugligging diagnostisch"),
])
def test_het_diagnostische_getal_staat_in_het_rapport(tekst, waarde, wat):
    """Zonder deze getallen leest de lezer het nachtgemiddelde als de meting
    waarop de diagnose rust."""
    assert waarde in tekst, f"{wat} ({waarde}) ontbreekt in de PDF"


def test_beide_helften_staan_op_dezelfde_regel(tekst):
    """Naast elkaar, niet in twee losse tabellen: het verschil IS de uitslag."""
    regel = next((ln for ln in tekst.splitlines()
                  if "36.0" in ln and t("pdf_arousal_index", "nl")[:7] in ln), None)
    assert regel, "de arousalrij staat niet in de split-tabel"
    assert "0.0" in regel, f"de therapiewaarde ontbreekt op die regel: {regel!r}"


def test_de_kolomkoppen_scheiden_de_twee_helften(tekst):
    assert t("pdf_split_col_diag", "nl") in tekst
    assert t("pdf_split_col_ther", "nl") in tekst


def test_de_lezer_krijgt_te_horen_waarom_dit_er_staat(tekst):
    """Een tabel met twee kolommen verklaart zichzelf niet."""
    kop = t("pdf_split_other_note", "nl")[:40]
    assert kop in tekst


def test_het_nachtgemiddelde_blijft_ook_staan(tekst):
    """Niet vervangen maar ernaast: de nacht-AHI is wat AASM voorschrijft."""
    assert "18.0" in tekst, "de nacht-arousalindex hoort zichtbaar te blijven"


# ── Wat er NIET moet staan ────────────────────────────────────────────────

def test_zonder_arousaldata_geen_lege_arousalrij(tmp_path):
    """Bij polygrafie bestaan er geen arousals. Een rij met '—' suggereert een
    gemeten nul; hij hoort te ontbreken."""
    out = tmp_path / "geen_arousal.pdf"
    generate_pdf_report(_results(met_arousal=False, met_plm=False),
                        str(out), lang="nl")
    txt = _pdf_text(out)
    kop = t("pdf_split_other_hdr", "nl")
    assert kop in txt, "de RDI-rij hoort er nog wel te staan"
    regels = [ln for ln in txt.splitlines() if kop in ln]
    assert "22.0" not in txt, "PLM-index zonder data"


def test_zonder_split_night_verschijnt_de_tabel_niet(tmp_path):
    r = _results()
    r["pneumo"].pop("split_night")
    out = tmp_path / "geen_split.pdf"
    generate_pdf_report(r, str(out), lang="nl")
    assert t("pdf_split_other_hdr", "nl") not in _pdf_text(out)


# ── Vier talen ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("taal", ["nl", "fr", "en", "de"])
def test_de_nieuwe_sleutels_bestaan_in_vier_talen(taal):
    from i18n import TRANSLATIONS
    for sleutel in ("pdf_split_col_diag", "pdf_split_col_ther",
                    "pdf_split_other_hdr", "pdf_split_other_note"):
        assert taal in TRANSLATIONS[sleutel], f"{sleutel} mist {taal}"
        assert TRANSLATIONS[sleutel][taal].strip(), f"{sleutel}/{taal} is leeg"


@pytest.mark.parametrize("taal", ["fr", "en", "de"])
def test_het_rapport_rendert_in_elke_taal(tmp_path, taal):
    r = _results()
    r["patient_info"]["lang"] = taal
    out = tmp_path / f"{taal}.pdf"
    generate_pdf_report(r, str(out), lang=taal)
    txt = _pdf_text(out)
    assert t("pdf_split_col_diag", taal) in txt
    assert "36.0" in txt
    assert "■" not in txt.split(t("pdf_split_col_diag", taal))[-1][:400], (
        "font-fallback in de nieuwe tabel")


def test_de_houding_staat_naast_de_therapie(tekst):
    """De klinische valkuil: diagnostisch op de rug, onder therapie op de zij.

    Dan verklaart de HOUDING een deel van de daling die anders volledig aan de
    CPAP wordt toegeschreven. Eén positie-AHI over de hele nacht laat dat niet
    zien.
    """
    regel = next((ln for ln in tekst.splitlines()
                  if "AHI supine" in ln and "52.0" in ln), None)
    assert regel, "de positie-AHI per helft staat niet in de split-tabel"
    assert "2.0" in regel, f"de therapiewaarde ontbreekt: {regel!r}"
