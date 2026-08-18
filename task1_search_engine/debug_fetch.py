"""
Diagnostic helper: fetches the CHCT publications listing page using the
exact same PoliteFetcher the crawler uses (browser headers, then the
Selenium fallback if needed) and saves the raw HTML to debug_page.html
in this folder, so we can see what the page actually looks like.

    python debug_fetch.py
"""
from crawler import ORG_PUBLICATIONS_URL, USER_AGENT
from robots import PoliteFetcher

fetcher = PoliteFetcher(user_agent=USER_AGENT, default_delay=3.0)
try:
    html = fetcher.fetch(ORG_PUBLICATIONS_URL)
finally:
    fetcher.close()

if html is None:
    print("Fetch returned None — the page could not be retrieved at all.")
else:
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {len(html)} characters to debug_page.html")
    print("\n--- first 1000 characters ---")
    print(html[:1000])
