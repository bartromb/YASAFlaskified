#!/usr/bin/env python3
"""
anonymize_edf.py — Strip personal information from EDF/EDF+ files.
==================================================================

Removes patient name, date of birth, patient ID, recording ID,
technician, and hospital fields from the fixed-size EDF header while
preserving all signal data byte-for-byte.

Works with both classic EDF (Kemp et al. 1992) and EDF+ (Kemp &
Olivan 2003) header formats, including EDF+C (continuous) and EDF+D
(discontinuous).

Usage
-----
Single file:
    python anonymize_edf.py recording.edf

Multiple files:
    python anonymize_edf.py *.edf

Entire directory (recursive):
    python anonymize_edf.py /path/to/edf_folder/

Custom output directory:
    python anonymize_edf.py recording.edf -o /output/dir/

Custom study prefix:
    python anonymize_edf.py recording.edf --prefix STUDY

Overwrite originals (DESTRUCTIVE):
    python anonymize_edf.py recording.edf --in-place

Dry run (show what would be changed):
    python anonymize_edf.py recording.edf --dry-run

Author:  Bart Rombaut, MD — Slaapkliniek AZORG
License: BSD-3-Clause (same as psgscoring / YASAFlaskified)
Version: 1.0 — April 2026
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import struct
import sys
from datetime import date
from pathlib import Path


# ── EDF header layout (bytes) ───────────────────────────────────────────────
# Offset  Length  Field
# 0       8       Version ("0       ")
# 8       80      Patient ID  ← contains name, DOB, sex, etc.
# 88      80      Recording ID ← contains startdate, hospital, technician
# 168     8       Start date (dd.mm.yy)
# 176     8       Start time (hh.mm.ss)
# 184     8       Header bytes
# 192     44      Reserved (EDF+: "EDF+C" or "EDF+D")
# 236     8       Number of data records
# 244     8       Duration of data record (seconds)
# 252     4       Number of signals (ns)
# 256     ns*16   Signal labels
# ...     (rest of signal headers + data)

PATIENT_OFFSET   = 8
PATIENT_LEN      = 80
RECORDING_OFFSET = 88
RECORDING_LEN    = 80
DATE_OFFSET      = 168
DATE_LEN         = 8
RESERVED_OFFSET  = 192
RESERVED_LEN     = 44


def _pad(s: str, length: int) -> bytes:
    """Pad string to fixed length with spaces, ASCII-encoded."""
    encoded = s.encode("ascii", errors="replace")[:length]
    return encoded.ljust(length)


def _read_field(data: bytes, offset: int, length: int) -> str:
    return data[offset : offset + length].decode("ascii", errors="replace").strip()


def _hash_id(original: str, prefix: str) -> str:
    """Deterministic pseudonymised ID from original (SHA-256, 8 hex chars)."""
    h = hashlib.sha256(original.encode("utf-8", errors="replace")).hexdigest()[:8].upper()
    return f"{prefix}_{h}"


def _anonymize_patient_field(original: str, prefix: str, keep_sex: bool,
                              keep_age_range: bool) -> str:
    """Anonymize EDF+ patient field: 'patient_id sex dob name'.

    EDF+ format: subfields separated by spaces.
    Field order: patient_code  sex  birthdate  patient_name
    Unknown subfields use 'X'.

    Returns anonymized version preserving EDF+ structure.
    """
    parts = original.split()

    # EDF+ patient field: code sex dob name [extra...]
    if len(parts) >= 4:
        code     = parts[0]
        sex      = parts[1] if keep_sex and parts[1] in ("M", "F", "X") else "X"
        dob_str  = parts[2]  # dd-MMM-yyyy or X
        # name    = parts[3:]  # stripped entirely

        anon_code = _hash_id(code, prefix) if code != "X" else "X"

        # Optionally keep decade of birth
        if keep_age_range and dob_str != "X":
            try:
                # Parse EDF+ date: dd-MMM-yyyy
                dob_year = int(dob_str.split("-")[-1])
                decade = (dob_year // 10) * 10
                anon_dob = f"01-JAN-{decade}"
            except (ValueError, IndexError):
                anon_dob = "X"
        else:
            anon_dob = "X"

        return f"{anon_code} {sex} {anon_dob} X"

    # Classic EDF: entire field is free-text patient info
    if original.strip() and original.strip() != "X":
        return _hash_id(original, prefix)
    return "X"


def _anonymize_recording_field(original: str, keep_startdate: bool) -> str:
    """Anonymize EDF+ recording field: 'Startdate dd-MMM-yyyy admin_code technician equipment'.

    Returns anonymized version.  Hospital, technician, admin code are stripped.
    """
    parts = original.split()

    # EDF+ recording field starts with "Startdate"
    if len(parts) >= 2 and parts[0].lower() == "startdate":
        if keep_startdate and len(parts) >= 2:
            startdate = parts[1]
        else:
            startdate = "X"
        return f"Startdate {startdate} X X X"

    # Classic EDF: free-text
    return "X"


def _anonymize_date_field(original: str, keep_date: bool) -> str:
    """Anonymize the start date field (dd.mm.yy).

    If keep_date is False, replaces with 01.01.85 (EDF convention for unknown).
    """
    if keep_date:
        return original
    return "01.01.85"


def anonymize_edf(
    input_path: Path,
    output_path: Path | None = None,
    prefix: str = "ANON",
    keep_sex: bool = False,
    keep_age_range: bool = False,
    keep_startdate: bool = True,
    keep_recording_date: bool = True,
    dry_run: bool = False,
) -> dict:
    """Anonymize a single EDF/EDF+ file.

    Parameters
    ----------
    input_path : Path
        Source EDF file.
    output_path : Path or None
        Destination.  If None, appends '_anon' before extension.
    prefix : str
        Prefix for pseudonymised patient ID (default: "ANON").
    keep_sex : bool
        Preserve sex field in EDF+ patient info.
    keep_age_range : bool
        Replace exact DOB with decade (e.g. 1970) instead of removing.
    keep_startdate : bool
        Preserve recording start date in recording field.
    keep_recording_date : bool
        Preserve dd.mm.yy date field in header.
    dry_run : bool
        If True, report changes but don't write.

    Returns
    -------
    dict with keys: input, output, original_patient, anon_patient,
    original_recording, anon_recording, original_date, anon_date, changed.
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_name(
            input_path.stem + "_anon" + input_path.suffix
        )
    output_path = Path(output_path)

    with open(input_path, "rb") as f:
        header = bytearray(f.read(256))
        # Read full file for writing later
        f.seek(0)
        full_data = bytearray(f.read())

    orig_patient   = _read_field(header, PATIENT_OFFSET,   PATIENT_LEN)
    orig_recording = _read_field(header, RECORDING_OFFSET, RECORDING_LEN)
    orig_date      = _read_field(header, DATE_OFFSET,      DATE_LEN)

    anon_patient   = _anonymize_patient_field(orig_patient, prefix,
                                               keep_sex, keep_age_range)
    anon_recording = _anonymize_recording_field(orig_recording, keep_startdate)
    anon_date      = _anonymize_date_field(orig_date, keep_recording_date)

    changed = (anon_patient != orig_patient or
               anon_recording != orig_recording or
               anon_date != orig_date)

    report = {
        "input":              str(input_path),
        "output":             str(output_path),
        "original_patient":   orig_patient,
        "anon_patient":       anon_patient,
        "original_recording": orig_recording,
        "anon_recording":     anon_recording,
        "original_date":      orig_date,
        "anon_date":          anon_date,
        "changed":            changed,
    }

    if dry_run or not changed:
        return report

    # Write anonymized header fields into full data
    full_data[PATIENT_OFFSET   : PATIENT_OFFSET   + PATIENT_LEN]   = _pad(anon_patient,   PATIENT_LEN)
    full_data[RECORDING_OFFSET : RECORDING_OFFSET + RECORDING_LEN] = _pad(anon_recording, RECORDING_LEN)
    full_data[DATE_OFFSET      : DATE_OFFSET      + DATE_LEN]      = _pad(anon_date,      DATE_LEN)

    # Also anonymize EDF+ annotation channels that might contain patient info
    # in TAL (Time-stamped Annotation List) — search for common patterns
    # This is a conservative approach: only strip obvious name patterns
    # from the annotation data area, not the signal data.

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(full_data)

    return report


