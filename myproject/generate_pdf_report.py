"""
generate_pdf_report.py — YASAFlaskified v0.8.37
Site-config: via config.json["site"] of site_config parameter.
"""
import io
import json
import logging
import os
from datetime import date

import matplotlib
from i18n import t
from version import PSGSCORING_VERSION as _PSGSCORING_VERSION
from version import __version__ as _APP_VERSION

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
import numpy as np

# v0.8.37: Medatec-parity PDF sections + OSAS score
from pdf_report_additions import (
    draw_ess_section,
    draw_position_stage_table,
    draw_snoring_crosstab,
    draw_spo2_bands,
    draw_stage_latencies,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from signal_io import read_raw_signal

# ── Pagina ─────────────────────────────────────────────────────
W_A4, H_A4 = A4
ML, MR, MT, MB = 2.0*cm, 2.0*cm, 1.8*cm, 1.6*cm
CW = W_A4 - ML - MR

# ── Kleuren ────────────────────────────────────────────────────
NAVY  = colors.HexColor("#1a3a8f")
BLUE  = colors.HexColor("#2c5fa8")
MINT  = colors.HexColor("#02C39A")
BGROW = colors.HexColor("#f0f4f8")
BGR2  = colors.HexColor("#e8f0fa")
GRID  = colors.HexColor("#d0dce8")
GR    = colors.HexColor("#6b7a99")
TXT   = colors.HexColor("#1a2a3a")
W     = colors.white
RED   = colors.HexColor("#c0392b")
ORA   = colors.HexColor("#d68910")
GRN   = colors.HexColor("#1e8449")

STAGE_CLR = {"W":"#e74c3c","N1":"#f39c12","N2":"#2980b9","N3":"#1a3a8f","R":"#8e44ad"}
AHI_SEV = [(5,GRN,"Normal"),(15,ORA,"Mild OSA"),(30,RED,"Moderate OSA"),(9999,colors.HexColor("#7b241c"),"Severe OSA")]

_SEV_LABELS = {
    "Normal":       {"nl": "Normaal",     "fr": "Normal",      "en": "Normal",       "de": "Normal"},
    "Mild OSA":     {"nl": "Mild OSA",    "fr": "SAOS léger",  "en": "Mild OSA",     "de": "Leichtes OSA"},
    "Moderate OSA": {"nl": "Matig OSA",   "fr": "SAOS modéré", "en": "Moderate OSA",  "de": "Mittelgradiges OSA"},
    "Severe OSA":   {"nl": "Ernstig OSA", "fr": "SAOS sévère", "en": "Severe OSA",    "de": "Schweres OSA"},
}

# ── Site-config ────────────────────────────────────────────────
# GEEN instellingsnaam in de code. Wie dit draait, zet zijn eigen gegevens in
# `instance/config.json`; dat bestand is host-lokaal, bind-gemount en staat in
# de rsync-uitsluitingen, dus een deploy raakt het niet. Stond hier tot v0.34.7
# "Slaapkliniek AZORG" met bijbehorend logo, en dat verscheen op het rapport van
# ELKE installatie -- ook bij de slaapcentra die het product uitproberen.
_DSITE = {"name": "", "address": "", "phone": "", "email": "",
          "logo_path": "", "url": ""}

#: Zoekvolgorde voor de site-configuratie. `instance/` gaat vóór: dat is de
#: enige plek die een deploy of een image-rebuild NIET overschrijft. De
#: `config.json` in de app-root komt uit `config.json.example` via de Dockerfile
#: en wordt bij elke rebuild teruggezet -- bruikbaar als voorbeeld, niet als
#: plek voor de identiteit van een centrum.
_SITE_PATHS = ("instance/config.json", "config.json")


def _site_config_paths():
    root = os.path.join(os.path.dirname(__file__), "..")
    return [os.path.join(root, p) for p in _SITE_PATHS] + list(_SITE_PATHS)


def _load_site(override=None):
    cfg = dict(_DSITE)
    try:
        for p in _site_config_paths():
            if os.path.exists(p):
                with open(p) as f:
                    blok = json.load(f).get("site", {})
                if blok:
                    cfg.update(blok)
                    break
    except Exception: pass
    if override: cfg.update(override)
    return cfg

# ── Stijlen ────────────────────────────────────────────────────
def _styles():
    s = getSampleStyleSheet()
    def a(n,**kw):
        if n not in s: s.add(ParagraphStyle(n,**kw))
    a("T",  fontName="Helvetica-Bold",fontSize=15,textColor=NAVY,spaceAfter=2,leading=18)
    a("ST", fontName="Helvetica",fontSize=8.5,textColor=GR,spaceAfter=4)
    a("B",  fontName="Helvetica",fontSize=8.5,textColor=TXT,spaceAfter=3,leading=12)
    a("SM", fontName="Helvetica",fontSize=7,textColor=GR,leading=10)
    a("W",  fontName="Helvetica-Bold",fontSize=8,textColor=RED)
    a("D",  fontName="Helvetica",fontSize=6.5,textColor=GR,leading=9)
    return s

# ── Hulp ───────────────────────────────────────────────────────
def _v(d,*keys,default="—",fmt=None):
    try:
        r=d
        for k in keys: r=r[k]
        if r is None: return default
        if fmt: return fmt.format(float(r))
        if isinstance(r,float): return f"{r:.1f}"
        return str(r)
    except: return default

def _f(d,*keys,default=None):
    try:
        r=d
        for k in keys: r=r[k]
        return float(r) if r is not None else default
    except: return default

def _rnd(v,dec=2):
    try: return f"{float(v):.{dec}f}"
    except: return str(v) if v is not None else "—"

def _sev(ahi, lang="nl"):
    try: v=float(ahi)
    except: return "—"
    for thr,_,l in AHI_SEV:
        if v<thr: return _SEV_LABELS.get(l, {}).get(lang, l)
    return _SEV_LABELS.get("Severe OSA", {}).get(lang, "Severe OSA")

def _sev_clr(ahi):
    try: v=float(ahi)
    except: return GR
    for thr,c,_ in AHI_SEV:
        if v<thr: return c
    return RED


# v0.8.43: Dynamische OSAS/CSAS/MSAS labeling op basis van apnoe-type
def _apnea_syndrome(rsum, lang="nl"):
    """
    Bepaal SAS-type op basis van dominante apnoe-type (>50%).
    Returnt vertaald syndroom-label: OSAS/CSAS/gemengde SAS/SAS.

    Klinische rationale: een AHI kan hoog zijn door obstructieve of centrale
    events. Het label 'OSA' hardcoden is misleidend bij CSAS-patronen
    (hartfalen met Cheyne-Stokes, post-stroke, opioid-geinduceerd).
    """
    n_o = (rsum or {}).get("n_obstructive", 0) or 0
    n_c = (rsum or {}).get("n_central", 0) or 0
    n_m = (rsum or {}).get("n_mixed", 0) or 0
    total = n_o + n_c + n_m
    if total == 0:
        return {"nl":"SAS","fr":"SAS","en":"SAS","de":"SAS"}.get(lang, "SAS")
    pct_c = n_c / total
    pct_o = n_o / total
    if pct_c > 0.5:
        return {"nl":"CSAS","fr":"SACS","en":"CSAS","de":"ZSAS"}.get(lang, "CSAS")
    if pct_o > 0.5:
        return {"nl":"OSAS","fr":"SAOS","en":"OSAS","de":"OSAS"}.get(lang, "OSAS")
    return {"nl":"gemengde SAS","fr":"SAS mixte","en":"mixed SAS","de":"gemischte SAS"}.get(lang, "mixed SAS")

def _classbar(*, ahi, oahi, split_diag, rsum, lang, unit,
              ahi_lbl, oahi_lbl, therapy_note, prof_lbl):
    """De tekst van de classificatiebalk in sectie 8, en waarop hij kleurt.

    Staat LOS van de renderfunctie omdat hij daarbinnen alleen te toetsen is
    door een volledige PDF te bouwen -- en dan toetst de test de reportlab-
    opmaak in plaats van de klinische logica.

    Op een split-night LEIDT de balk met de diagnostische helft. Andersom --
    zoals het tot 30-08-2026 stond -- classificeert sectie 8 het
    NACHTGEMIDDELDE. Bij een korte diagnostische periode gevolgd door vele uren
    onder therapie trekt dat gemiddelde naar de therapiewaarde: de balk toont
    dan een milde ernst, in de bijbehorende kleur, terwijl het deel zonder
    therapie ernstig is. De kop, de historielijst, de nachtgrafieken en de
    automatische conclusie waren hier al voor gerepareerd; deze balk was
    overgeslagen.

    Returns ``(tekst, ernstlabel, waarde_voor_de_kleur)``. Die derde is er
    omdat de kleur dezelfde grootheid moet volgen als het label; ze los
    berekenen is precies hoe ze uiteen gingen lopen.
    """
    if split_diag is not None:
        sev = _sev_with_syndrome(split_diag, rsum, lang)
        txt = (f"{t('pdf_kpi_ahi_no_cpap', lang)} = {split_diag:.1f}{unit}  →  "
               f"<b>{sev}</b>   |   "
               + t("pdf_classbar_wholenight", lang).format(
                   ahi=f"{ahi:.1f}", oahi=f"{oahi:.1f}")
               + f"   |   Profile: {prof_lbl}")
        return txt, sev, split_diag
    sev = _sev_with_syndrome(ahi, rsum, lang)
    osev = _sev(oahi, lang)
    txt = (f"{ahi_lbl} = {ahi:.1f}{unit}  →  <b>{sev}</b>   |   "
           f"{oahi_lbl} = {oahi:.1f}{unit}  →  <b>{osev}</b>{therapy_note}"
           f"   |   Profile: {prof_lbl}")
    return txt, sev, ahi


def _sev_with_syndrome(ahi, rsum, lang="nl"):
    """
    Severity-label gecombineerd met dynamisch syndroom-type.
    Alleen voor AHI, NIET voor OAHI (OAHI is per definitie obstructief).

    Voorbeelden:
      - Loos: AHI 51.1, 94% centraal -> 'Ernstig CSAS'
      - Standaard OSA: AHI 28, 95% obstructief -> 'Matig OSAS'
      - Normale AHI: geen syndroom-label, gewoon 'Normaal'
    """
    try:
        v = float(ahi)
    except Exception:
        return "--"
    generic_labels = {
        "Normal":   {"nl":"Normaal",  "fr":"Normal",  "en":"Normal",   "de":"Normal"},
        "Mild":     {"nl":"Mild",     "fr":"Leger",   "en":"Mild",     "de":"Leicht"},
        "Moderate": {"nl":"Matig",    "fr":"Modere",  "en":"Moderate", "de":"Mittel"},
        "Severe":   {"nl":"Ernstig",  "fr":"Severe",  "en":"Severe",   "de":"Schwer"},
    }
    if v < 5:    sev_key = "Normal"
    elif v < 15: sev_key = "Mild"
    elif v < 30: sev_key = "Moderate"
    else:        sev_key = "Severe"
    sev_text = generic_labels[sev_key].get(lang, generic_labels[sev_key]["en"])
    if sev_key == "Normal":
        return sev_text
    syndrome = _apnea_syndrome(rsum, lang)
    return sev_text + " " + syndrome

def _apnea_breakdown_line(rsum, lang="nl"):
    """
    Compacte breakdown-regel voor pagina 1:
    'Apnoe-type: obstructief 16 (6%) . centraal 223 (94%) . gemengd 0 (0%)'

    Returnt None bij totaal=0 (dan niks tonen).
    """
    n_o = (rsum or {}).get("n_obstructive", 0) or 0
    n_c = (rsum or {}).get("n_central", 0) or 0
    n_m = (rsum or {}).get("n_mixed", 0) or 0
    total = n_o + n_c + n_m
    if total == 0:
        return None
    pct_o = round(100 * n_o / total)
    pct_c = round(100 * n_c / total)
    pct_m = round(100 * n_m / total)
    labels = {
        "nl": ("Apnoe-type", "obstructief", "centraal", "gemengd"),
        "fr": ("Type d'apnee", "obstructif", "central", "mixte"),
        "en": ("Apnea type", "obstructive", "central", "mixed"),
        "de": ("Apnoe-Typ", "obstruktiv", "zentral", "gemischt"),
    }
    lab, lab_o, lab_c, lab_m = labels.get(lang, labels["en"])
    return (lab + ": " + lab_o + " " + str(n_o) + " (" + str(pct_o) + "%) · "
            + lab_c + " " + str(n_c) + " (" + str(pct_c) + "%) · "
            + lab_m + " " + str(n_m) + " (" + str(pct_m) + "%)")


# ── v0.15.0: clinician-report enrichments (B1 conclusion, B4 phenotypes, B5 flags) ──

def _phenotype_summary_line(rsum, lang="nl"):
    """B4: compact one-line phenotype summary for page 1 (POSA / REM-predominant)."""
    _UH = t("unit_per_hour", lang)
    ph = (rsum or {}).get("phenotypes") or {}
    tags = []
    posa = ph.get("positional_osa")
    if posa and posa.get("flag"):
        s = t("pdf_pheno_posa", lang)
        if posa.get("ahi_supine") is not None and posa.get("ahi_non_supine") is not None:
            s += f" (supine {posa['ahi_supine']} vs non-supine {posa['ahi_non_supine']}{_UH})"
        tags.append(s)
    remp = ph.get("rem_predominant")
    if remp and remp.get("flag"):
        s = t("pdf_pheno_rem", lang)
        if remp.get("rem_ahi") is not None and remp.get("nrem_ahi") is not None:
            s += f" (REM {remp['rem_ahi']} vs NREM {remp['nrem_ahi']}{_UH})"
        tags.append(s)
    if not tags:
        return None
    return "<b>" + t("pdf_pheno_hdr", lang) + ":</b> " + "  ·  ".join(tags)


def _recording_date(meta, dash="—"):
    """De datum waarop de OPNAME gemaakt is, niet die van de analyse.

    `analysis_timestamp` stond onder het label "Opnamedatum". Dat is de datum
    waarop de analyse draaide: een heranalyse verzette daarmee de datum van een
    onderzoek dat maanden eerder plaatsvond, en twee runs van dezelfde nacht
    kregen twee verschillende "opnamedatums".

    Ontbreekt `recording_start` — oudere resultaten dragen hem niet — dan is een
    streepje eerlijker dan de verkeerde datum.
    """
    v = (meta or {}).get("recording_start")
    return str(v)[:10] if v else dash


try:                                            # psgscoring >= 0.15.1
    from psgscoring.respiratory import MIN_STAGE_MIN_FOR_INDEX as _MIN_REM_MIN
except Exception:                               # oudere installatie in dev
    _MIN_REM_MIN = 30.0

# Spiegelt `rem_gap_tolerance` in yasa_analysis.py (4 epochs à 30 s). Hier
# gedupliceerd omdat het rapport die module niet importeert; een toets in
# tests/test_report_index_consistency.py bewaakt dat de twee gelijk blijven.
REM_GAP_TOLERANCE_MIN = 2.0


def rem_ahi_caveat(rsum, lang="nl"):
    """Kwalificeer de REM-AHI wanneer er te weinig REM was om hem te dragen.

    psgscoring levert het FEIT (`ahi_rem_reliable`, `rem_min`); dit rapport
    levert de FORMULERING, want de tekst in de bibliotheek is eentalig en dit
    rapport verschijnt in vier talen.

    Waarom kwalificeren en niet weglaten: de index bestaat wél, hij is alleen
    niet te vertrouwen. Weglaten roept bij de lezer de vraag op waar hij bleef;
    een REM-AHI van 64/u naast een NREM-AHI van 39/u zonder vermelding dat de
    eerste op 22 minuten en ~24 events rust, leest als REM-predominante OSA —
    een patroon met behandelconsequenties.

    Ontbreekt het veld — resultaten van vóór 0.15.1 dragen het niet — dan
    zwijgt deze functie. Geen kwalificatie is beter dan een verzonnen kwalificatie.
    """
    rsum = rsum or {}
    if rsum.get("ahi_rem") is None or rsum.get("ahi_rem_reliable") is not False:
        return None
    m = rsum.get("rem_min")
    return t("pdf_rem_ahi_caveat", lang).format(
        rem=f"{m:.0f}" if isinstance(m, (int, float)) else "?",
        min=f"{_MIN_REM_MIN:.0f}")


def provenance_rows(results, lang="nl"):
    """Welk kanaal voedde welke analyse — als ``[[label, waarde], ...]``.

    Drie fouten in de rapporten van augustus 2026 waren allemaal hetzelfde
    soort fout: het rapport beschreef de METHODE in plaats van de UITVOERING.
    Welk EMG de staging voedde stond nergens (en week af van wat het
    kanaaloverzicht toonde), de sensornoot volgde het profiel in plaats van de
    afgekeurde thermistor, en dat de vijf afgeleide analyses een ander
    flowkanaal lezen dan de apneudetectie was onzichtbaar. Twee runs van
    dezelfde nacht waren daardoor niet te vergelijken zonder de logs erbij.

    Deze tabel maakt elk van die drie zichtbaar op de plek waar de lezer ze
    nodig heeft, en is meteen de provenance die externe centra vragen.
    """
    results = results or {}
    meta    = results.get("meta") or {}
    pneumo  = results.get("pneumo") or {}
    pmeta   = pneumo.get("meta") or {}
    fc      = pmeta.get("flow_channels") or {}
    dash    = "—"

    def _lbl(key, fallback):
        try:
            return t(key, lang) or fallback
        except Exception:
            return fallback

    # De staging-rijen komen uit de JOBCONFIG — wat de gebruiker koos, niet
    # wat het EDF bevat. Op een echte opname stonden hier EOG1 en EMG1 terwijl
    # het bestand die kanalen niet had; het blok bevestigde dus een keuze in
    # plaats van de uitvoering, en dat is precies de fout waartegen het bestaat.
    # Toetsen tegen de werkelijke kanaallijst en het verschil benoemen.
    present = set(pmeta.get("all_channels") or [])

    def _staging_ch(name):
        if not name:
            return dash
        if present and name not in present:
            return f"{name} — {_lbl('prov_ch_absent', 'niet in dit EDF-bestand')}"
        return name

    rows = [
        [_lbl("prov_staging_eeg", "Staging — EEG"), _staging_ch(meta.get("eeg_channel"))],
        [_lbl("prov_staging_eog", "Staging — EOG"), _staging_ch(meta.get("eog_channel"))],
        [_lbl("prov_staging_emg", "Staging — EMG"), _staging_ch(meta.get("emg_channel"))],
        [_lbl("prov_apnea", "Apneu"), fc.get("apnea_sensor") or dash],
        [_lbl("prov_hypopnea", "Hypopneu"), fc.get("hypopnea_sensor") or dash],
    ]

    # Het EEG dat de arousal-analyse voedde is niet noodzakelijk het EEG dat
    # de staging voedde: staging krijgt de kanaalkeuze van de gebruiker, de
    # respiratoire pijplijn detecteert zijn eigen EEG-rol. Op een echte opname
    # was dat C4 tegen C3 — twee kanalen in één run, en het rapport toonde er
    # één. Alleen tonen wanneer ze verschillen, anders is het ruis.
    _ar_sum = ((pneumo.get("arousal") or {}).get("arousals") or {}).get(
        "summary") or {}
    _ar_eeg = _arousal_eeg_label(pmeta, _ar_sum)
    if _arousal_row_needed(meta.get("eeg_channel"), pmeta, _ar_sum):
        rows.append([_lbl("prov_arousal_eeg", "Arousal-analyse — EEG"), _ar_eeg])

    # psgscoring kan de arousal-onsets over een vast aantal seconden schuiven
    # (`arousal_onset_offset_s`, default 0,0). Staat die vlag aan, dan liggen
    # de onsets in DIT rapport ergens anders dan de detector ze vond, en is de
    # AHI/RDI met die verschoven arousals berekend. Een verschuiving die
    # nergens vermeld wordt, maakt twee rapporten van dezelfde nacht
    # onvergelijkbaar zonder dat iemand kan zien waarom -- dezelfde fout als de
    # drie waarvoor deze tabel is gebouwd. Alleen tonen als er geschoven is.
    # Een DC-gekoppelde opname is vóór de analyse gefilterd. Dat verandert de
    # signalen waarop ALLES rust, dus het hoort in de provenance en niet alleen
    # in een waarschuwing die je kunt wegkijken. Alleen tonen als het gebeurd is.
    # Split-night: het breekpunt hoort in de provenance, want alles wat
    # eronder staat is per segment berekend. Zonder deze regel is niet te zien
    # dat de nacht in tweeën is gelezen.
    _sn = ((results.get("pneumo") or {}).get("split_night")
           or results.get("split_night") or {})
    if _sn.get("detected") and _sn.get("breakpoint_s"):
        _b = float(_sn["breakpoint_s"])
        _hoe = {"manual": "opgegeven", "flow_amplitude+spo2_baseline": "gedetecteerd"}.get(
            _sn.get("method"), _sn.get("method") or "")
        rows.append([_lbl("prov_split_night", "Split-night — start therapie"),
                     f"{int(_b // 3600)}:{int((_b % 3600) // 60):02d} ({_hoe})"])

    _dc = (results.get("dc_highpass") or
           (results.get("meta") or {}).get("dc_highpass") or {})
    if _dc.get("applied"):
        _n = _dc.get("n_channels") or len(_dc.get("channels") or {})
        _max = _dc.get("max_offset_uv")
        _txt = f"{_dc.get('cutoff_hz', 0.3):.2f} Hz — {_n} kanalen"
        if _max:
            _txt += f", offset tot {abs(float(_max)):.0f} µV"
        rows.append([_lbl("prov_dc_highpass",
                          "Gelijkspanning verwijderd (hoogdoorlaat)"), _txt])

    _off = _ar_sum.get("onset_offset_s")
    try:
        _off = float(_off) if _off is not None else 0.0
    except (TypeError, ValueError):
        _off = 0.0
    if _off:
        rows.append([_lbl("prov_arousal_onset_offset", "Arousal-onsets verschoven"),
                     f"{_off:+.1f} s"])

    # Env-overrides overrulen profielwaarden. Zonder deze regel betekent
    # dezelfde profielnaam op twee machines iets anders, en juist dit blok
    # hoort de UITVOERING te tonen in plaats van de keuze. Alleen tonen wanneer
    # er iets aan staat — anders is het ruis op elk rapport.
    _env = pmeta.get("env_overrides") or {}
    if _env:
        rows.append([_lbl("prov_env_overrides", "Afwijkende parameters (omgeving)"),
                     ", ".join(f"{k}={v}" for k, v in sorted(_env.items()))])

    # De vijf afgeleide analyses (AHI-sweep, baseline, arousal-koppeling, CSR,
    # ventilatoire last) lezen sinds psgscoring 0.14.1 een eigen referentie.
    # Alleen tonen wanneer die afwijkt van het apneukanaal — anders is het ruis.
    ref = fc.get("reference_sensor")
    if ref and ref != fc.get("apnea_sensor"):
        rows.append([_lbl("prov_reference", "Afgeleide analyses"), ref])

    # Thermistor: VIER gevallen, niet drie. Het vierde ontbrak en dat leverde
    # een tegenspraak binnen één rapport op: bij een additief profiel wordt een
    # thermistor die de kwaliteitstoets NIET haalt toch behouden — de tweede
    # detectiepas maakt hem onschadelijk — en dit blok noemde hem dan
    # "bruikbaar", terwijl de corroboratiekolom twee bladzijden verderop toonde
    # dat hij 0 van de 95 apneus had bijgedragen. De overeenstemming was 0,23
    # tegen een drempel van 0,40. Behouden omdat het profiel additief is, is
    # iets anders dan bruikbaar.
    rejected = fc.get("thermistor_rejected")
    check    = fc.get("thermistor_check") or {}
    agree    = check.get("agreement")
    usable   = check.get("usable")
    agree_s  = f" ({agree:.2f})" if isinstance(agree, (int, float)) else ""
    label    = _lbl("prov_thermistor", "Thermistor")
    name     = rejected or fc.get("apnea_sensor") or dash
    if rejected:
        rows.append([label,
                     f"{name} — {_lbl('prov_therm_rejected', 'afgekeurd')}{agree_s}"])
    elif fc.get("dual_sensor") and usable is False:
        # Aanwezig, onder de drempel, tóch gebruikt omdat het profiel additief
        # is. Het getal erbij, zodat de lezer ziet hoe zwak de steun is.
        rows.append([label,
                     f"{name} — {_lbl('prov_therm_additive', 'onder de kwaliteitsdrempel, additief gebruikt')}{agree_s}"])
    elif fc.get("dual_sensor"):
        rows.append([label,
                     f"{name} — {_lbl('prov_therm_usable', 'bruikbaar')}{agree_s}"])
    else:
        rows.append([label, _lbl("prov_therm_absent", "niet in montage")])

    rows.append([_lbl("prov_profile", "Scoringsprofiel"),
                 pmeta.get("scoring_profile") or dash])
    # De versie die GESCOORD heeft, niet die van vandaag. Een rapport kan
    # later gerenderd worden dan de analyse draaide -- dan is de actueel
    # geinstalleerde versie de verkeerde herkomst. `tasks.py` legt de echte
    # versie bij het scoren vast in `comparison._meta.psgscoring_version`;
    # ontbreekt die (oudere jobs), dan valt hij terug op wat er nu staat, en
    # dat wordt dan als benadering gemarkeerd.
    # Eerst het stempel dat de pipeline zelf in elke run zet (psgscoring
    # >= 0.27.0); daarna het `comparison`-blok, dat alleen bestaat als er
    # meerdere profielen vergeleken zijn -- bij een gewone klinische run met
    # EEN profiel dus niet, en daar bleef het onzekerheidsteken permanent staan.
    _stored = ((results or {}).get("pneumo") or {}).get("meta", {}).get(
        "psgscoring_version")
    if not _stored:
        _stored = (((results or {}).get("comparison") or {}).get("_meta") or {}
                   ).get("psgscoring_version")
    if _stored:
        _psg = str(_stored)
    else:
        _psg = f"{_PSGSCORING_VERSION} (?)"
    rows.append([_lbl("prov_software", "Software"),
                 f"psgscoring {_psg} · YASAFlaskified {_APP_VERSION}"])
    return rows


def flow_sensor_notes(resp, pneumo):
    """Welke sensornoot hoort onder de respiratoire tabel?

    Retourneert ``[(i18n_key, format_kwargs), ...]`` — de tekst zelf blijft in
    i18n, de keuze is hier en is los testbaar.

    De noot volgde het PROFIEL ("dual-sensor gevraagd") in plaats van wat er
    feitelijk gebeurde. Twee gevolgen in échte rapporten: een duaal rapport
    claimde "apneu op thermistor" terwijl de corroboratiekolom liet zien dat
    geen enkele apneu van de thermistor kwam, en een rapport meldde "één
    flowkanaal beschikbaar" terwijl de kanaallijst erboven er twee toonde —
    de thermistor zat in het bestand maar was door de kwaliteitstoets
    afgewezen. Afwezig en afgekeurd is niet hetzelfde, en dat verschil hoort
    de lezer te zien.
    """
    resp   = resp or {}
    fc     = ((pneumo or {}).get("meta") or {}).get("flow_channels") or {}
    apnea  = fc.get("apnea_sensor") or "—"
    hypop  = fc.get("hypopnea_sensor") or "—"
    rejected = fc.get("thermistor_rejected")
    agree    = (fc.get("thermistor_check") or {}).get("agreement")
    agree_s  = f"{agree:.2f}" if isinstance(agree, (int, float)) else "—"

    # Geval 1: twee sensoren, elk in hun AASM-rol.
    if resp.get("dual_sensor") and apnea != hypop:
        notes = [("pdf_dual_sensor_note", {})]
        dsa = resp.get("dual_sensor_apnea") or {}
        if dsa and not (dsa.get("n_both") or dsa.get("n_thermistor_only")):
            notes.append(("pdf_dual_sensor_no_corrob", {}))
        return notes

    # Geval 2: thermistor aanwezig maar afgekeurd.
    if rejected:
        return [("pdf_thermistor_rejected_note",
                 {"therm": rejected, "apnea": apnea, "agreement": agree_s})]

    # Geval 3: werkelijk één flowkanaal.
    return [("pdf_single_sensor_note", {"apnea": apnea, "hypopnea": hypop})]


def _central_component_present(rsum, pneumo):
    """True when a clinically relevant central component is present."""
    try:
        n_o = (rsum or {}).get("n_obstructive", 0) or 0
        n_c = (rsum or {}).get("n_central", 0) or 0
        n_m = (rsum or {}).get("n_mixed", 0) or 0
        total = n_o + n_c + n_m
        if total and (n_c / total) > 0.5:
            return True
    except Exception:
        pass
    return bool((pneumo.get("cheyne_stokes") or {}).get("criteria_met"))


def _is_central_dominant(rsum):
    """True when > 50% of apneic events are central (CSAS pattern). Used to suppress
    the ventilatory-burden reference (≤ 25%), which is derived and validated in
    OBSTRUCTIVE OSA cohorts (AJRCCM 2023) and is not calibrated for central apnea /
    Cheyne-Stokes, where VB is inherently very high by morphology."""
    try:
        n_o = (rsum or {}).get("n_obstructive", 0) or 0
        n_c = (rsum or {}).get("n_central", 0) or 0
        n_m = (rsum or {}).get("n_mixed", 0) or 0
        total = n_o + n_c + n_m
        return bool(total > 0 and (n_c / total) > 0.5)
    except Exception:
        return False


# Analysewaarschuwing -> vertaalsleutel. Een code zonder sleutel valt terug op
# zijn eigen (Nederlandse) `message`: zichtbaar in de verkeerde taal is beter
# dan onzichtbaar, en dat was tot v0.34.1 het geval voor alle codes.
_WARNING_KEYS = {
    "emg_channel_missing": "pdf_warn_emg_missing",
    "eog_channel_missing": "pdf_warn_eog_missing",
    "all_epochs_artefact": "pdf_warn_all_artefact",
    "dc_highpass_applied": "pdf_warn_dc_highpass",
    "atypical_topography": "pdf_warn_topography",
}


def _arousal_eeg_label(pmeta, ar_summary):
    """Welke EEG-afleiding(en) de arousal-analyse gevoed hebben.

    `channels_used["eeg"]` is element 0 van de afleidingsset, niet de set. Op
    een klinisch rapport stond daardoor "C3" terwijl er `C3 u C4` draaide --
    twee afleidingen met allebei events (142 en 115). Dat is precies wat deze
    tabel moet tonen; er staat onder dat de kanaalkeuze de uitkomst bepaalt.

    De lijst wint van het enkele kanaal; ontbreekt hij (resultaten van vóór dit
    veld, of het single-modus-pad dat er geen zet), dan blijft het kanaal.
    """
    pmeta = pmeta or {}
    derivs = (ar_summary or {}).get("derivations")
    if derivs:
        namen = [str(d) for d in derivs if d]
        if len(namen) > 1:
            return " \u222a ".join(namen)
        if namen:
            return namen[0]
    return (pmeta.get("channels_used") or {}).get("eeg")


def _arousal_row_needed(staging_eeg, pmeta, ar_summary) -> bool:
    """Hoort de arousal-EEG-rij in de tabel?

    Ze stond er alleen wanneer het arousal-EEG AFWEEK van het stagingkanaal.
    Draait er een union op C4 u O2 terwijl de staging ook C4 gebruikt, dan
    verdween de hele rij en zag niemand dat er twee afleidingen liepen.
    """
    label = _arousal_eeg_label(pmeta, ar_summary)
    if not label:
        return False
    derivs = (ar_summary or {}).get("derivations") or []
    return len(derivs) > 1 or label != staging_eeg


def _detector_row_label(rij) -> str:
    """Het label van een spindel- of SW-samenvattingsrij.

    Kanaal én stadium wanneer de detector op allebei gegroepeerd heeft --
    anders staan er twee rijen "C4-M1" onder elkaar met verschillende getallen
    en is niet te zien welke welke is.
    """
    delen = []
    for sleutel in ("Channel", "channel"):
        if rij.get(sleutel):
            delen.append(str(rij[sleutel]))
            break
    for sleutel in ("Stage", "stage"):
        if rij.get(sleutel) not in (None, ""):
            delen.append(str(rij[sleutel]))
            break
    return " · ".join(delen) if delen else "—"


def _position_rows(pos_sum, lang="nl"):
    """De positie-AHI-rijen: getal, "te kort", of geen rij.

    psgscoring geeft `None` zodra er minder dan `min_minutes_for_index` in een
    houding geslapen is -- de tabel toonde daarvoor 120,0/u uit één event in
    een halve minuut. De rapportlaag sloeg elke None over, en dan staat er
    NIETS: niet te onderscheiden van een houding waarin de patiënt nooit
    gelegen heeft. Die twee horen verschillend te lezen.
    """
    _UH = t("unit_per_hour", lang)
    pos_sum = pos_sum or {}
    ahi_pos = pos_sum.get("ahi_per_pos") or {}
    minuten = pos_sum.get("sleep_time_min") or {}
    drempel = pos_sum.get("min_minutes_for_index") or 15.0
    rijen = []
    for naam, ahi in sorted(ahi_pos.items()):
        if ahi is not None:
            rijen.append([f"AHI {naam}", f"{ahi:.1f} {_UH}"])
            continue
        m = minuten.get(naam)
        if not m:                      # nooit in die houding geslapen
            continue
        # Niet afronden op hele minuten: 0,5 min zou "0 min" worden en dat
        # leest als "nooit in die houding" -- precies het onderscheid dat deze
        # rij moet maken.
        _m = f"{m:.1f}" if m < 10 else f"{m:.0f}"
        rijen.append([f"AHI {naam}",
                      t("pdf_pos_too_short", lang).format(
                          min=_m, drempel=f"{drempel:.0f}")])
    # Is de codering niet herkend, dan is de labelvolgorde een aanname en mag
    # geen enkele rij als meting gelezen worden.
    if rijen and not _position_mapping_is_coded(pos_sum):
        rijen.append(["", t("pdf_pos_uncoded", lang)])
    return rijen


def _channel_counts(blok):
    """{kanaalnaam: aantal} uit een YASA-samenvatting, hoofdletterongevoelig."""
    uit = {}
    for rij in (blok or {}).get("summary") or []:
        if not isinstance(rij, dict):
            continue
        naam = str(rij.get("Channel") or "").upper()
        try:
            uit[naam] = uit.get(naam, 0) + int(rij.get("Count") or 0)
        except (TypeError, ValueError):
            continue
    return uit


def _som(tellingen, namen):
    """Telt kanalen op waarvan de naam een van `namen` bevat (F3 matcht EEG F3-A2)."""
    return sum(v for k, v in tellingen.items() if any(n in k for n in namen))


def _topography_warning(results):
    """Staan de spindels en trage golven waar ze horen?

    Spindels zijn frontocentraal maximaal, trage golven frontaal dominant. Op de
    Thaise casus van 26-08-2026 stond het dubbel omgekeerd: spindels F4 804 /
    F3 521 tegen C3 14 / C4 36, en trage golven O1/O2 elk 276 tegen F3 3. Dat
    patroon is geen fysiologie maar een montage: verwisselde labels of een
    andere referentie. Staging draaide er wél op.

    Alleen vlaggen, nooit corrigeren -- welke twee kanalen verwisseld zijn, is
    van buitenaf niet vast te stellen, en een gok zou de fout verplaatsen in
    plaats van hem te tonen.
    """
    sp = _channel_counts(results.get("spindles"))
    sw = _channel_counts(results.get("slow_waves"))
    if not sp or not sw:
        return None
    sw_occ, sw_front = _som(sw, ("O1", "O2")), _som(sw, ("F3", "F4"))
    sp_front, sp_centr = _som(sp, ("F3", "F4")), _som(sp, ("C3", "C4"))
    # Beide omkeringen moeten meedoen. Eén ervan alleen komt voor bij een
    # slecht kanaal; samen zijn ze een montagepatroon.
    if (sw_front > 0 or sw_occ > 0) and (sp_centr > 0 or sp_front > 0):
        if sw_occ > 3 * max(sw_front, 1) and sp_front > 3 * max(sp_centr, 1):
            return {"sw_occipital": sw_occ, "sw_frontal": sw_front,
                    "spindles_frontal": sp_front, "spindles_central": sp_centr}
    return None


def _position_mapping_is_coded(pos_sum):
    """Is de houdingscodering herkend, of is de volgorde een aanname?

    `position_mapping_method` staat sinds psgscoring 0.27.2 in de samenvatting.
    "levels" betekent: de recorder gebruikt codes die wij niet kennen, en de
    rangorde is geraden. Op de Thaise casus leverde dat vrijwel de hele nacht
    "PRO" op -- onwaarschijnlijk en niet te weerleggen. De tabel mag dan blijven
    staan, maar niet ongekwalificeerd.
    """
    return str((pos_sum or {}).get("position_mapping_method") or "") == "coded"


_FRI_SENTINEL = object()


def _fri_index(rsum, stats=None):
    """De FRI-index, uit één bron.

    Sectie 8d en de RERA-sectie rekenden hem elk zelf uit, met een andere
    noemer: `stats["TST"]` uit de YASA-slaapstatistiek tegenover de slaaptijd
    die psgscoring voor al zijn indices gebruikt (artefact-epochs eruit). Eén
    rapport toonde daardoor 44,3/u naast 43,2/u over dezelfde nacht.

    Volgorde:
      1. `rsum["fri_index"]` -- psgscoring vanaf 0.27.1. Ook `None` telt: dat
         betekent "geen bruikbare slaaptijd", een uitspraak en geen gat.
      2. de noemer gereconstrueerd uit `n_rera / rera_index` -- dezelfde
         noemer, voor resultaten van vóór dat veld.
      3. `stats["TST"]` -- laatste redmiddel, en de enige die kan afwijken.
    """
    if rsum is None:
        return None
    val = rsum.get("fri_index", _FRI_SENTINEL)
    if val is not _FRI_SENTINEL:
        return val
    n_fri = rsum.get("n_fri")
    if not n_fri:
        return None
    n_rera, rera_idx = rsum.get("n_rera"), rsum.get("rera_index")
    if n_rera and rera_idx:
        return round(n_fri / (n_rera / rera_idx), 1)
    try:
        tst_h = float(str((stats or {}).get("TST", 0) or 0)) / 60.0
    except (TypeError, ValueError):
        return None
    return round(n_fri / tst_h, 1) if tst_h > 0 else None


def _clinical_flags(rsum, pneumo, ss, asum, lang="nl", warnings=None):
    """B5: descriptive clinician attention points (NOT medical advice).

    v0.34.1: `analysis_warnings` uit `tasks.py` komt hier binnen. Die lijst
    werd geschreven en door NIEMAND gelezen -- geen PDF-sectie, geen sjabloon,
    geen route. Dat is dezelfde fout als de regressie die deze release
    repareert, een laag hoger: een waarschuwing die alleen in een JSON-bestand
    staat is geen waarschuwing.
    """
    flags = []
    for w in (warnings or []):
        if not isinstance(w, dict):
            continue
        key = _WARNING_KEYS.get(w.get("code"))
        txt = t(key, lang) if key else (w.get("message") or "")
        if txt:
            flags.append(txt)
    ph = (rsum or {}).get("phenotypes") or {}
    posa = ph.get("positional_osa")
    if posa and posa.get("flag") and posa.get("positional_therapy_candidate"):
        flags.append(t("pdf_flag_positional", lang))
    remp = ph.get("rem_predominant")
    if remp and remp.get("flag"):
        flags.append(t("pdf_flag_rem", lang))
    if (pneumo.get("cheyne_stokes") or {}).get("criteria_met"):
        flags.append(t("pdf_flag_csr", lang))
    elif _central_component_present(rsum, pneumo):
        flags.append(t("pdf_flag_central", lang))
    try:
        t90 = ss.get("pct_below_90")
        if t90 is not None and float(t90) >= 10:
            flags.append(t("pdf_flag_hypoxemia", lang).format(pct=f"{float(t90):.0f}"))
    except Exception:
        pass
    try:
        ai = asum.get("arousal_index")
        if ai is not None and float(ai) >= 25:
            flags.append(t("pdf_flag_arousal", lang).format(ai=f"{float(ai):.0f}"))
    except Exception:
        pass
    # ── Discrepantie: meer desaturatie dan er events gescoord zijn ──────
    #
    # Eén rapport toonde AHI 3,1 naast ODI3 14,1, T90 28 % en een hypoxic
    # burden van 17 %·min/u. De hypoxemie werd gevlagd, de discrepantie niet --
    # terwijl die de klinische boodschap is: de desaturatie komt ergens vandaan
    # en de scoring vindt het niet.
    try:
        _ahi = rsum.get("ahi_total")
        _odi = ss.get("odi_3pct")
        _t90 = ss.get("pct_below_90")
        _ahi_f = float(_ahi) if _ahi is not None else None
        _odi_f = float(_odi) if _odi is not None else None
        _t90_f = float(_t90) if _t90 is not None else None
        _disproportie = (
            (_odi_f is not None and _ahi_f is not None
             and _ahi_f > 0 and _odi_f >= 3 * _ahi_f)
            or (_t90_f is not None and _t90_f >= 10
                and _ahi_f is not None and _ahi_f < 5)
        )
        if _disproportie:
            flags.append(t("pdf_flag_desat_discrepancy", lang).format(
                odi=f"{_odi_f:.1f}" if _odi_f is not None else "—",
                ahi=f"{_ahi_f:.1f}" if _ahi_f is not None else "—",
                t90=f"{_t90_f:.0f}" if _t90_f is not None else "—"))
    except (TypeError, ValueError):
        pass

    # ── Split-night: hoort BOVENAAN, niet alleen in een sectie verderop ──
    # De kop meldt één AHI over de hele nacht. Op de casus die dit aanleiding
    # gaf stond daar "Mild SAS, AHI 10,1/u" terwijl het diagnostische deel op
    # 83,5/u lag. Wie alleen de eerste bladzijde leest -- en dat is wat er
    # gebeurt -- zag geen enkel teken dat de nacht in tweeën viel.
    try:
        _sn = (pneumo or {}).get("split_night") or {}
        _seg = _sn.get("segments") or {}
        if _sn.get("detected") and _seg:
            _b = float(_sn.get("breakpoint_s") or 0)
            _d = _seg.get("diagnostic") or {}
            _th = _seg.get("therapeutic") or {}

            def _beste(seg):
                """De AHI die het beeld draagt.

                Bij een falende effort-band is `ahi` een onvolledige telling en
                `ahi_incl_uncertain` het eerlijke getal; boven een vijfde
                ongetypeerd is die tweede de enige die iets zegt.
                """
                if (seg.get("uncertain_fraction") or 0) >= 0.20:
                    return seg.get("ahi_incl_uncertain")
                return seg.get("ahi")

            _dv, _tv = _beste(_d), _beste(_th)
            if _dv is not None and _tv is not None:
                flags.append(t("pdf_flag_split_night", lang).format(
                    tijd=f"{int(_b // 3600)}:{int((_b % 3600) // 60):02d}",
                    diag=f"{_dv:.1f}", ther=f"{_tv:.1f}"))
    except (TypeError, ValueError):
        pass

    # ── Arousal-index die niet bij de eventlast past ────────────────────
    #
    # AI 3,5/u bij AHI 42 met 217 respiratoire events kan fysiologisch niet.
    # Die combinatie stond in een klinisch rapport zonder enige vlag; deze
    # regel had de EMG-transportregressie in één oogopslag zichtbaar gemaakt.
    try:
        _ahi_a = rsum.get("ahi_total")
        _ai = asum.get("arousal_index")
        if _ahi_a is not None and _ai is not None:
            _ahi_a, _ai = float(_ahi_a), float(_ai)
            if _ahi_a >= 15 and _ai < _ahi_a / 2:
                flags.append(t("pdf_flag_arousal_implausible", lang).format(
                    ai=f"{_ai:.1f}", ahi=f"{_ahi_a:.1f}"))
    except (TypeError, ValueError):
        pass

    # ── Bradycardie op het gemiddelde ───────────────────────────────────
    #
    # Beide rapporten toonden 43,8 bpm náást hun eigen referentie "60-100",
    # zonder vlag, terwijl verderop al een bradycardie-telling staat.
    try:
        _hr = ((pneumo.get("heart_rate", {}) or {}).get("summary", {})
               or {}).get("avg_hr")
        if _hr is not None and float(_hr) < 50:
            flags.append(t("pdf_flag_bradycardia_mean", lang).format(
                hr=f"{float(_hr):.1f}"))
    except (TypeError, ValueError):
        pass

    # Het dual-sensor algoritme is gevraagd maar niet uitvoerbaar: dat mag
    # niet stilzwijgend een ander algoritme opleveren dan de gebruiker koos.
    _dsf = (pneumo.get("meta", {}) or {}).get("dual_sensor_fallback") or {}
    if _dsf.get("requested") and not _dsf.get("performed"):
        flags.append(t("pdf_flag_dual_fallback", lang).format(
            channel=_dsf.get("channel") or "—"))
    return flags


def _auto_conclusion(rsum, pneumo, ss, lang="nl"):
    """B1: descriptive auto-generated impression (informational; the physician's
    manual diagnosis always takes precedence). Combines severity+syndrome with
    phenotype and burden qualifiers into one sentence."""
    _UH = t("unit_per_hour", lang)
    try:
        ahi = float(rsum.get("ahi_total", 0) or 0)
    except Exception:
        return None

    # ── Split-night: het nachtgemiddelde is hier de verkeerde grootheid ──
    # Het telt de uren vóór de titratie samen met de uren eronder. Op de casus
    # die dit aan het licht bracht stond er "Mild OSAS (AHI 13,7/u)" terwijl
    # het diagnostische deel op 83,5/u lag -- de samenvatting sprak de kop van
    # hetzelfde rapport tegen.
    #
    # De ondergrens hoort mee te verhuizen: een nacht die gemiddeld onder 5/u
    # uitkomt maar vóór CPAP zwaar is, zou anders "geen significante
    # slaapapneu" heten.
    _ther = None
    try:
        _sn = (pneumo or {}).get("split_night") or {}
        _seg = _sn.get("segments") or {}
        _d, _th = _seg.get("diagnostic") or {}, _seg.get("therapeutic") or {}
        if _sn.get("detected") and _d.get("reliable"):
            def _kies(seg):
                v = (seg.get("ahi_incl_uncertain")
                     if (seg.get("uncertain_fraction") or 0) >= 0.20
                     else seg.get("ahi"))
                return float(v) if v is not None else None
            _dv = _kies(_d)
            if _dv is not None:
                ahi, _ther = _dv, _kies(_th)
    except (TypeError, ValueError):
        _ther = None

    if ahi < 5 and _ther is None:
        return t("pdf_concl_none", lang)
    sev = _sev_with_syndrome(ahi, rsum, lang)          # e.g. "Matig OSAS"
    if _ther is not None:
        sev = f"{sev} {t('pdf_concl_without_cpap', lang)}"
    quals = []
    ph = (rsum or {}).get("phenotypes") or {}
    if (ph.get("positional_osa") or {}).get("flag"):
        quals.append(t("pdf_concl_positional", lang))
    if (ph.get("rem_predominant") or {}).get("flag"):
        quals.append(t("pdf_concl_rem", lang))
    if _central_component_present(rsum, pneumo):
        quals.append(t("pdf_concl_central", lang))
    try:
        if ss.get("pct_below_90") is not None and float(ss["pct_below_90"]) >= 10:
            quals.append(t("pdf_concl_hypoxemia", lang))
    except Exception:
        pass
    txt = f"{sev} (AHI {ahi:.1f}{_UH}"
    if quals:
        txt += ", " + ", ".join(quals)
    txt += ")."
    if _ther is not None:
        txt += " " + t("pdf_concl_on_cpap", lang).format(ther=f"{_ther:.1f}")
    return txt


# ── Componenten ────────────────────────────────────────────────
def _hdr(title,color=None):
    bg=color or NAVY
    t=Table([[Paragraph(title,ParagraphStyle("SH",fontName="Helvetica-Bold",
              fontSize=9,textColor=W,leading=11))]],colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),8)]))
    return t

