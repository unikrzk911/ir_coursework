"""
Task 2 — Document Clustering
=============================
Loads the labelled news corpus in `data/{economics,entertainment,politics}`,
vectorises it with TF-IDF (built on top of the shared pre-processing
pipeline: lowercase -> strip punctuation -> tokenize -> stopword removal
-> stemming), clusters it with K-means, and evaluates the clustering
against the known ground-truth category of each document (the ground
truth is only used for EVALUATION here — K-means itself is unsupervised
and never sees the labels while fitting).

Run:
    python clustering.py

Outputs (written to ./output/):
    - elbow.png            inertia vs K (elbow method)
    - silhouette.png        silhouette score vs K
    - confusion_matrix.png  true category vs assigned cluster
    - metrics.json           purity / ARI / NMI / silhouette for the chosen K
    - model.joblib            fitted TfidfVectorizer + KMeans + cluster->label
                               mapping, reloaded by predict.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    adjusted_rand_score,
    normalized_mutual_info_score,
    silhouette_score,
    confusion_matrix,
)
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.textprep import preprocess_to_string, backend_name  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUTPUT_DIR = os.path.join(HERE, "output")
CATEGORIES = ["economics", "entertainment", "politics"]
RANDOM_STATE = 42
CHOSEN_K = 3  # matches the 3 known categories; elbow/silhouette scan below
# also reports what K the data would suggest on its own.


def load_corpus(data_dir: str = DATA_DIR):
    texts, labels, filenames = [], [], []
    for category in CATEGORIES:
        folder = os.path.join(data_dir, category)
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(folder, fname)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
            texts.append(raw)
            labels.append(category)
            filenames.append(f"{category}/{fname}")
    return texts, labels, filenames


def vectorize(texts):
    print(f"[textprep backend: {backend_name()}] pre-processing {len(texts)} documents...")
    preprocessed = [preprocess_to_string(t) for t in texts]
    vectorizer = TfidfVectorizer(
        max_df=0.85,   # drop terms in >85% of docs (too common to discriminate)
        min_df=2,      # drop terms that appear in only one document (noise)
        sublinear_tf=True,
    )
    X = vectorizer.fit_transform(preprocessed)
    print(f"TF-IDF matrix: {X.shape[0]} docs x {X.shape[1]} terms")
    return X, vectorizer


def scan_k(X, k_range=range(2, 11)):
    inertias, sil_scores = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        km.fit(X)
        inertias.append(km.inertia_)
        sil_scores.append(silhouette_score(X, km.labels_))
    return list(k_range), inertias, sil_scores


def purity_score(true_labels, cluster_labels):
    """Fraction of documents assigned to the cluster that, after mapping
    each cluster to its majority true category, matches that category."""
    clusters = defaultdict(list)
    for t, c in zip(true_labels, cluster_labels):
        clusters[c].append(t)
    correct = sum(Counter(members).most_common(1)[0][1] for members in clusters.values())
    return correct / len(true_labels)


def majority_label_map(true_labels, cluster_labels):
    clusters = defaultdict(list)
    for t, c in zip(true_labels, cluster_labels):
        clusters[c].append(t)
    return {c: Counter(members).most_common(1)[0][0] for c, members in clusters.items()}


def plot_elbow(k_values, inertias, path):
    plt.figure(figsize=(6, 5))
    plt.plot(k_values, inertias, marker="o")
    plt.title("Elbow Method — Inertia vs K")
    plt.xlabel("Number of clusters (K)")
    plt.ylabel("Inertia")
    plt.xticks(k_values)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def plot_silhouette(k_values, sil_scores, path):
    plt.figure(figsize=(6, 5))
    plt.plot(k_values, sil_scores, marker="o", color="green")
    plt.title("Silhouette Score vs K")
    plt.xlabel("Number of clusters (K)")
    plt.ylabel("Silhouette score")
    plt.xticks(k_values)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def plot_confusion(true_labels, cluster_labels, label_map, path):
    mapped_pred = [label_map[int(c)] for c in cluster_labels]
    labels_sorted = CATEGORIES
    cm = confusion_matrix(true_labels, mapped_pred, labels=labels_sorted)
    plt.figure(figsize=(5.5, 5))
    plt.imshow(cm, cmap="Blues")
    plt.title("True category vs Predicted cluster (majority-mapped)")
    plt.colorbar()
    plt.xticks(range(len(labels_sorted)), labels_sorted, rotation=30)
    plt.yticks(range(len(labels_sorted)), labels_sorted)
    plt.xlabel("Predicted (cluster mapped to majority label)")
    plt.ylabel("True category")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center",
                      color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()
    return cm


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    texts, true_labels, filenames = load_corpus()
    if len(texts) < 100:
        print(f"WARNING: only {len(texts)} documents found (assignment asks for >= 100).")
    print(f"Loaded {len(texts)} documents across categories: {Counter(true_labels)}")

    X, vectorizer = vectorize(texts)

    print("Scanning K = 2..10 for elbow / silhouette diagnostics...")
    k_values, inertias, sil_scores = scan_k(X)
    plot_elbow(k_values, inertias, os.path.join(OUTPUT_DIR, "elbow.png"))
    plot_silhouette(k_values, sil_scores, os.path.join(OUTPUT_DIR, "silhouette.png"))
    best_k_by_silhouette = k_values[int(np.argmax(sil_scores))]
    print(f"Best K by silhouette score: {best_k_by_silhouette} "
          f"(this project uses K={CHOSEN_K} to match the 3 known categories)")

    print(f"Fitting final KMeans with K={CHOSEN_K} ...")
    kmeans = KMeans(n_clusters=CHOSEN_K, random_state=RANDOM_STATE, n_init=10)
    cluster_labels = kmeans.fit_predict(X)

    label_map = {int(k): v for k, v in majority_label_map(true_labels, cluster_labels).items()}
    print("Cluster -> majority category mapping:", label_map)

    purity = purity_score(true_labels, cluster_labels)
    ari = adjusted_rand_score(true_labels, cluster_labels)
    nmi = normalized_mutual_info_score(true_labels, cluster_labels)
    sil_final = silhouette_score(X, cluster_labels)

    cm = plot_confusion(true_labels, cluster_labels, label_map,
                         os.path.join(OUTPUT_DIR, "confusion_matrix.png"))

    metrics = {
        "n_documents": len(texts),
        "vocabulary_size": len(vectorizer.vocabulary_),
        "chosen_k": CHOSEN_K,
        "best_k_by_silhouette": best_k_by_silhouette,
        "silhouette_scan": dict(zip(k_values, sil_scores)),
        "inertia_scan": dict(zip(k_values, inertias)),
        "purity": purity,
        "adjusted_rand_index": ari,
        "normalized_mutual_info": nmi,
        "silhouette_at_chosen_k": sil_final,
        "cluster_to_category_map": label_map,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": CATEGORIES,
    }
    with open(os.path.join(OUTPUT_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print("\n=== Evaluation against ground-truth categories ===")
    print(f"Purity:                    {purity:.3f}")
    print(f"Adjusted Rand Index (ARI):  {ari:.3f}")
    print(f"Normalized Mutual Info:     {nmi:.3f}")
    print(f"Silhouette score (K={CHOSEN_K}):     {sil_final:.3f}")

    joblib.dump(
        {
            "vectorizer": vectorizer,
            "kmeans": kmeans,
            "label_map": label_map,
            "categories": CATEGORIES,
        },
        os.path.join(OUTPUT_DIR, "model.joblib"),
    )
    print(f"\nSaved trained model + plots + metrics to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
