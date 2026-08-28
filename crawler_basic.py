"""
Original notebook crawler (notebooks_original/original_crawler_snippet.ipynb),
flattened into a plain script and pointed at the publications page.

Only real change from the notebook: PurePortal puts a Cloudflare "Just a
moment..." challenge in front of /publications/ that plain Selenium can't
get past, so the driver setup swaps in undetected-chromedriver (headed,
not headless -- headless still gets stuck on the challenge) and waits for
the challenge page to clear before reading page_source. Everything else
(extraction, crawl loop, indexing, search) is the notebook's code as-is.
"""
import re
import sys
import time
import math
import types
import schedule
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import urllib.request
from collections import deque, Counter
from datetime import datetime, timezone

import nltk
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

from pymongo import MongoClient

# --- Python 3.12+ dropped distutils; undetected-chromedriver still imports
# it. Shim it in before importing uc (see task1_search_engine/_distutils_shim.py
# for the original of this). ---
if "distutils" not in sys.modules:
    try:
        import distutils  # noqa: F401
    except ModuleNotFoundError:
        class _LooseVersion:
            _component_re = re.compile(r"(\d+|[a-zA-Z]+|\.)")

            def __init__(self, vstring=None):
                self.vstring, self.version = "", []
                if vstring:
                    self.parse(vstring)

            def parse(self, vstring):
                self.vstring = vstring
                comps = [x for x in self._component_re.split(vstring) if x and x != "."]
                for i, o in enumerate(comps):
                    try:
                        comps[i] = int(o)
                    except ValueError:
                        pass
                self.version = comps

            def _cmp(self, other):
                if isinstance(other, str):
                    other = _LooseVersion(other)
                if self.version == other.version:
                    return 0
                return -1 if self.version < other.version else 1

            def __eq__(self, o): return self._cmp(o) == 0
            def __lt__(self, o): return self._cmp(o) < 0
            def __le__(self, o): return self._cmp(o) <= 0
            def __gt__(self, o): return self._cmp(o) > 0
            def __ge__(self, o): return self._cmp(o) >= 0

        distutils_mod = types.ModuleType("distutils")
        version_mod = types.ModuleType("distutils.version")
        version_mod.LooseVersion = _LooseVersion
        distutils_mod.version = version_mod
        sys.modules["distutils"] = distutils_mod
        sys.modules["distutils.version"] = version_mod

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

STOPWORDS = set(stopwords.words("english"))
stemmer = PorterStemmer()

# --- 2. MongoDB Connection ---
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["vertical_search_engine"]

raw_pages = db["raw_pages"]
doc_vectors = db["doc_vectors"]
term_index = db["term_index"]
crawl_log = db["crawl_log"]

raw_pages.create_index("url", unique=True)
doc_vectors.create_index("url", unique=True)
term_index.create_index("term", unique=True)

print("Connected:", db.name, "| collections:", db.list_collection_names())

# --- 3. Crawler ---
SEED_URL = "https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/publications/"
ALLOWED_DOMAIN = "pureportal.coventry.ac.uk"
CRAWL_DELAY_SECONDS = 1
MAX_PAGES = 200
USER_AGENT = "SoftwaricaVerticalSearchBot/1.0 (+educational IR project)"


def get_robot_parser(base_url):
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        rp.parse(raw.splitlines())
    except Exception:
        rp = None
    return rp


def can_fetch(rp, url):
    if rp is None:
        return True
    return rp.can_fetch(USER_AGENT, url)


def extract_content(html, base_url):
    """Safely extracts links and fully rendered text."""
    soup = BeautifulSoup(html, "html.parser")

    links = set()
    for a in soup.find_all("a", href=True):
        link = urljoin(base_url, a["href"]).split("#")[0]
        parsed = urlparse(link)
        if parsed.netloc.endswith(ALLOWED_DOMAIN) and parsed.scheme in ("http", "https"):
            links.add(link)

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if (soup.title and soup.title.string) else ""
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()

    return title, text, links


