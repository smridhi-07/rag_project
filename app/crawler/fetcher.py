"""
Fetch a single page and extract clean, readable text from it —
stripping nav bars, footers, ads, and scripts.

trafilatura does the heavy lifting here; it's specifically built for
"give me the main article content" extraction and handles messy real
world HTML far better than hand-rolled BeautifulSoup heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
import trafilatura

HEADERS = {"User-Agent": "rag-website-chat-bot/0.1 (educational project)"}
TIMEOUT = 10


@dataclass
class FetchedPage:
    url: str
    title: str | None
    text: str
    success: bool
    error: str | None = None


def fetch_page(url: str) -> FetchedPage:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        return FetchedPage(url=url, title=None, text="", success=False, error=str(e))

    if resp.status_code != 200:
        return FetchedPage(
            url=url, title=None, text="", success=False,
            error=f"HTTP {resp.status_code}",
        )

    html = resp.text

    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )

    if not extracted:
        return FetchedPage(
            url=url, title=None, text="", success=False,
            error="no extractable content",
        )

    metadata = trafilatura.extract_metadata(html)
    title = metadata.title if metadata else None

    return FetchedPage(url=url, title=title, text=extracted, success=True)