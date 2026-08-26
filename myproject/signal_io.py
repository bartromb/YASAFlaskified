"""Eén plek die weet welk opnameformaat er binnenkomt.

WAAROM NATIEF BDF EN NIET OMZETTEN NAAR EDF
-------------------------------------------
BDF is 24-bit, EDF is 16-bit. Een centrum dat zijn BDF eerst naar EDF exporteert
om het hier te kunnen uploaden, scoort daarna de CONVERSIE mee: bij een
verkeerde schaling knipt of kwantiseert het EEG, en de uitkomst zegt dan iets
over de exporter in plaats van over de nacht. Een gebruiker meldde precies dat
(25-08-2026): downsampling naar 125 Hz plus een 50 Hz-notch volgens de
YASA-tutorial, en de EDF zag er "a bit discontinuous" uit.

MNE leest BDF rechtstreeks. Zodra het bestand een `Raw` is, kan de rest van de
keten -- kanaaldetectie, staging, psgscoring -- niet meer zien waar het vandaan
kwam. De enige plekken die het formaat moeten kennen zijn dus het inlezen en het
terugvinden van het bronbestand; die staan hier.

WAT ER NIET VERANDERT
---------------------
De uitvoer blijft EDF+ (`{job_id}_scored.edf`). Annotaties horen in EDF+ thuis
en elk scoringsprogramma leest dat; een BDF+ terugschrijven zou de uitwisseling
smaller maken in plaats van breder.

De anonimisering werkt op de eerste 256 bytes, en die header heeft in BDF exact
dezelfde indeling als in EDF (patiëntveld op 8, opnameveld op 88, startdatum op
168). Alleen byte 0 verschilt: 0xFF plus "BIOSEMI" tegen "0       ". De
anonimiseerder hoeft dus niets te weten van 24-bit samples -- hij raakt de data
niet aan.
"""
from __future__ import annotations

import glob
import logging
import os

import mne

logger = logging.getLogger(__name__)

# Kleine letters, met punt. Volgorde bepaalt de zoekvolgorde bij het
# terugvinden van een bronbestand.
SIGNAL_EXTENSIONS = (".edf", ".bdf")

#: Achtervoegsel van het bestand dat WIJ schrijven; nooit een bronbestand.
SCORED_SUFFIX = "_scored.edf"


def is_signal_file(filename: str) -> bool:
    """Draagt deze naam een formaat dat we kunnen lezen?"""
    return str(filename).lower().endswith(SIGNAL_EXTENSIONS)


def signal_extension(path: str) -> str:
    """`.edf` of `.bdf`, in kleine letters; `.edf` als de naam niets zegt."""
    ext = os.path.splitext(str(path))[1].lower()
    return ext if ext in SIGNAL_EXTENSIONS else ".edf"


def read_raw_signal(path, **kwargs):
    """`read_raw_edf` of `read_raw_bdf`, gekozen op de extensie.

    Beide MNE-functies delen hun handtekening (`exclude`, `preload`, `verbose`),
    dus de aanroepers hoeven alleen deze naam te veranderen.

    Een BDF die `.edf` heet, wordt niet gered: `read_raw_edf` faalt er hoorbaar
    op. Dat is beter dan raden op de magic bytes en er stilletjes naast zitten --
    een verkeerd gelezen 24-bit bestand levert plausibele maar onjuiste
    amplitudes, en dat is precies de fout die deze module moet voorkomen.
    """
    reader = (mne.io.read_raw_bdf if signal_extension(path) == ".bdf"
              else mne.io.read_raw_edf)
    return reader(path, **kwargs)


def source_candidates(folder: str, job_id: str) -> list[str]:
    """De mogelijke bronbestanden van een job, nieuwste eerst.

    Sluit `_scored.edf` uit: dat is onze eigen uitvoer. Zonder die filter pakt
    een tweede analyse van dezelfde job zijn eigen resultaat als invoer.
    """
    uit: list[str] = []
    for ext in SIGNAL_EXTENSIONS:
        uit += [c for c in glob.glob(os.path.join(folder, f"{job_id}*{ext}"))
                if not c.endswith(SCORED_SUFFIX)]
    uit.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0,
             reverse=True)
    return uit


