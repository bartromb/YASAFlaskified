/**
 * edf_viewer_v12.js — YASAFlaskified v12
 * =======================================
 * Multi-kanaal EDF-viewer MET event-overlay.
 * Uitbreiding van v11: events (OA/CA/MA/H/AR/RERA) als gekleurde
 * rechthoeken op de signalen, klikken om te togglen.
 *
 * Gebruik:
 *   const viewer = new EdfViewer("div-id", jobId, {
 *     scorer, lang,
 *     eventsEnabled: true,
 *     activeEventType: "OA",   // huidig geselecteerde tool
 *   });
 */

"use strict";

// ── Constanten ─────────────────────────────────────────────────────────────
const EDF_COLORS = {
  eeg:"#1a3a8f", eog:"#8e44ad", emg:"#27ae60",
  resp:"#e67e22", spo2:"#e74c3c", ecg:"#c0392b",
  snore:"#7f8c8d", pos:"#2980b9", other:"#95a5a6",
};

const EVENT_META = {
  OA:  { label:"Obstructief apnea", color:"#e74c3c", alpha:0.25, minDur:10 },
  CA:  { label:"Centraal apnea",    color:"#3498db", alpha:0.25, minDur:10 },
  MA:  { label:"Gemengd apnea",     color:"#9b59b6", alpha:0.25, minDur:10 },
  H:   { label:"Hypopnea",          color:"#f39c12", alpha:0.25, minDur:10 },
  AR:  { label:"Arousal",           color:"#2ecc71", alpha:0.30, minDur: 3 },
  RERA:{ label:"RERA",              color:"#1abc9c", alpha:0.25, minDur:10 },
};

const CH_LABELS = {
  eeg:"EEG", eog:"EOG", emg:"EMG", resp:"Resp",
  spo2:"SpO₂", ecg:"ECG", snore:"Snurk", pos:"Positie", other:"—",
};

const VI18N = {
  nl:{ loading:"Laden…", error:"Fout bij laden.",
       epoch:"Epoch", prev:"◀ Vorige", next:"Volgende ▶",
       zoom_in:"Zoom +", zoom_out:"Zoom −", ch_toggle:"Kanalen",
       no_data:"Geen signaaldata.",
       event_added:"Event toegevoegd", event_removed:"Event verwijderd",
       click_to_toggle:"Klik op signaal om event toe te voegen / te verwijderen",
       active_tool:"Actief:",
  },
  fr:{ loading:"Chargement…", error:"Erreur de chargement.",
       epoch:"Époque", prev:"◀ Précédent", next:"Suivant ▶",
       zoom_in:"Zoom +", zoom_out:"Zoom −", ch_toggle:"Canaux",
       no_data:"Aucune donnée de signal.",
       event_added:"Événement ajouté", event_removed:"Événement supprimé",
       click_to_toggle:"Cliquez sur le signal pour ajouter / supprimer un événement",
       active_tool:"Actif :",
  },
  en:{ loading:"Loading…", error:"Load error.",
       epoch:"Epoch", prev:"◀ Prev", next:"Next ▶",
       zoom_in:"Zoom +", zoom_out:"Zoom −", ch_toggle:"Channels",
       no_data:"No signal data.",
       event_added:"Event added", event_removed:"Event removed",
       click_to_toggle:"Click signal to add / remove event",
       active_tool:"Active:",
  },
};

// ── Viewer klasse ───────────────────────────────────────────────────────────
class EdfViewer {
  constructor(containerId, jobId, opts = {}) {
    this.container       = document.getElementById(containerId);
    this.jobId           = jobId;
    this.scorer          = opts.scorer        || null;
    this.lang            = VI18N[opts.lang]   || VI18N.nl;
    this.onEpochChange   = opts.onEpochChange || null;
    this.eventsEnabled   = opts.eventsEnabled !== false;
    this.activeEventType = opts.activeEventType || "OA";
    this.onStatsUpdate   = opts.onStatsUpdate  || null;

    // State
    this.info        = null;
    this.epochIdx    = 0;
    this.epochSpan   = 1;            // v13: hoeveel epochs tegelijk tonen (1,2,5,10)
    this.cache       = {};          // epoch_idx → signaaldata
    this.evCache     = {};          // epoch_idx → events[]
    this.hiddenChs   = new Set();
    this.ampScale    = 1.0;
    this.chAmpScale  = {};          // per-kanaal amplitude multiplier {ch_name: float}

    // Layout
    this.TRACK_H = 62;
    this.LABEL_W = 92;
    this.PAD_TOP = 4;
    this.PAD_BOT = 22;

    this._build();
    this._loadInfo();
    if (this.scorer) {
      this.scorer._onEpochSelect = (idx) => this.goTo(idx);
    }
  }

