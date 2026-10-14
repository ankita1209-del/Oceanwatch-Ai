"""Model B prediction endpoint — inference always runs; DB persistence is optional."""

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
    BaselineUnavailableError,
    load_baselines,
    make_model_features,
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

    # ── Load trained model ────────────────────────────────────────────────────
    try:
        model = load_prediction_model(settings.PREDICTION_MODEL_PATH)
    except Exception as exc:
        logger.exception("Unable to load HAB prediction model")
        raise HTTPException(status_code=503, detail={
            "error": "Prediction model unavailable.",
            "detail": str(exc),
        }) from exc

    if model is None:
        raise HTTPException(status_code=503, detail={
            "error": "No trained HAB prediction model found.",
            "detail": (
                f"Expected at: {settings.PREDICTION_MODEL_PATH}. "
                "Run train.bat to train the model first."
            ),
        })

    # ── Run inference ─────────────────────────────────────────────────────────
    try:
        metadata_path = Path(settings.MODEL_METADATA_PATH)
        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"Model metadata missing: {settings.MODEL_METADATA_PATH}"
            )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        feature_names = metadata.get("features")
        model_name = metadata.get("model_name", "XGBoost HAB Model")
        model_version = metadata.get("version", "unknown")

        if not isinstance(feature_names, list) or not feature_names:
            raise ValueError("Model metadata must provide an ordered list of features")

        features = make_model_features(data, feature_names)
        probability = infer_prediction(
            np.asarray(features, dtype=float), feature_names
        )["probability"]
        baselines = load_baselines(settings.ANOMALY_BASELINE_PATH)
        risk_input = make_risk_input(data, baselines, probability)
        risk = compute_risk_score(risk_input)

    except FileNotFoundError as exc:
        logger.warning("Prediction resource missing: %s", exc)
        raise HTTPException(status_code=503, detail={
            "error": "Required resource file not found.",
            "detail": str(exc),
        }) from exc
    except BaselineUnavailableError as exc:
        logger.warning("Baseline unavailable: %s", exc)
        raise HTTPException(status_code=503, detail={
            "error": "Calibrated baselines unavailable.",
            "detail": str(exc),
        }) from exc
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Prediction config/input error: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("HAB model inference failed")
        raise HTTPException(status_code=503, detail={
            "error": "Model inference failed.",
            "detail": str(exc),
        }) from exc

    # ── Persist to DB (fully optional — never blocks the inference response) ──
    prediction_id = 0
    created_at = datetime.now(timezone.utc)

    if session is not None:
        try:
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
                historical_hab_risk=risk.components.get("hist_score"),
                model_name=model_name,
                location=None,          # geometry only stored on PostgreSQL
                created_at=created_at,
            )
            session.add(prediction)
            await session.commit()
            await session.refresh(prediction)
            prediction_id = prediction.id
            created_at = prediction.created_at

            if risk.score >= settings.ALERT_THRESHOLD:
                try:
                    await create_alert(
                        session, AlertCreate(prediction_id=prediction.id)
                    )
                except Exception:
                    logger.warning(
                        "Prediction saved but alert creation failed"
                    )

        except Exception as exc:
            logger.warning(
                "DB persist skipped (%s: %s); returning inference result anyway.",
                type(exc).__name__, exc,
            )
            try:
                await session.rollback()
            except Exception:
                pass

    return PredictionResponse(
        prediction_id=prediction_id,
        hab_probability=probability,
        risk_score=risk.score,
        risk_level=risk.level,
        confidence=None,
        model_version=model_version,
        location={"latitude": data.latitude, "longitude": data.longitude},
        created_at=created_at,
    )
