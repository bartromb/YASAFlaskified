"""De topografiewaarschuwing is nooit één keer afgegaan.

`tasks.py` riep `_topography_warning(results)` aan binnen `run_analysis_job`,
waar die naam niet bestaat -- de resultaten heten daar `yasa_results`. De
NameError viel in een `except Exception: logger.debug(...)`, dus de melding
verdween zonder spoor: geen rapport, geen log op zichtbaar niveau, geen
mislukte job. De ruff-poort zag hem wél (F821) en stond sinds ten minste
26-08-2026 rood, maar niemand las hem.

De lezerskant is al gedekt (`test_analysis_warnings_surface.py`); dit is de
producerkant. Beide moeten kloppen voordat een waarschuwing bestaat.

De casus in de docstring van `_topography_warning` is de Thaise opname van
26-08-2026: spindels F4 804 / F3 521 tegen C3 14 / C4 36, trage golven O1/O2
elk 276 tegen F3 3.
"""
import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_pdf_report import _clinical_flags, _topography_warning  # noqa: E402

_TASKS = Path(__file__).resolve().parent.parent / "tasks.py"


def _omgekeerde_montage():
    """De Thaise opname: trage golven occipitaal, spindels frontaal."""
    return {
        "spindles": {"summary": [{"Channel": "EEG F4-A1", "Count": 804},
                                 {"Channel": "EEG F3-A2", "Count": 521},
                                 {"Channel": "EEG C3-A2", "Count": 14},
                                 {"Channel": "EEG C4-A1", "Count": 36}]},
        "slow_waves": {"summary": [{"Channel": "EEG O1-A2", "Count": 276},
                                   {"Channel": "EEG O2-A1", "Count": 276},
                                   {"Channel": "EEG F3-A2", "Count": 3}]},
    }


def _gezonde_montage():
    return {
        "spindles": {"summary": [{"Channel": "EEG C3-A2", "Count": 512},
                                 {"Channel": "EEG C4-A1", "Count": 488},
                                 {"Channel": "EEG F3-A2", "Count": 120}]},
        "slow_waves": {"summary": [{"Channel": "EEG F3-A2", "Count": 301},
                                   {"Channel": "EEG F4-A1", "Count": 287},
                                   {"Channel": "EEG O1-A2", "Count": 12}]},
    }


# ── 1. De aanroep in tasks.py krijgt een naam die daar bestaat ────────────

def test_the_call_site_passes_a_name_that_exists():
    """Dit is de bug zelf: `results` bestaat niet in `run_analysis_job`.

    Een naam die niet bestaat wordt hier stil opgegeten, dus alleen deze
    statische controle vangt het -- de functie draait door alsof er geen
    afwijkende topografie was.
    """
    boom = ast.parse(_TASKS.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(boom)
              if isinstance(n, ast.FunctionDef) and n.name == "run_analysis_job")

    gebonden = {t.id for n in ast.walk(fn) for t in ast.walk(n)
                if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)}
    gebonden |= {a.arg for a in fn.args.args}

    aanroepen = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)
                 and n.func.id == "_topography_warning"]
    assert aanroepen, "de topografiecheck staat niet meer in run_analysis_job"

    for call in aanroepen:
        arg = call.args[0]
        assert isinstance(arg, ast.Name), f"onverwacht argument: {ast.dump(arg)}"
        assert arg.id in gebonden, (
            f"_topography_warning({arg.id}) -- die naam bestaat niet in "
            f"run_analysis_job; de NameError verdwijnt in het except-blok")


def test_the_call_site_uses_the_dict_that_holds_the_yasa_output():
    """Niet elke bestaande naam is de juiste: het moet de dict zijn met
    `spindles` en `slow_waves`, en dat is `yasa_results`."""
    boom = ast.parse(_TASKS.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(boom)
              if isinstance(n, ast.FunctionDef) and n.name == "run_analysis_job")
    call = next(n for n in ast.walk(fn) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "_topography_warning")
    assert call.args[0].id == "yasa_results", (
        f"de check draait op `{call.args[0].id}`, niet op de YASA-uitvoer")


# ── 2. De detector zelf ───────────────────────────────────────────────────

def test_an_inverted_montage_is_flagged():
    uit = _topography_warning(_omgekeerde_montage())
    assert uit is not None, "de omgekeerde Thaise montage wordt niet gevlagd"
    assert uit["sw_occipital"] == 552 and uit["sw_frontal"] == 3
    assert uit["spindles_frontal"] == 1325 and uit["spindles_central"] == 50


def test_a_normal_montage_is_not_flagged():
    assert _topography_warning(_gezonde_montage()) is None


def test_missing_blocks_do_not_raise():
    assert _topography_warning({}) is None
    assert _topography_warning({"spindles": {}, "slow_waves": {}}) is None


# ── 3. Producer → lezer ───────────────────────────────────────────────────

def test_the_warning_reaches_the_report_surface():
    """Een code zonder vertaalsleutel mag niet stil verdwijnen -- daarom hier
    de hele weg van detector naar aandachtsblok in het rapport."""
    topo = _topography_warning(_omgekeerde_montage())
    melding = ("EEG-topografie atypisch: trage golven occipitaal "
               f"({topo['sw_occipital']}) tegen frontaal ({topo['sw_frontal']}).")
    uit = _clinical_flags({}, {}, {}, {}, lang="nl",
                          warnings=[{"code": "atypical_topography",
                                     "severity": "warning",
                                     "message": melding}])
    assert uit, "de topografiewaarschuwing haalt het rapport niet"
    assert any("topografie" in r.lower() for r in uit), uit