  // ── DOM ────────────────────────────────────────────────────────────────────
  _el(tag, cls="") {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    return e;
  }
  _btn(html, variant, fn, title="") {
    const b = this._el("button", `btn btn-sm btn-${variant}`);
    b.innerHTML = html; b.title = title;
    b.addEventListener("click", fn);
    return b;
  }

  _build() {
    this.container.innerHTML = "";
    this.container.style.fontFamily = "system-ui,sans-serif";

    // ── Toolbar signaalnavigatie ──────────────────────────────
    const tb = this._el("div","d-flex align-items-center gap-1 mb-1 flex-wrap");
    this.prevBtn   = this._btn(`◀ ${this.lang.prev}`,  "outline-secondary", () => this.goTo(this.epochIdx-this.epochSpan));
    this.epochLbl  = this._el("span","badge bg-primary px-3"); this.epochLbl.style.fontSize=".82rem";
    this.nextBtn   = this._btn(`${this.lang.next} ▶`,  "outline-secondary", () => this.goTo(this.epochIdx+this.epochSpan));
    const zIn      = this._btn("＋","outline-secondary",() => {this.ampScale*=1.4;this._redraw();},this.lang.zoom_in);
    const zOut     = this._btn("－","outline-secondary",() => {this.ampScale/=1.4;this._redraw();},this.lang.zoom_out);

    // v13: Epoch span zoom (hoeveel epochs tegelijk tonen)
    this.spanBtns = {};
    const spanGrp = this._el("span","d-inline-flex gap-0 ms-1");
    for (const n of [1,2,5,10]) {
      const b = this._btn(`${n*30}s`, n===1?"primary":"outline-primary",
        () => this.setEpochSpan(n), `${n} epoch(s)`);
      b.style.fontSize=".7rem"; b.style.padding="1px 6px";
      spanGrp.appendChild(b);
      this.spanBtns[n] = b;
    }

    this.chBtn     = this._btn(`☰ ${this.lang.ch_toggle}`,"outline-secondary",() => this._toggleChPanel());
    this.statusBadge = this._el("span","badge bg-secondary ms-auto");
    this.statusBadge.textContent = this.lang.loading;
    [this.prevBtn,this.epochLbl,this.nextBtn,zOut,zIn,spanGrp,this.chBtn,this.statusBadge].forEach(e=>tb.appendChild(e));
    this.container.appendChild(tb);

    // ── Event-toolbar ─────────────────────────────────────────
    if (this.eventsEnabled) {
      const etb = this._el("div","d-flex align-items-center gap-1 mb-1 flex-wrap");
      const lbl = this._el("span","text-muted small me-1");
      lbl.textContent = this.lang.active_tool;
      etb.appendChild(lbl);

      this.evtBtns = {};
      for (const [type, meta] of Object.entries(EVENT_META)) {
        const b = this._el("button","btn btn-sm");
        b.style.cssText = `background:${meta.color}22;border:2px solid ${meta.color};
          color:${meta.color};font-size:.72rem;padding:1px 8px;font-weight:600`;
        b.textContent = type;
        b.title = meta.label;
        b.dataset.evtype = type;
        b.addEventListener("click", () => this._selectTool(type));
        etb.appendChild(b);
        this.evtBtns[type] = b;
      }

      this.evtStatus = this._el("span","badge bg-light text-dark ms-auto border");
      this.evtStatus.style.fontSize = ".72rem";
      etb.appendChild(this.evtStatus);
      this.container.appendChild(etb);
      this._selectTool(this.activeEventType);
    }

    // ── Kanalen-panel ─────────────────────────────────────────
    this.chPanel = this._el("div","border rounded p-2 mb-1 bg-light small");
    this.chPanel.style.display = "none";
    this.container.appendChild(this.chPanel);

    // ── Canvas ────────────────────────────────────────────────
    this.wrap   = this._el("div","border rounded bg-white position-relative");
    this.wrap.style.overflowY = "auto";
    this.canvas = document.createElement("canvas");
    this.canvas.style.display = "block";
    this.wrap.appendChild(this.canvas);
    this.container.appendChild(this.wrap);

    // ── Tooltip ───────────────────────────────────────────────
    this.tooltip = this._el("div","position-absolute bg-dark text-white px-2 py-1 rounded small");
    this.tooltip.style.cssText="pointer-events:none;display:none;z-index:999;font-size:.72rem";
    this.wrap.appendChild(this.tooltip);

    // ── Event-feedback label ──────────────────────────────────
    this.evFeedback = this._el("div","text-success small mt-1");
    this.evFeedback.style.minHeight = "1.2em";
    this.container.appendChild(this.evFeedback);

    this._bindCanvas();
    window.addEventListener("resize", () => this._resize());
  }

