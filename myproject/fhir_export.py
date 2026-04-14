"""
fhir_export.py — YASAFlaskified v0.8.36
===================================
Exporteert analyseresultaten als FHIR R4 DiagnosticReport (JSON).
Conform: https://www.hl7.org/fhir/diagnosticreport.html

Gebruik:
    from fhir_export import results_to_fhir
    fhir_json = results_to_fhir(results, job_id, site_config)
"""
import json
from version import __version__ as _APP_VERSION
from datetime import datetime, timezone


def results_to_fhir(results: dict, job_id: str,
                    site_config: dict = None) -> dict:
    """
    Bouw een FHIR R4 DiagnosticReport van YASAFlaskified-resultaten.
    Geeft een Python-dict terug (serialiseer met json.dumps).
    """
    pat   = results.get("patient_info", {})
    stats = results.get("sleep_statistics", {}).get("stats", {})
    pneumo= results.get("pneumo", {})
    rsum  = pneumo.get("respiratory", {}).get("summary", {})
    meta  = results.get("meta", {})
    site  = site_config or {}

    now_iso = datetime.now(timezone.utc).isoformat()
    rec_date= (meta.get("analysis_timestamp") or now_iso)[:10]

    # ── Patiënt-resource (contained) ──────────────────────────
    patient = {
        "resourceType": "Patient",
        "id": f"pat-{job_id[:8]}",
        "identifier": [{
            "system": "urn:yasaflaskified:patient-id",
            "value":  str(pat.get("patient_id", "unknown"))
        }],
        "name": [{
            "family": pat.get("patient_name", "Unknown"),
            "given":  [pat.get("patient_firstname", "")] if pat.get("patient_firstname") else []
        }],
        "gender": {"M": "male", "V": "female"}.get(
            str(pat.get("sex", "")).upper(), "unknown"),
        "birthDate": _fmt_date(pat.get("dob")),
    }

    # ── Observaties ───────────────────────────────────────────
    obs = []

    def _obs(code, display, value, unit, system="http://loinc.org"):
        obs.append({
            "resourceType": "Observation",
            "id": f"obs-{code.replace(' ','-').lower()}-{job_id[:6]}",
            "status": "final",
            "code": {"coding": [{"system": system, "code": code, "display": display}]},
            "subject": {"reference": f"#pat-{job_id[:8]}"},
            "effectiveDateTime": rec_date,
            "valueQuantity": {
                "value": _to_float(value),
                "unit":  unit,
                "system":"http://unitsofmeasure.org",
                "code":  unit,
            } if value not in (None, "—", "") else {"valueString": "—"}
        })

    # Slaaparchitectuur (LOINC codes conform AASM/HL7)
    _obs("93832-4", "Total sleep time",          stats.get("TST"),   "min")
    _obs("93830-8", "Sleep efficiency",           stats.get("SE"),    "%")
    _obs("93828-2", "Sleep onset latency",        stats.get("SOL"),   "min")
    _obs("93829-0", "Wake after sleep onset",     stats.get("WASO"),  "min")
    # v0.8.36: convert stage durations (minutes) to % of TST
    _tst = _to_float(stats.get("TST")) or 1
    _obs("93833-2", "N1 sleep %",   round((_to_float(stats.get("N1"))  or 0) / _tst * 100, 1), "%")
    _obs("93834-0", "N2 sleep %",   round((_to_float(stats.get("N2"))  or 0) / _tst * 100, 1), "%")
    _obs("93835-7", "N3 sleep %",   round((_to_float(stats.get("N3"))  or 0) / _tst * 100, 1), "%")
    _obs("93836-5", "REM sleep %",  round((_to_float(stats.get("REM")) or 0) / _tst * 100, 1), "%")

    # Respiratoir
    ahi = rsum.get("ahi_total")
    _obs("69990-0", "Apnea-Hypopnea Index (AHI)", ahi,               "/h")
    _obs("70954-2", "Obstructive AHI (OAHI)",      rsum.get("oahi"),  "/h")
    _obs("59408-5", "Oxygen saturation mean",       pneumo.get("spo2",{}).get("summary",{}).get("mean_spo2"), "%")
    _obs("59417-6", "Oxygen saturation nadir",      pneumo.get("spo2",{}).get("summary",{}).get("min_spo2"),  "%")

    # PLM
    plm_sum = pneumo.get("plm", {}).get("summary", {})
    if plm_sum:
        _obs("80487-3", "PLM index", plm_sum.get("plm_index"), "/h")

    # ── Conclusie + behandeladviezen (v0.8.11) ──────────────────
    severity = _ahi_severity(ahi)

    # v0.8.11: Voeg behandeladviezen toe aan FHIR conclusion
    # Ref: Gemini review — "Ensure Interpretation fields contain
    # the Automated Conclusions from the diagnostic table."
    tx_parts = []
    if ahi is not None:
        if ahi >= 30:
            tx_parts.append("CPAP urgent, ENT evaluation, supplemental O2 if desaturations.")
        elif ahi >= 15:
            tx_parts.append("CPAP first-line; MAD if intolerant.")
        elif ahi >= 5:
            tx_parts.append("Positional therapy, MAD, sleep hygiene.")

    plmi = plm_sum.get("plm_index") if plm_sum else None
    if plmi is not None and plmi >= 15:
        tx_parts.append("Check ferritin, iron supplementation if <75 ug/L, dopamine agonist.")

    se_val = stats.get("SE")
    tst_val = stats.get("TST")
    if (se_val is not None and float(se_val) < 85) or (tst_val is not None and float(tst_val) < 360):
        tx_parts.append("CBT-I first-line, sleep hygiene evaluation.")

    # Cheyne-Stokes
    csr = results.get("pneumo", {}).get("cheyne_stokes", {})
    if csr.get("csr_detected"):
        tx_parts.append("Cardiology referral, echocardiography, ASV consideration.")

    treatment_text = " ".join(tx_parts) if tx_parts else ""

    # v0.2.8: AHI confidence interval
    _interval = pneumo.get("ahi_interval", {})
    _intv_lo = _interval.get("interval", [None, None])[0]
    _intv_hi = _interval.get("interval", [None, None])[1]
    _robust = _interval.get("robustness_grade", "")
    _robust_label = _interval.get("robustness_label", "")

    conclusion = (
        f"Automated PSG analysis (YASAFlaskified v{_APP_VERSION}, AASM 2.6). "
        f"AHI = {_fmt_val(ahi)} /h ({severity}). "
    )
    if _intv_lo is not None and _intv_hi is not None:
        conclusion += (
            f"AHI interval [{_intv_lo:.1f} – {_intv_hi:.1f}] /h "
            f"(robustness: {_robust}). "
        )
    conclusion += (
        f"TST = {_fmt_val(stats.get('TST'))} min, "
        f"SE = {_fmt_val(stats.get('SE'))} %. "
        f"Patient: {patient['name'][0]['family']}."
    )
    if treatment_text:
        conclusion += f" Treatment considerations: {treatment_text}"

    # ── DiagnosticReport ──────────────────────────────────────
    report = {
        "resourceType": "Bundle",
        "id": f"bundle-{job_id[:8]}",
        "type": "collection",
        "timestamp": now_iso,
        "entry": [
            {"resource": patient},
            {
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "id": f"dr-{job_id[:8]}",
                    "contained": [patient],
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": "SLP",
                            "display": "Sleep Studies"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code":   "59282-4",
                            "display":"Polysomnography"
                        }]
                    },
                    "subject": {"reference": f"#pat-{job_id[:8]}"},
                    "effectiveDateTime": rec_date,
                    "issued": now_iso,
                    "performer": [{
                        "display": site.get("name", "SleepAI") +
                                   (f"  ·  {site['email']}" if site.get("email") else "")
                    }],
                    "result": [
                        {"reference": f"#{o['id']}"} for o in obs
                    ],
                    "conclusion": conclusion,
                    "conclusionCode": [{
                        "coding": _aasm_snomed(severity)
                    }],
                    "extension": [{
                        "url": "https://sleepai.be/fhir/StructureDefinition/yasaflaskified-job-id",
                        "valueString": job_id
                    }]
                }
            },
        ] + [{"resource": o} for o in obs]
    }

    return report


