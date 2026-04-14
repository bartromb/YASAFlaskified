"""
generate_edfplus.py — YASAFlaskified v0.8.36
==========================================
Snelle, geheugenefficiënte EDF+ export met slaapstaging en events.

v0.8.11 fixes:
  - edfio header-kopie: veilig via try/except per attribuut (geen crash
    op read-only attrs of ontbrekende attrs in verschillende edfio versies)
  - MNE fallback: raw.export() ipv mne.export.export_raw() (MNE >=1.6)
  - Robuustere signaal-kopie: vangt digital_min/max uitzonderingen op
  - Annotatie-beschrijving: strip non-ASCII karakters die edfio weigert
  - pyedflib als ultieme fallback
  - Logging verbeterd

v14 verbeteringen (behouden):
  - edfio als primaire engine (geen MNE preload -> <10s ipv ~3 min)
  - Correcte physical_dimension per kanaal (uit origineel EDF)
  - Inline in pipeline (niet meer als aparte achtergrondtaak)
  - PLM, positie en snurk-annotaties toegevoegd
  - Confidencescore per event in annotatie

Gebruik:
    from generate_edfplus import generate_edfplus
    generate_edfplus(edf_path, results, output_path)
"""

import os
import logging
import numpy as np

logger = logging.getLogger("yasaflaskified.edfplus")


def generate_edfplus(edf_path: str, results: dict, output_path: str) -> str:
    """
    Genereer EDF+ bestand met annotaties uit analyseresultaten.

    v0.8.11 FIX: pyedflib als primaire export.
    edfio 0.4.x schrijft gewoon EDF (niet EDF+) — annotaties gaan verloren.
    pyedflib heeft expliciete FILETYPE_EDFPLUS ondersteuning.

    Strategie: pyedflib (betrouwbaar EDF+C) -> MNE fallback -> edfio (laatste keus).
    """
    logger.info("EDF+ genereren: %s -> %s", os.path.basename(edf_path), output_path)

    annotations = _collect_annotations(results)
    logger.info("Totaal %d annotaties verzameld", len(annotations))

    # Maak output-directory aan indien nodig
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Poging 1: pyedflib (betrouwbaar EDF+C met annotaties)
    e1 = None
    try:
        _export_via_pyedflib_from_file(edf_path, annotations, output_path)
        logger.info("EDF+ opgeslagen via pyedflib: %s", output_path)
        return output_path
    except Exception as exc:
        e1 = exc
        logger.warning("pyedflib export mislukt: %s — probeer MNE fallback", exc)

    # Poging 2: MNE (trager, preload nodig)
    e2 = None
    try:
        _export_via_mne(edf_path, annotations, output_path)
        logger.info("EDF+ opgeslagen via MNE fallback: %s", output_path)
        return output_path
    except Exception as exc:
        e2 = exc
        logger.warning("MNE fallback mislukt: %s — probeer edfio", exc)

    # Poging 3: edfio (NB: schrijft mogelijk gewoon EDF, maar beter dan niets)
    try:
        _export_via_edfio(edf_path, annotations, output_path)
        logger.info("EDF+ opgeslagen via edfio: %s (annotaties mogelijk ontbrekend)", output_path)
        return output_path
    except Exception as e3:
        logger.error("Alle exports mislukt: pyedflib=%s, MNE=%s, edfio=%s", e1, e2, e3)
        raise RuntimeError(f"EDF+ export mislukt. pyedflib: {e1}. MNE: {e2}. edfio: {e3}")


# ═══════════════════════════════════════════════════════════════
# ANNOTATIE VERZAMELING
# ═══════════════════════════════════════════════════════════════

def _safe_str(text: str, max_len: int = 80) -> str:
    """Maak annotatie-tekst veilig voor EDF+: strip non-ASCII, limiteer lengte."""
    if not text:
        return ""
    # EDF+ annotaties: alleen printbare ASCII (32-126)
    cleaned = "".join(c if 32 <= ord(c) <= 126 else "?" for c in str(text))
    return cleaned[:max_len]


