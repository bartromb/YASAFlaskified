"""Rendertests voor de rapportreview van 2026-09-07 (slaaprapport_91a67fa3).

Elke toets hier komt uit een bevinding op een ECHT productierapport (0.38.0):
het rapport sprak zichzelf tegen (POSA beweerd én onbepaalbaar verklaard),
het kanaalpaneel noemde de analyse-subset "het EDF-bestand", er lekten
i18n-placeholders en Engelse fragmenten in een Nederlands rapport, en twee
labels beschreven iets anders dan het getal eronder. Alle toetsen renderen de
PDF echt en lezen de tekstlaag terug — de les van de scoorder-noot: een veld
zonder lezer is niets, en een lezer toets je op het leveringsoppervlak.
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


def _render(results, tmp_path, naam="uit.pdf"):
    out = tmp_path / naam
    generate_pdf_report(results, str(out), lang="nl")
    return _pdf_text(out)


def _results(*, pos_method="levels", posa_flag=True, vb=None,
             hypoxic_burden=None, hb_method="percentile",
             profiel="aasm_v3_rec", edf_channels=None,
             eog_ch="EOG1:A2", spindles=False, timeline=None):
    """Een minimale maar realistische resultatenstructuur (naar 91a67fa3)."""
    events = [{"type": "hypopnea", "onset_s": 100.0 + 60 * i,
               "duration_s": 20.0, "stage": "N2",
               "epoch": int((100.0 + 60 * i) // 30), "confidence": 0.9,
               "desaturation_pct": 4.0, "flow_reduction": 55.0}
              for i in range(30)]
    rsum = {"ahi_total": 22.0, "n_ah_total": len(events),
            "n_obstructive": 0, "n_central": 0, "n_mixed": 0,
            "n_hypopnea": len(events), "obstructive_index": 0.0,
            "central_index": 0.0, "mixed_index": 0.0, "hypopnea_index": 22.0,
            "ahi_rem": 18.1, "ahi_nrem": 22.9, "rem_min": 64.0,
            "nrem_min": 257.0, "ahi_rem_reliable": True,
            "n_fri": 86, "fri_index": 16.2,
            "phenotypes": {
                "positional_osa": {
                    "flag": posa_flag, "ahi_supine": 38.6,
                    "ahi_non_supine": 13.9, "supine_non_supine_ratio": 2.8,
                    "positional_therapy_candidate": True},
                "rem_predominant": {"flag": False, "rem_ahi": 18.1,
                                    "nrem_ahi": 22.9, "rem_nrem_ratio": 0.8},
            }}
    if vb is not None:
        rsum["ventilatory_burden"] = vb
    spo2_sum = {"mean_spo2": 92.0, "baseline_spo2": 96.0, "min_spo2": 75.8,
                "pct_below_90": 19.5, "odi_3pct": 19.8, "odi_4pct": 14.0,
                "hypoxic_burden": hypoxic_burden,
                "hypoxic_burden_method": hb_method,
                "time_95_100_min": 55.6, "pct_95_100": 17.3,
                "time_90_95_min": 184.7, "pct_90_95": 57.5,
                "time_80_90_min": 62.5, "pct_80_90": 19.5,
                "time_70_80_min": 0.2, "pct_70_80": 0.1,
                "time_below_70_min": 0.0, "total_sleep_s": 321 * 60}
    res = {
        "patient_info": {"lang": "nl"},
        "meta": {"eeg_channel": "C4", "eog_channel": eog_ch,
                 "emg_channel": "EMG1"},
        "pneumo": {
            "meta": {"all_channels": ["C4", "EMG1", "Pressure Flow",
                                      "Flow Th.", "SpO2"],
                     "scoring_profile": profiel,
                     "channels_used": {"eeg": "C4"}},
            "respiratory": {"success": True, "events": events,
                            "summary": rsum},
            "position": {"success": True, "summary": {
                "position_mapping_method": pos_method,
                "ahi_per_pos": {"Supine": 38.6, "Left": 5.6},
                "sleep_time_min": {"Supine": 120.0, "Left": 90.0},
                "min_minutes_for_index": 15.0}},
            "spo2": {"success": True, "summary": spo2_sum},
            "arousal": {"success": True, "summary": {
                "arousal_index": 21.7, "respiratory_arousal_index": 8.4,
                "spontaneous_arousal_index": 13.3, "plm_arousal_index": 1.7,
                "n_respiratory_arousals": 45, "n_spontaneous_arousals": 71}},
            "plm": {"success": True, "summary": {
                "n_lm_total": 1486, "n_lm_sleep": 508,
                "n_resp_associated": 8, "n_plm": 81, "n_plm_series": 18,
                "plm_index": 15.2, "plm_severity": "moderate"}},
        },
    }
    if edf_channels is not None:
        res["edf_channels"] = edf_channels
    if spindles:
        res["spindles"] = {"success": True, "total_spindles": 9, "summary": [
            {"Channel": "C3", "Count": 5, "Duration": 0.76,
             "Frequency": 13.3},
            {"Channel": "C4", "Count": 4, "Duration": 0.78,
             "Frequency": 13.4}]}
    if timeline is not None:
        res["hypnogram_timeline"] = {"timeline": [{"stage": s,
                                                   "epoch": i}
                                                  for i, s in
                                                  enumerate(timeline)]}
    return res


# ── 1. POSA: beweren én onbepaalbaar verklaren kan niet allebei ──────────

def test_posa_niet_geclaimd_bij_onherkende_houdingscodering(tmp_path):
    """Rapport 91a67fa3: de caveat zei "POSA-fenotype niet bepaalbaar", maar
    voorpagina, fenotypeblok en Besluit beweerden POSA alle drie."""
    txt = _pdf_text_low = _render(_results(pos_method="levels"), tmp_path)
    assert "vs non-supine" not in txt, (
        "een supine/non-supine-claim hoort niet in een rapport waarvan de "
        "houdingscodering niet herkend is")
    assert "niet bepaalbaar" in txt
    # Het fenotypeblok mag "Positioneel OSAS (POSA): niet bepaalbaar" tonen;
    # wat weg moet zijn de dríe claims: "ja", het Besluit-bijvoeglijk
    # ("..., positioneel, ...") en het therapie-aandachtspunt.
    assert "(posa): ja" not in txt.lower()
    assert ", positioneel" not in txt.lower(), (
        "het automatische Besluit noemt het fenotype nog steeds")
    assert "positietherapie" not in txt.lower()


def test_posa_wel_geclaimd_bij_gecodeerde_houding(tmp_path):
    txt = _render(_results(pos_method="coded"), tmp_path)
    assert "vs non-supine" in txt, (
        "bij herkende codering moet de POSA-claim juist blijven staan")


# ── 2. Kanaalpaneel: zeg wat de lijst is ─────────────────────────────────

def test_kanaalpaneel_toont_echte_edf_lijst(tmp_path):
    txt = _render(_results(edf_channels=[
        "C4", "C3", "F3", "O1", "EOG1:A2", "EMG1", "Pressure Flow",
        "Flow Th.", "SpO2"]), tmp_path)
    assert "9 kanalen in EDF-bestand" in txt
    assert "F3" in txt and "O1" in txt


def test_kanaalpaneel_zonder_edf_lijst_claimt_geen_edf(tmp_path):
    """Oude resultaten dragen alleen de analyse-subset; het label mag dan
    niet "EDF-bestand" zeggen — dat was de bron van het F3/O1-raadsel."""
    txt = _render(_results(edf_channels=None), tmp_path)
    assert "kanalen in EDF-bestand" not in txt
    assert "kanalen gebruikt in de analyse" in txt


def test_provenance_geen_valse_afwezigheidsclaim(tmp_path):
    """EOG1:A2 zit in het EDF maar niet in de pneumo-subset; het rapport
    beweerde "niet in dit EDF-bestand" op basis van de verkeerde lijst."""
    txt = _render(_results(edf_channels=[
        "C4", "EOG1:A2", "EMG1", "Pressure Flow", "Flow Th.", "SpO2"]),
        tmp_path)
    assert "niet in dit EDF-bestand" not in txt


def test_provenance_echte_afwezigheid_blijft_gemeld(tmp_path):
    txt = _render(_results(edf_channels=[
        "C4", "EMG1", "Pressure Flow", "Flow Th.", "SpO2"]), tmp_path)
    assert "niet in dit EDF-bestand" in txt


# ── 3. Template-lekken ───────────────────────────────────────────────────

def test_odi_referentie_zonder_placeholder(tmp_path):
    txt = _render(_results(), tmp_path)
    assert "{_UH}" not in txt, "letterlijke accolades in de ODI-referentie"
    assert "<5/u" in txt.replace(" ", "")


def test_saturatiebanden_nederlands_juiste_noemer_geen_blokjes(tmp_path):
    txt = _render(_results(), tmp_path)
    assert "Tijd in saturatiebanden" in txt
    assert "% van slaaptijd" in txt
    assert "% of recording" not in txt, (
        "de banden zijn percentages van de SLAAPTIJD (psgscoring spo2.py), "
        "niet van de opname — en het label stond in het Engels")
    assert "Time in saturation bands" not in txt
    for line in txt.splitlines():
        if "95-100" in line or "saturatieband" in line.lower():
            assert "■" not in line, f"font-fallback in bandtabel: {line!r}"


def test_ess_sectie_in_rapporttaal(tmp_path):
    txt = _render(_results(), tmp_path)
    assert "not provided" not in txt
    assert "niet ingevuld" in txt


def test_plmi_ernst_vertaald(tmp_path):
    txt = _render(_results(), tmp_path)
    assert "moderate" not in txt, "psgscoring-ernstwoord onvertaald in PLMI-rij"
    assert "matig" in txt.lower()


def test_spindelkoppen_en_totaal_vertaald(tmp_path):
    """De kop "604 spindels gedetecteerd" telt kanalen samen (zelfde spindel
    op C3 én C4 telt dubbel) en de kolomkoppen waren Engelse df-kolommen."""
    txt = _render(_results(spindles=True), tmp_path)
    assert "kanalen samengeteld" in txt
    assert "Aantal" in txt, "kolomkop Count onvertaald"


# ── 4. Verkeerde labels bij juiste getallen ──────────────────────────────

def test_fri_herstel_heet_regel_1a(tmp_path):
    """Arousal-herstel is Regel 1A (flow + arousal); het label zei Rule 1B —
    het criterium dat juist GEEN arousal kent."""
    txt = _render(_results(), tmp_path)
    assert "Rule 1B (arousal)" not in txt
    assert "Regel 1A (arousal)" in txt


def test_arousal_uitsplitsing_voetnoot(tmp_path):
    """8,4 + 13,3 + 1,7 ≠ 21,7: PLM-arousals zitten bínnen "spontaan"
    (= niet aan een respiratoir event gekoppeld). Zonder voetnoot leest de
    tabel als een optelling die niet klopt."""
    txt = _render(_results(), tmp_path)
    assert "spontaan" in txt.lower()
    assert "niet aan een respiratoir event gekoppeld" in txt


def test_stadiawissels_teller_zonder_diagonaal(tmp_path):
    """647× W→W is geen stadiawissel; n telde alle epochparen."""
    # 12 epochs: W W W N1 N1 N2 N2 N2 N1 W W W  → 4 échte wissels
    txt = _render(_results(timeline=["W", "W", "W", "N1", "N1", "N2", "N2",
                                     "N2", "N1", "W", "W", "W"]), tmp_path)
    assert "(n=4)" in txt
    assert "(n=11)" not in txt


# ── 5. Wat de lezer nog miste ────────────────────────────────────────────

def test_ventilatoire_last_boven_referentie_wordt_aandachtspunt(tmp_path):
    txt = _render(_results(vb=27.4), tmp_path)
    assert "Verhoogde ventilatoire last" in txt


def test_ventilatoire_last_onder_referentie_geen_aandachtspunt(tmp_path):
    txt = _render(_results(vb=20.0), tmp_path)
    assert "Verhoogde ventilatoire last" not in txt


def test_hypoxic_burden_leeg_met_reden(tmp_path):
    txt = _render(_results(hypoxic_burden=None), tmp_path)
    assert "niet berekenbaar op deze opname" in txt


def test_hypoxic_burden_aanwezig_geen_reden_nodig(tmp_path):
    txt = _render(_results(hypoxic_burden=12.1, hb_method="azarbarzin"),
                  tmp_path)
    assert "niet berekenbaar op deze opname" not in txt


def test_besluit_meldt_experimenteel_profiel(tmp_path):
    """De subtitel zegt "(experimental)" maar het Besluit — wat de verwijzer
    leest — verzweeg dat dit niet het klinische standaardprofiel is."""
    txt = _render(_results(profiel="aasm_v3_breath_dual"), tmp_path)
    assert "experimenteel profiel" in txt
    assert "aasm_v3_breath_dual" in txt


def test_besluit_zwijgt_over_profiel_bij_klinische_standaard(tmp_path):
    txt = _render(_results(profiel="aasm_v3_rec"), tmp_path)
    assert "experimenteel profiel" not in txt


def test_t90_voorpagina_zelfde_precisie_als_sectie9(tmp_path):
    """Voorpagina zei "T90 20%" naast "19.5 %" in sectie 9 — zelfde waarde,
    twee afrondingen."""
    txt = _render(_results(), tmp_path)
    assert "T90 19.5%" in txt.replace(",", ".")
