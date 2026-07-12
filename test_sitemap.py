from app.crawler.sitemap import discover_urls

urls = discover_urls("https://docs.python.org/3/")
print(f"Found {len(urls)} URLs")
for u in urls[:10]:
    print(u)