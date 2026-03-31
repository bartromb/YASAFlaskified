"""
generate_pdf_report.py — YASAFlaskified v0.8.12
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

# ── v0.8.12: Overview plots — gedeelde x-as (uren) ────────────

# Shared plot setup for all overview panels
_OV_WC = 16.2   # cm width
_OV_DPI = 150
_OV_YLABEL_W = 0.55  # inch — vaste y-label breedte voor uitlijning

def _ov_setup(hc, dur_h):
    """Maak figuur + ax met identieke marges voor alle overview-panelen."""
    fig, ax = plt.subplots(figsize=(_OV_WC/2.54, hc/2.54), dpi=_OV_DPI)
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    fig.subplots_adjust(left=_OV_YLABEL_W / (_OV_WC/2.54), right=0.98, top=0.95, bottom=0.15)
    ax.set_xlim(0, dur_h)
    step = max(1, round(dur_h / 8))
    xt = np.arange(0, dur_h + 0.01, step)
    ax.set_xticks(xt)
    ax.set_xticklabels([f"{t:.0f}h" for t in xt], fontsize=5, color="#6b7a99")
    ax.grid(axis="x", color="#e0e6ed", linewidth=0.3)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines["left"].set_linewidth(0.4); ax.spines["bottom"].set_linewidth(0.4)
    ax.tick_params(axis="both", length=2, width=0.4)
    return fig, ax

def _ov_finish(fig, hc):
    """Sla op als Image met vaste breedte."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_OV_DPI, bbox_inches="tight")
    plt.close(fig); buf.seek(0)
    return Image(buf, width=_OV_WC*cm, height=hc*cm)

POS_LABELS = {0:"BUK",1:"LNK",2:"RUG",3:"REC",4:"STA"}
POS_LABELS_FR = {0:"PRO",1:"GAU",2:"DOS",3:"DRO",4:"DEB"}
POS_LABELS_EN = {0:"PRO",1:"LFT",2:"SUP",3:"RGT",4:"UPR"}

def _hypno_ov(timeline, dur_h, hc=2.2, lang="nl"):
    """Hypnogram voor overview (x-as in uren)."""
    stages = [ep.get("stage","W") for ep in timeline]
    order = {"W":0,"N1":1,"N2":2,"N3":3,"R":4}
    n = len(stages)
    epoch_h = 30/3600  # 30s in uren
    x_h = np.arange(n) * epoch_h
    y = [order.get(s,0) for s in stages]

    fig, ax = _ov_setup(hc, dur_h)
    ax.step(x_h, y, where="post", color="#1a3a5c", linewidth=0.7, alpha=0.9)
    for i,(s,yv) in enumerate(zip(stages,y)):
        ax.fill_between([x_h[i], x_h[i]+epoch_h], [yv-.4,yv-.4], [yv+.4,yv+.4],
                        color=STAGE_CLR.get(s,"#ccc"), alpha=0.35, linewidth=0)
    ax.set_yticks([0,1,2,3,4])
    ax.set_yticklabels(["W","N1","N2","N3","REM"], fontsize=6, color="#1a3a5c", fontweight="600")
    ax.set_ylim(-0.7, 4.7); ax.invert_yaxis()
    for yy in [0,1,2,3,4]: ax.axhline(yy, color="#e0e6ed", linewidth=0.3, zorder=0)
    return _ov_finish(fig, hc)

def _events_ov(events, dur_h, rejected_hyps=None, hc=2.0):
    """Events tijdlijn: OA/CA/MA/HYP/FR — altijd alle rijen zichtbaar."""
    fig, ax = _ov_setup(hc, dur_h)
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

def _pos_ov(pos_per_epoch, dur_h, hc=1.6, lang="nl"):
    """Positie-tijdlijn (x-as in uren)."""
    labels = POS_LABELS if lang=="nl" else POS_LABELS_FR if lang=="fr" else POS_LABELS_EN
    n = len(pos_per_epoch)
    epoch_h = 30/3600
    x_h = np.arange(n) * epoch_h
    y = np.array([min(p,4) for p in pos_per_epoch])

    fig, ax = _ov_setup(hc, dur_h)
    ax.step(x_h, y, where="post", color="#27ae60", linewidth=0.8)
    for i,yv in enumerate(y):
        ax.fill_between([x_h[i], x_h[i]+epoch_h], [yv-.3,yv-.3], [yv+.3,yv+.3],
                        color="#27ae60", alpha=0.15, linewidth=0)
    ax.set_yticks([0,1,2,3,4])
    ax.set_yticklabels([labels.get(i,"?") for i in range(5)], fontsize=6, color="#2c3e50")
    ax.set_ylim(-0.5, 4.5); ax.invert_yaxis()
    for yy in range(5): ax.axhline(yy, color="#e0e6ed", linewidth=0.3, zorder=0)
    return _ov_finish(fig, hc)

