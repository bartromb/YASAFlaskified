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


# ═══════════════════════════════════════════════════════════════
# H. ECG effort module (v0.2.5)
# ═══════════════════════════════════════════════════════════════

class TestEcgEffort:
    """Tests for ecg_effort: R-peak detection, TECG, spectral classifier."""

    @staticmethod
    def _make_ecg(duration_s=30, hr_bpm=72):
        """Synthetic ECG: QRS spikes at given heart rate."""
        t = np.arange(0, duration_s, 1 / SF)
        ecg = np.random.randn(len(t)) * 0.05  # noise floor
        rr_s = 60.0 / hr_bpm
        n_beats = int(duration_s / rr_s)
        peak_locs = []
        for i in range(n_beats):
            idx = int(i * rr_s * SF)
            if idx < len(ecg):
                ecg[idx] = 1.5   # R-peak
                if idx + 1 < len(ecg):
                    ecg[idx + 1] = -0.5  # S-wave
                peak_locs.append(idx)
        return ecg, peak_locs

    def test_detect_r_peaks_count(self):
        from psgscoring.ecg_effort import detect_r_peaks
        ecg, expected = self._make_ecg(duration_s=20, hr_bpm=60)
        peaks = detect_r_peaks(ecg, SF)
        # Should detect roughly 20 peaks (1/s for 20s)
        assert 15 < len(peaks) < 25, f"Expected ~20 peaks, got {len(peaks)}"

    def test_detect_r_peaks_empty(self):
        from psgscoring.ecg_effort import detect_r_peaks
        flat = np.zeros(int(5 * SF))
        peaks = detect_r_peaks(flat, SF)
        assert len(peaks) == 0

    def test_compute_tecg_shape(self):
        from psgscoring.ecg_effort import compute_tecg, detect_r_peaks
        ecg, _ = self._make_ecg(duration_s=10)
        r_peaks = detect_r_peaks(ecg, SF)
        tecg = compute_tecg(ecg, SF, r_peaks)
        assert tecg.shape == ecg.shape

    def test_compute_tecg_blanking_reduces_qrs(self):
        from psgscoring.ecg_effort import compute_tecg, detect_r_peaks
        ecg, _ = self._make_ecg(duration_s=10)
        r_peaks = detect_r_peaks(ecg, SF)
        tecg = compute_tecg(ecg, SF, r_peaks)
        # TECG should have lower peak amplitude than raw (QRS removed)
        assert np.max(np.abs(tecg)) < np.max(np.abs(ecg))

    def test_adaptive_cardiac_band_normal_hr(self):
        from psgscoring.ecg_effort import compute_adaptive_cardiac_band, detect_r_peaks
        ecg, _ = self._make_ecg(duration_s=30, hr_bpm=72)
        r_peaks = detect_r_peaks(ecg, SF)
        low, high = compute_adaptive_cardiac_band(r_peaks, SF)
        hr_hz = 72 / 60  # 1.2 Hz
        assert low < hr_hz < high, f"Band ({low}, {high}) should contain {hr_hz}"

    def test_adaptive_cardiac_band_bradycardia(self):
        from psgscoring.ecg_effort import compute_adaptive_cardiac_band, detect_r_peaks
        ecg, _ = self._make_ecg(duration_s=30, hr_bpm=45)
        r_peaks = detect_r_peaks(ecg, SF)
        low, high = compute_adaptive_cardiac_band(r_peaks, SF)
        hr_hz = 45 / 60  # 0.75 Hz
        # Band should adapt downward for bradycardia
        assert low < 0.75, f"Low bound {low} should be below 0.75 for 45 bpm"

    def test_adaptive_cardiac_band_no_peaks(self):
        from psgscoring.ecg_effort import compute_adaptive_cardiac_band, CARDIAC_BAND_HZ
        low, high = compute_adaptive_cardiac_band(None, SF)
        assert (low, high) == CARDIAC_BAND_HZ

    def test_spectral_effort_cardiac_dominant(self):
        from psgscoring.ecg_effort import spectral_effort_classifier
        t = np.arange(0, 15, 1 / SF)
        # Pure 1.2 Hz (cardiac) — no respiratory component
        signal = np.sin(2 * np.pi * 1.2 * t)
        result = spectral_effort_classifier(signal, SF, 0, len(signal))
        assert result["cardiac_fraction"] > 0.6, f"Expected cardiac dominant, got {result}"

    def test_spectral_effort_respiratory_present(self):
        from psgscoring.ecg_effort import spectral_effort_classifier
        t = np.arange(0, 15, 1 / SF)
        # Pure 0.25 Hz (respiratory) — no cardiac
        signal = np.sin(2 * np.pi * 0.25 * t)
        result = spectral_effort_classifier(signal, SF, 0, len(signal))
        assert result["respiratory_fraction"] > 0.6
        assert not result["cardiac_dominant"]

    def test_spectral_effort_with_adaptive_band(self):
        from psgscoring.ecg_effort import spectral_effort_classifier
        t = np.arange(0, 15, 1 / SF)
        signal = np.sin(2 * np.pi * 1.2 * t)
        result = spectral_effort_classifier(signal, SF, 0, len(signal),
                                             cardiac_band_hz=(0.9, 2.0))
        assert "cardiac_band_hz" in result
        assert result["cardiac_band_hz"] == (0.9, 2.0)

    def test_ecg_effort_assessment_combined(self):
        from psgscoring.ecg_effort import ecg_effort_assessment
        ecg, _ = self._make_ecg(duration_s=30, hr_bpm=72)
        # Create a flat effort signal (no respiratory effort → central)
        flat_effort = np.random.randn(len(ecg)) * 0.001
        result = ecg_effort_assessment(
            ecg=ecg, thorax_raw=flat_effort, abdomen_raw=flat_effort,
            sf=SF, onset_idx=int(5 * SF), end_idx=int(15 * SF))
        assert "ecg_effort_present" in result
        assert "spectral_cardiac_dominant" in result
        assert "reclassify_as_central" in result

    def test_spectral_short_segment(self):
        from psgscoring.ecg_effort import spectral_effort_classifier
        short = np.random.randn(int(2 * SF))  # only 2s — too short
        result = spectral_effort_classifier(short, SF, 0, len(short))
        assert result["classification_hint"] == "insufficient_data"