def _collect_annotations(results: dict) -> list[dict]:
    """Verzamel alle annotaties uit analyseresultaten."""
    annots = []

    # 1. Sleep staging (per 30s epoch)
    hypno = results.get("staging", {}).get("hypnogram", [])
    stage_labels = {
        "W": "Sleep stage W", "N1": "Sleep stage N1",
        "N2": "Sleep stage N2", "N3": "Sleep stage N3",
        "R": "Sleep stage R",
    }
    for i, stage in enumerate(hypno):
        annots.append({
            "onset": i * 30.0, "duration": 30.0,
            "description": stage_labels.get(stage, f"Sleep stage {stage}"),
        })

    # 2. Respiratoire events
    type_labels = {
        "obstructive": "Obstructive apnea", "central": "Central apnea",
        "mixed": "Mixed apnea", "hypopnea": "Hypopnea",
        "hypopnea_central": "Central hypopnea",
        "hypopnea_obstructive": "Obstructive hypopnea",
    }
    for e in results.get("pneumo", {}).get("respiratory", {}).get("events", []):
        label = type_labels.get(e.get("type", ""), f"Resp ({e.get('type','')})")
        parts = [label]
        if e.get("desaturation_pct") is not None:
            parts.append(f"desat={e['desaturation_pct']}%")
        if e.get("confidence") is not None:
            parts.append(f"conf={e['confidence']}")
        annots.append({
            "onset": float(e.get("onset_s", 0)),
            "duration": float(e.get("duration_s", 10)),
            "description": " ".join(parts),
        })

    # 3. SpO2 desaturaties (max 200)
    for d in results.get("pneumo", {}).get("spo2", {}).get("desaturations", [])[:200]:
        annots.append({
            "onset": float(d.get("onset_s", 0)),
            "duration": float(d.get("duration_s", 5)),
            "description": f"SpO2 desaturation {d.get('drop_pct', '?')}%",
        })

    # 4. Arousals
    for a in results.get("pneumo", {}).get("arousal", {}).get("events", []):
        atype = a.get("type", "spontaneous")
        label = {"respiratory": "Arousal (respiratory)",
                 "rera": "RERA", "plm": "Arousal (PLM)"}.get(atype, "Arousal")
        annots.append({
            "onset": float(a.get("onset_s", 0)),
            "duration": float(a.get("duration_s", 3)),
            "description": label,
        })

    # 5. PLM events
    for lm in results.get("pneumo", {}).get("plm", {}).get("events", []):
        if lm.get("is_plm"):
            desc = "PLM" + (" (resp-assoc)" if lm.get("resp_associated") else "")
            annots.append({
                "onset": float(lm.get("onset_s", 0)),
                "duration": float(lm.get("duration_s", 2)),
                "description": desc,
            })

    # 6. Artefact epochs
    arts = results.get("artifacts", {})
    if arts.get("success"):
        for ep in arts.get("artifact_epochs", []):
            annots.append({
                "onset": ep.get("epoch", 0) * 30.0,
                "duration": 30.0, "description": "Artifact",
            })

    # 7. Positie-veranderingen (v0.8.11: arrow -> ASCII-safe)
    for change in results.get("pneumo", {}).get("position", {}).get("position_changes", []):
        annots.append({
            "onset": float(change.get("time_s", 0)),
            "duration": 0.0,
            "description": f"Position -> {change.get('to', '?')}",
        })

    # 8. Cheyne-Stokes
    csr = results.get("pneumo", {}).get("cheyne_stokes", {})
    if csr.get("csr_detected"):
        annots.append({
            "onset": 0.0, "duration": 0.0,
            "description": f"CSR detected (period={csr.get('periodicity_s','?')}s)",
        })

    annots.sort(key=lambda a: a["onset"])
    return annots


# ═══════════════════════════════════════════════════════════════
# EXPORT VIA EDFIO (PRIMAIR — SNEL)
# ═══════════════════════════════════════════════════════════════