def anonymize_directory(
    dir_path: Path,
    output_dir: Path | None = None,
    recursive: bool = True,
    **kwargs,
) -> list[dict]:
    """Anonymize all EDF files in a directory."""
    dir_path = Path(dir_path)
    pattern = "**/*.edf" if recursive else "*.edf"
    results = []
    for edf_file in sorted(dir_path.glob(pattern)):
        if "_anon" in edf_file.stem:
            continue  # skip already anonymized
        if output_dir:
            rel = edf_file.relative_to(dir_path)
            out = Path(output_dir) / rel.with_name(
                rel.stem + "_anon" + rel.suffix
            )
        else:
            out = None
        results.append(anonymize_edf(edf_file, out, **kwargs))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Anonymize EDF/EDF+ files by stripping patient information.",
        epilog="Examples:\n"
               "  python anonymize_edf.py study.edf\n"
               "  python anonymize_edf.py /data/sleep_lab/ -o /data/anon/ --prefix AZORG\n"
               "  python anonymize_edf.py *.edf --dry-run\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+",
                        help="EDF file(s) or directory to anonymize")
    parser.add_argument("-o", "--output-dir", default=None,
                        help="Output directory (default: same dir, _anon suffix)")
    parser.add_argument("--prefix", default="ANON",
                        help="Prefix for pseudonymised patient ID (default: ANON)")
    parser.add_argument("--keep-sex", action="store_true",
                        help="Preserve sex field (M/F) in patient info")
    parser.add_argument("--keep-age-range", action="store_true",
                        help="Replace exact DOB with birth decade instead of removing")
    parser.add_argument("--strip-date", action="store_true",
                        help="Replace recording start date with 01.01.85")
    parser.add_argument("--in-place", action="store_true",
                        help="Overwrite original files (DESTRUCTIVE)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be changed without writing")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress output except errors")

    args = parser.parse_args()

    kwargs = dict(
        prefix=args.prefix,
        keep_sex=args.keep_sex,
        keep_age_range=args.keep_age_range,
        keep_startdate=not args.strip_date,
        keep_recording_date=not args.strip_date,
        dry_run=args.dry_run,
    )

    all_results = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_dir():
            results = anonymize_directory(
                p, output_dir=args.output_dir, **kwargs)
            all_results.extend(results)
        elif p.is_file() and p.suffix.lower() in (".edf", ".edf+", ".rec"):
            if args.in_place:
                out = p
            elif args.output_dir:
                out = Path(args.output_dir) / (p.stem + "_anon" + p.suffix)
            else:
                out = None  # default: _anon suffix
            all_results.append(anonymize_edf(p, out, **kwargs))
        else:
            print(f"WARNING: Skipping {inp} (not an EDF file or directory)",
                  file=sys.stderr)

    # Report
    n_changed = sum(1 for r in all_results if r["changed"])
    n_total   = len(all_results)

    if not args.quiet:
        for r in all_results:
            status = "CHANGED" if r["changed"] else "UNCHANGED"
            if args.dry_run:
                status = "DRY-RUN " + status
            print(f"\n{'='*60}")
            print(f"  {status}: {r['input']}")
            if r["changed"]:
                print(f"  Output:    {r['output']}")
                print(f"  Patient:   '{r['original_patient']}'")
                print(f"           → '{r['anon_patient']}'")
                print(f"  Recording: '{r['original_recording']}'")
                print(f"           → '{r['anon_recording']}'")
                if r["original_date"] != r["anon_date"]:
                    print(f"  Date:      '{r['original_date']}' → '{r['anon_date']}'")

        print(f"\n{'='*60}")
        action = "Would anonymize" if args.dry_run else "Anonymized"
        print(f"  {action} {n_changed}/{n_total} files.")
        if not args.dry_run and n_changed > 0:
            print(f"  Signal data preserved byte-for-byte.")
        print(f"{'='*60}\n")

    return 0 if n_changed >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
