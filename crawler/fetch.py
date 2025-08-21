"""HTTP fetching helpers using httpx and tenacity for retries."""
from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

DEFAULT_HEADERS = {"User-Agent": "MyBookCrawler/1.0"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_html(
    client: httpx.AsyncClient,
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    timeout: float = 10.0,
) -> httpx.Response:
    """Fetch *url* returning ``httpx.Response``.

    Conditional headers are added when ``etag`` or ``last_modified`` are provided.
    """
    headers = DEFAULT_HEADERS.copy()
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    resp = await client.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    return resp
