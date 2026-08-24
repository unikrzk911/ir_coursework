# ST7071CEM Information Retrieval Coursework

Two tasks, one Streamlit GUI:

- **Task 1 — Search Engine**: a vertical search engine over publications by
  members of Coventry University's *Centre for Healthcare and Community
  Transformation* on PurePortal — crawl, TF-IDF index, and cosine-similarity
  search, backed by MongoDB.
- **Task 2 — Document Clustering**: TF-IDF + K-Means clustering of a
  generated Economics / Entertainment / Politics corpus, with a held-out
  generalisation evaluation.

```
ir_coursework/
├── requirements.txt
├── app.py                 # Streamlit GUI for both tasks
├── crawler_basic.py       # Task 1: crawl -> MongoDB -> TF-IDF index -> search
├── generate_documents.py  # Task 2: builds corpus/ from category templates
├── clustering_basic.py    # Task 2: TF-IDF + K-Means fit_model()/classify()
├── evaluate_holdout.py    # Task 2: held-out generalisation eval + confusion matrix
├── corpus/                # Task 2: generated Economics/Entertainment/Politics .txt files
├── notebooks_original/    # the original notebook snippets Task 1 builds on
└── report/                # the written coursework report
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

Task 1 requires a local MongoDB instance running on
`mongodb://localhost:27017/` (db `vertical_search_engine`), and Chrome
installed locally. Task 2 has no external dependencies beyond the pip
packages.

## Run it

```bash
streamlit run app.py
```

Opens a GUI to switch between Task 1 (crawl/search) and Task 2 (view
clusters, classify a new document).

### Task 1 — from the command line

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

### Task 2 — from the command line

```bash
python generate_documents.py   # only needed if corpus/ doesn't exist yet
python clustering_basic.py     # fits the model, prints clusters, lets you classify text interactively
python evaluate_holdout.py     # runs the held-out generalisation test, saves confusion_matrix.png
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
