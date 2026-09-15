"""Retrieval evaluation metrics: Hit@K, Recall@K, Precision@K, MRR@K."""

from typing import Any, Dict, Iterable, List, Sequence, Set, Union


def hit_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Sequence[str], Set[str]],
    k: int = 5,
) -> float:
    """Compute Hit@K: 1.0 if at least one relevant item appears in top-K, else 0.0."""
    if not ground_truth_ids or k <= 0:
        return 0.0
    gt_set = set(ground_truth_ids)
    top_k = retrieved_ids[:k]
    return 1.0 if any(item in gt_set for item in top_k) else 0.0


def recall_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Sequence[str], Set[str]],
    k: int = 5,
) -> float:
    """Compute Recall@K: proportion of relevant items retrieved in top-K."""
    if not ground_truth_ids or k <= 0:
        return 0.0
    gt_set = set(ground_truth_ids)
    top_k_set = set(retrieved_ids[:k])
    intersection = top_k_set.intersection(gt_set)
    return len(intersection) / len(gt_set)


def precision_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Sequence[str], Set[str]],
    k: int = 5,
) -> float:
    """Compute Precision@K: proportion of top-K items that are relevant."""
    if k <= 0:
        return 0.0
    gt_set = set(ground_truth_ids)
    top_k = retrieved_ids[:k]
    relevant_retrieved = sum(1 for item in top_k if item in gt_set)
    return relevant_retrieved / min(k, len(top_k)) if top_k else 0.0


def mrr_at_k(
    retrieved_ids: Sequence[str],
    ground_truth_ids: Union[Sequence[str], Set[str]],
    k: int = 5,
) -> float:
    """Compute Mean Reciprocal Rank (MRR@K): 1/rank of the first relevant item in top-K."""
    if not ground_truth_ids or k <= 0:
        return 0.0
    gt_set = set(ground_truth_ids)
    for rank, item in enumerate(retrieved_ids[:k], start=1):
        if item in gt_set:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval_batch(
    eval_items: List[Dict[str, Any]],
    k_list: Sequence[int] = (1, 3, 5),
) -> Dict[str, Any]:
    """Evaluate a batch of retrieval query results against ground truth relevance.
    
    Each item in eval_items must have:
    - 'retrieved_ids': List[str]
    - 'ground_truth_ids': List[str]
    """
    if not eval_items:
        return {
            "total_queries": 0,
            "metrics": {},
        }

    results: Dict[str, float] = {}
    n = len(eval_items)

    for k in k_list:
        hits = [
            hit_at_k(item.get("retrieved_ids", []), item.get("ground_truth_ids", []), k=k)
            for item in eval_items
        ]
        recalls = [
            recall_at_k(item.get("retrieved_ids", []), item.get("ground_truth_ids", []), k=k)
            for item in eval_items
        ]
        precisions = [
            precision_at_k(item.get("retrieved_ids", []), item.get("ground_truth_ids", []), k=k)
            for item in eval_items
        ]
        mrrs = [
            mrr_at_k(item.get("retrieved_ids", []), item.get("ground_truth_ids", []), k=k)
            for item in eval_items
        ]

        results[f"hit@{k}"] = round(sum(hits) / n, 4)
        results[f"recall@{k}"] = round(sum(recalls) / n, 4)
        results[f"precision@{k}"] = round(sum(precisions) / n, 4)
        results[f"mrr@{k}"] = round(sum(mrrs) / n, 4)

    return {
        "total_queries": n,
        "metrics": results,
    }
