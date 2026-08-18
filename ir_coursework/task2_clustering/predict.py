"""
Task 2 — assign a NEW document to one of the existing clusters.

Usage:
    python predict.py "A new sentence or document to classify..."
    python predict.py                 # interactive mode, prompts for input
    python predict.py --file path.txt # classify the contents of a file

Loads the TF-IDF vectorizer + KMeans model trained by clustering.py
(output/model.joblib), pre-processes the new document with the exact
same pipeline used for training, projects it into the same TF-IDF space,
and reports which cluster (and, via the majority-vote mapping learned
during training, which of Economics / Entertainment / Politics) it is
closest to — together with the distance to every cluster centroid, so
the result isn't a black box.
"""
from __future__ import annotations

import argparse
import os
import sys

import joblib
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.textprep import preprocess_to_string  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "output", "model.joblib")


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise SystemExit(
            f"No trained model found at {MODEL_PATH}.\n"
            f"Run `python clustering.py` first to train and save the model."
        )
    return joblib.load(MODEL_PATH)


def classify(text: str, bundle=None):
    bundle = bundle or load_model()
    vectorizer = bundle["vectorizer"]
    kmeans = bundle["kmeans"]
    label_map = bundle["label_map"]

    cleaned = preprocess_to_string(text)
    if not cleaned.strip():
        raise ValueError("After pre-processing, this document contains no usable terms.")

    vec = vectorizer.transform([cleaned])
    cluster_id = int(kmeans.predict(vec)[0])
    category = label_map.get(cluster_id, f"cluster_{cluster_id}")

    distances = kmeans.transform(vec)[0]  # distance to every centroid
    ranked = sorted(
        ((label_map.get(int(c), f"cluster_{c}"), float(d)) for c, d in enumerate(distances)),
        key=lambda x: x[1],
    )
    return {
        "predicted_category": category,
        "predicted_cluster_id": cluster_id,
        "distances_to_all_clusters": ranked,
    }


def main():
    parser = argparse.ArgumentParser(description="Classify a new document into a learned cluster.")
    parser.add_argument("text", nargs="?", help="Document text to classify")
    parser.add_argument("--file", help="Path to a text file to classify instead of inline text")
    args = parser.parse_args()

    bundle = load_model()

    if args.file:
        with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        print("Enter/paste the document text, then press Enter on an empty line to classify:")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "":
                break
            lines.append(line)
        text = "\n".join(lines)

    if not text.strip():
        raise SystemExit("No text provided.")

    result = classify(text, bundle=bundle)
    print(f"\nPredicted category: {result['predicted_category'].upper()} "
          f"(cluster #{result['predicted_cluster_id']})")
    print("\nDistance to every cluster centroid (smaller = closer):")
    for category, dist in result["distances_to_all_clusters"]:
        print(f"  {category:<15s} {dist:.4f}")


if __name__ == "__main__":
    main()
