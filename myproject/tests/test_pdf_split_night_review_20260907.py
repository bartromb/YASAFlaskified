"""Rendertests voor de tweede rapportreview van 2026-09-07 (80722e9c, EN, split-night).

De 0.38.2-review repareerde Engels-in-Nederlands; dit Engelse productierapport
toonde de spiegelfout (Nederlandse fragmenten in een Engels rapport) plus drie
gaten die alleen op een split-night zichtbaar worden: fenotypes beoordeeld
over twee onvergelijkbare nachthelften, een diagnostisch deel van 51 minuten
zonder vlag, en 25 % artefact-epochs zonder vlag. Zelfde methode als de
vorige ronde: echt renderen, tekstlaag teruglezen, eerst rood zien.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_pdf_report import generate_pdf_report  # noqa: E402


def _pdf_text(path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("pdftotext niet beschikbaar")
    return out.stdout.decode("utf-8", "replace")


def _render(results, tmp_path, lang="nl", naam="uit.pdf"):
    out = tmp_path / naam
    generate_pdf_report(results, str(out), lang=lang)
    return _pdf_text(out)


def _results(*, split=True, diag_sleep_h=0.85, artifact_pct=25.19,
             edf_header_naam=None, form_naam=None):
    """Naar productierapport 80722e9c: split-night met kort diagnostisch deel."""
    events = [{"type": "obstructive", "onset_s": 100.0 + 40 * i,
               "duration_s": 20.0, "stage": "N2",
               "epoch": int((100.0 + 40 * i) // 30), "confidence": 0.7,
               "desaturation_pct": 4.0, "flow_reduction": 90.0}
              for i in range(76)]
    rsum = {"ahi_total": 13.7, "n_ah_total": len(events),
            "n_obstructive": 67, "n_central": 0, "n_mixed": 5,
            "n_hypopnea": 4, "obstructive_index": 12.1,
            "central_index": 0.0, "mixed_index": 0.9, "hypopnea_index": 0.7,
            "ahi_rem": 1.9, "ahi_nrem": 18.3, "rem_min": 98.0,
            "nrem_min": 332.0, "ahi_rem_reliable": True,
            "n_csr_flagged": 29, "ahi_csr_corrected": 8.5,
            "n_low_conf_noise": 0, "n_low_conf_borderline": 14,
            "ahi_excl_noise": 13.6,
            "phenotypes": {
                "positional_osa": {
                    "flag": True, "ahi_supine": 38.6, "ahi_non_supine": 13.9,
                    "supine_non_supine_ratio": 2.8,
                    "positional_therapy_candidate": True},
                "rem_predominant": {"flag": False, "rem_ahi": 1.9,
                                    "nrem_ahi": 18.3, "rem_nrem_ratio": 0.1},
            }}
    res = {
        "patient_info": ({"patient_name": form_naam} if form_naam else {}),
        "meta": {"eeg_channel": "C4", "eog_channel": "LEOG",
                 "emg_channel": "Chin"},
        "edf_channels": ["C4", "LEOG", "Chin", "Flow", "SAO2_4"],
        "dc_highpass": {"applied": True, "n_channels": 11,
                        "max_offset_uv": 173323.0, "cutoff_hz": 0.30,
                        "channels": ["F3", "C3"]},
        "artifacts": {"success": True, "summary": {
            "artifact_percent": artifact_pct, "n_artifact_epochs": 228,
            "n_total_epochs": 905}},
        "pneumo": {
            "meta": {"all_channels": ["C4", "Chin", "Flow", "SAO2_4"],
                     "scoring_profile": "aasm_v3_rec",
                     "channels_used": {"eeg": "C4"},
                     "patient_info": ({"name": edf_header_naam}
                                      if edf_header_naam else {})},
            "respiratory": {"success": True, "events": events,
                            "summary": rsum,
                            "n_local_baseline_rejected": 87},
            # Houdingscodering HERKEND: de POSA-claim is op zichzelf
            # toegestaan — alleen de split-night mag hem hier stoppen.
            "position": {"success": True, "summary": {
                "position_mapping_method": "coded",
                "ahi_per_pos": {"Prone": 11.4, "Left": 1.6},
                "sleep_time_min": {"Prone": 300.0, "Left": 30.0},
                "min_minutes_for_index": 15.0}},
            "spo2": {"success": True, "summary": {
                "mean_spo2": 93.2, "baseline_spo2": 96.0, "min_spo2": 66.0,
                "pct_below_90": 16.4, "odi_3pct": 25.3, "odi_4pct": 24.6,
                "hypoxic_burden": None, "hypoxic_burden_method": "percentile",
                "total_sleep_s": 430 * 60}},
        },
    }
    if split:
        res["pneumo"]["split_night"] = {
            "detected": True, "breakpoint_s": 8100.0,
            "method": "flow_amplitude+spo2_baseline",
            "segments": {
                "diagnostic": {"reliable": True, "sleep_h": diag_sleep_h,
                               "ahi": 83.5, "ahi_incl_uncertain": 83.5,
                               "uncertain_fraction": 0.0},
                "therapeutic": {"reliable": True, "sleep_h": 4.7,
                                "ahi": 1.1, "ahi_incl_uncertain": 1.1,
                                "uncertain_fraction": 0.0}},
            "summaries": {
                "diagnostic": {"ahi_total": 83.5, "ahi_incl_uncertain": 83.5},
                "therapeutic": {"ahi_total": 1.1, "ahi_incl_uncertain": 1.1}},
        }
    return res


# ── 1. Nederlandse fragmenten in een Engels rapport ──────────────────────

def test_engels_rapport_zonder_nederlandse_fragmenten(tmp_path):
    """80722e9c toonde "(gedetecteerd)", "11 kanalen, offset tot", "87
    afgewezen", "0 ruis" en "A+H totaal" — hardgecodeerd Nederlands."""
    txt = _render(_results(), tmp_path, lang="en")
    for nl in ("gedetecteerd", "kanalen", "afgewezen", " ruis", "A+H totaal"):
        assert nl not in txt, f"Nederlands fragment in Engels rapport: {nl!r}"
    assert "(detected)" in txt
    assert "channels, offset up to" in txt
    assert "87 rejected" in txt
    assert "noise" in txt
    assert "A+H total" in txt


