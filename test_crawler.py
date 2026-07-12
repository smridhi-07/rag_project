from app.crawler.crawler import crawl_site

result = crawl_site("https://docs.python.org/3/", max_pages=5)

print(f"Fetched: {len(result.pages)}")
print(f"Skipped by robots.txt: {len(result.skipped_robots)}")
print(f"Failed: {len(result.failed)}")

for page in result.pages:
    print("-", page.url, "|", page.title, "|", len(page.text), "chars")