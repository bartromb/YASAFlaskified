"""arousal_analysis.py — compatibility shim.

Arousal & RERA detection now lives in **psgscoring.arousal** (ported there so the
scoring library is self-contained — see psgscoring CHANGELOG v0.9.0). This module
re-exports the full API, including private helpers and constants, so any code that
still does ``from arousal_analysis import ...`` keeps working unchanged.

⚠️ Requires **psgscoring >= 0.9.0** (older releases have no `arousal` submodule).
Deploy the matched pair together: bump the `psgscoring` pin in requirements.txt to
>= 0.8.0 in the same release that ships this shim.
"""
from __future__ import annotations

from psgscoring import arousal as _arousal
from psgscoring.arousal import *  # noqa: F401,F403

# Re-export every public + private module attribute so historical imports of helper
# functions / constants (detect_arousals, detect_reras, run_arousal_respiratory_analysis,
# _recompute_arousal_summary, AROUSAL_LGBM_THRESHOLD, …) resolve exactly as before.
globals().update(
    {k: getattr(_arousal, k) for k in dir(_arousal) if not k.startswith("__")}
)
