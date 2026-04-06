"""
generate_psg_report.py — Klinisch PSG-rapport conform ASZ Aalst lay-out
Genereert een professioneel A4-landscape verslag met:
  - Patiëntgegevens, opname-info
  - Slaapstadia (hypnogram, tabellen)
  - Respiratoire analyse (AHI, apnea-types, positie)
  - SpO2-analyse
  - Hartritme, PLM, Snurken
  - Diagnose & opmerkingen veld

Gebruik:
    from generate_psg_report import generate_psg_report
    generate_psg_report(results, pneumo, patient_info, output_path)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import io
import os
from datetime import datetime

# ── Kleuren conform referentierapport ──
BLAUW      = colors.HexColor("#1a3a8f")
LICHTBLAUW = colors.HexColor("#4472c4")
TAB_BG     = colors.HexColor("#d0dff5")
TAB_HDR    = colors.HexColor("#1a3a8f")
GRIJS_L    = colors.HexColor("#f2f2f2")
GRIJS_D    = colors.HexColor("#cccccc")
DONKER     = colors.HexColor("#1a1a1a")
WIT        = colors.white

STAGE_COLORS_MPL = {
    "W": "#e74c3c", "N1": "#f39c12", "N2": "#3498db",
    "N3": "#2c3e50", "R": "#8e44ad"
}

PAGE_W, PAGE_H = A4

def _layout_table(cells, col_widths):
    """Layout-hulptabel: geen padding (voorkomt negatieve breedte bij smalle kolommen)."""
    t = Table([cells], colWidths=col_widths)
    t.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    return t

MARGIN = 1.5 * cm
CONTENT_W = PAGE_W - 2 * MARGIN


# ─────────────────────────────────────────────
# STIJLEN
# ─────────────────────────────────────────────

def _styles():
    s = getSampleStyleSheet()
    def add(name, **kw):
        s.add(ParagraphStyle(name, **kw))

    add("PSGTitle",    fontName="Helvetica-Bold",  fontSize=11, textColor=DONKER)
    add("PSGSub",      fontName="Helvetica",        fontSize=8,  textColor=colors.HexColor("#444"))
    add("PSGLabel",    fontName="Helvetica-Bold",   fontSize=7.5,textColor=DONKER)
    add("PSGVal",      fontName="Helvetica",         fontSize=7.5,textColor=DONKER)
    add("PSGSecHead",  fontName="Helvetica-Bold",   fontSize=9,  textColor=WIT,
        spaceBefore=4, spaceAfter=2)
    add("PSGSmall",    fontName="Helvetica",         fontSize=6.5,textColor=colors.HexColor("#555"))
    add("PSGFooter",   fontName="Helvetica",         fontSize=6,  textColor=colors.HexColor("#888"),
        alignment=TA_CENTER)
    add("PSGDiag",     fontName="Helvetica-Oblique", fontSize=8,  textColor=DONKER, leading=12)
    return s


def _s():
    return _styles()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def v(d, *keys, default="—", suffix="", dec=1):
    try:
        x = d
        for k in keys:
            x = x[k]
        if x is None:
            return default
        if isinstance(x, float):
            return f"{round(x, dec)}{suffix}"
        return f"{x}{suffix}"
    except (KeyError, TypeError, IndexError):
        return default


def sec_header(title, width=None):
    w = width or CONTENT_W
    t = Table([[Paragraph(f"<b>{title}</b>",
                ParagraphStyle("_sh", fontName="Helvetica-Bold",
                               fontSize=8.5, textColor=WIT))]], colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLAUW),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ]))
    return t


def simple_table(headers, rows, col_widths, stripe=True, small=False):
    # Filter None waarden uit col_widths
    col_widths = [w if w is not None else 2*cm for w in col_widths]
    # Filter lege rows
    rows = [r for r in rows if r]
    if not rows:
        rows = [["—"] * len(headers)]
    fs = 7 if small else 8
    style = [
        ("BACKGROUND",    (0,0),(-1,0),  BLAUW),
        ("TEXTCOLOR",     (0,0),(-1,0),  WIT),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), fs),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("GRID",          (0,0),(-1,-1), 0.3, GRIJS_D),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
    ]
    if stripe:
        style.append(("ROWBACKGROUNDS", (0,1),(-1,-1), [WIT, GRIJS_L]))
    return Table([headers] + rows, colWidths=col_widths,
                 style=TableStyle(style))


def _fmt(val, suffix="", dec=1):
    if val is None:
        return "—"
    try:
        return f"{round(float(val), dec)}{suffix}"
    except Exception:
        return str(val)


# ─────────────────────────────────────────────
# MATPLOTLIB FIGUREN → ReportLab Images
# ─────────────────────────────────────────────

def _fig_to_rl_image(fig, width_cm=18, height_cm=4):
    """Converteer matplotlib Figure naar ReportLab Image (via PNG buffer)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)


