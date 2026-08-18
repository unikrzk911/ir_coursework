"""
Shared text pre-processing pipeline used by BOTH coursework tasks
(Task 1 search engine and Task 2 document clustering), so that crawled
publication text, user search queries, and news documents are all
normalised the same way before they are turned into vectors.

Pipeline (matches the approach used in the original crawler notebook):
  1. lower-case
  2. strip everything that isn't a letter/digit/whitespace
  3. tokenize
  4. drop English stopwords
  5. drop tokens shorter than `min_len`
  6. stem what's left (Porter-style)

Design note — graceful degradation:
NLTK (`punkt`, `stopwords`, `PorterStemmer`) gives the highest-quality
result, but its corpora must be downloaded from the internet the first
time it runs. This module tries NLTK first and, if it isn't installed or
its data can't be downloaded (e.g. no internet access), transparently
falls back to a dependency-free regex tokenizer, a built-in NLTK-derived
stopword list, and a pure-Python Porter-style stemmer implemented below.
Either way, `preprocess()` behaves identically to callers — the crawler,
the query processor and the clustering pipeline never need to know or
care which backend is active.
"""
from __future__ import annotations

import re
import functools

_STOPWORDS = None
_STEMMER = None
_BACKEND = None  # "nltk" or "builtin"


# --------------------------------------------------------------------------
# Pure-Python Porter-style stemmer (used when NLTK is unavailable).
# Implements the standard Porter (1980) suffix-stripping steps for the
# common English inflectional/derivational endings. This keeps the
# pipeline fully offline-capable while remaining faithful to the
# algorithm's spirit: strip plurals/verb endings first (step 1),
# then derivational suffixes (steps 2-4), then tidy up (step 5).
# --------------------------------------------------------------------------
class _SimplePorterStemmer:
    _VOWELS = "aeiou"

    def _measure(self, stem: str) -> int:
        """Approximate Porter's 'm' consonant-vowel-group count."""
        s = re.sub(r"[^aeiouy]+", "C", stem)
        s = re.sub(r"[aeiouy]+", "V", s)
        return s.count("CV") if s.startswith("C") else s.count("VC")

    def _contains_vowel(self, stem: str) -> bool:
        return any(c in self._VOWELS for c in stem)

    def stem(self, word: str) -> str:
        w = word.lower()
        if len(w) <= 2:
            return w

        # Step 1a: plurals
        if w.endswith("sses"):
            w = w[:-2]
        elif w.endswith("ies"):
            w = w[:-2]
        elif w.endswith("ss"):
            pass
        elif w.endswith("s") and len(w) > 3:
            w = w[:-1]

        # Step 1b: verb endings
        if w.endswith("eed"):
            if self._measure(w[:-3]) > 0:
                w = w[:-1]
        else:
            stripped = None
            if w.endswith("ed") and self._contains_vowel(w[:-2]):
                stripped = w[:-2]
            elif w.endswith("ing") and self._contains_vowel(w[:-3]):
                stripped = w[:-3]
            if stripped is not None:
                w = stripped
                if w.endswith(("at", "bl", "iz")):
                    w += "e"
                elif len(w) > 1 and w[-1] == w[-2] and w[-1] not in "lsz":
                    w = w[:-1]
                elif self._measure(w) == 1 and w[-2:] in ("cv",) :
                    w += "e"

        # Step 1c: y -> i
        if w.endswith("y") and len(w) > 2 and self._contains_vowel(w[:-1]):
            w = w[:-1] + "i"

        # Step 2/3/4: common derivational suffixes, longest first
        suffix_groups = [
            ("ational", "ate"), ("tional", "tion"), ("enci", "ence"),
            ("anci", "ance"), ("izer", "ize"), ("abli", "able"),
            ("alli", "al"), ("entli", "ent"), ("eli", "e"),
            ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
            ("ator", "ate"), ("alism", "al"), ("iveness", "ive"),
            ("fulness", "ful"), ("ousness", "ous"), ("aliti", "al"),
            ("iviti", "ive"), ("biliti", "ble"),
            ("icate", "ic"), ("ative", ""), ("alize", "al"),
            ("iciti", "ic"), ("ical", "ic"), ("ful", ""), ("ness", ""),
            ("ement", ""), ("ment", ""), ("ent", ""), ("ion", ""),
            ("al", ""), ("er", ""), ("ic", ""), ("able", ""),
            ("ible", ""), ("ant", ""), ("ive", ""), ("ize", ""),
            ("ous", ""),
        ]
        for suf, repl in suffix_groups:
            if w.endswith(suf) and len(w) - len(suf) >= 2:
                stem_part = w[: -len(suf)]
                if self._measure(stem_part) > 0:
                    w = stem_part + repl
                    break

        # Step 5a: remove trailing 'e' if measure > 1
        if w.endswith("e"):
            m = self._measure(w[:-1])
            if m > 1 or (m == 1 and not self._cvc(w[:-1])):
                w = w[:-1]

        # Step 5b: degemination of trailing double 'l'
        if w.endswith("ll") and self._measure(w[:-1]) > 1:
            w = w[:-1]

        return w

    def _cvc(self, stem: str) -> bool:
        if len(stem) < 3:
            return False
        c1, v, c2 = stem[-3], stem[-2], stem[-1]
        if v not in self._VOWELS and c1 in self._VOWELS and c2 not in self._VOWELS:
            return c2 not in "wxy"
        return False


