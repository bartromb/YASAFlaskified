"""generate_profile_report.py — het profielrapport, een tweede PDF.

Implementeert §5 van YF_PROFIEL_PDF_SPEC.md. Dit document beschrijft één nacht
onder meerdere regelsets; het klinische rapport blijft onaangeraakt.

WAAROM DIT EEN APART DOCUMENT IS

De profieltabel is in v0.15.0 bewust uit het klinische rapport gehaald omdat ze
niet als ernstmaat gevalideerd is. Die beslissing terugdraaien als bijeffect van
een rapportagevraag zou de verkeerde keuze zijn. Dus: een eigen document, met
een eigen bestandsnaam, en op elke pagina de markering dat het onderzoek is.

Dat laatste is geen formaliteit. Twee PDF's per opname betekent dat er één de
verkeerde kant op kan, en een document met vijf verschillende AHI's voor
dezelfde nacht is in een patiëntendossier of bij een verwijzer een risico dat
geen technische maatregel wegneemt.

WAT DIT DOCUMENT NIET DOET

Geen "beste profiel", geen kleurcodering op de Δ-kolom, geen conclusie. De
matrix beschrijft; de onderzoeker kiest. Een groene rij is een klinische
uitspraak die dit rapport niet doet.
"""
from __future__ import annotations

from profile_matrix import MISSING, build_matrix, fmt, fmt_delta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

__all__ = ["generate_profile_report"]

_GREY = colors.HexColor("#555555")
_LINE = colors.HexColor("#BBBBBB")
_HEADBG = colors.HexColor("#EEEEEE")

_BANNER = ("ONDERZOEKSDOCUMENT — niet voor klinische besluitvorming. "
           "Het klinische rapport van deze opname is een apart document.")

# Menselijke overeenkomst op PSG-IPA: twaalf onafhankelijk scorende mensen per
# opname, 66 paren per opname, gemeten met exact deze matcher en drempel
# (19-08-2026). Dit staat in het rapport omdat een Jaccard zonder schaal als
# oordeel wordt gelezen: 0,5 tussen twee profielen lijkt weinig tot je ziet dat
# twee mensen mediaan op 0,385 zitten.
#
# Context, geen norm. Vijf opnames is een kleine set en PSG-IPA is één cohort
# met zijn eigen scoringsconventies.
_HUMAN_REF = [
    ("SN1", "27–38", 0.703, "0,561–0,865"),
    ("SN2", "8–33", 0.378, "0,167–0,606"),
    ("SN3", "273–339", 0.902, "0,779–0,965"),
    ("SN4", "1–38", 0.382, "0,026–0,691"),
    ("SN5", "25–101", 0.385, "0,141–0,580"),
]
_HUMAN_MEDIAN = 0.385


def _styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("pr_h1", parent=ss["Heading1"], fontSize=15,
                             spaceAfter=4),
        "h2": ParagraphStyle("pr_h2", parent=ss["Heading2"], fontSize=11.5,
                             spaceBefore=12, spaceAfter=4),
        "body": ParagraphStyle("pr_body", parent=ss["BodyText"], fontSize=8.5,
                               leading=11.5),
        "note": ParagraphStyle("pr_note", parent=ss["BodyText"], fontSize=7.5,
                               leading=10, textColor=_GREY),
        "cell": ParagraphStyle("pr_cell", parent=ss["BodyText"], fontSize=7.5,
                               leading=9.5),
    }


def _page_furniture(canvas, doc):
    """Markering op ELKE pagina, niet alleen de eerste.

    Een PDF wordt doorgestuurd, geprint en uit zijn context gehaald; een
    banner die alleen op pagina 1 staat beschermt pagina 2 niet.
    """
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(colors.HexColor("#8A4B00"))
    canvas.drawString(2 * cm, A4[1] - 1.05 * cm, _BANNER)
    canvas.setStrokeColor(_LINE)
    canvas.line(2 * cm, A4[1] - 1.25 * cm, A4[0] - 2 * cm, A4[1] - 1.25 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_GREY)
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"pagina {doc.page}")
    canvas.restoreState()


