"""
Sitemap discovery.

Most real sites expose a sitemap.xml (or a sitemap index pointing to
several sitemaps). If we can find one, it's a much faster and more
reliable way to get a list of URLs than crawling links by hand.
"""

from __future__ import annotations

import requests
from urllib.parse import urljoin
from xml.etree import ElementTree

HEADERS = {"User-Agent": "rag-website-chat-bot/0.1 (educational project)"}
TIMEOUT = 10


def _get(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def _parse_sitemap_xml(xml_text: str) -> tuple[list[str], list[str]]:
    """
    Returns (page_urls, sub_sitemap_urls).
    A sitemap index file contains <sitemap><loc> entries pointing to
    other sitemaps. A regular sitemap contains <url><loc> entries
    pointing to actual pages. We handle both.
    """
    page_urls: list[str] = []
    sub_sitemaps: list[str] = []

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return page_urls, sub_sitemaps

    for elem in root:
        tag = elem.tag.rsplit("}", 1)[-1]  # strip namespace
        if tag == "sitemap":
            loc = elem.find("{*}loc")
            if loc is not None and loc.text:
                sub_sitemaps.append(loc.text.strip())
        elif tag == "url":
            loc = elem.find("{*}loc")
            if loc is not None and loc.text:
                page_urls.append(loc.text.strip())

    return page_urls, sub_sitemaps


def discover_urls(base_url: str, max_urls: int = 500) -> list[str]:
    """
    Try to find all page URLs for a site via its sitemap(s).
    Returns an empty list if no sitemap is found (caller should fall
    back to link-crawling in that case).
    """
    candidates = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
    ]

    all_urls: list[str] = []
    seen_sitemaps: set[str] = set()
    queue: list[str] = []

    for c in candidates:
        text = _get(c)
        if text:
            queue.append(c)
            seen_sitemaps.add(c)
            pages, subs = _parse_sitemap_xml(text)
            all_urls.extend(pages)
            queue.extend(s for s in subs if s not in seen_sitemaps)
            break

    i = 1
    while i < len(queue) and len(all_urls) < max_urls:
        sm_url = queue[i]
        i += 1
        if sm_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sm_url)
        text = _get(sm_url)
        if not text:
            continue
        pages, subs = _parse_sitemap_xml(text)
        all_urls.extend(pages)
        queue.extend(s for s in subs if s not in seen_sitemaps)

    deduped = list(dict.fromkeys(all_urls))
    return deduped[:max_urls]