#!/usr/bin/env python3
"""
generate_demo_edf.py — Create a synthetic demo EDF for YASAFlaskified
=====================================================================

Generates a ~30-minute synthetic PSG recording with clearly visible:
  - Normal breathing epochs
  - Obstructive apneas (flow cessation, effort present)
  - Central apneas (flow + effort cessation)
  - Hypopneas (partial flow reduction + desaturation)
  - Arousals (brief alpha bursts after events)
  - Position changes (supine/lateral)

The resulting EDF can be uploaded to slaapkliniek.be for platform
evaluation without any patient data or GDPR concerns.

Usage:
    python generate_demo_edf.py
    python generate_demo_edf.py --duration 60 --output demo_60min.edf

Author:  Bart Rombaut, MD — Slaapkliniek AZORG
Version: 0.8.27
"""

from __future__ import annotations
import argparse
import numpy as np

DEMO_SF = 256       # Hz
DEMO_DURATION_MIN = 30


def _breathing_signal(t, rate_hz=0.25, amp=1.0):
    """Normal sinusoidal breathing."""
    return amp * np.sin(2 * np.pi * rate_hz * t)


def _eeg_signal(t, stage="N2"):
    """Simplified EEG: stage-dependent spectral content."""
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(len(t)) * 15  # µV
    if stage == "W":
        # Alpha (8-12 Hz)
        return noise + 20 * np.sin(2 * np.pi * 10 * t)
    elif stage == "N1":
        return noise + 10 * np.sin(2 * np.pi * 6 * t)
    elif stage == "N2":
        # Spindles (12-14 Hz bursts) + K-complexes
        spindle = 15 * np.sin(2 * np.pi * 13 * t)
        # Add spindle bursts every ~30s
        spindle_env = np.zeros(len(t))
        for burst_t in np.arange(5, t[-1], 30):
            mask = (t >= burst_t) & (t < burst_t + 0.5)
            spindle_env[mask] = 1.0
        return noise + spindle * spindle_env
    elif stage == "N3":
        # Delta (0.5-2 Hz), high amplitude
        return noise + 60 * np.sin(2 * np.pi * 1 * t)
    elif stage == "R":
        # Low amplitude, mixed frequency
        return noise * 0.7 + 8 * np.sin(2 * np.pi * 5 * t)
    return noise


