from __future__ import annotations

import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlencode

import httpx
from bs4 import BeautifulSoup


BASE = "https://www.gumtree.com.au"


def _client() -> httpx.Client:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.8",
        "Referer": f"{BASE}/",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    return httpx.Client(headers=headers, timeout=10.0, follow_redirects=True)


def build_search_url(keywords: Optional[str], state: Optional[str], page: int) -> str:
    # Use a generic all-items path with keyword param to avoid brittle category ids
    params = {
        "ad": "offering",
        "priceType": "fixed",
        "sort": "rank",
        "page": str(page),
    }
    if keywords:
        params["keyword"] = "-".join(keywords.split())
    if state:
        params["state"] = state.upper()
    return f"{BASE}/s-all-items/k0?{urlencode(params)}"


def search(
    make: Optional[str] = None,
    model: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 10,
    page_limit: int = 2,
    debug: bool = False,
) -> List[Dict[str, Any]]:
    # Polite throttle config (milliseconds)
    try:
        delay_lo_ms = int(os.getenv("SCRAPE_DELAY_MIN_MS", "400"))
        delay_hi_ms = int(os.getenv("SCRAPE_DELAY_MAX_MS", "900"))
    except ValueError:
        delay_lo_ms, delay_hi_ms = 400, 900
    if delay_hi_ms < delay_lo_ms:
        delay_hi_ms = delay_lo_ms

    keywords = " ".join(x for x in [make, model] if x)
    items: List[Dict[str, Any]] = []
    with _client() as client:
        # Optional robots check
        ignore_robots = os.getenv("GUMTREE_IGNORE_ROBOTS", "false").lower() in ("1", "true", "yes")
        try:
            rbt = client.get(urljoin(BASE, "/robots.txt"))
            if rbt.status_code == 200:
                txt = rbt.text
                disallows = [ln.split(":", 1)[1].strip() for ln in txt.splitlines() if ln.lower().startswith("disallow:")]
                blocks = any(seg for seg in disallows if "/s-" in seg or "all-items" in seg)
                if ignore_robots:
                    print(f"robots: ignored (dev); disallows={len(disallows)} blocks_listing_paths={blocks}")
                else:
                    print(f"robots: disallows={len(disallows)} blocks_listing_paths={blocks}")
                    if blocks:
                        raise RuntimeError("robots disallow listing paths")
        except Exception as _e:
            # do not hard fail for robots read errors unless explicitly blocked
            if str(_e).startswith("robots disallow"):
                raise
            pass

        # Warmup cookies
        try:
            warm = client.get(BASE + "/")
            print(f"WARMUP {warm.request.url} -> {warm.status_code} len={len(warm.text)}")
        except Exception:
            pass
        for page in range(1, max(1, page_limit) + 1):
            url = build_search_url(keywords, state, page)
            resp = client.get(url)
            print(f"GET {resp.request.url} -> {resp.status_code} len={len(resp.text)}")
            # Detect challenge/captcha/403 pages politely
            if resp.status_code == 403:
                # Optional Playwright fallback
                if os.getenv("USE_PLAYWRIGHT", "false").lower() in ("1", "true", "yes"):
                    try:
                        from engine.scraper.vendors.gumtree_playwright import fetch_page
                        debug_path = None
                        if debug:
                            snap_dir = Path(__file__).resolve().parents[1] / "storage" / "snapshots"
                            snap_dir.mkdir(parents=True, exist_ok=True)
                            debug_path = str(snap_dir / "gumtree_pw_page1.html")
                        rows = fetch_page(
                            url,
                            limit=limit,
                            timeout=20000,
                            debug_html_path=debug_path,
                            assist=(os.getenv("PW_ASSIST", "false").lower() in ("1", "true", "yes")),
                        )
                        print(f"fallback: playwright rows={len(rows)}")
                        return rows[:limit]
                    except Exception as _e:
                        raise RuntimeError("challenge/403 (HTTPX)") from _e
                raise RuntimeError("challenge/403 (HTTPX)")
            lower = resp.text.lower()
            if (
                "pardon our interruption" in lower
                or "/splashui/challenge" in lower
                or "captcha" in lower
            ):
                if os.getenv("USE_PLAYWRIGHT", "false").lower() in ("1", "true", "yes"):
                    try:
                        from engine.scraper.vendors.gumtree_playwright import fetch_page
                        debug_path = None
                        if debug:
                            snap_dir = Path(__file__).resolve().parents[1] / "storage" / "snapshots"
                            snap_dir.mkdir(parents=True, exist_ok=True)
                            debug_path = str(snap_dir / "gumtree_pw_page1.html")
                        rows = fetch_page(
                            url,
                            limit=limit,
                            timeout=20000,
                            debug_html_path=debug_path,
                            assist=(os.getenv("PW_ASSIST", "false").lower() in ("1", "true", "yes")),
                        )
                        print(f"fallback: playwright rows={len(rows)}")
                        return rows[:limit]
                    except Exception as _e:
                        raise RuntimeError("challenge/403 (HTTPX)") from _e
                raise RuntimeError("challenge/403 (HTTPX)")
            if resp.status_code != 200:
                continue
            if debug and page == 1:
                snap_dir = Path(__file__).resolve().parents[1] / "storage" / "snapshots"
                snap_dir.mkdir(parents=True, exist_ok=True)
                (snap_dir / "gumtree_page1.html").write_text(resp.text, encoding="utf-8")

            soup = BeautifulSoup(resp.text, "html.parser")
            count_before = len(items)

            # Tolerant: any anchor to a listing page containing /s-ad/
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/s-ad/" not in href:
                    continue
                abs_url = urljoin(BASE, href)
                title = (a.get_text(" ", strip=True) or "").strip()
                # Find a container card by walking up a couple of levels
                card = a
                for _ in range(2):
                    if card.parent:
                        card = card.parent

                # Price text within the card vicinity
                price_text = None
                text_block = card.get_text(" ", strip=True)
                mprice = re.search(r"\$\s*([0-9][0-9,]*)", text_block)
                if mprice:
                    price_text = mprice.group(0)

                # Location/state similarly
                location = None
                mstate = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", text_block)
                if mstate:
                    location = mstate.group(1)

                # Image thumb near the anchor
                thumb = None
                img = card.find("img")
                if img:
                    thumb = img.get("src") or (img.get("srcset") or "").split(" ")[0]

                # Ad id from url
                ad_id = None
                mid = re.search(r"/(\d+)(?:\?.*)?$", abs_url)
                if mid:
                    ad_id = mid.group(1)
                if not ad_id and card and card.has_attr("data-ad-id"):
                    ad_id = card.get("data-ad-id")

                items.append(
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
                if len(items) >= limit:
                    print(f"gumtree tiles: {len(items) - count_before}")
                    return items[:limit]

            print(f"gumtree tiles: {len(items) - count_before}")
            # Throttle between pages
            if page < page_limit and len(items) < limit:
                delay = random.uniform(delay_lo_ms / 1000.0, delay_hi_ms / 1000.0)
                time.sleep(delay)
    return items[:limit]


def scrape_gumtree(max_pages: int = 2):
    # Backward-compatible wrapper around HTTPX search
    return search(limit=60, page_limit=max_pages)
