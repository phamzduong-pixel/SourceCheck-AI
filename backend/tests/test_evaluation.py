"""Tests for RAG and Fact-Checking Minimal Evaluation Framework (CHAT-04.8)."""

from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.metrics.classification import compute_classification_metrics
from evaluation.metrics.retrieval import (
    evaluate_retrieval_batch,
    hit_at_k,
    mrr_at_k,
    precision_at_k,
    recall_at_k,
)
from evaluation.run_evaluation import EvaluationRunner, load_dataset

DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "rag_benchmark_dataset.json"


# =========================================================================
# 1. Unit Tests for Retrieval Metrics
# =========================================================================

def test_hit_at_k():
    retrieved = ["doc_1", "doc_2", "doc_3", "doc_4"]
    ground_truth = ["doc_3", "doc_9"]

    assert hit_at_k(retrieved, ground_truth, k=1) == 0.0
    assert hit_at_k(retrieved, ground_truth, k=2) == 0.0
    assert hit_at_k(retrieved, ground_truth, k=3) == 1.0
    assert hit_at_k(retrieved, ground_truth, k=5) == 1.0
    assert hit_at_k([], ground_truth, k=5) == 0.0
    assert hit_at_k(retrieved, [], k=5) == 0.0


def test_recall_at_k():
    retrieved = ["c1", "c2", "c3", "c4", "c5"]
    ground_truth = ["c1", "c3", "c9"]  # total 3 relevant

    assert recall_at_k(retrieved, ground_truth, k=1) == pytest.approx(1 / 3, rel=1e-3)
    assert recall_at_k(retrieved, ground_truth, k=3) == pytest.approx(2 / 3, rel=1e-3)
    assert recall_at_k(retrieved, ground_truth, k=5) == pytest.approx(2 / 3, rel=1e-3)


def test_precision_at_k():
    retrieved = ["c1", "c2", "c3", "c4"]
    ground_truth = ["c1", "c3"]

    assert precision_at_k(retrieved, ground_truth, k=1) == 1.0
    assert precision_at_k(retrieved, ground_truth, k=2) == 0.5
    assert precision_at_k(retrieved, ground_truth, k=4) == 0.5


def test_mrr_at_k():
    retrieved = ["c1", "c2", "c3"]
    assert mrr_at_k(retrieved, ["c1"], k=3) == 1.0
    assert mrr_at_k(retrieved, ["c2"], k=3) == 0.5
    assert mrr_at_k(retrieved, ["c3"], k=3) == pytest.approx(1 / 3, rel=1e-3)
    assert mrr_at_k(retrieved, ["c9"], k=3) == 0.0


def test_evaluate_retrieval_batch():
    batch = [
        {"retrieved_ids": ["c1", "c2"], "ground_truth_ids": ["c1"]},
        {"retrieved_ids": ["c3", "c4"], "ground_truth_ids": ["c9"]},
    ]
    res = evaluate_retrieval_batch(batch, k_list=[1, 2])
    assert res["total_queries"] == 2
    assert res["metrics"]["hit@1"] == 0.5
    assert res["metrics"]["hit@2"] == 0.5


# =========================================================================
# 2. Unit Tests for Classification & Verification Metrics
# =========================================================================

def test_compute_classification_metrics():
    y_true = ["SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO", "SUPPORTED"]
    y_pred = ["SUPPORTED", "REFUTED", "SUPPORTED", "SUPPORTED"]

    labels = ["SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO"]
    metrics = compute_classification_metrics(y_true, y_pred, labels=labels)

    assert metrics["total_samples"] == 4
    assert metrics["accuracy"] == 0.75  # 3 out of 4 correct
    assert "SUPPORTED" in metrics["per_class"]
    assert "REFUTED" in metrics["per_class"]
    assert metrics["per_class"]["REFUTED"]["f1"] == 1.0


def test_classification_metrics_empty():
    res = compute_classification_metrics([], [])
    assert res["total_samples"] == 0
    assert res["accuracy"] == 0.0


# =========================================================================
# 3. Dataset Validation Tests
# =========================================================================

def test_benchmark_dataset_integrity():
    """Verify that benchmark dataset file exists, has >= 20 cases, and valid schema."""
    assert DATASET_PATH.exists(), f"Missing dataset file: {DATASET_PATH}"
    dataset = load_dataset(DATASET_PATH)

    assert len(dataset) >= 20, f"Expected at least 20 cases, got {len(dataset)}"
    
    categories = set(c["category"] for c in dataset)
    expected_categories = {
        "grounded_qa",
        "insufficient_evidence",
        "contradiction",
        "fact_check",
        "intent_routing",
    }
    assert expected_categories.issubset(categories), f"Missing categories in dataset: {expected_categories - categories}"

    for case in dataset:
        assert "id" in case
        assert "category" in case
        assert "query" in case
        assert "ground_truth" in case


# =========================================================================
# 4. Evaluation Runner Integration Test
# =========================================================================

@pytest.mark.asyncio
async def test_evaluation_runner_execution():
    """Verify that EvaluationRunner runs asynchronously without errors."""
    dataset = load_dataset(DATASET_PATH)
    runner = EvaluationRunner()
    
    summary = await runner.run_benchmark(dataset)
    assert summary["total_cases"] == len(dataset)
    assert summary["passed_cases"] >= 20
    assert "retrieval_metrics" in summary
    assert "verification_metrics" in summary
    assert "intent_metrics" in summary
