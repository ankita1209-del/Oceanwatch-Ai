"""
Model Evaluation Stubs
=======================
Placeholder tests for model quality metrics.
Fill in once real trained models are available.

Run: pytest tests/test_models.py -v
"""

import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Minimum metric thresholds (adjust based on validation data)
# ---------------------------------------------------------------------------
MIN_F1 = 0.60
MIN_ROC_AUC = 0.75
MIN_RECALL = 0.65  # recall is critical for rare-event detection


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """Compute all required evaluation metrics."""
    from sklearn.metrics import (
        precision_score, recall_score, f1_score,
        roc_auc_score, confusion_matrix,
    )
    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_prob),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


@pytest.mark.skip(reason="Replace with real model predictions before running")
def test_prediction_model_metrics():
    """
    TODO (Member 2 — AI/ML Engineer):
    Load saved model, run on held-out test set, assert metric thresholds.
    """
    # Stub — replace with real test-set inference
    y_true = np.array([0, 1, 1, 0, 1, 0, 0, 1])
    y_pred = np.array([0, 1, 1, 0, 1, 0, 1, 1])
    y_prob = np.array([0.1, 0.9, 0.85, 0.2, 0.95, 0.15, 0.6, 0.88])

    metrics = compute_metrics(y_true, y_pred, y_prob)

    assert metrics["f1"]      >= MIN_F1,      f"F1 {metrics['f1']:.3f} < {MIN_F1}"
    assert metrics["roc_auc"] >= MIN_ROC_AUC, f"AUC {metrics['roc_auc']:.3f} < {MIN_ROC_AUC}"
    assert metrics["recall"]  >= MIN_RECALL,  f"Recall {metrics['recall']:.3f} < {MIN_RECALL}"


@pytest.mark.skip(reason="Replace with real model predictions before running")
def test_detection_model_metrics():
    """
    TODO (Member 2 — AI/ML Engineer):
    Load CNN detection model, run on held-out image test set, assert metrics.
    Add IoU/Dice here if using U-Net segmentation.
    """
    pass
