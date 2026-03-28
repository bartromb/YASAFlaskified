/**
 * scorer_v12.js — YASAFlaskified v12
 * ====================================
 * Epoch-per-epoch AASM hypnogram editor.
 *
 * Gebruik:
 *   <script src="/static/scorer_v12.js"></script>
 *   <div id="hypno-editor"></div>
 *   <script>
 *     const scorer = new HypnoScorer("hypno-editor", hypnoData, jobId, lang);
 *   </script>
 *
 * hypnoData = array van strings: ["W","N1","N2","N3","R","W",...]  (AI-staging)
 * jobId     = string (job UUID)
 * lang      = "nl"|"fr"|"en"
 */

"use strict";

const STAGE_ORDER = ["W", "N1", "N2", "N3", "R"];
const STAGE_KEYS  = { "KeyW":"W", "Digit1":"N1", "Digit2":"N2",
                       "Digit3":"N3", "KeyR":"R" };
const STAGE_COLORS = {
  W:  "#e74c3c", N1: "#f39c12", N2: "#2980b9",
  N3: "#1a3a8f", R:  "#8e44ad"
};
const STAGE_Y = { W: 0, N1: 1, N2: 2, N3: 3, R: 4 };

const I18N = {
  nl: { save:"Opslaan & hergeneren", saved:"Opgeslagen!", saving:"Bezig...",
        undo:"Ongedaan (Ctrl+Z)", reset:"Terug naar AI",
        changes:"wijzigingen t.o.v. AI", epoch:"Epoch",
        help:"Klik epoch | Toetsenbord: W · 1=N1 · 2=N2 · 3=N3 · R | Ctrl+Z=ongedaan",
        confirm_reset:"Alle manuele correcties wissen en terugkeren naar AI-staging?" },
  fr: { save:"Enregistrer & regénérer", saved:"Enregistré !", saving:"En cours...",
        undo:"Annuler (Ctrl+Z)", reset:"Revenir à l'IA",
        changes:"modifications vs IA", epoch:"Époque",
        help:"Cliquez époque | Clavier: W · 1=N1 · 2=N2 · 3=N3 · R | Ctrl+Z=annuler",
        confirm_reset:"Effacer toutes les corrections et revenir au staging IA ?" },
  en: { save:"Save & regenerate", saved:"Saved!", saving:"Saving...",
        undo:"Undo (Ctrl+Z)", reset:"Reset to AI",
        changes:"changes vs AI", epoch:"Epoch",
        help:"Click epoch | Keyboard: W · 1=N1 · 2=N2 · 3=N3 · R | Ctrl+Z=undo",
        confirm_reset:"Clear all manual corrections and revert to AI staging?" },
};

class HypnoScorer {
  constructor(containerId, aiStages, jobId, lang="nl") {
    this.container  = document.getElementById(containerId);
    this.aiStages   = [...aiStages];           // AI origineel — nooit wijzigen
    this.stages     = [...aiStages];           // actief (manueel)
    this.jobId      = jobId;
    this.lang       = I18N[lang] || I18N.nl;
    this.history    = [];                      // undo-stack: [{idx, from, to}]
    this.selected   = null;                    // huidig geselecteerde epoch-index
    this.isDragging = false;
    this.dragStage  = null;

    this._build();
    this._bindKeys();
  }

  // ── DOM bouwen ────────────────────────────────────────────────────────────

  _build() {
    this.container.innerHTML = "";
    this.container.style.cssText = "font-family:system-ui,sans-serif;user-select:none";

    // Toolbar
    const toolbar = this._el("div", "d-flex align-items-center gap-2 mb-2 flex-wrap");
    this._btnGroup(toolbar);
    this.changesLabel = this._el("span","badge bg-secondary ms-auto");
    toolbar.appendChild(this.changesLabel);
    this.container.appendChild(toolbar);

    // Help-tekst
    const help = this._el("p","text-muted small mb-1");
    help.textContent = this.lang.help;
    this.container.appendChild(help);

    // Canvas wrapper
    this.canvasWrap = this._el("div","position-relative border rounded bg-white");
    this.canvasWrap.style.cssText = "overflow-x:auto;overflow-y:hidden";
    this.canvas = document.createElement("canvas");
    this.canvasWrap.appendChild(this.canvas);
    this.container.appendChild(this.canvasWrap);

    // Tooltip
    this.tooltip = this._el("div","position-absolute bg-dark text-white px-2 py-1 rounded small");
    this.tooltip.style.cssText = "pointer-events:none;display:none;z-index:999;font-size:.75rem";
    this.canvasWrap.appendChild(this.tooltip);

    // Status label
    this.statusLabel = this._el("p","text-muted small mt-1 mb-0 text-end");
    this.container.appendChild(this.statusLabel);

    this._resize();
    window.addEventListener("resize", () => this._resize());
    this._bindCanvas();
    this._draw();
    this._updateChanges();
  }

