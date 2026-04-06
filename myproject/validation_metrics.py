"""
validation_metrics.py — YASAFlaskified v0.8.29
============================================
Berekent validatie-metrics voor AI vs manuele scoring.

Gebruik:
    from validation_metrics import compute_staging_metrics, compute_ahi_agreement

Metrics:
  - Per-stage sensitivity, specificity, PPV, NPV
  - Overall accuracy, Cohen's kappa
  - Confusion matrix
  - Bland-Altman voor AHI
"""

import numpy as np
from collections import Counter

STAGES = ["W", "N1", "N2", "N3", "R"]


def _confusion_matrix(y_true, y_pred, labels=None):
    """Bereken confusion matrix."""
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    n = len(labels)
    label_idx = {l: i for i, l in enumerate(labels)}
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred):
        if t in label_idx and p in label_idx:
            cm[label_idx[t]][label_idx[p]] += 1
    return cm, labels


def _cohens_kappa(y_true, y_pred):
    """Cohen's kappa voor multi-class."""
    cm, labels = _confusion_matrix(y_true, y_pred, STAGES)
    n = cm.sum()
    if n == 0:
        return 0.0
    po = np.trace(cm) / n  # observed agreement
    pe = sum(cm[i, :].sum() * cm[:, i].sum() for i in range(len(labels))) / (n * n)
    if pe >= 1.0:
        return 1.0
    return float((po - pe) / (1 - pe))


def compute_staging_metrics(ai_stages, manual_stages):
    """
    Vergelijk AI-staging met manuele scoring.

    Parameters
    ----------
    ai_stages     : list[str] — AI-gegenereerde stages per epoch
    manual_stages : list[str] — Manueel gescoorde stages per epoch

    Returns
    -------
    dict met:
        accuracy       : float (0-1)
        kappa          : float (-1 tot 1)
        confusion_matrix : 5×5 matrix
        per_stage      : dict per stage met sensitivity, specificity, ppv, npv
        n_epochs       : int
        n_agree        : int
        n_disagree     : int
        disagreement_epochs : list[int] — epoch-indices waar AI ≠ manueel
    """
    n = min(len(ai_stages), len(manual_stages))
    ai = ai_stages[:n]
    man = manual_stages[:n]

    # Basics
    agree = sum(1 for a, m in zip(ai, man) if a == m)
    accuracy = agree / n if n > 0 else 0

    # Kappa
    kappa = _cohens_kappa(ai, man)

    # Confusion matrix
    cm, labels = _confusion_matrix(ai, man, STAGES)

    # Per-stage metrics
    per_stage = {}
    for i, stage in enumerate(STAGES):
        tp = cm[i][i]
        fn = cm[i, :].sum() - tp   # manueel = stage, AI ≠ stage
        fp = cm[:, i].sum() - tp   # AI = stage, manueel ≠ stage
        tn = n - tp - fn - fp

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0

        per_stage[stage] = {
            "sensitivity":  round(sensitivity, 3),
            "specificity":  round(specificity, 3),
            "ppv":          round(ppv, 3),
            "npv":          round(npv, 3),
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
            "n_manual":     int(cm[i, :].sum()),
            "n_ai":         int(cm[:, i].sum()),
        }

    # Disagreement epochs
    disagree_epochs = [i for i in range(n) if ai[i] != man[i]]

    return {
        "accuracy":             round(accuracy, 4),
        "kappa":                round(kappa, 4),
        "confusion_matrix":     cm.tolist(),
        "labels":               STAGES,
        "per_stage":            per_stage,
        "n_epochs":             n,
        "n_agree":              agree,
        "n_disagree":           n - agree,
        "disagreement_epochs":  disagree_epochs,
    }