# Individual publication detail pages look like /en/publications/<slug>/ --
# distinct from listing pages like /en/publications/ or
# /en/organisations/<org>/publications/(?page=..) which have nothing after
# the "publications" segment.
PUBLICATION_PATH_RE = re.compile(r"^/en/publications/[^/?]+/?$")


def is_publication_page(url):
    return bool(PUBLICATION_PATH_RE.match(urlparse(url).path))


def extract_publication_meta(html):
    """Pulls title, authors (name + PurePortal profile link), and publication
    year from a publication detail page. Run only on pages that pass
    is_publication_page() -- the markup below (h1, ul.relations.persons,
    span.date) is specific to that page type."""
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    pub_title = h1.get_text(strip=True) if h1 else ""

    authors = []
    persons_ul = soup.select_one("ul.relations.persons")
    if persons_ul:
        for li in persons_ul.find_all("li"):
            a = li.find("a", class_="person")
            if a:
                authors.append({
                    "name": a.get_text(strip=True),
                    "profile_url": urljoin("https://" + ALLOWED_DOMAIN, a["href"]),
                })
            else:
                # co-authors with no PurePortal profile are listed as plain text
                name = li.get_text(strip=True).lstrip(",").strip()
                if name:
                    authors.append({"name": name, "profile_url": None})

    year = None
    for span in soup.select("span.date"):
        if "embargo-date" in (span.parent.get("class") or []):
            continue
        match = re.search(r"(19|20)\d{2}", span.get_text(strip=True))
        if match:
            year = int(match.group(0))
        break

    return pub_title, authors, year


def setup_driver():
    """Headed undetected-Chrome -- headless gets stuck on PurePortal's Cloudflare check."""
    options = uc.ChromeOptions()
    options.add_argument(f"user-agent={USER_AGENT}")
    driver = uc.Chrome(options=options, version_main=151)
    return driver


def wait_for_cloudflare(driver, timeout=15):
    """Blocks until the 'Just a moment...' interstitial clears."""
    start = time.time()
    while "Just a moment" in driver.title and time.time() - start < timeout:
        time.sleep(1)


def crawl(seed_url=SEED_URL, max_pages=MAX_PAGES):
    rp = get_robot_parser(seed_url)
    visited = set()
    queue = deque([seed_url])
    crawled_count = 0
    skipped_by_robots = 0

    print("Starting Chrome...")
    driver = setup_driver()

    try:
        while queue and crawled_count < max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            if not can_fetch(rp, url):
                print(f"Blocked by robots.txt: {url}")
                skipped_by_robots += 1
                continue

            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                wait_for_cloudflare(driver)
                time.sleep(1)  # hydration delay
                html = driver.page_source

            except Exception as e:
                print(f"Failed to fetch {url}: {e}")
                continue

            title, text, links = extract_content(html, url)

            record = {"url": url, "title": title, "text": text, "crawled_at": datetime.now(timezone.utc)}
            if is_publication_page(url):
                pub_title, authors, year = extract_publication_meta(html)
                record.update({
                    "title": pub_title or title,
                    "authors": authors,
                    "author_profile_urls": [a["profile_url"] for a in authors if a["profile_url"]],
                    "publication_year": year,
                })

            raw_pages.update_one(
                {"url": url},
                {"$set": record},
                upsert=True,
            )

            crawled_count += 1
            print(f"[{crawled_count}] Crawled: {url}")

            for link in links:
                if link not in visited:
                    queue.append(link)

            time.sleep(CRAWL_DELAY_SECONDS)

    finally:
        driver.quit()
        print("Closed Chrome.")

    crawl_log.insert_one({
        "run_at": datetime.now(timezone.utc),
        "pages_crawled": crawled_count,
        "skipped_by_robots": skipped_by_robots,
    })
    print(f"Crawl finished. {crawled_count} pages stored, {skipped_by_robots} skipped by robots.txt.")
    return crawled_count