  _el(tag, cls="") {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    return e;
  }

  _btnGroup(parent) {
    // Stage-knoppen
    const grp = this._el("div","btn-group btn-group-sm");
    for (const s of STAGE_ORDER) {
      const b = this._el("button","btn btn-outline-secondary");
      b.style.borderColor = STAGE_COLORS[s];
      b.style.color       = STAGE_COLORS[s];
      b.innerHTML = `<b>${s}</b>`;
      b.title = s + (s==="W"?" (W)":s==="R"?" (R)":" ("+s.slice(1)+")");
      b.addEventListener("click", () => {
        if (this.selected !== null) this._setStage(this.selected, s);
      });
      grp.appendChild(b);
    }
    parent.appendChild(grp);

    // Undo
    const undoBtn = this._el("button","btn btn-sm btn-outline-secondary");
    undoBtn.innerHTML = `↩ ${this.lang.undo}`;
    undoBtn.addEventListener("click", () => this._undo());
    parent.appendChild(undoBtn);

    // Reset
    const resetBtn = this._el("button","btn btn-sm btn-outline-warning");
    resetBtn.textContent = `⟲ ${this.lang.reset}`;
    resetBtn.addEventListener("click", () => {
      if (confirm(this.lang.confirm_reset)) {
        this.stages  = [...this.aiStages];
        this.history = [];
        this._draw();
        this._updateChanges();
      }
    });
    parent.appendChild(resetBtn);

    // Save
    this.saveBtn = this._el("button","btn btn-sm btn-success");
    this.saveBtn.innerHTML = `💾 ${this.lang.save}`;
    this.saveBtn.addEventListener("click", () => this._save());
    parent.appendChild(this.saveBtn);
  }

  // ── Canvas dimensionering ────────────────────────────────────────────────

  _resize() {
    const n   = this.stages.length;
    const W   = Math.max(this.container.clientWidth - 4, 400);
    const EPW = Math.max(2, Math.min(12, Math.floor((W - 40) / n)));
    const H   = 160;
    this.epw  = EPW;
    this.offX = 38;  // ruimte voor y-labels
    this.offY = 10;
    this.plotH= H - 30;
    this.canvas.width  = this.offX + n * EPW;
    this.canvas.height = H;
    this.canvas.style.height = H + "px";
    this.canvas.style.display= "block";
    this._draw();
  }

  // ── Tekenen ──────────────────────────────────────────────────────────────

  _draw() {
    const ctx = this.canvas.getContext("2d");
    const n   = this.stages.length;
    const W   = this.canvas.width;
    const H   = this.canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Achtergrond
    ctx.fillStyle = "#fafbfd";
    ctx.fillRect(0, 0, W, H);

    // Y-gridlijnen + labels
    for (const [s, yi] of Object.entries(STAGE_Y)) {
      const y = this._yPx(yi);
      ctx.strokeStyle = "#e8eef5";
      ctx.lineWidth   = 0.5;
      ctx.beginPath(); ctx.moveTo(this.offX, y); ctx.lineTo(W, y); ctx.stroke();
      ctx.fillStyle   = STAGE_COLORS[s];
      ctx.font        = "bold 10px system-ui";
      ctx.textAlign   = "right";
      ctx.fillText(s, this.offX - 4, y + 4);
    }

    // Gekleurde epoch-blokjes
    for (let i = 0; i < n; i++) {
      const s   = this.stages[i];
      const ai  = this.aiStages[i];
      const x   = this.offX + i * this.epw;
      const y   = this._yPx(STAGE_Y[s]);
      const bh  = Math.max(3, this.plotH / 8);

      // Achtergrond blokje (kleur stadium)
      ctx.fillStyle   = STAGE_COLORS[s] + "99";
      ctx.fillRect(x, y - bh/2, this.epw, bh);

      // Manueel gewijzigde epoch: dikke rand + lichte achtergrond
      if (s !== ai) {
        ctx.strokeStyle = STAGE_COLORS[s];
        ctx.lineWidth   = 1.5;
        ctx.strokeRect(x + 0.5, y - bh/2 + 0.5, this.epw - 1, bh - 1);
      }

      // Geselecteerde epoch: highlight
      if (i === this.selected) {
        ctx.fillStyle = "rgba(255,255,255,0.5)";
        ctx.fillRect(x, 0, this.epw, H - 25);
        ctx.strokeStyle = "#333";
        ctx.lineWidth   = 1.5;
        ctx.strokeRect(x + 0.5, 0.5, this.epw - 1, H - 26);
      }
    }

    // Hypnogramlijn (AI = gestippeld grijs, manueel = vol blauw)
    this._drawLine(ctx, this.aiStages, "#b0bec5", true);
    this._drawLine(ctx, this.stages,   "#1a3a8f", false);

    // X-as tijdlabels
    ctx.fillStyle  = "#888";
    ctx.font       = "9px system-ui";
    ctx.textAlign  = "center";
    const step = Math.max(1, Math.round(n / 10));
    for (let i = 0; i <= n; i += step) {
      const x = this.offX + i * this.epw;
      const h = (i * 30 / 3600).toFixed(1);
      ctx.fillText(h + "h", x, H - 5);
    }
  }

