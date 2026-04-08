#!/usr/bin/env python3
"""
batch_analyse.py — Batch PSG analysis for YASAFlaskified
========================================================

Process multiple EDF files from a directory and output a summary CSV
with AHI, OAHI, ODI, staging stats, and per-fix counters for each study.

Designed for the AZORG-YASA-2026-001 validation study: feed 50+ EDFs
and get a structured dataset suitable for Bland-Altman / κ analysis.

Usage
-----
    python batch_analyse.py /path/to/edfs/ -o /path/to/output/
    python batch_analyse.py /path/to/edfs/ --profile standard --workers 4
    python batch_analyse.py /path/to/edfs/ --profile strict standard sensitive

Author:  Bart Rombaut, MD — Slaapkliniek AZORG
Version: 0.8.33
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s %(message)s")
logger = logging.getLogger("batch")


def _analyse_single(edf_path: str, output_dir: str, profile: str) -> dict:
    """Analyse a single EDF file. Runs in a subprocess."""
    import mne
    import numpy as np
    mne.set_log_level("ERROR")

    from yasa_analysis import run_sleep_staging
    from pneumo_analysis import run_pneumo_analysis, detect_channels

    result = {
        "file": os.path.basename(edf_path),
        "profile": profile,
        "status": "error",
        "error": None,
    }

    try:
        t0 = time.time()
        raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)

        # Sleep staging
        staging = run_sleep_staging(raw)
        hypno = staging.get("hypnogram", [])
        if not hypno:
            result["error"] = "Staging failed: no hypnogram"
            return result

        # Channel detection
        channels = detect_channels(raw)

        # Respiratory analysis
        pneumo = run_pneumo_analysis(raw, hypno, scoring_profile=profile)
        resp = pneumo.get("respiratory", {})
        rsum = resp.get("summary", {})
        spo2 = pneumo.get("spo2", {}).get("summary", {})
        arousal = pneumo.get("arousal", {}).get("summary", {})

        # Sleep statistics
        from collections import Counter
        stage_counts = Counter(hypno)
        tst_min = sum(1 for s in hypno if s in ("N1","N2","N3","R")) * 0.5
        se = tst_min / (len(hypno) * 0.5) * 100 if hypno else 0

        elapsed = time.time() - t0

        result.update({
            "status": "ok",
            "duration_s": round(elapsed, 1),
            "n_epochs": len(hypno),
            "tst_min": round(tst_min, 1),
            "sleep_efficiency_pct": round(se, 1),
            "n_W": stage_counts.get("W", 0),
            "n_N1": stage_counts.get("N1", 0),
            "n_N2": stage_counts.get("N2", 0),
            "n_N3": stage_counts.get("N3", 0),
            "n_REM": stage_counts.get("R", 0),
            # Respiratory
            "ahi_total": rsum.get("ahi_total"),
            "oahi": rsum.get("oahi"),
            "cahi": rsum.get("cahi"),
            "ahi_rem": rsum.get("ahi_rem"),
            "ahi_nrem": rsum.get("ahi_nrem"),
            "ahi_supine": rsum.get("ahi_supine"),
            "ahi_nonsupine": rsum.get("ahi_nonsupine"),
            "n_apneas": rsum.get("n_apneas"),
            "n_hypopneas": rsum.get("n_hypopneas"),
            "n_obstructive": rsum.get("n_obstructive"),
            "n_central": rsum.get("n_central"),
            "n_mixed": rsum.get("n_mixed"),
            "rera_index": rsum.get("rera_index"),
            "rdi": rsum.get("rdi"),
            # Fix counters
            "n_spo2_cross_contaminated": rsum.get("n_spo2_cross_contaminated", 0),
            "n_csr_flagged": rsum.get("n_csr_flagged", 0),
            "n_low_conf_noise": rsum.get("n_low_conf_noise", 0),
            "n_low_conf_borderline": rsum.get("n_low_conf_borderline", 0),
            "n_gap_excluded": rsum.get("n_gap_excluded", 0),
            "n_local_baseline_rejected": resp.get("n_local_baseline_rejected", 0),
            "n_ecg_reclassified_central": rsum.get("n_ecg_reclassified_central", 0),
            "ahi_csr_corrected": rsum.get("ahi_csr_corrected"),
            "ahi_excl_noise": rsum.get("ahi_excl_noise"),
            # SpO2
            "baseline_spo2": spo2.get("baseline_spo2"),
            "min_spo2": spo2.get("min_spo2"),
            "mean_spo2": spo2.get("mean_spo2"),
            "odi_3pct": spo2.get("odi_3pct"),
            "odi_4pct": spo2.get("odi_4pct"),
            "pct_below_90": spo2.get("pct_below_90"),
            "low_baseline_warning": spo2.get("low_baseline_warning", False),
            # Arousal
            "arousal_index": arousal.get("arousal_index"),
            # PLM
            "plmi": pneumo.get("plm", {}).get("summary", {}).get("plmi"),
        })

        # Save full JSON result
        json_path = os.path.join(output_dir, Path(edf_path).stem + f"_{profile}.json")
        with open(json_path, "w") as f:
            json.dump(pneumo, f, indent=2, default=str)

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        logger.error("Failed %s: %s", edf_path, traceback.format_exc())

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Batch PSG analysis for validation study")
    parser.add_argument("input_dir", help="Directory with EDF files")
    parser.add_argument("-o", "--output-dir", default=None,
                        help="Output directory (default: input_dir/batch_results/)")
    parser.add_argument("--profile", nargs="+", default=["standard"],
                        choices=["strict", "standard", "sensitive"],
                        help="Scoring profile(s) to run (default: standard)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers (default: 1)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of EDFs to process")

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else input_dir / "batch_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    edfs = sorted(input_dir.glob("*.edf"))
    if args.limit:
        edfs = edfs[:args.limit]

    if not edfs:
        logger.error("No EDF files found in %s", input_dir)
        return 1

    logger.info("Found %d EDF files, profiles: %s, workers: %d",
                len(edfs), args.profile, args.workers)

    all_results = []

    # Add myproject to path for imports
    sys.path.insert(0, str(Path(__file__).parent))

    for profile in args.profile:
        logger.info("=== Profile: %s ===", profile)

        if args.workers <= 1:
            for edf in edfs:
                logger.info("Processing %s [%s]...", edf.name, profile)
                r = _analyse_single(str(edf), str(output_dir), profile)
                all_results.append(r)
                status = r["status"]
                ahi = r.get("ahi_total", "?")
                logger.info("  → %s  AHI=%s  (%.1fs)",
                            status, ahi, r.get("duration_s", 0))
        else:
            with ProcessPoolExecutor(max_workers=args.workers) as executor:
                futures = {
                    executor.submit(_analyse_single, str(edf), str(output_dir), profile): edf
                    for edf in edfs
                }
                for future in as_completed(futures):
                    edf = futures[future]
                    r = future.result()
                    all_results.append(r)
                    logger.info("  %s → %s  AHI=%s",
                                edf.name, r["status"], r.get("ahi_total", "?"))

    # Write summary CSV
    csv_path = output_dir / "batch_summary.csv"
    if all_results:
        keys = all_results[0].keys()
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_results)
        logger.info("Summary CSV: %s", csv_path)

    n_ok = sum(1 for r in all_results if r["status"] == "ok")
    n_err = sum(1 for r in all_results if r["status"] == "error")
    logger.info("Done: %d OK, %d errors out of %d total", n_ok, n_err, len(all_results))

    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