# ── DC-koppeling ─────────────────────────────────────────────────────────────
#
# Een BioSemi-achtige versterker neemt gelijkspanning mee op: elk kanaal draagt
# een eigen staande offset en het EEG staat daar in microvolts bovenop. Op de
# opname die dit aan het licht bracht (Chulalongkorn, 27 kanalen, 250 Hz):
#
#     F3  ruw p95 144.571 uV   ->  na 0,3 Hz hoogdoorlaat  25,2 uV
#     C4  ruw p95  20.403 uV   ->                         203,3 uV
#
# Datzelfde ene feit verklaarde drie klachten tegelijk: vlakke lijnen in de
# viewer (de schaal volgt de offset, niet het EEG -- gain helpt niet), een
# "discontinuous" EDF na conversie (16-bit kan 145 mV en microvoltdetail niet
# tegelijk dragen) en 100 % van de samples boven de 500 uV-artefactregel.
#
# HERREFEREREN WERKT NIET. F3-A2 blijft 136.088 uV: elk kanaal draagt zijn
# EIGEN offset, dus het verschil houdt er een over. Alleen een hoogdoorlaat
# haalt hem weg.
#
# WAAROM DIT AUTOMATISCH MAG, TEGEN DE GEWOONTE IN
# De drempel ligt op dezelfde 500 uV als de artefactregel van psgscoring. Een
# kanaal met een offset daarboven wordt op dit moment al volledig als artefact
# weggegooid -- er is geen bestaande, bruikbare uitkomst om te breken. De
# ingreep verandert alleen opnames die nu onbruikbaar zijn.

#: Boven deze mediane afwijking (µV) noemen we een kanaal DC-gekoppeld.
DC_OFFSET_THRESHOLD_UV = 500.0

#: Kantelfrequentie. Laag genoeg om trage slaap-EEG-golven te sparen
#: (delta begint bij 0,5 Hz), hoog genoeg om de offset weg te nemen.
DC_HIGHPASS_HZ = 0.3

#: Alleen rollen waar gelijkspanning GEEN signaal is. SpO2, hartslag, positie
#: en snurk dragen hun informatie juist in het DC-niveau; die filteren zou ze
#: vernietigen.
_AC_TOKENS = ("EEG", "EOG", "EMG", "ECG", "EKG", "CHIN", "MENT",
              "LEG", "TIB", "ANKLE",
              "F3", "F4", "FZ", "FP1", "FP2", "C3", "C4", "CZ",
              "O1", "O2", "OZ", "P3", "P4", "PZ", "T3", "T4", "T5", "T6",
              "A1", "A2", "M1", "M2", "LEOG", "REOG", "LOC", "ROC", "E1", "E2")

#: Wint ALTIJD van `_AC_TOKENS`. Twee soorten kanalen staan hier:
#:
#: 1. kanalen waar het DC-niveau juist de meting IS (SpO2, hartslag, positie);
#: 2. kanalen die traag ademen. Een ademhaling van 12/min is 0,2 Hz, dus een
#:    hoogdoorlaat op 0,3 Hz filtert precies het signaal weg. `EMG/Piezo` is
#:    daar het voorbeeld van: de naam draagt "EMG", maar een piëzo-band meet
#:    ademhaling. Zonder deze voorrangsregel zou dat kanaal stilzwijgend
#:    onbruikbaar gemaakt worden -- en juist stille schade is wat hier telt.
_DC_TOKENS = ("SPO2", "SAO2", "SAT", "PLETH", "PULSE", "POS", "HR",
              "SNORE", "PRESS", "FLOW", "THERM", "THORAX", "CHEST", "ABD",
              "RIP", "DC-", "PIEZO", "RESP", "CANNULA", "NASAL", "EFFORT",
              "CO2", "SUM", "BELT")


def _is_ac_channel(name: str) -> bool:
    """Is dit een kanaal waar een gelijkspanningsoffset een defect is?

    De uitsluitlijst gaat vóór: bij twijfel niet filteren. Een gemist kanaal
    houdt het gedrag van vandaag; een ten onrechte gefilterd ademhalingskanaal
    levert een plausibel ogende, stille fout op.
    """
    u = str(name).upper()
    if any(t in u for t in _DC_TOKENS):
        return False
    return any(t in u for t in _AC_TOKENS)