def compute_ahi_agreement(ai_ahi_list, manual_ahi_list):
    """
    Bland-Altman analyse voor AHI agreement.

    Parameters
    ----------
    ai_ahi_list     : list[float] — AI AHI per studie
    manual_ahi_list : list[float] — Manueel AHI per studie

    Returns
    -------
    dict met:
        mean_diff    : float (bias)
        std_diff     : float
        loa_lower    : float (lower limit of agreement, -1.96 SD)
        loa_upper    : float (upper limit of agreement, +1.96 SD)
        correlation  : float (Pearson r)
        n_studies    : int
        severity_agreement : float (% studies met zelfde AASM-categorie)
    """
    ai = np.array(ai_ahi_list, dtype=float)
    man = np.array(manual_ahi_list, dtype=float)
    n = min(len(ai), len(man))
    ai, man = ai[:n], man[:n]

    diff = ai - man
    mean_diff = float(np.mean(diff))
    std_diff = float(np.std(diff, ddof=1))

    # Pearson correlation
    if np.std(ai) > 0 and np.std(man) > 0:
        corr = float(np.corrcoef(ai, man)[0, 1])
    else:
        corr = 0.0

    # Severity classification agreement
    def _classify(ahi):
        if ahi < 5:   return "normal"
        if ahi < 15:  return "mild"
        if ahi < 30:  return "moderate"
        return "severe"

    sev_agree = sum(1 for a, m in zip(ai, man) if _classify(a) == _classify(m))
    sev_pct = sev_agree / n if n > 0 else 0

    return {
        "n_studies":           n,
        "mean_diff":           round(mean_diff, 2),
        "std_diff":            round(std_diff, 2),
        "loa_lower":           round(mean_diff - 1.96 * std_diff, 2),
        "loa_upper":           round(mean_diff + 1.96 * std_diff, 2),
        "correlation":         round(corr, 3),
        "severity_agreement":  round(sev_pct, 3),
        "severity_kappa":      round(_cohens_kappa(
            [_classify(a) for a in ai],
            [_classify(m) for m in man]), 3),
    }


def compute_confidence_review_stats(hypnogram, confidence, threshold=0.70):
    """
    Bereken statistieken over low-confidence epochs.

    Parameters
    ----------
    hypnogram  : list[str] — stages per epoch
    confidence : dict — {stage_name: [probabilities per epoch]}
    threshold  : float — onder deze max-probability → "review aanbevolen"

    Returns
    -------
    dict met:
        n_epochs          : int
        n_low_confidence  : int
        pct_low_confidence: float
        low_conf_epochs   : list[int]
        per_stage_low     : dict {stage: count}
    """
    n = len(hypnogram)
    if not confidence:
        return {
            "n_epochs": n, "n_low_confidence": 0,
            "pct_low_confidence": 0, "low_conf_epochs": [],
            "per_stage_low": {},
        }

    # Bereken max probability per epoch
    stages_in_conf = list(confidence.keys())
    low_epochs = []
    per_stage = Counter()

    for i in range(n):
        max_prob = 0
        for stage_name in stages_in_conf:
            probs = confidence[stage_name]
            if i < len(probs):
                max_prob = max(max_prob, probs[i])
        if max_prob < threshold:
            low_epochs.append(i)
            per_stage[hypnogram[i]] += 1

    return {
        "n_epochs":           n,
        "n_low_confidence":   len(low_epochs),
        "pct_low_confidence": round(len(low_epochs) / n * 100, 1) if n > 0 else 0,
        "low_conf_epochs":    low_epochs,
        "per_stage_low":      dict(per_stage),
        "threshold":          threshold,
    }


