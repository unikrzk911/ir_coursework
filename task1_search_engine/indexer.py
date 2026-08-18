"""
Task 1 — Indexing: builds the inverted index using a TF-IDF weighted
vector-space model, exactly the scheme from the original notebook
snippet (tf * idf, L2-normalised per document) but now persisted to
SQLite via db.write_index() instead of a MongoDB collection.

For each crawled publication we index: title + abstract + author names
+ raw page text, so a query can match on any of those fields.
"""
from __future__ import annotations

import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import db as db_mod  # noqa: E402
from shared.textprep import preprocess  # noqa: E402


def _document_text(pub_row, authors):
    parts = [pub_row["title"] or "", pub_row["abstract"] or ""]
    parts += [name for name, _ in [(a["name"], a["profile_url"]) for a in authors]]
    parts.append(pub_row["raw_text"] or "")
    return " ".join(parts)


def build_index(db_path: str = db_mod.DB_PATH):
    with db_mod.get_conn(db_path) as conn:
        pubs = db_mod.all_publications(conn)
        n_docs = len(pubs)
        if n_docs == 0:
            print("No publications in the database yet. Run the crawler first.")
            return {"n_docs": 0, "vocab_size": 0}

        doc_tokens = {}
        df = Counter()
        for pub in pubs:
            authors = db_mod.get_authors_for_publication(conn, pub["id"])
            text = _document_text(pub, authors)
            tokens = preprocess(text)
            doc_tokens[pub["id"]] = tokens
            for term in set(tokens):
                df[term] += 1

        idf = {term: math.log(n_docs / (1 + freq)) + 1 for term, freq in df.items()}
        term_stats = {term: (df[term], idf[term]) for term in df}

        doc_weights = {}
        for pub_id, tokens in doc_tokens.items():
            total_terms = len(tokens) or 1
            tf = Counter(tokens)
            vector = {term: (count / total_terms) * idf.get(term, 0.0) for term, count in tf.items()}
            norm = math.sqrt(sum(w * w for w in vector.values())) or 1.0
            doc_weights[pub_id] = {t: w / norm for t, w in vector.items()}

        db_mod.write_index(conn, term_stats, doc_weights)

        print(f"Indexed {n_docs} publications. Vocabulary size: {len(idf)} terms.")
        return {"n_docs": n_docs, "vocab_size": len(idf)}


if __name__ == "__main__":
    build_index()
