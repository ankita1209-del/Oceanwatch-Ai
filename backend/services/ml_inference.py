"""
ML Inference Service
====================
Loads Model A (HAB Detection CNN) and Model B (HAB Prediction XGBoost)
and exposes simple inference functions for use in API routes.

TODO (Member 2 — AI/ML Engineer):
    - Save trained models to models/detection/ and models/prediction/
    - Implement real load_detection_model() and load_prediction_model()
    - Replace stub inference functions with real forward passes
"""

import os
from typing import Optional
import numpy as np

# Lazy model references — loaded on first call
_detection_model = None
_prediction_model = None


def load_detection_model(path: str):
    """
    Load the CNN detection model (PyTorch).

    TODO: implement with torch.load()
    """
    global _detection_model
    if _detection_model is None:
        if not os.path.exists(path):
            print(f"[WARN] Detection model not found at {path} — using stub.")
            return None
        # import torch
        # _detection_model = torch.load(path, map_location="cpu")
        # _detection_model.eval()
    return _detection_model


def load_prediction_model(path: str):
    """
    Load the XGBoost prediction model.

    TODO: implement with xgboost.Booster().load_model()
    """
    global _prediction_model
    if _prediction_model is None:
        if not os.path.exists(path):
            print(f"[WARN] Prediction model not found at {path} — using stub.")
            return None
        # import xgboost as xgb
        # _prediction_model = xgb.Booster()
        # _prediction_model.load_model(path)
    return _prediction_model


def infer_detection(image_array: np.ndarray) -> float:
    """
    Run Model A: image → HAB probability.

    Args:
        image_array: numpy array of shape (H, W, C)

    Returns:
        HAB probability (0.0–1.0)

    TODO: replace stub with real CNN forward pass
    """
    # Stub: return a fixed probability
    return 0.55


def infer_prediction(feature_vector: np.ndarray) -> dict:
    """
    Run Model B: env. feature vector → HAB probability + risk level.

    Args:
        feature_vector: numpy array of shape (n_features,)

    Returns:
        dict with 'probability' and 'confidence'

    TODO: replace stub with real XGBoost inference
    """
    # Stub: return fixed values
    return {"probability": 0.42, "confidence": 0.78}
