#!/usr/bin/env python3
"""
Playwright demo recorder for YASAFlaskified.

Captures a guided walkthrough video per language (nl/fr/en/de):
  landing (/about) -> login -> dashboard -> results -> report editor -> upload

USAGE
  # First-time setup (one-off):
  python -m pip install playwright
  python -m playwright install chromium

  # Local Docker (default upload port 8071):
  python tools/record_demo.py \\
      --base-url http://localhost:8071 \\
      --username demo --password demo123 \\
      --langs en nl fr de

  # Production demo account (no real patient data on screen!):
  python tools/record_demo.py \\
      --base-url https://slaapkliniek.be \\
      --username demo --password "$DEMO_PW" \\
      --langs en

OUTPUT
  videos/nl.webm, videos/fr.webm, videos/en.webm, videos/de.webm
  (1366x768, ~30-45 s each)

  Convert to mp4 for sharing:
      ffmpeg -i videos/en.webm -c:v libx264 -pix_fmt yuv420p videos/en.mp4

PRIVACY
  Do not run this against production with an account that sees real
  patient studies. Create a dedicated demo account first.
"""
import argparse
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page  # noqa: F401


LANG_LABELS = {
    "nl": "Nederlands",
    "fr": "Français",
    "en": "English",
    "de": "Deutsch",
}

CAPTIONS = {
    "intro":    {"nl": "🌍 {name} — YASAFlaskified demo", "fr": "🌍 {name} — démo YASAFlaskified",
                 "en": "🌍 {name} — YASAFlaskified demo", "de": "🌍 {name} — YASAFlaskified-Demo"},
    "login":    {"nl": "Aanmelden", "fr": "Connexion",         "en": "Sign in",            "de": "Anmelden"},
    "upload":   {"nl": "Upload — sleep een EDF-bestand", "fr": "Upload — glissez un fichier EDF",
                 "en": "Upload — drag & drop an EDF file", "de": "Upload — EDF-Datei per Drag-and-Drop"},
    "uploading":{"nl": "Bestand uploaden…", "fr": "Téléversement du fichier…",
                 "en": "Uploading file…",  "de": "Datei wird hochgeladen…"},
    "channels": {"nl": "Kanaalselectie — auto-gedetecteerd uit EDF",
                 "fr": "Sélection des canaux — détection automatique depuis l'EDF",
                 "en": "Channel selection — auto-detected from EDF",
                 "de": "Kanalauswahl — automatisch aus EDF erkannt"},
    "analyzing":{"nl": "Analyse loopt — staging + AHI + spindles + slow waves",
                 "fr": "Analyse en cours — staging + IAH + spindles + ondes lentes",
                 "en": "Analysis running — staging + AHI + spindles + slow waves",
                 "de": "Analyse läuft — Staging + AHI + Spindeln + Slow Waves"},
    "dash":     {"nl": "Dashboard — overzicht analyses", "fr": "Tableau de bord — analyses",
                 "en": "Dashboard — analyses overview", "de": "Dashboard — Übersicht der Analysen"},
    "results":  {"nl": "Resultaten — hypnogram, AHI, signaalkwaliteit",
                 "fr": "Résultats — hypnogramme, IAH, qualité du signal",
                 "en": "Results — hypnogram, AHI, signal quality",
                 "de": "Ergebnisse — Hypnogramm, AHI, Signalqualität"},
    "editor":   {"nl": "Rapport bewerken", "fr": "Édition du rapport",
                 "en": "Report editor", "de": "Bericht bearbeiten"},
}

RESOLUTIONS = {
    "hd":  (1366, 768),
    "fhd": (1920, 1080),
}