  _selectTool(type) {
    this.activeEventType = type;
    for (const [t, b] of Object.entries(this.evtBtns||{})) {
      b.style.boxShadow = t===type ? `0 0 0 3px ${EVENT_META[t].color}88` : "none";
      b.style.fontWeight= t===type ? "900" : "600";
    }
    const meta = EVENT_META[type];
    if (this.evtStatus)
      this.evtStatus.textContent = `${meta.label} (${meta.minDur}s)`;
  }

  _buildChPanel() {
    if (!this.info) return;
    this.chPanel.innerHTML = "";

    const hdr = this._el("div","d-flex justify-content-between align-items-center mb-2");
    hdr.innerHTML = `<b>${this.lang.ch_toggle}</b>
      <span class="text-muted" style="font-size:.7rem">Klik naam = tonen/verbergen · ＋/－ = amplitude</span>`;
    this.chPanel.appendChild(hdr);

    // ── v0.8.2: Kanaalgroep-filters ──────────────────────────
    const GROUPS = [
      { id:"neuro",  label:"🧠 Neuro",  types:["eeg","eog","emg"], color:"#1a3a8f" },
      { id:"pneumo", label:"🫁 Pneumo", types:["resp","spo2"],     color:"#e67e22" },
      { id:"cardio", label:"❤ Cardio",  types:["ecg"],             color:"#c0392b" },
      { id:"overig", label:"📋 Overig",  types:["snore","pos","other"], color:"#7f8c8d" },
    ];

    const groupRow = this._el("div","d-flex flex-wrap gap-1 mb-2 pb-2");
    groupRow.style.borderBottom = "1px solid #dee2e6";

    // "Alle" toggle
    const allBtn = this._el("button","btn btn-sm");
    allBtn.style.cssText = `font-size:.7rem;padding:2px 8px;border:1px solid #333;background:#fff;color:#333;font-weight:600`;
    allBtn.textContent = "👁 Alle";
    allBtn.addEventListener("click",()=>{
      this.hiddenChs.clear();
      this._buildChPanel(); this._resize(); this._redraw();
    });
    groupRow.appendChild(allBtn);

    for (const grp of GROUPS) {
      // Find channels in this group
      const grpChs = this.info.channels.filter(ch =>
        grp.types.includes(this.info.ch_types[ch] || "other"));
      if (grpChs.length === 0) continue;

      const allHidden = grpChs.every(ch => this.hiddenChs.has(ch));
      const someHidden = grpChs.some(ch => this.hiddenChs.has(ch));

      const btn = this._el("button","btn btn-sm");
      const active = !allHidden;
      btn.style.cssText = `font-size:.7rem;padding:2px 8px;border:1px solid ${grp.color};
        background:${active ? grp.color : "#fff"};color:${active ? "#fff" : grp.color};
        font-weight:600;opacity:${allHidden ? "0.5" : "1"}`;
      btn.textContent = `${grp.label} (${grpChs.length})`;
      btn.title = `${allHidden ? "Toon" : "Verberg"} ${grp.label} kanalen`;

      btn.addEventListener("click",()=>{
        if (allHidden) {
          // Toon alleen deze groep, verberg alle andere
          this.info.channels.forEach(ch => this.hiddenChs.add(ch));
          grpChs.forEach(ch => this.hiddenChs.delete(ch));
        } else {
          // Toggle: als alles zichtbaar → verberg groep, anders → toon groep
          if (someHidden) {
            grpChs.forEach(ch => this.hiddenChs.delete(ch));
          } else {
            grpChs.forEach(ch => this.hiddenChs.add(ch));
          }
        }
        this._buildChPanel(); this._resize(); this._redraw();
      });
      groupRow.appendChild(btn);
    }
    this.chPanel.appendChild(groupRow);

    // ── Individuele kanalen ───────────────────────────────────
    const tbl = this._el("div","");
    for (const ch of this.info.channels) {
      const t = this.info.ch_types[ch]||"other";
      const color = EDF_COLORS[t];
      const row = this._el("div","d-flex align-items-center gap-1 mb-1");

      // Visibility toggle (channel name)
      const nameBtn = this._el("button","btn btn-sm");
      nameBtn.style.cssText=`background:${color}18;border:1px solid ${color};
        color:${color};font-size:.7rem;padding:1px 6px;min-width:90px;text-align:left;font-weight:600`;
      nameBtn.textContent = ch;
      nameBtn.addEventListener("click",()=>{
        if(this.hiddenChs.has(ch)){this.hiddenChs.delete(ch);nameBtn.style.opacity="1";}
        else{this.hiddenChs.add(ch);nameBtn.style.opacity="0.25";}
        this._resize(); this._redraw();
      });
      if (this.hiddenChs.has(ch)) nameBtn.style.opacity = "0.25";
      row.appendChild(nameBtn);

      // Amplitude decrease
      const minusBtn = this._el("button","btn btn-outline-secondary btn-sm");
      minusBtn.style.cssText="font-size:.65rem;padding:0 5px;line-height:1.4";
      minusBtn.textContent = "－";
      minusBtn.title = `${ch}: amplitude verlagen`;
      minusBtn.addEventListener("click",()=>{
        this.chAmpScale[ch] = (this.chAmpScale[ch]||1.0) / 1.5;
        ampLabel.textContent = `×${(this.chAmpScale[ch]||1).toFixed(1)}`;
        this._redraw();
      });
      row.appendChild(minusBtn);

      // Amplitude label
      const ampLabel = this._el("span","badge bg-light text-dark border");
      ampLabel.style.cssText="font-size:.65rem;min-width:36px;text-align:center";
      ampLabel.textContent = `×${(this.chAmpScale[ch]||1.0).toFixed(1)}`;
      row.appendChild(ampLabel);

      // Amplitude increase
      const plusBtn = this._el("button","btn btn-outline-secondary btn-sm");
      plusBtn.style.cssText="font-size:.65rem;padding:0 5px;line-height:1.4";
      plusBtn.textContent = "＋";
      plusBtn.title = `${ch}: amplitude verhogen`;
      plusBtn.addEventListener("click",()=>{
        this.chAmpScale[ch] = (this.chAmpScale[ch]||1.0) * 1.5;
        ampLabel.textContent = `×${(this.chAmpScale[ch]||1).toFixed(1)}`;
        this._redraw();
      });
      row.appendChild(plusBtn);

      // Reset button
      const resetBtn = this._el("button","btn btn-outline-warning btn-sm");
      resetBtn.style.cssText="font-size:.6rem;padding:0 4px;line-height:1.4";
      resetBtn.textContent = "↺";
      resetBtn.title = `${ch}: reset amplitude`;
      resetBtn.addEventListener("click",()=>{
        delete this.chAmpScale[ch];
        ampLabel.textContent = "×1.0";
        this._redraw();
      });
      row.appendChild(resetBtn);

      // Channel type label
      const typeLabel = this._el("span","text-muted");
      typeLabel.style.fontSize = ".65rem";
      typeLabel.textContent = CH_LABELS[t]||t;
      row.appendChild(typeLabel);

      tbl.appendChild(row);
    }
    this.chPanel.appendChild(tbl);

    // Reset all button
    const resetAll = this._btn("↺ Reset alle","outline-warning",()=>{
      this.chAmpScale = {};
      this._buildChPanel();
      this._redraw();
    });
    resetAll.style.cssText="font-size:.7rem;margin-top:6px";
    this.chPanel.appendChild(resetAll);
  }

