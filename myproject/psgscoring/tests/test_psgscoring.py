"""
test_psgscoring.py — Unit tests for core signal processing algorithms.

Run with: pytest tests/ -v
"""

import numpy as np
import pytest

from psgscoring import (
    linearize_nasal_pressure,
    compute_mmsd,
    preprocess_flow,
    compute_dynamic_baseline,
    bandpass_flow,
    detect_breaths,
    compute_breath_amplitudes,
    compute_flattening_index,
    build_sleep_mask,
    is_nrem, is_rem, is_sleep,
)


SF = 256.0  # Standard sample frequency


# ═══════════════════════════════════════════════════════════════
# A. linearize_nasal_pressure
# ═══════════════════════════════════════════════════════════════

class TestLinearize:
    def test_preserves_sign(self):
        x = np.array([-4.0, -1.0, 0.0, 1.0, 4.0])
        y = linearize_nasal_pressure(x)
        assert y[0] < 0  # negative stays negative
        assert y[3] > 0  # positive stays positive
        assert y[2] == 0  # zero stays zero

    def test_sqrt_magnitude(self):
        x = np.array([4.0])
        y = linearize_nasal_pressure(x)
        assert abs(y[0] - 2.0) < 1e-10  # √4 = 2

    def test_corrects_pressure_flow_relationship(self):
        """50% flow reduction = 75% pressure reduction.
        After linearization, should show ~50% amplitude reduction."""
        flow_100 = np.array([1.0])  # 100% flow → pressure = 1²  = 1.0
        flow_50 = np.array([0.25])  # 50% flow  → pressure = 0.5² = 0.25

        lin_100 = linearize_nasal_pressure(flow_100)  # √1.0 = 1.0
        lin_50 = linearize_nasal_pressure(flow_50)    # √0.25 = 0.5

        ratio = lin_50[0] / lin_100[0]
        assert abs(ratio - 0.5) < 1e-10, f"Expected 0.5, got {ratio}"

    def test_empty_input(self):
        y = linearize_nasal_pressure(np.array([]))
        assert len(y) == 0

    def test_large_array(self):
        x = np.random.randn(100000)
        y = linearize_nasal_pressure(x)
        assert y.shape == x.shape


# ═══════════════════════════════════════════════════════════════
# B. compute_mmsd
# ═══════════════════════════════════════════════════════════════

class TestMMSD:
    def _make_signal(self, duration_s=60):
        t = np.arange(0, duration_s, 1/SF)
        flow = np.sin(2 * np.pi * 0.25 * t)
        # Apnea at t=20-30s
        flow[int(20*SF):int(30*SF)] *= 0.02
        return flow

    def test_shape(self):
        flow = self._make_signal()
        mmsd = compute_mmsd(flow, SF)
        assert mmsd.shape == flow.shape

    def test_apnea_lower_than_normal(self):
        flow = self._make_signal()
        filt = bandpass_flow(flow, SF)
        mmsd = compute_mmsd(filt, SF)
        normal = np.mean(mmsd[int(5*SF):int(15*SF)])
        apnea = np.mean(mmsd[int(22*SF):int(28*SF)])
        assert apnea < normal * 0.40, \
            f"MMSD during apnea ({apnea:.6f}) should be <40% of normal ({normal:.6f})"

    def test_constant_signal_near_zero(self):
        """A constant signal has zero 2nd derivative → MMSD ≈ 0."""
        flat = np.ones(int(10 * SF))
        mmsd = compute_mmsd(flat, SF)
        assert np.max(mmsd) < 1e-10


# ═══════════════════════════════════════════════════════════════
# C. preprocess_flow
# ═══════════════════════════════════════════════════════════════

