"""Evaluation metrics package for SourceCheck AI."""

from evaluation.metrics.retrieval import (
    evaluate_retrieval_batch,
    hit_at_k,
    mrr_at_k,
    precision_at_k,
    recall_at_k,
)
from evaluation.metrics.classification import compute_classification_metrics

__all__ = [
    "hit_at_k",
    "recall_at_k",
    "precision_at_k",
    "mrr_at_k",
    "evaluate_retrieval_batch",
    "compute_classification_metrics",
]