def build_hypnogram_figure(hypno: list, width_cm=26, height_cm=3.5, lang="nl"):
    """Hypnogram plot conform AASM standaard: W bovenaan, REM onderaan."""
    # AASM standaard volgorde (boven → onder)
    stage_map = {"W": 0, "N1": 1, "N2": 2, "N3": 3, "R": 4}

    yvals = [stage_map.get(s, 0) for s in hypno]
    times = np.arange(len(hypno)) * 0.5   # minuten

    fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54), dpi=180)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")

    # Stap-lijn (fijn)
    ax.step(times, yvals, where="post", color="#1a3a5c", linewidth=0.6)

    # Subtiele kleurbanden per stadium
    stage_colors = {"W": "#e74c3c", "N1": "#f39c12", "N2": "#2980b9",
                    "N3": "#1a3a8f", "R": "#8e44ad"}
    for i, (s, yv) in enumerate(zip(hypno, yvals)):
        ax.fill_between([i*0.5, (i+1)*0.5], [yv-0.42, yv-0.42], [yv+0.42, yv+0.42],
                        color=stage_colors.get(s, "#ccc"), alpha=0.30, linewidth=0)

    # Y-as: W bovenaan, REM onderaan
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_yticklabels(["W", "N1", "N2", "N3", "REM"], fontsize=7,
                       color="#1a3a5c", fontweight="600")
    ax.set_ylim(-0.7, 4.7)
    ax.invert_yaxis()

    # X-as
    from i18n import t as _t
    ax.set_xlabel(_t("pdf_time_axis", lang), fontsize=7, color="#6b7a99")
    ax.tick_params(axis="x", labelsize=6)
    ax.set_xlim(0, len(hypno) * 0.5)

    # Fijne horizontale lijnen
    for yy in [0, 1, 2, 3, 4]:
        ax.axhline(yy, color="#e0e6ed", linewidth=0.3, zorder=0)
    ax.grid(axis="x", color="#e0e6ed", linewidth=0.3)

    # Spines
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines["left"].set_linewidth(0.4); ax.spines["left"].set_color("#b0b8c4")
    ax.spines["bottom"].set_linewidth(0.4); ax.spines["bottom"].set_color("#b0b8c4")
    ax.tick_params(axis="both", length=2, width=0.4, color="#b0b8c4")

    fig.tight_layout(pad=0.3)
    return _fig_to_rl_image(fig, width_cm, height_cm)


def build_spo2_figure(spo2_summary: dict, width_cm=10, height_cm=4):
    """SpO2 balk als percentage-histogram."""
    fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54))
    pcts = {
        "≥95%":  100 - float(spo2_summary.get("pct_below_90") or 0),
        "90-95%": float(spo2_summary.get("pct_below_90") or 0)
             - float(spo2_summary.get("pct_below_80") or 0),
        "<90%":   float(spo2_summary.get("pct_below_90") or 0),
        "<80%":   float(spo2_summary.get("pct_below_80") or 0),
    }
    colors_bar = ["#27ae60", "#f39c12", "#e67e22", "#c0392b"]
    bars = ax.barh(list(pcts.keys()), list(pcts.values()),
                   color=colors_bar, height=0.5)
    ax.set_xlabel("% Slaaptijd", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.set_xlim(0, 100)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout(pad=0.3)
    return _fig_to_rl_image(fig, width_cm, height_cm)


def build_stage_pie(stage_pcts: dict, width_cm=5, height_cm=4):
    """Taartdiagram slaapstadia."""
    labels = []
    sizes  = []
    clrs   = []
    for stage, col in [("W","#e74c3c"),("N1","#f39c12"),("N2","#3498db"),
                       ("N3","#2c3e50"),("R","#8e44ad")]:
        val = stage_pcts.get(stage, stage_pcts.get(f"{stage} (%)", 0)) or 0
        try:
            val = float(val)
        except Exception:
            val = 0
        if val > 0:
            labels.append(stage)
            sizes.append(val)
            clrs.append(col)

    if not sizes:
        sizes  = [25, 10, 40, 15, 10]
        labels = ["W","N1","N2","N3","R"]
        clrs   = ["#e74c3c","#f39c12","#3498db","#2c3e50","#8e44ad"]

    fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54))
    ax.pie(sizes, labels=labels, colors=clrs, autopct="%1.0f%%",
           textprops={"fontsize": 6}, startangle=90)
    fig.tight_layout(pad=0.2)
    return _fig_to_rl_image(fig, width_cm, height_cm)


# ─────────────────────────────────────────────
# HOOFD GENERATOR
# ─────────────────────────────────────────────