def _tbl(headers,rows,widths=None,stripe=True):
    if not rows: rows=[["—"]*len(headers)]
    n=len(headers)
    if widths is None: widths=[CW/n]*n
    total=sum(widths); widths=[w*CW/total for w in widths]
    def hp(h): return Paragraph(str(h),ParagraphStyle("TH",fontName="Helvetica-Bold",fontSize=7.5,textColor=W,leading=10))
    def cp(c): return Paragraph(str(c) if c is not None else "—",ParagraphStyle("TC",fontName="Helvetica",fontSize=7.5,textColor=TXT,leading=10))
    data=[[hp(h) for h in headers]]+[[cp(c) for c in r] for r in rows]
    t=Table(data,colWidths=widths)
    st=[("BACKGROUND",(0,0),(-1,0),NAVY),("FONTSIZE",(0,0),(-1,-1),7.5),
        ("GRID",(0,0),(-1,-1),0.25,GRID),("TOPPADDING",(0,0),(-1,-1),2.5),
        ("BOTTOMPADDING",(0,0),(-1,-1),2.5),("LEFTPADDING",(0,0),(-1,-1),4),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE")]
    if stripe:
        for i in range(1,len(data)):
            st.append(("BACKGROUND",(0,i),(-1,i),BGROW if i%2==1 else W))
    t.setStyle(TableStyle(st)); return t

def _kpi(items):
    """items=[(val,lbl,unit,clr),...]"""
    n=len(items); w=CW/n
    cells=[]
    for val,lbl,unit,clr in items:
        vp=Paragraph(f'<font size="13"><b>{val}</b></font><font size="7" color="#6b7a99"> {unit}</font>',
                     ParagraphStyle("KV",fontName="Helvetica-Bold",fontSize=13,alignment=TA_CENTER,leading=15))
        lp=Paragraph(lbl,ParagraphStyle("KL",fontName="Helvetica",fontSize=7,textColor=GR,alignment=TA_CENTER,leading=9))
        inner=Table([[vp],[lp]],colWidths=[w-6])
        inner.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),BGR2),
            ("BOX",(0,0),(-1,-1),0.5,GRID),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("ALIGN",(0,0),(-1,-1),"CENTER")]))
        cells.append(inner)
    t=Table([cells],colWidths=[w]*n)
    t.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),3),
        ("RIGHTPADDING",(0,0),(-1,-1),3),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    return t