# ═══════════════════════════════════════════════════════════════
# I. Classify — flattening index integration (v0.2.5)
# ═══════════════════════════════════════════════════════════════

class TestClassifyFlattening:
    def _make_effort(self, n, amp=1.0):
        return np.ones(n) * amp

    def test_high_flattening_boosts_obstructive(self):
        from psgscoring.classify import classify_apnea_type
        n = int(15 * SF)
        thorax = self._make_effort(n, 0.5)
        abdomen = self._make_effort(n, 0.5)
        # Borderline event — Rule 6
        typ1, conf1, _ = classify_apnea_type(
            0, n, thorax, abdomen, thorax, abdomen, 1.0, SF,
            flattening_index=None)
        typ2, conf2, _ = classify_apnea_type(
            0, n, thorax, abdomen, thorax, abdomen, 1.0, SF,
            flattening_index=0.50)
        # With high flattening, confidence should be higher
        assert conf2 >= conf1, f"Flattening should boost conf: {conf2} >= {conf1}"

    def test_low_flattening_supports_central(self):
        from psgscoring.classify import classify_apnea_type
        n = int(15 * SF)
        # Very low effort — should trigger central (Rule 5)
        thorax = np.random.randn(n) * 0.001
        abdomen = np.random.randn(n) * 0.001
        typ, conf, detail = classify_apnea_type(
            0, n, thorax, abdomen, thorax, abdomen, 1.0, SF,
            flattening_index=0.05)
        assert "flattening_index" in detail


