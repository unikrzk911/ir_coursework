"""Streamlit GUI: choose Task 1 (search engine) or Task 2 (document clustering)."""
import streamlit as st

st.title("ST7071CEM IR Coursework")

task = st.radio(
    "Choose a task",
    ["Task 1: Search Engine", "Task 2: Document Clustering"],
    horizontal=True,
)

if task == "Task 1: Search Engine":
    from crawler_basic import crawl, build_index, search

    st.header("PurePortal Vertical Search Engine")

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

else:
    from clustering_basic import K, classify, fit_model

    st.header("Document Clustering: Economics / Entertainment / Politics")

    @st.cache_resource
    def get_model():
        return fit_model()

    model = get_model()
    st.write(f"Loaded {model['doc_count']} documents across {model['category_count']} categories.")

    st.subheader("Clusters found")
    for cid in range(K):
        terms = ", ".join(model["top_terms"][cid])
        st.markdown(
            f"**Cluster {cid} ({model['cluster_names'][cid]}, {model['sizes'][cid]} docs)**  \n"
            f"Top terms: {terms}"
        )

    st.subheader("Classify a new document")

    EXAMPLE_DOCUMENTS = {
        "Economics example": (
            "The Federal Reserve is expected to cut interest rates next month amid "
            "slowing inflation. Analysts on Wall Street are watching bond yields "
            "closely following the announcement."
        ),
        "Entertainment example": (
            "Critics are praising the visual effects and soundtrack of the new "
            "Marvel blockbuster, which broke opening weekend box office records."
        ),
        "Politics example": (
            "Senators clashed over a new bill regulating social media companies "
            "during a heated committee hearing."
        ),
    }

    example_cols = st.columns(len(EXAMPLE_DOCUMENTS))
    for col, (label, example_text) in zip(example_cols, EXAMPLE_DOCUMENTS.items()):
        if col.button(label):
            st.session_state["cluster_doc_text"] = example_text

    text = st.text_area("Document text", key="cluster_doc_text")
    if st.button("Assign to cluster") and text:
        cluster_id, distances = classify(model, text)
        st.success(f"Assigned to cluster {cluster_id} ({model['cluster_names'][cluster_id]})")
        st.write("Distance to each cluster centroid (closer = stronger match):")
        for cid, dist in distances.items():
            marker = "  <-- assigned" if cid == cluster_id else ""
            st.write(f"Cluster {cid} ({model['cluster_names'][cid]}): {dist:.4f}{marker}")
