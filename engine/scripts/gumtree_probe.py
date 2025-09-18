# engine/scripts/gumtree_probe.py
import argparse, asyncio, json, os, re, time
from pathlib import Path

from playwright.sync_api import sync_playwright

SNAP = Path("engine/storage/snapshots")
SNAP.mkdir(parents=True, exist_ok=True)

TARGET_PAT = re.compile(r"(api|search|ads|listing|results)", re.I)

def run(url: str, storage: str | None, save_storage: str | None, headless: bool):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=[
            "--disable-blink-features=AutomationControlled",
            "--lang=en-AU",
        ])
        context = browser.new_context(
            locale="en-AU",
            timezone_id="Australia/Sydney",
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/118.0.0.0 Safari/537.36"),
            viewport={"width": 1368, "height": 900},
            storage_state=storage if storage else None,
        )

        page = context.new_page()

        def on_response(resp):
            try:
                ct = (resp.headers() or {}).get("content-type", "")
                url = resp.url
                if "application/json" in ct and TARGET_PAT.search(url):
                    body = resp.text()  # small payloads; OK for probe
                    ts = int(time.time())
                    fname = SNAP / f"gumtree_json_{ts}.json"
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(body)
                    print(f"[JSON] {resp.status} {url}\n -> saved {fname}")
            except Exception:
                pass

        context.on("response", on_response)

        print("Navigate to:", url)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Give you time to interact: accept cookies, run a search, paginate, etc.
        print(">>> You now have ~90s to interact. Accept cookies, run a search, paginate.")
        page.wait_for_timeout(90000)

        if save_storage:
            context.storage_state(path=save_storage)
            print(f"Saved storage state to {save_storage}")

        browser.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gumtree probe for JSON endpoints")
    ap.add_argument("--url", required=True, help="A real search or category URL")
    ap.add_argument("--storage", help="path to storage_state.json to reuse login/session")
    ap.add_argument("--save-storage", help="path to save updated storage_state.json")
    ap.add_argument("--headless", action="store_true", help="Run headless (default: headful)")
    args = ap.parse_args()
    run(args.url, args.storage, args.save_storage, args.headless)