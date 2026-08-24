"""
Evaluates clustering_basic.py's classify() against a held-out set of
hand-written sentences that are NOT part of the training corpus — the same
generalisation test described in the report's Task 2 evaluation section
(the one that improved from 7/9 to 9/9 after adding more concrete
vocabulary to the corpus templates).

Run from the project root, alongside clustering_basic.py and corpus/:

    python evaluate_holdout.py

Prints a per-sentence pass/fail table plus accuracy / Adjusted Rand Index /
Normalised Mutual Information, and saves confusion_matrix.png — screenshot
either (or both) for the report's Figure 12 placeholder.

If your actual held-out set (the one that produced your reported 9/9)
used different sentences, replace HOLDOUT_SET below with those exact ones
so the figure matches what the report claims.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    adjusted_rand_score,
    confusion_matrix,
    normalized_mutual_info_score,
)

from clustering_basic import classify, fit_model

# (sentence, true_category) -- true_category must exactly match a
# corpus/<Category> folder name (Economics / Entertainment / Politics).
HOLDOUT_SET = [
    ("The Federal Reserve is expected to cut interest rates next month amid slowing inflation.", "Economics"),
    ("Wall Street closed higher today after the company's latest earnings report beat expectations.", "Economics"),
    ("Consumer prices rose again this quarter, adding pressure on household budgets nationwide.", "Economics"),
    ("The studio's new blockbuster topped the box office in its opening weekend, according to Rotten Tomatoes.", "Entertainment"),
    ("Fans lined up outside the theatre hours before the film's midnight release.", "Entertainment"),
    ("The streaming platform announced a new season of its most-watched series.", "Entertainment"),
    ("Senators clashed over a new bill regulating social media companies.", "Politics"),
    ("Voter turnout is expected to be historically high in the upcoming election.", "Politics"),
    ("Lawmakers on the campaign trail debated the government's latest policy proposal.", "Politics"),
]


def main():
    model = fit_model()

    true_labels, pred_labels = [], []
    print("Held-out classification pass:\n")
    for text, true_category in HOLDOUT_SET:
        cluster_id, _distances = classify(model, text)
        predicted_category = model["cluster_names"][cluster_id]
        outcome = "correct" if predicted_category == true_category else "WRONG"
        print(f"  [{outcome:7}] true={true_category:<13} predicted={predicted_category:<13} \"{text}\"")
        true_labels.append(true_category)
        pred_labels.append(predicted_category)

    accuracy = accuracy_score(true_labels, pred_labels)
    correct_count = round(accuracy * len(HOLDOUT_SET))
    ari = adjusted_rand_score(true_labels, pred_labels)
    nmi = normalized_mutual_info_score(true_labels, pred_labels)

    print(f"\nAccuracy: {accuracy:.2f}  ({correct_count}/{len(HOLDOUT_SET)})")
    print(f"Adjusted Rand Index: {ari:.2f}")
    print(f"Normalised Mutual Information: {nmi:.2f}")

    labels = sorted(set(true_labels) | set(pred_labels))
    cm = confusion_matrix(true_labels, pred_labels, labels=labels)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)

    fig, ax = plt.subplots(figsize=(5, 5))
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"Held-Out Classification — {correct_count}/{len(HOLDOUT_SET)} Correct")
    plt.tight_layout()

    out_path = Path("confusion_matrix.png")
    fig.savefig(out_path, dpi=200)
    print(f"\nSaved confusion matrix plot to {out_path.resolve()}")


if __name__ == "__main__":
    main()