def _table(data, widths, styles_extra=None):
    t = Table(data, colWidths=widths, repeatRows=1)
    base = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADBG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.25, _LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    t.setStyle(TableStyle(base + list(styles_extra or [])))
    return t


def _label(row):
    """Rijlabel uit de registry, met de merktekens die de spec voorschrijft.

    De specificatie schrijft ▶ voor. Dat teken bestaat niet in de base-14
    Helvetica die ReportLab standaard gebruikt: het rendert als een blokje —
    geverifieerd door het te zetten en terug te lezen, niet aangenomen op
    `stringWidth`, die ook voor ontbrekende glyphs een breedte teruggeeft.
    `»`, `●` en `▲` renderen wél. Het merkteken hoort leesbaar te zijn, dus
    hier `»`; de specificatie is hierop bijgesteld.
    """
    name = row["display_name"]
    if row["is_primary"]:
        name = f"<b>» {name}</b>"
    if row["is_frozen"]:
        name = f"{name} [bevroren]"
    return name


# ── §A — indexmatrix ────────────────────────────────────────────────────

def _section_a(matrix, st):
    out = [Paragraph("A. Indexmatrix", st["h2"])]
    rows = matrix["rows"]
    prim = next((r for r in rows if r["is_primary"]), None)
    head = [["Profiel", "Regelset", "AHI", "OAHI", "CAI", "n events",
             "RDI", "Ernst", "Δ AHI"]]
    body = []
    for r in rows:
        d = (None if prim is None or r["ahi"] is None or prim["ahi"] is None
             else r["ahi"] - prim["ahi"])
        body.append([
            Paragraph(_label(r), st["cell"]),
            Paragraph(r["ruleset"], st["cell"]),
            fmt(r["ahi"]), fmt(r["oahi"]), fmt(r["cai"]),
            fmt(r["n_events"], 0), fmt(r["rdi"]),
            r["severity"], "—" if r["is_primary"] else fmt_delta(d),
        ])
    w = [4.4 * cm, 3.2 * cm, 1.3 * cm, 1.3 * cm, 1.2 * cm, 1.5 * cm,
         1.3 * cm, 2.0 * cm, 1.4 * cm]
    extra = [("ALIGN", (2, 1), (-1, -1), "RIGHT")]
    for i, r in enumerate(rows, start=1):
        if r["is_primary"]:
            extra.append(("BACKGROUND", (0, i), (-1, i),
                          colors.HexColor("#F4F4F4")))
    out.append(_table(head + body, w, extra))
    return out


# ── §B — eventovereenkomst ──────────────────────────────────────────────

