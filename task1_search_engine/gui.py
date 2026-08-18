"""
Task 1 — simple Tkinter desktop UI.

A search box, a "Update Index" button to (re)crawl PurePortal, and a
results pane where each title and author name is a clickable link
(opens in your browser) — this is what the assignment means by
"preferable to be able to click on the printed links rather than
copying and pasting them", without needing a web server.

    python gui.py

Tkinter ships with standard Python (including the python.org installers
for Windows/macOS). On Linux, if `import tkinter` fails, install it with
your package manager, e.g. `sudo apt install python3-tk`.
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import db as db_mod
from search import search as run_search


class SearchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("CHCT Publication Search")
        root.geometry("820x600")
        self._link_counter = 0

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")

        self.query_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.query_var)
        entry.pack(side="left", fill="x", expand=True, padx=8)
        entry.bind("<Return>", lambda e: self.do_search())
        entry.focus_set()

        ttk.Button(top, text="Search", command=self.do_search).pack(side="left")
        self.update_btn = ttk.Button(top, text="Update Index", command=self.do_crawl)
        self.update_btn.pack(side="left", padx=(8, 0))

        self.status_var = tk.StringVar()
        ttk.Label(root, textvariable=self.status_var, padding=(10, 0), foreground="#555").pack(fill="x")

        body = ttk.Frame(root, padding=(10, 6, 10, 10))
        body.pack(fill="both", expand=True)
        self.text = tk.Text(body, wrap="word", cursor="arrow", state="disabled", borderwidth=0)
        scrollbar = ttk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.text.tag_configure("title", font=("TkDefaultFont", 12, "bold"), foreground="#1a56db")
        self.text.tag_configure("meta", foreground="#178038")
        self.text.tag_configure("snippet", foreground="#333333")
        self.text.tag_configure("url", foreground="#006621", font=("TkDefaultFont", 9))

        self.refresh_status()

    # -- helpers -----------------------------------------------------
    def _add_link(self, text: str, url: str, base_tag: str):
        tag = f"link-{self._link_counter}"
        self._link_counter += 1
        self.text.insert("end", text, (base_tag, tag))
        self.text.tag_configure(tag, underline=True)
        self.text.tag_bind(tag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
        self.text.tag_bind(tag, "<Enter>", lambda e: self.text.config(cursor="hand2"))
        self.text.tag_bind(tag, "<Leave>", lambda e: self.text.config(cursor="arrow"))

    def refresh_status(self):
        if not os.path.exists(db_mod.DB_PATH):
            self.status_var.set('No index yet — click "Update Index" to crawl PurePortal.')
            return
        with db_mod.get_conn(db_mod.DB_PATH) as conn:
            n = conn.execute("SELECT COUNT(*) AS n FROM publications").fetchone()["n"]
            last = conn.execute("SELECT run_at FROM crawl_log ORDER BY run_at DESC LIMIT 1").fetchone()
        last_str = f", last crawled {last['run_at'][:19]} UTC" if last else ""
        self.status_var.set(f"{n} publication(s) indexed{last_str}")

    # -- search --------------------------------------------------------
    def do_search(self):
        query = self.query_var.get().strip()
        self.text.config(state="normal")
        self.text.delete("1.0", "end")

        if not query:
            self.text.config(state="disabled")
            return
        if not os.path.exists(db_mod.DB_PATH):
            self.text.insert("end", 'No index yet. Click "Update Index" first.\n')
            self.text.config(state="disabled")
            return

        results = run_search(query, top_k=20)
        if not results:
            self.text.insert("end", f'No results found for "{query}".\n')

        for i, r in enumerate(results, start=1):
            self.text.insert("end", f"{i}. ")
            self._add_link(r["title"] or "(untitled)", r["pub_url"], "title")
            year = f" ({r['year']})" if r["year"] else ""
            self.text.insert("end", f"{year}   score {r['score']:.3f}\n", "meta")

            if r["authors"]:
                for j, (name, url) in enumerate(r["authors"]):
                    if url:
                        self._add_link(name, url, "meta")
                    else:
                        self.text.insert("end", name, "meta")
                    if j != len(r["authors"]) - 1:
                        self.text.insert("end", ", ", "meta")
                self.text.insert("end", "\n")

            if r["snippet"]:
                self.text.insert("end", r["snippet"] + "\n", "snippet")
            self.text.insert("end", r["pub_url"] + "\n\n", "url")

        self.text.config(state="disabled")
        self.status_var.set(f'{len(results)} result(s) for "{query}"')

    # -- crawl / update index --------------------------------------------
    def do_crawl(self):
        self.update_btn.config(state="disabled")
        self.status_var.set("Crawling PurePortal and rebuilding the index... this can take a while.")
        threading.Thread(target=self._crawl_worker, daemon=True).start()

    def _crawl_worker(self):
        try:
            import run_pipeline
            run_pipeline.run_once()
            self.root.after(0, self._crawl_done, None)
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, self._crawl_done, exc)

    def _crawl_done(self, error: Exception | None):
        self.update_btn.config(state="normal")
        if error is not None:
            messagebox.showerror("Crawl failed", str(error))
            self.status_var.set("Crawl failed — see error dialog.")
        else:
            self.refresh_status()


def main():
    root = tk.Tk()
    SearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
