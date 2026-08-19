"""De sensornoot onder de respiratoire tabel moet zeggen wat er gebeurd is.

Twee waargenomen tegenspraken in échte rapporten:

  * duaal rapport: "apneu op thermistor, hypopneu op nasale druk" terwijl de
    corroboratiekolom liet zien dat élke apneu alleen op de neusdruk gezien is;
  * pressure rapport: "één flowkanaal beschikbaar" terwijl de kanaallijst
    erboven zowel `Pressure Flow` als `Flow Th.` toonde — de thermistor zat in
    het bestand maar was door de kwaliteitstoets afgewezen.

De keuze zit in flow_sensor_notes(); de teksten in i18n.
"""

import os
import sys

from generate_pdf_report import flow_sensor_notes
from i18n import TRANSLATIONS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _pneumo(apnea, hypopnea, rejected=None, agreement=None):
    return {"meta": {"flow_channels": {
        "apnea_sensor":       apnea,
        "hypopnea_sensor":    hypopnea,
        "thermistor_rejected": rejected,
        "thermistor_check":   ({"agreement": agreement} if agreement is not None else None),
    }}}


def _keys(resp, pneumo):
    return [k for k, _ in flow_sensor_notes(resp, pneumo)]


def test_two_usable_sensors_report_the_aasm_method():
    resp = {"dual_sensor": True}
    assert _keys(resp, _pneumo("Flow Th.", "Pressure Flow")) == ["pdf_dual_sensor_note"]


def test_a_thermistor_that_corroborated_nothing_is_called_out():
    """De duale noot claimt apneus op de thermistor — als die niets bevestigde,
    spreekt de corroboratiekolom de noot tegen."""
    resp = {"dual_sensor": True,
            "dual_sensor_apnea": {"n_both": 0, "n_thermistor_only": 0,
                                  "n_pressure_only": 10, "n_kept": 10}}
    assert _keys(resp, _pneumo("Flow Th.", "Pressure Flow")) == [
        "pdf_dual_sensor_note", "pdf_dual_sensor_no_corrob"]


def test_a_corroborating_thermistor_gets_no_extra_warning():
    resp = {"dual_sensor": True,
            "dual_sensor_apnea": {"n_both": 7, "n_thermistor_only": 1,
                                  "n_pressure_only": 2, "n_kept": 10}}
    assert _keys(resp, _pneumo("Flow Th.", "Pressure Flow")) == ["pdf_dual_sensor_note"]


def test_a_rejected_thermistor_is_not_reported_as_a_missing_channel():
    """Het geval dat het rapport zichzelf liet tegenspreken."""
    resp = {"dual_sensor": False}
    pneumo = _pneumo("Pressure Flow", "Pressure Flow",
                     rejected="Flow Th.", agreement=0.32)
    assert _keys(resp, pneumo) == ["pdf_thermistor_rejected_note"]
    kwargs = flow_sensor_notes(resp, pneumo)[0][1]
    assert kwargs["therm"] == "Flow Th."
    assert kwargs["apnea"] == "Pressure Flow"
    assert kwargs["agreement"] == "0.32"


def test_a_rejected_thermistor_without_an_agreement_number_still_renders():
    resp = {"dual_sensor": False}
    pneumo = _pneumo("Pressure Flow", "Pressure Flow", rejected="Flow Th.")
    key, kwargs = flow_sensor_notes(resp, pneumo)[0]
    assert kwargs["agreement"] == "—"
    for lang in ("nl", "fr", "en", "de"):
        TRANSLATIONS[key][lang].format(**kwargs)  # mag niet op KeyError klappen


def test_a_genuinely_single_channel_montage_says_so():
    resp = {"dual_sensor": False}
    assert _keys(resp, _pneumo("Pressure Flow", "Pressure Flow")) == [
        "pdf_single_sensor_note"]


def test_dual_flag_without_two_distinct_sensors_does_not_claim_the_method():
    """Vangnet: de vlag mag de sensornamen niet overrulen."""
    resp = {"dual_sensor": True}
    assert _keys(resp, _pneumo("Pressure Flow", "Pressure Flow")) == [
        "pdf_single_sensor_note"]


def test_every_note_is_translated_in_all_four_languages():
    for key in ("pdf_dual_sensor_note", "pdf_dual_sensor_no_corrob",
                "pdf_thermistor_rejected_note", "pdf_single_sensor_note"):
        for lang in ("nl", "fr", "en", "de"):
            assert TRANSLATIONS[key][lang].strip(), f"{key}/{lang} ontbreekt"


# ── de RIP-paarpoort hoort in het RAPPORT, niet alleen in een badge ─────

