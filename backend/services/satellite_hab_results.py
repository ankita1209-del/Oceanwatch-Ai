"""Experimental ResNet inference for CIcyano satellite images.

The model score is NOT a validated HAB probability.
"""

import json
import logging
from pathlib import Path
from typing import Any

from backend.services.ml_inference import infer_detection

logger = logging.getLogger(__name__)


def _not_run(
    reason: str,
    probability_reason: str | None = None,
) -> dict[str, Any]:
    """Return a consistent response when inference is not performed."""

    return {
        "hab_probability": None,
        "experimental_model_score": None,
        "risk_score": None,
        "risk_level": None,
        "model": {
            "name": None,
            "version": None,
            "status": "not_run",
            "inference_ran": False,
            "reason": reason,
        },
        "reasons": {
            "experimental_model_score": reason,
            "hab_probability": probability_reason or (
                "The model is not validated or calibrated to estimate "
                "biological HAB probability."
            ),
            "risk_score": (
                "Risk scoring requires environmental observations "
                "that are not supplied by this image alone."
            ),
            "risk_level": (
                "A risk level cannot be calculated without a valid risk score."
            ),
        },
    }


def build_satellite_hab_results(
    image_path: str | Path,
    product_metadata: dict[str, Any],
    analysis_result: dict[str, Any],
    model_path: str,
    model_metadata_path: str,
) -> dict[str, Any]:
    """Run experimental image classification only for CIcyano products."""

    if product_metadata.get("analysis_capability") != "ci_cyano_screening":
        return _not_run(
            "This product is not a CIcyano image. The image is available "
            "for preview only; experimental CIcyano inference was not run."
        )

    quality = analysis_result.get("quality")
    quality = quality if isinstance(quality, dict) else {}

    coverage_category = quality.get("coverage_category")

    if coverage_category in {
        "NO_VALID_PIXELS",
        "INSUFFICIENT_COVERAGE",
    }:
        reason = (
            "Inference was not run because the image has insufficient "
            "valid CIcyano coverage."
        )
        return _not_run(
            reason,
            probability_reason=reason,
        )

    image_file = Path(image_path)
    model_file = Path(model_path)
    metadata_file = Path(model_metadata_path)

    if not image_file.is_file():
        return _not_run("The uploaded satellite image file could not be found.")

    if not model_file.is_file():
        return _not_run("The CIcyano detection model is not installed.")

    model_metadata: dict[str, Any] = {}

    try:
        if metadata_file.is_file():
            with metadata_file.open("r", encoding="utf-8") as file:
                loaded_metadata = json.load(file)

            if isinstance(loaded_metadata, dict):
                model_metadata = loaded_metadata

    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read detection model metadata: %s", exc)

    try:
        inference = infer_detection(
            image_file,
            str(model_file),
        )

        score = float(inference["score"])
        predicted_class = int(inference["predicted_class"])

        if not 0.0 <= score <= 1.0:
            raise ValueError("The model returned a score outside the 0–1 range.")

        if predicted_class not in (0, 1):
            raise ValueError("The model returned an unknown class.")

    except Exception:
        logger.exception("Experimental CIcyano model inference failed.")
        return _not_run(
            "Experimental CIcyano model inference could not be completed."
        )

    class_label = (
        "higher_ci_cyano_intensity"
        if predicted_class == 1
        else "lower_ci_cyano_intensity"
    )

    model_name = model_metadata.get("model_name")
    if not isinstance(model_name, str) or not model_name.strip():
        model_name = None

    model_version = model_metadata.get("version")
    if not isinstance(model_version, str) or not model_version.strip():
        model_version = None

    caveat = (
        "This is an experimental classifier score for classes generated "
        "using a CIcyano image-intensity threshold. It is not a verified "
        "HAB detection, biological HAB probability, or environmental risk score. "
        "The current training evaluation has limitations, including test-set "
        "reuse during model selection."
    )

    return {
        "hab_probability": None,
        "experimental_model_score": score,
        "risk_score": None,
        "risk_level": None,
        "model": {
            "name": model_name,
            "version": model_version,
            "status": "experimental",
            "inference_ran": True,
            "predicted_class": predicted_class,
            "class_label": class_label,
            "score_label": "Experimental CIcyano classifier score",
            "reason": caveat,
            "label_method": model_metadata.get("label_method"),
        },
        "reasons": {
            "experimental_model_score": (
                "Experimental model inference completed. "
                "Interpret this score only as a classifier output."
            ),
            "hab_probability": (
                "Not calculated: this model has not been validated or "
                "calibrated to estimate biological HAB probability."
            ),
            "risk_score": (
                "Not calculated: environmental observations are required."
            ),
            "risk_level": (
                "Not calculated: a valid environmental risk score is required."
            ),
        },
    }