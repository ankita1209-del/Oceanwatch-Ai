"""Model loading and inference for trained HAB model artifacts."""

import logging
import os
import numpy as np
import joblib
import pandas as pd

# Lazy model references — loaded on first call
_detection_model = None
_prediction_model = None
_prediction_model_path = None
logger = logging.getLogger(__name__)


def load_detection_model(path: str):
    """Detection inference stays unavailable until a trained artifact exists."""
    global _detection_model
    if _detection_model is None:
        if not os.path.exists(path):
            return None
    return _detection_model


def load_prediction_model(path: str):
    """Load a trained scikit-learn-compatible model saved with joblib."""
    global _prediction_model, _prediction_model_path
    if _prediction_model is None or _prediction_model_path != path:
        if not os.path.exists(path):
            return None
        logger.info("Loading HAB prediction model from %s", path)
        _prediction_model = joblib.load(path)
        if not callable(getattr(_prediction_model, "predict_proba", None)):
            _prediction_model = None
            _prediction_model_path = None
            raise ValueError("Prediction model must implement predict_proba")
        _prediction_model_path = path
    return _prediction_model


def infer_detection(image_array: np.ndarray) -> float:
    """Run Model A; fail clearly until a trained image model is available."""
    if _detection_model is None:
        raise RuntimeError("A trained HAB image-detection model is not available")
    raise NotImplementedError("The configured image model has no supported inference adapter")


def infer_prediction(feature_vector: np.ndarray, feature_names: list[str] | None = None) -> dict:
    """Run Model B and return its positive-class probability."""
    if _prediction_model is None:
        raise RuntimeError("Prediction model has not been loaded")
    row = np.asarray(feature_vector).reshape(1, -1)
    model_input = pd.DataFrame(row, columns=feature_names) if feature_names else row
    probabilities = _prediction_model.predict_proba(model_input)
    if probabilities.shape[1] < 2:
        raise ValueError("Prediction model must provide probabilities for both classes")
    probability = float(probabilities[0, 1])
    if not 0.0 <= probability <= 1.0:
        raise ValueError("Prediction model returned a probability outside [0, 1]")
    return {"probability": probability}