def _snore_ov(rms_1s, dur_h, hc=1.4):
    """Snurk-amplitude (PHONO) — x-as in uren."""
    y = np.array(rms_1s, dtype=float)
    x_h = np.arange(len(y)) / 3600

    fig, ax = _ov_setup(hc, dur_h)
    ax.fill_between(x_h, 0, y, color="#95a5a6", alpha=0.4, linewidth=0)
    ax.plot(x_h, y, color="#7f8c8d", linewidth=0.3)
    threshold = float(np.percentile(y, 60))
    ax.axhline(threshold, color="#e67e22", linewidth=0.5, linestyle="--", alpha=0.6)
    ax.set_ylim(0, None)

    return _ov_finish(fig, hc)

def _spo2_ov(ts, dur_h, hc=1.6):
    """SpO2 tijdlijn — x-as in uren."""
    y = np.array(ts, dtype=float)
    x_h = np.arange(len(y)) / 3600  # SpO2 timeseries at 1 Hz

    fig, ax = _ov_setup(hc, dur_h)
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
            "YASAFlaskified v0.8.12  |  AASM 2.6  |  www.slaapkliniek.be  |  \u00a9 Bart Rombaut")
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

    # ══════════════════════════════════════════════════════════════
    # OVERZICHTSPAGINA (v0.8.12) — kanalen + visueel overzicht
    # ══════════════════════════════════════════════════════════════

    # ── 0a. Registratie: kanalen in EDF ────────────────────────
    all_ch = pneumo.get("meta", {}).get("all_channels", [])
    if all_ch:
        story.append(_hdr(t("rpt_sec0a", lang))); sp(0.1)
        # Groepeer kanalen in rijen van 4
        ch_rows = []
        for i in range(0, len(all_ch), 4):
            row = all_ch[i:i+4]
            while len(row) < 4:
                row.append("")
            ch_rows.append(row)
        story.append(_tbl(
            [t("pdf_ch_col", lang)+" 1", t("pdf_ch_col", lang)+" 2",
             t("pdf_ch_col", lang)+" 3", t("pdf_ch_col", lang)+" 4"],
            ch_rows, [4.25, 4.25, 4.25, 4.25])); sp(0.1)
        story.append(Paragraph(
            f"<i>{len(all_ch)} {t('pdf_ch_total', lang)}</i>",
            styles["SM"])); sp(0.2)

    # ── 0b. Visueel overzicht ─────────────────────────────────
    story.append(_hdr(t("rpt_sec0b", lang))); sp(0.1)

    # Bereken gedeelde tijdsduur (uren) voor alle grafieken
    timeline = results.get("hypnogram_timeline", {}).get("timeline", [])
    n_epochs = len(timeline) if timeline else 0
    dur_h = n_epochs * 30 / 3600 if n_epochs > 0 else float(meta.get("duration_min", 480)) / 60

    # Hypnogram
    if timeline:
        story.append(Paragraph("<b>HYPNO</b>", styles["SM"]))
        try:
            story.append(_hypno_ov(timeline, dur_h, hc=2.2, lang=lang))
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
        try: story.append(_events_ov(resp_events, dur_h, rejected_hyps=rejected_hyps))
        except: pass
        sp(0.1)

    # Positie
    pos_data = pneumo.get("position", {})
    pos_epochs = pos_data.get("pos_per_epoch", [])
    if pos_epochs:
        story.append(Paragraph("<b>POS</b>", styles["SM"]))
        try: story.append(_pos_ov(pos_epochs, dur_h, hc=1.6, lang=lang))
        except: pass
        sp(0.1)

    # Snurk (PHONO)
    snore_rms = pneumo.get("snore", {}).get("rms_1s", [])
    if snore_rms and len(snore_rms) > 60:
        story.append(Paragraph("<b>PHONO</b>", styles["SM"]))
        try: story.append(_snore_ov(snore_rms, dur_h, hc=1.4))
        except: pass
        sp(0.1)

    # SpO2
    spo2_ts = pneumo.get("spo2", {}).get("timeseries")
    if spo2_ts and len(spo2_ts) > 10:
        story.append(Paragraph("<b>SpO2</b>", styles["SM"]))
        try: story.append(_spo2_ov(spo2_ts, dur_h, hc=1.6))
        except: pass
        sp(0.1)

    story.append(PageBreak())

    # ── 1. AASM SLAAPARCHITECTUUR ──────────────────────────────
    story.append(_hdr(t("rpt_sec1", lang))); sp(0.15)
    story.append(KeepTogether([_aasm_tbl(stats, lang=lang)])); sp(0.3)

    # ── 2. SLAAPCYCLI ──────────────────────────────────────────
    cyc=results.get("sleep_cycles",{})
    if cyc.get("success") and cyc.get("cycles"):
        story.append(_hdr(t("rpt_sec2", lang))); sp(0.1)
        story.append(Paragraph(f"{cyc['n_cycles']} NREM/REM-cycli gedetecteerd.",styles["B"]))
        cyc_rows=[[c["cycle"],f"{c['start_epoch']}–{c['end_epoch']}",
                   f"{c['duration_min']} min",
                   "  ".join(f"{s}:{p}%" for s,p in c["stage_distribution"].items())]
                  for c in cyc["cycles"]]
        story.append(_tbl([t("cycle",lang),t("epochs",lang),t("duration",lang),t("composition",lang)],
                          cyc_rows,[2,3,2.5,9.5])); sp(0.3)

    story.append(PageBreak())

    # ── 3. SPINDLES ────────────────────────────────────────────
    spd=results.get("spindles",{})
    story.append(_hdr(t("rpt_sec3", lang))); sp(0.1)
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

    # ── 4. SLOW WAVES ──────────────────────────────────────────
    sw=results.get("slow_waves",{})
    story.append(_hdr(t("rpt_sec4", lang))); sp(0.1)
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
    else:
        story.append(Paragraph(f"Niet beschikbaar: {rem.get('error','—')}",styles["SM"]))
    sp(0.25)

    # ── 6. BANDVERMOGEN ────────────────────────────────────────
    bp=results.get("bandpower",{})
    story.append(_hdr(t("rpt_sec6", lang))); sp(0.1)
    if bp.get("success"):
        bands=["delta","theta","alpha","sigma","beta"]
        ps=bp.get("per_stage",{})
        rows=[[st]+[_rnd(bd.get(b),3) if bd.get(b) is not None else "—" for b in bands]
              for st,bd in ps.items()]
        story.append(_tbl(["Fase"]+[b.capitalize() for b in bands],rows,[2.5,3,3,3,2.5,3]))
    else:
        story.append(Paragraph(f"Niet beschikbaar: {bp.get('error','—')}",styles["SM"]))
    sp(0.25)

    # ── 7. ARTEFACTEN ──────────────────────────────────────────
    art=results.get("artifacts",{})
    story.append(_hdr(t("rpt_sec7", lang))); sp(0.1)
    if art.get("success"):
        sa=art.get("summary",{}); pct=sa.get("artifact_percent",0)
        story.append(Paragraph(
            f"{sa.get('n_artifact_epochs',0)} van {sa.get('n_total_epochs',0)} epochs ({pct}%) als artefact.",
            styles["B"]))
    else:
        story.append(Paragraph(f"Niet beschikbaar: {art.get('error','—')}",styles["SM"]))
    sp(0.3)

    # ── 7b. SIGNAAL KWALITEIT & CONFIDENCE ─────────────────────
    conf_rev = results.get("confidence_review", {})
    sig_q = results.get("signal_quality", {})
    if conf_rev.get("n_low_confidence", 0) > 0 or sig_q.get("issues"):
        story.append(_hdr(t("rpt_sec7b", lang),color=colors.HexColor("#e67e22"))); sp(0.1)

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

    # ── 8. RESPIRATOIR ─────────────────────────────────────────
    resp=pneumo.get("respiratory",{})
    story.append(_hdr(t("rpt_sec8", lang))); sp(0.15)
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
            story.append(_hdr("Overschatting-correctie", color=BLUE)); sp(0.1)
            corr_rows = [
                ["Fix 1 — Post-apnea basislijn",
                 "Gecorrigeerd",
                 "Hyperpnea recovery 30s uitgesloten uit basislijnberekening"],
                ["Fix 2 — SpO2 kruiscontaminatie",
                 f"{n_spo2_cc} events",
                 "Hypopneas waarvoor SpO2-nadir mogelijk van vorig event stamt"],
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
            story.append(_hdr(t("rpt_sec8b", lang),color=BLUE)); sp(0.1)
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
                flat_label = "normaal" if flat_val < 0.25 else "verhoogd" if flat_val < 0.40 else "hoog (flow-limitatie)"
                rows.append([t("pdf_mean_flattening", lang), f"{flat_val:.2f} ({flat_label})"])
            story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], rows, [9, 8])); sp(0.15)

        if resp.get("dual_sensor"):
            story.append(Paragraph(
                "<i>Dual-sensor scoring: apneu op thermistor, hypopneu op nasale druk (AASM 2.6).</i>",
                styles["SM"]))
        sp(0.25)

    # ── 8d. FLOW-REDUCTIE ZONDER CRITERIA (FRI) ──────────────
    rejected_hyps = resp.get("rejected_hypopneas", [])
    n_reinstated  = resp.get("rule1b_reinstated", 0) or 0
    n_fri = max(0, len(rejected_hyps) - n_reinstated)
    if n_fri > 0 and resp.get("success"):
        tst_h = float(str(stats.get("TST", 0) or 0)) / 60.0
        fri_index = n_fri / tst_h if tst_h > 0 else 0
        story.append(_hdr(t("rpt_sec8d", lang), color=BLUE)); sp(0.1)
        story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], [
            [t("pdf_fri_count", lang),  str(n_fri)],
            [t("pdf_fri_index", lang),  f"{fri_index:.1f} /u"],
            [t("pdf_fri_r1b", lang),    str(n_reinstated)],
        ], [9, 8])); sp(0.1)
        story.append(Paragraph(
            f"<i>{t('pdf_fri_note', lang)}</i>", styles["SM"])); sp(0.2)

    # ── 9. SpO2 ───────────────────────────────────────────────
    spo2=pneumo.get("spo2",{}); ss=spo2.get("summary",{})
    story.append(_hdr(t("rpt_sec9", lang))); sp(0.1)
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

    # ── 10. PLM ────────────────────────────────────────────────
    plm=pneumo.get("plm",{}); ps=plm.get("summary",{})
    if plm.get("success") and ps:
        story.append(_hdr(t("rpt_sec10", lang))); sp(0.1)
        plmi=_f(ps,"plm_index") or 0
        story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang)],[
            [t("pdf_total_lms",lang),                 str(ps.get("n_lm_total","—"))],
            ["LMs tijdens slaap",          str(ps.get("n_lm_sleep","—"))],
            ["Resp.-geassocieerd (excl.)", str(ps.get("n_resp_associated","—"))],
            [t("pdf_plms_series",lang),           str(ps.get("n_plm","—"))],
            [t("pdf_plm_series",lang),                 str(ps.get("n_plm_series","—"))],
            ["PLMI",                       f"{plmi:.1f} /u  —  {ps.get('plm_severity','—')}"],
        ],[9,8])); sp(0.2)

    # ── 10b. RONCHOPATHIE (snurk-analyse) ─────────────────────
    snore = pneumo.get("snore", {})
    snore_s = snore.get("summary", {})
    story.append(_hdr(t("rpt_sec10b", lang))); sp(0.1)
    if snore.get("success") and snore_s:
        story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], [
            [t("pdf_snore_min", lang),     f"{snore_s.get('snore_min', '—')} min"],
            [t("pdf_snore_pct", lang),     f"{snore_s.get('snore_pct_tst', '—')} %"],
            [t("pdf_snore_index", lang),   f"{snore_s.get('snore_index', '—')} /u"],
        ], [9, 8])); sp(0.2)
    else:
        story.append(Paragraph(
            f"<i>{t('pdf_snore_no_data', lang)}</i>", styles["SM"])); sp(0.2)

    # Ensure arousal summary is available for diagnosis
    try:
        asum
    except NameError:
        asum = pneumo.get("arousal", {}).get("summary", {})

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

    # v0.8.12: Besluit wordt NIET meer automatisch gegenereerd.
    # De arts vult het besluit manueel in via de rapport-editor.
    if manual_diag:
        story.append(Paragraph(f"<b>{t('concl_diagnosis', lang)}:</b> {manual_diag}", styles["B"]))
    else:
        story.append(Paragraph(
            f"<i>{t('concl_empty', lang)}</i>", styles["SM"]))

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
