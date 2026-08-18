"""
Standalone Cloudflare-bypass diagnostic — nothing from the rest of the
project involved, just undetected-chromedriver on its own, so we can see
exactly what's happening with nothing else in the way.

    python debug_cloudflare.py

Watch the Chrome window that opens, and watch this terminal's output.
The browser stays open at the end so you can look around manually
(view-source, F12 devtools, etc.) before pressing Enter to close it.
"""
import sys
import time
import traceback

print(f"Python: {sys.version}")

try:
    from _distutils_shim import ensure_distutils_shim
    ensure_distutils_shim()
    import undetected_chromedriver as uc
except Exception:
    print("\nFailed to import undetected_chromedriver. Full error below:\n")
    traceback.print_exc()
    print("\n(pip shows it installed, so this is almost certainly a real import-time "
          "error, not a 'not installed' situation — the traceback above is the actual cause.)")
    raise SystemExit(1)

URL = (
    "https://pureportal.coventry.ac.uk/en/organisations/"
    "centre-for-healthcare-and-community-transformation/publications/"
)

print(f"undetected_chromedriver version: {uc.__version__ if hasattr(uc, '__version__') else 'unknown'}")

from robots import _detect_chrome_major_version  # noqa: E402

version_main = _detect_chrome_major_version(uc)
print(f"Detected installed Chrome major version: {version_main}")

print("Starting Chrome (a visible window should appear)...")
options = uc.ChromeOptions()
driver = uc.Chrome(options=options, version_main=version_main)

print(f"Navigating to: {URL}")
driver.get(URL)

for i in range(60):
    title = driver.title
    print(f"[{i:02d}s] page title: {title!r}")
    if "just a moment" not in title.lower() and "attention" not in title.lower():
        print(">>> Title no longer looks like a challenge page.")
        break
    time.sleep(1)
else:
    print(">>> Still looked like a challenge page after 60 seconds.")

with open("debug_page2.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print(f"\nSaved current page source ({len(driver.page_source)} chars) to debug_page2.html")
print("Look at the actual Chrome window now: what do you see?")
print("(a spinner / checkmark that never finishes? a checkbox to click? something else?)")

input("\nPress Enter here once you've looked, to close the browser...")
driver.quit()