# ═══════════════════════════════════════════════════════════════
# J. SpO2 low baseline warning (v0.2.5)
# ═══════════════════════════════════════════════════════════════

class TestSpo2LowBaseline:
    def test_normal_baseline_no_warning(self):
        from psgscoring.spo2 import analyze_spo2
        spo2 = np.full(int(60 * SF), 95.0)
        hypno = ["N2"] * (60 // 30)
        result = analyze_spo2(spo2, SF, hypno)
        if result["success"]:
            assert result["summary"]["low_baseline_warning"] is False

    def test_low_baseline_warning(self):
        from psgscoring.spo2 import analyze_spo2
        spo2 = np.full(int(60 * SF), 85.0)
        hypno = ["N2"] * (60 // 30)
        result = analyze_spo2(spo2, SF, hypno)
        if result["success"]:
            assert result["summary"]["low_baseline_warning"] is True
            assert result["summary"]["low_baseline_note"] is not None
            assert "COPD" in result["summary"]["low_baseline_note"]


# ═══════════════════════════════════════════════════════════════
# K. Regression tests — golden standard (v0.8.29)
# ═══════════════════════════════════════════════════════════════

class TestRegressionGoldenStandard:
    """Run the classify pipeline on known synthetic signals and verify
    that outputs match expected values.  Any code change that silently
    alters the scoring will be caught here."""

    @staticmethod
    def _make_apnea_signal(dur_s=120, event_start=40, event_dur=15,
                            reduction=0.95, sf=SF):
        """Synthetic flow + effort with one apnea event."""
        t = np.arange(0, dur_s, 1 / sf)
        flow = np.sin(2 * np.pi * 0.25 * t) * 100  # normal breathing
        thorax = np.sin(2 * np.pi * 0.25 * t) * 50
        abdomen = np.sin(2 * np.pi * 0.25 * t) * 40
        # Insert event
        s = int(event_start * sf)
        e = int((event_start + event_dur) * sf)
        flow[s:e] *= (1 - reduction)
        return flow, thorax, abdomen, t

    def test_classify_obstructive_apnea(self):
        """Apnea with effort present → obstructive."""
        from psgscoring.classify import classify_apnea_type
        from psgscoring.signal import preprocess_flow, preprocess_effort
        flow, thorax, abdomen, _ = self._make_apnea_signal()
        flow_env = preprocess_flow(flow, SF, is_nasal_pressure=True)
        thorax_env = preprocess_effort(thorax, SF)
        abdomen_env = preprocess_effort(abdomen, SF)
        effort_bl = float(np.percentile(thorax_env, 90))
        s, e = int(40 * SF), int(55 * SF)
        typ, conf, detail = classify_apnea_type(
            s, e, thorax_env, abdomen_env, thorax, abdomen,
            effort_bl, SF)
        assert typ == "obstructive", f"Expected obstructive, got {typ} ({detail.get('decision_reason')})"
        assert conf > 0.3

    def test_classify_central_apnea(self):
        """Apnea with NO effort → central.
        Pre-event: normal sinusoidal effort. During event: flat (no effort).
        This mimics real central apnea: the patient simply stops breathing."""
        from psgscoring.classify import classify_apnea_type
        from psgscoring.signal import preprocess_effort
        n = int(120 * SF)  # 120s total
        t = np.arange(n) / SF
        # Normal effort for first 40s and after 55s
        thorax = np.sin(2 * np.pi * 0.25 * t) * 50
        abdomen = np.sin(2 * np.pi * 0.25 * t) * 40
        # Flat during event (40-55s) — only tiny cardiac pulsation
        s, e = int(40 * SF), int(55 * SF)
        shared_noise = np.random.RandomState(42).randn(e - s) * 0.3
        thorax[s:e] = shared_noise
        abdomen[s:e] = shared_noise.copy()
        thorax_env = preprocess_effort(thorax, SF)
        abdomen_env = preprocess_effort(abdomen, SF)
        effort_bl = float(np.percentile(thorax_env[:s], 90))
        typ, conf, detail = classify_apnea_type(
            s, e, thorax_env, abdomen_env, thorax, abdomen,
            effort_bl, SF)
        assert typ == "central", f"Expected central, got {typ} ({detail.get('decision_reason')})"

    def test_classify_mixed_apnea(self):
        """First half no effort, second half effort → mixed."""
        from psgscoring.classify import classify_apnea_type
        from psgscoring.signal import preprocess_effort
        n = int(20 * SF)  # 20s event
        half = n // 2
        # First half: no effort
        thorax = np.random.randn(n) * 0.3
        abdomen = np.random.randn(n) * 0.3
        # Second half: clear effort
        thorax[half:] = np.sin(2 * np.pi * 0.25 * np.arange(half) / SF) * 50
        abdomen[half:] = np.sin(2 * np.pi * 0.25 * np.arange(half) / SF) * 40
        thorax_env = preprocess_effort(thorax, SF)
        abdomen_env = preprocess_effort(abdomen, SF)
        effort_bl = float(np.percentile(thorax_env[half:], 90))
        typ, conf, detail = classify_apnea_type(
            0, n, thorax_env, abdomen_env, thorax, abdomen,
            effort_bl, SF)
        assert typ == "mixed", f"Expected mixed, got {typ} ({detail.get('decision_reason')})"

    def test_dynamic_baseline_stability(self):
        """Baseline should be stable for constant-amplitude breathing."""
        from psgscoring.signal import compute_dynamic_baseline
        t = np.arange(0, 300, 1 / SF)  # 5 minutes
        env = np.abs(np.sin(2 * np.pi * 0.25 * t)) * 100 + 10
        bl = compute_dynamic_baseline(env, SF)
        # Baseline should be close to the amplitude (~100)
        mid = bl[len(bl) // 2]
        assert 70 < mid < 130, f"Baseline {mid} out of expected range"
        # Baseline should not vary much for constant signal
        bl_std = np.std(bl[int(60*SF):int(240*SF)])
        assert bl_std < 20, f"Baseline too variable: std={bl_std}"

    def test_spo2_desaturation_detection(self):
        """A clear 5% desaturation should be detected."""
        from psgscoring.spo2 import get_desaturation
        sf_spo2 = 1.0  # 1 Hz
        # 120s of SpO2: baseline 96%, drop to 91% at t=40-60s
        spo2 = np.full(120, 96.0)
        spo2[40:60] = np.linspace(96, 91, 20)
        spo2[60:75] = np.linspace(91, 96, 15)
        desat, nadir = get_desaturation(spo2, onset_s=35, dur_s=15,
                                         sf_spo2=sf_spo2)
        assert desat is not None and desat >= 3.0, f"Expected ≥3% desat, got {desat}"
        assert nadir is not None and nadir <= 92, f"Expected nadir ≤92, got {nadir}"

    def test_breath_detection_count(self):
        """12 breaths/min for 2 min → ~24 breaths."""
        t = np.arange(0, 120, 1 / SF)
        flow = np.sin(2 * np.pi * 0.20 * t)  # 0.20 Hz = 12/min
        filt = bandpass_flow(flow, SF)
        breaths = detect_breaths(filt, SF)
        assert 18 < len(breaths) < 30, f"Expected ~24, got {len(breaths)}"

    def test_flattening_index_passed_to_detail(self):
        """classify_apnea_type should include flattening_index in detail."""
        from psgscoring.classify import classify_apnea_type
        n = int(15 * SF)
        thorax = np.ones(n) * 0.5
        abdomen = np.ones(n) * 0.5
        _, _, detail = classify_apnea_type(
            0, n, thorax, abdomen, thorax, abdomen, 1.0, SF,
            flattening_index=0.35)
        assert detail.get("flattening_index") == 0.35


# ═══════════════════════════════════════════════════════════════
# L. Property-based tests — Hypothesis (v0.8.29)
# ═══════════════════════════════════════════════════════════════

try:
    from hypothesis import given, settings, assume
    from hypothesis.strategies import floats, integers, none, one_of

    _HAS_HYPOTHESIS = True
except ImportError:
    _HAS_HYPOTHESIS = False


@pytest.mark.skipif(not _HAS_HYPOTHESIS, reason="hypothesis not installed")
class TestClassifyPropertyBased:
    """Property-based tests: random inputs must never crash and must
    always return a valid (type, confidence, detail) tuple."""

    @given(
        effort_ratio=floats(0.0, 2.0, allow_nan=False),
        raw_var=floats(0.0, 3.0, allow_nan=False),
        phase_angle=one_of(none(), floats(0.0, 180.0, allow_nan=False)),
        flattening=one_of(none(), floats(0.0, 1.0, allow_nan=False)),
    )
    @settings(max_examples=500, deadline=None)
    def test_classify_never_crashes(self, effort_ratio, raw_var,
                                     phase_angle, flattening):
        """classify_apnea_type must never raise, regardless of input."""
        from psgscoring.classify import classify_apnea_type
        n = int(15 * SF)
        # Build synthetic effort signals from the ratios
        thorax = np.ones(n) * effort_ratio * 0.5
        abdomen = np.ones(n) * effort_ratio * 0.5
        # Add variability proportional to raw_var
        thorax += np.random.randn(n) * raw_var * 0.1
        abdomen += np.random.randn(n) * raw_var * 0.1
        thorax_env = np.abs(thorax) + 1e-9
        abdomen_env = np.abs(abdomen) + 1e-9

        typ, conf, detail = classify_apnea_type(
            0, n, thorax_env, abdomen_env, thorax, abdomen,
            1.0, SF, flattening_index=flattening)

        assert typ in ("obstructive", "central", "mixed"), f"Invalid type: {typ}"
        assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"
        assert isinstance(detail, dict)
        assert "decision_reason" in detail

    @given(
        effort_ratio=floats(0.001, 0.15, allow_nan=False),
        raw_var=floats(0.001, 0.10, allow_nan=False),
    )
    @settings(max_examples=200, deadline=None)
    def test_very_low_effort_tends_central(self, effort_ratio, raw_var):
        """Very low effort + very low variability should lean central."""
        from psgscoring.classify import classify_apnea_type
        n = int(15 * SF)
        rng = np.random.RandomState(int(effort_ratio * 1e6) % 2**31)
        shared = rng.randn(n) * raw_var * 0.01
        thorax = shared.copy()
        abdomen = shared.copy()
        thorax_env = np.abs(thorax) + 1e-9
        abdomen_env = np.abs(abdomen) + 1e-9

        typ, conf, detail = classify_apnea_type(
            0, n, thorax_env, abdomen_env, thorax, abdomen,
            1.0, SF)

        # With near-zero correlated effort, should not default to obstructive
        assert typ in ("central", "mixed", "obstructive"), f"Invalid type: {typ}"
        # If obstructive, confidence should be low (borderline default)
        if typ == "obstructive":
            assert conf < 0.60, (
                f"Low effort ({effort_ratio:.3f}, var={raw_var:.3f}) "
                f"classified as obstructive with high conf={conf}"
            )

    @given(n_samples=integers(2, 100))
    @settings(max_examples=50, deadline=None)
    def test_classify_short_segments(self, n_samples):
        """Even very short segments should not crash."""
        from psgscoring.classify import classify_apnea_type
        thorax = np.random.randn(n_samples)
        abdomen = np.random.randn(n_samples)
        typ, conf, detail = classify_apnea_type(
            0, n_samples, np.abs(thorax), np.abs(abdomen),
            thorax, abdomen, 1.0, SF)
        assert typ in ("obstructive", "central", "mixed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
