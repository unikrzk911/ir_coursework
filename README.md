# ST7071CEM Information Retrieval Coursework

A vertical search engine over publications by members of Coventry
University's *Centre for Healthcare and Community Transformation* on
PurePortal — crawl, TF-IDF index, and cosine-similarity search, backed
by MongoDB.

```
ir_coursework/
├── requirements.txt
├── crawler_basic.py       # crawl -> MongoDB -> TF-IDF index -> search, all in one script
├── notebooks_original/    # the original notebook snippets this builds on
└── report/                # the written 2000-word report
```

`crawler_basic.py` is a flattened, single-file version of
`notebooks_original/original_crawler_snippet.ipynb`: same crawl loop,
same TF-IDF indexing, same cosine-similarity search — just as a plain
script instead of notebook cells, pointed at the CHCT publications page.

## Setup

```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"
```

Requires a local MongoDB instance running on `mongodb://localhost:27017/`
(db `vertical_search_engine`), and Chrome installed locally.

## Run it

```bash
python crawler_basic.py
```

This crawls up to `MAX_PAGES` pages from `SEED_URL`, stores them in
MongoDB (`raw_pages`), builds the TF-IDF index (`doc_vectors`,
`term_index`), logs the run (`crawl_log`), and prints a sample search.

To search interactively or run more queries, import the module's
functions (`crawl`, `build_index`, `search`) from a Python shell — same
functions as the notebook, e.g.:

```python
from crawler_basic import search
for score, url, title in search("healthcare research"):
    print(f"{score:.4f}  {title}  ({url})")
```

## A note on Cloudflare

PurePortal's `robots.txt` permits crawling, but puts a Cloudflare "Just
a moment..." challenge in front of pages — plain Selenium (what the
original notebook used) gets stuck on it. `crawler_basic.py` uses
`undetected-chromedriver` in **headed** mode instead (a visible Chrome
window pops up while crawling — headless still gets stuck on the
challenge) and waits for the challenge to clear before reading the page.
Everything else — extraction, crawl loop, indexing, search — is the
notebook's code unchanged.
