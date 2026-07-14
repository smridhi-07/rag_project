from app.crawler.crawler import _load_robots, HEADERS
from app.crawler.sitemap import discover_urls

base_url = "https://requests.readthedocs.io/en/stable/"

robots = _load_robots(base_url)
print("Robots URL used:", robots.url if hasattr(robots, "url") else "unknown")

urls = discover_urls(base_url, max_urls=15)
print(f"\nDiscovered {len(urls)} URLs via sitemap:")
for u in urls:
    allowed = robots.can_fetch(HEADERS["User-Agent"], u)
    print(f"  {'ALLOWED' if allowed else 'BLOCKED'} - {u}")