def test_nederlands_rapport_blijft_nederlands(tmp_path):
    txt = _render(_results(), tmp_path, lang="nl")
    assert "(gedetecteerd)" in txt
    assert "87 afgewezen" in txt
    assert "A+H totaal" in txt


# ── 2. Fenotypes over twee onvergelijkbare nachthelften ──────────────────

def test_split_night_fenotypes_niet_beoordeeld(tmp_path):
    """De ernstkolom zegt "—" op een split-night, maar REM-predominant en
    POSA werden gewoon beoordeeld over de hele nacht — de REM lag onder
    CPAP, dus zelfs het "nee" is onbewijsbaar."""
    txt = _render(_results(split=True), tmp_path, lang="nl")
    assert "vs non-supine" not in txt
    assert "vs NREM" not in txt, "REM-predominant-claim over de hele nacht"
    assert "niet beoordeelbaar op een split-night" in txt
    assert "positietherapie" not in txt.lower()
    assert ", positioneel" not in txt.lower()


def test_zonder_split_fenotypes_gewoon_beoordeeld(tmp_path):
    txt = _render(_results(split=False), tmp_path, lang="nl")
    assert "vs non-supine" in txt
    assert "niet beoordeelbaar op een split-night" not in txt


def test_split_night_stadium_ahi_krijgt_noot(tmp_path):
    """AHI REM 1.9 / AHI NREM 18.3 zijn nachtwaarden inclusief de uren onder
    therapie; zonder noot lezen ze als diagnose."""
    txt = _render(_results(split=True), tmp_path, lang="nl")
    assert "inclusief de uren onder therapie" in txt


# ── 3. Kort diagnostisch deel ────────────────────────────────────────────

def test_kort_diagnostisch_deel_wordt_aandachtspunt(tmp_path):
    txt = _render(_results(diag_sleep_h=0.85), tmp_path, lang="nl")
    assert "Kort diagnostisch deel (51 min" in txt


def test_lang_diagnostisch_deel_geen_aandachtspunt(tmp_path):
    txt = _render(_results(diag_sleep_h=3.0), tmp_path, lang="nl")
    assert "Kort diagnostisch deel" not in txt


# ── 4. Hoog artefactaandeel ──────────────────────────────────────────────

def test_hoog_artefactaandeel_wordt_aandachtspunt(tmp_path):
    txt = _render(_results(artifact_pct=25.19), tmp_path, lang="nl")
    assert "Hoog artefactaandeel (25.2" in txt.replace(",", ".")


def test_laag_artefactaandeel_geen_aandachtspunt(tmp_path):
    txt = _render(_results(artifact_pct=5.0), tmp_path, lang="nl")
    assert "Hoog artefactaandeel" not in txt


# ── 5. Headerjunk wordt geen naam ────────────────────────────────────────

def test_vrije_headertekst_wordt_geen_naam(tmp_path):
    """80722e9c: Naam = "20260629, Anonymous01 Height 169 cm. We" — het
    vrije-tekstveld van de recorder, afgekapt op de 80-byte headergrens,
    als achternaam-komma-voornaam opgediend."""
    txt = _render(_results(
        edf_header_naam="20260629 Anonymous01 Height 169 cm. We"),
        tmp_path, lang="nl")
    assert "20260629," not in txt
    assert "Height 169" not in txt


def test_echte_headernaam_blijft_werken(tmp_path):
    txt = _render(_results(edf_header_naam="Peeters Jan"), tmp_path,
                  lang="nl")
    assert "Peeters, Jan" in txt


# ── 6. KPI-label ─────────────────────────────────────────────────────────

def test_kpi_label_diagnostische_slaap(tmp_path):
    txt = _render(_results(), tmp_path, lang="en")
    assert "diagnostic sleep" in txt
    assert "sleep diagnostic" not in txt
