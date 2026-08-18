"""
Scheduled re-crawl: "because of low rate of changes to this information,
your crawler may be scheduled to look for new information, say, once
per week, but it should ideally be able to do so automatically... Every
time it runs, it should update the index with the new data."

Two ways to run it, both included:

1. In-process background thread (start_background_scheduler) — handy
   for a demo or for keeping a long-running app's index warm while it
   runs. Simple, but only re-crawls while that process is alive.

2. OS-level scheduling (recommended for a real deployment) — this
   script can equally be invoked directly by cron / Windows Task
   Scheduler, e.g.:

       # crontab -e   (every Monday at 03:00)
       0 3 * * 1  cd /path/to/task1_search_engine && /usr/bin/python3 run_pipeline.py >> crawl.log 2>&1

   This is more robust than an in-process sleep loop (survives reboots,
   doesn't depend on a long-lived process, easy to monitor via normal
   OS tooling) and is what's documented as the production approach in
   the report; the in-process option below exists for convenience when
   just running the whole thing from one script/one terminal.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime

from run_pipeline import run_once


def run_weekly_scheduler(interval_days: float = 7, **crawl_kwargs):
    """Blocking loop: run the crawl+index pipeline immediately, then
    again every `interval_days`, forever. Call this directly if you just
    want a single long-lived "scheduler process" (e.g. `python
    scheduler.py`); use start_background_scheduler() instead if another
    program needs to keep running at the same time.
    """
    while True:
        print(f"[{datetime.now().isoformat()}] Running scheduled crawl + reindex...")
        try:
            run_once(**crawl_kwargs)
        except Exception as exc:
            print(f"[{datetime.now().isoformat()}] Scheduled run FAILED: {exc}")
        sleep_seconds = interval_days * 24 * 3600
        print(f"Sleeping for {interval_days} day(s) until the next scheduled crawl.")
        time.sleep(sleep_seconds)


def start_background_scheduler(interval_days: float = 7, **crawl_kwargs) -> threading.Thread:
    """Runs run_weekly_scheduler in a daemon thread so a long-lived
    process can keep serving search requests while the index refreshes
    itself in the background."""
    thread = threading.Thread(
        target=run_weekly_scheduler,
        kwargs={"interval_days": interval_days, **crawl_kwargs},
        daemon=True,
    )
    thread.start()
    return thread


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the crawl+index pipeline every N days, forever.")
    parser.add_argument("--interval-days", type=float, default=7)
    parser.add_argument("--max-publications", type=int, default=None)
    args = parser.parse_args()

    run_weekly_scheduler(interval_days=args.interval_days, max_publications=args.max_publications)
