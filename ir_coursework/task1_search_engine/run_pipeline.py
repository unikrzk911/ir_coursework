"""
One-command pipeline: crawl the CHCT PurePortal publications, store/
update them in SQLite, then rebuild the inverted index. This is what
both a one-off manual run and the weekly scheduler (scheduler.py) call.

    python run_pipeline.py                     # normal run
    python run_pipeline.py --max-publications 40 --no-abstracts   # quick/cheap run
"""
from __future__ import annotations

import argparse

import crawler
import db as db_mod
import indexer


def run_once(
    seed_url: str = crawler.ORG_PUBLICATIONS_URL,
    max_pages: int = 20,
    max_publications: int | None = None,
    fetch_abstracts: bool = True,
    db_path: str = db_mod.DB_PATH,
):
    db_mod.init_db(db_path)

    publications, stats = crawler.crawl(
        seed_url=seed_url,
        max_pages=max_pages,
        max_publications=max_publications,
        fetch_abstracts=fetch_abstracts,
    )

    new_count = updated_count = 0
    with db_mod.get_conn(db_path) as conn:
        for pub in publications:
            _, is_new, is_updated = db_mod.upsert_publication(
                conn,
                pub.pub_url,
                pub.title,
                pub.year,
                pub.abstract,
                pub.abstract,
                pub.content_hash(),
                pub.authors,
            )
            new_count += int(is_new)
            updated_count += int(is_updated)
        db_mod.log_crawl(
            conn,
            seed_url,
            stats["pages_visited"],
            len(publications),
            new_count,
            updated_count,
            stats["skipped_by_robots"],
            stats["duration_seconds"],
        )

    print(f"\nCrawl summary: {len(publications)} publications seen "
          f"({new_count} new, {updated_count} changed since last crawl)")

    index_stats = indexer.build_index(db_path)
    return stats, index_stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl + index the CHCT PurePortal vertical search engine.")
    parser.add_argument("--seed", default=crawler.ORG_PUBLICATIONS_URL)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-publications", type=int, default=None)
    parser.add_argument("--no-abstracts", action="store_true")
    parser.add_argument("--db", default=db_mod.DB_PATH)
    args = parser.parse_args()

    run_once(
        seed_url=args.seed,
        max_pages=args.max_pages,
        max_publications=args.max_publications,
        fetch_abstracts=not args.no_abstracts,
        db_path=args.db,
    )