# ── Figuren ────────────────────────────────────────────────────
def _hypno_img(timeline, wc=16.2, hc=3.0, lang="nl"):
    stages=[ep.get("stage","W") for ep in timeline]
    # AASM standaard: W bovenaan, REM onderaan
    order={"W":0,"N1":1,"N2":2,"N3":3,"R":4}
    y=[order.get(s,0) for s in stages]; n=len(stages); x=np.arange(n)

    fig,ax=plt.subplots(figsize=(wc/2.54,hc/2.54),dpi=180)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")

    # Stap-lijn (fijn)
    ax.step(x,y,where="post",color="#1a3a5c",linewidth=0.7,alpha=0.9)

    # Gekleurde blokjes per epoch (subtiel)
    for i,(s,yv) in enumerate(zip(stages,y)):
        ax.fill_between([i,i+1],[yv-.42,yv-.42],[yv+.42,yv+.42],
                        color=STAGE_CLR.get(s,"#ccc"),alpha=0.35,linewidth=0)

    # Y-as: W bovenaan (invert)
    ax.set_yticks([0,1,2,3,4])
    ax.set_yticklabels(["W","N1","N2","N3","REM"],fontsize=7,
                       color="#1a3a5c",fontweight="600")
    ax.set_ylim(-0.7,4.7)
    ax.invert_yaxis()  # W bovenaan, REM onderaan

    # X-as: tijd in uren
    te=max(1,n//8); xt=np.arange(0,n+1,te)
    ax.set_xlim(0,max(n,1))
    ax.set_xticks(xt)
    ax.set_xticklabels([f"{t*30/3600:.1f}h" for t in xt],fontsize=6,color="#6b7a99")
    ax.set_xlabel(t("pdf_time_axis",lang),fontsize=7,color="#6b7a99")

    # Horizontale lijnen per stadium (subtiel)
    for yy in [0,1,2,3,4]:
        ax.axhline(yy,color="#e0e6ed",linewidth=0.3,zorder=0)

    # Grid en spines
    ax.grid(axis="x",color="#e0e6ed",linewidth=0.3)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines["left"].set_linewidth(0.4); ax.spines["left"].set_color("#b0b8c4")
    ax.spines["bottom"].set_linewidth(0.4); ax.spines["bottom"].set_color("#b0b8c4")
    ax.tick_params(axis="both",length=2,width=0.4,color="#b0b8c4")

    plt.tight_layout(pad=0.3)
    buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=180,bbox_inches="tight"); plt.close(fig); buf.seek(0)
    return Image(buf,width=wc*cm,height=hc*cm)

