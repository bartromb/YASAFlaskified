"""
tests/test_profile_dropdown.py — the scoring-profile dropdown on channel_select.

v0.22.0 groups the dropdown by the **family** psgscoring reports, instead of by
the AASM-version string. The defect that motivated it was silent and it was
structural, not a typo:

Until 0.21.0 the list was built from `PROFILES` with no family filter, and the
template sorted it into three optgroups on `aasm_version`. Every exploratory
profile therefore sat among the clinical ones, visually indistinguishable — and
any new profile in the library landed there automatically, with no decision by
anyone. Bumping the pin to psgscoring 0.19.x would have put four envelope arms
next to `aasm_v3_rec`, one of which (`aasm_v3_env_breath`) was measured and
**rejected** on two independent cohorts.

So these tests check two different things:

  * that the grouping is right *now* — clinical, historical, frozen, and
    experimental behind its own heading with a warning;
  * that it cannot silently go wrong *later* — every profile the library
    exposes must land in exactly one group, so a new family or a new profile
    fails the test instead of appearing unannounced in a clinician's list.
"""
from __future__ import annotations

import re

import pytest
from app import app
from psgscoring.profiles import PROFILES

LANGS = ("nl", "fr", "en", "de")
CLINICAL = {n for n, p in PROFILES.items() if p.family == "clinical"}
EXPLORATORY = {n for n, p in PROFILES.items() if p.family == "exploratory"}
FROZEN = {n for n, p in PROFILES.items() if p.family in ("dataset", "legacy")}


def _render_select() -> str:
    """Render only the scoring-profile <select> out of the real template.

    Pulling the fragment from the template file keeps this honest: if the markup
    is restructured, the extraction fails loudly instead of testing a copy that
    no longer resembles the page.
    """
    from pathlib import Path

    from jinja2 import Environment

    tpl_path = (Path(__file__).resolve().parents[1]
                / "templates" / "channel_select.html")
    src = tpl_path.read_text(encoding="utf-8")
    m = re.search(r'<select name="scoring_profile".*?</select>', src, re.S)
    assert m, "the scoring-profile select could not be located in the template"

    env = Environment(autoescape=True)
    tpl = env.from_string(m.group(0))
    profiles = [(n, p.display_name, p.aasm_version, p.family)
                for n, p in PROFILES.items()]
    return tpl.render(available_profiles=profiles, _sel="aasm_v3_rec",
                      t=lambda k: k)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    return app.test_client()


def _optgroups(html: str) -> dict[str, list[str]]:
    """{optgroup label: [profile values]} from the scoring-profile select."""
    sel = re.search(r'<select[^>]*id="scoringProfile".*?</select>', html, re.S)
    assert sel, "the scoring-profile select is gone from channel_select"
    out: dict[str, list[str]] = {}
    for m in re.finditer(r'<optgroup label="([^"]*)"(.*?)</optgroup>', sel.group(0), re.S):
        out[m.group(1)] = re.findall(r'<option value="([^"]+)"', m.group(2))
    return out


# ─────────────────────────────────────────────────────────────────────────
# Grouping
# ─────────────────────────────────────────────────────────────────────────

