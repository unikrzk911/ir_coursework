"""Streamlit GUI for crawler_basic.py: a crawl button, a search bar, and results."""
import streamlit as st

from crawler_basic import crawl, build_index, search

st.title("PurePortal Vertical Search Engine")

if st.button("Crawl"):
    with st.spinner("Crawling and indexing..."):
        count = crawl()
        build_index()
    st.success(f"Crawled {count} pages and rebuilt the index.")

query = st.text_input("Search query")
if st.button("Search") and query:
    results = search(query)
    if not results:
        st.write("No results found.")
    for score, url, title, authors, year in results:
        author_names = ", ".join(a["name"] for a in authors) if authors else "N/A"
        year_str = year if year else "N/A"
        st.markdown(
            f"**{title or url}**  \n"
            f"Authors: {author_names}  \n"
            f"Publication year: {year_str}  \n"
            f"{url}  \n"
            f"Score: {score:.4f}"
        )