  _toggleChPanel() {
    this.chPanel.style.display = this.chPanel.style.display==="none"?"block":"none";
  }

  // ── Afmeting ───────────────────────────────────────────────────────────────
  _resize() {
    if (!this.info) return;
    const visChs = this.info.channels.filter(c=>!this.hiddenChs.has(c));
    const nCh = visChs.length||1;
    const W   = Math.max(this.container.clientWidth-4, 400);
    const H   = this.PAD_TOP + nCh*this.TRACK_H + this.PAD_BOT;
    this.canvas.width=W; this.canvas.height=H;
    this.canvas.style.height=H+"px";
    this.wrap.style.maxHeight="540px";
    this._redraw();
  }

  // ── Navigatie ───────────────────────────────────────────────────────────────
  setEpochSpan(n) {
    this.epochSpan = n;
    // Update buttons
    for (const [span, b] of Object.entries(this.spanBtns)) {
      b.className = `btn btn-sm btn-${parseInt(span)===n?'primary':'outline-primary'}`;
    }
    this._resize();
    this.goTo(this.epochIdx);
  }

  goToTime(seconds) {
    if (!this.info) return;
    const epochLen = this.info.epoch_len_s || 30;
    const idx = Math.floor(seconds / epochLen);
    this.goTo(idx);
  }

  async goTo(idx) {
    if (!this.info) return;
    idx = Math.max(0, Math.min(idx, this.info.n_epochs - this.epochSpan));
    this.epochIdx = idx;
    this._updateLabel();

    // Laad alle epochs in de huidige span
    const loads = [];
    for (let i = idx; i < idx + this.epochSpan && i < this.info.n_epochs; i++) {
      if (!this.cache[i])
        loads.push(fetch(`/api/edf/${this.jobId}/epoch/${i}`)
          .then(r=>r.json()).then(d=>{this.cache[i]=d;}));
      if (!this.evCache[i])
        loads.push(fetch(`/api/edf/${this.jobId}/events/${i}`)
          .then(r=>r.json()).then(d=>{this.evCache[i]=d.events||[];}));
    }
    if (loads.length) {
      this._drawLoading();
      try { await Promise.all(loads); } catch(e) { this._drawError(e.message); return; }
    }

    this._redraw();
    this._prefetch(idx + this.epochSpan - 1);
    if (this.scorer && this.scorer.selected!==idx){
      this.scorer.selected=idx; this.scorer._draw(); this.scorer._scrollToEpoch(idx);
    }
    if (this.onEpochChange) this.onEpochChange(idx);
  }

