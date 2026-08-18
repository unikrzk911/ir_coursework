"""
Task 1 — Polite structured crawler for Coventry University's PurePortal,
scoped to the Centre for Healthcare and Community Transformation (CHCT).

What it extracts, per publication (per the assignment brief):
  - title
  - authors (name + link to their PurePortal "person" profile page,
    when the author is CHCT/Coventry-affiliated and so has a profile)
  - publication year
  - link to the publication's own PurePortal page
  - abstract (best-effort, from the publication's detail page — used to
    build better search snippets; optional/toggle-able since it costs
    one extra polite request per publication)

Politeness (assignment requirement):
  - robots.txt is fetched and honoured via robots.PoliteFetcher
  - Pure Portal's robots.txt declares `Crawl-Delay: 5`; PoliteFetcher
    reads that and waits at least that long between requests to the
    same host (never hard-codes a delay that could be lower than what
    the site asked for)
  - a custom, honest User-Agent string identifies the bot
  - only same-host, same-organisation URLs are ever requested — no
    open-ended crawling of the wider internet

Design notes / HTML robustness:
  Pure (the Elsevier CRIS platform Coventry's portal runs on) publishes
  a fairly stable listing markup (`li.list-result-item`, `h3.title a`,
  `a.link.person[rel="Person"]`, `span.date`), but institutional themes
  do get restyled over time. Every extraction step below tries the
  known Pure selectors FIRST and falls back to more generic heuristics
  (regex over hrefs / text) if those don't match, so a markup tweak on
  Coventry's end degrades the crawler gracefully instead of breaking it
  outright.

  IMPORTANT — this sandboxed environment's network egress is restricted
  to a small allow-list (package registries only) and cannot reach
  pureportal.coventry.ac.uk directly, so this module cannot be
  live-tested from here. `tests/test_crawler_offline.py` proves the
  parsing logic end-to-end against saved fixture HTML that mirrors
  Pure's real markup. Run `python crawler.py` on a machine with normal
  internet access to perform the real crawl.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from robots import PoliteFetcher

USER_AGENT = (
    "CoventryCHCT-VerticalSearchBot/1.0 "
    "(+educational Information-Retrieval coursework; Softwarica College)"
)
ORG_SLUG = "centre-for-healthcare-and-community-transformation"
BASE_HOST = "https://pureportal.coventry.ac.uk"
ORG_PUBLICATIONS_URL = f"{BASE_HOST}/en/organisations/{ORG_SLUG}/publications/"


@dataclass
class Publication:
    title: str
    pub_url: str
    year: int | None
    authors: list[tuple[str, str | None]] = field(default_factory=list)
    abstract: str = ""

    def content_hash(self) -> str:
        payload = (
            self.title
            + "|"
            + str(self.year)
            + "|"
            + ",".join(n for n, _ in self.authors)
            + "|"
            + self.abstract
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_year(text: str) -> int | None:
    if not text:
        return None
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group(0)) if m else None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_listing_page(html: str, base_url: str) -> tuple[list[Publication], bool]:
    """Parse one page of the organisation's publications listing.
    Returns (publications_on_this_page, has_next_page)."""
    soup = BeautifulSoup(html, "html.parser")
    publications: list[Publication] = []

    items = soup.select("li.list-result-item") or soup.select(
        "ul.list-results > li"
    )
    if not items:
        # Fallback heuristic: any <h3> whose only/first link points at a
        # publications detail page.
        items = [h3.parent for h3 in soup.select("h3") if h3.find("a", href=re.compile(r"/en/publications/"))]

    for item in items:
        title_tag = item.select_one("h3.title a") or item.find(
            "a", href=re.compile(r"/en/publications/")
        )
        if not title_tag:
            continue
        title = _clean(title_tag.get_text())
        pub_url = urljoin(base_url, title_tag.get("href", ""))
        if not title or not pub_url:
            continue

        authors: list[tuple[str, str | None]] = []
        author_tags = item.select("a.link.person") or item.select('a[href*="/en/persons/"]')
        for a in author_tags:
            name = _clean(a.get_text())
            href = urljoin(base_url, a.get("href", "")) if a.get("href") else None
            if name:
                authors.append((name, href))
        if not authors:
            # Some entries list co-authors as plain (non-linked) text in a
            # "persons"/"relations" block — grab whatever text is there so
            # the publication isn't left with zero attribution.
            persons_block = item.select_one(".persons, .relations")
            if persons_block:
                text = _clean(persons_block.get_text(separator=", "))
                if text:
                    authors = [(name.strip(), None) for name in text.split(",") if name.strip()]

        date_tag = item.select_one("span.date") or item.select_one(".date")
        year = _extract_year(date_tag.get_text() if date_tag else item.get_text())

        publications.append(Publication(title=title, pub_url=pub_url, year=year, authors=authors))

    next_link = soup.select_one('a.nextLink, a[href*="page="][rel="next"]')
    has_next = next_link is not None and next_link.get("href") is not None
    return publications, has_next


def parse_detail_page(html: str) -> str:
    """Best-effort abstract extraction from a publication's own page."""
    soup = BeautifulSoup(html, "html.parser")

    meta = soup.find("meta", attrs={"name": "citation_abstract"})
    if meta and meta.get("content"):
        return _clean(meta["content"])

    abstract_block = soup.select_one(".rendering_researchoutput .textblock, .abstract-content, .rendering_abstractportal")
    if abstract_block:
        return _clean(abstract_block.get_text(separator=" "))

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return _clean(meta_desc["content"])

    return ""


