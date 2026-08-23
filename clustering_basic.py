"""
Document clustering over corpus/{Economics,Entertainment,Politics}/*.txt:
TF-IDF + K-Means, then assign a new, user-entered document to one of the
fitted clusters.
"""
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

RANDOM_STATE = 42
CORPUS_DIR = Path("corpus")
K = 3  # Economics, Entertainment, Politics
TOP_TERMS = 8


def load_corpus():
    texts, true_labels = [], []
    for category_dir in sorted(CORPUS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue
        for path in sorted(category_dir.glob("*.txt")):
            texts.append(path.read_text(encoding="utf-8"))
            true_labels.append(category_dir.name)
    return texts, true_labels


def cluster_category_names(true_labels, cluster_labels, k):
    """Maps each cluster id to the majority category among its members, for
    a readable label."""
    names = {}
    for cluster_id in range(k):
        members = [true_labels[i] for i in range(len(true_labels)) if cluster_labels[i] == cluster_id]
        names[cluster_id] = max(set(members), key=members.count) if members else str(cluster_id)
    return names


def cluster_sizes(cluster_labels, k):
    return {cid: int(np.sum(cluster_labels == cid)) for cid in range(k)}


def top_terms_per_cluster(kmeans, vectorizer, top_n=TOP_TERMS):
    terms = vectorizer.get_feature_names_out()
    order = kmeans.cluster_centers_.argsort()[:, ::-1]
    return {cid: [terms[i] for i in order[cid, :top_n]] for cid in range(kmeans.n_clusters)}


def main():
    texts, true_labels = load_corpus()
    print(f"Loaded {len(texts)} documents across {len(set(true_labels))} categories.")

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2, max_df=0.9)
    X = vectorizer.fit_transform(texts)

    kmeans = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init=10)
    kmeans.fit(X)

    cluster_names = cluster_category_names(true_labels, kmeans.labels_, K)
    sizes = cluster_sizes(kmeans.labels_, K)
    top_terms = top_terms_per_cluster(kmeans, vectorizer)

    print("\nClusters found:")
    for cid in range(K):
        print(f"  Cluster {cid} ({cluster_names[cid]}, {sizes[cid]} docs) -- top terms: {', '.join(top_terms[cid])}")

    print("\nEnter a document to assign it to a cluster (blank line to quit).")
    while True:
        text = input("\nDocument text: ").strip()
        if not text:
            break

        vector = vectorizer.transform([text])
        cluster_id = kmeans.predict(vector)[0]
        distances = kmeans.transform(vector)[0]

        print(f"Assigned to cluster {cluster_id} ({cluster_names[cluster_id]})")
        print("Distance to each cluster centroid (closer = stronger match):")
        for cid in np.argsort(distances):
            marker = "  <-- assigned" if cid == cluster_id else ""
            print(f"  Cluster {cid} ({cluster_names[cid]}): {distances[cid]:.4f}{marker}")


if __name__ == "__main__":
    main()