  _prefetch(cur) {
    const nxt = cur+1;
    if (nxt<this.info.n_epochs) {
      if (!this.cache[nxt])
        fetch(`/api/edf/${this.jobId}/epoch/${nxt}`).then(r=>r.json())
          .then(d=>{this.cache[nxt]=d;}).catch(()=>{});
      if (!this.evCache[nxt])
        fetch(`/api/edf/${this.jobId}/events/${nxt}`).then(r=>r.json())
          .then(d=>{this.evCache[nxt]=d.events||[];}).catch(()=>{});
    }
  }

  _updateLabel() {
    if (!this.info) return;
    const t0h = (this.epochIdx*30/3600).toFixed(2);
    const endEp = Math.min(this.epochIdx + this.epochSpan, this.info.n_epochs);
    if (this.epochSpan === 1) {
      this.epochLbl.textContent=`${this.lang.epoch} ${this.epochIdx+1} / ${this.info.n_epochs}  (${t0h}h)`;
    } else {
      const t1h = (endEp*30/3600).toFixed(2);
      this.epochLbl.textContent=`${this.lang.epoch} ${this.epochIdx+1}–${endEp} / ${this.info.n_epochs}  (${t0h}–${t1h}h)`;
    }
    this.prevBtn.disabled = this.epochIdx===0;
    this.nextBtn.disabled = this.epochIdx>=this.info.n_epochs-this.epochSpan;
  }

  // ── Tekenen ────────────────────────────────────────────────────────────────
  _redraw() {
    if (!this.info) return;

    // Verzamel signalen en events over alle epochs in de span
    const firstSig = this.cache[this.epochIdx];
    if (!firstSig) { this._drawLoading(); return; }

    const totalEpochLen = (firstSig.epoch_len_s||30) * this.epochSpan;
    const t0 = firstSig.t0_s || 0;

    // Combineer signalen van alle epochs
    const combinedChannels = {};
    const combinedEvents = [];
    const visChs = this.info.channels.filter(c=>!this.hiddenChs.has(c)&&firstSig.channels[c]);

    for (let ei = 0; ei < this.epochSpan; ei++) {
      const epIdx = this.epochIdx + ei;
      const sig = this.cache[epIdx];
      const evs = this.evCache[epIdx] || [];
      if (!sig) break;
      for (const ch of visChs) {
        if (!combinedChannels[ch]) combinedChannels[ch] = [];
        const arr = sig.channels[ch] || [];
        combinedChannels[ch] = combinedChannels[ch].concat(Array.from(arr));
      }
      combinedEvents.push(...evs);
    }

    const ctx = this.canvas.getContext("2d");
    const W   = this.canvas.width;
    const H   = this.canvas.height;
    ctx.clearRect(0,0,W,H);
    ctx.fillStyle="#fafbfd"; ctx.fillRect(0,0,W,H);

    const usableW = W - this.LABEL_W;

    // ── Event-overlay (achtergrond) ──────────────────────────
    this._drawEventOverlay(ctx, combinedEvents, W, visChs.length, usableW, totalEpochLen, t0);

    // ── Signaalsporen ────────────────────────────────────────
    visChs.forEach((ch,i) => {
      const sig   = combinedChannels[ch];
      const ctype = this.info.ch_types[ch]||"other";
      const color = EDF_COLORS[ctype];
      const scale = (this.info.ch_scales[ch]||1.0) * this.ampScale * (this.chAmpScale[ch]||1.0);
      const trackY= this.PAD_TOP + i*this.TRACK_H;
      const midY  = trackY + this.TRACK_H/2;

      // Achtergrond baan
      ctx.fillStyle = i%2===0?"#fafbfd":"#f3f6fb";
      ctx.fillRect(this.LABEL_W, trackY, usableW, this.TRACK_H);

      // Label
      ctx.fillStyle=color; ctx.font="bold 10px system-ui"; ctx.textAlign="right";
      ctx.fillText(ch, this.LABEL_W-5, midY-2);
      ctx.fillStyle="#aaa"; ctx.font="9px system-ui";
      ctx.fillText(CH_LABELS[ctype]||ctype, this.LABEL_W-5, midY+8);

      // Per-kanaal amplitude indicator (als niet 1.0)
      const chScale = this.chAmpScale[ch];
      if (chScale && Math.abs(chScale - 1.0) > 0.05) {
        ctx.fillStyle="#e67e22"; ctx.font="bold 8px system-ui";
        ctx.fillText(`×${chScale.toFixed(1)}`, this.LABEL_W-5, midY+18);
      }

      // Middenlijn
      ctx.strokeStyle="#dde3ed"; ctx.lineWidth=0.5;
      ctx.beginPath(); ctx.moveTo(this.LABEL_W,midY); ctx.lineTo(W,midY); ctx.stroke();

      // Signaal (downsample als te veel punten)
      if (!sig||sig.length<2) return;
      ctx.strokeStyle=color; ctx.lineWidth=0.9;
      const maxPx = usableW * 2;
      const step = sig.length > maxPx ? Math.ceil(sig.length / maxPx) : 1;
      ctx.beginPath();
      for (let j=0;j<sig.length;j+=step) {
        const x = this.LABEL_W + (j/sig.length)*usableW;
        const norm = sig[j]/scale;
        const y    = midY - norm*(this.TRACK_H/2)*0.85;
        j===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      }
      ctx.stroke();

      // Baan-scheidingslijn
      ctx.strokeStyle="#d8e3ef"; ctx.lineWidth=0.4;
      ctx.beginPath(); ctx.moveTo(0,trackY+this.TRACK_H); ctx.lineTo(W,trackY+this.TRACK_H); ctx.stroke();
    });

    // ── Event-labels (voor op signalen) ─────────────────────
    this._drawEventLabels(ctx, combinedEvents, usableW, visChs.length, totalEpochLen, t0);

    // ── Epoch scheidslijnen (bij multi-epoch) ────────────────
    if (this.epochSpan > 1) {
      ctx.strokeStyle="#b0c4de"; ctx.lineWidth=1; ctx.setLineDash([4,4]);
      for (let ei = 1; ei < this.epochSpan; ei++) {
        const x = this.LABEL_W + (ei / this.epochSpan) * usableW;
        ctx.beginPath(); ctx.moveTo(x, this.PAD_TOP);
        ctx.lineTo(x, this.PAD_TOP + visChs.length * this.TRACK_H); ctx.stroke();
      }
      ctx.setLineDash([]);
    }

    // ── Tijdas + grid ────────────────────────────────────────
    this._drawTimeGrid(ctx, W, H, totalEpochLen, visChs.length);
    this._drawTimeAxis(ctx, W, H, totalEpochLen, t0);
  }