_FALLBACK_STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further had hadn't has hasn't have haven't having he he'd he'll
he's her here here's hers herself him himself his how how's i i'd i'll
i'm i've if in into is isn't it it's its itself let's me more most
mustn't my myself no nor not of off on once only or other ought our ours
ourselves out over own same shan't she she'd she'll she's should
shouldn't so some such than that that's the their theirs them themselves
then there there's these they they'd they'll they're they've this those
through to too under until up very was wasn't we we'd we'll we're we've
were weren't what what's when when's where where's which while who
who's whom why why's with won't would wouldn't you you'd you'll you're
you've your yours yourself yourselves
""".split())


def _ensure_backend():
    global _STOPWORDS, _STEMMER, _BACKEND
    if _BACKEND is not None:
        return
    try:
        import nltk
        for pkg in ("punkt", "punkt_tab", "stopwords"):
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass
        from nltk.corpus import stopwords as nltk_stopwords
        from nltk.tokenize import word_tokenize
        from nltk.stem import PorterStemmer

        word_tokenize("warm up check")  # raises if punkt data missing
        _STOPWORDS = set(nltk_stopwords.words("english"))
        _STEMMER = PorterStemmer()
        _BACKEND = "nltk"
    except Exception:
        _STOPWORDS = _FALLBACK_STOPWORDS
        _STEMMER = _SimplePorterStemmer()
        _BACKEND = "builtin"


def backend_name() -> str:
    _ensure_backend()
    return _BACKEND


def tokenize(text: str):
    _ensure_backend()
    if _BACKEND == "nltk":
        from nltk.tokenize import word_tokenize
        return word_tokenize(text)
    return re.findall(r"[a-z0-9]+", text)


def preprocess(text: str, min_len: int = 3) -> list[str]:
    """Lowercase -> strip punctuation -> tokenize -> remove stopwords ->
    remove very short tokens -> stem. Returns a list of stemmed terms.
    Used for crawled document text, user search queries, and the
    clustering corpus alike."""
    if not text:
        return []
    _ensure_backend()
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = tokenize(text)
    return [
        _STEMMER.stem(t)
        for t in tokens
        if t not in _STOPWORDS and len(t) >= min_len
    ]


def preprocess_to_string(text: str, min_len: int = 3) -> str:
    """Convenience wrapper returning the stemmed tokens re-joined into a
    single space-separated string (handy as input to scikit-learn's
    TfidfVectorizer with its default whitespace tokenizer)."""
    return " ".join(preprocess(text, min_len=min_len))
