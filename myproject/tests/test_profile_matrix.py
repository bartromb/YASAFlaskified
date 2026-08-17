"""
tests/test_profile_matrix.py — de profielmatrix en de studieprofiel-set.

De zes tests die `YF_PROFIELMATRIX_SPEC.md` voorschrijft, plus wat de meting
tijdens de uitvoering opleverde.

DRIE PREMISSEN UIT DE SPEC DIE NIET KLOPTEN
-------------------------------------------
1. "`run_profile_comparison` draait sinds v0.9.0 de hele registry." Nee — die
   functie kwam in de hele codebase exact één keer voor, in haar eigen `def`.
   Nooit aangeroepen, nooit ge-enqueued, `profile_comparison.json` nooit
   geschreven.
2. "De PDF-tabel toont een hard-coded drietal." Die tabel wordt *niet
   gerenderd*: `# story.append(_prof_tbl)   # intentionally not rendered`, in
   v0.15.0 bewust uit de klinische PDF gehaald omdat hij niet gevalideerd is als
   ernstinstrument.
3. Wat het rapport wél las kwam uit **psgscoring** (`ahi_interval`, drie
   intervalarmen), niet uit tasks.py.

Gevolg voor de uitvoering: de matrix is een **studie**-artefact, zoals de eerste
regel van de spec ook zegt ("Wanneer een studie via YF loopt"). Hij verschijnt
bij een volledige vergelijking of een geconfigureerde studieprofiel-set, en
laat het klinische rapport anders ongemoeid — het v0.15.0-besluit wordt niet als
bijeffect van een rapportagevraag teruggedraaid.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
from profile_matrix import MISSING, build_matrix, fmt, fmt_delta, validate_study_set
from psgscoring.profiles import PROFILES

REPO = Path(__file__).resolve().parents[1]


def _pneumo(primary="aasm_v3_rec", ahi=12.3, interval=True):
    out = {
        "meta": {"scoring_profile": primary},
        "respiratory": {"summary": {"ahi_total": ahi, "oahi": ahi - 1.0,
                                    "severity": "Mild"}},
    }
    if interval:
        out["ahi_interval"] = {
            "strict":    {"ahi": 9.1, "oahi": 8.0, "severity": "Mild"},
            "standard":  {"ahi": ahi, "oahi": ahi - 1.0, "severity": "Mild"},
            "sensitive": {"ahi": 18.7, "oahi": 17.2, "severity": "Moderate"},
            "interval": [9.1, 18.7], "robustness_grade": "B",
        }
    return out


# ─────────────────────────────────────────────────────────────────────────
# Spec-test 1 — registrykoppeling, geen hard-coded profielnamen
# ─────────────────────────────────────────────────────────────────────────

def test_row_labels_come_from_the_registry():
    m = build_matrix(_pneumo())
    labels = {r["display_name"] for r in m["rows"]}
    expected = {PROFILES[n].display_name
                for n in ("aasm_v3_strict", "aasm_v3_rec", "aasm_v3_sensitive")}
    assert labels == expected, (
        "de rijlabels komen niet uit display_name van de registry")
    for r in m["rows"]:
        assert PROFILES[r["name"]].aasm_version in r["ruleset"]


def test_no_hardcoded_profile_parameters_in_the_report_code():
    """
    Het echte defect in de tabel die dit vervangt: kolommen als "70% (≥30%)",
    "30s", "3s" kwamen uit geen enkele bron en konden dus uit de pas lopen met
    de registry. Ze mogen niet terugkeren in de matrixcode.

    De oude, niet-gerenderde tabel mag blijven staan — die is expliciet
    uitgezet — dus dit kijkt uitsluitend naar het matrixblok.
    """
    src = (REPO / "generate_pdf_report.py").read_text(encoding="utf-8")
    start = src.find("v0.23.0: profielmatrix")
    assert start != -1, "het matrixblok is verdwenen uit generate_pdf_report.py"
    end = src.find("profielmatrix niet gerenderd", start)
    # Commentaarregels eruit: het blok LEGT UIT dat deze waarden er niet horen en
    # citeert ze daarbij. Een test die prosa toetst in plaats van code zou de
    # uitleg straffen en de eerste versie van deze test deed precies dat.
    block = "\n".join(ln for ln in src[start:end].splitlines()
                      if not ln.lstrip().startswith("#"))
    for forbidden in ('"70%', "'70%", '"30s"', '"45s"', '"15s"', "≥30%", "≥25%"):
        assert forbidden not in block, (
            f"hard-coded profielparameter {forbidden!r} in de matrixcode; die "
            f"hoort uit de registry te komen")


# ─────────────────────────────────────────────────────────────────────────
# Spec-test 2 — primair-assert
# ─────────────────────────────────────────────────────────────────────────

def test_a_primary_mismatch_is_flagged_and_logged(caplog):
    """
    De matrixrij van het primaire profiel moet met het hoofdresultaat
    overeenkomen. Verschilt hij, dan zijn twee codepaden uit de pas — een
    cache-, env- of versieverschil — en dat moet je zien, niet verbergen.
    """
    pn = _pneumo(ahi=12.3)
    comparison = {
        "_meta": {"primary_profile": "aasm_v3_rec",
                  "profiles_compared": ["aasm_v3_rec", "aasm_v3_breath"]},
        "aasm_v3_rec":    {"ahi_total": 15.9, "severity": "Moderate"},   # afwijkend!
        "aasm_v3_breath": {"ahi_total": 13.1, "severity": "Mild"},
    }
    with caplog.at_level(logging.ERROR):
        m = build_matrix(pn, comparison)
    assert m["primary_mismatch"] is not None
    assert m["primary_mismatch"]["matrix"] == pytest.approx(15.9)
    assert m["primary_mismatch"]["head"] == pytest.approx(12.3)
    assert any(r.levelno == logging.ERROR for r in caplog.records), (
        "een mismatch tussen twee codepaden moet op ERROR gelogd worden")


def test_a_matching_primary_is_not_flagged():
    pn = _pneumo(ahi=12.3)
    comparison = {
        "_meta": {"primary_profile": "aasm_v3_rec"},
        "aasm_v3_rec": {"ahi_total": 12.3, "severity": "Mild"},
    }
    assert build_matrix(pn, comparison)["primary_mismatch"] is None


def test_the_report_is_still_generated_on_mismatch():
    """
    Een mismatch waarschuwt, maar blokkeert niet: een ontbrekende matrix is
    zichtbaar, een ontbrekend rapport is een incident.
    """
    pn = _pneumo(ahi=12.3)
    m = build_matrix(pn, {"_meta": {"primary_profile": "aasm_v3_rec"},
                          "aasm_v3_rec": {"ahi_total": 99.9}})
    assert m["rows"], "de matrix hoort ondanks de mismatch rijen te bevatten"
    assert m["footnotes"]["primary"] is True


# ─────────────────────────────────────────────────────────────────────────
# Spec-test 3 — bevroren profielen
# ─────────────────────────────────────────────────────────────────────────

def test_frozen_profiles_are_absent_by_default():
    resolved, errors = validate_study_set({})
    assert not errors
    m = build_matrix(_pneumo())
    assert not any(r["is_frozen"] for r in m["rows"]), (
        "mesa_shhs of chicago_1999 in een matrix die er niet om vroeg")


def test_frozen_profiles_appear_marked_when_asked_explicitly():
    resolved, errors = validate_study_set(
        {"comparison_profiles": ["aasm_v3_rec", "mesa_shhs"]})
    assert not errors
    assert "mesa_shhs" in resolved["comparison_profiles"]

    comparison = {
        "_meta": {"primary_profile": "aasm_v3_rec"},
        "aasm_v3_rec": {"ahi_total": 12.3},
        "mesa_shhs":   {"ahi_total": 7.7},
    }
    m = build_matrix(_pneumo(), comparison)
    frozen = [r for r in m["rows"] if r["name"] == "mesa_shhs"]
    assert frozen and frozen[0]["is_frozen"], "mesa_shhs is niet als bevroren gemarkeerd"
    assert m["footnotes"]["frozen_present"] is True
    assert m["rows"][-1]["name"] == "mesa_shhs", "bevroren hoort onderaan"


# ─────────────────────────────────────────────────────────────────────────
# Spec-test 4 — de RDI-cel
# ─────────────────────────────────────────────────────────────────────────

def test_a_missing_rdi_is_a_dash_and_never_zero():
    """
    De bekende valkuil uit de rapportvergelijking van 13-08: 0,0 tonen waar de
    RERA-tak niet draait leest als "geen RERA's gevonden" in plaats van "niet
    gemeten".
    """
    m = build_matrix(_pneumo())
    for r in m["rows"]:
        assert r["rdi"] is None
        assert fmt(r["rdi"]) == MISSING
        assert fmt(r["rdi"]) != "0.0"
    assert m["footnotes"]["rdi_missing"] is True


def test_a_present_rdi_is_shown():
    comparison = {"_meta": {"primary_profile": "aasm_v3_rec"},
                  "aasm_v3_rec": {"ahi_total": 12.3, "rdi": 14.8}}
    m = build_matrix(_pneumo(), comparison)
    assert fmt(m["rows"][0]["rdi"]) == "14.8"
    assert m["footnotes"]["rdi_missing"] is False


def test_zero_is_distinguished_from_missing():
    """Een echte nul is een meting en moet als 0.0 verschijnen."""
    assert fmt(0.0) == "0.0"
    assert fmt(None) == MISSING
    assert fmt("") == MISSING


# ─────────────────────────────────────────────────────────────────────────
# Spec-test 5 — de Δ-kolom
# ─────────────────────────────────────────────────────────────────────────

def test_delta_sign_and_rounding_are_pinned():
    m = build_matrix(_pneumo(ahi=12.3))
    by = {r["name"]: r for r in m["rows"]}
    assert by["aasm_v3_rec"]["delta_ahi"] == pytest.approx(0.0)
    assert by["aasm_v3_strict"]["delta_ahi"] == pytest.approx(9.1 - 12.3)
    assert by["aasm_v3_sensitive"]["delta_ahi"] == pytest.approx(18.7 - 12.3)
    assert fmt_delta(by["aasm_v3_strict"]["delta_ahi"]) == "-3.2"
    assert fmt_delta(by["aasm_v3_sensitive"]["delta_ahi"]) == "+6.4"
    assert fmt_delta(0.0) == "+0.0", (
        "identiek aan het primaire profiel is een uitkomst, geen ontbrekende waarde")
    assert fmt_delta(None) == MISSING


def test_the_primary_row_sorts_first():
    m = build_matrix(_pneumo())
    assert m["rows"][0]["is_primary"], "het primaire profiel hoort bovenaan"


# ─────────────────────────────────────────────────────────────────────────
# Spec-test 6 — configuratievalidatie
# ─────────────────────────────────────────────────────────────────────────

def test_a_frozen_profile_is_refused_as_primary():
    resolved, errors = validate_study_set({"primary_profile": "mesa_shhs"})
    assert resolved["primary_profile"] is None
    assert errors and "bevroren" in errors[0]
    assert "comparison_profiles" in errors[0], (
        "de melding moet zeggen wat de gebruiker in plaats daarvan kan doen")


def test_an_unknown_primary_is_refused_with_the_available_list():
    resolved, errors = validate_study_set({"primary_profile": "aasm_v9_future"})
    assert resolved["primary_profile"] is None
    assert errors and "bestaat niet" in errors[0]
    assert "aasm_v3_rec" in errors[0], "de melding noemt de beschikbare profielen niet"


def test_an_experimental_primary_needs_the_flag():
    resolved, errors = validate_study_set({"primary_profile": "aasm_v3_env_breath"})
    assert resolved["primary_profile"] is None
    assert errors and "experimenteel" in errors[0]

    resolved, errors = validate_study_set(
        {"primary_profile": "aasm_v3_env_breath", "include_experimental": True})
    assert not errors
    assert resolved["primary_profile"] == "aasm_v3_env_breath"


def test_a_clinical_primary_passes():
    resolved, errors = validate_study_set({"primary_profile": "aasm_v3_rec"})
    assert not errors and resolved["primary_profile"] == "aasm_v3_rec"


def test_a_group_resolves_and_drops_experimental_unless_asked():
    resolved, errors = validate_study_set({"comparison_group": "clinical"})
    assert not errors
    # De groep 'clinical' bevat strict en sensitive, en die zijn exploratory.
    assert resolved["comparison_profiles"] == ["aasm_v3_rec"], (
        "zonder include_experimental horen de exploratory-armen eruit")

    resolved, _ = validate_study_set({"comparison_group": "clinical",
                                      "include_experimental": True})
    assert set(resolved["comparison_profiles"]) == {
        "aasm_v3_strict", "aasm_v3_rec", "aasm_v3_sensitive"}


def test_an_unknown_group_is_refused():
    _resolved, errors = validate_study_set({"comparison_group": "nonexistent"})
    assert errors and "bestaat niet" in errors[0]


def test_an_explicit_list_is_not_silently_filtered():
    """
    Een expliciete lijst is een keuze van de onderzoeker. Die stil inkorten zou
    een studie laten denken dat ze meer profielen vergeleek dan ze deed.
    """
    resolved, errors = validate_study_set(
        {"comparison_profiles": ["aasm_v3_rec", "aasm_v3_env_breath"]})
    assert not errors
    assert "aasm_v3_env_breath" in resolved["comparison_profiles"]


# ─────────────────────────────────────────────────────────────────────────
# Wat de uitvoering opleverde: de bron van de matrix
# ─────────────────────────────────────────────────────────────────────────

def test_the_matrix_says_which_source_it_used():
    """
    Er zijn twee bronnen en ze leveren niet dezelfde kolommen. Zonder dit veld
    is een matrix met drie rijen en lege CAHI-cellen niet te onderscheiden van
    een volledige vergelijking die stukliep.
    """
    assert build_matrix(_pneumo())["source"] == "ahi_interval"
    assert build_matrix(_pneumo(), {"_meta": {}, "aasm_v3_rec": {"ahi_total": 1.0}}
                        )["source"] == "full_comparison"
    assert build_matrix(_pneumo(interval=False))["source"] == "primary_only"


def test_a_comparison_without_meta_is_marked_pre_config():
    """Oude studies missen `_meta`; die moeten leesbaar blijven, met een regel
    dat de primair-markering niet vastligt."""
    m = build_matrix(_pneumo(), {"aasm_v3_rec": {"ahi_total": 12.3},
                                 "aasm_v3_breath": {"ahi_total": 13.0}})
    assert m["footnotes"]["pre_config"] is True
    assert len(m["rows"]) == 2


def test_legacy_alias_names_resolve_to_registry_names():
    """
    `ahi_interval` gebruikt de legacy-aliassen strict/standard/sensitive, die
    niet in de registry staan. Zonder resolutie zou elke rij "?" als familie en
    de alias als label krijgen.
    """
    m = build_matrix(_pneumo())
    assert {r["name"] for r in m["rows"]} == {
        "aasm_v3_strict", "aasm_v3_rec", "aasm_v3_sensitive"}
    assert all(r["family"] != "?" for r in m["rows"])