  _drawEventOverlay(ctx, events, W, nChs, usableW, epochLen, t0) {
    const totalH = nChs * this.TRACK_H;
    for (const ev of events) {
      const meta  = EVENT_META[ev.type];
      if (!meta) continue;
      // Positie binnen deze epoch
      const relStart = Math.max(0, ev.t_start - t0);
      const relEnd   = Math.min(epochLen, ev.t_end - t0);
      if (relEnd <= 0 || relStart >= epochLen) continue;
      const x1 = this.LABEL_W + (relStart/epochLen)*usableW;
      const x2 = this.LABEL_W + (relEnd  /epochLen)*usableW;
      const w  = Math.max(2, x2-x1);

      // Transparante overlay over alle banen
      ctx.fillStyle = meta.color + Math.round(meta.alpha*255).toString(16).padStart(2,"0");
      ctx.fillRect(x1, this.PAD_TOP, w, totalH);

      // Dunne gekleurde rand
      ctx.strokeStyle = meta.color + "cc";
      ctx.lineWidth   = 1.5;
      ctx.strokeRect(x1, this.PAD_TOP, w, totalH);
    }
  }

  _drawEventLabels(ctx, events, usableW, nChs, epochLen, t0) {
    const totalH = nChs * this.TRACK_H;
    ctx.font      = "bold 9px system-ui";
    ctx.textAlign = "left";
    for (const ev of events) {
      const meta = EVENT_META[ev.type]; if (!meta) continue;
      const relStart = Math.max(0, ev.t_start - t0);
      const relEnd   = Math.min(epochLen, ev.t_end - t0);
      if (relEnd<=0||relStart>=epochLen) continue;
      const x1 = this.LABEL_W + (relStart/epochLen)*usableW;
      const x2 = this.LABEL_W + (relEnd  /epochLen)*usableW;
      // Type-label bovenaan overlay
      ctx.fillStyle = meta.color;
      ctx.fillText(ev.type, x1+2, this.PAD_TOP+10);
      // Duur onderaan (als genoeg ruimte)
      if (x2-x1 > 22) {
        ctx.fillStyle="#555"; ctx.font="8px system-ui";
        ctx.fillText(`${ev.duration.toFixed(0)}s`, x1+2, this.PAD_TOP+totalH-3);
        ctx.font="bold 9px system-ui";
      }
      // Markeer manuele events met ✏
      if (ev.source==="manual") {
        ctx.fillStyle = meta.color;
        ctx.fillText("✏", x1+2, this.PAD_TOP+22);
      }
    }
  }

