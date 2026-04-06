"""
conclusions.py — YASAFlaskified v0.8.25
======================================
Centralized clinical conclusion logic.

Used by both generate_pdf_report.py and generate_psg_report.py.
All translatable strings come from i18n.py — no hardcoded text here.

Usage:
    from conclusions import generate_conclusions
    parts = generate_conclusions(ahi, oahi, plmi, se, tst, ai, bmi,
                                 spo2_nadir, spo2_pct_below90,
                                 csr_info, lang="nl")
    for part in parts:
        print(part["title"])   # bold heading
        print(part["body"])    # description
        print(part["tx"])      # treatment suggestion (may be empty)
"""

from i18n import t


def generate_conclusions(
    ahi: float,
    oahi: float = 0,
    plmi: float = 0,
    se: float = 100,
    tst: float = 480,
    ai: float = 0,
    bmi: float = None,
    spo2_nadir: float = None,
    spo2_pct_below90: float = None,
    csr_info: dict = None,
    lang: str = "nl",
) -> list:
    """
    Generate structured conclusion parts based on clinical indices.

    Returns a list of dicts, each with:
        title : str   — bold conclusion heading
        body  : str   — descriptive text with values
        tx    : str   — treatment suggestion (empty string if none)
        type  : str   — "normal" | "osas" | "plm" | "insomnia" | "csr"
    """
    parts = []

    # ── OSAS / Normal ────────────────────────────────────────
    if ahi < 5 and plmi < 15 and se >= 85:
        parts.append({
            "type":  "normal",
            "title": t("concl_normal_title", lang),
            "body":  t("concl_normal_body", lang),
            "tx":    "",
        })
    else:
        if ahi >= 5:
            if ahi < 15:
                title = t("concl_mild_title", lang)
                body = (f"AHI: {ahi:.1f} /u, OAHI: {oahi:.1f} /u. "
                        + t("concl_mild_body", lang))
                tx = t("concl_mild_tx", lang)
                if bmi and bmi > 28:
                    tx += f" {t('concl_weight', lang)} (BMI: {bmi:.1f} kg/m²)."
            elif ahi < 30:
                title = t("concl_mod_title", lang)
                body = (f"AHI: {ahi:.1f} /u, OAHI: {oahi:.1f} /u. "
                        + t("concl_mod_body", lang)
                        + f" (arousal index: {ai:.1f} /u).")
                tx = t("concl_mod_tx", lang)
                if bmi and bmi > 28:
                    tx += f" {t('concl_weight', lang)} (BMI: {bmi:.1f} kg/m²)."
            else:
                title = t("concl_sev_title", lang)
                body = (f"AHI: {ahi:.1f} /u, OAHI: {oahi:.1f} /u. "
                        + t("concl_sev_body", lang)
                        + f" (arousal index: {ai:.1f} /u).")
                if spo2_nadir is not None and spo2_nadir < 90:
                    body += (f" {t('concl_sev_desat', lang)}: "
                             f"SpO₂ nadir {spo2_nadir:.0f}%")
                    if spo2_pct_below90 is not None:
                        body += f", < 90%: {spo2_pct_below90:.1f}%"
                    body += "."
                tx = t("concl_sev_tx", lang)
                if bmi and bmi > 28:
                    tx += f" {t('concl_weight_essential', lang)} (BMI: {bmi:.1f} kg/m²)."

            parts.append({
                "type":  "osas",
                "title": title,
                "body":  body,
                "tx":    tx,
            })

    # ── PLM ──────────────────────────────────────────────────
    if plmi >= 15:
        parts.append({
            "type":  "plm",
            "title": t("concl_plm_title", lang),
            "body":  (f"PLM-index: {plmi:.1f} /u. "
                      + t("concl_plm_body", lang)),
            "tx":    t("concl_plm_tx", lang),
        })

    # ── Insomnia ─────────────────────────────────────────────
    if se < 85 or tst < 360:
        details = []
        if se < 85:
            details.append(t("concl_insomnia_se", lang).format(se=se))
        if tst < 360:
            details.append(t("concl_insomnia_tst", lang).format(tst=tst))
        parts.append({
            "type":  "insomnia",
            "title": t("concl_insomnia_title", lang),
            "body":  (t("concl_insomnia_quality", lang) + ": "
                      + ", ".join(details) + "."),
            "tx":    t("concl_insomnia_tx", lang),
        })

    # ── Cheyne-Stokes ────────────────────────────────────────
    if csr_info and csr_info.get("csr_detected"):
        body = t("concl_csr_body", lang)
        per = csr_info.get("periodicity_s", "—")
        mins = csr_info.get("csr_minutes", "—")
        body += f" ({per} s, {mins} min)."
        parts.append({
            "type":  "csr",
            "title": t("concl_csr_title", lang),
            "body":  body,
            "tx":    t("concl_csr_tx", lang),
        })

    return parts