def crawl(
    seed_url: str = ORG_PUBLICATIONS_URL,
    max_pages: int = 20,
    fetch_abstracts: bool = True,
    max_publications: int | None = None,
    fetcher: PoliteFetcher | None = None,
):
    """Crawl the organisation's paginated publications listing, then
    (optionally) each publication's own page for its abstract.

    Returns (publications: list[Publication], stats: dict)
    """
    fetcher = fetcher or PoliteFetcher(user_agent=USER_AGENT, default_delay=3.0)
    start = time.monotonic()

    all_pubs: dict[str, Publication] = {}
    page = 0
    pages_visited = 0

    while page < max_pages:
        page_url = seed_url if page == 0 else f"{seed_url}?page={page}"
        print(f"Fetching listing page {page}: {page_url}")
        html = fetcher.fetch(page_url)
        pages_visited += 1
        if html is None:
            print("  (skipped — disallowed by robots.txt or fetch failed)")
            break

        pubs, has_next = parse_listing_page(html, page_url)
        if not pubs:
            print("  No publications found on this page — stopping pagination.")
            break

        for p in pubs:
            all_pubs[p.pub_url] = p  # dedupe by canonical publication URL

        print(f"  Found {len(pubs)} publications (running total: {len(all_pubs)})")

        if max_publications and len(all_pubs) >= max_publications:
            break
        if not has_next:
            break
        page += 1

    publications = list(all_pubs.values())
    if max_publications:
        publications = publications[:max_publications]

    if fetch_abstracts:
        for i, pub in enumerate(publications, start=1):
            print(f"Fetching abstract {i}/{len(publications)}: {pub.pub_url}")
            html = fetcher.fetch(pub.pub_url)
            if html:
                pub.abstract = parse_detail_page(html)

    stats = {
        "seed_url": seed_url,
        "pages_visited": pages_visited,
        "publications_found": len(publications),
        "skipped_by_robots": fetcher.skipped_by_robots,
        "duration_seconds": time.monotonic() - start,
    }
    return publications, stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Crawl Coventry PurePortal CHCT publications.")
    parser.add_argument("--seed", default=ORG_PUBLICATIONS_URL)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-publications", type=int, default=None)
    parser.add_argument("--no-abstracts", action="store_true")
    args = parser.parse_args()

    pubs, stats = crawl(
        seed_url=args.seed,
        max_pages=args.max_pages,
        fetch_abstracts=not args.no_abstracts,
        max_publications=args.max_publications,
    )
    print(f"\nCrawled {len(pubs)} publications in {stats['duration_seconds']:.1f}s "
          f"({stats['pages_visited']} listing pages, {stats['skipped_by_robots']} skipped by robots.txt)")
    for p in pubs[:5]:
        print(f" - {p.title} ({p.year}) — {len(p.authors)} author(s)")
