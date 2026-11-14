"""Model loading and inference for trained HAB model artifacts."""

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy-loaded model references.
_detection_model = None
_detection_model_path: str | None = None
_detection_transform = None

_prediction_model = None
_prediction_model_path: str | None = None


def load_detection_model(path: str | Path):
    """
    Load the PyTorch ResNet-18 image model.

    The architecture must match the training architecture:
        ResNet18
        fc = Sequential(
            Dropout(0.3),
            Linear(512, 2)
        )
    """

    global _detection_model
    global _detection_model_path
    global _detection_transform

    model_path = str(Path(path).resolve())

    if not Path(model_path).is_file():
        logger.warning(
            "Satellite detection model does not exist: %s",
            model_path,
        )
        return None

    if (
        _detection_model is not None
        and _detection_model_path == model_path
    ):
        return _detection_model

    try:
        import torch
        from torch import nn
        from torchvision import models, transforms

        logger.info(
            "Loading ResNet-18 satellite model from %s",
            model_path,
        )

        model = models.resnet18(weights=None)

        model.fc = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(512, 2),
        )

        try:
            checkpoint = torch.load(
                model_path,
                map_location="cpu",
                weights_only=True,
            )
        except TypeError:
            # Compatibility with older PyTorch versions.
            checkpoint = torch.load(
                model_path,
                map_location="cpu",
            )

        if isinstance(checkpoint, dict):
            if "state_dict" in checkpoint:
                checkpoint = checkpoint["state_dict"]
            elif "model_state_dict" in checkpoint:
                checkpoint = checkpoint["model_state_dict"]

        if not isinstance(checkpoint, dict):
            raise ValueError(
                "The detection checkpoint does not contain a valid state dictionary."
            )

        model.load_state_dict(checkpoint, strict=True)
        model.eval()

        # Match the preprocessing used during model training.
        image_transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )

        _detection_model = model
        _detection_model_path = model_path
        _detection_transform = image_transform

        logger.info("ResNet-18 satellite model loaded successfully.")

        return _detection_model

    except Exception:
        _detection_model = None
        _detection_model_path = None
        _detection_transform = None

        logger.exception(
            "Could not load the satellite detection model."
        )
        raise


def infer_detection(
    image_path: str | Path,
    model_path: str | Path,
) -> dict[str, Any]:
    """
    Run experimental ResNet-18 inference on one satellite image.

    Returns the softmax score for class index 1.

    IMPORTANT:
    The training labels were generated from CIcyano image-index
    values. This score is not a verified HAB probability.
    """

    import torch
    from PIL import Image

    model = load_detection_model(model_path)

    if model is None:
        raise RuntimeError(
            "The satellite detection model is unavailable."
        )

    if _detection_transform is None:
        raise RuntimeError(
            "The satellite image preprocessing pipeline is unavailable."
        )

    image_path = Path(image_path)

    if not image_path.is_file():
        raise FileNotFoundError(
            f"Satellite image not found: {image_path}"
        )

    try:
        # Training used PIL Image.open(...).convert("RGB").
        with Image.open(image_path) as source_image:
            image = source_image.convert("RGB")

            image_tensor = _detection_transform(image)

        image_tensor = image_tensor.unsqueeze(0)

        model.eval()

        with torch.inference_mode():
            logits = model(image_tensor)
            probabilities = torch.softmax(logits, dim=1)

        if probabilities.ndim != 2 or probabilities.shape[1] != 2:
            raise ValueError(
                "The detection model must return two class scores."
            )

        score = float(probabilities[0, 1].item())

        if not np.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError(
                "The detection model returned an invalid score."
            )

        predicted_class = int(
            torch.argmax(probabilities, dim=1).item()
        )

        return {
            "score": score,
            "predicted_class": predicted_class,
        }

    except Exception:
        logger.exception(
            "Experimental satellite image inference failed."
        )
        raise


def load_prediction_model(path: str):
    """Load the XGBoost/scikit-learn-compatible prediction model."""

    global _prediction_model
    global _prediction_model_path

    model_path = str(Path(path).resolve())

    if (
        _prediction_model is None
        or _prediction_model_path != model_path
    ):
        if not Path(model_path).is_file():
            logger.warning(
                "Prediction model does not exist: %s",
                model_path,
            )
            return None

        logger.info(
            "Loading HAB prediction model from %s",
            model_path,
        )

        model = joblib.load(model_path)

        if not callable(getattr(model, "predict_proba", None)):
            raise ValueError(
                "Prediction model must implement predict_proba."
            )

        _prediction_model = model
        _prediction_model_path = model_path

    return _prediction_model


def infer_prediction(
    feature_vector: np.ndarray,
    feature_names: list[str] | None = None,
) -> dict[str, float]:
    """Run Model B and return its positive-class probability."""

    if _prediction_model is None:
        raise RuntimeError(
            "Prediction model has not been loaded."
        )

    row = np.asarray(feature_vector).reshape(1, -1)

    model_input = (
        pd.DataFrame(row, columns=feature_names)
        if feature_names
        else row
    )

    probabilities = _prediction_model.predict_proba(model_input)

    if probabilities.shape[1] < 2:
        raise ValueError(
            "Prediction model must provide probabilities for both classes."
        )

    probability = float(probabilities[0, 1])

    if not 0.0 <= probability <= 1.0:
        raise ValueError(
            "Prediction model returned a probability outside [0, 1]."
        )

    return {
        "probability": probability,
    }