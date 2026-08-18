"""
Plain command-line search interface (this alone satisfies "the usual
Python interface in your IDE would do" — gui.py additionally offers a
simple Tkinter window with clickable result links for easier browsing).

    python cli.py

Result titles and author names are printed as clickable terminal
hyperlinks (OSC 8) in terminals that support it, so you can click
straight through instead of copy/pasting URLs — the assignment calls
this out as preferable even for a non-web interface.
"""
import os
import sys

import db as db_mod
from search import run_cli_search_interface

if __name__ == "__main__":
    if not os.path.exists(db_mod.DB_PATH):
        print("No index found yet.")
        print("Run `python run_pipeline.py` first to crawl PurePortal and build the index.\n")
        sys.exit(1)
    run_cli_search_interface()
