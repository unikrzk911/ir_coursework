"""
Politeness layer: robots.txt compliance + rate limiting, shared by the
crawler. This is what the assignment means by "your crawler is polite,
i.e. it preserves the robots.txt rules and does not hit the servers
unnecessarily or too fast."
"""
from __future__ import annotations

import time
import urllib.request
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class PoliteFetcher:
    """Wraps robots.txt rules + a minimum delay between requests to the
    same host. `crawl_delay` falls back to a safe default if the site's
    robots.txt doesn't declare one; if it *does* declare one (as Pure
    Portal's does — 5 seconds), that value always wins, since the whole
    point is to respect what the site operator asked for."""

    def __init__(self, user_agent: str, default_delay: float = 3.0, timeout: int = 15):
        self.user_agent = user_agent
        self.default_delay = default_delay
        self.timeout = timeout
        self._parsers: dict[str, RobotFileParser] = {}
        self._last_request_time: dict[str, float] = {}
        self.skipped_by_robots = 0

    def _get_parser(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        host = parsed.netloc
        if host in self._parsers:
            return self._parsers[host]

        robots_url = f"{parsed.scheme}://{host}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            req = urllib.request.Request(robots_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
            rp.parse(raw.splitlines())
        except Exception:
            # No robots.txt (or unreachable) => treat as "allow everything",
            # per the standard's convention, but keep the default delay.
            rp.parse([])
        self._parsers[host] = rp
        return rp

    def can_fetch(self, url: str) -> bool:
        rp = self._get_parser(url)
        allowed = rp.can_fetch(self.user_agent, url)
        if not allowed:
            self.skipped_by_robots += 1
        return allowed

    def crawl_delay(self, url: str) -> float:
        rp = self._get_parser(url)
        host = urlparse(url).netloc
        delay = None
        try:
            delay = rp.crawl_delay(self.user_agent)
        except Exception:
            pass
        if delay is None:
            try:
                req_rate = rp.request_rate(self.user_agent)
                if req_rate:
                    delay = req_rate.seconds / max(req_rate.requests, 1)
            except Exception:
                pass
        return float(delay) if delay else self.default_delay

    def wait_if_needed(self, url: str):
        """Block just long enough to respect this host's crawl-delay
        since our last request to it — never hammer the server."""
        host = urlparse(url).netloc
        delay = self.crawl_delay(url)
        last = self._last_request_time.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            remaining = delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_time[host] = time.monotonic()

    def fetch(self, url: str, allow_redirects: bool = True) -> str | None:
        """Politely GET a URL: checks robots.txt, waits out the crawl
        delay, then fetches. Returns None (and does not raise) if the
        page is disallowed or the request fails, so the crawler loop can
        just skip it and move on."""
        if not self.can_fetch(url):
            return None
        self.wait_if_needed(url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="ignore")
        except Exception as exc:
            print(f"  [fetch failed] {url}: {exc}")
            return None
