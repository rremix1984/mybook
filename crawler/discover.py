"""Site discovery and BFS traversal logic."""
from __future__ import annotations

import asyncio
import random
from collections import deque
from typing import Iterable, List, Tuple
from urllib.parse import urljoin, urlparse, urldefrag
import urllib.robotparser as robotparser

import httpx
from bs4 import BeautifulSoup

from . import storage, fetch


async def _extract_links(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        href, _ = urldefrag(href)
        links.append(href)
    return links


async def crawl(
    start_url: str,
    conn: storage.sqlite3.Connection,
    *,
    max_pages: int = 1000,
    concurrency: int = 5,
    timeout: float = 10.0,
) -> List[Tuple[str, str, httpx.Headers, int]]:
    """Breadth-first crawl starting at *start_url*.

    Returns list of tuples ``(url, html, headers, status_code)`` for new or updated pages.
    """
    parsed_root = urlparse(start_url)
    queue: deque[str] = deque([start_url])
    seen = {start_url}
    results = []

    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(urljoin(start_url, "/robots.txt"))
        rp.read()
    except Exception:
        rp = None

    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        async def worker():
            nonlocal results
            while queue and len(results) < max_pages:
                url = queue.popleft()
                if rp and not rp.can_fetch("*", url):
                    continue
                record = storage.get_page(conn, url)
                etag = record.get("etag") if record else None
                last_mod = record.get("last_modified") if record else None
                async with sem:
                    resp = await fetch.fetch_html(client, url, etag=etag, last_modified=last_mod, timeout=timeout)
                if resp.status_code == 304:
                    storage.touch_page(conn, url)
                    continue
                if resp.status_code >= 400 or "text/html" not in resp.headers.get("Content-Type", ""):
                    storage.upsert_page(
                        conn,
                        url=url,
                        status=resp.status_code,
                        last_modified=resp.headers.get("Last-Modified"),
                        etag=resp.headers.get("ETag"),
                        content_hash=record.get("content_hash", "") if record else "",
                        screenshot_hash=record.get("screenshot_hash") if record else None,
                    )
                    continue
                html = resp.text
                results.append((url, html, resp.headers, resp.status_code))
                links = await _extract_links(url, html)
                for link in links:
                    p = urlparse(link)
                    if p.netloc != parsed_root.netloc:
                        continue
                    if link not in seen:
                        seen.add(link)
                        queue.append(link)
                await asyncio.sleep(random.uniform(0.5, 1.5))

        tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]
        await asyncio.gather(*tasks)

    return results