class TestGrouping:
    """
    These run against the rendered template through a fake `available_profiles`,
    so they test the Jinja logic rather than a re-implementation of it.
    """

    def test_the_rendered_markup_groups_as_intended(self):
        """
        Renders the real `<select>` fragment out of the real template, so this
        tests the Jinja conditions rather than a re-implementation of them.
        Rendering the whole page would need a job context; the fragment is the
        part under test.
        """
        html = _render_select()
        groups = _optgroups(html)
        assert len(groups) == 4, f"expected four optgroups, got {list(groups)}"
        labels = list(groups)

        clinical_v3 = {n for n in CLINICAL if "v3" in PROFILES[n].aasm_version}
        clinical_hist = CLINICAL - clinical_v3

        assert set(groups[labels[0]]) == clinical_v3, "the v3 clinical group is wrong"
        assert set(groups[labels[1]]) == clinical_hist, "the historical group is wrong"
        assert set(groups[labels[2]]) == FROZEN, "the frozen group is wrong"
        assert set(groups[labels[3]]) == EXPLORATORY, "the experimental group is wrong"

        # No exploratory profile may appear in any clinical group.
        for lbl in labels[:2]:
            assert not (set(groups[lbl]) & EXPLORATORY), (
                f"exploratory profiles leaked into '{lbl}': "
                f"{sorted(set(groups[lbl]) & EXPLORATORY)}")

    def test_every_experimental_option_is_marked_in_the_list(self):
        """
        The optgroup heading is easy to scroll past. Each experimental option
        also carries a marker in its own label.
        """
        html = _render_select()
        sel = re.search(r"<select.*?</select>", html, re.S).group(0)
        block = re.search(r'<optgroup label="[^"]*"((?:(?!<optgroup).)*)</optgroup>\s*</select>',
                          sel, re.S)
        assert block, "the experimental optgroup is not the last one"
        for name in EXPLORATORY:
            m = re.search(rf'<option value="{name}"[^>]*>([^<]*)<', block.group(1))
            assert m, f"{name} is missing from the experimental group"
            assert "⚠" in m.group(1), f"{name} carries no warning marker: {m.group(1)!r}"

    def test_every_profile_lands_in_exactly_one_group(self):
        """
        The property that matters. A profile in no group is invisible; a profile
        in two groups is ambiguous. Both are silent.
        """
        clinical_v3 = {n for n in CLINICAL if "v3" in PROFILES[n].aasm_version}
        clinical_hist = {n for n in CLINICAL
                         if "v2" in PROFILES[n].aasm_version
                         or "v1" in PROFILES[n].aasm_version}
        groups = [clinical_v3, clinical_hist, FROZEN, EXPLORATORY]

        seen: dict[str, int] = {}
        for g in groups:
            for n in g:
                seen[n] = seen.get(n, 0) + 1

        missing = set(PROFILES) - set(seen)
        doubled = {n for n, c in seen.items() if c > 1}
        assert not missing, (
            f"these profiles land in no optgroup and would be unselectable: "
            f"{sorted(missing)}")
        assert not doubled, f"these profiles land in two optgroups: {sorted(doubled)}"

    def test_the_families_are_the_ones_the_template_knows(self):
        """
        The template branches on 'clinical', 'exploratory', 'dataset', 'legacy'.
        A new family in psgscoring would fall through every branch and vanish
        from the dropdown without a word.
        """
        known = {"clinical", "exploratory", "dataset", "legacy"}
        actual = {p.family for p in PROFILES.values()}
        assert actual <= known, (
            f"psgscoring introduced family {sorted(actual - known)}, which the "
            f"template does not render — those profiles would disappear from the "
            f"dropdown silently")

    def test_the_envelope_arms_are_experimental_not_clinical(self):
        """
        The concrete case this work exists for. `aasm_v3_env_breath` was measured
        and rejected on PSG-IPA and MESA; it must never sit in a clinical group.
        """
        arms = {n for n in PROFILES if n.startswith("aasm_v3_env_")}
        if not arms:
            pytest.skip("psgscoring predates the envelope axis")
        assert arms <= EXPLORATORY, (
            f"envelope arms outside the exploratory family: {sorted(arms - EXPLORATORY)}")

    def test_strict_and_sensitive_are_experimental(self):
        """
        Deliberate and worth pinning: they are the AHI-interval bounds, not
        standalone clinical choices, so they belong behind the warning. If a
        later change promotes them, this test makes that a decision rather than
        a side effect.
        """
        assert {"aasm_v3_strict", "aasm_v3_sensitive"} <= EXPLORATORY

    def test_the_recommended_profile_is_clinical(self):
        assert "aasm_v3_rec" in CLINICAL

    def test_the_frozen_profiles_are_not_clinical(self):
        """`mesa_shhs` and `chicago_1999` reproduce published numbers."""
        assert {"mesa_shhs", "chicago_1999"} <= FROZEN


# ─────────────────────────────────────────────────────────────────────────
# The warning and the help text
# ─────────────────────────────────────────────────────────────────────────

