"""
generate_pdf_report.py — YASAFlaskified v0.8.30
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
AHI_SEV = [(5,GRN,"Normal"),(15,ORA,"Mild OSA"),(30,RED,"Moderate OSA"),(9999,colors.HexColor("#7b241c"),"Severe OSA")]

_SEV_LABELS = {
    "Normal":       {"nl": "Normaal",     "fr": "Normal",      "en": "Normal",       "de": "Normal"},
    "Mild OSA":     {"nl": "Mild OSA",    "fr": "SAOS léger",  "en": "Mild OSA",     "de": "Leichtes OSA"},
    "Moderate OSA": {"nl": "Matig OSA",   "fr": "SAOS modéré", "en": "Moderate OSA",  "de": "Mittelgradiges OSA"},
    "Severe OSA":   {"nl": "Ernstig OSA", "fr": "SAOS sévère", "en": "Severe OSA",    "de": "Schweres OSA"},
}

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

def _sev(ahi, lang="nl"):
    try: v=float(ahi)
    except: return "—"
    for t,_,l in AHI_SEV:
        if v<t: return _SEV_LABELS.get(l, {}).get(lang, l)
    return _SEV_LABELS.get("Severe OSA", {}).get(lang, "Severe OSA")

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

# ── v0.8.22: Overview plots — gedeelde x-as (uren) ────────────

# Shared plot setup for all overview panels
_OV_WC = 16.2   # cm width
_OV_DPI = 150
_OV_LEFT = 0.09   # fraction — vaste linkermarge voor y-labels
_OV_RIGHT = 0.98

def _ov_setup(hc, dur_h, show_xticklabels=True):
    """Maak figuur + ax met identieke marges voor alle overview-panelen."""
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

def _hypno_ov(timeline, dur_h, hc=2.2, lang="nl"):
    """Hypnogram voor overview (x-as in uren)."""
    stages = [ep.get("stage","W") for ep in timeline]
    order = {"W":0,"N1":1,"N2":2,"N3":3,"R":4}
    n = len(stages)
    epoch_h = 30/3600  # 30s in uren
    x_h = np.arange(n) * epoch_h
    y = [order.get(s,0) for s in stages]

    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False)
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
    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False)
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
    # x-labels alleen op laatste plot
    labels = POS_LABELS if lang=="nl" else POS_LABELS_FR if lang=="fr" else POS_LABELS_EN
    n = len(pos_per_epoch)
    epoch_h = 30/3600
    x_h = np.arange(n) * epoch_h
    y = np.array([min(p,4) for p in pos_per_epoch])

    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False)
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

    fig, ax = _ov_setup(hc, dur_h, show_xticklabels=False)
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
            "YASAFlaskified v0.8.30  |  AASM 2.6  |  www.slaapkliniek.be  |  \u00a9 Bart Rombaut")
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
    ("spo2",            "SpO₂",         "#e74c3c"),
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


def _plot_epoch_example(edf_path, channel_map, event, hypno=None,
                        pre_s=15, post_s=30, wc=16.2, hc_per_ch=1.2):
    """Plot een enkel epoch-voorbeeld: gestapelde pneumokanalen rond een event.

    Parameters
    ----------
    edf_path : str       Pad naar EDF-bestand
    channel_map : dict   {type: channel_name} mapping
    event : dict         Event met onset_s, duration_s, type, etc.
    hypno : list         Hypnogram (optioneel, voor stage label)
    pre_s, post_s : float  Seconden vóór/na event
    """
    import mne
    mne.set_log_level("ERROR")

    onset  = float(event["onset_s"])
    dur    = float(event["duration_s"])
    t_start = max(0, onset - pre_s)
    t_end   = onset + dur + post_s

    # Bepaal welke kanalen beschikbaar zijn
    try:
        raw_hdr = mne.io.read_raw_edf(edf_path, preload=False, verbose=False)
        available = raw_hdr.ch_names
    except Exception:
        return None

    ch_to_plot = []
    for ch_type, label, color in _EPOCH_CH_ORDER:
        ch_name = channel_map.get(ch_type)
        if ch_name and ch_name in available:
            ch_to_plot.append((ch_type, ch_name, label, color))

    if len(ch_to_plot) < 2:
        return None

    # Laad alleen de benodigde kanalen
    try:
        ch_names_load = [c[1] for c in ch_to_plot]
        raw = mne.io.read_raw_edf(edf_path, preload=False, verbose=False)
        raw.pick(ch_names_load)
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

    for i, (ch_type, ch_name, label, color) in enumerate(ch_to_plot):
        ax = axes[i]
        ax.set_facecolor("white")
        try:
            data = raw.get_data(picks=[ch_name])[0][s_start:s_end]
        except Exception:
            data = np.zeros(s_end - s_start)

        # SpO2: vaste y-as
        if ch_type == "spo2":
            ax.plot(times, data, color=color, linewidth=0.6)
            valid = data[(data >= 50) & (data <= 100)]
            if len(valid) > 0:
                ax.set_ylim(max(50, np.min(valid) - 3), min(102, np.max(valid) + 2))
            ax.axhline(90, color="#e74c3c", linewidth=0.4, linestyle="--", alpha=0.5)
        else:
            ax.plot(times, data, color=color, linewidth=0.5)
            # Auto-scale met clipping op P1/P99
            if len(data) > 10:
                p1, p99 = np.percentile(data, [1, 99])
                margin = max((p99 - p1) * 0.1, 1)
                ax.set_ylim(p1 - margin, p99 + margin)

        # Event markering (grijze band)
        ax.axvspan(onset, onset + dur, color="#e74c3c", alpha=0.12, zorder=0)
        ax.axvline(onset, color="#e74c3c", linewidth=0.5, alpha=0.6)
        ax.axvline(onset + dur, color="#e74c3c", linewidth=0.5, alpha=0.6)

        ax.set_ylabel(label, fontsize=5.5, color="#4a5568", rotation=0,
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

    title = f"{ev_type} — {ev_dur}{ev_desat}{ev_conf}{stage} — t={onset_hm}"
    fig.suptitle(title, fontsize=6.5, color="#1a3a5c", fontweight="bold", y=0.99)

    plt.tight_layout(pad=0.3)
    fig.subplots_adjust(top=0.94, hspace=0.15)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=wc*cm, height=total_hc*cm)


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
    images = []
    for ev in picks:
        try:
            img = _plot_epoch_example(edf_path, ch_map, ev, hypno=hypno,
                                       pre_s=15, post_s=30, wc=wc)
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
    is_titration = study_type.startswith("titration_")
    is_polygraphy = "_pg_" in study_type
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
    else:
        title_txt = t("pdf_title_psg", lang)

    sp(0.1)
    story.append(Paragraph(title_txt, styles["T"]))
    _sp_label = pneumo.get("meta", {}).get("scoring_label", "Standard (AASM 2.6)")
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
    story.append(pt); sp(0.15)

    # ── KPI-BALK ───────────────────────────────────────────────
    ahi_v=_f(rsum,"ahi_total"); ahi_s=f"{ahi_v:.1f}" if ahi_v is not None else "—"
    # v0.8.22: Label afhankelijk van studietype
    if is_polygraphy:
        ahi_label = f"REI  ({_sev(ahi_v, lang)})"
    elif is_titration:
        ahi_label = f"{t('pdf_residual',lang)} AHI  ({_sev(ahi_v, lang)})"
    else:
        ahi_label = f"AHI  ({_sev(ahi_v, lang)})"
    story.append(_kpi([
        (ahi_s, ahi_label, "/u", _sev_clr(ahi_v) if ahi_v else GR),
        (_v(stats,"TST",fmt="{:.0f}"),  "TST", "min", NAVY),
        (_v(stats,"SE",fmt="{:.1f}"),   t("pdf_se",lang),  "%",   NAVY),
        (_v(stats,"SOL",fmt="{:.0f}"),  t("pdf_sol",lang),    "min", NAVY),
        (_v(stats,"WASO",fmt="{:.0f}"), "WASO",                   "min", NAVY),
    ])); sp(0.15)

    # ── v0.8.22: Prominente waarschuwing bij slechte signaalkwaliteit ──
    sig_q = results.get("signal_quality", {})
    conf_rev = results.get("confidence_review", {})
    sq_grade = sig_q.get("overall_grade", "unknown")
    pct_low_conf = conf_rev.get("pct_low_confidence", 0) or 0
    _warnings = []
    if sq_grade == "poor":
        _n_unusable = sum(1 for ch in (sig_q.get("channels") or [])
                         if ch.get("quality_grade") == "unusable")
        if _n_unusable > 0:
            _warnings.append(
                f"⚠ Signaalkwaliteit: {_n_unusable} kanalen onbruikbaar "
                f"(amplitude &lt; minimum). Staging en micro-architectuur "
                f"(spindles, slow waves) zijn mogelijk onbetrouwbaar.")
    if pct_low_conf >= 20:
        _warnings.append(
            f"⚠ AI-staging confidence: {pct_low_conf:.0f}% van epochs "
            f"met confidence &lt;70%. Manuele verificatie aanbevolen.")
    if _warnings:
        _warn_style = ParagraphStyle("WarnBanner", fontName="Helvetica-Bold",
                                      fontSize=7.5, textColor=colors.white,
                                      backColor=colors.HexColor("#e74c3c"),
                                      leading=11, spaceBefore=2, spaceAfter=2,
                                      leftIndent=4, rightIndent=4)
        for _w in _warnings:
            story.append(Paragraph(_w, _warn_style))
        sp(0.1)

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

    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY — key findings at a glance (v0.8.30)
    # ═══════════════════════════════════════════════════════════════════════
    _rsum = pneumo.get("respiratory", {}).get("summary", {})
    _spo2s = pneumo.get("spo2", {}).get("summary", {})
    _arous = pneumo.get("arousal", {}).get("summary", {})
    _plms  = pneumo.get("plm", {}).get("summary", {})
    _hrs   = pneumo.get("heart_rate", {}).get("summary", {})

    if _rsum:
        _ahi_v = _f(_rsum, "ahi_total")
        _oahi_v = _f(_rsum, "oahi") or 0
        _cahi_v = _f(_rsum, "cahi") or 0
        _sev_txt = _sev(_ahi_v, lang) if _ahi_v is not None else "—"
        _sev_c   = _sev_clr(_ahi_v) if _ahi_v is not None else GR

        # Row 1: AHI (big) + severity
        _ahi_str = f"{_ahi_v:.1f}" if _ahi_v is not None else "—"
        _big = ParagraphStyle("BIG", fontName="Helvetica-Bold", fontSize=22,
                               textColor=_sev_c, alignment=TA_CENTER, leading=24)
        _med = ParagraphStyle("MED", fontName="Helvetica-Bold", fontSize=10,
                               textColor=TXT, alignment=TA_CENTER, leading=12)
        _sm2 = ParagraphStyle("SM2", fontName="Helvetica", fontSize=7,
                               textColor=GR, alignment=TA_CENTER, leading=9)

        def _kv_cell(val, label, unit=""):
            v = f"{val:.1f}{unit}" if val is not None else "—"
            return [Paragraph(v, _med), Paragraph(label, _sm2)]

        _exec_data = [
            # Row 1: AHI big + OAHI + CAHI + SpO2 + Arousal + PLM
            [
                [Paragraph(_ahi_str, _big), Paragraph(f"AHI — {_sev_txt}", _sm2)],
                _kv_cell(_oahi_v, "OAHI", "/h"),
                _kv_cell(_cahi_v, "CAI", "/h"),
                _kv_cell(_f(_spo2s, "baseline_spo2"), "SpO₂ base", "%"),
                _kv_cell(_f(_spo2s, "min_spo2"), "SpO₂ nadir", "%"),
                _kv_cell(_f(_arous, "arousal_index"), "Arousal idx", "/h"),
                _kv_cell(_f(_plms, "plmi"), "PLMI", "/h"),
            ]
        ]

        # Flatten: each cell is a list of [value_para, label_para] → stack in mini table
        _exec_cells = []
        for cell_parts in _exec_data[0]:
            mini = Table([cell_parts], colWidths=[2.2*cm])
            mini.setStyle(TableStyle([
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("TOPPADDING", (0,0), (-1,-1), 1),
                ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ]))
            _exec_cells.append(mini)

        _exec_tbl = Table([_exec_cells],
                          colWidths=[3.0*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.5*cm, 2.2*cm])
        _exec_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f0f4f8")),
            ("BOX", (0,0), (-1,-1), 1.0, _sev_c),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(_exec_tbl); sp(0.15)

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

    # ── Legende visueel overzicht ──────────────────────────────
    sp(0.1)
    leg_parts = [
        '<font size="6" color="#6b7a99"><b>EVENT:</b></font>',
        '<font size="6" color="#e74c3c">■</font><font size="6" color="#6b7a99"> OA (obstructief)</font>',
        '<font size="6" color="#3498db">■</font><font size="6" color="#6b7a99"> CA (centraal)</font>',
        '<font size="6" color="#9b59b6">■</font><font size="6" color="#6b7a99"> MA (gemengd)</font>',
        '<font size="6" color="#e67e22">■</font><font size="6" color="#6b7a99"> HYP (hypopnea)</font>',
        '<font size="6" color="#95a5a6">■</font><font size="6" color="#6b7a99"> FR (flow-reductie)</font>',
        '&nbsp;&nbsp;',
        '<font size="6" color="#6b7a99"><b>SpO2:</b></font>',
        '<font size="6" color="#e74c3c">---</font><font size="6" color="#6b7a99"> 90% drempel</font>',
        '<font size="6" color="#e74c3c">■</font><font size="6" color="#6b7a99"> &lt;90% zone</font>',
        '&nbsp;&nbsp;',
        '<font size="6" color="#6b7a99"><b>PHONO:</b></font>',
        '<font size="6" color="#e67e22">---</font><font size="6" color="#6b7a99"> P60 drempel</font>',
    ]
    story.append(Paragraph("  ".join(leg_parts), styles["SM"]))
    # v0.8.22: Positie-legende
    pos_leg = [
        '<font size="6" color="#6b7a99"><b>POS:</b></font>',
        '<font size="6" color="#2ecc71">■</font><font size="6" color="#6b7a99"> BUK (buiklig)</font>',
        '<font size="6" color="#3498db">■</font><font size="6" color="#6b7a99"> LNK (linker zijlig)</font>',
        '<font size="6" color="#e74c3c">■</font><font size="6" color="#6b7a99"> RUG (ruglig)</font>',
        '<font size="6" color="#9b59b6">■</font><font size="6" color="#6b7a99"> REC (rechter zijlig)</font>',
        '<font size="6" color="#95a5a6">■</font><font size="6" color="#6b7a99"> STA (staand/rechtop)</font>',
    ]
    story.append(Paragraph("  ".join(pos_leg), styles["SM"]))
    sp(0.1)

    story.append(PageBreak())

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

        # ── 1b. Stage transition matrix (v0.8.30) ────────────────────
        if timeline and len(timeline) > 10:
            _stages_order = ["W", "N1", "N2", "N3", "R"]
            _trans = {s1: {s2: 0 for s2 in _stages_order} for s1 in _stages_order}
            for i in range(len(timeline) - 1):
                s1, s2 = str(timeline[i]), str(timeline[i+1])
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
            rows=[[s.get("Channel",s.get("channel",s.get("Stage",s.get("stage","—"))))]+[_rnd(s.get(k)) for k in keys] for s in summ]
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
            rows=[[s.get("Channel",s.get("channel",s.get("Stage",s.get("stage","—"))))]+[_rnd(s.get(k)) for k in keys] for s in summ]
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
            f"{sa.get('n_artifact_epochs',0)} van {sa.get('n_total_epochs',0)} epochs ({pct}%) als artefact.",
            styles["B"]))
      else:
        story.append(Paragraph(f"{t('pdf_not_available', lang)}: {art.get('error','—')}",styles["SM"]))
      sp(0.15)
    # ── END polygraphy skip ──────────────────────────────────────

    # ── 7b. SIGNAAL KWALITEIT & CONFIDENCE ─────────────────────
    conf_rev = results.get("confidence_review", {})
    sig_q = results.get("signal_quality", {})
    sq_channels = sig_q.get("channels", {})
    sq_warnings = sig_q.get("montage_warnings", [])
    sq_grade = sig_q.get("overall_grade", "unknown")
    has_sq = (sq_grade != "unknown" and sq_channels) or conf_rev.get("n_low_confidence", 0) > 0

    if has_sq:
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
                g = ch_info.get("quality_grade", "?")
                g_clr = {"good":"#27ae60","acceptable":"#e67e22","poor":"#e74c3c"}.get(g,"#888")
                sq_rows.append([
                    ch_name,
                    f"{ch_info.get('flat_pct',0):.1f}%",
                    f"{ch_info.get('clip_pct',0):.1f}%",
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
        sev   = _sev(ahi, lang);  osev = _sev(oahi, lang);  clr = _sev_clr(ahi)
        # v0.8.22: Labels per studietype
        _ahi_lbl = "REI" if is_polygraphy else (f"{t('pdf_residual',lang)} AHI" if is_titration else "AHI")
        _oahi_lbl = "REI" if is_polygraphy else (f"{t('pdf_residual',lang)} OAHI" if is_titration else "OAHI")
        _therapy_note = f"  [{t('pdf_therapy',lang)}: {therapy_label}]" if is_titration else ""
        cb    = rsum.get("confidence_bands") or {}
        thr   = rsum.get("oahi_thresholds")  or {}
        avg_c = rsum.get("avg_classification_confidence")
        avg_s = f"{avg_c:.2f}" if avg_c else "—"

        # ── Classificatiebalk ────────────────────────────────────────────
        _active_prof = pneumo.get("meta", {}).get("scoring_profile", "standard")
        _prof_labels = {"strict": "Strict", "standard": "Standard (AASM 2.6)", "sensitive": "Sensitive"}
        _prof_lbl = _prof_labels.get(_active_prof, _active_prof)
        ab = Table([[Paragraph(
            f"{_ahi_lbl} = {ahi:.1f}/u  →  <b>{sev}</b>   |   "
            f"{_oahi_lbl} = {oahi:.1f}/u  →  <b>{osev}</b>{_therapy_note}"
            f"   |   Profile: {_prof_lbl}",
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
            [t("pdf_obstructive",lang),
             str(n_obstr), _v(rsum, "obstructive_index", fmt="{:.1f}"),
             str(_ev_conf("obstructive","high")),
             str(_ev_conf("obstructive","moderate")),
             str(_ev_conf("obstructive","borderline")),
             str(_ev_conf("obstructive","low"))],
            [t("pdf_central",lang),
             str(n_centr), _v(rsum, "central_index", fmt="{:.1f}"),
             str(_ev_conf("central","high")),
             str(_ev_conf("central","moderate")),
             str(_ev_conf("central","borderline")),
             str(_ev_conf("central","low"))],
            [t("pdf_mixed",lang),
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
        sp(0.12)

        # ── OAHI drempelgevoeligheidstabel ───────────────────────────────
        story.append(_hdr("OAHI — drempelgevoeligheid", color=BLUE)); sp(0.1)
        story.append(Paragraph(
            f"Gem. confidence apneas: <b>{avg_s}</b>  |  "
            f"Alle events: OAHI = {oahi_all:.1f}/u",
            styles["SM"])); sp(0.1)

        oahi_rows = [
            ["≥ 0.85 (hoge zekerheid)",
             f"{thr.get('0.85', '—'):.1f}" if isinstance(thr.get('0.85'), float) else "—",
             _sev(thr.get('0.85') or 0, lang),
             f"{cb.get('high',0)} events"],
            ["≥ 0.60 (matig + hoog)",
             f"{oahi60:.1f}",
             _sev(oahi60, lang),
             f"{cb.get('high',0) + cb.get('moderate',0)} events"],
            ["≥ 0.40 (incl. grensgebied)",
             f"{thr.get('0.40', '—'):.1f}" if isinstance(thr.get('0.40'), float) else "—",
             _sev(thr.get('0.40') or 0, lang),
             f"{cb.get('high',0)+cb.get('moderate',0)+cb.get('borderline',0)} events"],
            ["Alle events  ← officiële OAHI",
             f"{oahi:.1f}",
             _sev(oahi, lang),
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
            styles["SM"])); sp(0.1)

        # ── v0.8.22: RERA, RDI, REM/NREM AHI ──────────────────────────
        rera_n   = rsum.get("n_rera", 0) or 0
        rera_idx = rsum.get("rera_index", 0) or 0
        rdi_val  = rsum.get("rdi", 0) or 0
        rem_ahi  = rsum.get("rem_ahi")
        nrem_ahi = rsum.get("nrem_ahi")
        n_fri_pure = rsum.get("n_fri", 0) or 0

        story.append(_hdr("RERA, RDI en slaapstadium-AHI", color=BLUE)); sp(0.1)
        n_rera_fri  = rsum.get("n_rera_fri", 0) or 0
        n_rera_flat = rsum.get("n_rera_flattening", 0) or 0
        ext_rows = [
            ["RERA — amplitude-reductie + arousal (FRI)",  str(n_rera_fri), f"{n_rera_fri}"],
            ["RERA — flattening + arousal (flow limitation)", str(n_rera_flat), f"{n_rera_flat}"],
            ["RERA totaal",  str(rera_n), f"{rera_idx:.1f} /u"],
            ["FRI (flow-reductie zonder criteria)", str(n_fri_pure), ""],
            ["RDI (AHI + RERA-index)",          "", f"{rdi_val:.1f} /u"],
        ]
        story.append(KeepTogether([_tbl(
            [t("pdf_param",lang), "n", "Index"],
            ext_rows,
            [8, 2, 4])])); sp(0.1)

        stage_rows = [
            ["REM AHI",  f"{rem_ahi:.1f} /u" if rem_ahi is not None else "—"],
            ["NREM AHI", f"{nrem_ahi:.1f} /u" if nrem_ahi is not None else "—"],
        ]
        # Positional AHI (from position analysis)
        pos_sum = pneumo.get("position", {}).get("summary", {})
        ahi_pos = pos_sum.get("ahi_per_pos", {})
        if ahi_pos:
            for pos_name, pos_ahi in sorted(ahi_pos.items()):
                if pos_ahi is not None:
                    stage_rows.append([f"AHI {pos_name}", f"{pos_ahi:.1f} /u"])
        story.append(KeepTogether([_tbl(
            [t("pdf_param",lang), t("pdf_value",lang)],
            stage_rows,
            [8, 6])])); sp(0.1)

        story.append(Paragraph(
            f"<i>{t('pdf_rera_explanation',lang)} "
            "RDI = AHI + RERA-index. Klinisch relevant bij vermoeden UARS.</i>",
            styles["SM"])); sp(0.1)

        # ── SpO2 samplerate waarschuwing ────────────────────────────────
        if pneumo.get("spo2", {}).get("spo2_low_samplerate"):
            story.append(Paragraph(
                "<b><font color='#e74c3c'>⚠ SpO2 samplerate &lt; 0.33 Hz "
                "(&gt;3s averaging) — ODI en desaturatie-detectie mogelijk onderschat "
                "(AASM: max 3s averaging).</font></b>",
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
                 (f"{n_csr_fl} events  →  AHI {ahi_csr:.1f}/u" if ahi_csr else f"{n_csr_fl} events"),
                 t("pdf_fix3_desc",lang)],
                [t("pdf_fix4_name",lang),
                 f"{n_noise} ruis  +  {n_border} borderline",
                 (f"AHI excl. ruis (<0.40): {ahi_noise:.1f}/u" if ahi_noise else "conf<0.40 = signaalruis")],
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
            story.append(KeepTogether([_tbl(
                [t("pdf_correction",lang), t("pdf_impact",lang), t("pdf_explanation",lang)],
                corr_rows, [4.0, 3.5, 9.5])]))
            sp(0.15)
            story.append(Paragraph(
                f"<i>{t('pdf_disc_informative',lang)}</i>",
                styles["SM"])); sp(0.1)

        # ── Overige respiratoire indices ─────────────────────────────────
        story.append(KeepTogether([_tbl(
            [t("pdf_param", lang), t("pdf_value", lang), ""],
            [["AHI REM",   _v(rsum,"ahi_rem",fmt="{:.1f}"),  ""],
             ["AHI NREM",  _v(rsum,"ahi_nrem",fmt="{:.1f}"), ""],
             [t("pdf_avg_apnea_dur", lang), f"{rsum.get('avg_apnea_dur_s','—')} s", ""],
             ["Max. apnea-duur",            f"{rsum.get('max_apnea_dur_s','—')} s", ""],
            ], [8, 4, 5])])); sp(0.1)

        # Arousal / RERA / RDI (v0.8.22: skip bij polygrafie)
        arous=pneumo.get("arousal",{}); asum=arous.get("summary",{})
        if not is_polygraphy and arous.get("success") and asum:
            story.append(_hdr(t("rpt_sec8b", lang),color=BLUE)); sp(0.1)
            rdi=_f(asum,"rdi")
            story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang)],[
                ["Arousal index (AI)",       f"{asum.get('arousal_index','—')} /u"],
                [t("pdf_resp_arousals",lang),    str(asum.get("n_respiratory_arousals","—"))],
                [t("pdf_spont_arousals",lang),        str(asum.get("n_spontaneous_arousals","—"))],
                ["RERA's",                   str(asum.get("n_reras","—"))],
                ["RERA-index",               f"{asum.get('rera_index','—')} /u"],
                ["RDI (AHI + RERA)",         f"{rdi:.1f} /u" if rdi else "—"],
            ],[9,8])); sp(0.1)
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
                flat_label = "normaal" if flat_val < 0.25 else "verhoogd" if flat_val < 0.40 else "hoog (flow-limitatie)"
                rows.append([t("pdf_mean_flattening", lang), f"{flat_val:.2f} ({flat_label})"])
            story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], rows, [9, 8])); sp(0.15)

        if resp.get("dual_sensor"):
            story.append(Paragraph(
                "<i>Dual-sensor scoring: apneu op thermistor, hypopneu op nasale druk (AASM 2.6).</i>",
                styles["SM"]))

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
        story.append(_prof_tbl)
        sp(0.12)

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
            f"<i>{t('pdf_fri_note', lang)}</i>", styles["SM"])); sp(0.1)

    # ── 8e. Signaalvoorbeelden ────────────────────────────────
    if not is_polygraphy:
        epoch_imgs = _build_epoch_examples(results)
        if epoch_imgs:
            story.append(PageBreak())
            story.append(_hdr(t("rpt_sec8e", lang), color=BLUE)); sp(0.1)
            story.append(Paragraph(
                t("pdf_epoch_intro", lang), styles["SM"])); sp(0.15)
            for ev, img in epoch_imgs:
                story.append(KeepTogether([img, Spacer(1, 0.15*cm)]))
                sp(0.1)

    # ── 9. SpO2 ───────────────────────────────────────────────
    spo2=pneumo.get("spo2",{}); ss=spo2.get("summary",{})
    story.append(_hdr(t("rpt_sec9", lang))); sp(0.1)
    if spo2.get("success") and ss:
        story.append(_tbl([t("pdf_param",lang),t("pdf_value",lang),"Ref"],[
            [t('pdf_mean_spo2', lang),  f"{ss.get('mean_spo2', ss.get('avg_spo2','—'))} %", "≥ 95%"],
            [t('pdf_baseline_spo2', lang),    f"{ss.get('baseline_spo2','—')} %",  ""],
            [t('pdf_min_spo2', lang),   f"{ss.get('min_spo2','—')} %",  ""],
            [t("pdf_time_below90",lang),       f"{ss.get('pct_below_90','—')} %","< 1%"],
            ["ODI 3%",           f"{ss.get('odi_3pct','—')} /u",    "< 5/u"],
            ["ODI 4%",           f"{ss.get('odi_4pct','—')} /u",    "< 5/u"],
        ],[8,4.5,4.5]))
        ts=spo2.get("timeseries")
        if ts and len(ts)>10:
            sp(0.15)
            try: story.append(KeepTogether([_spo2_img(ts)]))
            except: pass
    else:
        story.append(Paragraph(f"SpO2: {spo2.get('error',t('pdf_no_channel',lang))}",styles["SM"]))
    sp(0.12)

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
            ["PLMI",                       f"{plmi:.1f} /u  —  {ps.get('plm_severity','—')}"],
        ],[9,8])); sp(0.1)

    # ── 10b. RONCHOPATHIE (snurk-analyse) ─────────────────────
    snore = pneumo.get("snore", {})
    snore_s = snore.get("summary", {})
    story.append(_hdr(t("rpt_sec10b", lang))); sp(0.1)
    if snore.get("success") and snore_s:
        story.append(_tbl([t("pdf_param", lang), t("pdf_value", lang)], [
            [t("pdf_snore_min", lang),     f"{snore_s.get('snore_min', '—')} min"],
            [t("pdf_snore_pct", lang),     f"{snore_s.get('snore_pct_tst', '—')} %"],
            [t("pdf_snore_index", lang),   f"{snore_s.get('snore_index', '—')} /u"],
        ], [9, 8])); sp(0.1)
    else:
        story.append(Paragraph(
            f"<i>{t('pdf_snore_no_data', lang)}</i>", styles["SM"])); sp(0.1)

    # Ensure arousal summary is available for diagnosis
    try:
        asum
    except NameError:
        asum = pneumo.get("arousal", {}).get("summary", {})

    # ── 10c. HARTRITME / ECG (v0.8.30) ──────────────────────────
    _hr = pneumo.get("heart_rate", {})
    _hr_sum = _hr.get("summary", {})
    if _hr.get("success") and _hr_sum:
        story.append(_hdr(t('pdf_ecg_hr_title', lang))); sp(0.05)
        _hr_rows = [
            [t("pdf_param", lang), t("pdf_value", lang), "Ref"],
        ]
        _hr_data = [
            [t('pdf_mean_hr', lang),    f"{_hr_sum.get('avg_hr', '—')} bpm",  "60–100"],
            [t('pdf_min_hr', lang),     f"{_hr_sum.get('min_hr', '—')} bpm",  ""],
            [t('pdf_max_hr', lang),     f"{_hr_sum.get('max_hr', '—')} bpm",  ""],
        ]
        if _hr_sum.get("bradycardia_episodes"):
            _hr_data.append([t('pdf_bradycardia', lang), str(_hr_sum["bradycardia_episodes"]), ""])
        if _hr_sum.get("tachycardia_episodes"):
            _hr_data.append([t('pdf_tachycardia', lang), str(_hr_sum["tachycardia_episodes"]), ""])
        story.append(_tbl(
            [t("pdf_param", lang), t("pdf_value", lang), "Ref"],
            _hr_data, [8, 4.5, 4.5])); sp(0.15)

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

    # v0.8.22: Besluit wordt NIET meer automatisch gegenereerd.
    # De arts vult het besluit manueel in via de rapport-editor.
    if manual_diag:
        story.append(Paragraph(f"<b>{t('concl_diagnosis', lang)}:</b> {manual_diag}", styles["B"]))
    else:
        story.append(Paragraph(
            f"<i>{t('concl_empty', lang)}</i>", styles["SM"]))

    sp(0.1)
    if manual_comment:
        story.append(Paragraph(f"<b>{t('comments', lang)}:</b> {manual_comment}", styles["B"]))
    sp(0.1)

    rec_date=(meta.get("analysis_timestamp","—") or "—")[:10]
    scorer=str(pat.get("scorer","—") or "—")
    sig=Table([[Paragraph(f"<b>{t('pdf_scorer',lang)}</b> {scorer}",styles["B"]),
                Paragraph(f"<b>{t('physician',lang)}:</b> _________________________",styles["B"]),
                Paragraph(f"<b>{t('date',lang)}:</b> {rec_date}",styles["B"])]],
              colWidths=[CW/3]*3)
    sig.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("BOX",(0,0),(-1,-1),0.4,GRID),("BACKGROUND",(0,0),(-1,-1),BGROW)]))
    story.append(sig); sp(0.15)

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