def dc_coupled_channels(raw, threshold_uv: float = DC_OFFSET_THRESHOLD_UV,
                        max_seconds: float = 300.0) -> dict:
    """Welke AC-kanalen dragen een staande offset, en hoe groot?

    Meet op de mediaan van een venster uit het MIDDEN van de opname: het begin
    van een nacht draagt vaak elektrode-instabiliteit, en een gemiddelde zou
    door uitschieters meebewegen waar een mediaan dat niet doet.

    Geeft ``{kanaalnaam: offset_in_uV}`` terug, leeg als er niets speelt.
    """
    import numpy as np

    namen = [c for c in raw.ch_names if _is_ac_channel(c)]
    if not namen:
        return {}
    sf = float(raw.info["sfreq"]) or 1.0
    n = int(min(max_seconds, raw.n_times / sf) * sf)
    if n < 2:
        return {}
    start = max(0, (raw.n_times - n) // 2)
    uit = {}
    for naam in namen:
        try:
            seg = raw.get_data(picks=[naam], start=start, stop=start + n)[0]
        except Exception:                                   # noqa: BLE001
            continue
        offset_uv = float(np.median(seg)) * 1e6
        if abs(offset_uv) > threshold_uv:
            uit[naam] = round(offset_uv, 1)
    return uit


def apply_dc_highpass(raw, threshold_uv: float = DC_OFFSET_THRESHOLD_UV,
                      cutoff_hz: float = DC_HIGHPASS_HZ) -> dict:
    """Haal de staande offset weg van de kanalen die er een dragen.

    Muteert `raw` (die moet dus geladen zijn) en geeft een verslag terug voor
    de provenance: welke kanalen, welke offsets, welke kantelfrequentie. Is er
    niets aan de hand, dan gebeurt er niets en is `channels` leeg -- op een
    gewone AC-gekoppelde opname is dit een no-op.
    """
    gevonden = dc_coupled_channels(raw, threshold_uv=threshold_uv)
    verslag = {"applied": False, "cutoff_hz": cutoff_hz,
               "threshold_uv": threshold_uv, "channels": {}}
    if not gevonden:
        return verslag
    try:
        raw.filter(l_freq=cutoff_hz, h_freq=None, picks=list(gevonden),
                   verbose=False)
    except Exception as e:                                  # noqa: BLE001
        logger.warning("[dc] hoogdoorlaat mislukt (%s); signalen ongewijzigd", e)
        verslag["error"] = str(e)
        return verslag
    verslag["applied"] = True
    verslag["channels"] = gevonden
    logger.warning(
        "[dc] %d kanalen DC-gekoppeld (grootste offset %.0f uV op %s); "
        "hoogdoorlaat %.2f Hz toegepast",
        len(gevonden), max(abs(v) for v in gevonden.values()),
        max(gevonden, key=lambda k: abs(gevonden[k])), cutoff_hz)
    return verslag


def strip_window_offset(data, names, threshold_uv: float = DC_OFFSET_THRESHOLD_UV):
    """Haal de offset uit een GETOOND venster, per kanaal.

    De viewer leest lui: hij vraagt 30 s uit een bestand dat hij nooit volledig
    inlaadt, dus een hoogdoorlaat over de hele opname kan daar niet. Voor
    weergave is de mediaan van het venster wegnemen genoeg -- en precies wat de
    klacht oplost: de schaal volgde de offset, waardoor het EEG als een vlakke
    lijn verscheen en gain niet hielp.

    Alleen boven de drempel, zodat een gewone opname byte-voor-byte toont wat er
    in het bestand staat. Muteert `data` in-place en geeft terug welke kanalen
    zijn bijgesteld.
    """
    import numpy as np

    drempel_v = float(threshold_uv) * 1e-6
    aangepast = []
    for i, naam in enumerate(names):
        if not _is_ac_channel(naam):
            continue
        rij = data[i]
        if rij.size == 0:
            continue
        med = float(np.median(rij))
        if abs(med) > drempel_v:
            data[i] = rij - med
            aangepast.append(naam)
    return aangepast