def _spo2_img(ts,wc=16.2,hc=2.2):
    y=np.array(ts,dtype=float); x=np.arange(len(y))
    fig,ax=plt.subplots(figsize=(wc/2.54,hc/2.54),dpi=150)
    fig.patch.set_facecolor("white"); ax.set_facecolor("#fafbfd")
    ax.fill_between(x,y,90,where=(y<90),color="#e74c3c",alpha=0.3)
    ax.plot(x,y,color="#2980b9",linewidth=0.8)
    ax.axhline(90,color="#e74c3c",linewidth=0.6,linestyle="--",alpha=0.7)
    ax.set_ylim(70,102); ax.set_ylabel("SpO2 %",fontsize=7)
    n=len(y); te=max(1,n//6); xt=np.arange(0,n+1,te)
    ax.set_xticks(xt); ax.set_xticklabels([f"{t/3600:.1f}h" for t in xt],fontsize=6)
    ax.spines[["top","right"]].set_visible(False); ax.grid(color="#e2e8f0",linewidth=0.3)
    plt.tight_layout(pad=0.3)
    buf=io.BytesIO(); fig.savefig(buf,format="png",dpi=150,bbox_inches="tight"); plt.close(fig); buf.seek(0)
    return Image(buf,width=wc*cm,height=hc*cm)

# ── v0.8.22: Overview plots — gedeelde x-as (uren) ────────────

# Shared plot setup for all overview panels
_OV_WC = 16.2   # cm width
_OV_DPI = 150
_OV_LEFT = 0.09   # fraction — vaste linkermarge voor y-labels
_OV_RIGHT = 0.98

def _ov_setup(hc, dur_h, show_xticklabels=True, split_h=None, split_label=None):
    """Maak figuur + ax met identieke marges voor alle overview-panelen.

    `split_h` tekent een verticale markering waar het tweede deel van de nacht
    begint. Die hoort op ELK paneel: wie de saturatie of de stadia bekijkt moet
    kunnen zien welk deel onder therapie ligt, anders leest hij een herstel als
    een eigenschap van de patiënt in plaats van als het effect van de CPAP.
    """
    fig, ax = plt.subplots(figsize=(_OV_WC/2.54, hc/2.54), dpi=_OV_DPI)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    bot = 0.22 if show_xticklabels else 0.08
    fig.subplots_adjust(left=_OV_LEFT, right=_OV_RIGHT, top=0.95, bottom=bot)
    ax.set_xlim(0, dur_h)
    step = max(1, round(dur_h / 8))
    xt = np.arange(0, dur_h + 0.01, step)
    ax.set_xticks(xt)
    if show_xticklabels:
        ax.set_xticklabels([f"{t:.0f}h" for t in xt], fontsize=5, color="#6b7a99")
    else:
        ax.set_xticklabels([])
    ax.grid(axis="x", color="#e0e6ed", linewidth=0.3)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines["left"].set_linewidth(0.4); ax.spines["bottom"].set_linewidth(0.4)
    ax.tick_params(axis="both", length=2, width=0.4)
    if split_h is not None and 0 < split_h < dur_h:
        ax.axvline(split_h, color="#8e44ad", linewidth=1.1,
                   linestyle=(0, (4, 2)), alpha=0.95, zorder=5)
        if split_label:
            ax.annotate(split_label, xy=(split_h, 1.0),
                        xycoords=("data", "axes fraction"),
                        xytext=(3, -1), textcoords="offset points",
                        fontsize=5, color="#8e44ad", fontweight="600",
                        ha="left", va="top", zorder=6)
    return fig, ax

def _ov_finish(fig, hc):
    """Sla op als Image met vaste breedte — GEEN bbox_inches=tight."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_OV_DPI)  # vaste marges, geen tight
    plt.close(fig); buf.seek(0)
    return Image(buf, width=_OV_WC*cm, height=hc*cm)

POS_LABELS = {0:"BUK",1:"LNK",2:"RUG",3:"REC",4:"STA"}
POS_LABELS_FR = {0:"PRO",1:"GAU",2:"DOS",3:"DRO",4:"DEB"}
POS_LABELS_EN = {0:"PRO",1:"LFT",2:"SUP",3:"RGT",4:"UPR"}

def _hypno_ov(timeline, dur_h, hc=2.2, lang="nl", split_h=None, split_label=None):
    """Hypnogram voor overview (x-as in uren)."""
    stages = [ep.get("stage","W") for ep in timeline]
    order = {"W":0,"N1":1,"N2":2,"N3":3,"R":4}
    n = len(stages)
    epoch_h = 30/3600  # 30s in uren
    x_h = np.arange(n) * epoch_h
    y = [order.get(s,0) for s in stages]

    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False,
                        split_h=split_h, split_label=split_label)
    ax.step(x_h, y, where="post", color="#1a3a5c", linewidth=0.7, alpha=0.9)
    for i,(s,yv) in enumerate(zip(stages,y)):
        ax.fill_between([x_h[i], x_h[i]+epoch_h], [yv-.4,yv-.4], [yv+.4,yv+.4],
                        color=STAGE_CLR.get(s,"#ccc"), alpha=0.35, linewidth=0)
    ax.set_yticks([0,1,2,3,4])
    ax.set_yticklabels(["W","N1","N2","N3","REM"], fontsize=6, color="#1a3a5c", fontweight="600")
    ax.set_ylim(-0.7, 4.7); ax.invert_yaxis()
    for yy in [0,1,2,3,4]: ax.axhline(yy, color="#e0e6ed", linewidth=0.3, zorder=0)
    return _ov_finish(fig, hc)

def _events_ov(events, dur_h, rejected_hyps=None, hc=2.0, split_h=None, split_label=None):
    """Events tijdlijn: OA/CA/MA/HYP/FR — altijd alle rijen zichtbaar."""
    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False,
                        split_h=split_h, split_label=split_label)
    type_map = {"obstructive":0, "central":1, "mixed":2}
    labels = ["OA","CA","MA","HYP","FR"]
    clr_map = {"obstructive":"#e74c3c","central":"#3498db","mixed":"#9b59b6"}
    for ev in events:
        et = ev.get("type","")
        if et in type_map:
            yi = type_map[et]
        elif "hypopnea" in et:
            yi = 3
        else:
            continue
        onset_h = ev.get("onset_s",0)/3600
        dur_ev = ev.get("duration_s",10)/3600
        ax.barh(yi, dur_ev, left=onset_h, height=0.6,
                color=clr_map.get(et,"#e67e22"), alpha=0.7, linewidth=0)
    if rejected_hyps:
        for rh in rejected_hyps:
            onset_h = rh.get("onset_s",0)/3600
            dur_ev = rh.get("duration_s",10)/3600
            ax.barh(4, dur_ev, left=onset_h, height=0.6,
                    color="#95a5a6", alpha=0.5, linewidth=0)
    # Altijd alle 5 rijen tonen
    ax.set_yticks([0,1,2,3,4])
    ax.set_yticklabels(labels, fontsize=6, color="#2c3e50")
    ax.set_ylim(-0.5, 4.5); ax.invert_yaxis()
    for yy in range(5): ax.axhline(yy, color="#e0e6ed", linewidth=0.3, zorder=0)
    return _ov_finish(fig, hc)

def _pos_ov(pos_per_epoch, dur_h, hc=1.6, lang="nl", split_h=None, split_label=None):
    """Positie-tijdlijn (x-as in uren)."""
    # x-labels alleen op laatste plot
    labels = POS_LABELS if lang=="nl" else POS_LABELS_FR if lang=="fr" else POS_LABELS_EN
    n = len(pos_per_epoch)
    epoch_h = 30/3600
    x_h = np.arange(n) * epoch_h
    y = np.array([min(p,4) for p in pos_per_epoch])

    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False,
                        split_h=split_h, split_label=split_label)
    ax.step(x_h, y, where="post", color="#27ae60", linewidth=0.8)
    for i,yv in enumerate(y):
        ax.fill_between([x_h[i], x_h[i]+epoch_h], [yv-.3,yv-.3], [yv+.3,yv+.3],
                        color="#27ae60", alpha=0.15, linewidth=0)
    ax.set_yticks([0,1,2,3,4])
    ax.set_yticklabels([labels.get(i,"?") for i in range(5)], fontsize=6, color="#2c3e50")
    ax.set_ylim(-0.5, 4.5); ax.invert_yaxis()
    for yy in range(5): ax.axhline(yy, color="#e0e6ed", linewidth=0.3, zorder=0)
    return _ov_finish(fig, hc)

def _snore_ov(rms_1s, dur_h, hc=1.4, split_h=None, split_label=None):
    """Snurk-amplitude (PHONO) — x-as in uren."""
    y = np.array(rms_1s, dtype=float)
    x_h = np.arange(len(y)) / 3600

    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False,
                        split_h=split_h, split_label=split_label)
    ax.fill_between(x_h, 0, y, color="#95a5a6", alpha=0.4, linewidth=0)
    ax.plot(x_h, y, color="#7f8c8d", linewidth=0.3)
    threshold = float(np.percentile(y, 60))
    ax.axhline(threshold, color="#e67e22", linewidth=0.5, linestyle="--", alpha=0.6)
    ax.set_ylim(0, None)

    return _ov_finish(fig, hc)

def _spo2_ov(ts, dur_h, hc=1.6, split_h=None, split_label=None):
    """SpO2 tijdlijn — x-as in uren."""
    y = np.array(ts, dtype=float)
    x_h = np.arange(len(y)) / 3600  # SpO2 timeseries at 1 Hz

    fig, ax = _ov_setup(hc, dur_h, split_h=split_h, split_label=split_label)
    ax.fill_between(x_h, y, 90, where=(y<90), color="#e74c3c", alpha=0.3)
    ax.plot(x_h, y, color="#2980b9", linewidth=0.8)
    ax.axhline(90, color="#e74c3c", linewidth=0.6, linestyle="--", alpha=0.7)
    ax.set_ylim(70, 102)

    return _ov_finish(fig, hc)

# ── Header / footer ────────────────────────────────────────────
def _callbacks(site, lang="nl"):
    logo=site.get("logo_path","")
    if logo and not os.path.isabs(logo):
        logo=os.path.join(os.path.dirname(__file__),"static",logo)
    has_logo=bool(logo and os.path.exists(logo))

    def draw(canvas,doc):
        canvas.saveState()
        ty=H_A4-MT+0.3*cm
        if has_logo:
            try: canvas.drawImage(logo,W_A4-MR-2.8*cm,ty-1.0*cm,
                                  width=2.8*cm,height=1.0*cm,
                                  preserveAspectRatio=True,mask="auto")
            except: pass
        canvas.setFont("Helvetica-Bold",9); canvas.setFillColor(NAVY)
        canvas.drawString(ML,ty-0.4*cm,site.get("name","SleepAI"))
        parts=[p for p in [site.get("address"),
               ("☎ "+site["phone"]) if site.get("phone") else None,
               site.get("email")] if p]
        if parts:
            canvas.setFont("Helvetica",7); canvas.setFillColor(GR)
            canvas.drawString(ML,ty-0.75*cm,"  ·  ".join(parts))
        canvas.setStrokeColor(NAVY); canvas.setLineWidth(0.8)
        canvas.line(ML,ty-0.95*cm,W_A4-MR,ty-0.95*cm)
        # ── Footer ──
        canvas.setLineWidth(0.3); canvas.setStrokeColor(GRID)
        canvas.line(ML,MB-0.2*cm,W_A4-MR,MB-0.2*cm)
        canvas.setFont("Helvetica",6.5); canvas.setFillColor(GR)
        canvas.drawString(ML,MB-0.45*cm,
            f"YASAFlaskified v{_APP_VERSION}  |  AASM  |  www.slaapkliniek.be  |  \u00a9 Bart Rombaut")
        canvas.drawRightString(W_A4-MR,MB-0.45*cm,f"{t('pdf_page',lang)} {doc.page}")
        canvas.restoreState()
    return draw,draw

# ── AASM scoretabel ────────────────────────────────────────────
def _aasm_tbl(stats, lang="nl"):
    def _vm(k): return _v(stats,k,fmt="{:.0f}")+" min"
    def _vp(k): return _v(stats,k,fmt="{:.1f}")+"%"
    rows=[
        ["TIB",                               _vm("TIB"),"100%",""],
        ["TST",                               _vm("TST"),_vp("SE"),""],
        ["SPT",                               _vm("SPT"),"—",""],
        [t("pdf_se",lang),                    _vp("SE"),"—","≥ 85%"],
        ["SME",                               _vp("SME"),"—",""],
        [t("pdf_sol",lang),                   _vm("SOL"),"—","< 30 min"],
        ["WASO",                              _vm("WASO"),"—","< 30 min"],
        [t("pdf_rem_lat",lang),               _v(stats,"Lat_REM",fmt="{:.0f}")+" min","—","< 120 min"],
        ["N1",                                _vm("N1"), _vp("%N1"),"2–5%"],
        ["N2",                                _vm("N2"), _vp("%N2"),"45–55%"],
        ["N3",                                _vm("N3"), _vp("%N3"),"15–20%"],
        ["REM",                               _vm("REM"),_vp("%REM"),"20–25%"],
    ]
    return _tbl([t("pdf_param",lang),t("pdf_value",lang),"% TST","Ref (AASM)"],
                rows,[7.5,3,3,3.5])


# ══════════════════════════════════════════════════════════════
# v0.8.22: EPOCH-VOORBEELDEN — representatieve signaalfragmenten
# ══════════════════════════════════════════════════════════════

# Kanalen die we willen tonen (in volgorde van boven naar beneden)
_EPOCH_CH_ORDER = [
    ("flow",            "Flow",         "#2980b9"),
    ("flow_pressure",   "Nasal P.",     "#3498db"),
    ("flow_thermistor", "Thermistor",   "#1abc9c"),
    ("thorax",          "Thorax",       "#e67e22"),
    ("abdomen",         "Abdomen",      "#d35400"),
    ("spo2",            "$SpO_2$",      "#e74c3c"),
    ("snore",           "Snore",        "#8e44ad"),
]

def _select_example_events(events, n=3):
    """Selecteer representatieve events voor epoch-voorbeelden.

    Strategie: 1 event met hoogste confidence, 1 langste event,
    1 event met grootste desaturatie. Deduplicatie op tijdsoverlap.
    """
    if not events:
        return []
    # Filter alleen events met onset_s
    valid = [e for e in events if e.get("onset_s") is not None]
    if not valid:
        return []

    picks = {}

    # Hoogste confidence
    by_conf = sorted(valid, key=lambda e: e.get("confidence", 0), reverse=True)
    if by_conf:
        picks["best"] = by_conf[0]

    # Langste event
    by_dur = sorted(valid, key=lambda e: e.get("duration_s", 0), reverse=True)
    if by_dur:
        picks["longest"] = by_dur[0]

    # Grootste desaturatie
    by_desat = sorted(valid, key=lambda e: e.get("desaturation_pct", 0) or 0, reverse=True)
    if by_desat and (by_desat[0].get("desaturation_pct") or 0) >= 3:
        picks["desat"] = by_desat[0]

    # Deduplicatie: events die <60s uit elkaar liggen zijn "hetzelfde"
    result = []
    for label, ev in picks.items():
        overlap = False
        for existing in result:
            if abs(ev["onset_s"] - existing["onset_s"]) < 60:
                overlap = True
                break
        if not overlap:
            ev = dict(ev)
            ev["_label"] = label
            result.append(ev)
        if len(result) >= n:
            break

    return result


def epoch_panel_png(edf_path, channel_map, event, hypno=None,
                    pre_s=15, post_s=30, wc=16.2, hc_per_ch=1.2,
                    all_events=None, raw=None):
    """Plot een enkel epoch-voorbeeld: gestapelde pneumokanalen rond een event.

    Parameters
    ----------
    edf_path : str       Pad naar EDF-bestand
    channel_map : dict   {type: channel_name} mapping
    event : dict         Event met onset_s, duration_s, type, etc.
    hypno : list         Hypnogram (optioneel, voor stage label)
    pre_s, post_s : float  Seconden vóór/na event
    all_events : list    Alle events (optioneel, voor markering van andere events in venster)
    """
    import mne
    mne.set_log_level("ERROR")

    onset  = float(event["onset_s"])
    dur    = float(event["duration_s"])
    t_start = max(0, onset - pre_s)
    t_end   = onset + dur + post_s

    # perf: reuse a pre-loaded raw (shared across all example events by
    # _build_epoch_examples) so the EDF is read+loaded ONCE per report instead
    # of once per event. The shared raw is read full-header (preload=False) +
    # pick(needed) + load_data, so sfreq and sample values are byte-identical to
    # the per-event path. When no raw is passed (e.g. standalone), we open it
    # here (a single read — was two: a redundant header read is gone).
    _own_raw = raw is None
    if _own_raw:
        try:
            raw = read_raw_signal(edf_path, preload=False, verbose=False)
        except Exception:
            return None
    available = raw.ch_names

    # Eén rij per FYSIEK kanaal, niet per rol. Op een montage met één
    # druksensor wijzen `flow` en `flow_pressure` allebei naar hetzelfde
    # kanaal; dat twee keer tekenen suggereert twee sensoren die het eens
    # zijn, wat in een controle-instrument precies de verkeerde indruk is.
    # (En `raw.pick()` weigert een lijst met dubbels ronduit:
    # "Found 6 / 7 unique names, sel is not unique".)
    ch_to_plot, _alias = [], {}
    for ch_type, label, color in _EPOCH_CH_ORDER:
        ch_name = channel_map.get(ch_type)
        if not ch_name or ch_name not in available:
            continue
        if ch_name in _alias:
            _alias[ch_name].append(ch_type)
            continue
        _alias[ch_name] = [ch_type]
        ch_to_plot.append((ch_type, ch_name, label, color))

    if len(ch_to_plot) < 2:
        return None

    try:
        if _own_raw:
            # Load only the needed channels (full night — required so the
            # mixed-sample-rate channels keep the same upsampling as before;
            # partial/cropped reads change those values).
            raw.pick([c[1] for c in ch_to_plot])
            raw.load_data()
        sf = raw.info["sfreq"]
    except Exception:
        return None

    n_ch = len(ch_to_plot)
    total_hc = max(n_ch * hc_per_ch, 3)
    fig, axes = plt.subplots(n_ch, 1, figsize=(wc/2.54, total_hc/2.54),
                              sharex=True, dpi=150)
    if n_ch == 1:
        axes = [axes]
    fig.patch.set_facecolor("white")

    s_start = int(t_start * sf)
    s_end   = min(int(t_end * sf), raw.n_times)
    times   = np.arange(s_start, s_end) / sf  # in seconds

    # Determine detection channel for this event type
    _det_ch_type = None
    ev_type_raw = event.get("type", "").lower()
    if "apnea" in ev_type_raw or ev_type_raw in ("obstructive", "central", "mixed"):
        _det_ch_type = "flow"  # thermistor for apneas
        if "flow" not in [c[0] for c in ch_to_plot]:
            _det_ch_type = "flow_thermistor"
    elif "hypopnea" in ev_type_raw:
        _det_ch_type = "flow_pressure"  # nasal pressure for hypopneas
        if "flow_pressure" not in [c[0] for c in ch_to_plot]:
            _det_ch_type = "flow"

    # De gezochte rol kan als dubbele zijn weggevallen: `flow_pressure` en
    # `flow` delen op veel montages één kanaal. De markering hoort dan op de
    # rij te staan die dat kanaal wél tekent, anders wijst hij nergens naar.
    if _det_ch_type and _det_ch_type not in [c[0] for c in ch_to_plot]:
        _gezocht = channel_map.get(_det_ch_type)
        for ct, cn, _, _ in ch_to_plot:
            if cn and cn == _gezocht:
                _det_ch_type = ct
                break

    # ── Blauw: andere GESCOORDE events in het venster ───────────
    #
    # Elk overlappend event wordt gemarkeerd, ook wanneer het de vensterrand
    # overschrijdt. De oude regel sloeg alles over waarvoor
    # `oe_onset < t_start + 2 or oe_end > t_end - 2` gold, en dat filterde juist
    # de half-zichtbare buren weg — de meest voorkomende soort. Op het paneel
    # rond de obstructieve apneu bij t=316,6 s (PSG-IPA SN3) bleef de apneu op
    # 359,4–371,1 s daardoor onbemarkeerd terwijl hij in beeld stond.
    #
    # Dat maakte de weergave dubbelzinnig op de ergst mogelijke manier: geen
    # blauw betekende niet "niet gescoord" maar "misschien wel, misschien niet".
    # In een controle-instrument moet de afwezigheid van een markering
    # betekenen dat er niets gescoord is.
    if all_events:
        for oe in all_events:
            try:
                oe_onset = float(oe.get("onset_s"))
                oe_dur = float(oe.get("duration_s") or 0.0)
            except (TypeError, ValueError):
                continue
            oe_end = oe_onset + oe_dur
            if oe_end <= t_start or oe_onset >= t_end:      # geen overlap
                continue
            if abs(oe_onset - onset) < 1.0:                 # het event zelf
                continue
            oe_type = str(oe.get("type", "")).lower()
            if "fri" in oe_type or "rejected" in oe_type:
                continue
            lo, hi = max(oe_onset, t_start), min(oe_end, t_end)
            for ax_j in axes:
                ax_j.axvspan(lo, hi, color="#3182CE", alpha=0.15, zorder=0)
                # Alleen een grenslijn waar de grens ECHT ligt. Een lijn op de
                # afgeknipte rand zou een begin of einde suggereren dat er niet
                # is, en dan lijkt een doorlopend event een kort event.
                if oe_onset >= t_start:
                    ax_j.axvline(oe_onset, color="#3182CE", linewidth=0.4, alpha=0.5)
                if oe_end <= t_end:
                    ax_j.axvline(oe_end, color="#3182CE", linewidth=0.4, alpha=0.5)

    # ── Per-channel data + red primary event marking ──────────
    for i, (ch_type, ch_name, label, color) in enumerate(ch_to_plot):
        ax = axes[i]
        ax.set_facecolor("white")
        try:
            data = raw.get_data(picks=[ch_name])[0][s_start:s_end]
        except Exception:
            data = np.zeros(s_end - s_start)

        # Detection channel: thicker line
        lw = 0.9 if ch_type == _det_ch_type else 0.5

        # SpO2: vaste y-as
        if ch_type == "spo2":
            ax.plot(times, data, color=color, linewidth=lw)
            valid = data[(data >= 50) & (data <= 100)]
            if len(valid) > 0:
                ax.set_ylim(max(50, np.min(valid) - 3), min(102, np.max(valid) + 2))
            ax.axhline(90, color="#e74c3c", linewidth=0.4, linestyle="--", alpha=0.5)
        else:
            ax.plot(times, data, color=color, linewidth=lw)
            # Schaal op de REFERENTIE-ademhaling buiten het event, niet op het
            # hele venster.
            #
            # De vorige regel was median ± 4·MAD over het volledige venster.
            # Een respiratoir event is per definitie een stille periode, dus
            # hoe overtuigender het event, hoe kleiner de MAD en hoe strakker
            # de schaal — precies omgekeerd aan wat de lezer nodig heeft. Op
            # een echte gemengde apneu (SN3, t=436 s) bleef van het
            # flowkanaal een streep over en stond Abdomen op 20–40 terwijl de
            # werkelijke excursies een veelvoud daarvan zijn. Je kunt de
            # reductie niet beoordelen als juist de ademhaling waartegen je
            # vergelijkt buiten beeld valt.
            if len(data) > 10:
                ev_mask = (times >= onset) & (times <= onset + dur)
                ref = data[~ev_mask]
                basis = ref if len(ref) > 10 else data
                lo, hi = np.percentile(basis, [1, 99])
                if hi <= lo:                       # vlak referentiesignaal
                    lo, hi = float(np.min(basis)), float(np.max(basis))
                # Het event zelf moet in beeld blijven, ook wanneer het buiten
                # de referentie valt — denk aan de drukpiek bij heropening.
                if ev_mask.any():
                    ev_data = data[ev_mask]
                    lo = min(lo, float(np.percentile(ev_data, 1)))
                    hi = max(hi, float(np.percentile(ev_data, 99)))
                if hi <= lo:                       # volledig vlak kanaal
                    lo, hi = lo - 1.0, hi + 1.0
                margin = (hi - lo) * 0.08
                ax.set_ylim(lo - margin, hi + margin)

        # Primary event (red)
        ax.axvspan(onset, onset + dur, color="#e74c3c", alpha=0.12, zorder=0)
        ax.axvline(onset, color="#e74c3c", linewidth=0.5, alpha=0.6)
        ax.axvline(onset + dur, color="#e74c3c", linewidth=0.5, alpha=0.6)

        # Detection channel marker in ylabel
        det_marker = " ◀" if ch_type == _det_ch_type else ""
        ax.set_ylabel(f"{label}{det_marker}", fontsize=5.5, color="#4a5568", rotation=0,
                      labelpad=30, ha="right", va="center")
        ax.tick_params(axis="y", labelsize=4.5, length=2, width=0.3)
        ax.tick_params(axis="x", labelsize=5, length=2, width=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines["left"].set_linewidth(0.3)
        ax.spines["bottom"].set_linewidth(0.3)

        if i < n_ch - 1:
            ax.tick_params(axis="x", labelbottom=False)

    # X-as label op onderste paneel
    axes[-1].set_xlabel("Tijd (s)", fontsize=5.5, color="#6b7a99")
    # Tijdstip in de nacht (uren:minuten)
    onset_hm = f"{int(onset//3600):02d}:{int((onset%3600)//60):02d}:{int(onset%60):02d}"

    # Event type + stage label
    ev_type = event.get("type", "?").upper()
    ev_dur  = f"{dur:.0f}s"
    ev_desat = ""
    if event.get("desaturation_pct"):
        ev_desat = f", desat {event['desaturation_pct']:.1f}%"
    ev_conf = ""
    if event.get("confidence"):
        ev_conf = f", conf {event['confidence']:.2f}"
    stage = ""
    if hypno:
        ep_idx = int(onset / 30)
        if 0 <= ep_idx < len(hypno):
            stage = f" [{hypno[ep_idx]}]"

    # Detection channel label for title
    _det_label = ""
    if _det_ch_type:
        for ct, cn, lb, _ in ch_to_plot:
            if ct == _det_ch_type:
                _det_label = f" [{lb}]"
                break

    title = f"{ev_type}{_det_label} — {ev_dur}{ev_desat}{ev_conf}{stage} — t={onset_hm}"
    fig.suptitle(title, fontsize=6.5, color="#1a3a5c", fontweight="bold", y=0.99)

    plt.tight_layout(pad=0.3)
    fig.subplots_adjust(top=0.94, hspace=0.15)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf, total_hc


def _plot_epoch_example(edf_path, channel_map, event, hypno=None,
                        pre_s=15, post_s=30, wc=16.2, hc_per_ch=1.2,
                        all_events=None, raw=None):
    """PDF-verpakking rond `epoch_panel_png`.

    De tekencode is gedeeld met de visuele eventcontrole in de webapp
    (`event_review.py`), die PNG-bytes nodig heeft in plaats van een
    ReportLab-object. Splitsen in plaats van dupliceren, zodat een verbetering
    aan het paneel op beide plekken landt.
    """
    out = epoch_panel_png(edf_path, channel_map, event, hypno=hypno,
                          pre_s=pre_s, post_s=post_s, wc=wc,
                          hc_per_ch=hc_per_ch, all_events=all_events, raw=raw)
    if out is None:
        return None
    buf, total_hc = out
    return Image(buf, width=wc*cm, height=total_hc*cm)


def load_panel_raw(edf_path, channel_map):
    """Lees de EDF ÉÉN keer en houd alleen de kanalen die de panelen tekenen.

    Dit is de dominante kostenpost, niet het tekenen: op een nacht van 6,6 uur
    kost de header 1,0 s en het laden van vier kanalen 5,1 s, goed voor 194 MB
    — tegenover 0,18 s per paneel. Eén lezing voor de hele set is daarom geen
    optimalisatie maar een ontwerpvoorwaarde; per-paneel herlezen maakt elke
    weergave van twintig events een zaak van twee minuten.

    Volledig laden, niet croppen: bij gemengde samplefrequenties verandert een
    partiële lezing de waarden van de trager bemonsterde kanalen.

    Geeft None terug wanneer het bestand onleesbaar is of geen enkel gevraagd
    kanaal bevat — de aanroeper valt dan terug op per-event laden.
    """
    try:
        import mne
        mne.set_log_level("ERROR")
        raw = read_raw_signal(edf_path, preload=False, verbose=False)
        available = raw.ch_names
        # dict.fromkeys: ontdubbelen met behoud van volgorde. Meerdere rollen
        # kunnen naar hetzelfde kanaal wijzen — op een montage met één
        # druksensor zijn `flow` en `flow_pressure` allebei "Pressure Flow" —
        # en `raw.pick()` weigert zo'n lijst met
        # "Found 6 / 7 unique names, sel is not unique".
        need = list(dict.fromkeys(
            channel_map[t] for t, _, _ in _EPOCH_CH_ORDER
            if channel_map.get(t) and channel_map.get(t) in available))
        if not need:
            logger.warning("signaalpanelen: geen van de gevraagde kanalen "
                           "staat in de EDF (%d kanalen beschikbaar)",
                           len(available))
            return None
        raw.pick(need)
        raw.load_data()
        return raw
    except Exception:
        # Niet stilzwijgend None: deze terugval maakte een pick-fout
        # onzichtbaar en de weergave meldde alleen "geen enkel paneel kon
        # getekend worden", zonder de reden.
        logger.exception("signaalpanelen: EDF laden mislukt (%s)",
                         os.path.basename(str(edf_path)))
        return None


def _build_epoch_examples(results, wc=16.2):
    """Bouw epoch-voorbeeld Image objecten voor het PDF-rapport.

    Returns list of (event_dict, Image) tuples, max 3.
    """
    edf_path = results.get("edf_path")
    if not edf_path or not os.path.exists(str(edf_path)):
        return []

    pneumo = results.get("pneumo", {})
    resp   = pneumo.get("respiratory", {})
    events = resp.get("events", [])
    if not events:
        return []

    # Kanaalmap: probeer pneumo_channels, dan meta.channels_used
    ch_map = results.get("pneumo_channels", {})
    if not ch_map:
        ch_map = pneumo.get("meta", {}).get("channels_used", {})
    if not ch_map:
        return []

    # Hypnogram voor stage-labels
    hypno = None
    timeline = results.get("timeline")
    if timeline:
        hypno = [ep.get("stage", "W") for ep in timeline]

    picks = _select_example_events(events, n=3)
    if not picks:
        return []

    # perf: read + load the EDF ONCE for all example events (only the channels
    # the plots need), then reuse it. Previously each _plot_epoch_example
    # re-read the full EDF — ~3x the load cost. Byte-identical (same channels,
    # same sfreq, same full load_data). Falls back to per-event loading.
    shared_raw = load_panel_raw(edf_path, ch_map)

    images = []
    for ev in picks:
        try:
            img = _plot_epoch_example(edf_path, ch_map, ev, hypno=hypno,
                                       pre_s=15, post_s=30, wc=wc,
                                       all_events=events, raw=shared_raw)
            if img:
                images.append((ev, img))
        except Exception:
            continue
    return images


# ══════════════════════════════════════════════════════════════
# HOOFD FUNCTIE
# ══════════════════════════════════════════════════════════════
def generate_pdf_report(results:dict, output_path:str,
                        site_config:dict=None, lang:str=None) -> str:
    site=_load_site(site_config)
    styles=_styles()

    # v0.8.11: taal bepalen
    if not lang:
        lang = (results.get("patient_info", {}).get("lang")
                or site.get("language", "en"))
    # De eenheid van een index per uur, in de taal van het rapport. Stond
    # hardgecodeerd als "/u" -- ook in Engelse rapporten.
    _UH = t("unit_per_hour", lang)

    # v0.8.11: patient_info kan custom header/logo bevatten (via rapport editor)
    pat_hdr = results.get("patient_info", {})
    if pat_hdr.get("report_header_name"):
        site["name"] = pat_hdr["report_header_name"]
    if pat_hdr.get("report_header_address"):
        site["address"] = pat_hdr["report_header_address"]
    if pat_hdr.get("report_header_phone"):
        site["phone"] = pat_hdr["report_header_phone"]
    if pat_hdr.get("report_logo_path"):
        logo_candidate = os.path.join(os.path.dirname(__file__), "static", "logos",
                                       pat_hdr["report_logo_path"])
        if os.path.exists(logo_candidate):
            site["logo_path"] = logo_candidate

    on1,onN=_callbacks(site, lang=lang)

    doc=SimpleDocTemplate(output_path,pagesize=A4,
        leftMargin=ML,rightMargin=MR,
        topMargin=MT+1.2*cm,bottomMargin=MB+0.6*cm)

    meta  =results.get("meta",{})
    stats =results.get("sleep_statistics",{}).get("stats",{})
    pat   =results.get("patient_info",{})
    pneumo=results.get("pneumo",{})
    rsum  =pneumo.get("respiratory",{}).get("summary",{})

    # v0.8.22: Als manuele velden leeg zijn, vul aan met EDF-header data
    edf_pat = pneumo.get("meta", {}).get("patient_info", {}) or {}
    if edf_pat:
        # v0.8.22: EDF-naam heeft voorrang als formulier-naam ontbreekt
        # OF als formulier-naam puur numeriek is (= patiëntcode, niet naam)
        form_name = (pat.get("patient_name") or "").strip()
        edf_name = (edf_pat.get("name") or "").strip()
        name_is_code = form_name.isdigit() or form_name == edf_pat.get("patient_code")
        if edf_name and (not form_name or name_is_code):
            parts = edf_name.split()
            if len(parts) >= 2:
                pat["patient_name"] = parts[0]
                pat["patient_firstname"] = " ".join(parts[1:])
            else:
                pat["patient_name"] = edf_name
        if edf_pat.get("sex"):
            form_sex = (pat.get("sex") or "").strip()
            if not form_sex or form_sex == "—":
                pat["sex"] = {"M": "Man", "F": "Vrouw"}.get(edf_pat["sex"], edf_pat["sex"])
        if edf_pat.get("birthdate"):
            form_dob = (pat.get("dob") or "").strip()
            if not form_dob or form_dob == "—":
                pat["dob"] = edf_pat["birthdate"][:10]
        if edf_pat.get("patient_code"):
            form_id = (pat.get("patient_id") or "").strip()
            if not form_id or form_id == "—":
                pat["patient_id"] = edf_pat["patient_code"]

    story=[]; sp=lambda n=0.25:story.append(Spacer(1,n*cm))

    # ── TITEL (v0.8.22: studietype-afhankelijk) ──────────────────
    study_type = results.get("study_type", "diagnostic_psg")
    # Eén gedeelde regel: `"_pg_" in study_type` miste `diagnostic_pg` en zou
    # daar een AHI-label boven een REI-getal zetten. Zie study_type.py.
    from study_type import is_polygraphy as _is_pg
    from study_type import is_titration as _is_titr
    is_titration = _is_titr(study_type)
    # `results["is_polygraphy"]` draagt wat er werkelijk gedraaid heeft: de
    # analyse merkt een montage zonder EEG zelf op, ook als het studietype op
    # PSG bleef staan. Het label moet die werkelijkheid volgen, anders staat er
    # "AHI" boven een getal dat over registratietijd gaat.
    is_polygraphy = bool(results.get("is_polygraphy")) or _is_pg(study_type)
    therapy_label = ""
    if study_type == "titration_psg_cpap":
        title_txt = t("pdf_titration_cpap", lang)
        therapy_label = "CPAP"
    elif study_type == "titration_pg_cpap":
        title_txt = t("pdf_titration_cpap", lang)
        therapy_label = "CPAP"
    elif study_type == "titration_pg_mra":
        title_txt = t("pdf_titration_mra", lang)
        therapy_label = "MRA"
    elif is_polygraphy:
        # Er stond "Polysomnografie" boven een polygrafierapport — een
        # onderzoek zonder EEG. Precies het soort etiket dat dit hele blok
        # rechtzet, dus het hoort de werkelijkheid te volgen: de titel komt uit
        # wat er gedraaid heeft, niet uit een vergeten keuzelijst.
        title_txt = t("pdf_title_pg", lang)
    else:
        title_txt = t("pdf_title_psg", lang)

    sp(0.1)
    story.append(Paragraph(title_txt, styles["T"]))
    _sp_label = pneumo.get("meta", {}).get("scoring_label", "Standard (AASM)")
    story.append(Paragraph(f"AASM-scoring via YASA  ·  {site.get('name','SleepAI')}  ·  {_sp_label}",styles["ST"]))
    story.append(HRFlowable(width="100%",thickness=1.2,color=NAVY,spaceAfter=6))

    # ── PATIËNTGEGEVENS ────────────────────────────────────────
    pname =(pat.get("patient_name","") or "").strip()
    pfirst=(pat.get("patient_firstname","") or "").strip()
    full  =f"{pname}, {pfirst}".strip(", ") or "—"
    dob   =str(pat.get("dob","—") or "—")
    age_s ="—"
    try:
        parts=dob.replace("/","-").split("-")
        if len(parts)==3:
            y,m,d_=(int(p) for p in parts)
            _today=date.today(); age_s=f"{_today.year-y-((_today.month,_today.day)<(m,d_))} {t('pdf_year',lang)}"
    except: pass

    def _pm(rows):
        data=[[Paragraph(f"<b>{r[0]}</b>",ParagraphStyle("PL",fontName="Helvetica-Bold",
                fontSize=7.5,textColor=GR,leading=10)),
               Paragraph(r[1],ParagraphStyle("PV",fontName="Helvetica",
                fontSize=8,textColor=TXT,leading=10))] for r in rows]
        t=Table(data,colWidths=[3.2*cm,5.1*cm])
        t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),1.5),
            ("BOTTOMPADDING",(0,0),(-1,-1),1.5),("LEFTPADDING",(0,0),(-1,-1),0)])); return t

    left_rows=[[t("pdf_name",lang),full],[t("pdf_dob",lang),dob],[t("pdf_age",lang),age_s],
               [t("pdf_sex",lang),str(pat.get("sex","—") or "—")],[t("pdf_bmi",lang),str(pat.get("bmi","—") or "—")],
               [t("pdf_indication",lang),str(pat.get("indication","—") or "—")]]
    _ess_raw = pat.get("ess")
    _ess_str = f"{_ess_raw}/24" if _ess_raw not in (None, "", "—") else "—"
    right_rows=[[t("pdf_patient_id",lang),str(pat.get("patient_id","—") or "—")],
                # "Opnamedatum" toonde `analysis_timestamp` — de datum waarop
                # de ANALYSE draaide. Twee runs van dezelfde nacht kregen
                # daardoor twee verschillende "opnamedatums", en een heranalyse
                # verzette de datum van een onderzoek dat maanden eerder
                # plaatsvond. De echte opnamestart staat in `recording_start`.
                [t("pdf_rec_date",lang), _recording_date(meta)],
                [t("pdf_duration",lang),_v(meta,"duration_min",fmt="{:.0f}")+" min"],
                [t("pdf_scorer",lang),str(pat.get("scorer","—") or "—")],
                [t("pdf_institution",lang),str(pat.get("institution",site.get("name","")) or "")],
                ["ESS", _ess_str],
                [t("pdf_referring",lang),str(pat.get("referring_physician","—") or "—")]]

    pt=Table([[_pm(left_rows),_pm(right_rows)]],colWidths=[CW/2,CW/2])
    pt.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,GRID),
        ("BACKGROUND",(0,0),(-1,-1),BGROW),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8)]))
    story.append(pt); sp(0.15)

    # ── KPI-BALK ───────────────────────────────────────────────
    ahi_v=_f(rsum,"ahi_total"); ahi_s=f"{ahi_v:.1f}" if ahi_v is not None else "—"
    # v0.8.22: Label afhankelijk van studietype
    # v0.8.43: syndroom-label dynamisch op basis van apnoe-type distributie
    # v0.15.0 fix: the results dict has no top-level "respiratory" key (respiratory
    # lives under results["pneumo"]), so this used to resolve to {} — making the KPI
    # syndrome label fall back to generic "SAS" and hiding the apnea-breakdown line.
    # Point it at the canonical summary instead.
    _rsum_for_sev = rsum or (results.get("respiratory") or {}).get("summary") or {}
    if is_polygraphy:
        ahi_label = f"REI  ({_sev_with_syndrome(ahi_v, _rsum_for_sev, lang)})"
    elif is_titration:
        ahi_label = f"{t('pdf_residual',lang)} AHI  ({_sev_with_syndrome(ahi_v, _rsum_for_sev, lang)})"
    else:
        ahi_label = f"AHI  ({_sev_with_syndrome(ahi_v, _rsum_for_sev, lang)})"

    # ── Split-night: het DIAGNOSTISCHE deel is de kop-KPI ──────────────
    #
    # Bij een split-night telt de nacht-AHI diagnostiek én titratie samen en
    # verdunt daarmee precies wat er gediagnosticeerd moet worden: op de casus
    # die dit aanleiding gaf 10,1/u over de nacht tegen 44,7/u (127,1 met de
    # ongetypeerde apneus erbij) in het diagnostische deel — een factor vier.
    #
    # De nacht-AHI verdwijnt niet: hij komt als tweede tegel te staan, want
    # AASM schrijft hem voor. Maar de eerste tegel — die de ernstklasse en de
    # kleur draagt — hoort het deel te tonen waarop de diagnose rust.
    _split_kpi = None
    try:
        _sn_k = ((results.get("pneumo") or {}).get("split_night") or {})
        _sum_k = (_sn_k.get("summaries") or {}).get("diagnostic") or {}
        _seg_k = (_sn_k.get("segments") or {}).get("diagnostic") or {}
        if _sn_k.get("detected") and _sum_k and _seg_k.get("reliable"):
            # Boven een vijfde ongetypeerd is `ahi_total` een onvolledige
            # telling en zegt alleen `ahi_incl_uncertain` iets.
            _onzeker = _seg_k.get("uncertain_fraction") or 0
            _dv = (_sum_k.get("ahi_incl_uncertain") if _onzeker >= 0.20
                   else _sum_k.get("ahi_total"))
            if _dv is not None:
                # De AHI onder therapie hoort ernaast: dat is wat de
                # titratie heeft opgeleverd, en zonder dat getal zegt het
                # diagnostische deel niets over het effect.
                _sum_t = (_sn_k.get("summaries") or {}).get("therapeutic") or {}
                _seg_t = (_sn_k.get("segments") or {}).get("therapeutic") or {}
                _onz_t = _seg_t.get("uncertain_fraction") or 0
                _tv_k = (_sum_t.get("ahi_incl_uncertain") if _onz_t >= 0.20
                         else _sum_t.get("ahi_total"))
                _split_kpi = {
                    "waarde": _dv,
                    "label": (f"{t('pdf_kpi_ahi_no_cpap', lang)}  "
                              f"({_sev(_dv, lang)})"),
                    "slaap_min": (_seg_k.get("sleep_h") or 0) * 60,
                    "therapie": _tv_k,
                }
    except (TypeError, ValueError, AttributeError):
        _split_kpi = None
    # TST, slaapefficiëntie, inslaaplatentie en WASO zijn allemaal
    # staging-uitkomsten. Zonder EEG bestaan ze niet, en ze tonen ze op grond
    # van een hypnogram uit een drukcurve is geen benadering maar een
    # verzinsel: op de opname die dit aan het licht bracht stond daar
    # TST 390 min en SE 72,3 %. Bij polygrafie komt in plaats daarvan de
    # registratietijd te staan, want dat is de noemer van de REI.
    if is_polygraphy:
        _rec_min = meta.get("duration_min")
        _den_h = ((results.get("pneumo") or {}).get("respiratory") or {}) \
            .get("summary", {}).get("index_denominator_h")
        story.append(_kpi([
            (ahi_s, ahi_label, _UH, _sev_clr(ahi_v) if ahi_v else GR),
            (f"{_rec_min:.0f}" if isinstance(_rec_min, (int, float)) else "—",
             t("pdf_rec_time", lang), "min", NAVY),
            (f"{_den_h:.1f}" if isinstance(_den_h, (int, float)) else "—",
             t("pdf_rei_denominator", lang), "u", NAVY),
        ])); sp(0.15)
    else:
        if _split_kpi:
            _dw = _split_kpi["waarde"]
            story.append(_kpi([
                (f"{_dw:.1f}", _split_kpi["label"], "{_UH}", _sev_clr(_dw)),
                (f"{_split_kpi['therapie']:.1f}"
                 if _split_kpi.get("therapie") is not None else "—",
                 t("pdf_kpi_ahi_cpap", lang), _UH,
                 _sev_clr(_split_kpi["therapie"])
                 if _split_kpi.get("therapie") is not None else GR),
                (f"{_split_kpi['slaap_min']:.0f}",
                 t("pdf_kpi_sleep_diag", lang), "min", NAVY),
                (_v(stats, "TST", fmt="{:.0f}"), "TST", "min", NAVY),
                (_v(stats, "SE", fmt="{:.1f}"), t("pdf_se", lang), "%", NAVY),
            ])); sp(0.15)
        else:
            story.append(_kpi([
                (ahi_s, ahi_label, _UH, _sev_clr(ahi_v) if ahi_v else GR),
                (_v(stats,"TST",fmt="{:.0f}"),  "TST", "min", NAVY),
                (_v(stats,"SE",fmt="{:.1f}"),   t("pdf_se",lang),  "%",   NAVY),
                (_v(stats,"SOL",fmt="{:.0f}"),  t("pdf_sol",lang),    "min", NAVY),
                (_v(stats,"WASO",fmt="{:.0f}"), "WASO",                   "min", NAVY),
            ])); sp(0.15)

    # v0.8.43: Apnoe-type breakdown regel (dominante type + percentages)
    from reportlab.lib.styles import ParagraphStyle as _PS_v0843
    _apnea_line = _apnea_breakdown_line(_rsum_for_sev, lang)
    if _apnea_line:
        _apnea_style = _PS_v0843(
            "ApneaBreakdown_v0843",
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6b7a99"),
            alignment=1,
            spaceAfter=2,
        )
        story.append(Paragraph(_apnea_line, _apnea_style))
        sp(0.1)

    # ── v0.15.0 (B4): page-1 clinical phenotype summary (POSA / REM-predominant) ──
    # (Signal-quality/confidence banners and the strict/std/sensitive AHI-robustness
    #  banner were removed from the PDF in v0.15.0 — see CHANGES.md.)
    _p1_pheno = _phenotype_summary_line(rsum, lang)
    if _p1_pheno:
        story.append(Paragraph(_p1_pheno, ParagraphStyle(
            "P1Pheno", fontName="Helvetica", fontSize=8,
            textColor=colors.HexColor("#1a3a5c"), alignment=TA_CENTER,
            leading=11, spaceBefore=1, spaceAfter=1)))
        sp(0.06)

    # ── v0.15.0 (B5): page-1 "Aandachtspunten" box (descriptive — not advice) ──
    _p1_flags = _clinical_flags(
        rsum, pneumo,
        pneumo.get("spo2", {}).get("summary", {}),
        pneumo.get("arousal", {}).get("summary", {}), lang,
        warnings=results.get("analysis_warnings"))
    if _p1_flags:
        _fl_hdr = ParagraphStyle("FlagHdr", fontName="Helvetica-Bold", fontSize=7.5,
                                 textColor=colors.HexColor("#7a5c00"), leading=10)
        _fl_body = ParagraphStyle("FlagBody", fontName="Helvetica", fontSize=7.5,
                                  textColor=colors.HexColor("#5c4600"), leading=10,
                                  leftIndent=6)
        _fl_cells = [[Paragraph(t("pdf_flags_hdr", lang), _fl_hdr)]]
        for _f_ln in _p1_flags:
            _fl_cells.append([Paragraph("• " + _f_ln, _fl_body)])
        _fl_tbl = Table(_fl_cells, colWidths=[CW])
        _fl_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8e1")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0c060")),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(_fl_tbl)
        sp(0.08)

    # ══════════════════════════════════════════════════════════════
    # OVERZICHTSPAGINA (v0.8.22) — patiënt + kanalen + visueel
    # ══════════════════════════════════════════════════════════════

    # ── Patient info from EDF: equipment/technician in header (v0.8.22) ──
    # Name, sex, DOB, patient_code already merged into header above.
    # Only show equipment/technician as extra line if present.
    _edf_extras = []
    _edf_p = pneumo.get("meta", {}).get("patient_info", {}) or {}
    if _edf_p.get("equipment"):
        _edf_extras.append(f"{t('pdf_equipment',lang)}: {_edf_p['equipment']}")
    if _edf_p.get("technician"):
        _edf_extras.append(f"{t('pdf_technician',lang)}: {_edf_p['technician']}")
    if _edf_p.get("recording_date"):
        _edf_extras.append(f"{t('pdf_recording_date',lang)}: {_edf_p['recording_date']}")
    if _edf_extras:
        story.append(Paragraph(
            "<i>" + "  ·  ".join(_edf_extras) + "</i>",
            styles["SM"])); sp(0.1)

    # ── 0a. Registratie: kanalen in EDF ────────────────────────
    all_ch = pneumo.get("meta", {}).get("all_channels", [])
    if all_ch:
        story.append(_hdr(t("rpt_sec0a", lang))); sp(0.1)
        # Groepeer kanalen in rijen van 4, geen header, klein lettertype
        ch_rows = []
        for i in range(0, len(all_ch), 4):
            row = all_ch[i:i+4]
            while len(row) < 4:
                row.append("")
            ch_rows.append(row)
        ch_style = ParagraphStyle("CH", fontName="Helvetica", fontSize=7,
                                   textColor=colors.HexColor("#4a5568"), leading=9)
        ch_data = [[Paragraph(c, ch_style) for c in row] for row in ch_rows]
        ch_tbl = Table(ch_data, colWidths=[4.25*cm]*4)
        ch_tbl.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(ch_tbl); sp(0.1)
        story.append(Paragraph(
            f"<i>{len(all_ch)} {t('pdf_ch_total', lang)}</i>",
            styles["SM"])); sp(0.1)

    # ── 0a-bis. Herkomst: welk kanaal voedde welke analyse ─────
    # Direct onder de kanaallijst, want dat is waar de lezer de vraag stelt.
    try:
        _prov = provenance_rows(results, lang)
        if _prov:
            story.append(_hdr(t("rpt_sec_provenance", lang))); sp(0.1)
            story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)],
                              _prov, [8, 9], stripe=True)); sp(0.1)
            story.append(Paragraph(t("prov_note", lang), styles["SM"])); sp(0.15)
    except Exception:
        pass

    # ── 0b. Visueel overzicht ─────────────────────────────────
    story.append(_hdr(t("rpt_sec0b", lang))); sp(0.1)

    # Bereken gedeelde tijdsduur (uren) voor alle grafieken
    timeline = results.get("hypnogram_timeline", {}).get("timeline", [])
    n_epochs = len(timeline) if timeline else 0
    dur_h = n_epochs * 30 / 3600 if n_epochs > 0 else float(meta.get("duration_min", 480)) / 60

    # Split-night: waar begint het tweede deel? Elk paneel hieronder krijgt
    # dezelfde markering, zodat de saturatiecurve en de stadia niet los van
    # elkaar gelezen worden -- een SpO2 die halverwege herstelt is anders niet
    # te onderscheiden van een patiënt die vanzelf beter wordt.
    _ov_split_h, _ov_split_lbl = None, None
    try:
        _sn_ov = ((results.get("pneumo") or {}).get("split_night")
                  or results.get("split_night") or {})
        if _sn_ov.get("detected") and _sn_ov.get("breakpoint_s") is not None:
            _ov_split_h = float(_sn_ov["breakpoint_s"]) / 3600.0
            _ov_split_lbl = t("pdf_split_marker", lang)
    except (TypeError, ValueError):
        _ov_split_h, _ov_split_lbl = None, None

    # Hypnogram — niet bij polygrafie.
    #
    # Zonder EEG bestaat er geen hypnogram. Wat er stond was gescoord op een
    # drukcurve: 11 slaapcycli, REM-latentie 6 minuten, 118 minuten REM. Dat is
    # geen zwak hypnogram maar een betekenisloos hypnogram, en een grafiek die
    # er wel uitziet als een hypnogram nodigt uit om hem te lezen.
    if timeline and not is_polygraphy:
        story.append(Paragraph("<b>HYPNO</b>", styles["SM"]))
        try:
            story.append(_hypno_ov(timeline, dur_h, hc=2.2, lang=lang,
                                       split_h=_ov_split_h, split_label=_ov_split_lbl))
            leg = "  ".join(f'<font color="{STAGE_CLR[s]}">■</font> {s}'
                            for s in ["W","N1","N2","N3","R"])
            story.append(Paragraph(leg, styles["SM"]))
        except: pass
        sp(0.1)

    # Events timeline (OA/CA/MA/HYP/FR — altijd alle rijen)
    resp_events = pneumo.get("respiratory", {}).get("events", [])
    rejected_hyps = pneumo.get("respiratory", {}).get("rejected_hypopneas", [])
    if (resp_events or rejected_hyps) and dur_h > 0:
        story.append(Paragraph("<b>EVENT</b>", styles["SM"]))
        try: story.append(_events_ov(resp_events, dur_h, rejected_hyps=rejected_hyps,
                                        split_h=_ov_split_h, split_label=_ov_split_lbl))
        except: pass
        sp(0.1)

    # Positie
    pos_data = pneumo.get("position", {})
    pos_epochs = pos_data.get("pos_per_epoch", [])
    if pos_epochs:
        story.append(Paragraph("<b>POS</b>", styles["SM"]))
        try: story.append(_pos_ov(pos_epochs, dur_h, hc=1.6, lang=lang,
                                     split_h=_ov_split_h, split_label=_ov_split_lbl))
        except: pass
        sp(0.1)

    # Snurk (PHONO)
    snore_rms = pneumo.get("snore", {}).get("rms_1s", [])
    if snore_rms and len(snore_rms) > 60:
        story.append(Paragraph("<b>PHONO</b>", styles["SM"]))
        try: story.append(_snore_ov(snore_rms, dur_h, hc=1.4,
                                       split_h=_ov_split_h, split_label=_ov_split_lbl))
        except: pass
        sp(0.1)

    # SpO2
    spo2_ts = pneumo.get("spo2", {}).get("timeseries")
    if spo2_ts and len(spo2_ts) > 10:
        story.append(Paragraph("<b>SpO2</b>", styles["SM"]))
        try: story.append(_spo2_ov(spo2_ts, dur_h, hc=1.6,
                                      split_h=_ov_split_h, split_label=_ov_split_lbl))
        except: pass
        sp(0.1)

    # ── Legende visueel overzicht ──────────────────────────────
    sp(0.1)
    leg_parts = [
        '<font size="6" color="#6b7a99"><b>EVENT:</b></font>',
        f'<font size="6" color="#e74c3c">■</font><font size="6" color="#6b7a99"> {t("pdf_leg_oa", lang)}</font>',
        f'<font size="6" color="#3498db">■</font><font size="6" color="#6b7a99"> {t("pdf_leg_ca", lang)}</font>',
        f'<font size="6" color="#9b59b6">■</font><font size="6" color="#6b7a99"> {t("pdf_leg_ma", lang)}</font>',
        f'<font size="6" color="#e67e22">■</font><font size="6" color="#6b7a99"> {t("pdf_leg_hyp", lang)}</font>',
        f'<font size="6" color="#95a5a6">■</font><font size="6" color="#6b7a99"> {t("pdf_leg_fr", lang)}</font>',
        '&nbsp;&nbsp;',
        '<font size="6" color="#6b7a99"><b>SpO2:</b></font>',
        f'<font size="6" color="#e74c3c">---</font><font size="6" color="#6b7a99"> {t("pdf_leg_spo2_thr", lang)}</font>',
        f'<font size="6" color="#e74c3c">■</font><font size="6" color="#6b7a99"> {t("pdf_leg_spo2_zone", lang)}</font>',
        '&nbsp;&nbsp;',
        '<font size="6" color="#6b7a99"><b>PHONO:</b></font>',
        f'<font size="6" color="#e67e22">---</font><font size="6" color="#6b7a99"> {t("pdf_leg_phono_thr", lang)}</font>',
    ]
    story.append(Paragraph("  ".join(leg_parts), styles["SM"]))
    # v0.8.22: Positie-legende
    pos_leg = [
        '<font size="6" color="#6b7a99"><b>POS:</b></font>',
        f'<font size="6" color="#2ecc71">■</font><font size="6" color="#6b7a99"> {t("pdf_pos_buk", lang)}</font>',
        f'<font size="6" color="#3498db">■</font><font size="6" color="#6b7a99"> {t("pdf_pos_lnk", lang)}</font>',
        f'<font size="6" color="#e74c3c">■</font><font size="6" color="#6b7a99"> {t("pdf_pos_rug", lang)}</font>',
        f'<font size="6" color="#9b59b6">■</font><font size="6" color="#6b7a99"> {t("pdf_pos_rec", lang)}</font>',
        f'<font size="6" color="#95a5a6">■</font><font size="6" color="#6b7a99"> {t("pdf_pos_sta", lang)}</font>',
    ]
    story.append(Paragraph("  ".join(pos_leg), styles["SM"]))
    sp(0.3)  # v0.9.1: vervangen PageBreak door spacer (voorkomt blanco pagina bij korte recordings)

    # ── 1. AASM SLAAPARCHITECTUUR ──────────────────────────────
    if is_polygraphy:
        story.append(_hdr(t("rpt_sec1", lang))); sp(0.1)
        story.append(Paragraph(
            f"<b>{t('pdf_no_staging',lang)}</b><br/>"
            f"<i>{t('pdf_rei',lang)}: {t('pdf_rei_explanation', lang)}</i>",
            styles["B"])); sp(0.15)
    else:
        story.append(_hdr(t("rpt_sec1", lang))); sp(0.15)
        story.append(KeepTogether([_aasm_tbl(stats, lang=lang)])); sp(0.15)

        # v0.8.37: Stage-specific sleep latencies
        _hypno = results.get("hypnogram", results.get("hypno", []))
        if _hypno and len(_hypno) > 10:
            try:
                draw_stage_latencies(story, hypno=_hypno, t=t)
            except Exception:
                pass

        # ── 1b. Stage transition matrix (v0.8.37) ────────────────────
        if timeline and len(timeline) > 10:
            _stages_order = ["W", "N1", "N2", "N3", "R"]
            _trans = {s1: {s2: 0 for s2 in _stages_order} for s1 in _stages_order}
            for i in range(len(timeline) - 1):
                s1, s2 = str(timeline[i].get("stage","")), str(timeline[i+1].get("stage",""))
                if s1 in _trans and s2 in _trans[s1]:
                    _trans[s1][s2] += 1
            _tr_rows = []
            for s1 in _stages_order:
                row = [s1] + [str(_trans[s1][s2]) if _trans[s1][s2] > 0 else "·" for s2 in _stages_order]
                _tr_rows.append(row)
            _tr_style = ParagraphStyle("TR", fontName="Helvetica", fontSize=6.5,
                                        textColor=TXT, alignment=TA_CENTER, leading=8)
            _tr_hdr_style = ParagraphStyle("TRH", fontName="Helvetica-Bold", fontSize=6.5,
                                            textColor=W, alignment=TA_CENTER, leading=8)
            _tr_header = [Paragraph("→", _tr_hdr_style)] + \
                         [Paragraph(s, _tr_hdr_style) for s in _stages_order]
            _tr_data = [[Paragraph(c, _tr_style if j > 0 else ParagraphStyle(
                "TRL", fontName="Helvetica-Bold", fontSize=6.5, textColor=NAVY, leading=8))
                for j, c in enumerate(row)] for row in _tr_rows]
            _tr_tbl = Table([_tr_header] + _tr_data,
                            colWidths=[1.2*cm] + [1.5*cm]*5)
            _tr_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), NAVY),
                ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#c0c8d4")),
                ("TOPPADDING", (0,0), (-1,-1), 1),
                ("BOTTOMPADDING", (0,0), (-1,-1), 1),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ]))
            # Highlight diagonal (staying in same stage)
            for i in range(5):
                _tr_tbl.setStyle(TableStyle([
                    ("BACKGROUND", (i+1, i+1), (i+1, i+1), colors.HexColor("#e8f5e9")),
                ]))
            story.append(Paragraph(
                f"<b>{t('pdf_transitions', lang)}</b> (n={len(timeline)-1})",
                styles["SM"]))
            story.append(_tr_tbl); sp(0.15)

    # ── 2. SLAAPCYCLI ──────────────────────────────────────────
    if not is_polygraphy:
      cyc=results.get("sleep_cycles",{})
      if cyc.get("success") and cyc.get("cycles"):
        story.append(_hdr(t("rpt_sec2", lang))); sp(0.1)
        story.append(Paragraph(f"{cyc['n_cycles']} {t('pdf_cycles_detected', lang)}",styles["B"]))
        cyc_rows=[[c["cycle"],f"{c['start_epoch']}–{c['end_epoch']}",
                   f"{c['duration_min']} min",
                   "  ".join(f"{s}:{p}%" for s,p in c["stage_distribution"].items())]
                  for c in cyc["cycles"]]
        story.append(_tbl([t("cycle",lang),t("epochs",lang),t("duration",lang),t("composition",lang)],
                          cyc_rows,[2,3,2.5,9.5])); sp(0.15)

      story.append(PageBreak())

      # ── 3. SPINDLES ────────────────────────────────────────────
      spd=results.get("spindles",{})
      story.append(_hdr(t("rpt_sec3", lang))); sp(0.1)
      if spd.get("success"):
        story.append(Paragraph(f"{spd.get('total_spindles',0)} {t('pdf_spindles_detected', lang)}",styles["B"]))
        summ=spd.get("summary",[])
        if summ:
            _skip={"Stage","stage","Channel","channel"}
            keys=[k for k in summ[0] if k not in _skip]
            rows=[[_detector_row_label(s)]+[_rnd(s.get(k)) for k in keys] for s in summ]
            story.append(_tbl([t("pdf_channel",lang)]+[k.replace("_"," ").capitalize() for k in keys],rows))
      else:
        story.append(Paragraph(f"{t('pdf_not_available', lang)}: {spd.get('error','—')}",styles["SM"]))
      sp(0.12)

      # ── 4. SLOW WAVES ──────────────────────────────────────────
      sw=results.get("slow_waves",{})
      story.append(_hdr(t("rpt_sec4", lang))); sp(0.1)
      if sw.get("success"):
        story.append(Paragraph(f"{sw.get('total_slow_waves',0)} {t('pdf_slow_waves_detected', lang)}",styles["B"]))
        summ=sw.get("summary",[])
        if summ:
            _skip={"Stage","stage","Channel","channel"}
            keys=[k for k in summ[0] if k not in _skip]
            rows=[[_detector_row_label(s)]+[_rnd(s.get(k)) for k in keys] for s in summ]
            story.append(_tbl([t("pdf_channel",lang)]+[k.replace("_"," ").capitalize() for k in keys],rows))
      else:
        story.append(Paragraph(f"{t('pdf_not_available', lang)}: {sw.get('error','—')}",styles["SM"]))
      sp(0.12)

      # ── 5. REM ─────────────────────────────────────────────────
      rem=results.get("rem",{})
      story.append(_hdr(t("rpt_sec5", lang))); sp(0.1)
      if rem.get("success"):
        rs=rem.get("summary",{})
        story.append(_kpi([
            (str(rs.get("n_rem_periods","—")),t("pdf_rem_periods",lang),"",NAVY),
            (str(rs.get("rem_duration_min","—")),t("pdf_rem_dur",lang),"min",NAVY),
            (str(rs.get("mean_rem_period_min","—")),t("pdf_mean_period",lang),"min",NAVY),
            (str(rs.get("longest_rem_period_min","—")),t("pdf_longest",lang),"min",NAVY),
        ]))
        # De vier tegels dragen twee definities: `rem_duration_min` telt
        # R-epochs, een periode is een spanne die korte onderbrekingen
        # overbrugt. Bij 8 perioden, 22,5 min REM en 3,69 min gemiddeld nodigt
        # dat uit tot vermenigvuldigen (29,5) en straft dat af. Alleen tonen
        # wanneer ze zichtbaar uiteenlopen; anders is het ruis op elk rapport.
        try:
            _n, _mean = rs.get("n_rem_periods"), rs.get("mean_rem_period_min")
            _dur = rs.get("rem_duration_min")
            if None not in (_n, _mean, _dur) and _n * _mean - _dur > 0.5:
                story.append(Paragraph(
                    f"<i>{t('pdf_rem_period_note', lang).format(gap=REM_GAP_TOLERANCE_MIN)}</i>",
                    styles["SM"]))
        except (TypeError, ValueError):
            pass
      else:
        story.append(Paragraph(f"{t('pdf_not_available', lang)}: {rem.get('error','—')}",styles["SM"]))
      sp(0.12)

      # ── 6. BANDVERMOGEN ────────────────────────────────────────
      bp=results.get("bandpower",{})
      story.append(_hdr(t("rpt_sec6", lang))); sp(0.1)
      if bp.get("success"):
        bands=["delta","theta","alpha","sigma","beta"]
        ps=bp.get("per_stage",{})
        rows=[[st]+[_rnd(bd.get(b),3) if bd.get(b) is not None else "—" for b in bands]
              for st,bd in ps.items()]
        story.append(_tbl([t("pdf_phase",lang)]+[b.capitalize() for b in bands],rows,[2.5,3,3,3,2.5,3]))
      else:
        story.append(Paragraph(f"{t('pdf_not_available', lang)}: {bp.get('error','—')}",styles["SM"]))
      sp(0.12)

      # ── 7. ARTEFACTEN ──────────────────────────────────────────
      art=results.get("artifacts",{})
      story.append(_hdr(t("rpt_sec7", lang))); sp(0.1)
      if art.get("success"):
        sa=art.get("summary",{}); pct=sa.get("artifact_percent",0)
        story.append(Paragraph(
            t("pdf_artifact_count", lang).format(
                n_art=sa.get('n_artifact_epochs',0),
                n_tot=sa.get('n_total_epochs',0),
                pct=pct),
            styles["B"]))
      else:
        story.append(Paragraph(f"{t('pdf_not_available', lang)}: {art.get('error','—')}",styles["SM"]))
      sp(0.15)
    # ── END polygraphy skip ──────────────────────────────────────

    # ── 7b. SIGNAAL KWALITEIT & CONFIDENCE ─────────────────────
    # STOND TOT NU TOE IN DODE CODE, EN DAT IS DE HELE LES
    #
    # Dit blok zat binnen `if has_sq:`, en `has_sq` staat sinds v0.15.0 HARD op
    # False: de signaalkwaliteitssectie is toen op verzoek uit het klinische
    # rapport gehaald. Het blok kon dus nooit renderen -- op een echte opname
    # met ratio 1186x en `pair_gate_suspect=True` stond er niets in het
    # rapport.
    #
    # De test die dit moest bewaken las de BRON op de aanwezigheid van
    # `pair_gate_suspect` en slaagde. Aanwezigheid is geen bereikbaarheid. De
    # vervangende test rendert een rapport en leest de PDF terug.
    # ── RIP-PAARPOORT ──────────────────────────────────────────
    # Deze stond tot v0.27.0 NERGENS in het rapport: de paarkwaliteit
    # werd alleen als badge in de webinterface getoond. Een clinicus las
    # dus "89 centrale apneus" zonder te kunnen zien dat de bilaterale
    # analyse uitstond en het onderscheid obstructief/centraal op één
    # kanaal berustte. Dat is precies de informatie die je nodig hebt om
    # de subtypering te wantrouwen.
    #
    # Lokale namen met _rip_-voorvoegsel: `_hdr` is verderop in deze
    # functie een helper, en een lokale hernoeming daarvan gaf eerder een
    # UnboundLocalError op ELK rapport (ruff F823).
    _rip_q = (results.get("pneumo") or {}).get("signal_quality") or {}
    _rip_mode = _rip_q.get("recommended_mode")
    if _rip_mode and _rip_mode != "bilateral":
        _rip_suspect = bool(_rip_q.get("pair_gate_suspect"))
        _rip_clr = "#e74c3c" if _rip_suspect else "#e67e22"
        _rip_head = (t("pdf_rip_gate_suspect", lang) if _rip_suspect
                     else t("pdf_rip_gate_single", lang))
        story.append(Paragraph(
            f"<font color='{_rip_clr}'><b>{_rip_head}</b></font>",
            styles["B"])); sp(0.04)
        _rip_lines = [
            f"{t('pdf_rip_mode', lang)}: <b>{_rip_mode}</b>"
            + (f" ({t('pdf_rip_working', lang)}: "
               f"<b>{_rip_q.get('working_channel')}</b>)"
               if _rip_q.get("working_channel") else ""),
        ]
        _rip_ratio = _rip_q.get("energy_ratio")
        if _rip_ratio:
            _rip_lines.append(f"{t('pdf_rip_ratio', lang)}: "
                              f"<b>{_rip_ratio:.0f}×</b>")
        for _w in (_rip_q.get("warnings") or [])[:3]:
            _rip_lines.append(_w)
        for _ln in _rip_lines:
            story.append(Paragraph(f"• {_ln}", styles["SM"]))
        sp(0.08)


    conf_rev = results.get("confidence_review", {})
    sig_q = results.get("signal_quality", {})
    sq_channels = sig_q.get("channels", {})
    sq_warnings = sig_q.get("montage_warnings", [])
    sq_grade = sig_q.get("overall_grade", "unknown")
    # v0.15.0: signal-quality & confidence-review section removed from the clinical
    # PDF (per site request — near-constantly graded "unusable"; kept in the web app).
    has_sq = False

    if has_sq:
        story.append(_hdr(t("rpt_sec7b", lang),color=colors.HexColor("#e67e22"))); sp(0.1)

        # Confidence review
        n_low = conf_rev.get("n_low_confidence", 0)
        pct_low = conf_rev.get("pct_low_confidence", 0)
        if n_low > 0:
            story.append(Paragraph(
                t("pdf_staging_conf_line", lang).format(
                    n_low=n_low,
                    n_tot=conf_rev.get('n_epochs',0),
                    pct=pct_low),
                styles["B"]))
            per_stage = conf_rev.get("per_stage_low", {})
            if per_stage:
                parts = [f"{k}: {v}" for k,v in sorted(per_stage.items(), key=lambda x: -x[1])]
                story.append(Paragraph(
                    t("pdf_low_conf_per_stage", lang).format(parts=', '.join(parts)),
                    styles["SM"]))
            sp(0.15)

        # v0.8.22: Signal quality per channel
        if sq_channels:
            grade_label = {"good": t("pdf_grade_good",lang), "acceptable": t("pdf_grade_acceptable",lang),
                           "poor": t("pdf_grade_poor",lang)}.get(sq_grade, sq_grade)
            grade_clr = {"good": "#27ae60", "acceptable": "#e67e22",
                         "poor": "#e74c3c"}.get(sq_grade, "#888")
            story.append(Paragraph(
                f"<b>{t('pdf_signal_quality',lang)}:</b> "
                f"<font color='{grade_clr}'><b>{grade_label}</b></font>",
                styles["B"])); sp(0.05)

            sq_rows = []
            for ch_name, ch_info in sorted(sq_channels.items()):
                g = ch_info.get("quality_grade", ch_info.get("quality", "—"))
                g_clr = {"good":"#27ae60","acceptable":"#e67e22","poor":"#e74c3c"}.get(g,"#888")
                sq_rows.append([
                    ch_name,
                    f"{ch_info.get('flat_pct', ch_info.get('flatline_pct', 0)):.1f}%",
                    f"{ch_info.get('clip_pct', ch_info.get('clipping_pct', 0)):.1f}%",
                    str(ch_info.get("n_disconnects", 0)),
                    f"<font color='{g_clr}'>{g}</font>",
                ])
            if sq_rows:
                story.append(KeepTogether([_tbl(
                    [t("pdf_channel",lang), "Flat-line", "Clipping",
                     "Disconnects", t("pdf_quality",lang)],
                    sq_rows, [4, 2.5, 2.5, 2.5, 3])]))
            sp(0.1)

        # Montage warnings
        if sq_warnings:
            story.append(Paragraph(
                f"<b><font color='#e74c3c'>{t('pdf_montage_warnings',lang)}:</font></b>",
                styles["B"]))
            for w in sq_warnings[:5]:
                story.append(Paragraph(f"  ⚠ {w}", styles["SM"]))
            sp(0.1)

        sp(0.15)

    story.append(PageBreak())

    # ── 8. RESPIRATOIR ─────────────────────────────────────────
    resp=pneumo.get("respiratory",{})
    story.append(_hdr(t("rpt_sec8", lang))); sp(0.15)
    if resp.get("success") and rsum:
        ahi   = _f(rsum, "ahi_total") or 0
        oahi  = _f(rsum, "oahi")      or 0
        oahi60 = _f(rsum, "oahi_conf60") or oahi
        oahi_all = _f(rsum, "oahi_all") or oahi
        # v0.8.43: AHI krijgt dynamisch syndroom-label; OAHI blijft 'OSA' (per definitie obstructief)
        sev   = _sev_with_syndrome(ahi, rsum, lang);  osev = _sev(oahi, lang);  clr = _sev_clr(ahi)
        # v0.8.22: Labels per studietype
        _ahi_lbl = "REI" if is_polygraphy else (f"{t('pdf_residual',lang)} AHI" if is_titration else "AHI")
        _oahi_lbl = "REI" if is_polygraphy else (f"{t('pdf_residual',lang)} OAHI" if is_titration else "OAHI")
        _therapy_note = f"  [{t('pdf_therapy',lang)}: {therapy_label}]" if is_titration else ""
        # Split-night: het ernstlabel achter de nacht-AHI classificeert een
        # gemiddelde van twee onvergelijkbare helften. Het getal blijft (AASM
        # schrijft het voor), maar niet zonder te zeggen wat eronder ligt.
        _split_diag = None
        try:
            _sn_b = (pneumo or {}).get("split_night") or {}
            _d_b = (_sn_b.get("segments") or {}).get("diagnostic") or {}
            if _sn_b.get("detected") and _d_b.get("reliable"):
                _dv_b = (_d_b.get("ahi_incl_uncertain")
                         if (_d_b.get("uncertain_fraction") or 0) >= 0.20
                         else _d_b.get("ahi"))
                if _dv_b is not None:
                    _split_diag = float(_dv_b)
        except (TypeError, ValueError):
            _split_diag = None
        cb    = rsum.get("confidence_bands") or {}
        thr   = rsum.get("oahi_thresholds")  or {}
        avg_c = rsum.get("avg_classification_confidence")
        avg_s = f"{avg_c:.2f}" if avg_c else "—"

        # ── Classificatiebalk ────────────────────────────────────────────
        _active_prof = pneumo.get("meta", {}).get("scoring_profile", "standard")
        _prof_labels = {"strict": "Strict", "standard": "Standard (AASM)", "sensitive": "Sensitive"}
        _prof_lbl = _prof_labels.get(_active_prof, _active_prof)
        _bar_txt, sev, _clr_val = _classbar(
            ahi=ahi, oahi=oahi, split_diag=_split_diag, rsum=rsum, lang=lang,
            unit=_UH, ahi_lbl=_ahi_lbl, oahi_lbl=_oahi_lbl,
            therapy_note=_therapy_note,
            prof_lbl=_prof_lbl)
        clr = _sev_clr(_clr_val)
        ab = Table([[Paragraph(
            _bar_txt,
            ParagraphStyle("AB", fontName="Helvetica-Bold", fontSize=9,
                           textColor=W, leading=12))]],
            colWidths=[CW])
        ab.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), clr),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ]))
        story.append(ab); sp(0.1)

        # ── v0.15.0 (B2): dual AHI — AASM v3 Rule 1A vs Rule 1B/CMS (4%) ──────
        _dual = rsum.get("ahi_dual") or {}
        if _dual.get("rule_1a") and _dual.get("rule_1b_4pct"):
            _1a = _dual["rule_1a"]; _1b = _dual["rule_1b_4pct"]
            # Op een split-night classificeert deze kolom een gemiddelde van
            # twee onvergelijkbare helften. Een ernstwoord tonen met eronder
            # de mededeling dat het niets betekent, is slechter dan het niet
            # tonen. De AHI's zelf blijven: de tabel vergelijkt
            # hypopneucriteria, en daarvoor zijn de nachtcijfers de juiste.
            def _dual_sev(v):
                return "—" if _split_diag is not None else _sev_with_syndrome(v, rsum, lang)
            _dual_rows = [
                [t("pdf_ahi_rule1a", lang),
                 f"{_1a.get('ahi')} {_UH}",
                 _dual_sev(_1a.get("ahi"))],
                [t("pdf_ahi_rule1b", lang),
                 f"{_1b.get('ahi')} {_UH}",
                 _dual_sev(_1b.get("ahi"))],
            ]
            story.append(KeepTogether([_tbl(
                [t("pdf_ahi_dual_hdr", lang), "AHI", t("pdf_severity", lang)],
                _dual_rows, [8, 3, 3])]))
            # Op een split-night classificeert de ernstkolom het
            # nachtgemiddelde. De tabel zelf blijft -- ze vergelijkt
            # hypopneucriteria, en daarvoor zijn de nachtcijfers de juiste --
            # maar niet zonder te zeggen waarop ze rust.
            if _split_diag is not None:
                story.append(Paragraph(
                    f"<i>{t('pdf_ahi_dual_split_note', lang).format(diag=f'{_split_diag:.1f}')}</i>",
                    ParagraphStyle("DualSplit", fontName="Helvetica", fontSize=7,
                                   textColor=colors.HexColor("#8e44ad"), leading=9,
                                   spaceAfter=2)))
            sp(0.05)

        # ── v0.15.0 (B3): AASM AHI severity reference scale ──────────────────
        story.append(Paragraph(
            f"<i>{t('pdf_ahi_ref_scale', lang)}</i>",
            ParagraphStyle("AHIRef", fontName="Helvetica", fontSize=7,
                           textColor=colors.HexColor("#6b7a99"), leading=9,
                           spaceAfter=2)))
        sp(0.08)

        # ── Hoofdtabel: events per type met confidence-kolom ────────────
        # Kolommen: Parameter | Aantal | Index /u | Hoog≥0.85 | Mat.0.60-0.84 | Grens 0.40-0.59 | Laag<0.40

        def _ev_conf(ev_type, band):
            """Aantal events van dit type in deze confidence-band."""
            lo = {"high": 0.85, "moderate": 0.60, "borderline": 0.40, "low": 0.0}
            hi = {"high": 2.00, "moderate": 0.85, "borderline": 0.60, "low": 0.40}
            return sum(
                1 for e in resp.get("events", [])
                if e.get("type") == ev_type
                and lo[band] <= (e.get("confidence") or 0) < hi[band]
            )

        def _hyp_conf(band):
            lo = {"high": 0.85, "moderate": 0.60, "borderline": 0.40, "low": 0.0}
            hi = {"high": 2.00, "moderate": 0.85, "borderline": 0.60, "low": 0.40}
            return sum(
                1 for e in resp.get("events", [])
                if "hypopnea" in (e.get("type") or "")
                and lo[band] <= (e.get("confidence") or 0) < hi[band]
            )

        n_obstr = rsum.get("n_obstructive", 0) or 0
        n_centr = rsum.get("n_central",     0) or 0
        n_mixed = rsum.get("n_mixed",       0) or 0
        n_hyp   = rsum.get("n_hypopnea",    0) or 0

        # Corroboratie: alleen tonen wanneer het dual-sensor algoritme
        # daadwerkelijk gedraaid heeft. Bij een enkele sensor zouden het drie
        # lege kolommen zijn.
        _dsa = resp.get("dual_sensor_apnea") or {}
        _show_corrob = bool(_dsa)

        def _corrob(ev_type, bucket):
            """Aantal apneus van dit type in dit corroboratievakje."""
            return sum(
                1 for e in resp.get("events", [])
                if e.get("type") == ev_type
                and (e.get("corroboration") or "") == bucket
            )

        hdr_conf = [
            t("pdf_param", lang), "n", _UH,
            "★★★\n≥0.85", "★★\n0.60–0.84",
            "~\n0.40–0.59", "?\n<0.40"
        ]
        if _show_corrob:
            hdr_conf += [t("pdf_corrob_both", lang),
                         t("pdf_corrob_therm", lang),
                         t("pdf_corrob_press", lang)]
        conf_rows = [
            [t("pdf_obstructive",lang),
             str(n_obstr), _v(rsum, "obstructive_index", fmt="{:.1f}"),
             str(_ev_conf("obstructive","high")),
             str(_ev_conf("obstructive","moderate")),
             str(_ev_conf("obstructive","borderline")),
             str(_ev_conf("obstructive","low"))]
            + ([str(_corrob("obstructive", "both")),
                str(_corrob("obstructive", "thermistor_only")),
                str(_corrob("obstructive", "pressure_only"))] if _show_corrob else []),
            [t("pdf_central",lang),
             str(n_centr), _v(rsum, "central_index", fmt="{:.1f}"),
             str(_ev_conf("central","high")),
             str(_ev_conf("central","moderate")),
             str(_ev_conf("central","borderline")),
             str(_ev_conf("central","low"))]
            + ([str(_corrob("central", "both")),
                str(_corrob("central", "thermistor_only")),
                str(_corrob("central", "pressure_only"))] if _show_corrob else []),
            [t("pdf_mixed",lang),
             str(n_mixed), _v(rsum, "mixed_index", fmt="{:.1f}"),
             str(_ev_conf("mixed","high")),
             str(_ev_conf("mixed","moderate")),
             str(_ev_conf("mixed","borderline")),
             str(_ev_conf("mixed","low"))]
            + ([str(_corrob("mixed", "both")),
                str(_corrob("mixed", "thermistor_only")),
                str(_corrob("mixed", "pressure_only"))] if _show_corrob else []),
            ["Hypopnea (Rule 1A/B)",
             str(n_hyp), _v(rsum, "hypopnea_index", fmt="{:.1f}"),
             str(_hyp_conf("high")),
             str(_hyp_conf("moderate")),
             str(_hyp_conf("borderline")),
             str(_hyp_conf("low"))] + (["", "", ""] if _show_corrob else []),
        ]
        # Hypopnee-subtypering, alleen wanneer er iets te tonen valt. In een
        # overwegend obstructief onderzoek zijn deze rijen nul en dus ruis;
        # bij een centraal beeld zijn ze juist het interessantste van de
        # tabel. De labels van psgscoring zijn hypopnea_central/_mixed.
        def _hyp_sub_conf(sub, band):
            lo = {"high": 0.85, "moderate": 0.60, "borderline": 0.40, "low": 0.0}
            hi = {"high": 2.00, "moderate": 0.85, "borderline": 0.60, "low": 0.40}
            return sum(
                1 for e in resp.get("events", [])
                if (e.get("type") or "") == f"hypopnea_{sub}"
                and lo[band] <= (e.get("confidence") or 0) < hi[band]
            )

        for _sub, _key in (("central", "pdf_hyp_sub_central"),
                           ("mixed", "pdf_hyp_sub_mixed")):
            _n = rsum.get(f"n_hypopnea_{_sub}", 0) or 0
            if not _n:
                continue
            conf_rows.append([
                # Geen ↳ of └: die glyphs zitten niet in het lettertype en
                # ReportLab zet er een zwart blokje voor in de plaats — dat
                # botst met ■, dat in dit rapport de legenda-kleurmarkering is.
                # De middenpunt wordt elders in het rapport al gebruikt.
                f"     · {t(_key, lang)}", str(_n), "",
                str(_hyp_sub_conf(_sub, "high")),
                str(_hyp_sub_conf(_sub, "moderate")),
                str(_hyp_sub_conf(_sub, "borderline")),
                str(_hyp_sub_conf(_sub, "low"))]
                + (["", "", ""] if _show_corrob else []))

        conf_rows.append(
            ["A+H totaal",
             str(rsum.get("n_ah_total","—")),
             _v(rsum,"ahi_total",fmt="{:.1f}"),
             "", "", "", ""] + (["", "", ""] if _show_corrob else []))
        _w = ([3.4,1.0,1.1,1.2,1.4,1.4,1.2,1.3,1.5,1.4] if _show_corrob
              else [5.0,1.2,1.5,1.5,1.8,1.8,1.5])
        story.append(KeepTogether([_tbl(hdr_conf, conf_rows, _w)]))
        if _show_corrob:
            story.append(Paragraph(
                f"<i>{t('pdf_corrob_note', lang)}</i>", styles["SM"]))
        # De sterrenkoppen tonen kale getallen ("★★★ ≥0.85"), wat als een
        # percentage gelezen wordt. Het is een rangschikking, geen kans:
        # tegen twaalf scorers per opname is de correlatie r = 0,19 en ligt
        # het niveau ruim 30 procentpunt te hoog.
        story.append(Paragraph(
            f"<i>{t('pdf_conf_bands_note', lang)}</i>", styles["SM"]))
        sp(0.12)

        # v0.15.0: the OAHI 3-point confidence sweep + robustness grade (the
        # threshold-severity "OSAS severity profile") was removed from the clinical
        # PDF (not validated as a severity instrument). The official OAHI is already
        # shown in the classification bar and events table above.

        # ── v0.8.22: RERA, RDI, REM/NREM AHI ──────────────────────────
        rera_n   = rsum.get("n_rera", 0) or 0
        rera_idx = rsum.get("rera_index", 0) or 0
        rdi_val  = rsum.get("rdi", 0) or 0
        # Eén bron. psgscoring levert deze grootheid twee keer: `ahi_rem` uit
        # respiratory.py (via is_rem(), en het enige paar dat `ahi_rem_reliable`
        # draagt) en `rem_ahi` uit pipeline.py (via stage == "R", een eigen
        # herberekening). §8c toonde de tweede, §8e de eerste, onder labels die
        # niet van elkaar te onderscheiden zijn: "REM AHI" en "AHI REM". Ze
        # geven doorgaans hetzelfde, maar als ze uiteenlopen staat er twee keer
        # een ander getal en kwalificeert de REM-noot de verkeerde. `rem_ahi`
        # blijft als terugval voor resultaten van vóór respiratory.py.
        rem_ahi  = rsum.get("ahi_rem")  if rsum.get("ahi_rem")  is not None else rsum.get("rem_ahi")
        nrem_ahi = rsum.get("ahi_nrem") if rsum.get("ahi_nrem") is not None else rsum.get("nrem_ahi")
        n_fri_pure = rsum.get("n_fri", 0) or 0

        # ── Split-night ────────────────────────────────────────────
        # De nacht-AHI hierboven telt diagnostiek én titratie samen en verdunt
        # de diagnose: op de casus die dit aanleiding gaf stond "Mild SAS,
        # AHI 10,1/u" in de kop terwijl het diagnostische deel op 83,5/u lag.
        # Die twee getallen horen naast elkaar te staan, niet één ervan alleen.
        _sn = ((results.get("pneumo") or {}).get("split_night")
               or results.get("split_night") or {})
        _seg = _sn.get("segments") or {}
        if _sn.get("detected") and _seg:
            story.append(_hdr(t("pdf_split_hdr", lang), color=BLUE)); sp(0.1)
            _kop = ["", t("pdf_split_col_sleep", lang),
                    t("pdf_split_col_ahi", lang),
                    t("pdf_split_col_ahi_unc", lang)]
            _rows = []
            _noten = []
            for _k, _lbl2 in (("diagnostic", "pdf_split_diagnostic"),
                              ("therapeutic", "pdf_split_therapeutic")):
                _d = _seg.get(_k) or {}
                _u = _d.get("sleep_h")
                _rows.append([
                    t(_lbl2, lang),
                    f"{_u * 60:.0f} min" if _u is not None else "—",
                    f"{_d.get('ahi'):.1f} {_UH}" if _d.get("ahi") is not None else "—",
                    (f"{_d.get('ahi_incl_uncertain'):.1f} {_UH}"
                     if _d.get("ahi_incl_uncertain") is not None else "—"),
                ])
                if _d.get("reliable") is False:
                    _noten.append(f"{t(_lbl2, lang)}: {t('pdf_split_short', lang)}")
                _uf = _d.get("uncertain_fraction") or 0
                if _uf >= 0.20:
                    _noten.append(f"{t(_lbl2, lang)}: " +
                                  t("pdf_split_untyped", lang).format(
                                      pct=f"{_uf * 100:.0f}"))
            story.append(_tbl(_kop, _rows,
                              [5.2 * cm, 2.6 * cm, 3.0 * cm, 4.4 * cm]))
            sp(0.06)
            story.append(Paragraph(t("pdf_split_note", lang), styles["SM"]))
            for _n in _noten:
                story.append(Paragraph(_n, styles["SM"]))
            sp(0.12)

            # ── De rest van de indexfamilie, ook per deel ────────────────
            #
            # Tot v0.37.3 stond hier een diagnostische AHI, en dáárnaast --
            # in de secties hieronder -- een arousalindex, een RDI, een ODI en
            # een PLM-index over de HELE nacht. Twee soorten getallen onder
            # elkaar alsof ze over hetzelfde stuk slaap gingen. De richting van
            # die fout is niet neutraal: de therapiehelft drukt elk van die
            # indices omlaag, dus de meting waarop de diagnose rust las
            # stelselmatig milder.
            #
            # De saturatie werd al sinds psgscoring 0.29.0 per segment
            # uitgerekend en door niemand gelezen -- dezelfde klasse fout als
            # `analysis_warnings` zonder lezer.
            _ar = _sn.get("arousal") or {}
            _rd = _sn.get("rdi") or {}
            _pl = _sn.get("plm") or {}
            _sp = _sn.get("spo2") or {}

            def _cel(blok, sleutel, decim=1, eenheid=_UH):
                w = (blok or {}).get(sleutel)
                if w is None:
                    return "—"
                return f"{float(w):.{decim}f}{(' ' + eenheid) if eenheid else ''}"

            _extra_defs = [
                (t("pdf_rdi_formula", lang),        _rd, "rdi",   1, _UH),
                (t("pdf_arousal_index", lang),      _ar, "arousal_index", 1, _UH),
                (t("pdf_resp_arousal_index", lang), _ar,
                 "respiratory_arousal_index", 1, _UH),
                ("ODI3",                            _sp, "odi_3pct", 1, _UH),
                ("T90",                             _sp, "pct_below_90", 1, "%"),
                ("PLMI",                            _pl, "plm_index", 1, _UH),
                (t("pdf_snore_index", lang),
                 _sn.get("snore") or {}, "snore_index", 1, _UH),
            ]
            _extra = []
            for _lab, _blk, _key, _dec, _eh in _extra_defs:
                _dv = (_blk.get("diagnostic") or {}).get(_key)
                _tv = (_blk.get("therapeutic") or {}).get(_key)
                # Een rij die in BEIDE helften leeg is, zegt niets en suggereert
                # een gemeten nul. Polygrafie heeft geen arousals; die rijen
                # horen dan te ontbreken, niet op "—" te staan.
                if _dv is None and _tv is None:
                    continue
                _extra.append([
                    _lab,
                    _cel(_blk.get("diagnostic"), _key, _dec, _eh),
                    _cel(_blk.get("therapeutic"), _key, _dec, _eh),
                ])
            # De positie-AHI is genest ({houding: ahi}) en past niet in de
            # vorm hierboven. Hij hoort er wel bij: ligt de patiënt
            # diagnostisch vooral op de rug en onder therapie op de zij, dan
            # verklaart de HOUDING een deel van de daling die anders volledig
            # aan de CPAP wordt toegeschreven.
            _po = _sn.get("position") or {}
            _pd = ((_po.get("diagnostic") or {}).get("ahi_per_pos") or {})
            _pt = ((_po.get("therapeutic") or {}).get("ahi_per_pos") or {})
            for _h in sorted(set(_pd) | set(_pt)):
                _dv, _tv = _pd.get(_h), _pt.get(_h)
                if _dv is None and _tv is None:
                    continue
                _extra.append([
                    f"AHI {_h}",
                    f"{_dv:.1f} {_UH}" if _dv is not None else "—",
                    f"{_tv:.1f} {_UH}" if _tv is not None else "—",
                ])

            if _extra:
                story.append(Paragraph(
                    f"<b>{t('pdf_split_other_hdr', lang)}</b>", styles["SM"]))
                sp(0.04)
                story.append(_tbl(
                    ["", t("pdf_split_col_diag", lang),
                     t("pdf_split_col_ther", lang)],
                    _extra, [7.2 * cm, 4.0 * cm, 4.0 * cm]))
                sp(0.04)
                story.append(Paragraph(t("pdf_split_other_note", lang),
                                       styles["SM"]))
                sp(0.12)

        story.append(_hdr(t("pdf_rera_section_hdr", lang), color=BLUE)); sp(0.1)
        n_rera_fri  = rsum.get("n_rera_fri", 0) or 0
        n_rera_flat = rsum.get("n_rera_flattening", 0) or 0
        # De kolom heet "Index" maar droeg het AANTAL: bij 57 RERA's stond er
        # "n=57 · Index 57". Alleen de totaalrij deelde door de tijd. Een index
        # van 57/u naast een totaal van 4,2/u leest als twee onverenigbare
        # getallen over hetzelfde. Zelfde noemer als het totaal, afgeleid uit
        # de twee waarden die er al waren zodat er geen tweede TST-definitie
        # bijkomt.
        _rera_h = (rera_n / rera_idx) if (rera_n and rera_idx) else None

        def _idx(n):
            return f"{n / _rera_h:.1f} {_UH}" if _rera_h else "—"

        # De FRI-rij deelde hier zelf; sectie 8d deed het met een ANDERE
        # noemer. Nu leest ze het veld dat psgscoring publiceert, en 8d
        # hetzelfde.
        _fri_i = _fri_index(rsum, stats)

        ext_rows = [
            [t("pdf_rera_amp_arousal", lang),  str(n_rera_fri), _idx(n_rera_fri)],
            [t("pdf_rera_flat_arousal", lang), str(n_rera_flat), _idx(n_rera_flat)],
            [t("pdf_rera_total", lang),  str(rera_n), f"{rera_idx:.1f} {_UH}"],
            [t("pdf_fri_no_criteria", lang), str(n_fri_pure),
             f"{_fri_i:.1f} {_UH}" if _fri_i is not None else "—"],
            [t("pdf_rdi_formula", lang),          "", f"{rdi_val:.1f} {_UH}"],
        ]
        story.append(KeepTogether([_tbl(
            [t("pdf_param",lang), "n", "Index"],
            ext_rows,
            [8, 2, 4])])); sp(0.1)

        stage_rows = [
            ["REM AHI",  f"{rem_ahi:.1f} {_UH}" if rem_ahi is not None else "—"],
            ["NREM AHI", f"{nrem_ahi:.1f} {_UH}" if nrem_ahi is not None else "—"],
        ]
        # Positional AHI (from position analysis)
        pos_sum = pneumo.get("position", {}).get("summary", {})
        stage_rows.extend(_position_rows(pos_sum, lang))
        story.append(KeepTogether([_tbl(
            [t("pdf_param",lang), t("pdf_value",lang)],
            stage_rows,
            [8, 6])])); sp(0.1)
        _rem_note = rem_ahi_caveat(rsum, lang)
        if _rem_note:
            # Geen waarschuwingsglyph: ⚠ ontbreekt in het ingebedde lettertype
            # en wordt een zwart blokje — dat is in dit rapport bovendien al de
            # legenda-kleurmarkering. Kleur en cursief dragen de nadruk.
            story.append(Paragraph(
                f"<i><font color='#e67e22'>REM AHI: {_rem_note}.</font></i>",
                styles["SM"])); sp(0.1)

        # ── v0.10.0: klinische fenotypes (POSA, REM-predominant) ──────────
        _ph = rsum.get("phenotypes") or {}
        _pheno_lines = []
        _posa = _ph.get("positional_osa")
        if _posa:
            _yn = t("pdf_pheno_yes", lang) if _posa.get("flag") else t("pdf_pheno_no", lang)
            _txt = (f"<b>{t('pdf_pheno_posa', lang)}:</b> {_yn} "
                    f"(supine {_posa.get('ahi_supine')} vs non-supine {_posa.get('ahi_non_supine')} {_UH}"
                    + (f", {_posa.get('supine_non_supine_ratio')}×"
                       if _posa.get('supine_non_supine_ratio') is not None else "") + ")")
            if _posa.get("flag") and _posa.get("positional_therapy_candidate"):
                _txt += " — " + t("pdf_pheno_posa_therapy", lang)
            _pheno_lines.append(_txt)
        _remp = _ph.get("rem_predominant")
        if _remp:
            _yn = t("pdf_pheno_yes", lang) if _remp.get("flag") else t("pdf_pheno_no", lang)
            _pheno_lines.append(
                f"<b>{t('pdf_pheno_rem', lang)}:</b> {_yn} "
                f"(REM {_remp.get('rem_ahi')} vs NREM {_remp.get('nrem_ahi')} {_UH}, "
                f"{_remp.get('rem_nrem_ratio')}×)")
        if _pheno_lines:
            story.append(_hdr(t("pdf_pheno_hdr", lang), color=BLUE)); sp(0.05)
            for _ln in _pheno_lines:
                story.append(Paragraph(_ln, styles["SM"]))
            sp(0.1)

        story.append(Paragraph(
            f"<i>{t('pdf_rera_explanation',lang)} {t('pdf_rdi_explanation', lang)}</i>",
            styles["SM"])); sp(0.1)

        # ── SpO2 samplerate warning ────────────────────────────────
        if pneumo.get("spo2", {}).get("spo2_low_samplerate"):
            story.append(Paragraph(
                t("pdf_spo2_low_sr_warn", lang),
                styles["SM"])); sp(0.1)

        # ── Overschatting-correctie samenvatting (v0.8.11) ───────────────
        n_spo2_cc  = rsum.get("n_spo2_cross_contaminated", 0) or 0
        n_csr_fl   = rsum.get("n_csr_flagged", 0) or 0
        n_noise    = rsum.get("n_low_conf_noise", 0) or 0
        n_border   = rsum.get("n_low_conf_borderline", 0) or 0
        ahi_csr    = rsum.get("ahi_csr_corrected")
        ahi_noise  = rsum.get("ahi_excl_noise")
        if n_spo2_cc > 0 or n_csr_fl > 0 or n_noise > 0:
            story.append(_hdr(t("pdf_overcounting_corrections", lang), color=BLUE)); sp(0.1)
            corr_rows = [
                [t("pdf_fix1_name",lang),
                 t("pdf_corrected",lang),
                 t("pdf_fix1_desc",lang)],
                [t("pdf_fix2_name",lang),
                 f"{n_spo2_cc} events",
                 t("pdf_fix2_desc",lang)],
                [t("pdf_fix3_name",lang),
                 (f"{n_csr_fl} events  →  AHI {ahi_csr:.1f}{_UH}" if ahi_csr else f"{n_csr_fl} events"),
                 t("pdf_fix3_desc",lang)],
                [t("pdf_fix4_name",lang),
                 f"{n_noise} ruis  +  {n_border} borderline",
                 (f"AHI excl. ruis (<0.40): {ahi_noise:.1f}{_UH}" if ahi_noise else t("pdf_conf_signal_noise", lang))],
                [t("pdf_fix5_name",lang),
                 t("pdf_corrected",lang),
                 t("pdf_fix5_desc",lang)],
            ]
            n_local_rej = resp.get("n_local_baseline_rejected", 0) or 0
            if n_local_rej > 0:
                corr_rows.append(
                    [t("pdf_fix6_name",lang),
                     f"{n_local_rej} afgewezen",
                     t("pdf_fix6_desc",lang)])
            n_ecg_reclass = rsum.get("n_ecg_reclassified_central", 0) or 0
            if n_ecg_reclass > 0:
                corr_rows.append(
                    [t("pdf_ecg_fix_name",lang),
                     f"{n_ecg_reclass} {t('pdf_to_central',lang)}",
                     t("pdf_ecg_fix_desc",lang)])
            # v0.8.37: postprocess — CSR reclassification + mixed decomposition
            pp = pneumo.get("postprocess", {})
            n_csr_recl = pp.get("n_csr_reclassified", 0) or 0
            if n_csr_recl > 0:
                corr_rows.append(
                    ["CSR reclassification",
                     f"{n_csr_recl} → central",
                     "CSR-flagged obstr/mixed → central (cardiac artifact)"])
            n_mix_decomp = pp.get("n_mixed_to_central", 0) or 0
            if n_mix_decomp > 0:
                corr_rows.append(
                    ["Mixed decomposition",
                     f"{n_mix_decomp} → central",
                     "Central portion ≥10 s → reclassified as central"])
            story.append(KeepTogether([_tbl(
                [t("pdf_correction",lang), t("pdf_impact",lang), t("pdf_explanation",lang)],
                corr_rows, [4.0, 3.5, 9.5])]))
            sp(0.15)
            story.append(Paragraph(
                f"<i>{t('pdf_disc_informative',lang)}</i>",
                styles["SM"])); sp(0.1)

        # ── Overige respiratoire indices ─────────────────────────────────
        _rem_cav = rem_ahi_caveat(rsum, lang)
        story.append(KeepTogether([_tbl(
            [t("pdf_param", lang), t("pdf_value", lang), ""],
            [["AHI REM",   _v(rsum,"ahi_rem",fmt="{:.1f}"),
              (_rem_cav or "")],
             ["AHI NREM",  _v(rsum,"ahi_nrem",fmt="{:.1f}"), ""],
             [t("pdf_avg_apnea_dur", lang), f"{rsum.get('avg_apnea_dur_s','—')} s", ""],
             [t("pdf_max_apnea_dur", lang),  f"{rsum.get('max_apnea_dur_s','—')} s", ""],
            ], [8, 4, 5])])); sp(0.1)

        # v0.8.37: Position × stage cross-table
        resp_events = resp.get("events", [])
        position_data = pneumo.get("position", {})
        _hypno = results.get("hypnogram", results.get("hypno", []))
        if resp_events and _hypno and position_data:
            try:
                draw_position_stage_table(
                    story, events=resp_events, hypno=_hypno,
                    position_data=position_data, sf_pos=1,
                    tst_hours=float(str(stats.get("TST", 0) or 0))/60, t=t)
            except Exception:
                pass
        sp(0.1)

        # Arousal / RERA / RDI (v0.8.22: skip bij polygrafie)
        arous=pneumo.get("arousal",{}); asum=arous.get("summary",{})
        if not is_polygraphy and arous.get("success") and asum:
            story.append(_hdr(t("rpt_sec8b", lang),color=BLUE)); sp(0.1)
            # v0.15.0 (B6): arousal aetiology as per-hour indices (AASM V.A Note 4)
            _ar_rows = [
                [t("pdf_arousal_index", lang),
                 f"{asum.get('arousal_index','—')} {_UH}  ({t('pdf_arousal_ref', lang)})"],
            ]
            if asum.get("respiratory_arousal_index") is not None:
                _ar_rows.append([t("pdf_resp_arousal_index", lang),
                                 f"{asum.get('respiratory_arousal_index')} {_UH}"])
            if asum.get("spontaneous_arousal_index") is not None:
                _ar_rows.append([t("pdf_spont_arousal_index", lang),
                                 f"{asum.get('spontaneous_arousal_index')} {_UH}"])
            if asum.get("plm_arousal_index") is not None:
                _ar_rows.append([t("pdf_plm_arousal_index", lang),
                                 f"{asum.get('plm_arousal_index')} {_UH}"])
            _ar_rows += [
                [t("pdf_resp_arousals",lang),    str(asum.get("n_respiratory_arousals","—"))],
                [t("pdf_spont_arousals",lang),        str(asum.get("n_spontaneous_arousals","—"))],
            ]
            # RERA's, RERA-index en RDI stonden hier ook — uit de
            # arousal-module, die ze onafhankelijk van de respiratoire
            # pijplijn berekent en NIET bijwerkt na RERA-promotie. Sectie 8
            # meldde 183 RERA's terwijl hier 0 stond, en er stonden twee
            # verschillende RDI's in één rapport. Sectie 8 is de bron: die
            # komt uit _compute_rera_rdi() en telt beide RERA-bronnen.
            #
            # Deze sectie gaat over arousal-ETIOLOGIE — waar arousals vandaan
            # komen — en dat is een andere vraag dan hoeveel RERA's er zijn.
            story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang)], _ar_rows,[9,8])); sp(0.1)
    else:
        story.append(Paragraph(f"{t('pdf_not_available', lang)}: {resp.get('error','—')}",styles["SM"]))
    sp(0.12)

    # ── 8c. Breath-by-breath analyse ───────────────────────────
    bb = resp.get("breath_analysis", {})
    if bb.get("n_breaths", 0) > 0:
        story.append(_hdr(t("rpt_sec8c", lang), color=BLUE)); sp(0.1)

        if not bb.get("fallback"):
            rows = [
                [t("pdf_detected_breaths", lang),  str(bb.get("n_breaths", "—"))],
                [t("pdf_bb_apneas", lang),     str(bb.get("n_bb_apneas", "—"))],
                [t("pdf_bb_hypopneas", lang),  str(bb.get("n_bb_hypopneas", "—"))],
            ]
            if bb.get("avg_flattening") is not None:
                flat_val = bb["avg_flattening"]
                flat_label = (t("pdf_flat_normal", lang) if flat_val < 0.25
                              else t("pdf_flat_elevated", lang) if flat_val < 0.40
                              else t("pdf_flat_high", lang))
                rows.append([t("pdf_mean_flattening", lang), f"{flat_val:.2f} ({flat_label})"])
            story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], rows, [9, 8]))
            sp(0.06)
            # Zonder deze regel nodigt het paneel uit tot de verkeerde
            # conclusie. Op de Thaise casus stond hier "190 apneus" naast NUL
            # gescoorde apneus, en dat werd — ook door mij — gelezen als bewijs
            # van onderdetectie. Op dertig gewone opnames loopt die verhouding
            # van 0 % tot 173 %: op één opname werden er MEER events gescoord
            # dan hier geteld. Twee getallen die zo uiteenlopen meten niet
            # hetzelfde ding.
            story.append(Paragraph(
                f"<i>{t('pdf_bb_not_a_reference', lang)}</i>", styles["SM"]))
            sp(0.15)

        # Twee sensoren: melden dat AASM gevolgd is. Eén sensor: melden dat
        # dat NIET zo is. Dat tweede ontbrak, terwijl juist dat geval de
        # lezer iets moet vertellen — apneus op nasale druk overdetecteren
        # ten opzichte van de thermistor, en de AASM schrijft de thermistor
        # daar juist om voor.
        for _key, _kw in flow_sensor_notes(resp, pneumo):
            story.append(Paragraph(t(_key, lang).format(**_kw), styles["SM"]))

        # ── Scoring profielen tabel ───────────────────────────────
        _active_profile = pneumo.get("meta", {}).get("scoring_profile", "standard")
        _prof_comp = pneumo.get("profile_comparison", {})

        # OAHI per profile: show active profile result, others if comparison available
        _oahi_strict    = _prof_comp.get("strict", {}).get("oahi")
        _oahi_standard  = _prof_comp.get("standard", {}).get("oahi")
        _oahi_sensitive = _prof_comp.get("sensitive", {}).get("oahi")

        # Fill active profile from current results
        if _active_profile == "strict" and _oahi_strict is None:
            _oahi_strict = oahi
        elif _active_profile == "standard" and _oahi_standard is None:
            _oahi_standard = oahi
        elif _active_profile == "sensitive" and _oahi_sensitive is None:
            _oahi_sensitive = oahi

        def _oahi_cell(val, is_active):
            if val is not None:
                s = f"{val:.1f}"
                return f"\u25b6 {s}" if is_active else s
            return "—"

        _profiles_data = [
            ["Strict",    "70% (\u226530%)", "30s",  "—",   "15s",
             f"{t('pdf_no',lang)} (envelope)",
             _oahi_cell(_oahi_strict, _active_profile == "strict")],
            ["Standard",  "70% (\u226530%)", "45s",  "3s",  "15s",
             f"{t('pdf_yes',lang)} (peak+env)",
             _oahi_cell(_oahi_standard, _active_profile == "standard")],
            ["Sensitive",  "75% (\u226525%)", "45s",  "5s",  "—",
             f"{t('pdf_yes',lang)} (peak+env)",
             _oahi_cell(_oahi_sensitive, _active_profile == "sensitive")],
        ]
        # Markeer actief profiel met *
        _pmap = {"strict": 0, "standard": 1, "sensitive": 2}
        _ai = _pmap.get(_active_profile, 1)
        _profiles_data[_ai][0] = f"\u25b6 {_profiles_data[_ai][0]}"

        _prof_hdr = [t("pdf_prof_header",lang), t("pdf_prof_hypopnea",lang), t("pdf_prof_nadir",lang), "Smoothing", "Cross-contam", t("pdf_prof_peak",lang), "OAHI"]
        _prof_tbl = Table([_prof_hdr] + _profiles_data,
                          colWidths=[2.0*cm, 2.3*cm, 1.6*cm, 1.6*cm, 2.0*cm, 2.8*cm, 1.8*cm])
        _prof_tbl.setStyle(TableStyle([
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 6),
            ("TEXTCOLOR",  (0,0), (-1,-1), colors.HexColor("#2c3e50")),
            ("BACKGROUND", (0,0), (-1,0),  colors.HexColor("#e8edf3")),
            ("BACKGROUND", (0, _ai+1), (-1, _ai+1), colors.HexColor("#d5f5e3")),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#c0c8d4")),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ]))
        # v0.15.0: strict/standard/sensitive "OSAS severity profile" comparison table
        # removed from the clinical PDF (not validated as a severity instrument). The
        # active profile is still named in the classification bar; the validated dual
        # AHI (Rule 1A vs 1B) is shown above.
        # story.append(_prof_tbl); sp(0.12)   # intentionally not rendered

        # ── v0.23.0: profielmatrix, uitsluitend voor studies ───────────────
        #
        # Deze matrix vervangt de tabel hierboven NIET in het klinische rapport.
        # Die is in v0.15.0 bewust verwijderd omdat hij niet gevalideerd is als
        # ernstinstrument, en meerdere severities naast elkaar zetten nodigt uit
        # tot lezen als alternatieve diagnoses. Dat besluit draai ik niet om als
        # bijeffect van een rapportagevraag.
        #
        # De specificatie opent met "Wanneer een studie via YF loopt", en dat is
        # precies de grens die het conflict oplost: de matrix is een
        # studieartefact. Hij verschijnt als er een volledige profielvergelijking
        # bestaat (`profile_comparison.json` met `_meta`) of als er een
        # studieprofiel-set is geconfigureerd. Zonder dat blijft het klinische
        # rapport ongewijzigd.
        #
        # De rijlabels en de regelset komen uit de registry — geen hard-coded
        # parameterkolommen meer. Dat wás het echte defect in de tabel hierboven:
        # "70% (≥30%)", "30s", "3s", "15s" kwamen uit geen enkele bron.
        try:
            from profile_matrix import build_matrix, fmt, fmt_delta

            _pm_comparison = results.get("profile_comparison_full") or None
            _pm_study = (results.get("study_profile_set") or {}) or None
            if _pm_comparison or _pm_study:
                _pm = build_matrix(pneumo, _pm_comparison)
                _pm_rows = _pm["rows"]
            else:
                _pm_rows = []

            if _pm_rows:
                story.append(Paragraph(t("pdf_prof_matrix_title", lang), styles["H2"]))
                _pm_hdr = [t("pdf_prof_matrix_profile", lang),
                        t("pdf_prof_matrix_ruleset", lang),
                        "AHI", "OAHI", "CAI", t("pdf_prof_matrix_events", lang),
                        "RDI", t("pdf_prof_matrix_severity", lang),
                        t("pdf_prof_matrix_delta", lang)]
                _pm_body = []
                for _r in _pm_rows:
                    _label = _r["display_name"]
                    if _r["is_frozen"]:
                        _label = f"\U0001F512 {_label}"
                    if _r["is_primary"]:
                        _label = f"<b>\u25b6 {_label}</b>"
                    _pm_body.append([
                        _label, _r["ruleset"],
                        fmt(_r["ahi"]), fmt(_r["oahi"]), fmt(_r["cai"]),
                        fmt(_r["n_events"], 0), fmt(_r["rdi"]),
                        _r["severity"],
                        "—" if _r["is_primary"] else fmt_delta(_r["delta_ahi"]),
                    ])
                story.append(_tbl(_pm_hdr, _pm_body, [5.2, 4.4, 1.5, 1.5, 1.5, 1.4, 1.5, 2.0, 1.6]))
                sp(0.08)

                _fn = _pm["footnotes"]
                _notes = []
                if _fn["primary"]:
                    _prim = next(r for r in _pm_rows if r["is_primary"])
                    _notes.append(t("pdf_prof_matrix_fn_primary", lang).format(
                        profile=_prim["display_name"]))
                _notes.append(t("pdf_prof_matrix_fn_channels", lang))
                if _fn["rdi_missing"]:
                    _notes.append(t("pdf_prof_matrix_fn_rdi", lang))
                if _fn["frozen_present"]:
                    _notes.append(t("pdf_prof_matrix_fn_frozen", lang))
                if _fn["experimental_present"]:
                    _notes.append(t("pdf_prof_matrix_fn_experimental", lang))
                if _fn["pre_config"]:
                    _notes.append(t("pdf_prof_matrix_fn_preconfig", lang))
                if _pm["primary_mismatch"]:
                    _mm = _pm["primary_mismatch"]
                    _notes.append(t("pdf_prof_matrix_fn_mismatch", lang).format(
                        matrix=f"{_mm['matrix']:.1f}", head=f"{_mm['head']:.1f}"))
                for _n in _notes:
                    story.append(Paragraph(_n, styles["SM"]))
                sp(0.12)
        except Exception as _pm_exc:                       # noqa: BLE001
            # Een rapport mag hier niet op stranden; een ontbrekende matrix is
            # zichtbaar, een ontbrekend rapport is een incident.
            logger.warning("profielmatrix niet gerenderd: %s", _pm_exc)

        # v0.2.8: AHI Confidence Interval + Robustness Score
        _ahi_intv = pneumo.get("ahi_interval", {})
        _intv = _ahi_intv.get("interval")
        _grade = _ahi_intv.get("robustness_grade", "")
        if False and _intv and _grade:  # v0.15.0: AHI-robustness interval removed from PDF
            _grade_colors = {"A": "#27ae60", "B": "#f39c12", "C": "#e74c3c"}
            _gcol = _grade_colors.get(_grade, "#95a5a6")
            _sev_strict = _ahi_intv.get("strict", {}).get("severity", "?")
            _sev_std    = _ahi_intv.get("standard", {}).get("severity", "?")
            _sev_sens   = _ahi_intv.get("sensitive", {}).get("severity", "?")
            _interval_text = (
                f'<b>AHI Interval: [{_intv[0]:.1f} – {_intv[1]:.1f}] /h</b>  '
                f'<font color="{_gcol}"><b>Robustness: {_grade}</b></font>  '
                f'({_sev_strict} → {_sev_std} → {_sev_sens})'
            )
            story.append(Paragraph(_interval_text, ParagraphStyle(
                "AHI_interval", parent=styles["SM"], fontSize=7,
                spaceAfter=2, spaceBefore=2,
            )))
            sp(0.1)

    # ── 8d. FLOW-REDUCTIE ZONDER CRITERIA (FRI) ──────────────
    rejected_hyps = resp.get("rejected_hypopneas", [])
    n_reinstated  = resp.get("rule1b_reinstated", 0) or 0
    # Deze sectie telde `len(rejected) - n_reinstated`: ALLE afgewezen
    # hypopneeën, inclusief die verderop tot RERA gepromoveerd zijn. Sectie 8
    # toont `rsum["n_fri"]`, de events die FRI BLEVEN. Twee definities onder
    # hetzelfde label, en de ene was systematisch hoger dan de andere.
    #
    # "Flow-reductie zonder criteria" betekent: geen desaturatie, geen arousal,
    # dus ook geen RERA. Dat is de tweede definitie. Sectie 8 is de bron.
    n_fri = rsum.get("n_fri")
    if n_fri is None:
        n_fri = max(0, len(rejected_hyps) - n_reinstated)
    if n_fri > 0 and resp.get("success"):
        fri_index = _fri_index(rsum, stats)
        story.append(_hdr(t("rpt_sec8d", lang), color=BLUE)); sp(0.1)
        story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], [
            [t("pdf_fri_count", lang),  str(n_fri)],
            [t("pdf_fri_index", lang),
             f"{fri_index:.1f} {_UH}" if fri_index is not None else "—"],
            [t("pdf_fri_r1b", lang),    str(n_reinstated)],
        ], [9, 8])); sp(0.1)
        story.append(Paragraph(
            f"<i>{t('pdf_fri_note', lang)}</i>", styles["SM"])); sp(0.1)

    # ── 8e. Signaalvoorbeelden ────────────────────────────────
    # Blijft uit het RAPPORT; de visuele controle krijgt een eigen weergave.
    #
    # Stond hier sinds v0.8.36 uit met "epoch alignment nog niet correct".
    # Die uitlijning is nagemeten en klopt: op een synthetische mixed-rate EDF
    # met een dropout op een bekende plek, en op menselijk gescoorde events uit
    # PSG-IPA (SN3, obstructief t=316,6 s, centraal t=241,8 s) valt de band
    # exact op het event, met het effort-gedrag dat bij het type hoort.
    # Vastgelegd in tests/test_epoch_panel_alignment.py.
    #
    # Wat wél stuk was — median ± 4·MAD dat de referentie-ademhaling wegklemde
    # zodra het event stil genoeg was — is gerepareerd in _plot_epoch_example.
    #
    # Waarom het toch uit blijft: 400 events is ~73 s rendertijd en ~28 MB aan
    # panelen. Een rapport is het verkeerde omhulsel voor een volledige
    # eventcontrole; die hoort achter een aparte weergave die op aanvraag
    # tekent.
    # if not is_polygraphy:
    #     epoch_imgs = _build_epoch_examples(results)
    #     if epoch_imgs:
    #         story.append(PageBreak())
    #         story.append(_hdr(t("rpt_sec8e", lang), color=BLUE)); sp(0.1)
    #         story.append(Paragraph(
    #             t("pdf_epoch_intro", lang), styles["SM"])); sp(0.15)
    #         for ev, img in epoch_imgs:
    #             story.append(KeepTogether([img, Spacer(1, 0.15*cm)]))
    #             sp(0.1)

    # ── 9. SpO2 ───────────────────────────────────────────────
    spo2=pneumo.get("spo2",{}); ss=spo2.get("summary",{})
    story.append(_hdr(t("rpt_sec9", lang))); sp(0.1)
    if spo2.get("success") and ss:
        # De laagste saturatie die bij een respiratoir event hoort. Het
        # nachtminimum een regel hoger kan van een artefact komen of van een
        # dip buiten elk event; dit getal is toewijsbaar aan een event.
        _ev_nadirs = [e.get("min_spo2") for e
                      in pneumo.get("respiratory", {}).get("events", [])
                      if isinstance(e.get("min_spo2"), (int, float))]
        _ev_nadir_row = ([[t("pdf_event_spo2_nadir", lang),
                           f"{min(_ev_nadirs):.0f} %", ""]] if _ev_nadirs else [])
        story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang),"Ref"],[
            [t('pdf_mean_spo2', lang),  f"{ss.get('mean_spo2', ss.get('avg_spo2','—'))} %", "≥ 95%"],
            [t('pdf_baseline_spo2', lang),    f"{ss.get('baseline_spo2','—')} %",  ""],
            [t('pdf_min_spo2', lang),   f"{ss.get('min_spo2','—')} %",  ""],
            *_ev_nadir_row,
            [t("pdf_time_below90",lang),       f"{ss.get('pct_below_90','—')} %","< 1%"],
            ["ODI 3%",           f"{ss.get('odi_3pct','—')} {_UH}",    "< 5{_UH}"],
            ["ODI 4%",           f"{ss.get('odi_4pct','—')} {_UH}",    "< 5{_UH}"],
            # De referentiewaarde "< 20" komt uit Azarbarzin et al. (Eur Heart
            # J 2019) en geldt voor DIE definitie: basislijn = maximum SpO2 in
            # de 100 s vóór het eventeinde, oppervlakte over een uit het
            # ensemble-gemiddelde afgeleid zoekvenster. psgscoring kan de
            # burden op meerdere manieren berekenen, en die geven op dezelfde
            # opname waarden die een factor 0,29 tot 2,34 uiteenlopen (acht
            # MESA-opnames; psgscoring/docs/hypoxic_burden_bevinding.md).
            # Toon de afkapwaarde daarom alleen naast de gepubliceerde
            # definitie -- een grens naast een getal van een andere definitie
            # suggereert een vergelijkbaarheid die er niet is.
            [("Hypoxic burden" if ss.get("hypoxic_burden_method") == "azarbarzin"
              else f"Hypoxic burden ({ss.get('hypoxic_burden_method') or '?'})"),
             # `.get(k, "—")` geeft de default NIET terug als de sleutel
             # bestaat met waarde None -- en dat is precies wat het
             # burden-plafond doet boven 150. Er stond letterlijk
             # "None %·min/u" in een klinisch rapport.
             (f"{ss['hypoxic_burden']} %·min{_UH}"
              if ss.get("hypoxic_burden") is not None else "—"),
             ("< 20" if ss.get("hypoxic_burden_method") == "azarbarzin" else "")],
            [t("pdf_ventilatory_burden", lang),
             (f"{rsum.get('ventilatory_burden')} %"
              if rsum.get('ventilatory_burden') is not None else "—"),
             # v0.16.5: hide the ≤25% reference for central-dominant (CSAS) studies —
             # the VB norm is OBSTRUCTIVE-OSA-derived and not calibrated for central apnea.
             ("" if _is_central_dominant(rsum) else "≤ 25%")],
        ],[8,4.5,4.5]))
        # De hypoxic burden meet de oppervlakte van event-gerelateerde
        # desaturaties TEN OPZICHTE VAN de baseline. Bij aanhoudende hypoxemie
        # ligt die baseline al laag en ogen de dips klein: één patiënt zat
        # 94,6% van de nacht tussen 80 en 90% met een baseline van 85% en kreeg
        # HB 21,6 — net boven de laagrisicodrempel. Het getal klopt, de indruk
        # niet. HB is ontworpen voor intermitterende OSA-desaturaties.
        try:
            _t90 = ss.get("pct_below_90")
            if (_t90 is not None and float(_t90) > 30
                    and ss.get("hypoxic_burden") is not None):
                story.append(Paragraph(t("pdf_hb_sustained_hypoxemia", lang),
                                       styles["SM"])); sp(0.1)
        except (TypeError, ValueError):
            pass
        ts=spo2.get("timeseries")
        if ts and len(ts)>10:
            sp(0.15)
            try: story.append(KeepTogether([_spo2_img(ts)]))
            except: pass
    else:
        story.append(Paragraph(f"SpO2: {spo2.get('error',t('pdf_no_channel',lang))}",styles["SM"]))
    sp(0.12)

    # v0.8.37: Detailed saturation band breakdown
    if spo2.get("success") and ss:
        try:
            tib_min = float(str(stats.get("TIB", 480) or 480))
            draw_spo2_bands(story, spo2_summary=ss, tib_min=tib_min, t=t)
        except Exception:
            pass

    # ── 10. PLM ────────────────────────────────────────────────
    plm=pneumo.get("plm",{}); ps=plm.get("summary",{})
    if plm.get("success") and ps:
        story.append(_hdr(t("rpt_sec10", lang))); sp(0.1)
        plmi=_f(ps,"plm_index") or 0
        story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang)],[
            [t("pdf_total_lms",lang),                 str(ps.get("n_lm_total","—"))],
            [t('pdf_lms_sleep', lang),          str(ps.get("n_lm_sleep","—"))],
            [t('pdf_resp_assoc', lang), str(ps.get("n_resp_associated","—"))],
            [t("pdf_plms_series",lang),           str(ps.get("n_plm","—"))],
            [t("pdf_plm_series",lang),                 str(ps.get("n_plm_series","—"))],
            ["PLMI",                       f"{plmi:.1f} {_UH}  —  {ps.get('plm_severity','—')}"],
        ],[9,8])); sp(0.1)

    # ── 10b. RONCHOPATHIE (snurk-analyse) ─────────────────────
    snore = pneumo.get("snore", {})
    snore_s = snore.get("summary", {})
    story.append(_hdr(t("rpt_sec10b", lang))); sp(0.1)
    if snore.get("success") and snore_s:
        story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], [
            [t("pdf_snore_min", lang),     f"{snore_s.get('snore_min', '—')} min"],
            [t("pdf_snore_pct", lang),     f"{snore_s.get('snore_pct_tst', '—')} %"],
            [t("pdf_snore_index", lang),   f"{snore_s.get('snore_index', '—')} {_UH}"],
        ], [9, 8])); sp(0.1)
    else:
        story.append(Paragraph(
            f"<i>{t('pdf_snore_no_data', lang)}</i>", styles["SM"])); sp(0.1)

    # v0.8.37: Snoring cross-table by position × stage
    _hypno = results.get("hypnogram", results.get("hypno", []))
    if snore.get("success") and _hypno:
        try:
            draw_snoring_crosstab(
                story, snore_data=snore, hypno=_hypno,
                position_data=pneumo.get("position", {}), t=t)
        except Exception:
            pass

    # Ensure arousal summary is available for diagnosis
    try:
        asum
    except NameError:
        asum = pneumo.get("arousal", {}).get("summary", {})

    # ── 10c. HARTRITME / ECG (v0.8.37) ──────────────────────────
    _hr = pneumo.get("heart_rate", {})
    _hr_sum = _hr.get("summary", {})
    if _hr.get("success") and _hr_sum:
        story.append(_hdr(t('pdf_ecg_hr_title', lang))); sp(0.05)
        _hr_rows = [
            [t("pdf_param", lang), t("pdf_value", lang), "Ref"],
        ]
        # psgscoring 0.14.2 zet er een oordeel bij. Een minimum van 20,0 bpm is
        # de ondergrens van het plausibiliteitsfilter en niet de patiënt; bij
        # sensoruitval tonen we de robuuste percentielen en zeggen we erbij
        # waarom. Ontbreekt het veld (oudere psgscoring), dan blijft alles zoals
        # het was.
        _hr_ok = _hr_sum.get("hr_reliable", True)
        _hr_data = [
            [t('pdf_mean_hr', lang),    f"{_hr_sum.get('avg_hr', '—')} bpm",  "60–100"],
        ]
        if _hr_ok:
            _hr_data += [
                [t('pdf_min_hr', lang), f"{_hr_sum.get('min_hr', '—')} bpm", ""],
                [t('pdf_max_hr', lang), f"{_hr_sum.get('max_hr', '—')} bpm", ""],
            ]
        else:
            _hr_data += [
                [t('pdf_hr_p1', lang),  f"{_hr_sum.get('hr_p1', '—')} bpm", ""],
                [t('pdf_hr_p99', lang), f"{_hr_sum.get('hr_p99', '—')} bpm", ""],
            ]
        if _hr_sum.get("bradycardia_episodes"):
            _hr_data.append([t('pdf_bradycardia', lang), str(_hr_sum["bradycardia_episodes"]), ""])
        if _hr_sum.get("tachycardia_episodes"):
            _hr_data.append([t('pdf_tachycardia', lang), str(_hr_sum["tachycardia_episodes"]), ""])
        story.append(_tbl(
            [t("pdf_param", lang), t("pdf_value", lang), "Ref"],
            _hr_data, [8, 4.5, 4.5])); sp(0.15)
        if not _hr_ok:
            story.append(Paragraph(
                t('pdf_hr_unreliable', lang).format(
                    reason=_hr_sum.get("hr_unreliable_reason") or "—"),
                styles["SM"])); sp(0.1)

    # ── 11. BESLUIT (gestandaardiseerd AASM) ────────────────────
    story.append(_hdr(t("rpt_sec11", lang))); sp(0.1)

    # Haal metrics op
    ahi = float(rsum.get("ahi_total", 0) or 0)
    oahi = float(rsum.get("oahi", 0) or 0)
    sev = rsum.get("severity", "unknown")
    spo2_min_v = ss.get("min_spo2", "—") if spo2.get("success") else "—"
    spo2_pct_v = ss.get("pct_below_90", "—") if spo2.get("success") else "—"
    plmi_v = float(ps.get("plm_index", 0) or 0) if plm.get("success") else 0
    ai_v = float(asum.get("arousal_index", 0) or 0) if pneumo.get("arousal", {}).get("success") else 0
    se_v = float(str(stats.get("SE", 0) or 0).replace("%", ""))
    tst_v = float(str(stats.get("TST", 0) or 0))

    # BMI
    bmi_raw = pat.get("bmi", "")
    try:
        bmi_v = float(str(bmi_raw).replace(",", "."))
    except (ValueError, TypeError):
        bmi_v = None

    # Manuele diagnose overschrijft auto
    manual_diag = pat.get("diagnosis", "").strip()
    manual_comment = pat.get("comments", "").strip()

    # De arts vult het besluit manueel in via de rapport-editor; de auto-samenvatting
    # (v0.15.0, B1) is louter informatief en overschrijft de manuele diagnose nooit.
    if manual_diag:
        story.append(Paragraph(f"<b>{t('concl_diagnosis', lang)}:</b> {manual_diag}", styles["B"]))
    else:
        story.append(Paragraph(
            f"<i>{t('concl_empty', lang)}</i>", styles["SM"]))

    # v0.15.0 (B1): auto-generated descriptive impression (informational only)
    _auto = _auto_conclusion(rsum, pneumo, ss, lang)
    if _auto:
        _auto_cells = [
            [Paragraph(f"<b>{t('pdf_concl_auto_hdr', lang)}</b>", ParagraphStyle(
                "AutoHdr", fontName="Helvetica-Bold", fontSize=7.5,
                textColor=colors.HexColor("#33465e"), leading=10))],
            [Paragraph(_auto, ParagraphStyle(
                "AutoBody", fontName="Helvetica", fontSize=8.5,
                textColor=TXT, leading=12))],
        ]
        _auto_tbl = Table(_auto_cells, colWidths=[CW])
        _auto_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f8fc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c6d2e3")),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(Spacer(1, 0.1 * cm))
        story.append(_auto_tbl)

    sp(0.1)
    if manual_comment:
        story.append(Paragraph(f"<b>{t('comments', lang)}:</b> {manual_comment}", styles["B"]))
    sp(0.1)

    # Bewust de ANALYSEDATUM: dit is het handtekeningblok, en het label is
    # "Datum" — de dag waarop dit rapport is opgemaakt. De opnamedatum staat
    # bovenaan en komt uit `recording_start`; zie _recording_date().
    report_date=(meta.get("analysis_timestamp","—") or "—")[:10]
    scorer=str(pat.get("scorer","—") or "—")
    sig=Table([[Paragraph(f"<b>{t('pdf_scorer',lang)}</b> {scorer}",styles["B"]),
                Paragraph(f"<b>{t('physician',lang)}:</b> _________________________",styles["B"]),
                Paragraph(f"<b>{t('date',lang)}:</b> {report_date}",styles["B"])]],
              colWidths=[CW/3]*3)
    sig.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("BOX",(0,0),(-1,-1),0.4,GRID),("BACKGROUND",(0,0),(-1,-1),BGROW)]))
    story.append(sig); sp(0.15)

    # ── v0.8.37: ESS + OSAS severity profile ─────────────────
    ess_value = pat.get("ess")  # None if not provided by clinician
    try:
        ess_value = int(ess_value) if ess_value is not None else None
    except (ValueError, TypeError):
        ess_value = None
    try:
        draw_ess_section(story, results=pneumo, ess=ess_value, t=t)
    except Exception:
        pass
    sp(0.15)

    # ── DISCLAIMER ─────────────────────────────────────────────
    story.append(HRFlowable(width="100%",thickness=0.3,color=GRID)); sp(0.1)

    # v0.8.11: verificatie-status in disclaimer (meertalig)
    verified_by   = pat.get("verified_by", "").strip()
    verified_role = pat.get("verified_role", "").strip()
    if verified_by and verified_role:
        role_label = {"technicus": t("pdf_role_tech",lang), "arts": t("pdf_role_physician",lang)}.get(verified_role, verified_role)
        story.append(Paragraph(
            f"<b>{t('pdf_verified_by',lang).format(role=role_label, name=verified_by)}</b>",
            styles["B"]))
        sp(0.1)

    disc_text = t("pdf_disc_auto", lang).format(version=_APP_VERSION) + " "
    if verified_by and verified_role:
        disc_text += t("pdf_disc_verified", lang).format(role=role_label, name=verified_by)
    else:
        disc_text += t("pdf_disc_screening", lang)
    story.append(Paragraph(disc_text, styles["D"]))

    doc.build(story,onFirstPage=on1,onLaterPages=onN)
    return output_path