def generate_psg_report(
    yasa_results:  dict,
    pneumo_results: dict,
    patient_info:  dict,
    output_path:   str,
    institution:   dict = None,
) -> str:
    """
    Genereer volledig PSG-rapport.

    Parameters
    ----------
    yasa_results   : uitvoer van run_full_analysis()
    pneumo_results : uitvoer van run_pneumo_analysis()
    patient_info   : dict met patient_name, dob, patient_id, bmi,
                     weight_kg, height_cm, recording_date
    output_path    : pad voor het PDF-bestand
    institution    : dict met name, department, address, city,
                     tel, fax, email, web  (optioneel)

    Returns
    -------
    str — output_path
    """
    styles = _styles()

    # v0.8.11: taal vroeg bepalen zodat alle subfuncties hem kunnen gebruiken
    from i18n import t as _t_func
    _site_for_lang = institution or {}
    lang = (
        (patient_info or {}).get("lang")
        or _site_for_lang.get("language", "nl")
        or "nl"
    )

    if institution is None:
        institution = {
            "name":       "Slaapkliniek AZORG",
            "department": "YASAFlaskified",
            "address":    "",
            "city":       "",
            "tel":        "",
            "web":        "www.slaapkliniek.be",
        }

    # v0.8.11: custom header/logo uit patient_info (via rapport editor)
    pat_hdr = patient_info or {}
    if pat_hdr.get("report_header_name"):
        institution["name"] = pat_hdr["report_header_name"]
    if pat_hdr.get("report_header_address"):
        institution["address"] = pat_hdr["report_header_address"]
    if pat_hdr.get("report_header_phone"):
        institution["tel"] = pat_hdr["report_header_phone"]

    doc = SimpleDocTemplate(
        output_path,
        pagesize      = A4,
        leftMargin    = MARGIN, rightMargin  = MARGIN,
        topMargin     = 1.8*cm, bottomMargin = 1.5*cm,
    )

    story = []
    sp    = lambda n=0.15: story.append(Spacer(1, n*cm))

    # ═══════════════════════════════════════════════════
    # PAGINA 1 — Patiëntdata + Slaap + Respiratoir
    # ═══════════════════════════════════════════════════

    # ── HEADER (institution + patient) ──────────────────
    # v0.8.11: logo naast institution naam
    _logo_path = None
    if pat_hdr.get("report_logo_path"):
        _lp = os.path.join(os.path.dirname(__file__), "static", "logos",
                           pat_hdr["report_logo_path"])
        if os.path.exists(_lp):
            _logo_path = _lp
    if not _logo_path:
        _lp = os.path.join(os.path.dirname(__file__), "static", "AZORG_rood.png")
        if os.path.exists(_lp):
            _logo_path = _lp

    inst_lines = []
    if _logo_path:
        try:
            inst_lines.append(Image(_logo_path, width=2.2*cm, height=1.0*cm))
        except Exception:
            pass
    inst_lines.append(
        Paragraph(f"<b>{institution['name']}</b>",
                  ParagraphStyle("_ih", fontName="Helvetica-Bold", fontSize=10, textColor=BLAUW)))
    inst_lines.append(
        Paragraph(institution.get("department",""),
                  ParagraphStyle("_is", fontName="Helvetica-Bold", fontSize=8.5)))
    for k in ["tel","fax","web"]:
        v_inst = institution.get(k,"")
        if v_inst:
            inst_lines.append(Paragraph(
                f"{k.capitalize()}: {v_inst}",
                ParagraphStyle("_il", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#444"))))

    pat  = patient_info
    meas = pat.get("recording_date","—")

    pat_tbl = simple_table(
        ["", ""],
        [
            [Paragraph("<b>Last Name:</b>",  styles["PSGLabel"]),
             Paragraph(pat.get("patient_name","—").split(",")[0] if "," in pat.get("patient_name","") else pat.get("patient_name","—"), styles["PSGVal"])],
            [Paragraph("<b>First Name:</b>", styles["PSGLabel"]),
             Paragraph(pat.get("patient_name","—").split(",")[1].strip() if "," in pat.get("patient_name","") else "", styles["PSGVal"])],
            [Paragraph("<b>Date of Birth:</b>", styles["PSGLabel"]),
             Paragraph(pat.get("dob","—"), styles["PSGVal"])],
            [Paragraph("<b>ID:</b>",          styles["PSGLabel"]),
             Paragraph(pat.get("patient_id","—"), styles["PSGVal"])],
        ],
        col_widths=[2.8*cm, 4.5*cm],
        stripe=False,
    )
    bmi_tbl = simple_table(
        ["", ""],
        [
            [Paragraph("<b>Height:</b>", styles["PSGLabel"]),
             Paragraph(f"{pat.get('height_cm','—')} cm", styles["PSGVal"])],
            [Paragraph("<b>Weight:</b>", styles["PSGLabel"]),
             Paragraph(f"{pat.get('weight_kg','—')} kg", styles["PSGVal"])],
            [Paragraph("<b>BMI:</b>",    styles["PSGLabel"]),
             Paragraph(f"{pat.get('bmi','—')} kg/m²",    styles["PSGVal"])],
        ],
        col_widths=[2.2*cm, 3*cm],
        stripe=False,
    )

    pat_bmi_row = _layout_table(
        [pat_tbl, "", bmi_tbl],
        [7.5*cm, 0.3*cm, 5.5*cm])
    patient_block = Table([
        [Paragraph(f"<b>Patient Data</b>",
                   ParagraphStyle("_pth", fontName="Helvetica-Bold",
                                  fontSize=8, textColor=WIT,
                                  backColor=BLAUW))],
        [pat_bmi_row],
    ], colWidths=[13.5*cm])
    header_row = _layout_table(
        [Table([[l] for l in inst_lines], colWidths=[9*cm]),
         "", patient_block],
        [9*cm, 0.5*cm, 13.5*cm])
    story.append(header_row)
    sp(0.3)

    # Opnamegegevens
    rec_tbl = simple_table(
        ["", "From", "To", "Artefact", "Duration"],
        [
            ["Recorded time",
             pat.get("recording_start","—"),
             pat.get("recording_end","—"),
             "—",
             pat.get("duration_recorded","—")],
            ["TIB",
             pat.get("tib_start","—"),
             pat.get("tib_end","—"),
             pat.get("tib_artefact","—"),
             pat.get("tib_duration","—")],
        ],
        col_widths=[3.5*cm, 5*cm, 5*cm, 3*cm, 3*cm],
    )
    story.append(rec_tbl)
    sp(0.3)

    # ── SLAAP SECTIE ────────────────────────────────────
    story.append(sec_header("Sleep"))
    sp(0.2)

    stats   = yasa_results.get("sleep_statistics", {}).get("stats", {})
    staging = yasa_results.get("staging", {})
    hypno   = staging.get("hypnogram", [])

    # Hypnogram figuur
    if hypno:
        story.append(build_hypnogram_figure(hypno, width_cm=27, height_cm=3.2, lang=lang))
        sp(0.2)

    # Slaapstatistieken tabel + stage-tabel naast elkaar
    sleep_left = [
        ["Total Sleep Time (TST)",     v(stats, "TST", suffix=" min")],
        ["Sleep Efficiency [%]",        v(stats, "SE",  suffix="%")],
        ["Sleep Latency [m]",           v(stats, "SOL")],
        ["Sleep Latency N1 [m]",        v(stats, "Lat_N1")],
        ["Sleep Latency N2 [m]",        v(stats, "Lat_N2")],
        ["Deep Sleep Latency [m]",      v(stats, "Lat_N3")],
        ["REM Latency [m]",             v(stats, "Lat_REM")],
        ["Total Sleep Period (SPT)",    v(stats, "SPT", suffix=" min")],
        ["WASO [m]",                    v(stats, "WASO")],
        ["Time in Bed (TIB) [m]",      v(stats, "TIB")],
        ["Sleep Maintenance Eff [%]",   v(stats, "SME", suffix="%")],
    ]

    stage_counts = yasa_results.get("sleep_statistics", {}).get("stage_counts", {})
    tst_min = float(stats.get("TST") or 1)

    def stage_row(label, stage_key):
        dur_min = stage_counts.get(stage_key, 0) * 0.5   # epochs → min
        tib_pct = stage_counts.get(stage_key, 0) * 0.5 / (float(stats.get("TRT_min") or tst_min) or 1) * 100
        slt_pct = dur_min / tst_min * 100 if tst_min > 0 else 0
        h = int(dur_min // 60)
        m = int(dur_min % 60)
        s_fmt = f"{h:02d}:{m:02d}:00"
        return [label, s_fmt, f"{tib_pct:.1f}", f"{slt_pct:.1f}"]

    stage_tbl_rows = [
        stage_row("Artefact",    "Artifact"),
        stage_row("Movement",    "Movement"),
        stage_row("Wake",        "Wake"),
        stage_row("REM",         "REM"),
        stage_row("N1",          "N1"),
        stage_row("N2",          "N2"),
        stage_row("N3",          "N3"),
        ["N4",           "N/A", "0", "0"],
        stage_row("Light Sleep", "N1"),
        stage_row("Deep Sleep",  "N3"),
    ]

    tbl_left = simple_table(
        ["Parameter", "Value"],
        sleep_left,
        col_widths=[5.8*cm, 2.8*cm],
        small=True,
    )
    tbl_stages = simple_table(
        ["Sleep Stage", "Duration", "(%) TIB", "(%) Sleep Time"],
        stage_tbl_rows,
        col_widths=[2.8*cm, 2.2*cm, 1.6*cm, 2.5*cm],
        small=True,
    )
    pie_img = build_stage_pie(stats)

    sleep_row = _layout_table(
        [tbl_left, "", tbl_stages, "", pie_img],
        [8.8*cm, 0.3*cm, 9.4*cm, 0.3*cm, 5.5*cm])
    story.append(sleep_row)
    sp(0.4)

    # ── RESPIRATOIRE SECTIE ──────────────────────────────
    story.append(sec_header("Respiratory"))
    sp(0.2)

    resp_sum     = pneumo_results.get("respiratory", {}).get("summary", {})
    resp_ev      = pneumo_results.get("respiratory", {}).get("events", [])
    ahi          = float(resp_sum.get("ahi_total", 0) or 0)
    oahi         = float(resp_sum.get("oahi", 0) or 0)        # officieel: alle obstr + hypopneas
    oahi60       = float(resp_sum.get("oahi_conf60", oahi) or 0)   # supplementair conf>0.60
    oahi_all     = float(resp_sum.get("oahi_all", oahi) or 0)
    cb           = resp_sum.get("confidence_bands") or {}
    thr          = resp_sum.get("oahi_thresholds")  or {}
    avg_c        = resp_sum.get("avg_classification_confidence")
    avg_s        = f"{avg_c:.2f}" if avg_c else "—"
    arousal_data = pneumo_results.get("arousal", {})
    arousal_sum  = arousal_data.get("summary", {})

    tst_h  = tst_min / 60 if tst_min > 0 else 1
    rem_h  = stage_counts.get("REM", 0) * 0.5 / 60 or 0.001
    nrem_h = (stage_counts.get("N1",0) + stage_counts.get("N2",0)
              + stage_counts.get("N3",0)) * 0.5 / 60 or 0.001

    def _f(d, k):
        v = d.get(k)
        return float(v) if v is not None else None

    # ── Classificatiebalk ────────────────────────────────────────────────
    def _sev(v):
        if v is None: return "—"
        if v < 5:  return "Normaal"
        if v < 15: return "Mild"
        if v < 30: return "Matig"
        return "Ernstig"

    def _sev_clr(v):
        from reportlab.lib import colors as _c
        if v < 5:  return _c.HexColor("#27ae60")
        if v < 15: return _c.HexColor("#f39c12")
        if v < 30: return _c.HexColor("#e67e22")
        return _c.HexColor("#c0392b")

    CW_PSG = PAGE_W - 2*MARGIN
    W = colors.white if hasattr(colors, "white") else colors.HexColor("#ffffff")
    clr = _sev_clr(ahi)
    ab = Table([[Paragraph(
        f"AHI = {ahi:.1f}/u  →  <b>{_sev(ahi)}</b>   |   "
        f"OAHI = {oahi:.1f}/u  →  <b>{_sev(oahi)}</b>",
        ParagraphStyle("PSAB", fontName="Helvetica-Bold", fontSize=9,
                       textColor=W, leading=12))]],
        colWidths=[CW_PSG])
    ab.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), clr),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(ab); sp(0.2)

    # ── Hoofdtabel: events per type × confidence-band ────────────────────
    # Kolommen: Type | n | /u | ★★★≥0.85 | ★★0.60-0.84 | ~0.40-0.59 | ?<0.40
    def _ec(ev_type, band):
        lo = {"high":0.85,"moderate":0.60,"borderline":0.40,"low":0.0}
        hi = {"high":2.0, "moderate":0.85,"borderline":0.60,"low":0.40}
        return sum(1 for e in resp_ev
                   if e.get("type")==ev_type
                   and lo[band] <= (e.get("confidence") or 0) < hi[band])

    def _hc(band):
        lo = {"high":0.85,"moderate":0.60,"borderline":0.40,"low":0.0}
        hi = {"high":2.0, "moderate":0.85,"borderline":0.60,"low":0.40}
        return sum(1 for e in resp_ev
                   if "hypopnea" in (e.get("type") or "")
                   and lo[band] <= (e.get("confidence") or 0) < hi[band])

    def _idx(n): return f"{round(n/tst_h,1)}" if tst_h>0 else "—"

    n_ob = resp_sum.get("n_obstructive", 0) or 0
    n_ce = resp_sum.get("n_central",     0) or 0
    n_mx = resp_sum.get("n_mixed",       0) or 0
    n_hy = resp_sum.get("n_hypopnea",    0) or 0

    conf_rows = [
        ["Obstructief",       str(n_ob), _idx(n_ob),
         str(_ec("obstructive","high")),  str(_ec("obstructive","moderate")),
         str(_ec("obstructive","borderline")), str(_ec("obstructive","low"))],
        ["Centraal",          str(n_ce), _idx(n_ce),
         str(_ec("central","high")),  str(_ec("central","moderate")),
         str(_ec("central","borderline")),    str(_ec("central","low"))],
        ["Gemengd",           str(n_mx), _idx(n_mx),
         str(_ec("mixed","high")),    str(_ec("mixed","moderate")),
         str(_ec("mixed","borderline")),      str(_ec("mixed","low"))],
        ["Hypopnea (Rule 1A/B)", str(n_hy), _idx(n_hy),
         str(_hc("high")), str(_hc("moderate")),
         str(_hc("borderline")), str(_hc("low"))],
        ["A+H totaal",
         str(resp_sum.get("n_ah_total","—")),
         f"{ahi:.1f}", "", "", "", ""],
        ["RERAs",
         str(arousal_sum.get("n_reras",0)),
         _fmt(arousal_sum.get("rera_index")), "", "", "", ""],
    ]
    story.append(simple_table(
        ["Type", "n", "/u", "★★★\n≥0.85", "★★\n0.60–0.84", "~\n0.40–0.59", "?\n<0.40"],
        conf_rows,
        col_widths=[4.0*cm, 1.2*cm, 1.4*cm, 1.6*cm, 1.8*cm, 1.8*cm, 1.6*cm],
        small=True,
    ))
    sp(0.25)

    # ── OAHI drempelgevoeligheidstabel ───────────────────────────────────
    story.append(sec_header("OAHI — drempelgevoeligheid"))
    sp(0.15)
    story.append(Paragraph(
        f"Gem. confidence apneas: <b>{avg_s}</b>  |  "
        f"AHI totaal: {ahi:.1f}/u  |  OAHI alle events: {oahi_all:.1f}/u",
        styles["Normal"]))
    sp(0.15)

    oahi_thr_rows = [
        ["≥ 0.85  (hoge zekerheid)",
         f"{thr.get('0.85','—'):.1f}" if isinstance(thr.get('0.85'),float) else "—",
         _sev(thr.get('0.85') or 0),
         f"{cb.get('high',0)} apneas",
         "Duidelijk patroon"],
        ["≥ 0.60  (matig + hoog)",
         f"{oahi60:.1f}", _sev(oahi60),
         f"{cb.get('high',0)+cb.get('moderate',0)} apneas",
         "Waarschijnlijk correct"],
        ["≥ 0.40  (incl. grensgebied)",
         f"{thr.get('0.40','—'):.1f}" if isinstance(thr.get('0.40'),float) else "—",
         _sev(thr.get('0.40') or 0),
         f"{cb.get('high',0)+cb.get('moderate',0)+cb.get('borderline',0)} apneas",
         "Incl. borderline default"],
        ["Alle events  ← officiële OAHI",
         f"{oahi:.1f}", _sev(oahi),
         f"{n_ob+n_hy} events",
         "AASM-conform"],
    ]
    story.append(simple_table(
        ["Drempel", "OAHI (/u)", "Ernst", "Basis", "Betekenis"],
        oahi_thr_rows,
        col_widths=[4.5*cm, 2.2*cm, 2.0*cm, 3.5*cm, 5.0*cm],
        small=True,
    ))
    sp(0.15)
    story.append(Paragraph(
        "<i>★★★ ≥0.85: duidelijk patroon  "
        "★★ 0.60–0.84: waarschijnlijk correct  "
        "~ 0.40–0.59: borderline default obstructief  "
        "? &lt;0.40: signaalruis/ontbrekende effort</i>",
        styles["Normal"]))
    sp(0.2)

    # ── Duurtijden ───────────────────────────────────────────────────────
    story.append(simple_table(
        ["Parameter", "Waarde"],
        [["Max. apnea-duur",    f"{_fmt(resp_sum.get('max_apnea_dur_s'))} s"],
         ["Gem. apnea-duur",    f"{_fmt(resp_sum.get('avg_apnea_dur_s'))} s"],
         ["Max. hypopnea-duur", f"{_fmt(resp_sum.get('max_hypopnea_dur_s'))} s"],
         ["Gem. hypopnea-duur", f"{_fmt(resp_sum.get('avg_hypopnea_dur_s'))} s"],
         ["Avg desat/event",    f"{_fmt(resp_sum.get('avg_desaturation'))}%"],
         ["Rule 1B reinstated", f"{pneumo_results.get('respiratory',{}).get('rule1b_reinstated',0)}"],
         ["AHI REM",            f"{_fmt(resp_sum.get('ahi_rem'))}/u"],
         ["AHI NREM",           f"{_fmt(resp_sum.get('ahi_nrem'))}/u"],
         ["RDI (AHI+RERA)",     f"{_fmt(arousal_sum.get('rdi','—'))}"],
        ],
        col_widths=[5.0*cm, 3.5*cm],
        small=True,
    ))
    sp(0.3)

    # ═══════════════════════════════════════════════════
    # PAGINA 2 — Positie + SpO2 + Hartritme + PLM + Snurk
    # ═══════════════════════════════════════════════════

    # ── POSITIE ─────────────────────────────────────────
    story.append(sec_header("Position"))
    sp(0.2)

    pos_sum   = pneumo_results.get("position", {}).get("summary", {})
    pos_time  = pos_sum.get("sleep_time_min", {})
    pos_pct   = pos_sum.get("sleep_pct", {})
    pos_ahi   = pos_sum.get("ahi_per_pos", {})
    pos_names = ["Supine", "Left", "Right", "Prone", "Upright"]

    pos_rows = []
    for metric, src in [
        ("RDI",                     pos_ahi),
        ("Obstructive Apnea (Index)", pos_ahi),
        ("Central Apnea (Index)",     {}),
        ("Mixed Apnea (Index)",       {}),
        ("Hypopnea (Index)",          pos_ahi),
        ("Flow Limitation (Index)",   {}),
        ("Sleep Time Fraction [%]",   pos_pct),
        ("RERAs (Index)",             {}),
    ]:
        row = [metric] + [
            _fmt(src.get(p)) if src.get(p) is not None else "0 (0)"
            for p in pos_names
        ] + ["—"]
        pos_rows.append(row)

    tbl_pos = simple_table(
        ["", "Supine", "Left", "Right", "Prone", "Upright", "Not Supine"],
        pos_rows,
        col_widths=[5.5*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm],
        small=True,
    )
    story.append(tbl_pos)
    sp(0.4)

    # ── SpO2 ────────────────────────────────────────────
    story.append(sec_header("O2 Saturation"))
    sp(0.2)

    spo2_sum = pneumo_results.get("spo2", {}).get("summary", {})

    spo2_left_rows = [
        ["Number of Desaturations (Index)",
         f"{spo2_sum.get('n_desaturations','—')} ({_fmt(spo2_sum.get('desat_index'))})"],
        ["Biggest Desaturation [%]",  _fmt(spo2_sum.get("min_spo2"))],
        ["Number desaturations < 90%", _fmt(spo2_sum.get("pct_below_90"), suffix="%")],
        ["Number desaturations < 80%", _fmt(spo2_sum.get("pct_below_80"), suffix="%")],
        ["Average Desaturation [%]",   _fmt(spo2_sum.get("avg_spo2"))],
        ["Minimal SpO2 [%]",           _fmt(spo2_sum.get("min_spo2"))],
        ["Average SpO2 [%]",           _fmt(spo2_sum.get("avg_spo2"))],
        ["Baseline O2 Saturation",     _fmt(spo2_sum.get("baseline_spo2"))],
        ["SpO2 Time < 90%",            f"{_fmt(spo2_sum.get('pct_below_90'), suffix='%')} "
                                       f"{spo2_sum.get('time_below_90','—')}"],
        ["SpO2 Time > 90%",            spo2_sum.get("time_below_90","—")],
    ]
    tbl_spo2_left = simple_table(
        ["Parameter", "Value"],
        spo2_left_rows,
        col_widths=[6*cm, 3*cm],
        small=True,
    )

    # SpO2 figuur
    spo2_img = build_spo2_figure(spo2_sum, width_cm=6, height_cm=3.5)

    spo2_right_rows = [
        ["", "Sleep", "REM", "Non-REM"],
        ["SpO2 Time < 90%",
         str(spo2_sum.get("time_below_90","—")),
         str(spo2_sum.get("rem_time_below_90","—")),
         str(spo2_sum.get("nrem_time_below_90","—"))],
        ["SpO2 Time > 90%", "—", "—", "—"],
        ["Minimal SpO2 [%]", _fmt(spo2_sum.get("min_spo2")), "—", "—"],
        ["Maximal SpO2 [%]", "—", "—", "—"],
    ]
    tbl_spo2_right = Table(
        spo2_right_rows,
        colWidths=[3.5*cm, 2.2*cm, 2.2*cm, 2.2*cm],
        style=TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), BLAUW),
            ("TEXTCOLOR",     (0,0),(-1,0), WIT),
            ("FONTNAME",      (0,0),(-1,-1),"Helvetica"),
            ("FONTSIZE",      (0,0),(-1,-1), 7),
            ("GRID",          (0,0),(-1,-1), 0.3, GRIJS_D),
            ("TOPPADDING",    (0,0),(-1,-1), 2),
            ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ]),
    )

    spo2_layout = _layout_table(
        [tbl_spo2_left, "", spo2_img, "", tbl_spo2_right],
        [9.2*cm, 0.2*cm, 6*cm, 0.2*cm, 10.5*cm])
    story.append(spo2_layout)
    sp(0.4)

    # ── HARTRITME ───────────────────────────────────────
    hr_sum = pneumo_results.get("heart_rate", {}).get("summary", {})
    story.append(sec_header("Heart Rate"))
    sp(0.2)

    hr_rows = [
        ["Average HR [bpm]",     _fmt(hr_sum.get("avg_hr"))],
        ["Minimum HR [bpm]",     _fmt(hr_sum.get("min_hr"))],
        ["Maximum HR [bpm]",     _fmt(hr_sum.get("max_hr"))],
        ["Std. deviation [bpm]", _fmt(hr_sum.get("std_hr"))],
        ["Tachycardia events",   str(hr_sum.get("n_tachycardia","—"))],
        ["Bradycardia events",   str(hr_sum.get("n_bradycardia","—"))],
    ]
    tbl_hr = simple_table(
        ["Parameter", "Value"],
        hr_rows,
        col_widths=[5*cm, 3*cm],
        small=True,
    )
    story.append(tbl_hr)
    sp(0.4)

    # ── PLM ─────────────────────────────────────────────
    plm_data = pneumo_results.get("plm", {})
    plm_sum = plm_data.get("summary", {})
    story.append(sec_header("Periodic Leg Movement (PLM)"))
    sp(0.2)

    if plm_data.get("success") and plm_sum:
        plmi = float(plm_sum.get("plm_index", 0) or 0)
        n_plm = int(plm_sum.get("n_plm", 0) or 0)
        n_series = int(plm_sum.get("n_plm_series", 0) or 0)
        n_resp = int(plm_sum.get("n_resp_associated", 0) or 0)
        n_lm_sleep = int(plm_sum.get("n_lm_sleep", 0) or 0)
        n_lm_wake = int(plm_sum.get("n_lm_wake", 0) or 0)

        plm_rows = [
            ["Totaal LMs",               str(plm_sum.get("n_lm_total", "—"))],
            ["LMs tijdens slaap",        str(n_lm_sleep)],
            ["LMs tijdens wake",         str(n_lm_wake)],
            ["Resp.-geassocieerd (excl.)", str(n_resp)],
            ["PLMs (in serie ≥4)",       str(n_plm)],
            ["PLM-series",               str(n_series)],
            ["LM Index (/u)",            _fmt(plm_sum.get("lm_index"))],
            ["PLM Index (/u)",           _fmt(plm_sum.get("plm_index"))],
            ["PLM Severity",             str(plm_sum.get("plm_severity", "—"))],
        ]
        tbl_plm = simple_table(
            ["Parameter", "Waarde"],
            plm_rows,
            col_widths=[6*cm, 3.5*cm],
            small=True,
        )
        story.append(tbl_plm)
        sp(0.2)

        # ── Klinische bespreking PLM ──
        if plmi >= 15:
            bespreking = (
                f"<b>Bespreking PLM:</b> Er werden {n_plm} periodieke beenbewegingen "
                f"gedetecteerd in {n_series} PLM-series, met een PLM-index van "
                f"{plmi:.1f}/u (klinisch significant, normaal &lt;15/u). "
            )
            if n_resp > 0:
                bespreking += (
                    f"{n_resp} bewegingen waren respiratoir-geassocieerd en werden "
                    "conform AASM 2.6 uitgesloten uit de PLM-telling. "
                )
            if ahi >= 5:
                bespreking += (
                    "Bij gelijktijdig OSAS kunnen PLMs secundair zijn aan respiratoire "
                    "events. Herevaluatie van PLMS na CPAP-instelling is aanbevolen. "
                )
            bespreking += (
                "<br/><b>Aanbeveling:</b> "
                "1) Klinisch screenen op restless legs syndroom (RLS): onweerstaanbare "
                "drang om de benen te bewegen, verergering bij rust, 's avonds/nacht. "
                "2) IJzerstatus controleren (serum ferritine): bij ferritine &lt; 75 µg/L "
                "ijzersuppletie starten. "
                "3) Bij persisterende klachten ondanks adequate ijzerstatus: "
                "dopamine-agonist (pramipexol, ropinirol) of gabapentinoïde "
                "(pregabaline, gabapentine) overwegen."
            )
            story.append(Paragraph(bespreking, styles["PSGVal"]))

        elif plmi >= 5:
            bespreking = (
                f"<b>Bespreking PLM:</b> PLMI {plmi:.1f}/u — licht verhoogd "
                "(normaal &lt;5/u, klinisch significant &gt;15/u). "
            )
            if n_resp > 0:
                bespreking += (
                    f"{n_resp} respiratoir-geassocieerde bewegingen werden uitgesloten. "
                )
            bespreking += (
                "Indien klachten passend bij restless legs syndroom: "
                "serum ferritine controleren."
            )
            story.append(Paragraph(bespreking, styles["PSGVal"]))

        elif n_lm_sleep > 0:
            story.append(Paragraph(
                f"<b>Bespreking PLM:</b> PLMI {plmi:.1f}/u — normaal. "
                f"Er werden {n_lm_sleep} beenbewegingen tijdens slaap gedetecteerd, "
                "maar deze voldoen niet aan de criteria voor klinisch significante PLMS.",
                styles["PSGVal"]))
        else:
            story.append(Paragraph(
                "<b>Bespreking PLM:</b> Geen periodieke beenbewegingen gedetecteerd.",
                styles["PSGVal"]))

    else:
        story.append(Paragraph(
            f"PLM-analyse niet beschikbaar: {plm_data.get('error', 'geen been-EMG kanalen')}. "
            "Opmerking: PLM-detectie vereist tibialis anterior EMG-kanalen (links en/of rechts).",
            styles["PSGVal"]))
    sp(0.4)

    # ── AROUSALS ────────────────────────────────────────
    # arousal_data / arousal_sum already defined in respiratory section
    story.append(sec_header("Arousal Analysis"))
    sp(0.2)

    arousal_rows = [
        ["Arousal Index (/h)",         _fmt(arousal_sum.get("arousal_index"))],
        ["Total Arousals",             str(arousal_sum.get("n_total_arousals", "—"))],
        ["Respiratory Arousals",       str(arousal_sum.get("n_respiratory_arousals", "—"))],
        ["Spontaneous Arousals",       str(arousal_sum.get("n_spontaneous_arousals", "—"))],
        ["% Respiratory",              _fmt(arousal_sum.get("pct_respiratory_arousals"), suffix="%")],
        ["RERAs",                      str(arousal_sum.get("n_reras", 0))],
        ["RERA Index (/h)",            _fmt(arousal_sum.get("rera_index"))],
        ["RDI (AHI + RERA) (/h)",      _fmt(arousal_sum.get("rdi"))],
    ]
    tbl_arousal = simple_table(
        ["Parameter", "Value"],
        arousal_rows,
        col_widths=[5.5*cm, 3.5*cm],
        small=True,
    )
    story.append(tbl_arousal)
    sp(0.4)

    # ── SNURKEN ─────────────────────────────────────────
    snore_sum = pneumo_results.get("snore", {}).get("summary", {})
    story.append(sec_header("Snore Analysis"))
    sp(0.2)

    snore_rows = [
        ["Snore Index",          _fmt(snore_sum.get("snore_index"))],
        ["Absolute Snore [min]", _fmt(snore_sum.get("snore_min"))],
        ["Snore episodic [% TST]", _fmt(snore_sum.get("snore_pct_tst"), suffix="%")],
    ]
    tbl_snore = simple_table(
        ["Parameter", "All"],
        snore_rows,
        col_widths=[5*cm, 3*cm],
        small=True,
    )
    story.append(tbl_snore)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════
    # PAGINA 3 — DIAGNOSE & CONCLUSIE
    # ═══════════════════════════════════════════════════

    story.append(sec_header("Diagnosis"))
    sp(0.4)

    ahi = resp_sum.get("ahi_total", 0) or 0
    oahi = resp_sum.get("oahi", 0) or 0
    severity = resp_sum.get("severity", "unknown")
    spo2_min = spo2_sum.get("min_spo2", "—")
    spo2_pct = spo2_sum.get("pct_below_90", "—")
    plmi = float(plm_sum.get("plm_index", 0) or 0)
    ai = float(arousal_sum.get("arousal_index", 0) or 0)
    rdi = arousal_sum.get("rdi", None)
    se = float(str(stats.get("SE") or 0).replace("%", ""))
    tst = float(str(stats.get("TST") or 0))

    # BMI ophalen
    bmi_raw = patient_info.get("bmi", "")
    try:
        bmi = float(str(bmi_raw).replace(",", "."))
    except (ValueError, TypeError):
        bmi = None

    # ── GESTANDAARDISEERD BESLUIT (v0.8.11: gecentraliseerd) ──
    diag_style = styles["PSGDiag"]
    conclusion_lines = []

    # v0.8.11: taal uit site of patient_info
    from i18n import t
    lang = (patient_info.get("lang") or site.get("language", "nl"))

    from conclusions import generate_conclusions
    spo2_nadir_f = None
    spo2_pct_f = None
    try:
        if spo2_min != "—":
            spo2_nadir_f = float(str(spo2_min))
        if spo2_pct != "—":
            spo2_pct_f = float(str(spo2_pct))
    except (ValueError, TypeError):
        pass

    concl_parts = generate_conclusions(
        ahi=ahi, oahi=oahi, plmi=plmi, se=se, tst=tst, ai=ai,
        bmi=bmi, spo2_nadir=spo2_nadir_f, spo2_pct_below90=spo2_pct_f,
        csr_info=pneumo.get("cheyne_stokes", {}), lang=lang,
    )
    for part in concl_parts:
        conclusion_lines.append(f"<b>{part['title']}</b>")
        conclusion_lines.append(part["body"])
        if part["tx"]:
            conclusion_lines.append(
                f"<b>{t('concl_treatment', lang)}:</b> {part['tx']}")
        conclusion_lines.append("")

    # Handmatig ingevoerde diagnose (overschrijft als ingevuld)
    manual_diag = patient_info.get("diagnosis", "")
    if manual_diag:
        conclusion_lines = [manual_diag]

    for line in conclusion_lines:
        if line:
            story.append(Paragraph(line, diag_style))
            sp(0.1)

    sp(0.5)
    story.append(sec_header("Comments"))
    sp(0.3)
    comments = patient_info.get("comments", "")
    if comments:
        story.append(Paragraph(comments, styles["PSGDiag"]))
    else:
        story.append(Spacer(1, 2*cm))

    # ── SAMENVATTING BALK ──
    sp(0.5)
    story.append(sec_header("Summary"))
    sp(0.2)

    # Arousal severity
    if ai > 25:
        arousal_sev = "severe"
    elif ai > 15:
        arousal_sev = "moderate"
    elif ai > 10:
        arousal_sev = "mild"
    elif ai > 0:
        arousal_sev = "normal"
    else:
        arousal_sev = "—"

    summary_items = [
        ("AHI",    severity),
        ("OAHI",   resp_sum.get("oahi_severity", "—")),
        ("Snore",  "present" if (snore_sum.get("snore_pct_tst") or 0) > 20 else "absent"),
        ("SpO2",   "severe" if (spo2_sum.get("pct_below_90") or 0) > 20 else
                   "mild" if (spo2_sum.get("pct_below_90") or 0) > 5 else "normal"),
        ("PLM",    plm_sum.get("plm_severity", "absent") if plmi > 5 else "absent"),
        ("Arousal", arousal_sev),
        ("Lat/Eff.", "reduced" if se < 85 else "normal"),
    ]
    color_map = {
        "normal": "#27ae60", "absent": "#27ae60",
        "mild":   "#f39c12",
        "moderate":"#e67e22",
        "severe": "#c0392b", "present": "#e67e22",
        "reduced":"#e67e22",
        "—":      "#aaaaaa",
    }
    sum_cells = []
    for label_s, val_s in summary_items:
        col = color_map.get(val_s, "#aaaaaa")
        cell = Table([
            [Paragraph(f"<b>{label_s}</b>",
                       ParagraphStyle("_sl", fontName="Helvetica-Bold",
                                      fontSize=7, textColor=DONKER,
                                      alignment=TA_CENTER))],
            [Paragraph(f"<b>{val_s}</b>",
                       ParagraphStyle("_sv", fontName="Helvetica-Bold",
                                      fontSize=8, textColor=WIT,
                                      alignment=TA_CENTER, backColor=colors.HexColor(col)))],
        ], colWidths=[3.5*cm])
        cell.setStyle(TableStyle([
            ("BOX", (0,0),(-1,-1), 0.5, GRIJS_D),
            ("BACKGROUND", (0,1),(-1,1), colors.HexColor(col)),
            ("TOPPADDING", (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ]))
        sum_cells.append(cell)

    story.append(Table([sum_cells],
                       colWidths=[3.7*cm] * len(sum_cells)))

    # ── FOOTER ──────────────────────────────────────────
    def make_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(colors.HexColor("#888"))
        canvas.line(MARGIN, 1.2*cm, PAGE_W - MARGIN, 1.2*cm)
        # v0.8.11: footer links = patient info, rechts = pagina, midden = versie
        canvas.drawString(MARGIN, 0.9*cm,
            f"{pat.get('patient_name','—')}, {pat.get('recording_date','—')}")
        canvas.drawRightString(PAGE_W - MARGIN, 0.9*cm, f"Pagina {doc.page}")
        # Tweede regel: versie-info (lager, geen overlap)
        canvas.drawString(MARGIN, 0.55*cm,
            "YASAFlaskified v0.8.25 | AASM 2.6 | www.slaapkliniek.be | \u00a9 Bart Rombaut")
        canvas.restoreState()

    doc.build(story, onFirstPage=make_footer, onLaterPages=make_footer)
    return output_path
