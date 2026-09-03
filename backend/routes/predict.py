"""
Route: POST /api/predict

Accepts environmental feature inputs and returns HAB probability
and risk level from Model B (XGBoost prediction model).
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()


class PredictionInput(BaseModel):
    """7-day environmental feature vector for Model B."""

    lat: float = Field(..., description="Latitude (decimal degrees)")
    lon: float = Field(..., description="Longitude (decimal degrees)")
    date: str = Field(..., description="Prediction target date (YYYY-MM-DD)")

    # Environmental features (7-day rolling means unless noted)
    sst_mean: float = Field(..., description="Mean sea surface temperature (°C)")
    sst_anomaly: float = Field(..., description="SST anomaly vs. climatology (°C)")
    chl_a_mean: float = Field(..., description="Mean chlorophyll-a (mg/m³)")
    chl_anomaly: float = Field(..., description="Chl-a anomaly vs. climatology")
    turbidity: float = Field(..., description="Water turbidity (NTU)")
    wind_speed: float = Field(..., description="Mean wind speed (m/s)")
    wind_direction: float = Field(..., description="Mean wind direction (degrees)")
    current_speed: Optional[float] = Field(None, description="Ocean current speed (m/s)")
    historical_hab_7d: int = Field(
        ..., description="Number of HAB occurrences in past 7 days at this location"
    )


class PredictionOutput(BaseModel):
    hab_probability: float = Field(..., description="HAB probability score (0.0–1.0)")
    risk_score: float = Field(..., description="Composite risk score (0–100)")
    risk_level: str = Field(..., description="LOW | MODERATE | HIGH | CRITICAL")
    confidence: float = Field(..., description="Model confidence (0.0–1.0)")
    model_version: str


@router.post("/predict", response_model=PredictionOutput)
async def predict_hab(data: PredictionInput):
    """
    Run HAB risk prediction for a given location and environmental conditions.

    **Model B** — XGBoost-based prediction on 7-day feature windows.

    TODO (Member 2 — AI/ML Engineer):
    - Load the trained model from `models/prediction/`
    - Run inference on the incoming feature vector
    - Replace the stub response below with real model output
    """
    # -----------------------------------------------------------------------
    # STUB — replace with real model inference
    # -----------------------------------------------------------------------
    stub_prob = 0.42
    stub_risk_score = (
        0.40 * stub_prob * 100
        + 0.20 * min(abs(data.chl_anomaly) * 10, 100)
        + 0.15 * min(abs(data.sst_anomaly) * 10, 100)
        + 0.15 * min(data.historical_hab_7d * 10, 100)
        + 0.10 * 20  # placeholder env anomaly
    )
    stub_risk_score = min(round(stub_risk_score, 2), 100.0)

    if stub_risk_score <= 30:
        level = "LOW"
    elif stub_risk_score <= 60:
        level = "MODERATE"
    elif stub_risk_score <= 80:
        level = "HIGH"
    else:
        level = "CRITICAL"

    return PredictionOutput(
        hab_probability=stub_prob,
        risk_score=stub_risk_score,
        risk_level=level,
        confidence=0.78,
        model_version="stub-0.1",
    )
