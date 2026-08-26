"""BDF wordt natief gelezen, niet eerst naar EDF omgezet.

WAAROM DIT ERIN ZIT
-------------------
BDF is 24-bit, EDF is 16-bit. Een centrum dat zijn BDF eerst exporteert naar EDF
om te kunnen uploaden, scoort daarna de CONVERSIE mee: bij verkeerde schaling
knipt of kwantiseert het EEG, en de uitkomst zegt iets over de exporter in
plaats van over de nacht. Een gebruiker meldde precies dat (25-08-2026):
downsampling naar 125 Hz plus een 50 Hz-notch, en de resulterende EDF zag er
"a bit discontinuous" uit.

WAT DEZE TESTEN BEWAKEN
-----------------------
`test_read_raw_edf_faalt_op_dezelfde_bdf` is de belangrijkste: hij laat zien dat
de dispatcher dragend is. Zou `read_raw_signal` stilletjes altijd de EDF-lezer
kiezen, dan valt die test om -- en zonder hem zou een BDF-upload pas in
productie stuklopen.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_io import (  # noqa: E402
    is_signal_file,
    read_raw_signal,
    signal_extension,
    source_candidates,
)

FS = 100
DUUR_S = 30
AMPLITUDE_UV = 50.0
HIER = os.path.dirname(os.path.abspath(__file__))
JS_PATH = os.path.join(HIER, "..", "static", "edf_anonymize.js")


def _sinus():
    n = FS * DUUR_S
    t = np.arange(n) / FS
    return (AMPLITUDE_UV * np.sin(2 * np.pi * 10 * t)).astype(np.float64)


def _schrijf(path, bdf: bool):
    """Een echte opname van twee kanalen, 24-bit (BDF) of 16-bit (EDF)."""
    import pyedflib

    soort = pyedflib.FILETYPE_BDFPLUS if bdf else pyedflib.FILETYPE_EDFPLUS
    dmax, dmin = (8388607, -8388608) if bdf else (32767, -32768)
    w = pyedflib.EdfWriter(str(path), 2, file_type=soort)
    w.setSignalHeaders([
        {"label": lab, "dimension": "uV", "sample_frequency": FS,
         "physical_max": 500.0, "physical_min": -500.0,
         "digital_max": dmax, "digital_min": dmin,
         "transducer": "", "prefilter": ""}
        for lab in ("C3-M2", "C4-M1")
    ])
    sig = _sinus()
    w.writeSamples([sig, sig * 0.8])
    w.close()
    return str(path)


@pytest.fixture
def bdf(tmp_path):
    return _schrijf(tmp_path / "opname.bdf", bdf=True)


@pytest.fixture
def edf(tmp_path):
    return _schrijf(tmp_path / "opname.edf", bdf=False)


def test_een_echte_bdf_wordt_gelezen_met_de_juiste_amplitude(bdf):
    raw = read_raw_signal(bdf, preload=True, verbose=False)
    assert raw.ch_names == ["C3-M2", "C4-M1"]
    assert raw.info["sfreq"] == pytest.approx(FS)
    assert raw.n_times == FS * DUUR_S
    p95 = float(np.percentile(np.abs(raw.get_data()[0]) * 1e6, 95))
    # Een 50 µV-sinus: p95 van |sin| ligt rond 0,95 x amplitude.
    assert 40.0 < p95 < 52.0, p95


def test_het_is_werkelijk_24_bits(bdf):
    """De BIOSEMI-magic staat op byte 0; EDF heeft daar '0'."""
    with open(bdf, "rb") as f:
        assert f.read(8) == b"\xffBIOSEMI"


def test_read_raw_edf_faalt_op_dezelfde_bdf(bdf):
    """Zonder dispatcher zou een BDF-upload pas in productie stuklopen.

    Deze test is de reden dat signal_io bestaat. Valt hij om omdat MNE ooit
    BDF via read_raw_edf gaat accepteren, controleer dan of de amplitudes nog
    kloppen voordat je de dispatcher weghaalt.
    """
    import mne

    with pytest.raises(Exception):
        mne.io.read_raw_edf(bdf, preload=True, verbose=False)


def test_edf_blijft_gewoon_werken(edf):
    raw = read_raw_signal(edf, preload=True, verbose=False)
    assert raw.ch_names == ["C3-M2", "C4-M1"]
    p95 = float(np.percentile(np.abs(raw.get_data()[0]) * 1e6, 95))
    assert 40.0 < p95 < 52.0, p95


def test_extensieherkenning():
    assert is_signal_file("a.BDF") and is_signal_file("a.edf")
    assert not is_signal_file("a.txt") and not is_signal_file("a")
    assert signal_extension("x.BDF") == ".bdf"
    assert signal_extension("x.edf") == ".edf"
    assert signal_extension("zonder") == ".edf"


def test_de_upload_houdt_de_bdf_extensie_vast():
    """Hernoemen naar .edf zou de lezer verkeerd kiezen — stil en fout."""
    from app import FileUploadHandler

    h = FileUploadHandler.__new__(FileUploadHandler)
    assert h.sanitize_filename("nacht.bdf") == "nacht.bdf"
    assert h.sanitize_filename("nacht.BDF").lower().endswith(".bdf")
    assert h.sanitize_filename("nacht.edf") == "nacht.edf"
    assert h.sanitize_filename("nacht") == "nacht.edf"


def test_bronbestand_terugvinden_vindt_ook_bdf(tmp_path):
    job = "abc123"
    (tmp_path / f"{job}_opname.bdf").write_bytes(b"x")
    (tmp_path / f"{job}_scored.edf").write_bytes(b"x")
    gevonden = source_candidates(str(tmp_path), job)
    assert [os.path.basename(p) for p in gevonden] == [f"{job}_opname.bdf"], gevonden


def test_bronbestand_negeert_onze_eigen_uitvoer(tmp_path):
    """Zonder deze filter voedt een tweede analyse zichzelf met haar resultaat."""
    job = "def456"
    (tmp_path / f"{job}_scored.edf").write_bytes(b"x")
    assert source_candidates(str(tmp_path), job) == []


def test_anonimiseren_van_een_bdf_laat_de_data_met_rust(bdf, tmp_path):
    """De header is in BDF net zo ingedeeld als in EDF; alleen byte 0 verschilt."""
    import hashlib

    from edf_anonymize import anonymize_file_in_place

    doel = str(tmp_path / "kopie.bdf")
    shutil.copy(bdf, doel)
    with open(doel, "rb") as f:
        f.seek(256)
        data_voor = hashlib.sha256(f.read()).hexdigest()

    na = anonymize_file_in_place(doel, study_code="TEST")
    assert na.patient.startswith("TEST")

    with open(doel, "rb") as f:
        kop = f.read(256)
        data_na = hashlib.sha256(f.read()).hexdigest()
    assert kop[:8] == b"\xffBIOSEMI", "de BIOSEMI-magic is overschreven"
    assert data_voor == data_na, "de signaaldata is aangeraakt"
    read_raw_signal(doel, preload=False, verbose=False)   # nog leesbaar


@pytest.mark.parametrize("sjabloon", ["index.html", "upload.html"])
def test_de_uploadvelden_accepteren_bdf(sjabloon):
    pad = os.path.join(HIER, "..", "templates", sjabloon)
    with open(pad, encoding="utf-8") as f:
        html = f.read()
    assert 'accept=".edf,.bdf"' in html, f"{sjabloon} accepteert nog alleen .edf"
    assert ".edf" in html


def test_de_anonimiseerder_in_de_browser_behoudt_de_extensie(tmp_path):
    """Een BDF die als .edf aankomt, wordt serverzijdig als 16-bit gelezen.

    Het script is geen CommonJS-module maar een IIFE die zich aan `global`
    hangt; het wordt dus geëvalueerd zoals in de browser, net als in
    test_edf_anonymize_js_parity.py.
    """
    if shutil.which("node") is None:
        pytest.skip("node niet beschikbaar — de extensieregel is nu ONBEWAAKT")
    runner = tmp_path / "runner.js"
    runner.write_text(
        "const fs = require('fs');\n"
        "global.window = global;\n"
        "global.crypto = require('crypto').webcrypto;\n"
        "eval(fs.readFileSync(process.argv[2], 'utf8'));\n"
        "const g = window.EdfAnonymize;\n"
        "process.stdout.write(JSON.stringify([\n"
        "  g.safeFilename('ANON_1234', '.bdf'),\n"
        "  g.safeFilename('ANON_1234', '.edf'),\n"
        "  g.safeFilename('ANON_1234'),\n"
        "  g.safeFilename('ANON_1234', '.exe'),\n"
        "  g.extensionOf('nacht.BDF'),\n"
        "  g.extensionOf('nacht.edf'),\n"
        "  g.extensionOf('nacht')\n"
        "]));\n"
    )
    proc = subprocess.run(["node", str(runner), os.path.abspath(JS_PATH)],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    got = json.loads(proc.stdout)
    assert got == ["ANON_1234.bdf", "ANON_1234.edf", "ANON_1234.edf",
                   "ANON_1234.edf", ".bdf", ".edf", ".edf"], got
