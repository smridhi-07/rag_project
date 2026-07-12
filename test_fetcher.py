from app.crawler.fetcher import fetch_page

result = fetch_page("https://docs.python.org/3/")
print("Success:", result.success)
print("Title:", result.title)
print("Text length:", len(result.text))
print("First 300 chars:\n", result.text[:300])