def generate_bland_altman_plot(ai_ahi_list, manual_ahi_list, output_path, title="AHI: AI vs Manual Scoring"):
    """
    Genereer Bland-Altman plot als PNG.

    Parameters
    ----------
    ai_ahi_list     : list[float]
    manual_ahi_list : list[float]
    output_path     : str — pad voor PNG output
    title           : str

    Returns
    -------
    dict met plot_path en agreement stats
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ai = np.array(ai_ahi_list, dtype=float)
    man = np.array(manual_ahi_list, dtype=float)
    n = min(len(ai), len(man))
    ai, man = ai[:n], man[:n]

    means = (ai + man) / 2
    diffs = ai - man
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs, ddof=1))
    loa_upper = mean_diff + 1.96 * std_diff
    loa_lower = mean_diff - 1.96 * std_diff

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # ── Left: Bland-Altman ──
    ax1.scatter(means, diffs, s=40, alpha=0.6, c="#2980b9", edgecolors="#1a5276", linewidth=0.5)
    ax1.axhline(mean_diff, color="#e74c3c", linewidth=1.5, label=f"Bias: {mean_diff:.2f}")
    ax1.axhline(loa_upper, color="#f39c12", linewidth=1, linestyle="--",
                label=f"+1.96 SD: {loa_upper:.2f}")
    ax1.axhline(loa_lower, color="#f39c12", linewidth=1, linestyle="--",
                label=f"-1.96 SD: {loa_lower:.2f}")
    ax1.axhline(0, color="#bbb", linewidth=0.5)
    ax1.fill_between([means.min()-2, means.max()+2], loa_lower, loa_upper,
                     alpha=0.08, color="#f39c12")
    ax1.set_xlabel("Mean AHI (AI + Manual) / 2", fontsize=10)
    ax1.set_ylabel("Difference (AI - Manual)", fontsize=10)
    ax1.set_title("Bland-Altman Plot", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=8, loc="upper left")
    ax1.grid(alpha=0.3)

    # ── Right: Correlation scatter ──
    max_val = max(ai.max(), man.max()) * 1.1
    ax2.scatter(man, ai, s=40, alpha=0.6, c="#27ae60", edgecolors="#1a5276", linewidth=0.5)
    ax2.plot([0, max_val], [0, max_val], "k--", linewidth=0.8, alpha=0.5, label="Identity line")

    # Regression line
    if n > 2:
        z = np.polyfit(man, ai, 1)
        poly = np.poly1d(z)
        x_line = np.linspace(0, max_val, 100)
        r = float(np.corrcoef(ai, man)[0, 1]) if np.std(ai) > 0 else 0
        ax2.plot(x_line, poly(x_line), color="#e74c3c", linewidth=1.2,
                 label=f"r = {r:.3f}")

    ax2.set_xlabel("Manual AHI (/h)", fontsize=10)
    ax2.set_ylabel("AI AHI (/h)", fontsize=10)
    ax2.set_title("Correlation Plot", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=8, loc="upper left")
    ax2.set_xlim(0, max_val)
    ax2.set_ylim(0, max_val)
    ax2.set_aspect("equal")
    ax2.grid(alpha=0.3)

    fig.suptitle(title, fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return {
        "plot_path": output_path,
        "n": n,
        "bias": round(mean_diff, 2),
        "loa_lower": round(loa_lower, 2),
        "loa_upper": round(loa_upper, 2),
    }


def generate_confusion_matrix_plot(ai_stages, manual_stages, output_path,
                                    title="Sleep Staging: AI vs Consensus"):
    """
    Genereer confusion matrix heatmap als PNG.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cm, labels = _confusion_matrix(ai_stages, manual_stages, STAGES)
    n = cm.sum()

    fig, ax = plt.subplots(figsize=(7, 5.5))

    # Normalize per row (sensitivity view)
    cm_norm = np.zeros_like(cm, dtype=float)
    for i in range(len(labels)):
        row_sum = cm[i].sum()
        cm_norm[i] = cm[i] / row_sum if row_sum > 0 else 0

    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1, aspect="auto")

    # Labels
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel("AI Predicted", fontsize=12)
    ax.set_ylabel("Manual (Consensus)", fontsize=12)

    # Annotate cells
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = cm[i][j]
            pct = cm_norm[i][j]
            color = "white" if pct > 0.5 else "black"
            ax.text(j, i, f"{val}\n({pct:.0%})", ha="center", va="center",
                    fontsize=9, color=color, fontweight="bold" if i == j else "normal")

    fig.colorbar(im, ax=ax, label="Sensitivity", shrink=0.8)

    # Overall stats
    accuracy = np.trace(cm) / n if n > 0 else 0
    kappa = _cohens_kappa(ai_stages, manual_stages)
    ax.set_title(f"{title}\nAccuracy: {accuracy:.1%}  |  Cohen's κ: {kappa:.3f}  |  n={n} epochs",
                 fontsize=11, fontweight="bold")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return {"plot_path": output_path, "accuracy": round(accuracy, 4), "kappa": round(kappa, 4)}


# ═══════════════════════════════════════════════════════════════════════════
# v0.8.29: Event-level comparison (manual vs automated scoring)
# ═══════════════════════════════════════════════════════════════════════════

