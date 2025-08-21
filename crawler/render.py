"""Page rendering and screenshot utilities using Playwright."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright

# CSS to hide small images and common decorative elements
HIDE_CSS = """
header, footer, aside, nav, .nav, .site-nav, .sidebar {display:none !important;}
*[class*="icon" i], *[id*="icon" i],
*[class*="logo" i], *[id*="logo" i],
*[class*="avatar" i], *[id*="avatar" i],
*[class*="badge" i], *[class*="sprite" i] {display:none !important;}
"""

JS_HIDE_SMALL = """
for (const el of Array.from(document.images).concat(Array.from(document.querySelectorAll('svg, picture')))) {
  const rect = el.getBoundingClientRect();
  if (Math.min(rect.width, rect.height) < 64) {
    el.style.display = 'none';
  }
}
"""

CONTENT_SELECTORS = ["main", "article", "[role=main]", ".post", ".article", ".content"]


async def screenshot(url: str, path: Path, *, headless: bool = True, timeout: int = 10000) -> Optional[Path]:
    """Capture screenshot of *url* into ``path``.

    Returns the path on success, or ``None`` if rendering fails.
    """
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={"width": 1200, "height": 800})
            page = await context.new_page()
            await page.goto(url, timeout=timeout)
            await page.add_style_tag(content=HIDE_CSS)
            await page.evaluate(JS_HIDE_SMALL)

            box = None
            for sel in CONTENT_SELECTORS:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    box = await loc.first.bounding_box()
                    if box:
                        break
            if box is None:
                box = await page.locator("body").bounding_box()
            if box is None:
                await browser.close()
                return None
            # add padding
            box["x"] = max(0, box["x"] - 24)
            box["y"] = max(0, box["y"] - 24)
            box["width"] = box["width"] + 48
            box["height"] = box["height"] + 48
            await page.screenshot(path=str(path), clip=box)
            await browser.close()
            return path
    except Exception:
        return None