def test_the_rip_block_actually_renders_in_a_pdf(tmp_path):
    """Bereikbaarheid, niet aanwezigheid.

    De vorige versie van deze test las de BRON op `pair_gate_suspect` en
    slaagde -- terwijl het blok binnen `if has_sq:` stond, en `has_sq` sinds
    v0.15.0 hard op False staat omdat de signaalkwaliteitssectie toen uit het
    klinische rapport is gehaald. Het blok kon dus nooit renderen, en op een
    echte opname met ratio 1186x stond er niets in het rapport.

    Deze test genereert een rapport en leest de PDF terug. Dat is het enige
    dat onderscheid maakt tussen "de code staat er" en "de lezer ziet het".
    """
    import shutil
    import subprocess
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert shutil.which("pdftotext"), "pdftotext ontbreekt (poppler-utils)"
    from generate_pdf_report import generate_pdf_report

    results = {
        "pneumo": {
            "meta": {"scoring_profile": "aasm_v3_rec"},
            "respiratory": {"summary": {"ahi_total": 25.9}, "events": []},
            "signal_quality": {
                "recommended_mode": "single-channel",
                "working_channel": "abdomen",
                "energy_ratio": 1186.16,
                "pair_gate_suspect": True,
                "warnings": ["RIP energy ratio 1186x — thorax likely disconnected."],
            },
        },
        "staging": {"hypnogram": ["N2"] * 100},
    }
    out = str(tmp_path / "r.pdf")
    generate_pdf_report(results, out, lang="nl")
    txt = subprocess.run(["pdftotext", out, "-"], capture_output=True,
                         text=True).stdout
    assert "1186" in txt, "de energieverhouding staat niet in het rapport"
    assert "abdomen" in txt.lower(), "het gebruikte kanaal ontbreekt"
    low = txt.lower()
    assert "twijfelachtig" in low or "doubtful" in low or "fraglich" in low, (
        "een twijfelachtige afkeuring wordt niet als zodanig gemeld")


def test_a_bilateral_recording_gets_no_rip_block(tmp_path):
    """Guard op de guard: zou het blok altijd renderen, dan zegt het niets."""
    import shutil
    import subprocess
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert shutil.which("pdftotext")
    from generate_pdf_report import generate_pdf_report
    results = {
        "pneumo": {
            "meta": {"scoring_profile": "aasm_v3_rec"},
            "respiratory": {"summary": {"ahi_total": 12.0}, "events": []},
            "signal_quality": {"recommended_mode": "bilateral",
                               "working_channel": None,
                               "energy_ratio": 2.1,
                               "pair_gate_suspect": False, "warnings": []},
        },
        "staging": {"hypnogram": ["N2"] * 100},
    }
    out = str(tmp_path / "r2.pdf")
    generate_pdf_report(results, out, lang="nl")
    txt = subprocess.run(["pdftotext", out, "-"], capture_output=True,
                         text=True).stdout
    assert "2.1" not in txt or "energieverhouding" not in txt.lower()


def test_the_rip_pair_gate_reaches_the_pdf_report():
    """Tot v0.27.0 stond de paarkwaliteit NERGENS in het rapport.

    Ze werd alleen als badge in de webinterface getoond. Een clinicus las dus
    "89 centrale apneus" zonder te kunnen zien dat de bilaterale analyse
    uitstond en het onderscheid obstructief/centraal op één kanaal berustte.
    Deze test leest de rapportcode: een blok dat er niet in staat, kan niet
    per ongeluk terugverdwijnen zonder dat er iets faalt.
    """
    import inspect
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import generate_pdf_report as G
    src = inspect.getsource(G)
    assert '(results.get("pneumo") or {}).get("signal_quality")' in src, (
        "het rapport leest de RIP-paarkwaliteit niet")
    assert "pair_gate_suspect" in src, (
        "het rapport maakt geen onderscheid tussen een terechte en een "
        "twijfelachtige afkeuring")
    assert "pdf_rip_gate_suspect" in src


def test_the_rip_block_uses_prefixed_locals():
    """`_hdr` hernoemen binnen deze functie gaf eerder een UnboundLocalError
    op ELK rapport (ruff F823). Nieuwe blokken gebruiken daarom _rip_-namen."""
    import inspect
    import os
    import re
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import generate_pdf_report as G
    src = inspect.getsource(G)
    block = src[src.index("RIP-PAARPOORT"):]
    block = block[:block.index("v0.8.22: Signal quality per channel")]
    assigned = set(re.findall(r"^\s+(_[a-z_]+) =", block, re.M))
    assert assigned, "geen lokale toewijzingen gevonden — is het blok er nog?"
    assert all(n.startswith("_rip_") for n in assigned), (
        f"niet-voorgevoegde lokalen in het RIP-blok: "
        f"{sorted(n for n in assigned if not n.startswith('_rip_'))}")