# ── Helpers ────────────────────────────────────────────────────

def _to_float(v):
    try:    return round(float(v), 2)
    except: return None


def _fmt_val(v):
    try:    return f"{float(v):.1f}"
    except: return "—"


def _fmt_date(dob):
    """Zet dd-mm-yyyy of yyyy-mm-dd om naar FHIR-datumformaat yyyy-mm-dd."""
    if not dob: return None
    try:
        parts = str(dob).replace("/", "-").split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:          # yyyy-mm-dd
                return f"{parts[0]}-{parts[1]:>02}-{parts[2]:>02}"
            else:                           # dd-mm-yyyy
                return f"{parts[2]}-{parts[1]:>02}-{parts[0]:>02}"
    except Exception:
        pass
    return None


def _ahi_severity(ahi):
    try:
        v = float(ahi)
        if v < 5:  return "Normaal"
        if v < 15: return "Mild OSA"
        if v < 30: return "Matig OSA"
        return "Ernstig OSA"
    except:
        return "Onbekend"


def _aasm_snomed(severity):
    """Geeft SNOMED-CT coding voor OSA-ernst conform AASM."""
    MAP = {
        "Normaal":     ("72274001",  "No diagnosis"),
        "Mild OSA":    ("230493001", "Mild obstructive sleep apnea"),
        "Matig OSA":   ("230492006", "Moderate obstructive sleep apnea"),
        "Ernstig OSA": ("230491004", "Severe obstructive sleep apnea"),
    }
    code, display = MAP.get(severity, ("72274001", "No diagnosis"))
    return [{"system": "http://snomed.info/sct", "code": code, "display": display}]