def caption(page, lang, key, **fmt):
    """Show a transient on-screen caption for ~3.5s as visual narration."""
    text = CAPTIONS[key][lang].format(**fmt) if fmt else CAPTIONS[key][lang]
    page.evaluate(
        """(msg) => {
            const old = document.getElementById('__demo_banner');
            if (old) old.remove();
            const div = document.createElement('div');
            div.id = '__demo_banner';
            div.textContent = msg;
            div.style.cssText = `
                position:fixed; top:24px; left:50%; transform:translateX(-50%);
                background:rgba(15,28,58,0.94); color:#f0f6ff;
                padding:14px 28px; border-radius:10px;
                font-family:'Lato',system-ui,sans-serif; font-size:20px; font-weight:300;
                z-index:99999; box-shadow:0 6px 30px rgba(0,0,0,0.45);
                border:1px solid rgba(56,189,248,0.4);
                letter-spacing:.01em;
            `;
            document.body.appendChild(div);
            setTimeout(() => { if (div.parentNode) div.remove(); }, 3500);
        }""",
        text,
    )
    page.wait_for_timeout(1200)


def smooth_scroll(page, *ys, dwell_ms=1400):
    for y in ys:
        page.evaluate(f"window.scrollTo({{top:{y}, behavior:'smooth'}})")
        page.wait_for_timeout(dwell_ms)


def record_one_language(p, args, lang):
    print(f"[{lang}] starting…")
    w, h = RESOLUTIONS[args.resolution]
    browser = p.chromium.launch(headless=args.headless)
    ctx = browser.new_context(
        record_video_dir=str(args.output_dir),
        record_video_size={"width": w, "height": h},
        viewport={"width": w, "height": h},
        ignore_https_errors=True,
    )
    page = ctx.new_page()
    page.set_default_timeout(30_000)

    try:
        # 1. Set lang BEFORE any page render so cookies are placed.
        page.goto(f"{args.base_url}/lang/{lang}", wait_until="domcontentloaded")
        page.goto(f"{args.base_url}/about", wait_until="networkidle")
        caption(page, lang, "intro", name=LANG_LABELS[lang])
        page.wait_for_timeout(3500)

        # Cinematic scroll through the landing page
        smooth_scroll(page, 400, 1000, 1700, 2400, 3100, dwell_ms=1500)
        page.evaluate("window.scrollTo({top:0, behavior:'smooth'})")
        page.wait_for_timeout(1200)

        if args.no_login:
            pass  # skip the authenticated walkthrough; finalize video below
        else:
            _do_authenticated_walkthrough(page, args, lang)
    finally:
        ctx.close()
        browser.close()

    # After ctx.close() Playwright finalizes the .webm. Find the newest file
    # in the output dir and rename it to <lang>.webm.
    target = args.output_dir / f"{lang}.webm"
    if target.exists():
        target.unlink()
    try:
        candidates = [p for p in args.output_dir.glob("*.webm")
                      if p.name != target.name]
        if not candidates:
            print(f"[{lang}] no video produced")
            return
        newest = max(candidates, key=os.path.getmtime)
        newest.rename(target)
        print(f"[{lang}] saved -> {target}  ({target.stat().st_size // 1024} KB)")
    except Exception as e:
        print(f"[{lang}] could not finalize video: {e}")