  _drawTimeGrid(ctx, W, H, epochLen, nChs) {
    ctx.strokeStyle="#dde3ed"; ctx.lineWidth=0.4;
    [5,10,15,20,25].forEach(s=>{
      if(s>=epochLen) return;
      const x = this.LABEL_W + (s/epochLen)*(W-this.LABEL_W);
      ctx.beginPath(); ctx.moveTo(x,this.PAD_TOP);
      ctx.lineTo(x, this.PAD_TOP+nChs*this.TRACK_H); ctx.stroke();
    });
  }

  _drawTimeAxis(ctx, W, H, epochLen, t0) {
    ctx.fillStyle="#888"; ctx.font="9px system-ui"; ctx.textAlign="center";
    [0,5,10,15,20,25,30].forEach(s=>{
      if(s>epochLen) return;
      const x = this.LABEL_W + (s/epochLen)*(W-this.LABEL_W);
      const t = t0+s; const mm=Math.floor(t/60); const ss=Math.round(t%60);
      ctx.fillText(`${mm}:${String(ss).padStart(2,"0")}`, x, H-5);
    });
  }

  _drawLoading() {
    const ctx=this.canvas.getContext("2d");
    ctx.clearRect(0,0,this.canvas.width,this.canvas.height);
    ctx.fillStyle="#f0f4f8"; ctx.fillRect(0,0,this.canvas.width,this.canvas.height);
    ctx.fillStyle="#888"; ctx.font="14px system-ui"; ctx.textAlign="center";
    ctx.fillText(this.lang.loading, this.canvas.width/2, this.canvas.height/2);
  }

  _drawError(msg) {
    const ctx=this.canvas.getContext("2d");
    ctx.clearRect(0,0,this.canvas.width,this.canvas.height);
    ctx.fillStyle="#fff5f5"; ctx.fillRect(0,0,this.canvas.width,this.canvas.height);
    ctx.fillStyle="#c0392b"; ctx.font="13px system-ui"; ctx.textAlign="center";
    ctx.fillText("⚠ "+msg, this.canvas.width/2, this.canvas.height/2);
  }

