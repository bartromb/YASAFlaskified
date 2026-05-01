"""
test_psgscoring_from_pypi.py — guards against accidental re-vendoring.

The de-vendor commit (faa8580) replaced a bundled `myproject/psgscoring/`
copy with a PyPI dependency pinned in requirements.txt. These tests
verify that `import psgscoring` does not silently fall back to a
leftover bundled stub under `myproject/psgscoring/`, and that the
loaded version meets the requirements.txt minimum.

Allows editable installs (developer environment) — the only failure
mode it catches is the specific accident this branch protects against:
a `myproject/psgscoring/` directory shadowing the PyPI install.
"""
from pathlib import Path

import psgscoring

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_psgscoring_imports():
    """Sanity: the package is importable at all."""
    assert hasattr(psgscoring, "__version__")
    assert hasattr(psgscoring, "run_pneumo_analysis")


def test_psgscoring_not_loaded_from_bundled_path():
    """Must not load from a leftover myproject/psgscoring/ vendored copy."""
    assert psgscoring.__file__ is not None, "psgscoring has no __file__ attribute"
    pkg_path = Path(psgscoring.__file__).resolve()
    bundled_path = REPO_ROOT / "myproject" / "psgscoring"
    assert bundled_path not in pkg_path.parents, (
        f"psgscoring imported from {pkg_path} — under the de-vendored path "
        f"{bundled_path}/. A leftover bundled copy is shadowing the PyPI "
        "install. Remove myproject/psgscoring/ and reinstall."
    )


def test_psgscoring_version_meets_minimum():
    """Pinned version in requirements.txt should be 0.4.x or newer."""
    parts = psgscoring.__version__.split(".")
    major, minor = int(parts[0]), int(parts[1])
    assert (major, minor) >= (0, 4), (
        f"psgscoring {psgscoring.__version__} too old; "
        "requirements.txt pins >= 0.4.x"
    )
