"""De browser en de server moeten letterlijk dezelfde header produceren.

Twee implementaties van dezelfde regels is een uitnodiging om uiteen te lopen.
Gebeurt dat, dan krijgt dezelfde opname via "anoniem opladen" een andere code
dan via "anonimiseren na het opladen", en zijn twee analyses van dezelfde nacht
niet meer aan elkaar te koppelen — zonder dat iemand dat merkt, want beide
resultaten zien er op zichzelf correct uit.

Deze test draait het echte JavaScript in Node en vergelijkt de uitvoer veld voor
veld met Python. Zonder Node wordt hij overgeslagen; dan bewaakt niets deze
gelijkheid, en dat is precies waarom de skip-reden dat zegt.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest
from edf_anonymize import anonymize_patient_field, anonymize_recording_field, pseudonym

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "edf_anonymize.js",
)

CASES = [
    # (patiëntveld, opnameveld, studiecode)
    ("MRN12345 M 03-MAR-1971 Janssens_Pieter",
     "Startdate 29-APR-2026 AZORG_SLAAP TECH_LV SOMNO_eco_0775", ""),
    ("MRN12345 M 03-MAR-1971 Janssens_Pieter",
     "Startdate 29-APR-2026 AZORG_SLAAP TECH_LV SOMNO_eco_0775", "AZORG-2026-014"),
    ("MRN999 F 12-DEC-1955 X", "Startdate 01-JAN-2026 X X X", ""),
    ("X X X X", "X", ""),
    ("Pieter Janssens 03/03/1971", "vrije tekst hier", ""),
    ("MRN1 M 03-MAR-1971 X", "Startdate 29-APR-2026 X X X", "AZORG 2026 014"),
    ("MRN1 M 03-MAR-1971 X", "Startdate 29-APR-2026 X X X", "AZORG/2026#014"),
]

RUNNER = r"""
const fs = require('fs');
global.window = global;
global.crypto = require('crypto').webcrypto;
eval(fs.readFileSync(process.argv[2], 'utf8'));
const cases = JSON.parse(process.argv[3]);
(async () => {
  const out = [];
  for (const [patient, recording, code] of cases) {
    const blob = new Blob([new Uint8Array(256)]);   // niet gebruikt, enkel API-vorm
    out.push({
      patient: await window.EdfAnonymize.__test.patientField(patient, 'ANON', true, code),
      recording: window.EdfAnonymize.__test.recordingField(recording, true),
      pseudo: await window.EdfAnonymize.pseudonym(patient, 'ANON'),
      code: window.EdfAnonymize.sanitizeStudyCode(code),
    });
  }
  process.stdout.write(JSON.stringify(out));
})();
"""


@pytest.fixture(scope="module")
def js_results(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node niet beschikbaar — de JS/Python-gelijkheid is nu ONBEWAAKT")
    runner = tmp_path_factory.mktemp("js") / "runner.js"
    runner.write_text(RUNNER)
    proc = subprocess.run(
        ["node", str(runner), JS_PATH, json.dumps(CASES)],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(f"node faalde: {proc.stderr[-2000:]}")
    return json.loads(proc.stdout)


@pytest.mark.parametrize("idx", range(len(CASES)))
def test_the_patient_field_is_identical_in_both_implementations(js_results, idx):
    patient, _rec, code = CASES[idx]
    assert js_results[idx]["patient"] == anonymize_patient_field(
        patient, "ANON", True, code), f"case {idx}: {patient!r} / {code!r}"


@pytest.mark.parametrize("idx", range(len(CASES)))
def test_the_recording_field_is_identical_in_both_implementations(js_results, idx):
    _pat, recording, _code = CASES[idx]
    assert js_results[idx]["recording"] == anonymize_recording_field(recording, True)


@pytest.mark.parametrize("idx", range(len(CASES)))
def test_the_pseudonym_is_identical_in_both_implementations(js_results, idx):
    patient, _rec, _code = CASES[idx]
    assert js_results[idx]["pseudo"] == pseudonym(patient, "ANON")