class TestWarningAndHelp:

    @pytest.mark.parametrize("lang", LANGS)
    def test_all_four_languages_have_the_warning_and_help(self, lang):
        """
        `t()` falls back silently to another language, so a missing key gives a
        page that renders in the wrong language rather than an error — on the
        one section whose job is to stop someone picking a rejected profile.
        """
        from i18n import TRANSLATIONS
        keys = ["prof_grp_v3", "prof_grp_hist", "prof_grp_dataset", "prof_grp_exp",
                "prof_exp_warn", "prof_help_toggle", "prof_help_intro",
                "prof_help_v3", "prof_help_hist", "prof_help_dataset",
                "prof_help_exp", "prof_help_pin"]
        missing = [k for k in keys if lang not in TRANSLATIONS.get(k, {})]
        assert not missing, f"{lang} is missing: {missing}"

    def test_each_language_has_its_own_text(self):
        """Distinct strings prove the fallback did not fire."""
        from i18n import TRANSLATIONS
        for key in ("prof_grp_exp", "prof_exp_warn", "prof_help_exp"):
            vals = {lang: TRANSLATIONS[key][lang] for lang in LANGS}
            assert len(set(vals.values())) == len(LANGS), (
                f"{key} repeats a string across languages, so at least one is "
                f"not translated: {vals}")

    def test_the_warning_says_not_for_clinical_use(self):
        """
        The one sentence that must survive any rewording, in every language.
        """
        from i18n import TRANSLATIONS
        for lang, needle in (("nl", "niet voor klinisch gebruik"),
                             ("en", "not for clinical use"),
                             ("fr", "pas pour un usage clinique"),
                             ("de", "nicht für den klinischen Einsatz")):
            assert needle in TRANSLATIONS["prof_grp_exp"][lang], (
                f"{lang}: the experimental group no longer says it is not for "
                f"clinical use")

    def test_the_template_renders_the_warning_and_the_help(self):
        """
        Guards against the keys existing while the template stopped using them.
        """
        from pathlib import Path
        tpl = (Path(__file__).resolve().parents[1]
               / "templates" / "channel_select.html").read_text(encoding="utf-8")
        for key in ("prof_grp_exp", "prof_exp_warn", "prof_help_toggle",
                    "prof_help_exp", "prof_help_pin"):
            assert key in tpl, f"channel_select.html no longer renders {key}"
        assert "alert-warning" in tpl, "the experimental warning is no longer an alert"
        assert "<details" in tpl, "the help section is no longer collapsible"


# ─────────────────────────────────────────────────────────────────────────
# The pin
# ─────────────────────────────────────────────────────────────────────────

def test_the_pinned_psgscoring_is_the_installed_one():
    """
    The dropdown builds itself from whatever psgscoring is installed, so a
    requirements pin that disagrees with the environment means the app under
    test is not the app that ships. The local dev venv had drifted to 0.14.4
    while requirements.txt pinned 0.17.0, which is exactly how that goes
    unnoticed.
    """
    import re as _re
    from pathlib import Path

    import psgscoring
    req = (Path(__file__).resolve().parents[2] / "requirements.txt").read_text()
    m = _re.search(r"^psgscoring(?:\[[^\]]*\])?==([0-9][^\s]*)", req, _re.M)
    assert m, "requirements.txt no longer pins psgscoring"
    assert psgscoring.__version__ == m.group(1), (
        f"requirements.txt pins {m.group(1)} but {psgscoring.__version__} is "
        f"installed; the dropdown under test is not the one that ships")


def test_version_py_agrees_with_the_pin():
    """
    `PSGSCORING_VERSION` is shown on the landing page's stack tile, so a stale
    value is a public claim about which library is running.
    """
    import re as _re
    from pathlib import Path

    from version import PSGSCORING_VERSION
    req = (Path(__file__).resolve().parents[2] / "requirements.txt").read_text()
    m = _re.search(r"^psgscoring(?:\[[^\]]*\])?==([0-9][^\s]*)", req, _re.M)
    assert PSGSCORING_VERSION == m.group(1), (
        f"version.py says {PSGSCORING_VERSION}, requirements.txt pins {m.group(1)}")
