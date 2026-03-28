"""
generate_pdf_report.py — YASAFlaskified v0.8.11
Site-config: via config.json["site"] of site_config parameter.
"""
import json, os, io
from datetime import datetime, date
from i18n import t

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image,
)

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
AHI_SEV = [(5,GRN,"Normaal"),(15,ORA,"Mild OSA"),(30,RED,"Matig OSA"),(9999,colors.HexColor("#7b241c"),"Ernstig OSA")]

# ── Site-config ────────────────────────────────────────────────
_DSITE = {"name":"Slaapkliniek AZORG","address":"","phone":"","email":"","logo_path":"AZORG_rood.png","url":"https://www.slaapkliniek.be"}

def _load_site(override=None):
    cfg = dict(_DSITE)
    try:
        for p in [os.path.join(os.path.dirname(__file__),"..","config.json"),"config.json"]:
            if os.path.exists(p):
                with open(p) as f: cfg.update(json.load(f).get("site",{}))
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

def _sev(ahi):
    try: v=float(ahi)
    except: return "—"
    for t,_,l in AHI_SEV:
        if v<t: return l
    return "Ernstig OSA"

def _sev_clr(ahi):
    try: v=float(ahi)
    except: return GR
    for t,c,_ in AHI_SEV:
        if v<t: return c
    return RED

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
            "YASAFlaskified v0.8.11  |  AASM 2.6  |  www.slaapkliniek.be  |  \u00a9 Bart Rombaut")
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
# HOOFD FUNCTIE
# ══════════════════════════════════════════════════════════════
def generate_pdf_report(results:dict, output_path:str,
                        site_config:dict=None, lang:str=None) -> str:
    site=_load_site(site_config)
    styles=_styles()

    # v0.8.11: taal bepalen
    if not lang:
        lang = (results.get("patient_info", {}).get("lang")
                or site.get("language", "nl"))

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

    story=[]; sp=lambda n=0.25:story.append(Spacer(1,n*cm))

    # ── TITEL ──────────────────────────────────────────────────
    sp(0.2)
    story.append(Paragraph("Polysomnografie — Slaaprapport",styles["T"]))
    story.append(Paragraph(f"AASM-scoring via YASA  ·  {site.get('name','SleepAI')}",styles["ST"]))
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
               [t("pdf_sex",lang),str(pat.get("sex","—") or "—")],[t("pdf_bmi",lang),str(pat.get("bmi","—") or "—")]]
    right_rows=[[t("pdf_patient_id",lang),str(pat.get("patient_id","—") or "—")],
                [t("pdf_rec_date",lang),(meta.get("analysis_timestamp","—") or "—")[:10]],
                [t("pdf_duration",lang),_v(meta,"duration_min",fmt="{:.0f}")+" min"],
                [t("pdf_scorer",lang),str(pat.get("scorer","—") or "—")],
                [t("pdf_institution",lang),str(pat.get("institution",site.get("name","")) or "")]]

    pt=Table([[_pm(left_rows),_pm(right_rows)]],colWidths=[CW/2,CW/2])
    pt.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,GRID),
        ("BACKGROUND",(0,0),(-1,-1),BGROW),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8)]))
    story.append(pt); sp(0.3)

    # ── KPI-BALK ───────────────────────────────────────────────
    ahi_v=_f(rsum,"ahi_total"); ahi_s=f"{ahi_v:.1f}" if ahi_v is not None else "—"
    story.append(_kpi([
        (ahi_s, f"AHI  ({_sev(ahi_v)})", "/u", _sev_clr(ahi_v) if ahi_v else GR),
        (_v(stats,"TST",fmt="{:.0f}"),  "TST", "min", NAVY),
        (_v(stats,"SE",fmt="{:.1f}"),   t("pdf_se",lang),  "%",   NAVY),
        (_v(stats,"SOL",fmt="{:.0f}"),  t("pdf_sol",lang),    "min", NAVY),
        (_v(stats,"WASO",fmt="{:.0f}"), "WASO",                   "min", NAVY),
    ])); sp(0.35)

    # ── 1. AASM SLAAPARCHITECTUUR ──────────────────────────────
    story.append(_hdr(t("rpt_sec1", lang))); sp(0.15)
    story.append(KeepTogether([_aasm_tbl(stats, lang=lang)])); sp(0.3)

    # ── 2. HYPNOGRAM ───────────────────────────────────────────
    story.append(_hdr(t("rpt_sec2", lang))); sp(0.15)
    tl=results.get("hypnogram_timeline",{}).get("timeline",[])
    if tl:
        try:
            story.append(KeepTogether([_hypno_img(tl, lang=lang)]))
            leg="  ".join(f'<font color="{STAGE_CLR[s]}">■</font> {s}'
                          for s in ["W","N1","N2","N3","R"])
            story.append(Paragraph(leg,styles["SM"]))
        except Exception as e:
            story.append(Paragraph(f"Hypnogram niet beschikbaar: {e}",styles["SM"]))
    else:
        story.append(Paragraph("Geen hypnogram-data.",styles["SM"]))
    sp(0.3)

    # ── 3. SLAAPCYCLI ──────────────────────────────────────────
    cyc=results.get("sleep_cycles",{})
    if cyc.get("success") and cyc.get("cycles"):
        story.append(_hdr(t("rpt_sec3", lang))); sp(0.1)
        story.append(Paragraph(f"{cyc['n_cycles']} NREM/REM-cycli gedetecteerd.",styles["B"]))
        cyc_rows=[[c["cycle"],f"{c['start_epoch']}–{c['end_epoch']}",
                   f"{c['duration_min']} min",
                   "  ".join(f"{s}:{p}%" for s,p in c["stage_distribution"].items())]
                  for c in cyc["cycles"]]
        story.append(_tbl([t("cycle",lang),t("epochs",lang),t("duration",lang),t("composition",lang)],
                          cyc_rows,[2,3,2.5,9.5])); sp(0.3)

    story.append(PageBreak())

    # ── 4. SPINDLES ────────────────────────────────────────────
    spd=results.get("spindles",{})
    story.append(_hdr(t("rpt_sec4", lang))); sp(0.1)
    if spd.get("success"):
        story.append(Paragraph(f"{spd.get('total_spindles',0)} spindels gedetecteerd (N1+N2).",styles["B"]))
        summ=spd.get("summary",[])
        if summ:
            keys=[k for k in summ[0] if k not in ("Stage","stage")]
            rows=[[s.get("Stage",s.get("stage","—"))]+[_rnd(s.get(k)) for k in keys] for s in summ]
            story.append(_tbl(["Stadium"]+[k.replace("_"," ").capitalize() for k in keys],rows))
    else:
        story.append(Paragraph(f"Niet beschikbaar: {spd.get('error','—')}",styles["SM"]))
    sp(0.25)

    # ── 5. SLOW WAVES ──────────────────────────────────────────
    sw=results.get("slow_waves",{})
    story.append(_hdr(t("rpt_sec5", lang))); sp(0.1)
    if sw.get("success"):
        story.append(Paragraph(f"{sw.get('total_slow_waves',0)} trage golven gedetecteerd.",styles["B"]))
        summ=sw.get("summary",[])
        if summ:
            keys=[k for k in summ[0] if k not in ("Stage","stage")]
            rows=[[s.get("Stage",s.get("stage","—"))]+[_rnd(s.get(k)) for k in keys] for s in summ]
            story.append(_tbl(["Stadium"]+[k.replace("_"," ").capitalize() for k in keys],rows))
    else:
        story.append(Paragraph(f"Niet beschikbaar: {sw.get('error','—')}",styles["SM"]))
    sp(0.25)

    # ── 6. REM ─────────────────────────────────────────────────
    rem=results.get("rem",{})
    story.append(_hdr(t("rpt_sec6", lang))); sp(0.1)
    if rem.get("success"):
        rs=rem.get("summary",{})
        story.append(_kpi([
            (str(rs.get("n_rem_periods","—")),t("pdf_rem_periods",lang),"",NAVY),
            (str(rs.get("rem_duration_min","—")),t("pdf_rem_dur",lang),"min",NAVY),
            (str(rs.get("mean_rem_period_min","—")),t("pdf_mean_period",lang),"min",NAVY),
            (str(rs.get("longest_rem_period_min","—")),t("pdf_longest",lang),"min",NAVY),
        ]))
    else:
        story.append(Paragraph(f"Niet beschikbaar: {rem.get('error','—')}",styles["SM"]))
    sp(0.25)

    # ── 7. BANDVERMOGEN ────────────────────────────────────────
    bp=results.get("bandpower",{})
    story.append(_hdr(t("rpt_sec7", lang))); sp(0.1)
    if bp.get("success"):
        bands=["delta","theta","alpha","sigma","beta"]
        ps=bp.get("per_stage",{})
        rows=[[st]+[_rnd(bd.get(b),3) if bd.get(b) is not None else "—" for b in bands]
              for st,bd in ps.items()]
        story.append(_tbl(["Fase"]+[b.capitalize() for b in bands],rows,[2.5,3,3,3,2.5,3]))
    else:
        story.append(Paragraph(f"Niet beschikbaar: {bp.get('error','—')}",styles["SM"]))
    sp(0.25)

    # ── 8. ARTEFACTEN ──────────────────────────────────────────
    art=results.get("artifacts",{})
    story.append(_hdr(t("rpt_sec8", lang))); sp(0.1)
    if art.get("success"):
        sa=art.get("summary",{}); pct=sa.get("artifact_percent",0)
        story.append(Paragraph(
            f"{sa.get('n_artifact_epochs',0)} van {sa.get('n_total_epochs',0)} epochs ({pct}%) als artefact.",
            styles["B"]))
    else:
        story.append(Paragraph(f"Niet beschikbaar: {art.get('error','—')}",styles["SM"]))
    sp(0.3)

    # ── 8b. SIGNAAL KWALITEIT & CONFIDENCE ─────────────────────
    conf_rev = results.get("confidence_review", {})
    sig_q = results.get("signal_quality", {})
    if conf_rev.get("n_low_confidence", 0) > 0 or sig_q.get("issues"):
        story.append(_hdr(t("rpt_sec8b", lang),color=colors.HexColor("#e67e22"))); sp(0.1)

        # Confidence review
        n_low = conf_rev.get("n_low_confidence", 0)
        pct_low = conf_rev.get("pct_low_confidence", 0)
        if n_low > 0:
            story.append(Paragraph(
                f"<b>Staging confidence:</b> {n_low}/{conf_rev.get('n_epochs',0)} epochs "
                f"({pct_low}%) AI confidence &lt;70%.",
                styles["B"]))
            per_stage = conf_rev.get("per_stage_low", {})
            if per_stage:
                parts = [f"{k}: {v}" for k,v in sorted(per_stage.items(), key=lambda x: -x[1])]
                story.append(Paragraph(
                    f"<i>Low-confidence per stadium: {', '.join(parts)}</i>",
                    styles["SM"]))
            sp(0.15)

        # Signal quality issues
        if sig_q.get("issues"):
            story.append(Paragraph(
                f"<b>Signaal-kwaliteit:</b> {sig_q.get('overall','—')} "
                f"({sig_q.get('n_good',0)} goed, {sig_q.get('n_moderate',0)} matig, "
                f"{sig_q.get('n_poor',0)} slecht, {sig_q.get('n_unusable',0)} onbruikbaar)",
                styles["B"]))
            for issue in sig_q.get("issues", [])[:5]:
                story.append(Paragraph(f"  ⚠ {issue}", styles["SM"]))
        sp(0.3)

    story.append(PageBreak())

    # ── 9. RESPIRATOIR ─────────────────────────────────────────
    resp=pneumo.get("respiratory",{})
    story.append(_hdr(t("rpt_sec9", lang))); sp(0.15)
    if resp.get("success") and rsum:
        ahi   = _f(rsum, "ahi_total") or 0
        oahi  = _f(rsum, "oahi")      or 0   # alle obstructief + hypopneas (AASM-conform)
        oahi60 = _f(rsum, "oahi_conf60") or oahi  # supplementair conf>0.60
        oahi_all = _f(rsum, "oahi_all") or oahi
        sev   = _sev(ahi);  osev = _sev(oahi);  clr = _sev_clr(ahi)
        cb    = rsum.get("confidence_bands") or {}
        thr   = rsum.get("oahi_thresholds")  or {}
        avg_c = rsum.get("avg_classification_confidence")
        avg_s = f"{avg_c:.2f}" if avg_c else "—"

        # ── Classificatiebalk ────────────────────────────────────────────
        ab = Table([[Paragraph(
            f"AHI = {ahi:.1f}/u  →  <b>{sev}</b>   |   "
            f"OAHI = {oahi:.1f}/u  →  <b>{osev}</b>",
            ParagraphStyle("AB", fontName="Helvetica-Bold", fontSize=9,
                           textColor=W, leading=12))]],
            colWidths=[CW])
        ab.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), clr),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ]))
        story.append(ab); sp(0.2)

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

        hdr_conf = [
            t("pdf_param", lang), "n", "/u",
            "★★★\n≥0.85", "★★\n0.60–0.84",
            "~\n0.40–0.59", "?\n<0.40"
        ]
        conf_rows = [
            ["Obstructief",
             str(n_obstr), _v(rsum, "obstructive_index", fmt="{:.1f}"),
             str(_ev_conf("obstructive","high")),
             str(_ev_conf("obstructive","moderate")),
             str(_ev_conf("obstructive","borderline")),
             str(_ev_conf("obstructive","low"))],
            ["Centraal",
             str(n_centr), _v(rsum, "central_index", fmt="{:.1f}"),
             str(_ev_conf("central","high")),
             str(_ev_conf("central","moderate")),
             str(_ev_conf("central","borderline")),
             str(_ev_conf("central","low"))],
            ["Gemengd",
             str(n_mixed), _v(rsum, "mixed_index", fmt="{:.1f}"),
             str(_ev_conf("mixed","high")),
             str(_ev_conf("mixed","moderate")),
             str(_ev_conf("mixed","borderline")),
             str(_ev_conf("mixed","low"))],
            ["Hypopnea (Rule 1A/B)",
             str(n_hyp), _v(rsum, "hypopnea_index", fmt="{:.1f}"),
             str(_hyp_conf("high")),
             str(_hyp_conf("moderate")),
             str(_hyp_conf("borderline")),
             str(_hyp_conf("low"))],
            ["A+H totaal",
             str(rsum.get("n_ah_total","—")),
             _v(rsum,"ahi_total",fmt="{:.1f}"),
             "", "", "", ""],
        ]
        story.append(KeepTogether([_tbl(hdr_conf, conf_rows, [5.0,1.2,1.5,1.5,1.8,1.8,1.5])]))
        sp(0.25)

        # ── OAHI drempelgevoeligheidstabel ───────────────────────────────
        story.append(_hdr("OAHI — drempelgevoeligheid", color=BLUE)); sp(0.1)
        story.append(Paragraph(
            f"Gem. confidence apneas: <b>{avg_s}</b>  |  "
            f"Alle events: OAHI = {oahi_all:.1f}/u",
            styles["SM"])); sp(0.1)

        oahi_rows = [
            ["≥ 0.85 (hoge zekerheid)",
             f"{thr.get('0.85', '—'):.1f}" if isinstance(thr.get('0.85'), float) else "—",
             _sev(thr.get('0.85') or 0),
             f"{cb.get('high',0)} events"],
            ["≥ 0.60 (matig + hoog)",
             f"{oahi60:.1f}",
             _sev(oahi60),
             f"{cb.get('high',0) + cb.get('moderate',0)} events"],
            ["≥ 0.40 (incl. grensgebied)",
             f"{thr.get('0.40', '—'):.1f}" if isinstance(thr.get('0.40'), float) else "—",
             _sev(thr.get('0.40') or 0),
             f"{cb.get('high',0)+cb.get('moderate',0)+cb.get('borderline',0)} events"],
            ["Alle events  ← officiële OAHI",
             f"{oahi:.1f}",
             _sev(oahi),
             f"{rsum.get('n_obstructive',0)+rsum.get('n_hypopnea',0)} events"],
        ]
        story.append(KeepTogether([_tbl(
            ["Drempel", "OAHI (/u)", "Ernst", "Basis"],
            oahi_rows,
            [6.5, 2.5, 3.5, 4.0])]))
        sp(0.15)
        story.append(Paragraph(
            "<i>★★★ Hoge zekerheid (≥0.85): duidelijk patroon  "
            "★★ Matige zekerheid (0.60–0.84): waarschijnlijk correct  "
            "~ Grensgebied (0.40–0.59): borderline default  "
            "? Lage zekerheid (<0.40): signaalruis / ontbrekende effort</i>",
            styles["SM"])); sp(0.2)

        # ── Overschatting-correctie samenvatting (v0.8.11) ───────────────
        n_spo2_cc  = rsum.get("n_spo2_cross_contaminated", 0) or 0
        n_csr_fl   = rsum.get("n_csr_flagged", 0) or 0
        n_noise    = rsum.get("n_low_conf_noise", 0) or 0
        n_border   = rsum.get("n_low_conf_borderline", 0) or 0
        ahi_csr    = rsum.get("ahi_csr_corrected")
        ahi_noise  = rsum.get("ahi_excl_noise")
        if n_spo2_cc > 0 or n_csr_fl > 0 or n_noise > 0:
            story.append(_hdr("Overschatting-correctie (v0.8.11)", color=BLUE)); sp(0.1)
            corr_rows = [
                ["Fix 1 — Post-apnea basislijn",
                 "Gecorrigeerd",
                 "Hyperpnea recovery 30s uitgesloten uit basislijnberekening"],
                ["Fix 2 — SpO₂ kruiscontaminatie",
                 f"{n_spo2_cc} events",
                 "Hypopneas waarvoor SpO₂-nadir mogelijk van vorig event stamt"],
                ["Fix 3 — Cheyne-Stokes events",
                 (f"{n_csr_fl} events  →  AHI {ahi_csr:.1f}/u" if ahi_csr else f"{n_csr_fl} events"),
                 "Events gemarkeerd als CSR-cyclus gerelateerd"],
                ["Fix 4 — Lage confidence",
                 f"{n_noise} ruis  +  {n_border} borderline",
                 (f"AHI excl. ruis (<0.40): {ahi_noise:.1f}/u" if ahi_noise else "conf<0.40 = signaalruis")],
                ["Fix 5 — Artefact-flanken",
                 "Gecorrigeerd",
                 "Post-gap exclusie 15s na signaaluitval ≥10s"],
            ]
            story.append(KeepTogether([_tbl(
                ["Correctie", "Impact", "Toelichting"],
                corr_rows, [4.0, 3.5, 9.5])]))
            sp(0.15)
            story.append(Paragraph(
                "<i>Deze correcties zijn informatief. De officiele AHI en OAHI blijven "
                "AASM 2.6-conform (alle events). Bovenstaande indices helpen de clinicus "
                "de robuustheid van de scoring te beoordelen.</i>",
                styles["SM"])); sp(0.2)

        # ── Overige respiratoire indices ─────────────────────────────────
        story.append(KeepTogether([_tbl(
            [t("pdf_param", lang), t("pdf_value", lang), ""],
            [["AHI REM",   _v(rsum,"ahi_rem",fmt="{:.1f}"),  ""],
             ["AHI NREM",  _v(rsum,"ahi_nrem",fmt="{:.1f}"), ""],
             [t("pdf_avg_apnea_dur", lang), f"{rsum.get('avg_apnea_dur_s','—')} s", ""],
             ["Max. apnea-duur",            f"{rsum.get('max_apnea_dur_s','—')} s", ""],
            ], [8, 4, 5])])); sp(0.2)

        # Arousal / RERA / RDI
        arous=pneumo.get("arousal",{}); asum=arous.get("summary",{})
        if arous.get("success") and asum:
            story.append(_hdr(t("rpt_sec9b", lang),color=BLUE)); sp(0.1)
            rdi=_f(asum,"rdi")
            story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang)],[
                ["Arousal index (AI)",       f"{asum.get('arousal_index','—')} /u"],
                [t("pdf_resp_arousals",lang),    str(asum.get("n_respiratory_arousals","—"))],
                [t("pdf_spont_arousals",lang),        str(asum.get("n_spontaneous_arousals","—"))],
                ["RERA's",                   str(asum.get("n_reras","—"))],
                ["RERA-index",               f"{asum.get('rera_index','—')} /u"],
                ["RDI (AHI + RERA)",         f"{rdi:.1f} /u" if rdi else "—"],
            ],[9,8])); sp(0.2)
    else:
        story.append(Paragraph(f"Niet beschikbaar: {resp.get('error','geen data')}",styles["SM"]))
    sp(0.25)

    # ── 9c. Breath-by-breath analyse ───────────────────────────
    bb = resp.get("breath_analysis", {})
    if bb.get("n_breaths", 0) > 0:
        story.append(_hdr(t("rpt_sec9c", lang), color=BLUE)); sp(0.1)

        if not bb.get("fallback"):
            rows = [
                [t("pdf_detected_breaths", lang),  str(bb.get("n_breaths", "—"))],
                [t("pdf_bb_apneas", lang),     str(bb.get("n_bb_apneas", "—"))],
                [t("pdf_bb_hypopneas", lang),  str(bb.get("n_bb_hypopneas", "—"))],
            ]
            if bb.get("avg_flattening") is not None:
                flat_val = bb["avg_flattening"]
                flat_label = "normaal" if flat_val < 0.25 else "verhoogd" if flat_val < 0.40 else "hoog (flow-limitatie)"
                rows.append([t("pdf_mean_flattening", lang), f"{flat_val:.2f} ({flat_label})"])
            story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], rows, [9, 8])); sp(0.15)

        if resp.get("dual_sensor"):
            story.append(Paragraph(
                "<i>Dual-sensor scoring: apneu op thermistor, hypopneu op nasale druk (AASM 2.6).</i>",
                styles["SM"]))
        sp(0.25)

    # ── 10. SpO2 ───────────────────────────────────────────────
    spo2=pneumo.get("spo2",{}); ss=spo2.get("summary",{})
    story.append(_hdr(t("rpt_sec10", lang))); sp(0.1)
    if spo2.get("success") and ss:
        story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang),"Ref"],[
            ["Gemiddelde SpO2",  f"{ss.get('mean_spo2','—')} %", "≥ 95%"],
            ["Minimale SpO2",   f"{ss.get('min_spo2','—')} %",  ""],
            [t("pdf_time_below90",lang),       f"{ss.get('pct_below_90','—')} %","< 1%"],
            ["ODI 3%",           str(ss.get("odi_3pct","—")),    "< 5/u"],
            ["ODI 4%",           str(ss.get("odi_4pct","—")),    "< 5/u"],
        ],[8,4.5,4.5]))
        ts=spo2.get("timeseries")
        if ts and len(ts)>10:
            sp(0.15)
            try: story.append(KeepTogether([_spo2_img(ts)]))
            except: pass
    else:
        story.append(Paragraph(f"SpO2: {spo2.get('error',t('pdf_no_channel',lang))}",styles["SM"]))
    sp(0.25)

    # ── 11. PLM ────────────────────────────────────────────────
    plm=pneumo.get("plm",{}); ps=plm.get("summary",{})
    if plm.get("success") and ps:
        story.append(_hdr(t("rpt_sec11", lang))); sp(0.1)
        plmi=_f(ps,"plm_index") or 0
        story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang)],[
            [t("pdf_total_lms",lang),                 str(ps.get("n_lm_total","—"))],
            ["LMs tijdens slaap",          str(ps.get("n_lm_sleep","—"))],
            ["Resp.-geassocieerd (excl.)", str(ps.get("n_resp_associated","—"))],
            [t("pdf_plms_series",lang),           str(ps.get("n_plm","—"))],
            [t("pdf_plm_series",lang),                 str(ps.get("n_plm_series","—"))],
            ["PLMI",                       f"{plmi:.1f} /u  —  {ps.get('plm_severity','—')}"],
        ],[9,8])); sp(0.2)

    # Ensure arousal summary is available for diagnosis
    try:
        asum
    except NameError:
        asum = pneumo.get("arousal", {}).get("summary", {})

    # ── 12. DIAGNOSE (gestandaardiseerd AASM) ────────────────────
    story.append(_hdr(t("rpt_sec12", lang))); sp(0.1)

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

    # v0.8.11: lang is al correct gezet bovenaan de functie (uit parameter)
    # NIET opnieuw overschrijven met site/patient defaults

    if manual_diag:
        story.append(Paragraph(f"<b>{t('concl_diagnosis', lang)}:</b> {manual_diag}", styles["B"]))
    else:
        # v0.8.11: gecentraliseerde conclusie-generatie
        from conclusions import generate_conclusions
        spo2_nadir_f = None
        spo2_pct_f = None
        try:
            if spo2_min_v != "—":
                spo2_nadir_f = float(str(spo2_min_v))
            if spo2_pct_v != "—":
                spo2_pct_f = float(str(spo2_pct_v))
        except (ValueError, TypeError):
            pass

        concl_parts = generate_conclusions(
            ahi=ahi, oahi=oahi, plmi=plmi_v, se=se_v, tst=tst_v, ai=ai_v,
            bmi=bmi_v, spo2_nadir=spo2_nadir_f, spo2_pct_below90=spo2_pct_f,
            csr_info=pneumo.get("cheyne_stokes", {}), lang=lang,
        )
        for part in concl_parts:
            sp(0.1)
            story.append(Paragraph(f"<b>{part['title']}</b>", styles["B"]))
            story.append(Paragraph(part["body"], styles["B"]))
            if part["tx"]:
                story.append(Paragraph(
                    f"<b>{t('concl_treatment', lang)}:</b> {part['tx']}", styles["B"]))

    sp(0.1)
    if manual_comment:
        story.append(Paragraph(f"<b>{t('comments', lang)}:</b> {manual_comment}", styles["B"]))
    sp(0.2)

    rec_date=(meta.get("analysis_timestamp","—") or "—")[:10]
    scorer=str(pat.get("scorer","—") or "—")
    sig=Table([[Paragraph(f"<b>{t('pdf_scorer',lang)}</b> {scorer}",styles["B"]),
                Paragraph(f"<b>{t('physician',lang)}:</b> _________________________",styles["B"]),
                Paragraph(f"<b>{t('date',lang)}:</b> {rec_date}",styles["B"])]],
              colWidths=[CW/3]*3)
    sig.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("BOX",(0,0),(-1,-1),0.4,GRID),("BACKGROUND",(0,0),(-1,-1),BGROW)]))
    story.append(sig); sp(0.3)

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

    disc_text = t("pdf_disc_auto", lang) + " "
    if verified_by and verified_role:
        disc_text += t("pdf_disc_verified", lang).format(role=role_label, name=verified_by)
    else:
        disc_text += t("pdf_disc_screening", lang)
    story.append(Paragraph(disc_text, styles["D"]))

    doc.build(story,onFirstPage=on1,onLaterPages=onN)
    return output_path
