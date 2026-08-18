"""
End-to-end offline test of the FULL Task 1 pipeline:

    politeness (robots.txt + crawl-delay) -> crawl -> parse -> store in
    SQLite -> build inverted index -> run search queries -> rank results

against a small local HTTP server serving fixture HTML that mirrors Pure
Portal's real markup (see fixtures/generate_fixtures.py). This is the
proof that the crawler/indexer/search code actually works, without
depending on this sandbox's network access to the real
pureportal.coventry.ac.uk (which its restricted egress can't reach).

Run: python tests/test_crawler_offline.py
"""
from __future__ import annotations

import http.server
import os
import sys
import tempfile
import threading
import time
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
TASK1_DIR = os.path.dirname(HERE)
SITE_DIR = os.path.join(HERE, "fixtures", "site")

sys.path.insert(0, TASK1_DIR)
sys.path.insert(0, os.path.join(TASK1_DIR, ".."))

import crawler  # noqa: E402
import db as db_mod  # noqa: E402
import indexer  # noqa: E402
import search  # noqa: E402
from robots import PoliteFetcher  # noqa: E402


class FixtureHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Serves SITE_DIR, mapping `<path>/?page=N` -> `<path>/page-N.html`
    (a plain static file server can't do query-string routing, but Pure
    Portal's real pagination does exactly this logically)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SITE_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if "page" in qs:
            page_num = qs["page"][0]
            self.path = f"{parsed.path.rstrip('/')}/page-{page_num}.html"
        elif parsed.path.endswith("/"):
            self.path = parsed.path + "index.html"
        elif not parsed.path.endswith(".html") and not parsed.path.endswith(".txt"):
            # Pure Portal detail-page URLs have no file extension, e.g.
            # /en/publications/some-title -> serve some-title.html
            candidate = os.path.join(SITE_DIR, parsed.path.lstrip("/") + ".html")
            if os.path.exists(candidate):
                self.path = parsed.path + ".html"
            else:
                self.path = parsed.path
        else:
            self.path = parsed.path
        return super().do_GET()

    def log_message(self, format, *args):
        pass  # keep test output clean


def start_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixtureHTTPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def run():
    print("=== Offline end-to-end test: crawler -> index -> search ===\n")
    server, port = start_server()
    base = f"http://127.0.0.1:{port}"
    seed = f"{base}/en/organisations/centre-for-healthcare-and-community-transformation/publications/"

    try:
        # --- 1. politeness: robots.txt must be honoured ---------------
        fetcher = PoliteFetcher(user_agent=crawler.USER_AGENT, default_delay=0.2)
        assert fetcher.can_fetch(seed), "robots.txt should allow the publications listing"
        delay = fetcher.crawl_delay(seed)
        assert delay >= 1.0, f"expected the fixture robots.txt Crawl-Delay of 1s to be honoured, got {delay}"
        print(f"[OK] robots.txt parsed; crawl-delay respected ({delay}s)")

        # --- 2. crawl + parse ------------------------------------------
        t0 = time.time()
        publications, stats = crawler.crawl(
            seed_url=seed, max_pages=10, fetch_abstracts=True, fetcher=fetcher
        )
        elapsed = time.time() - t0
        assert len(publications) == 6, f"expected 6 publications, got {len(publications)}"
        assert stats["pages_visited"] == 2, f"expected 2 listing pages, got {stats['pages_visited']}"
        print(f"[OK] crawled {len(publications)} publications across {stats['pages_visited']} "
              f"listing pages in {elapsed:.1f}s (politeness delay included)")

        one = publications[0]
        assert one.title and one.pub_url and one.year, "core fields must be populated"
        assert any(href for _, href in one.authors), "at least one author should have a profile link"
        assert one.abstract, "abstract should have been fetched from the detail page"
        print(f"[OK] structured fields present, e.g.: '{one.title}' ({one.year}) "
              f"by {', '.join(n for n, _ in one.authors)}")
        print(f"     abstract: {one.abstract[:80]}...")

        # --- 3. persist + build inverted index --------------------------
        tmp_db = os.path.join(tempfile.mkdtemp(), "test_search_engine.db")
        db_mod.init_db(tmp_db)
        with db_mod.get_conn(tmp_db) as conn:
            new_count = updated_count = 0
            for pub in publications:
                _, is_new, is_updated = db_mod.upsert_publication(
                    conn, pub.pub_url, pub.title, pub.year, pub.abstract,
                    pub.abstract, pub.content_hash(), pub.authors,
                )
                new_count += is_new
                updated_count += is_updated
            db_mod.log_crawl(conn, seed, stats["pages_visited"], len(publications),
                              new_count, updated_count, stats["skipped_by_robots"],
                              stats["duration_seconds"])
        print(f"[OK] persisted {len(publications)} publications to SQLite ({new_count} new)")

        index_stats = indexer.build_index(tmp_db)
        assert index_stats["n_docs"] == 6
        assert index_stats["vocab_size"] > 10
        print(f"[OK] built inverted index: {index_stats['vocab_size']} terms over {index_stats['n_docs']} docs")

        # --- 4. re-run the crawl to prove incremental update works -----
        publications2, _ = crawler.crawl(seed_url=seed, max_pages=10, fetch_abstracts=False, fetcher=fetcher)
        with db_mod.get_conn(tmp_db) as conn:
            new2 = updated2 = 0
            for pub in publications2:
                _, is_new, is_updated = db_mod.upsert_publication(
                    conn, pub.pub_url, pub.title, pub.year, pub.abstract or "",
                    pub.abstract or "", pub.content_hash(), pub.authors,
                )
                new2 += is_new
                updated2 += is_updated
        assert new2 == 0, "re-crawling the same unchanged site should add 0 new publications"
        print(f"[OK] weekly re-crawl simulation: 0 new / re-upserted {len(publications2)} unchanged publications")

        # --- 5. search + ranking ----------------------------------------
        test_queries = {
            "nutrition obesity older adults": "community-nutrition-intervention-outcomes",
            "exercise diabetes prevention": "physical-activity-diabetes-prevention",
            "mental health co-production": "mental-health-community-transformation",
            "digital health monitoring": "digital-health-community-monitoring",
        }
        for query, expected_slug in test_queries.items():
            results = search.search(query, top_k=3, db_path=tmp_db)
            assert results, f"query '{query}' returned no results"
            top = results[0]
            assert expected_slug in top["pub_url"], (
                f"query '{query}' expected top hit '{expected_slug}', got '{top['pub_url']}' "
                f"(score={top['score']:.4f})"
            )
            print(f"[OK] query '{query}' -> top result: '{top['title']}' (score={top['score']:.4f})")

        no_match = search.search("xyzzy quantum unrelated plughhh", top_k=3, db_path=tmp_db)
        assert no_match == [], "a query with no matching terms should return no results"
        print("[OK] query with no matching terms correctly returns zero results")

        print("\n=== ALL OFFLINE PIPELINE CHECKS PASSED ===")
    finally:
        server.shutdown()


if __name__ == "__main__":
    run()
