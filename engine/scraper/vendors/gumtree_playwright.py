from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


BASE = "https://www.gumtree.com.au"


def fetch_page(
    url: str,
    limit: int = 10,
    timeout: int = 20000,
    debug_html_path: str | None = None,
    assist: bool = False,
) -> List[Dict[str, Any]]:
    profile_dir = Path(os.getenv("PW_PROFILE_DIR", "~/.rideradar/pw-gumtree")).expanduser()
    headless = os.getenv("PW_HEADLESS", "false").lower() == "true"
    rows: List[Dict[str, Any]] = []
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            viewport={"width": 1280, "height": 800},
            locale="en-AU",
            timezone_id="Australia/Brisbane",
            args=["--disable-blink-features=AutomationControlled"],
            slow_mo=50,
        )
        try:
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            if assist:
                print(
                    "Manual assist: ensure listings are visible (dismiss banners/challenges), then press ENTER here…",
                    flush=True,
                )
                try:
                    input()
                except EOFError:
                    pass
            content = page.content()
            if debug_html_path:
                Path(debug_html_path).parent.mkdir(parents=True, exist_ok=True)
                Path(debug_html_path).write_text(content, encoding="utf-8")
            lower = content.lower()
            if (
                "captcha" in lower
                or "pardon our interruption" in lower
                or "/splashui/challenge" in lower
            ):
                raise RuntimeError("challenge (PW)")

            anchors = page.locator("a[href*='/s-ad/']").all()
            for a in anchors:
                href = a.get_attribute("href")
                if not href:
                    continue
                abs_url = urljoin(BASE, href)
                title = (a.inner_text() or "").strip()
                # Walk up two levels to get a card's text content
                card = a.element_handle()
                for _ in range(2):
                    if card and card.evaluate("el => el.parentElement"):
                        card = card.evaluate_handle("el => el.parentElement").as_element()
                card_text = (card.inner_text().strip() if card else "")
                mprice = re.search(r"\$\s*([0-9][0-9,]*)", card_text)
                price_text = mprice.group(0) if mprice else None
                mstate = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", card_text)
                location = mstate.group(1) if mstate else None
                img_el = card.query_selector("img") if card else None
                thumb = img_el.get_attribute("src") if img_el else None
                if not thumb and img_el:
                    srcset = img_el.get_attribute("srcset") or ""
                    thumb = srcset.split(" ")[0] if srcset else None
                mid = re.search(r"/(\d+)(?:\?.*)?$", abs_url)
                ad_id = mid.group(1) if mid else None

                rows.append(
                    {
                        "url": abs_url,
                        "title": title,
                        "price_str": price_text,
                        "location": location,
                        "thumb": thumb,
                        "ad_id": ad_id,
                        "vendor": "Gumtree",
                    }
                )
                if len(rows) >= limit:
                    break
        finally:
            ctx.close()
    return rows[:limit]