def _section_b(comparison, primary, st):
    out = [Paragraph("B. Eventovereenkomst met het primaire profiel",
                     st["h2"])]
    pairs = [(n, d["agreement_vs_primary"])
             for n, d in sorted(comparison.items())
             if n != "_meta" and isinstance(d, dict)
             and d.get("agreement_vs_primary")]
    if not pairs:
        out.append(Paragraph(
            "Geen overeenkomstgegevens in deze vergelijking. Dat is iets "
            "anders dan “geen verschillen”: zonder eventlijsten kan de vraag "
            "niet gesteld worden.", st["note"]))
        return out

    out.append(Paragraph(
        "Gepaard op <b>onset_s</b> en <b>duration_s</b> met IoU ≥ 0,20, "
        "dezelfde drempel als de validatieharness. Jaccard 1,00 betekent "
        "dezelfde events; een gelijke AHI uit een lagere Jaccard betekent "
        "andere events die op hetzelfde getal uitkomen.", st["body"]))
    out.append(Spacer(1, 3))

    head = [["Profiel", "n", "gedeeld", "alleen primair", "alleen dit",
             "Jaccard", "med. IoU", "herlabeld"]]
    body = []
    for name, a in pairs:
        body.append([
            Paragraph(name, st["cell"]),
            str(a["n_b"]), str(a["n_shared"]), str(a["n_only_a"]),
            str(a["n_only_b"]),
            fmt(a["jaccard"], 3), fmt(a["median_iou"], 3),
            str(a["n_type_changed"]),
        ])
    w = [4.6 * cm, 1.1 * cm, 1.6 * cm, 2.4 * cm, 1.9 * cm, 1.6 * cm,
         1.7 * cm, 1.8 * cm]
    out.append(_table(head + body, w,
                      [("ALIGN", (1, 1), (-1, -1), "RIGHT")]))

    # De twee uncertain-klassen, expliciet gemaakt.
    out.append(Spacer(1, 6))
    head2 = [["Profiel", "Jaccard incl. “uncertain”", "excl.",
              "kale uncertain: primair / dit"]]
    body2 = []
    for name, a in pairs:
        x = a.get("excl_bare_uncertain") or {}
        bu = a.get("n_bare_uncertain") or {}
        body2.append([
            Paragraph(name, st["cell"]),
            fmt(a["jaccard"], 3), fmt(x.get("jaccard"), 3),
            f"{bu.get('a', MISSING)} / {bu.get('b', MISSING)}",
        ])
    out.append(_table(head2 + body2,
                      [4.6 * cm, 5.0 * cm, 2.4 * cm, 4.7 * cm],
                      [("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
    out.append(Spacer(1, 4))
    out.append(Paragraph(
        "Kale <i>uncertain</i> valt buiten <b>ahi_total</b>, terwijl "
        "<i>hypopnea_uncertain</i> gewoon meetelt. De eventlijst bevat dus "
        "events die de index niet telt: een rij met meer events dan de AHI "
        "doet vermoeden is geen tegenspraak. Beide varianten staan hierboven "
        "zodat de keuze zichtbaar is in plaats van opgelegd.", st["note"]))

    # De schaal. Zonder deze cijfers is een Jaccard een getal zonder betekenis.
    out.append(Spacer(1, 8))
    out.append(Paragraph("Hoeveel zijn mensen het onderling eens?", st["h2"]))
    out.append(Paragraph(
        "Dezelfde matcher en drempel, toegepast op PSG-IPA: twaalf "
        "onafhankelijke scorers per opname, 66 paren per opname.", st["body"]))
    out.append(Spacer(1, 3))
    href = [["Opname", "events per scorer", "Jaccard mediaan", "spreiding"]]
    for sn, ev, med, rng in _HUMAN_REF:
        href.append([sn, ev, f"{med:.3f}".replace(".", ","), rng])
    out.append(_table(href, [2.6 * cm, 4.6 * cm, 4.2 * cm, 4.6 * cm],
                      [("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
    out.append(Spacer(1, 4))
    out.append(Paragraph(
        f"<b>Mediaan over de vijf opnames: "
        f"{('%.3f' % _HUMAN_MEDIAN).replace('.', ',')}.</b> Een Jaccard van "
        f"0,5 tussen twee profielen is dus geen tekortkoming van het "
        f"algoritme: twee mensen op dezelfde nacht halen mediaan minder. "
        f"Let daarbij op de eventdichtheid — SN3 heeft honderden events en "
        f"0,902, SN4 hooguit enkele tientallen en 0,382 met paren tot 0,026. "
        f"Bij weinig events domineert één meningsverschil de maat, en "
        f"Jaccards van verschillende opnames zijn daarom niet zonder meer "
        f"vergelijkbaar.", st["note"]))
    out.append(Paragraph(
        "Deze referentie is context, geen norm: vijf opnames is een kleine "
        "set en PSG-IPA is één cohort met zijn eigen scoringsconventies.",
        st["note"]))

    # Herlabeling: hetzelfde event, ander oordeel.
    changes = [(n, a["type_changes"]) for n, a in pairs if a.get("type_changes")]
    if changes:
        out.append(Spacer(1, 6))
        out.append(Paragraph("Gepaard maar anders geclassificeerd", st["h2"]))
        rows3 = [["Profiel", "Verschuiving", "n"]]
        for name, ch in changes:
            for k, v in ch.items():
                rows3.append([Paragraph(name, st["cell"]),
                              Paragraph(k.replace("->", "→"), st["cell"]),
                              str(v)])
        out.append(_table(rows3, [4.6 * cm, 9.0 * cm, 1.4 * cm],
                          [("ALIGN", (2, 1), (-1, -1), "RIGHT")]))
        out.append(Spacer(1, 3))
        out.append(Paragraph(
            "Deze events zijn door beide profielen gevonden, maar niet gelijk "
            "beoordeeld. Een indextabel maakt dat volledig onzichtbaar.",
            st["note"]))
    return out


# ── §C — sensorherkomst ─────────────────────────────────────────────────

def _section_c(comparison, st):
    meta = comparison.get("_meta") or {}
    flow = meta.get("flow_channels") or {}
    out = [Paragraph("C. Sensorherkomst per profiel", st["h2"])]
    if not flow:
        out.append(Paragraph(
            "Niet vastgelegd in deze vergelijking.", st["note"]))
        return out

    out.append(Paragraph(
        "De thermistorpoort beslist <b>per opname</b> of apneus op de "
        "thermistor of op de neusdruk gescoord worden. Verschilt een profiel "
        "van het primaire omdat die poort omsloeg, dan is dát de verklaring.",
        st["body"]))
    out.append(Spacer(1, 3))

    head = [["Profiel", "Apneu-sensor", "Hypopneu-sensor", "Duaal",
             "Thermistor afgekeurd"]]
    body, reasons = [], {}
    for name in sorted(k for k in flow):
        f = flow[name] or {}
        rej = f.get("thermistor_rejected")
        chk = f.get("thermistor_check") or {}
        if chk.get("reason"):
            reasons[name] = chk["reason"]
        body.append([
            Paragraph(name, st["cell"]),
            Paragraph(str(f.get("apnea_sensor") or MISSING), st["cell"]),
            Paragraph(str(f.get("hypopnea_sensor") or MISSING), st["cell"]),
            "ja" if f.get("dual_sensor") else "nee",
            Paragraph(str(rej) if rej else MISSING, st["cell"]),
        ])
    out.append(_table(head + body,
                      [4.2 * cm, 3.2 * cm, 3.4 * cm, 1.4 * cm, 4.5 * cm]))
    if reasons:
        out.append(Spacer(1, 4))
        out.append(Paragraph(
            "Aanwezig-maar-afgekeurd is iets anders dan afwezig; het oordeel "
            "van de poort staat er letterlijk bij:", st["note"]))
        for name, r in reasons.items():
            out.append(Paragraph(f"• <b>{name}</b>: {r}", st["note"]))
    return out


# ── §D — herkomst en caveats ────────────────────────────────────────────

def _section_d(pneumo, comparison, matrix, st):
    meta = comparison.get("_meta") or {}
    out = [Paragraph("D. Herkomst en voorbehouden", st["h2"])]

    wall = meta.get("wall_clock_s") or {}
    rows = [["psgscoring", str(meta.get("psgscoring_version") or MISSING)],
            ["Primair profiel", str(meta.get("primary_profile") or MISSING)],
            ["Vergeleken profielen",
             str(len(meta.get("profiles_compared") or []))],
            ["Gedeeld hypnogram",
             "ja" if meta.get("hypnogram_shared") else "nee"],
            ["Rekentijd totaal",
             f"{sum(wall.values()):.0f} s ({sum(wall.values())/60:.1f} min)"
             if wall else MISSING]]
    out.append(_table([["Veld", "Waarde"]] + rows, [5.0 * cm, 11.0 * cm]))

    if wall:
        out.append(Spacer(1, 6))
        out.append(Paragraph("Rekentijd per profiel", st["h2"]))
        wr = [["Profiel", "seconden"]] + [
            [Paragraph(k, st["cell"]), f"{v:.1f}"]
            for k, v in sorted(wall.items(), key=lambda kv: -kv[1])]
        out.append(_table(wr, [8.0 * cm, 3.0 * cm],
                          [("ALIGN", (1, 1), (-1, -1), "RIGHT")]))

    notes = []
    fn = matrix.get("footnotes") or {}
    notes.append("Alle rijen beschrijven <b>dezelfde opname met dezelfde "
                 "kanalen en hetzelfde hypnogram</b>. Dat is wat de "
                 "vergelijking betekenisvol maakt.")
    notes.append("Het hoofdresultaat en het klinische besluit volgen "
                 f"uitsluitend <b>{matrix.get('primary') or MISSING}</b>.")
    if fn.get("rdi_missing"):
        notes.append("“—” in de RDI-kolom betekent dat de RERA-tak onder dat "
                     "profiel niet draaide — niet dat de RDI nul is.")
    if fn.get("experimental_present"):
        notes.append("Exploratieve profielen zijn <b>niet gevalideerd voor "
                     "klinisch gebruik</b>. Sommige zijn tegen menselijke "
                     "scoring gemeten en afgewezen.")
    if fn.get("frozen_present"):
        notes.append("Bevroren profielen zijn reproductieprofielen voor "
                     "gepubliceerde analyses; hun indices zijn buiten die "
                     "context betekenisloos.")
    if matrix.get("primary_mismatch"):
        pm = matrix["primary_mismatch"]
        notes.append(f"<b>WAARSCHUWING:</b> de rij van het primaire profiel "
                     f"({pm.get('matrix')}) wijkt af van het hoofdresultaat "
                     f"({pm.get('head')}). Dat hoort niet te kunnen; "
                     f"behandel deze vergelijking met voorbehoud.")
    caveat = ((pneumo.get("respiratory") or {}).get("summary") or {}).get(
        "ahi_rem_caveat")
    if caveat:
        notes.append(f"REM-AHI: {caveat}")

    out.append(Spacer(1, 6))
    for n in notes:
        out.append(Paragraph(f"• {n}", st["note"]))
    out.append(Spacer(1, 8))
    out.append(Paragraph(
        "Dit document doet geen uitspraak over welk profiel beter is. Er is "
        "bewust geen kleurcodering en geen aanbeveling: de matrix beschrijft, "
        "de onderzoeker kiest.", st["note"]))
    return out


def generate_profile_report(pneumo: dict, comparison: dict, output_path: str,
                            *, job_id: str = "", lang: str = "nl") -> str:
    """Bouw het profielrapport en schrijf het naar ``output_path``."""
    st = _styles()
    matrix = build_matrix(pneumo or {}, comparison or {})

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.9 * cm, bottomMargin=1.8 * cm,
        title=f"Profielrapport {job_id}".strip(),
        author="YASAFlaskified")

    story = [
        Paragraph("Profielrapport", st["h1"]),
        Paragraph(
            f"Opname <b>{job_id or MISSING}</b> · primair profiel "
            f"<b>{matrix.get('primary') or MISSING}</b> · "
            f"{len((comparison.get('_meta') or {}).get('profiles_compared') or [])}"
            f" profielen vergeleken", st["body"]),
        Spacer(1, 8),
        Paragraph(
            "Dit document toont één nacht onder meerdere regelsets. Het "
            "klinische rapport en het klinische besluit volgen uitsluitend het "
            "primaire profiel; de overige rijen zijn dezelfde opname onder een "
            "andere regelset of methode.", st["body"]),
        Spacer(1, 6),
    ]
    story += _section_a(matrix, st)
    story.append(Spacer(1, 8))
    story += _section_b(comparison or {}, matrix.get("primary"), st)
    story.append(PageBreak())
    story += _section_c(comparison or {}, st)
    story.append(Spacer(1, 10))
    story += _section_d(pneumo or {}, comparison or {}, matrix, st)

    doc.build(story, onFirstPage=_page_furniture, onLaterPages=_page_furniture)
    return output_path
