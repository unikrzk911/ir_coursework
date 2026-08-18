"""
Task 1 — persistence layer.

The original notebook snippet used MongoDB. This project uses SQLite
instead: it needs no external server, ships in the Python standard
library, and the whole index is a single portable file
(`search_engine.db`) that a marker can open and run with zero setup.
The data model (raw pages -> pre-processed terms -> an inverted index
of TF-IDF weights -> cosine-similarity ranking at query time) is the
same vector-space design as the snippet; only the storage engine
changed.

Schema
------
publications         one row per crawled Pure Portal publication
authors               one row per distinct author (their PurePortal
                       "person" profile), deduplicated by profile_url
publication_authors   many-to-many link, preserves author order
inverted_index         (term, publication_id) -> normalised TF-IDF weight
term_stats             (term) -> document frequency, idf
crawl_log              one row per crawl run, for the "runs weekly and
                       updates the index" requirement
"""
from __future__ import annotations

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_engine.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS publications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT UNIQUE NOT NULL,
    title           TEXT,
    year            INTEGER,
    abstract        TEXT,
    raw_text        TEXT,
    content_hash    TEXT,
    first_crawled_at TEXT,
    last_crawled_at  TEXT
);

CREATE TABLE IF NOT EXISTS authors (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    profile_url  TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS publication_authors (
    publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
    author_id       INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_order    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (publication_id, author_id)
);

CREATE TABLE IF NOT EXISTS inverted_index (
    term            TEXT NOT NULL,
    publication_id  INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
    weight          REAL NOT NULL,
    PRIMARY KEY (term, publication_id)
);
CREATE INDEX IF NOT EXISTS idx_inverted_index_term ON inverted_index(term);

CREATE TABLE IF NOT EXISTS term_stats (
    term       TEXT PRIMARY KEY,
    doc_freq   INTEGER NOT NULL,
    idf        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at              TEXT NOT NULL,
    seed_url            TEXT,
    pages_visited       INTEGER,
    publications_found  INTEGER,
    publications_new    INTEGER,
    publications_updated INTEGER,
    skipped_by_robots   INTEGER,
    duration_seconds    REAL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH):
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)


def upsert_publication(conn, url, title, year, abstract, raw_text, content_hash, authors):
    """authors: list of (name, profile_url) in display order.
    Returns (publication_id, is_new, is_updated)."""
    cur = conn.execute("SELECT id, content_hash FROM publications WHERE url = ?", (url,))
    row = cur.fetchone()
    ts = now_iso()
    is_new = row is None
    is_updated = False

    if is_new:
        cur = conn.execute(
            """INSERT INTO publications
               (url, title, year, abstract, raw_text, content_hash, first_crawled_at, last_crawled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (url, title, year, abstract, raw_text, content_hash, ts, ts),
        )
        pub_id = cur.lastrowid
    else:
        pub_id = row["id"]
        if row["content_hash"] != content_hash:
            is_updated = True
        conn.execute(
            """UPDATE publications
               SET title=?, year=?, abstract=?, raw_text=?, content_hash=?, last_crawled_at=?
               WHERE id=?""",
            (title, year, abstract, raw_text, content_hash, ts, pub_id),
        )
        conn.execute("DELETE FROM publication_authors WHERE publication_id = ?", (pub_id,))

    for order, (name, profile_url) in enumerate(authors):
        if profile_url:
            cur = conn.execute("SELECT id FROM authors WHERE profile_url = ?", (profile_url,))
        else:
            cur = conn.execute(
                "SELECT id FROM authors WHERE name = ? AND profile_url IS NULL", (name,)
            )
        arow = cur.fetchone()
        if arow:
            author_id = arow["id"]
        else:
            cur = conn.execute(
                "INSERT INTO authors (name, profile_url) VALUES (?, ?)", (name, profile_url)
            )
            author_id = cur.lastrowid
        conn.execute(
            """INSERT OR IGNORE INTO publication_authors (publication_id, author_id, author_order)
               VALUES (?, ?, ?)""",
            (pub_id, author_id, order),
        )

    return pub_id, is_new, is_updated


def all_publications(conn):
    return conn.execute("SELECT * FROM publications").fetchall()


def get_authors_for_publication(conn, pub_id):
    return conn.execute(
        """SELECT a.name, a.profile_url FROM authors a
           JOIN publication_authors pa ON pa.author_id = a.id
           WHERE pa.publication_id = ?
           ORDER BY pa.author_order""",
        (pub_id,),
    ).fetchall()


def clear_index(conn):
    conn.execute("DELETE FROM inverted_index")
    conn.execute("DELETE FROM term_stats")


def write_index(conn, term_stats: dict, doc_weights: dict):
    """term_stats: {term: (doc_freq, idf)}
       doc_weights: {publication_id: {term: normalised_weight}}"""
    clear_index(conn)
    conn.executemany(
        "INSERT INTO term_stats (term, doc_freq, idf) VALUES (?, ?, ?)",
        [(t, df, idf) for t, (df, idf) in term_stats.items()],
    )
    rows = [
        (term, pub_id, weight)
        for pub_id, weights in doc_weights.items()
        for term, weight in weights.items()
    ]
    conn.executemany(
        "INSERT INTO inverted_index (term, publication_id, weight) VALUES (?, ?, ?)", rows
    )


def get_postings(conn, terms):
    """Return {term: {publication_id: weight}} for the given terms only
    (this IS the inverted-index lookup: we never scan documents that
    don't contain at least one query term)."""
    if not terms:
        return {}
    placeholders = ",".join("?" for _ in terms)
    rows = conn.execute(
        f"SELECT term, publication_id, weight FROM inverted_index WHERE term IN ({placeholders})",
        list(terms),
    ).fetchall()
    postings = {}
    for r in rows:
        postings.setdefault(r["term"], {})[r["publication_id"]] = r["weight"]
    return postings


def get_idf_map(conn, terms):
    if not terms:
        return {}
    placeholders = ",".join("?" for _ in terms)
    rows = conn.execute(
        f"SELECT term, idf FROM term_stats WHERE term IN ({placeholders})", list(terms)
    ).fetchall()
    return {r["term"]: r["idf"] for r in rows}


def log_crawl(conn, seed_url, pages_visited, found, new, updated, skipped, duration):
    conn.execute(
        """INSERT INTO crawl_log
           (run_at, seed_url, pages_visited, publications_found, publications_new,
            publications_updated, skipped_by_robots, duration_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (now_iso(), seed_url, pages_visited, found, new, updated, skipped, duration),
    )
