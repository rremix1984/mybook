"""HTML parsing and content extraction utilities."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
from readability import Document

TIME_RE = re.compile(r"(20\d{2}-\d{1,2}-\d{1,2})")


def _extract_time(soup: BeautifulSoup) -> Optional[str]:
    # time tag
    t = soup.find("time")
    if t:
        if t.get("datetime"):
            return t["datetime"].split("T")[0]
        text = t.get_text(strip=True)
        m = TIME_RE.search(text)
        if m:
            return m.group(1)
    # meta property
    meta = soup.find("meta", attrs={"property": re.compile("date", re.I)})
    if meta and meta.get("content"):
        return meta["content"].split("T")[0]
    # ld+json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                for key in ("datePublished", "dateModified"):
                    if key in data:
                        return data[key].split("T")[0]
        except Exception:
            continue
    # generic regex
    m = TIME_RE.search(soup.get_text(" ", strip=True))
    if m:
        return m.group(1)
    return None


def extract(url: str, html: str) -> Dict[str, any]:
    """Extract structured information from HTML."""
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    h1 = soup.find("h1")
    h2 = soup.find("h2")
    h3 = soup.find("h3")
    meta_desc_tag = soup.find("meta", attrs={"name": re.compile("description", re.I)})
    meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else ""
    pub_time = _extract_time(soup)

    # readability to get main content
    doc = Document(html)
    content_html = doc.summary(html_partial=True)
    content_text = BeautifulSoup(content_html, "lxml").get_text("\n", strip=True)
    content_text = re.sub(r"\s+", " ", content_text)

    # key fields: take lines split by period or newline
    sentences = re.split(r"[\n\.]", content_text)
    key_fields: List[str] = []
    for s in sentences:
        s = s.strip()
        if 10 < len(s) <= 80:
            key_fields.append(s[:40])
        if len(key_fields) >= 8:
            break
    # ensure at least 3 entries
    key_fields = key_fields[:8]

    # summary
    summary = content_text[:600]

    return {
        "url": url,
        "title": title,
        "h1": h1.get_text(strip=True) if h1 else "",
        "h2": h2.get_text(strip=True) if h2 else "",
        "h3": h3.get_text(strip=True) if h3 else "",
        "meta_desc": meta_desc,
        "pub_time": pub_time,
        "key_fields": key_fields[:8],
        "summary": summary,
        "content_text": content_text,
    }
