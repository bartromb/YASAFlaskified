"""Hartslagstijging per respiratoir event (heart rate surge) op het leveringsoppervlak.

psgscoring levert (vanaf de release ná 0.36.2) in
``pneumo["heart_rate"]["summary"]["event_hr_surge_bpm"]`` de maat van Huang e.a.
(JACC Asia 2026): piekhartslag in het eventvenster min de gemiddelde hartslag van
de 60 s vóór het event, gemiddeld over de events van de nacht. Een veld dat de
bibliotheek maakt is pas geleverd als het verslag het leest — dus hier wordt de
PDF echt gerenderd en de tekstlaag teruggelezen, met en zonder het veld. De
productie-pin (0.36.2) kent het veld nog niet: dan hoort er geen rij te staan en
niets te falen.

De resultatenpagina rendert alleen met een volledige YASA-structuur; daarvoor
geldt, zoals voor het studieprofiel-vinkje, de bronwacht: de rij staat achter
een controle op het veld.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_pdf_review_fixes_20260907 import _render, _results  # noqa: E402


def _met_hr(res, surge="afwezig"):
    hs = {"avg_hr": 62.0, "min_hr": 48.0, "max_hr": 95.0, "std_hr": 6.0,
          "n_tachycardia": 0, "n_bradycardia": 3, "hr_p1": 50.0, "hr_p99": 90.0,
          "hr_source": "pulse", "hr_implausible_pct": 0.0, "hr_reliable": True,
          "hr_unreliable_reason": ""}
    if surge != "afwezig":
        hs.update({"event_hr_surge_bpm": surge,
                   "event_hr_surge_method": "huang2026",
                   "event_hr_surge_n": 30})
    res["pneumo"]["heart_rate"] = {"success": True, "summary": hs}
    return res


def _basis():
    return _results(hypoxic_burden=31.2, hb_method="azarbarzin", vb=12.0)


def test_pdf_toont_de_hartslagstijging_naast_de_burdens(tmp_path):
    txt = _render(_met_hr(_basis(), 12.3), tmp_path)
    assert "Hartslagstijging" in txt
    assert "12.3 bpm" in txt
    assert "Hypoxic burden" in txt, "de bestaande rij blijft staan"


def test_pdf_zonder_het_veld_toont_geen_rij_en_faalt_niet(tmp_path):
    """De productie-pin 0.36.2 levert het veld niet."""
    txt = _render(_met_hr(_basis()), tmp_path)
    assert "Hartslagstijging" not in txt
    assert "Hypoxic burden" in txt


def test_pdf_met_veld_none_toont_geen_rij(tmp_path):
    """psgscoring zet None mét reden (geen pulse, ruw ECG): geen 'None bpm'."""
    txt = _render(_met_hr(_basis(), None), tmp_path)
    assert "Hartslagstijging" not in txt
    assert "None bpm" not in txt


def test_resultatenpagina_rij_staat_achter_een_controle_op_het_veld():
    import app as A
    tpl = A.app.jinja_env.get_template("results_extended.html")
    src = tpl.environment.loader.get_source(tpl.environment,
                                            "results_extended.html")[0]
    assert "event_hr_surge_bpm" in src, "de resultatenpagina leest het veld niet"
    i = src.index("pdf_hr_surge")
    guard = src[max(0, i - 400):i]
    assert "event_hr_surge_bpm') is not none" in guard, (
        "de rij staat niet achter een controle op het veld")
