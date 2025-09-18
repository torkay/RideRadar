from __future__ import annotations

import os
import re
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from playwright.async_api import async_playwright


BASE = "https://www.gumtree.com.au"


async def fetch_page(url: str, limit: int = 10, timeout: int = 15000, debug: bool = False) -> List[Dict[str, Any]]:
    headless = os.getenv("PW_HEADLESS", "false").lower() == "true"
    rows: List[Dict[str, Any]] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless, slow_mo=50)
        try:
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            content = (await page.content()).lower()
            if debug:
                snap_dir = Path(__file__).resolve().parents[2] / "storage" / "snapshots"
                snap_dir.mkdir(parents=True, exist_ok=True)
                (snap_dir / "gumtree_pw_page1.html").write_text(await page.content(), encoding="utf-8")
            if (
                "captcha" in content
                or "pardon our interruption" in content
                or "/splashui/challenge" in content
            ):
                raise RuntimeError("challenge (PW)")

            anchors = await page.query_selector_all("a[href*='/s-ad/']")
            for a in anchors:
                href = await a.get_attribute("href")
                if not href:
                    continue
                abs_url = urljoin(BASE, href)
                title = (await a.inner_text()).strip()
                # Walk up two levels to get a card's text content
                card = await a.evaluate_handle("(el) => el.parentElement && el.parentElement.parentElement || el")
                card_text: str = (await (await card.as_element()).inner_text()).strip() if card else ""
                mprice = re.search(r"\$\s*([0-9][0-9,]*)", card_text)
                price_text = mprice.group(0) if mprice else None
                mstate = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", card_text)
                location = mstate.group(1) if mstate else None
                # Attempt image within the card
                img_el = await (await card.as_element()).query_selector("img") if card else None
                thumb = await img_el.get_attribute("src") if img_el else None
                if not thumb and img_el:
                    srcset = await img_el.get_attribute("srcset")
                    thumb = (srcset or "").split(" ")[0] if srcset else None
                mid = re.search(r"/(\d+)(?:\?.*)?$", abs_url)
                ad_id = mid.group(1) if mid else None

                rows.append({
                    "url": abs_url,
                    "title": title,
                    "price_str": price_text,
                    "location": location,
                    "thumb": thumb,
                    "ad_id": ad_id,
                    "vendor": "Gumtree",
                })
                if len(rows) >= limit:
                    break
        finally:
            await browser.close()
    return rows[:limit]


# Convenience sync wrapper if ever needed elsewhere
def fetch_page_sync(url: str, limit: int = 10, timeout: int = 15000, debug: bool = False) -> List[Dict[str, Any]]:
    return asyncio.run(fetch_page(url, limit=limit, timeout=timeout, debug=debug))

