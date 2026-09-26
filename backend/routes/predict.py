"""Model B prediction endpoint; real artifacts and calibrated baselines required."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.connection import get_optional_db
from backend.database.models import Prediction
from backend.database.schemas import AlertCreate, PredictionInput, PredictionResponse
from backend.services.alert_service import create_alert
from backend.services.feature_service import (
    load_baselines,
    make_model_features,
    BaselineUnavailableError,
    make_risk_input,
)
from backend.services.ml_inference import infer_prediction, load_prediction_model
from backend.services.risk_engine import compute_risk_score

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_hab(
    data: PredictionInput,
    session: AsyncSession | None = Depends(get_optional_db),
):
    settings = get_settings()
    try:
        model = load_prediction_model(settings.PREDICTION_MODEL_PATH)
    except Exception as exc:
        logger.exception("Unable to load HAB prediction model")
        raise HTTPException(
            status_code=503,
            detail={"error": "Prediction model is unavailable.", "detail": "The configured model artifact could not be loaded."},
        ) from exc
    if model is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Prediction model is not available.",
                "detail": "A trained HAB prediction model is required for real predictions.",
            },
        )
    if session is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "Database is not configured.", "detail": "Set DATABASE_URL and start PostgreSQL with PostGIS enabled."},
        )

    try:
        metadata_path = Path(settings.MODEL_METADATA_PATH)
        if not metadata_path.is_file():
            raise FileNotFoundError("Model metadata is missing; expected feature order is not known")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        feature_names = metadata.get("features")
        model_name = metadata.get("model_name")
        model_version = metadata.get("version")
        if not isinstance(feature_names, list) or not feature_names or not model_name:
            raise ValueError("Model metadata must provide model_name and ordered features")
        trained_features = getattr(model, "feature_names_in_", None)
        if trained_features is not None and list(trained_features) != feature_names:
            raise ValueError("Model metadata feature order does not match the trained model")
        trained_feature_count = getattr(model, "n_features_in_", None)
        if trained_feature_count is not None and trained_feature_count != len(feature_names):
            raise ValueError("Model metadata feature count does not match the trained model")
        features = make_model_features(data, feature_names)
        probability = infer_prediction(
            np.asarray(features, dtype=float), feature_names
        )["probability"]
        baselines = load_baselines(settings.ANOMALY_BASELINE_PATH)
        risk_input = make_risk_input(data, baselines, probability)
        risk = compute_risk_score(risk_input)
    except FileNotFoundError as exc:
        logger.info("Prediction cannot run: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "Prediction resources are unavailable.", "detail": str(exc)},
        ) from exc
    except BaselineUnavailableError as exc:
        logger.info("Prediction calibration unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "Calibrated risk baselines are unavailable.", "detail": str(exc)},
        ) from exc
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Invalid prediction configuration or input: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("HAB model inference failed")
        raise HTTPException(
            status_code=503,
            detail={"error": "HAB model inference is unavailable.", "detail": "The configured model could not process these features."},
        ) from exc

    prediction = Prediction(
        prediction_date=data.target_date,
        latitude=data.latitude,
        longitude=data.longitude,
        hab_probability=probability,
        risk_score=risk.score,
        risk_level=risk.level,
        chlorophyll_a=data.chl_a_mean,
        chlorophyll_anomaly=data.chl_anomaly,
        sst=data.sst_mean,
        sst_anomaly=data.sst_anomaly,
        turbidity=data.turbidity,
        wind_speed=data.wind_speed,
        wind_direction=data.wind_direction,
        ocean_current=data.current_speed,
        historical_hab_risk=risk.components["hist_score"],
        model_name=model_name,
        created_at=datetime.now(timezone.utc),
    )
    session.add(prediction)
    try:
        await session.commit()
        await session.refresh(prediction)
    except Exception as exc:
        await session.rollback()
        logger.exception("Unable to persist HAB prediction")
        raise HTTPException(status_code=503, detail="Prediction could not be saved to the database") from exc

    if risk.score >= settings.ALERT_THRESHOLD:
        try:
            await create_alert(session, AlertCreate(prediction_id=prediction.id))
        except Exception:
            logger.exception("Prediction was saved, but its dashboard alert could not be created")

    return PredictionResponse(
        prediction_id=prediction.id,
        hab_probability=probability,
        risk_score=risk.score,
        risk_level=risk.level,
        confidence=None,
        model_version=model_version or model_name,
        location={"latitude": data.latitude, "longitude": data.longitude},
        created_at=prediction.created_at,
    )