def _do_authenticated_walkthrough(page, args, lang):
    """Login -> upload -> channel-select -> analyze (briefly) -> dashboard ->
    pre-analyzed result -> report editor -> logout."""
    base = args.base_url

    # 2. Login
    page.goto(f"{base}/login", wait_until="networkidle")
    caption(page, lang, "login")
    try:
        page.fill('input[name="username"]', args.username)
        page.wait_for_timeout(400)
        page.fill('input[name="password"]', args.password)
        page.wait_for_timeout(600)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=20_000)
    except PWTimeout:
        print(f"[{lang}] login form timeout — continuing")

    # Re-assert the demo language (login may apply user.language)
    page.goto(f"{base}/lang/{lang}", wait_until="domcontentloaded")

    # 3. Upload phase (if EDF supplied) — drag-drop + parse + channel-select + analyze
    if args.edf_path:
        page.goto(f"{base}/upload", wait_until="networkidle")
        caption(page, lang, "upload")
        page.wait_for_timeout(2000)
        try:
            page.set_input_files('#edfInput', args.edf_path)
            page.wait_for_timeout(1200)  # dropzone updates with file name
            caption(page, lang, "uploading")
            page.locator('#uploadBtn').click()
            page.wait_for_url(f"{base}/channel-select/**", timeout=90_000)
            page.wait_for_load_state("networkidle")
            caption(page, lang, "channels")
            page.wait_for_timeout(2500)
            smooth_scroll(page, 200, 600, 1000, dwell_ms=1300)
            # Fill minimum patient fields, then submit
            try:
                page.fill('input[name="patient_name"]', "Demo")
                page.fill('input[name="patient_firstname"]', "Patient")
                page.fill('input[name="patient_id"]', "DEMO-001")
            except Exception:
                pass
            page.wait_for_timeout(800)
            page.locator('#channelForm button[type="submit"]').first.click()
            page.wait_for_url(f"{base}/status/**", timeout=30_000)
            caption(page, lang, "analyzing")
            page.wait_for_timeout(4500)  # let progress bar appear briefly
        except Exception as e:
            print(f"[{lang}] upload phase issue: {e}")

    # 4. Dashboard
    page.goto(f"{base}/dashboard", wait_until="networkidle")
    caption(page, lang, "dash")
    page.wait_for_timeout(2500)
    smooth_scroll(page, 200, 600, 1000, dwell_ms=1200)

    # 5. Open a COMPLETED study (not the one we just enqueued — that's still running).
    #    Look for any study whose row links to /results/ AND is not the current one.
    results_link = page.locator('a[href*="/results/"]').first
    if results_link.count() > 0:
        try:
            href = results_link.get_attribute("href") or ""
            if href.startswith("/"):
                page.goto(f"{base}{href}", wait_until="networkidle")
                caption(page, lang, "results")
                page.wait_for_timeout(3500)
                smooth_scroll(page, 400, 1000, 1700, 2400, 3100, 3800, dwell_ms=1700)

                # 6. Report editor
                edit = page.locator('a[href*="/edit"], a[href*="report_editor"]').first
                if edit.count() > 0:
                    ehref = edit.get_attribute("href") or ""
                    if ehref.startswith("/"):
                        page.goto(f"{base}{ehref}", wait_until="networkidle")
                        caption(page, lang, "editor")
                        page.wait_for_timeout(3000)
                        smooth_scroll(page, 300, 700, 1100, dwell_ms=1300)
        except Exception as e:
            print(f"[{lang}] results/editor section skipped: {e}")
    else:
        print(f"[{lang}] no completed studies visible — skipping results")

    # 7. Logout (clean exit)
    try:
        page.goto(f"{base}/logout", wait_until="domcontentloaded")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--base-url", required=True,
                    help="e.g. http://localhost:8071 or https://slaapkliniek.be")
    ap.add_argument("--username", default="")
    ap.add_argument("--password", default="")
    ap.add_argument("--no-login", action="store_true",
                    help="record only the public landing page (no login, no dashboard)")
    ap.add_argument("--langs", nargs="+", default=["en", "nl", "fr", "de"],
                    choices=["nl", "fr", "en", "de"],
                    help="languages to record, one video each")
    ap.add_argument("--output-dir", type=Path, default=Path("videos"))
    ap.add_argument("--headless", action="store_true",
                    help="run without a visible browser window (faster, no live preview)")
    ap.add_argument("--resolution", choices=list(RESOLUTIONS), default="fhd",
                    help="hd=1366x768, fhd=1920x1080 (default)")
    ap.add_argument("--edf-path", type=str, default="",
                    help="path to an EDF file; if set, the recording includes "
                         "the real upload + channel-select + start-analysis flow")
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        for lang in args.langs:
            record_one_language(p, args, lang)

    print(f"\nDone. Videos in {args.output_dir.resolve()}/")
    print("Convert to mp4 with:")
    print(f"  for f in {args.output_dir}/*.webm; do "
          f'ffmpeg -y -i "$f" -c:v libx264 -pix_fmt yuv420p "${{f%.webm}}.mp4"; done')


if __name__ == "__main__":
    main()
