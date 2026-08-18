# ST7071CEM Information Retrieval Coursework

Two independent deliverables, one shared text pre-processing pipeline:

* **Task 1** (`task1_search_engine/`) — a vertical search engine over
  publications by members of Coventry University's *Centre for
  Healthcare and Community Transformation* on PurePortal.
* **Task 2** (`task2_clustering/`) — a K-means document clustering
  system over a 210-document BBC News corpus (Economics / Entertainment
  / Politics), with a CLI to classify a brand-new document.

```
ir_coursework/
├── requirements.txt
├── shared/textprep.py          # pre-processing pipeline used by BOTH tasks
├── task1_search_engine/
│   ├── crawler.py               # polite PurePortal crawler (structured extraction)
│   ├── robots.py                 # robots.txt + crawl-delay politeness layer
│   ├── db.py                     # SQLite schema + inverted index storage
│   ├── indexer.py                # builds the TF-IDF inverted index
│   ├── search.py                  # query processing + cosine-similarity ranking
│   ├── run_pipeline.py            # one-shot: crawl -> store -> index
│   ├── scheduler.py               # weekly automatic re-crawl + reindex
│   ├── cli.py                      # plain-terminal search interface
│   ├── gui.py                       # Tkinter desktop UI with clickable result links
│   └── tests/test_crawler_offline.py  # full pipeline test against local fixture site
├── task2_clustering/
│   ├── data/{economics,entertainment,politics}/  # 70 docs each, see data/SOURCES.md
│   ├── clustering.py               # TF-IDF + KMeans + elbow/silhouette + evaluation
│   ├── predict.py                   # classify a new document
│   └── output/                       # generated: plots, metrics.json, model.joblib
├── notebooks_original/              # the original snippets this project builds on
└── report/                          # the written 2000-word report
```

## Setup

```bash
pip install -r requirements.txt
```

Both tasks work with **zero external services** — no MongoDB, no
Selenium/Chrome driver, no API keys. Task 1 stores its index in a single
SQLite file (`task1_search_engine/search_engine.db`), which trades a
little flexibility for something a marker can run in one command.

## Task 1 — run it

```bash
cd task1_search_engine

# 1. Crawl PurePortal + build the inverted index (first run can take a
#    few minutes — it's deliberately polite, see "Politeness" below)
python run_pipeline.py

# 2a. Search from the terminal...
python cli.py

# 2b. ...or launch the simple Tkinter desktop UI (clickable result links,
#     plus an "Update Index" button that re-crawls in the background)
python gui.py

# 3. Keep the index fresh automatically, once a week
python scheduler.py               # long-running; or use cron (see scheduler.py docstring)
```

### A note on testing this crawler in this environment

This project was developed inside a sandboxed cloud environment whose
network egress is restricted to package registries — it cannot reach
`pureportal.coventry.ac.uk` directly, so the crawler could not be
live-tested from there. Instead, `tests/test_crawler_offline.py` spins
up a small local HTTP server serving fixture HTML that mirrors Pure
Portal's real markup (`li.list-result-item`, `h3.title a`,
`a.link.person[rel="Person"]`, `span.date`, pagination via
`a.nextLink`/`?page=N`, a `robots.txt` with a `Crawl-Delay`), and runs
the **entire** pipeline against it end-to-end: robots.txt compliance,
pagination, structured field extraction, incremental re-crawl (a
second crawl of an unchanged site adds 0 new records), SQLite
persistence, inverted-index construction, and ranked search — all
assertions pass:

```bash
cd task1_search_engine
python tests/test_crawler_offline.py
```

`crawler.py`'s parsing functions try Pure's known CSS classes first and
fall back to more generic heuristics (regex over `href`s, nearby text)
if a class name doesn't match, so it degrades gracefully rather than
breaking outright if Coventry's theme changes. Run `python
run_pipeline.py` on any machine with normal internet access to perform
the real crawl against the live site.

### "HTTP Error 403: Forbidden" when actually crawling PurePortal

This is expected on some networks and isn't a robots.txt violation —
PurePortal's `robots.txt` explicitly permits crawling (`Crawl-Delay: 5`,
no relevant `Disallow`). The 403 comes from a separate WAF/bot-mitigation
layer that blocks plain, non-browser HTTP requests regardless of what
robots.txt says. `robots.py` handles this automatically: a plain request
is tried first, and if it comes back 403/429/503, it's retried once with
a real headless Chrome session via Selenium (the same technique the
original notebook used successfully against this exact site). To enable
it: `pip install selenium` and make sure Chrome/Chromium is installed —
Selenium will drive it headlessly, no extra setup needed on a machine
that already has Chrome. If Selenium isn't installed, the crawler logs a
one-line message and skips the blocked page instead of crashing.

### Politeness

* `robots.py` fetches and parses `robots.txt` before any page is
  requested, and skips (and counts) any URL it disallows.
* PurePortal's `robots.txt` declares `Crawl-Delay: 5`; `PoliteFetcher`
  reads that value and enforces at least that gap between requests to
  the same host (never less, even if you pass a smaller default).
* robots.txt permission and crawl-delay are always evaluated against the
  crawler's own declared identity (`crawler.USER_AGENT`, a descriptive
  string identifying the bot and its purpose) — the browser-like
  `User-Agent` sent on the wire (see previous section) only affects
  which requests get past incidental bot-mitigation, never what the
  crawler treats itself as allowed to do.
* The crawler only ever requests URLs on `pureportal.coventry.ac.uk`
  under the CHCT organisation/publications paths — it does not do
  open-ended crawling of the wider site or web.

## Task 2 — run it

```bash
cd task2_clustering
python clustering.py          # trains + evaluates + saves plots/model to output/
python predict.py "A new sentence describing some news story..."
```

`data/SOURCES.md` documents exactly where the corpus comes from and how
copyright is handled (see also the report). `clustering.py` prints and
saves purity / Adjusted Rand Index / Normalized Mutual Information
against the known ground-truth category (used only for evaluation —
K-means itself is unsupervised) plus elbow and silhouette plots
justifying K=3.

## Design decisions worth knowing about

* **SQLite instead of MongoDB, no Selenium.** The original notebook
  snippets used MongoDB + a headless Selenium/Chrome browser (needed
  because the *first* target site in that notebook, softwarica.edu.np,
  is a JS-rendered React site). PurePortal's publication listing pages
  are server-rendered HTML, so a plain `urllib` GET is sufficient and
  far lighter-weight; SQLite removes the need to stand up a database
  server just to run/mark this project.
* **The crawler extracts structured records, not generic page text.**
  The assignment specifically asks for title/authors+profile
  links/year/publication link per publication, so the crawler parses
  Pure's listing markup into `Publication` records rather than indexing
  whole pages of boilerplate text (nav bars, footers, etc.) the way a
  general-purpose crawler would.
* **Search uses the inverted index for lookup, not a full scan.** A
  query only ever touches documents that share at least one (stemmed)
  term with it, via `db.get_postings()` — this is what makes it an
  "inverted index" in the algorithmic sense, not just a name for a
  table of document vectors.
* **One shared pre-processing module (`shared/textprep.py`)** guarantees
  crawled text, search queries, and the Task 2 news corpus are all
  normalised identically (lowercase, strip punctuation, tokenize,
  stopword removal, stemming) — this matters because TF-IDF/cosine
  similarity only works if both sides of the comparison speak the same
  "vocabulary".