  // ── Info laden ─────────────────────────────────────────────────────────────
  async _loadInfo() {
    try {
      const resp = await fetch(`/api/edf/${this.jobId}/info`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      this.info = await resp.json();
      this._buildChPanel();
      this._resize();
      this.statusBadge.textContent = `${this.info.channels.length} kanalen`;
      this.statusBadge.className   = "badge bg-success ms-auto";
      await this.goTo(0);
    } catch(err) {
      this.statusBadge.textContent = this.lang.error;
      this.statusBadge.className   = "badge bg-danger ms-auto";
      this._drawError(this.lang.error+" "+err.message);
    }
  }

  // ── Klik-handler (toggle event) ────────────────────────────────────────────
  _bindCanvas() {
    this.canvas.addEventListener("mousemove", e => {
      if (!this.info||!this.cache[this.epochIdx]) return;
      const d   = this.cache[this.epochIdx];
      const totalLen = (d.epoch_len_s||30) * this.epochSpan;
      const rect= this.canvas.getBoundingClientRect();
      const cx  = e.clientX-rect.left;
      const usW = this.canvas.width-this.LABEL_W;
      const t   = Math.max(0,((cx-this.LABEL_W)/usW)*totalLen);
      if (cx<this.LABEL_W){this.tooltip.style.display="none"; return;}

      const visChs= this.info.channels.filter(c=>!this.hiddenChs.has(c));
      const chIdx = Math.floor((e.offsetY-this.PAD_TOP)/this.TRACK_H);
      const ch    = visChs[chIdx];
      const tAbs  = (d.t0_s||0)+t;
      const mm    = Math.floor(tAbs/60); const ss=(tAbs%60).toFixed(1);

      // Toon event-info — zoek in alle epochs van de span
      let evInfo = "";
      for (let ei=0; ei<this.epochSpan; ei++) {
        const evs = this.evCache[this.epochIdx+ei]||[];
        for (const ev of evs) {
          if (ev.t_start<=tAbs && ev.t_end>=tAbs) {
            evInfo = `  [${ev.type} ${ev.duration.toFixed(0)}s${ev.source==="manual"?" ✏":""}]`;
            break;
          }
        }
        if (evInfo) break;
      }
      this.tooltip.textContent = `${ch||""}  ${mm}:${String(ss).padStart(4,"0")}${evInfo}`;
      this.tooltip.style.display="block";
      this.tooltip.style.left=(e.offsetX+12)+"px";
      this.tooltip.style.top =(e.offsetY-20)+"px";
    });

    this.canvas.addEventListener("mouseleave",()=>{this.tooltip.style.display="none";});

    // ── Muiswiel: per-kanaal amplitude (op label) of globaal (op signaal) ──
    this.canvas.addEventListener("wheel", e => {
      if (!this.info) return;
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.offsetY;
      const visChs = this.info.channels.filter(c=>!this.hiddenChs.has(c));
      const chIdx = Math.floor((cy - this.PAD_TOP) / this.TRACK_H);
      const factor = e.deltaY < 0 ? 1.25 : 0.8;

      if (cx < this.LABEL_W && chIdx >= 0 && chIdx < visChs.length) {
        // Per-kanaal amplitude
        const ch = visChs[chIdx];
        this.chAmpScale[ch] = (this.chAmpScale[ch] || 1.0) * factor;
        // Feedback via tooltip
        this.tooltip.textContent = `${ch}: ×${(this.chAmpScale[ch]).toFixed(1)}`;
        this.tooltip.style.display = "block";
        this.tooltip.style.left = (e.offsetX + 12) + "px";
        this.tooltip.style.top = (e.offsetY - 20) + "px";
        this._redraw();
      } else {
        // Globale amplitude
        this.ampScale *= factor;
        this._redraw();
      }
    }, {passive: false});

    this.canvas.addEventListener("click", async e => {
      if (!this.eventsEnabled||!this.info) return;
      const d   = this.cache[this.epochIdx];
      if (!d) return;
      const rect= this.canvas.getBoundingClientRect();
      const cx  = e.clientX-rect.left;
      if (cx<this.LABEL_W) return;

      const usW    = this.canvas.width-this.LABEL_W;
      const totalLen = (d.epoch_len_s||30) * this.epochSpan;
      const relT   = ((cx-this.LABEL_W)/usW)*totalLen;
      const tAbs   = (d.t0_s||0)+relT;
      const meta   = EVENT_META[this.activeEventType];

      // POST naar toggle-endpoint
      try {
        const csrf = document.cookie.match(/csrf_token=([^;]+)/)?.[1]||"";
        const resp = await fetch(`/api/edf/${this.jobId}/events/toggle`,{
          method:"POST",
          headers:{"Content-Type":"application/json","X-CSRFToken":csrf},
          body: JSON.stringify({
            type:     this.activeEventType,
            t_click:  tAbs,
            duration: meta.minDur,
          }),
        });
        const result = await resp.json();
        if (!resp.ok) throw new Error(result.error||"Fout");

        // Herlaad events voor huidig epoch en aangrenzende
        await this._reloadEvents(this.epochIdx);
        this._redraw();

        // Feedback
        const action = result.action==="added"?this.lang.event_added:this.lang.event_removed;
        this.evFeedback.textContent = `${action}: ${meta.label} @ ${Math.floor(tAbs/60)}:${String(Math.round(tAbs%60)).padStart(2,"0")}`;
        this.evFeedback.className   = result.action==="added"?"text-success small mt-1":"text-warning small mt-1";

        // Stats bijwerken
        if (result.stats && this.onStatsUpdate) this.onStatsUpdate(result.stats);

      } catch(err) {
        this.evFeedback.textContent="❌ "+err.message;
        this.evFeedback.className  ="text-danger small mt-1";
      }
    });
  }

  async _reloadEvents(idx) {
    try {
      // Invalideer cache rondom gewijzigde epoch
      for (const i of [idx-1,idx,idx+1]) {
        if (i>=0) delete this.evCache[i];
      }
      const resp = await fetch(`/api/edf/${this.jobId}/events/${idx}`);
      const d    = await resp.json();
      this.evCache[idx] = d.events||[];
    } catch(e) { console.warn("Events herladen mislukt:", e); }
  }

  // ── Toetsenbord ────────────────────────────────────────────────────────────
  bindKeyboard() {
    document.addEventListener("keydown",e=>{
      if(e.code==="PageDown"){e.preventDefault();this.goTo(this.epochIdx+this.epochSpan);}
      if(e.code==="PageUp")  {e.preventDefault();this.goTo(this.epochIdx-this.epochSpan);}
      if(e.code==="Home")    {e.preventDefault();this.goTo(0);}
      if(e.code==="End")     {e.preventDefault();this.goTo(this.info?this.info.n_epochs-this.epochSpan:0);}
      // Sneltoetsen event-types
      const map={"KeyO":"OA","KeyC":"CA","KeyM":"MA","KeyH":"H","KeyA":"AR","KeyE":"RERA"};
      if(e.altKey&&map[e.code]){e.preventDefault();this._selectTool(map[e.code]);}
      // Zoom: Ctrl+1..4
      if(e.ctrlKey&&e.code==="Digit1"){e.preventDefault();this.setEpochSpan(1);}
      if(e.ctrlKey&&e.code==="Digit2"){e.preventDefault();this.setEpochSpan(2);}
      if(e.ctrlKey&&e.code==="Digit3"){e.preventDefault();this.setEpochSpan(5);}
      if(e.ctrlKey&&e.code==="Digit4"){e.preventDefault();this.setEpochSpan(10);}
    });
  }

  get currentEpoch() { return this.epochIdx; }
  clearCache() { this.cache={}; this.evCache={}; }
}