def _export_via_edfio(edf_path: str, annotations: list[dict], output_path: str):
    """Exporteer EDF+ via edfio met correcte physical dimensions."""
    import edfio

    original = edfio.read_edf(edf_path)

    new_signals = []
    for sig in original.signals:
        kwargs = {
            "data": sig.data.copy(),
            "sampling_frequency": sig.sampling_frequency,
            "label": sig.label,
        }

        # Physical dimension — veilig kopiëren
        try:
            pd_val = sig.physical_dimension
            if pd_val is not None:
                kwargs["physical_dimension"] = pd_val
        except (AttributeError, Exception):
            pass

        # Kopieer optionele metadata veilig
        for attr in ("transducer_type", "prefiltering"):
            try:
                val = getattr(sig, attr, None)
                if val is not None:
                    kwargs[attr] = val
            except Exception:
                pass

        # Physical/digital range: gebruik originele waarden
        # v0.8.11 FIX: apart try/except per range om crash te voorkomen
        try:
            kwargs["physical_range"] = (sig.physical_min, sig.physical_max)
        except (AttributeError, Exception):
            pass
        try:
            kwargs["digital_range"] = (sig.digital_min, sig.digital_max)
        except (AttributeError, Exception):
            pass

        try:
            new_signals.append(edfio.EdfSignal(**kwargs))
        except Exception as e:
            # Fallback: minimale signaal-kopie
            logger.warning("EdfSignal fallback voor '%s': %s", sig.label, e)
            new_signals.append(edfio.EdfSignal(
                data=sig.data.copy(),
                sampling_frequency=sig.sampling_frequency,
                label=sig.label,
            ))

    edf_out = edfio.Edf(new_signals)

    # v0.8.11 FIX: Forceer EDF+C (continuous) modus
    # edfio.Edf() maakt standaard EDF, niet EDF+. Zonder dit worden
    # annotaties opgeslagen in het object maar NIET als EDF Annotations
    # signaalkanaal geschreven → EDFbrowser toont geen annotaties.
    try:
        edf_out._version = "EDF+C"
    except (AttributeError, Exception):
        pass
    # Alternatieve manier voor nieuwere edfio versies
    try:
        if hasattr(edf_out, 'set_filetype'):
            edf_out.set_filetype(edfio.FILETYPE_EDFPLUS)
    except (AttributeError, Exception):
        pass

    # Kopieer header-metadata — per attribuut veilig
    for attr in ("local_patient_identification",
                 "local_recording_identification",
                 "starttime", "startdate",
                 "recording_startdate", "recording_starttime"):
        try:
            val = getattr(original, attr, None)
            if val is not None:
                setattr(edf_out, attr, val)
        except (AttributeError, TypeError, ValueError, Exception) as e:
            logger.debug("Header attr '%s' niet gekopieerd: %s", attr, e)

    # Annotaties toevoegen
    n_added = 0
    for a in annotations:
        try:
            edf_out.append_annotation(
                float(a["onset"]), float(a["duration"]),
                _safe_str(a["description"]),
            )
            n_added += 1
        except Exception as e:
            if n_added == 0:
                logger.warning("Eerste annotatie mislukt: %s", e)

    logger.info("edfio: %d/%d annotaties toegevoegd", n_added, len(annotations))

    if n_added == 0 and len(annotations) > 0:
        raise RuntimeError("edfio: 0 annotaties geschreven — fallback naar MNE/pyedflib")

    edf_out.write(output_path)

    # v0.8.11: Verifieer dat het bestand EDF+ is (niet gewoon EDF)
    with open(output_path, "rb") as fcheck:
        header_8 = fcheck.read(8).decode("ascii", errors="replace").strip()
    if "+" not in header_8:
        logger.warning("edfio schreef EDF in plaats van EDF+ — header: '%s'. "
                       "Fallback naar pyedflib.", header_8)
        os.remove(output_path)
        raise RuntimeError(f"edfio schreef EDF header '{header_8}', niet EDF+C")


# ═══════════════════════════════════════════════════════════════
# EXPORT VIA MNE (FALLBACK)
# ═══════════════════════════════════════════════════════════════

def _export_via_mne(edf_path: str, annotations: list[dict], output_path: str):
    """Fallback: MNE export (trager, vereist preload)."""
    import mne

    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    raw.set_annotations(mne.Annotations([], [], []))

    if annotations:
        annot = mne.Annotations(
            onset=[a["onset"] for a in annotations],
            duration=[a["duration"] for a in annotations],
            description=[_safe_str(a["description"]) for a in annotations],
            orig_time=raw.info.get("meas_date"),
        )
        raw.set_annotations(annot)

    # Clip extreme waarden (voorkomt EDF write-fouten)
    data = raw.get_data()
    clip_val = 9999999
    for i in range(data.shape[0]):
        ch_min, ch_max = float(data[i].min()), float(data[i].max())
        if ch_min < -clip_val or ch_max > clip_val:
            data[i] = data[i].clip(-clip_val, clip_val)
    raw._data = data

    # v0.8.11 FIX: raw.export() werkt in MNE >=1.1
    # mne.export.export_raw() is verwijderd/verplaatst in nieuwere versies
    try:
        raw.export(output_path, fmt="edf", overwrite=True)
        return
    except (AttributeError, TypeError):
        pass

    # MNE <1.1: probeer mne.export.export_raw
    try:
        mne.export.export_raw(output_path, raw, fmt="edf", overwrite=True)
        return
    except (AttributeError, ImportError):
        pass

    # Ultieme fallback: pyedflib
    _export_via_pyedflib(raw, annotations, output_path)