  _drawLine(ctx, stages, color, dashed) {
    ctx.strokeStyle = color;
    ctx.lineWidth   = dashed ? 0.8 : 1.8;
    if (dashed) ctx.setLineDash([3, 3]); else ctx.setLineDash([]);
    ctx.beginPath();
    for (let i = 0; i < stages.length; i++) {
      const x = this.offX + i * this.epw + this.epw / 2;
      const y = this._yPx(STAGE_Y[stages[i]]);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  _yPx(yi) {
    // yi=0(W) bovenaan, yi=4(R) onderaan (slaapdiepte)
    const usableH = this.plotH;
    return this.offY + (yi / 4) * usableH;
  }

  // ── Interactie ───────────────────────────────────────────────────────────

  _epochAt(x) {
    const rect = this.canvas.getBoundingClientRect();
    const cx   = x - rect.left;
    const i    = Math.floor((cx - this.offX) / this.epw);
    return (i >= 0 && i < this.stages.length) ? i : null;
  }

  _bindCanvas() {
    this.canvas.addEventListener("mousemove", e => {
      const i = this._epochAt(e.clientX);
      if (i === null) { this.tooltip.style.display = "none"; return; }
      const ai = this.aiStages[i]; const man = this.stages[i];
      this.tooltip.textContent =
        `${this.lang.epoch} ${i + 1}  |  AI: ${ai}  →  ${man !== ai ? "✏ " : ""}${man}`;
      this.tooltip.style.display = "block";
      this.tooltip.style.left    = (e.offsetX + 10) + "px";
      this.tooltip.style.top     = (e.offsetY - 24) + "px";
      if (this.isDragging && this.dragStage) this._setStage(i, this.dragStage);
    });

    this.canvas.addEventListener("mouseleave", () => {
      this.tooltip.style.display = "none";
      this.isDragging = false;
    });

    this.canvas.addEventListener("mousedown", e => {
      const i = this._epochAt(e.clientX);
      if (i === null) return;
      this.selected   = i;
      this.isDragging = true;
      // Cyclen door stages bij klikken op al geselecteerde epoch
      if (i === this.selected) {
        const cur  = STAGE_ORDER.indexOf(this.stages[i]);
        this.dragStage = STAGE_ORDER[(cur + 1) % STAGE_ORDER.length];
      } else {
        this.dragStage = this.stages[i];
      }
      this._setStage(i, this.dragStage);
    });

    this.canvas.addEventListener("mouseup", () => { this.isDragging = false; });

    this.canvas.addEventListener("click", e => {
      const i = this._epochAt(e.clientX);
      if (i === null) return;
      this.selected = i;
      this._draw();
    });
  }

  _bindKeys() {
    document.addEventListener("keydown", e => {
      // Ctrl+Z = undo
      if ((e.ctrlKey || e.metaKey) && e.code === "KeyZ") {
        e.preventDefault(); this._undo(); return;
      }
      if (this.selected === null) return;
      const stage = STAGE_KEYS[e.code];
      if (stage) { e.preventDefault(); this._setStage(this.selected, stage); }
      // Pijltoetsen: navigeer epoch
      if (e.code === "ArrowRight") {
        e.preventDefault();
        this.selected = Math.min(this.stages.length - 1, this.selected + 1);
        this._scrollToEpoch(this.selected); this._draw();
      }
      if (e.code === "ArrowLeft") {
        e.preventDefault();
        this.selected = Math.max(0, this.selected - 1);
        this._scrollToEpoch(this.selected); this._draw();
      }
    });
  }

  _scrollToEpoch(i) {
    const x = this.offX + i * this.epw;
    this.canvasWrap.scrollLeft = Math.max(0, x - this.canvasWrap.clientWidth / 2);
  }

  // ── Staging aanpassen ────────────────────────────────────────────────────

  _setStage(idx, newStage) {
    const old = this.stages[idx];
    if (old === newStage) return;
    this.history.push({ idx, from: old, to: newStage });
    this.stages[idx] = newStage;
    this._draw();
    this._updateChanges();
  }

  _undo() {
    const last = this.history.pop();
    if (!last) return;
    this.stages[last.idx] = last.from;
    this.selected = last.idx;
    this._draw();
    this._updateChanges();
  }

  _updateChanges() {
    let n = 0;
    for (let i = 0; i < this.stages.length; i++)
      if (this.stages[i] !== this.aiStages[i]) n++;
    this.changesLabel.textContent = `${n} ${this.lang.changes}`;
    this.changesLabel.className   = n > 0
      ? "badge bg-warning text-dark ms-auto"
      : "badge bg-secondary ms-auto";
  }

  // ── Opslaan ──────────────────────────────────────────────────────────────

  async _save() {
    this.saveBtn.disabled    = true;
    this.saveBtn.textContent = this.lang.saving;
    this.statusLabel.textContent = "";

    // Bouw corrections-object (enkel gewijzigde epochs)
    const corrections = {};
    for (let i = 0; i < this.stages.length; i++) {
      if (this.stages[i] !== this.aiStages[i])
        corrections[i] = this.stages[i];
    }

    try {
      const resp = await fetch(`/api/scoring/${this.jobId}/save`, {
        method:  "POST",
        headers: { "Content-Type":"application/json",
                   "X-CSRFToken": document.cookie.match(/csrf_token=([^;]+)/)?.[1] || "" },
        body: JSON.stringify({
          hypnogram:    this.stages,
          corrections:  corrections,
          n_changes:    Object.keys(corrections).length,
        }),
      });
      const data = await resp.json();
      if (data.success) {
        this.statusLabel.textContent = "✅ " + this.lang.saved;
        this.statusLabel.className   = "text-success small mt-1 mb-0 text-end";
        // Herlaad na 2s om nieuw PDF-rapport te tonen
        setTimeout(() => window.location.reload(), 2000);
      } else {
        throw new Error(data.error || "Server error");
      }
    } catch (err) {
      this.statusLabel.textContent = "❌ " + err.message;
      this.statusLabel.className   = "text-danger small mt-1 mb-0 text-end";
    }

    this.saveBtn.disabled    = false;
    this.saveBtn.innerHTML   = `💾 ${this.lang.save}`;
  }

  // ── Publieke methoden ────────────────────────────────────────────────────

  getStages()      { return [...this.stages]; }
  getCorrections() {
    const c = {};
    for (let i = 0; i < this.stages.length; i++)
      if (this.stages[i] !== this.aiStages[i]) c[i] = this.stages[i];
    return c;
  }
}

// ── v11: viewer-sync extensie ─────────────────────────────────────────────
// HypnoScorer emits _onEpochSelect(idx) wanneer een epoch geselecteerd wordt.
// EdfViewer registreert zich via scorer._onEpochSelect = (idx) => viewer.goTo(idx)

(function patchHypnoScorerV11() {
  const origClick = HypnoScorer.prototype._bindCanvas;
  HypnoScorer.prototype._bindCanvas = function() {
    origClick.call(this);
    // Patch mousedown om ook _onEpochSelect te triggeren
    const canvas = this.canvas;
    canvas.addEventListener("mousedown", e => {
      const i = this._epochAt(e.clientX);
      if (i !== null && typeof this._onEpochSelect === "function") {
        this._onEpochSelect(i);
      }
    });
    // Patch pijltoets-navigatie
    const origKeys = this._bindKeys.bind(this);
    document.addEventListener("keydown", e => {
      if (e.code === "ArrowRight" || e.code === "ArrowLeft") {
        setTimeout(() => {
          if (typeof this._onEpochSelect === "function" && this.selected !== null) {
            this._onEpochSelect(this.selected);
          }
        }, 10);
      }
    });
  };
})();