def generate_demo_edf(duration_min: int = DEMO_DURATION_MIN,
                       output_path: str = "demo_recording.edf"):
    """Generate a synthetic demo EDF file."""
    try:
        import pyedflib
    except ImportError:
        print("ERROR: pyedflib required. Install: pip install pyedflib")
        return

    sf = DEMO_SF
    n_samples = int(duration_min * 60 * sf)
    t = np.arange(n_samples) / sf

    rng = np.random.default_rng(2026)

    # ── Define sleep stages (30s epochs) ───────────────────────────
    n_epochs = int(duration_min * 2)
    # Simple progression: W -> N1 -> N2 -> N3 -> N2 -> REM -> N2 ...
    stage_seq = (["W"] * 2 + ["N1"] * 2 + ["N2"] * 6 + ["N3"] * 4 +
                 ["N2"] * 4 + ["R"] * 5 + ["N2"] * 6 + ["N3"] * 3 +
                 ["N2"] * 4 + ["R"] * 4 + ["N2"] * 5 + ["W"] * 2)
    # Repeat/trim to match duration
    while len(stage_seq) < n_epochs:
        stage_seq += stage_seq
    stage_seq = stage_seq[:n_epochs]

    # ── Generate EEG ──────────────────────────────────────────────
    eeg = np.zeros(n_samples)
    for ep_i, stage in enumerate(stage_seq):
        s = ep_i * 30 * sf
        e = min(s + 30 * sf, n_samples)
        t_ep = t[s:e] - t[s]
        eeg[s:e] = _eeg_signal(t_ep, stage)

    # ── Generate EOG (slow eye movements in N1, REMs in REM) ─────
    eog = rng.standard_normal(n_samples) * 5
    for ep_i, stage in enumerate(stage_seq):
        s = ep_i * 30 * sf
        e = min(s + 30 * sf, n_samples)
        if stage == "N1":
            eog[s:e] += 30 * np.sin(2 * np.pi * 0.3 * (t[s:e] - t[s]))
        elif stage == "R":
            # REMs: random saccades
            for _ in range(rng.integers(3, 8)):
                rem_t = rng.integers(s, max(s+1, e - int(0.5*sf)))
                rem_e = min(rem_t + int(0.3 * sf), n_samples)
                eog[rem_t:rem_e] += rng.choice([-1, 1]) * 80

    # ── Generate EMG (low in REM, higher in wake) ─────────────────
    emg = rng.standard_normal(n_samples) * 3
    for ep_i, stage in enumerate(stage_seq):
        s = ep_i * 30 * sf
        e = min(s + 30 * sf, n_samples)
        if stage == "W":
            emg[s:e] *= 3
        elif stage == "R":
            emg[s:e] *= 0.3

    # ── Generate respiratory channels ─────────────────────────────
    flow = np.zeros(n_samples)
    thorax = np.zeros(n_samples)
    abdomen = np.zeros(n_samples)
    spo2 = np.full(n_samples, 96.0)

    # Normal breathing everywhere first
    flow[:] = _breathing_signal(t, rate_hz=0.25, amp=100)
    thorax[:] = _breathing_signal(t, rate_hz=0.25, amp=50)
    abdomen[:] = _breathing_signal(t, rate_hz=0.25, amp=40)

    # ── Insert respiratory events ─────────────────────────────────
    events_inserted = []

    def _insert_apnea(start_s, dur_s, apnea_type="obstructive"):
        s = int(start_s * sf)
        e = min(int((start_s + dur_s) * sf), n_samples)
        flow[s:e] *= 0.02  # near-zero flow
        if apnea_type == "obstructive":
            # Effort PRESENT but paradoxical
            thorax[s:e] *= 1.5
            abdomen[s:e] *= -1.2  # paradoxical
        elif apnea_type == "central":
            thorax[s:e] *= 0.05
            abdomen[s:e] *= 0.05
        # Desaturation 10-25s after event start
        desat_s = min(int((start_s + 15) * sf), n_samples)
        desat_e = min(int((start_s + dur_s + 20) * sf), n_samples)
        desat_depth = rng.uniform(4, 8)
        desat_curve = np.linspace(0, desat_depth, desat_e - desat_s)
        if desat_s < desat_e <= n_samples:
            spo2[desat_s:desat_e] -= desat_curve
            # Recovery
            rec_e = min(desat_e + int(15 * sf), n_samples)
            if desat_e < rec_e:
                spo2[desat_e:rec_e] += np.linspace(0, desat_depth, rec_e - desat_e)
        events_inserted.append({"type": apnea_type, "onset_s": start_s, "duration_s": dur_s})

    def _insert_hypopnea(start_s, dur_s):
        s = int(start_s * sf)
        e = min(int((start_s + dur_s) * sf), n_samples)
        flow[s:e] *= 0.45  # 55% reduction
        thorax[s:e] *= 0.7
        abdomen[s:e] *= 0.7
        desat_s = min(int((start_s + 10) * sf), n_samples)
        desat_e = min(int((start_s + dur_s + 15) * sf), n_samples)
        if desat_s < desat_e <= n_samples:
            spo2[desat_s:desat_e] -= np.linspace(0, 4, desat_e - desat_s)
            rec_e = min(desat_e + int(10 * sf), n_samples)
            if desat_e < rec_e:
                spo2[desat_e:rec_e] += np.linspace(0, 4, rec_e - desat_e)
        events_inserted.append({"type": "hypopnea", "onset_s": start_s, "duration_s": dur_s})

    # Place events in sleep epochs (skip wake)
    event_times = [120, 150, 210, 260, 320, 380, 440, 510,
                   580, 650, 720, 800, 880, 960, 1050, 1140,
                   1230, 1320, 1410, 1500]
    for i, et in enumerate(event_times):
        if et + 30 > duration_min * 60:
            break
        if i % 5 == 0:
            _insert_apnea(et, rng.uniform(12, 25), "obstructive")
        elif i % 5 == 1:
            _insert_apnea(et, rng.uniform(12, 20), "central")
        else:
            _insert_hypopnea(et, rng.uniform(12, 22))

    # Clamp SpO2
    spo2 = np.clip(spo2, 70, 100)

    # ── Position channel (supine first half, lateral second) ──────
    position = np.full(n_samples, 2.0)  # supine
    position[n_samples // 2:] = 1.0     # left lateral

    # ── Heart rate proxy (ECG-like) ───────────────────────────────
    hr_hz = 1.2  # 72 bpm
    ecg = np.zeros(n_samples)
    beat_interval = int(sf / hr_hz)
    for i in range(0, n_samples, beat_interval):
        if i + 5 < n_samples:
            ecg[i:i+3] = 500
            ecg[i+3:i+5] = -200

    # ── Write EDF with pyedflib ───────────────────────────────────
    channels = [
        ("EEG C3-A2",    "uV",   eeg,      -500, 500),
        ("EOG E1-A2",    "uV",   eog,      -500, 500),
        ("EMG chin",     "uV",   emg,      -100, 100),
        ("Nasal Pres",   "cmH2O", flow,    -200, 200),
        ("Thermistor",   "mV",   flow * 0.8, -200, 200),
        ("Thorax",       "mV",   thorax,   -200, 200),
        ("Abdomen",      "mV",   abdomen,  -200, 200),
        ("SpO2",         "%",    spo2,      50,  100),
        ("Pulse",        "bpm",  np.full(n_samples, 72.0) + rng.standard_normal(n_samples) * 2, 30, 200),
        ("Position",     "",     position,   0,    5),
        ("ECG II",       "mV",   ecg,     -1000, 1000),
        ("Snore",        "dB",   rng.standard_normal(n_samples) * 2, -50, 50),
    ]

    n_ch = len(channels)
    writer = pyedflib.EdfWriter(output_path, n_ch, file_type=pyedflib.FILETYPE_EDFPLUS)

    writer.setPatientName("DEMO_PATIENT")
    writer.setPatientCode("DEMO_001")
    writer.setGender("")
    writer.setTechnician("YASAFlaskified")
    writer.setRecordingAdditional("Synthetic demo recording — no patient data")

    for i, (label, dim, data, phys_min, phys_max) in enumerate(channels):
        writer.setSignalHeader(i, {
            "label": label,
            "dimension": dim,
            "sample_frequency": sf,
            "physical_min": phys_min,
            "physical_max": phys_max,
            "digital_min": -32768,
            "digital_max": 32767,
            "transducer": "Synthetic",
            "prefilter": "",
        })

    # Write data in 1-second blocks
    block_samples = sf
    n_blocks = n_samples // block_samples
    for b in range(n_blocks):
        s = b * block_samples
        e = s + block_samples
        block_data = [ch[3][s:e].astype(np.float64) for ch in channels]
        writer.writeSamples(block_data)

    writer.close()

    print(f"Created: {output_path}")
    print(f"  Duration: {duration_min} min, {n_ch} channels, {sf} Hz")
    print(f"  Events: {len(events_inserted)} respiratory events inserted")
    print(f"  Stages: {len(stage_seq)} epochs")
    for ev in events_inserted:
        print(f"    {ev['type']:15s}  t={ev['onset_s']:.0f}s  dur={ev['duration_s']:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic demo EDF")
    parser.add_argument("--duration", type=int, default=30,
                        help="Duration in minutes (default: 30)")
    parser.add_argument("--output", default="demo_recording.edf",
                        help="Output EDF path")
    args = parser.parse_args()
    generate_demo_edf(args.duration, args.output)


if __name__ == "__main__":
    main()
