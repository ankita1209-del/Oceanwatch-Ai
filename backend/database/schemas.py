"""Request and response schemas shared by the HAB API routes."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]


class PredictionInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, allow_inf_nan=False)

    latitude: float = Field(ge=-90, le=90, validation_alias="lat")
    longitude: float = Field(ge=-180, le=180, validation_alias="lon")
    target_date: date = Field(validation_alias="date")
    sst_mean: float = Field(ge=-3, le=45)
    sst_anomaly: float
    chl_a_mean: float = Field(ge=0)
    chl_anomaly: float
    turbidity: float = Field(ge=0)
    wind_speed: float = Field(ge=0)
    wind_direction: float = Field(ge=0, le=360)
    current_speed: float | None = Field(default=None, ge=0)
    historical_hab_7d: int = Field(ge=0)


class HABEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_date: date = Field(serialization_alias="date")
    latitude: float = Field(serialization_alias="lat")
    longitude: float = Field(serialization_alias="lon")
    location_name: str | None
    species: str | None
    severity: str | None
    chlorophyll_a: float | None
    sea_surface_temperature: float | None
    sample_water_temperature: float | None
    turbidity: float | None
    wind_speed: float | None
    source: str
    source_record_id: str | None = None
    description: str | None
    risk_score: float | None = None
    created_at: datetime


class PredictionResponse(BaseModel):
    prediction_id: int
    hab_probability: float
    risk_score: float
    risk_level: RiskLevel
    confidence: float | None = None
    model_version: str
    location: dict[str, float]
    created_at: datetime


class AlertCreate(BaseModel):
    prediction_id: int
    message: str | None = Field(default=None, max_length=1000)


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prediction_id: int | None
    alert_level: RiskLevel
    message: str
    latitude: float
    longitude: float
    risk_score: float | None
    hab_probability: float | None
    created_at: datetime
    acknowledged: bool
