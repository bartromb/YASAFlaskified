#!/usr/bin/env python3
"""
One-shot setup: login as demo user, upload demo.edf via the real UI,
auto-detect channels, submit channel-select, kick off analysis.

After this completes, the demo account has one study in progress.
Poll /api/status/<job_id> (or just wait ~5-7 min) before recording.
"""
import argparse
import sys
import time

from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--username", default="demo")
    ap.add_argument("--password", required=True)
    ap.add_argument("--edf-path", required=True)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--wait-for-completion", action="store_true",
                    help="Poll job status until analysis is done (up to 15 min)")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            ignore_https_errors=True,
        )
        page = ctx.new_page()
        page.set_default_timeout(30_000)

        # Set language to English
        page.goto(f"{args.base_url}/lang/en", wait_until="domcontentloaded")

        # Login
        print("login…")
        page.goto(f"{args.base_url}/login", wait_until="networkidle")
        page.fill('input[name="username"]', args.username)
        page.fill('input[name="password"]', args.password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Force English again (login may have applied user.language)
        page.goto(f"{args.base_url}/lang/en", wait_until="domcontentloaded")

        # Go to upload page (role=site redirects from / to /dashboard)
        page.goto(f"{args.base_url}/upload", wait_until="networkidle")
        print(f"selecting file: {args.edf_path}")
        page.set_input_files('#edfInput', args.edf_path)
        page.wait_for_timeout(1500)

        # Click Upload + parse
        print("clicking upload button…")
        page.locator('#uploadBtn').click()

        # Wait for redirect to /channel-select/<job_id>
        print("waiting for channel-select page…")
        page.wait_for_url(f"{args.base_url}/channel-select/**", timeout=120_000)
        job_id = page.url.split("/")[-1]
        print(f"job_id = {job_id}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)

        # Fill mandatory patient_name and submit (everything else auto)
        try:
            page.fill('input[name="patient_name"]', "Demo")
            page.fill('input[name="patient_firstname"]', "Patient")
            page.fill('input[name="patient_id"]', "DEMO-001")
        except Exception as e:
            print(f"could not fill patient fields ({e}); continuing anyway")

        # Submit the channel-select form -> POST /analyze
        print("submitting channel-select…")
        page.locator('#channelForm button[type="submit"]').first.click()
        page.wait_for_url(f"{args.base_url}/status/**", timeout=30_000)
        print(f"analysis started, status page: {page.url}")

        if args.wait_for_completion:
            print("polling for completion…")
            start = time.time()
            while time.time() - start < 900:  # 15 min cap
                try:
                    resp = page.request.get(f"{args.base_url}/api/status/{job_id}")
                    data = resp.json()
                    progress = data.get("progress", {})
                    print(f"  [{int(time.time()-start)}s] status={data.get('status')} "
                          f"step={progress.get('step','?')}/{progress.get('total','?')} "
                          f"{progress.get('label','')}")
                    if data.get("done"):
                        print(f"✓ analysis done in {int(time.time()-start)}s")
                        break
                    if data.get("failed"):
                        print(f"✗ analysis failed: {data.get('error','?')}")
                        sys.exit(1)
                except Exception as e:
                    print(f"  poll error: {e}")
                time.sleep(10)
            else:
                print("✗ timeout after 15 min")
                sys.exit(1)

        ctx.close()
        browser.close()

    print(f"DONE. job_id={job_id}")


if __name__ == "__main__":
    main()
