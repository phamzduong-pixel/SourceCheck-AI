"""Classification metrics: Accuracy, Macro-F1, Weighted-F1, Per-class Precision/Recall/F1."""

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence


def compute_classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Compute comprehensive classification metrics:
    - Overall Accuracy
    - Macro-Precision, Macro-Recall, Macro-F1
    - Weighted-Precision, Weighted-Recall, Weighted-F1
    - Per-class detailed breakdown
    - Confusion matrix
    """
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"y_true (len={len(y_true)}) and y_pred (len={len(y_pred)}) must have equal length."
        )

    n_samples = len(y_true)
    if n_samples == 0:
        return {
            "total_samples": 0,
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "per_class": {},
            "confusion_matrix": {},
        }

    # Determine unique labels
    if labels is None:
        unique_labels = sorted(list(set(y_true).union(set(y_pred))))
    else:
        unique_labels = list(labels)

    # 1. Overall Accuracy
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / n_samples

    # 2. Confusion Matrix & Per-class counts
    # matrix[true_label][pred_label] = count
    confusion_matrix: Dict[str, Dict[str, int]] = {
        tl: {pl: 0 for pl in unique_labels} for tl in unique_labels
    }
    for yt, yp in zip(y_true, y_pred):
        if yt in confusion_matrix and yp in confusion_matrix[yt]:
            confusion_matrix[yt][yp] += 1

    per_class: Dict[str, Dict[str, Any]] = {}
    macro_p_sum = 0.0
    macro_r_sum = 0.0
    macro_f1_sum = 0.0
    weighted_p_sum = 0.0
    weighted_r_sum = 0.0
    weighted_f1_sum = 0.0

    for label in unique_labels:
        # TP: true is label and pred is label
        tp = confusion_matrix.get(label, {}).get(label, 0)
        # FP: true is NOT label and pred is label
        fp = sum(
            confusion_matrix[tl].get(label, 0)
            for tl in unique_labels
            if tl != label
        )
        # FN: true is label and pred is NOT label
        fn = sum(
            confusion_matrix.get(label, {}).get(pl, 0)
            for pl in unique_labels
            if pl != label
        )
        support = sum(confusion_matrix.get(label, {}).values())

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class[label] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }

        macro_p_sum += prec
        macro_r_sum += rec
        macro_f1_sum += f1

        weighted_p_sum += prec * support
        weighted_r_sum += rec * support
        weighted_f1_sum += f1 * support

    num_classes = len(unique_labels) if unique_labels else 1
    macro_precision = macro_p_sum / num_classes
    macro_recall = macro_r_sum / num_classes
    macro_f1 = macro_f1_sum / num_classes

    weighted_precision = weighted_p_sum / n_samples if n_samples > 0 else 0.0
    weighted_recall = weighted_r_sum / n_samples if n_samples > 0 else 0.0
    weighted_f1 = weighted_f1_sum / n_samples if n_samples > 0 else 0.0

    return {
        "total_samples": n_samples,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_precision": round(weighted_precision, 4),
        "weighted_recall": round(weighted_recall, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix,
    }