def _export_via_pyedflib(raw, annotations: list[dict], output_path: str):
    """Ultieme fallback via pyedflib als MNE export niet beschikbaar is."""
    try:
        import pyedflib
    except ImportError:
        raise RuntimeError("Geen werkende EDF+ export beschikbaar (edfio/MNE/pyedflib)")

    n_channels = len(raw.ch_names)
    sf = raw.info["sfreq"]

    f = pyedflib.EdfWriter(output_path, n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)
    try:
        data = raw.get_data()
        for i, ch_name in enumerate(raw.ch_names):
            f.setLabel(i, ch_name)
            f.setSamplefrequency(i, sf)
            ch_data = data[i]
            phys_max = float(np.max(np.abs(ch_data))) + 1.0
            f.setPhysicalMaximum(i, phys_max)
            f.setPhysicalMinimum(i, -phys_max)
            f.setDigitalMaximum(i, 32767)
            f.setDigitalMinimum(i, -32768)
            f.setPhysicalDimension(i, "uV")

        f.writeSamples(data)

        for a in annotations:
            f.writeAnnotation(
                float(a["onset"]),
                float(a["duration"]),
                _safe_str(a["description"]),
            )
    finally:
        f.close()
    logger.info("EDF+ opgeslagen via pyedflib fallback: %s", output_path)




def _export_via_pyedflib_from_file(edf_path: str, annotations: list[dict], output_path: str):
    """
    v0.8.11: Primaire EDF+ export via pyedflib.EdfReader + EdfWriter.

    Leest het originele EDF direct met pyedflib (niet via MNE) en schrijft
    EDF+C met behoud van originele signaalmetadata (physical dimensions,
    transducer types, prefiltering, physical/digital ranges).

    pyedflib is de enige library die betrouwbaar EDF+C schrijft met
    annotaties die zichtbaar zijn in EDFbrowser.
    """
    import pyedflib

    # Lees origineel
    reader = pyedflib.EdfReader(edf_path)
    try:
        n_channels = reader.signals_in_file
        logger.info("pyedflib: %d kanalen lezen uit %s", n_channels, os.path.basename(edf_path))

        # Schrijf EDF+C
        writer = pyedflib.EdfWriter(output_path, n_channels,
                                     file_type=pyedflib.FILETYPE_EDFPLUS)
        try:
            # Kopieer header-metadata
            try:
                writer.setPatientName(reader.getPatientName() or "")
            except Exception:
                pass
            try:
                writer.setRecordingAdditional(reader.getRecordingAdditional() or "")
            except Exception:
                pass
            try:
                writer.setStartdatetime(reader.getStartdatetime())
            except Exception:
                pass

            # Kopieer signaal-metadata per kanaal
            for i in range(n_channels):
                label = reader.getLabel(i)
                writer.setLabel(i, label)
                writer.setSamplefrequency(i, reader.getSampleFrequency(i))

                # Physical dimensions (units)
                try:
                    dim = reader.getPhysicalDimension(i)
                    if dim:
                        writer.setPhysicalDimension(i, dim)
                except Exception:
                    writer.setPhysicalDimension(i, "uV")

                # Physical/digital ranges
                try:
                    writer.setPhysicalMaximum(i, reader.getPhysicalMaximum(i))
                    writer.setPhysicalMinimum(i, reader.getPhysicalMinimum(i))
                    writer.setDigitalMaximum(i, reader.getDigitalMaximum(i))
                    writer.setDigitalMinimum(i, reader.getDigitalMinimum(i))
                except Exception:
                    # Fallback: bereken uit data
                    pass

                # Optionele metadata
                try:
                    writer.setTransducer(i, reader.getTransducer(i) or "")
                except Exception:
                    pass
                try:
                    writer.setPrefilter(i, reader.getPrefilter(i) or "")
                except Exception:
                    pass

            # Kopieer signaaldata
            # pyedflib.EdfWriter.writeSamples verwacht een lijst van arrays
            data_list = []
            for i in range(n_channels):
                data_list.append(reader.readSignal(i))

            writer.writeSamples(data_list)
            logger.info("pyedflib: %d kanalen geschreven", n_channels)

            # Annotaties toevoegen
            n_added = 0
            for a in annotations:
                try:
                    writer.writeAnnotation(
                        float(a["onset"]),
                        float(a["duration"]),
                        _safe_str(a["description"]),
                    )
                    n_added += 1
                except Exception as e:
                    if n_added == 0:
                        logger.warning("Eerste annotatie mislukt: %s", e)

            logger.info("pyedflib: %d/%d annotaties geschreven", n_added, len(annotations))

        finally:
            writer.close()
    finally:
        reader.close()

    # Verifieer EDF+
    with open(output_path, "rb") as fcheck:
        hdr = fcheck.read(8).decode("ascii", errors="replace").strip()
    if "+" not in hdr:
        raise RuntimeError(f"pyedflib schreef '{hdr}' in plaats van EDF+C")
    logger.info("EDF+C geverifieerd: header='%s'", hdr)
