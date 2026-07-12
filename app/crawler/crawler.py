"""
Orchestrates a site crawl:
  1. Check robots.txt — build a parser we consult before every fetch.
  2. Try sitemap discovery (fast path).
  3. If no sitemap, fall back to crawling links from the homepage
     up to a depth/page limit.
  4. Fetch + extract clean text for every allowed URL.
  5. Politely rate-limit requests (small delay between fetches).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from app.crawler.fetcher import FetchedPage, fetch_page
from app.crawler.sitemap import discover_urls

HEADERS = {"User-Agent": "rag-website-chat-bot/0.1 (educational project)"}
TIMEOUT = 10
DEFAULT_DELAY_SECONDS = 0.5


@dataclass
class CrawlResult:
    pages: list[FetchedPage] = field(default_factory=list)
    skipped_robots: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def _load_robots(base_url: str) -> RobotFileParser:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        pass
    return rp


def _same_domain(url: str, base_netloc: str) -> bool:
    return urlparse(url).netloc == base_netloc


def _extract_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        full = urljoin(page_url, href)
        full = full.split("#")[0]
        links.append(full)
    return links


def _crawl_via_links(base_url: str, max_pages: int, robots: RobotFileParser) -> list[str]:
    base_netloc = urlparse(base_url).netloc
    visited: set[str] = set()
    queue: list[str] = [base_url]
    discovered: list[str] = []

    while queue and len(discovered) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        if not _same_domain(url, base_netloc):
            continue
        if not robots.can_fetch(HEADERS["User-Agent"], url):
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            time.sleep(DEFAULT_DELAY_SECONDS)
        except requests.RequestException:
            continue

        if resp.status_code != 200:
            continue

        discovered.append(url)

        for link in _extract_links(resp.text, url):
            if link not in visited and link not in queue:
                queue.append(link)

    return discovered[:max_pages]


def crawl_site(base_url: str, max_pages: int = 100) -> CrawlResult:
    result = CrawlResult()
    robots = _load_robots(base_url)

    urls = discover_urls(base_url, max_urls=max_pages)
    if not urls:
        urls = _crawl_via_links(base_url, max_pages, robots)

    for url in urls:
        if not robots.can_fetch(HEADERS["User-Agent"], url):
            result.skipped_robots.append(url)
            continue

        page = fetch_page(url)
        time.sleep(DEFAULT_DELAY_SECONDS)

        if page.success:
            result.pages.append(page)
        else:
            result.failed.append(url)

    return result