def compare_respiratory_events(
    manual_events: list[dict],
    auto_events: list[dict],
    tolerance_s: float = 5.0,
) -> dict:
    """Compare manual vs automated respiratory events with temporal matching.

    Each event dict must have at minimum: onset_s, duration_s, type.

    Parameters
    ----------
    manual_events : list of dict
        Reference (human-scored) events.
    auto_events : list of dict
        Algorithm-detected events.
    tolerance_s : float
        Maximum temporal distance (seconds) between event midpoints for a match.

    Returns
    -------
    dict with keys:
        matched (list of tuples), false_positives (list), false_negatives (list),
        type_mismatches (list), sensitivity, ppv, f1, n_manual, n_auto.
    """
    def _mid(ev):
        return ev["onset_s"] + ev["duration_s"] / 2

    manual_used = set()
    auto_used = set()
    matched = []
    type_mismatches = []

    # Greedy matching: for each manual event, find closest unmatched auto event
    for mi, m_ev in enumerate(manual_events):
        m_mid = _mid(m_ev)
        best_ai, best_dist = None, float("inf")
        for ai, a_ev in enumerate(auto_events):
            if ai in auto_used:
                continue
            dist = abs(_mid(a_ev) - m_mid)
            if dist < best_dist:
                best_dist = dist
                best_ai = ai
        if best_ai is not None and best_dist <= tolerance_s:
            manual_used.add(mi)
            auto_used.add(best_ai)
            pair = {
                "manual": m_ev,
                "auto": auto_events[best_ai],
                "time_diff_s": round(_mid(auto_events[best_ai]) - m_mid, 2),
                "type_match": _types_match(m_ev.get("type"), auto_events[best_ai].get("type")),
            }
            matched.append(pair)
            if not pair["type_match"]:
                type_mismatches.append(pair)

    false_negatives = [manual_events[i] for i in range(len(manual_events)) if i not in manual_used]
    false_positives = [auto_events[i] for i in range(len(auto_events)) if i not in auto_used]

    n_m = len(manual_events)
    n_a = len(auto_events)
    tp = len(matched)
    sens = tp / n_m if n_m > 0 else 0.0
    ppv = tp / n_a if n_a > 0 else 0.0
    f1 = 2 * sens * ppv / (sens + ppv) if (sens + ppv) > 0 else 0.0

    return {
        "matched": matched,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "type_mismatches": type_mismatches,
        "n_manual": n_m,
        "n_auto": n_a,
        "n_matched": tp,
        "n_false_positive": len(false_positives),
        "n_false_negative": len(false_negatives),
        "n_type_mismatch": len(type_mismatches),
        "sensitivity": round(sens, 4),
        "ppv": round(ppv, 4),
        "f1": round(f1, 4),
    }


def _types_match(t1: str | None, t2: str | None) -> bool:
    """Check if two event types are concordant (case-insensitive)."""
    if t1 is None or t2 is None:
        return False
    t1, t2 = t1.lower().strip(), t2.lower().strip()
    # Normalize aliases
    aliases = {"oa": "obstructive", "ca": "central", "ma": "mixed",
               "h": "hypopnea", "hyp": "hypopnea", "a": "apnea"}
    t1 = aliases.get(t1, t1)
    t2 = aliases.get(t2, t2)
    return t1 == t2


def compute_event_type_confusion(
    manual_events: list[dict],
    auto_events: list[dict],
    tolerance_s: float = 5.0,
) -> dict:
    """Per-type confusion matrix for matched respiratory events.

    Returns dict with confusion_matrix (dict of dicts), per-type sensitivity/PPV.
    """
    comparison = compare_respiratory_events(manual_events, auto_events, tolerance_s)
    types = ["obstructive", "central", "mixed", "hypopnea"]

    cm = {t: {t2: 0 for t2 in types + ["unmatched"]} for t in types + ["unmatched"]}

    for pair in comparison["matched"]:
        mt = pair["manual"].get("type", "unknown").lower()
        at = pair["auto"].get("type", "unknown").lower()
        mt = mt if mt in types else "unmatched"
        at = at if at in types else "unmatched"
        cm[mt][at] += 1

    for ev in comparison["false_negatives"]:
        mt = ev.get("type", "unknown").lower()
        mt = mt if mt in types else "unmatched"
        cm[mt]["unmatched"] += 1

    for ev in comparison["false_positives"]:
        at = ev.get("type", "unknown").lower()
        at = at if at in types else "unmatched"
        cm["unmatched"][at] += 1

    return {
        "confusion_matrix": cm,
        "event_comparison": comparison,
    }
