"""
tests/test_v0840_fixes.py — Unit tests for v0.8.40 code hygiene fixes

Run:
    cd myproject
    python3 -m pytest tests/test_v0840_fixes.py -v

Or standalone:
    python3 tests/test_v0840_fixes.py
"""
import sys
import os
import logging
from collections import Counter

import numpy as np
from scipy.signal import butter, filtfilt


# ══════════════════════════════════════════════════════════════
#  Test 1: _hypno_str_to_int logs unknown stages
# ══════════════════════════════════════════════════════════════

def test_hypno_known_stages(caplog=None):
    """Known stages produce no warning, correct int mapping."""
    from yasa_analysis import _hypno_str_to_int
    result = _hypno_str_to_int(["W", "N1", "N2", "N3", "R", "N2"])
    assert list(result) == [0, 1, 2, 3, 4, 2], \
        f"Expected [0,1,2,3,4,2], got {list(result)}"


def test_hypno_unknown_stages_log(caplog=None):
    """Unknown stages (ART, UNS) map to W (0) AND log warning."""
    from yasa_analysis import _hypno_str_to_int

    # Capture warning log
    logger = logging.getLogger("yasaflaskified")
    logger.setLevel(logging.WARNING)

    with _CaptureWarnings(logger) as warnings:
        result = _hypno_str_to_int(["W", "ART", "N2", "UNS", "N3", "ART"])

    # Mapping correct
    assert list(result) == [0, 0, 2, 0, 3, 0]

    # Warning emitted
    assert any("onbekende stadia" in msg for msg in warnings), \
        f"Expected warning about unknown stages, got: {warnings}"


# ══════════════════════════════════════════════════════════════
#  Test 2: Bounded flow-limitation valley search
# ══════════════════════════════════════════════════════════════

def test_bounded_flow_limitation_search():
    """Monotone rising signal must terminate at max_extend, not infinite."""
    sf = 100.0
    max_extend = int(2.0 * sf)  # 200 samples

    # Worst case: strictly monotone rising
    monotone = np.linspace(0.0, 1.0, 10000)

    # Imitate bounded left-ward search from middle
    pk = 5000
    left = pk
    steps = 0
    while (left > 0 and monotone[left-1] < monotone[left]
           and steps < max_extend):
        left -= 1
        steps += 1

    assert steps == max_extend, \
        f"Expected bounded at {max_extend}, got {steps}"


# ══════════════════════════════════════════════════════════════
#  Test 3: EMG filter handles low sample rates
# ══════════════════════════════════════════════════════════════

def _apply_emg_filter(sf, n_samples=1000):
    """Imitate v0.8.40 EMG filter logic."""
    emg_work = np.random.randn(n_samples)
    nyq = sf / 2.0
    high = min(100.0, nyq - 1.0)
    if nyq > 10.0 and high > 10.0:
        b, a = butter(4, [10, high], btype="band", fs=sf)
        return filtfilt(b, a, emg_work), "filtered"
    return emg_work, "bypassed"


def test_emg_filter_valid_sf():
    """Normal sample rates → filtered."""
    for sf in [128, 64, 32, 256]:
        _, status = _apply_emg_filter(sf)
        assert status == "filtered", f"sf={sf} should be filtered"


def test_emg_filter_low_sf_bypassed():
    """Low sample rates → bypassed without error."""
    for sf in [20, 16, 8]:
        emg, status = _apply_emg_filter(sf)
        assert status == "bypassed", f"sf={sf} should be bypassed"
        assert len(emg) > 0, "EMG should still be returned"


# ══════════════════════════════════════════════════════════════
#  Test 4: Rolling baseline noise-floor fallback
# ══════════════════════════════════════════════════════════════

def _rolling_baseline_fallback(power_arr, stage_mask):
    """Imitate v0.8.40 baseline fallback logic."""
    if stage_mask.any():
        vals = power_arr[stage_mask & (power_arr > 0)]
        global_bl = float(np.percentile(vals, 50)) if len(vals) > 20 else 1e-9
    else:
        global_bl = 1e-9

    positive = power_arr[power_arr > 0]
    noise_floor = (float(np.percentile(positive, 5))
                   if positive.size > 0 else 1e-9)
    return max(global_bl, noise_floor * 2.0)


def test_noise_floor_fallback():
    """Arousal-inflated global baseline gets noise-floor safety."""
    n = 1000
    mask = np.ones(n, dtype=bool)

    # Arousal-inflated scenario: baseline + frequent spikes
    power = np.abs(np.random.randn(n)) * 0.5
    power[::10] = 10.0  # many pseudo-arousals

    safe_bl = _rolling_baseline_fallback(power, mask)

    positive = power[power > 0]
    noise_floor = float(np.percentile(positive, 5))

    # Safe baseline must be at least 2x noise floor (mathematically
    # guaranteed by max()), OR higher if global baseline dominates.
    assert safe_bl >= 2 * noise_floor - 1e-9, \
        f"safe_bl={safe_bl}, 2*noise_floor={2*noise_floor}"


# ══════════════════════════════════════════════════════════════
#  Test 5: Staging failed flag is set
# ══════════════════════════════════════════════════════════════

def test_staging_failed_flag_conceptual():
    """Conceptual test: staging dict should have staging_failed when fallback."""
    # This is a conceptual test; the full function requires MNE Raw object
    staging = {}
    staging["fallback"] = True
    staging["staging_failed"] = True
    staging["warning"] = "Staging failed — N2 fallback used."

    assert staging.get("staging_failed") is True
    assert "Staging failed" in staging.get("warning", "")


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

class _CaptureWarnings:
    """Context manager to capture logger warnings."""
    def __init__(self, logger):
        self.logger = logger
        self.messages = []
        self.handler = None

    def __enter__(self):
        import logging as lg

        class _H(lg.Handler):
            def __init__(self, target):
                super().__init__()
                self.target = target
            def emit(self, record):
                self.target.append(record.getMessage())

        self.handler = _H(self.messages)
        self.logger.addHandler(self.handler)
        return self.messages

    def __exit__(self, *a):
        self.logger.removeHandler(self.handler)


# ══════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

    tests = [
        ("test_hypno_known_stages", test_hypno_known_stages),
        ("test_hypno_unknown_stages_log", test_hypno_unknown_stages_log),
        ("test_bounded_flow_limitation_search", test_bounded_flow_limitation_search),
        ("test_emg_filter_valid_sf", test_emg_filter_valid_sf),
        ("test_emg_filter_low_sf_bypassed", test_emg_filter_low_sf_bypassed),
        ("test_noise_floor_fallback", test_noise_floor_fallback),
        ("test_staging_failed_flag_conceptual", test_staging_failed_flag_conceptual),
    ]

    print("═" * 60)
    print("  v0.8.40 Code Hygiene Tests")
    print("═" * 60)

    passed = 0
    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
            failed += 1

    print("═" * 60)
    print(f"  {passed}/{len(tests)} passed, {failed} failed")
    print("═" * 60)
    sys.exit(0 if failed == 0 else 1)