def scheduled_job(seed_url=SEED_URL, max_pages=MAX_PAGES):
    print(f"Running scheduled weekly crawl at {datetime.now()}")
    crawl(seed_url, max_pages)
    build_index()


def run_weekly(seed_url=SEED_URL, max_pages=MAX_PAGES):
    """Blocks forever, re-crawling and re-indexing once a week. Run this in
    its own long-lived process (not inside the Streamlit app)."""
    schedule.every(7).days.do(scheduled_job, seed_url=seed_url, max_pages=max_pages)
    print("Weekly crawl scheduled. Waiting for the next run...")
    while True:
        schedule.run_pending()
        time.sleep(60)


# --- 5. Text Preprocessing ---
def preprocess(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = word_tokenize(text)
    tokens = [stemmer.stem(t) for t in tokens if t not in STOPWORDS and len(t) > 2]
    return tokens


# --- 6. Indexing -- Vector Space Model (TF-IDF) ---
def build_index():
    docs = list(raw_pages.find({}))
    N = len(docs)
    if N == 0:
        print("No documents to index. Run crawl() first.")
        return

    doc_tokens = {}
    df = Counter()

    for doc in docs:
        tokens = preprocess(doc["text"])
        doc_tokens[doc["url"]] = tokens
        for term in set(tokens):
            df[term] += 1

    idf = {term: math.log(N / (1 + freq)) + 1 for term, freq in df.items()}

    term_index.delete_many({})
    if idf:
        term_index.insert_many([{"term": t, "idf": v} for t, v in idf.items()])

    doc_vectors.delete_many({})
    for doc in docs:
        url = doc["url"]
        tokens = doc_tokens[url]
        total_terms = len(tokens) or 1
        tf = Counter(tokens)

        vector = {term: (count / total_terms) * idf.get(term, 0) for term, count in tf.items()}
        norm = math.sqrt(sum(w * w for w in vector.values())) or 1.0
        vector = {t: w / norm for t, w in vector.items()}

        doc_vectors.update_one(
            {"url": url},
            {"$set": {"url": url, "title": doc.get("title", ""), "vector": vector,
                       "authors": doc.get("authors", []),
                       "publication_year": doc.get("publication_year"),
                       "indexed_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    print(f"Indexed {N} documents. Vocabulary size: {len(idf)} terms.")


# --- 7. Query Processing & Cosine Similarity Ranking ---
def build_query_vector(query):
    tokens = preprocess(query)
    tf = Counter(tokens)
    total_terms = len(tokens) or 1

    idf_docs = term_index.find({"term": {"$in": list(tf.keys())}})
    idf_map = {d["term"]: d["idf"] for d in idf_docs}

    vector = {term: (count / total_terms) * idf_map[term] for term, count in tf.items() if term in idf_map}
    norm = math.sqrt(sum(w * w for w in vector.values())) or 1.0
    return {t: w / norm for t, w in vector.items()}


def cosine_similarity(vec1, vec2):
    common_terms = set(vec1.keys()) & set(vec2.keys())
    return sum(vec1[t] * vec2[t] for t in common_terms)


def search(query, top_k=10):
    q_vector = build_query_vector(query)
    if not q_vector:
        print("No matching terms found in the index.")
        return []

    results = []
    for doc in doc_vectors.find({}):
        score = cosine_similarity(q_vector, doc["vector"])
        if score > 0:
            results.append((
                score,
                doc["url"],
                doc.get("title", ""),
                doc.get("authors", []),
                doc.get("publication_year"),
            ))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    crawl()
    build_index()

    print("\nSample query: 'Mental Well-Being'")
    for score, url, title, authors, year in search("Mental Well-Being"):
        author_names = ", ".join(a["name"] for a in authors) if authors else ""
        print(f"{score:.4f}  {title}  ({year})  [{author_names}]  {url}")