class TestPreprocessFlow:
    def test_output_shape(self):
        x = np.random.randn(int(30 * SF))
        env = preprocess_flow(x, SF)
        assert env.shape == x.shape

    def test_envelope_nonnegative(self):
        x = np.random.randn(int(30 * SF))
        env = preprocess_flow(x, SF)
        assert np.all(env >= 0)

    def test_nasal_pressure_flag(self):
        """With is_nasal_pressure=True, output should differ from False."""
        x = np.abs(np.random.randn(int(30 * SF))) + 0.1
        env_raw = preprocess_flow(x, SF, is_nasal_pressure=False)
        env_lin = preprocess_flow(x, SF, is_nasal_pressure=True)
        # They should differ (sqrt changes the signal)
        assert not np.allclose(env_raw, env_lin)


# ═══════════════════════════════════════════════════════════════
# D. compute_dynamic_baseline
# ═══════════════════════════════════════════════════════════════

class TestDynamicBaseline:
    def test_positive(self):
        env = np.abs(np.sin(np.arange(0, 300, 1/SF) * 0.25)) + 0.1
        bl = compute_dynamic_baseline(env, SF)
        assert np.all(bl > 0)

    def test_length(self):
        n = int(60 * SF)
        env = np.random.rand(n) + 0.1
        bl = compute_dynamic_baseline(env, SF)
        assert len(bl) == n


# ═══════════════════════════════════════════════════════════════
# E. detect_breaths
# ═══════════════════════════════════════════════════════════════

class TestDetectBreaths:
    def test_regular_breathing(self):
        """15 breaths/min for 2 min → expect ~28-32 breaths."""
        t = np.arange(0, 120, 1/SF)
        flow = np.sin(2 * np.pi * 0.25 * t)  # 0.25 Hz = 15/min
        filt = bandpass_flow(flow, SF)
        breaths = detect_breaths(filt, SF)
        assert 20 < len(breaths) < 40, f"Expected ~30 breaths, got {len(breaths)}"

    def test_breath_has_required_keys(self):
        t = np.arange(0, 30, 1/SF)
        flow = np.sin(2 * np.pi * 0.25 * t)
        filt = bandpass_flow(flow, SF)
        breaths = detect_breaths(filt, SF)
        if breaths:
            b = breaths[0]
            for key in ["start", "end", "onset_s", "duration_s",
                        "amplitude", "insp_segment"]:
                assert key in b, f"Missing key: {key}"


# ═══════════════════════════════════════════════════════════════
# F. compute_flattening_index
# ═══════════════════════════════════════════════════════════════

class TestFlatteningIndex:
    def test_sinusoidal_low(self):
        """A sinusoidal inspiratory segment has low flattening."""
        seg = np.sin(np.linspace(0, np.pi, 100))
        fi = compute_flattening_index(seg)
        assert fi <= 0.4, f"Sinusoidal should be low, got {fi}"

    def test_flat_plateau_high(self):
        """A plateau signal has high flattening."""
        seg = np.ones(100)
        fi = compute_flattening_index(seg)
        assert fi > 0.8, f"Plateau should be high, got {fi}"


# ═══════════════════════════════════════════════════════════════
# G. Utility functions
# ═══════════════════════════════════════════════════════════════

class TestUtils:
    def test_is_nrem(self):
        assert is_nrem("N1") and is_nrem("N2") and is_nrem("N3")
        assert is_nrem(1) and is_nrem(2) and is_nrem(3)
        assert not is_nrem("W") and not is_nrem("R")

    def test_is_rem(self):
        assert is_rem("R") and is_rem(4)
        assert not is_rem("N2") and not is_rem("W")

    def test_is_sleep(self):
        assert is_sleep("N1") and is_sleep("R")
        assert not is_sleep("W")

    def test_build_sleep_mask(self):
        hypno = ["W", "N1", "N2", "N3", "R", "W"]
        mask = build_sleep_mask(hypno, SF, int(6 * 30 * SF))
        # First epoch (W) = False, epochs 1-4 (sleep) = True, epoch 5 (W) = False
        assert not mask[0]
        assert mask[int(1.5 * 30 * SF)]  # middle of N1
        assert not mask[int(5.5 * 30 * SF)]  # middle of last W


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
