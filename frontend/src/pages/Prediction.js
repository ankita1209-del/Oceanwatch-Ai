import React, { useState } from "react";
import { apiFailureMessage, predictHAB } from "../services/api";
import "./Prediction.css";

const initialValues = {
  latitude: "27.65",
  longitude: "-83.15",
  target_date: new Date().toLocaleDateString("en-CA"),
  sst_mean: "28",
  sst_anomaly: "1.2",
  chl_a_mean: "5",
  chl_anomaly: "2",
  turbidity: "4",
  wind_speed: "5",
  wind_direction: "180",
  current_speed: "0.3",
  historical_hab_7d: "2",
};

const fields = [
  { name: "latitude", label: "Latitude", min: -90, max: 90, step: "any" },
  { name: "longitude", label: "Longitude", min: -180, max: 180, step: "any" },
  { name: "sst_mean", label: "Sea surface temperature (°C)", min: -3, max: 45, step: "any" },
  { name: "sst_anomaly", label: "Sea surface temperature anomaly (°C)", step: "any" },
  { name: "chl_a_mean", label: "Chlorophyll-a mean", min: 0, step: "any" },
  { name: "chl_anomaly", label: "Chlorophyll-a anomaly", step: "any" },
  { name: "turbidity", label: "Turbidity", min: 0, step: "any" },
  { name: "wind_speed", label: "Wind speed", min: 0, step: "any" },
  { name: "wind_direction", label: "Wind direction (0–360°)", min: 0, max: 360, step: "any" },
  { name: "current_speed", label: "Current speed (optional)", min: 0, step: "any", optional: true },
  { name: "historical_hab_7d", label: "Historical HAB events (last 7 days)", min: 0, step: 1 },
];

function riskClass(level) {
  return String(level || "unknown").toLowerCase();
}

export default function Prediction() {
  const [values, setValues] = useState(initialValues);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateField(event) {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    const requiredFields = fields.filter((field) => !field.optional);
    for (const field of requiredFields) {
      if (values[field.name] === "" || !Number.isFinite(Number(values[field.name]))) {
        setError(`Please enter a valid value for ${field.label}.`);
        return;
      }
    }

    if (!values.target_date) {
      setError("Please select a target date.");
      return;
    }

    const payload = {
      latitude: Number(values.latitude),
      longitude: Number(values.longitude),
      target_date: values.target_date,
      sst_mean: Number(values.sst_mean),
      sst_anomaly: Number(values.sst_anomaly),
      chl_a_mean: Number(values.chl_a_mean),
      chl_anomaly: Number(values.chl_anomaly),
      turbidity: Number(values.turbidity),
      wind_speed: Number(values.wind_speed),
      wind_direction: Number(values.wind_direction),
      current_speed: values.current_speed === "" ? null : Number(values.current_speed),
      historical_hab_7d: Number(values.historical_hab_7d),
    };

    setLoading(true);
    try {
      const prediction = await predictHAB(payload);
      setResult(prediction);
    } catch (requestError) {
      setError(apiFailureMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="prediction-page">
      <header className="prediction-header">
        <p className="prediction-eyebrow">OCEANWATCH AI / MACHINE LEARNING</p>
        <h1>HAB Prediction</h1>
        <p>
          Estimate harmful algal bloom risk from environmental measurements.
          Enter values for the location and target date, then run the model.
        </p>
      </header>

      <div className="prediction-notice">
        <strong>Research prototype:</strong> Use verified measurements whenever
        possible. Example values are provided for testing and are not live
        satellite observations or an official public-health warning.
      </div>

      <form className="prediction-form" onSubmit={handleSubmit}>
        <div className="prediction-section-heading">
          <h2>Location and date</h2>
          <p>Enter the coordinates and date to evaluate.</p>
        </div>

        <div className="prediction-fields">
          <label className="prediction-field">
            <span>Latitude (−90 to 90)</span>
            <input
              name="latitude"
              type="number"
              min="-90"
              max="90"
              step="any"
              value={values.latitude}
              onChange={updateField}
              required
            />
          </label>
          <label className="prediction-field">
            <span>Longitude (−180 to 180)</span>
            <input
              name="longitude"
              type="number"
              min="-180"
              max="180"
              step="any"
              value={values.longitude}
              onChange={updateField}
              required
            />
          </label>
          <label className="prediction-field">
            <span>Target date</span>
            <input
              name="target_date"
              type="date"
              value={values.target_date}
              onChange={updateField}
              required
            />
          </label>
        </div>

        <div className="prediction-section-heading">
          <h2>Environmental measurements</h2>
          <p>Use measurements in the units expected by your model.</p>
        </div>

        <div className="prediction-fields">
          {fields.filter((field) => !["latitude", "longitude"].includes(field.name)).map((field) => (
            <label className="prediction-field" key={field.name}>
              <span>{field.label}{field.optional ? " — leave blank if unavailable" : ""}</span>
              <input
                name={field.name}
                type="number"
                min={field.min}
                max={field.max}
                step={field.step}
                value={values[field.name]}
                onChange={updateField}
                required={!field.optional}
              />
            </label>
          ))}
        </div>

        {error && (
          <div className="prediction-error" role="alert">
            {error}
          </div>
        )}

        <button className="prediction-submit" type="submit" disabled={loading}>
          {loading ? "Calculating prediction..." : "Run HAB prediction"}
        </button>
      </form>

      {result && (
        <section className="prediction-result" aria-live="polite">
          <p className="prediction-eyebrow">MODEL OUTPUT</p>
          <h2>Prediction result</h2>

          <div className="prediction-result-grid">
            <div className="prediction-result-card">
              <span>HAB probability</span>
              <strong>
                {Number.isFinite(Number(result.hab_probability))
                  ? `${(Number(result.hab_probability) * 100).toFixed(2)}%`
                  : "Not provided"}
              </strong>
            </div>
            <div className="prediction-result-card">
              <span>Risk score</span>
              <strong>
                {Number.isFinite(Number(result.risk_score))
                  ? Number(result.risk_score).toFixed(2)
                  : "Not provided"}
              </strong>
            </div>
            <div className={`prediction-result-card risk-${riskClass(result.risk_level)}`}>
              <span>Risk level</span>
              <strong>{result.risk_level || "Not provided"}</strong>
            </div>
            <div className="prediction-result-card">
              <span>Model version</span>
              <strong>{result.model_version || "Not provided"}</strong>
            </div>
          </div>

          <p className="prediction-result-meta">
            Prediction ID: {result.prediction_id ?? "Not provided"}
            {" · "}
            Confidence: {result.confidence == null ? "Not provided" : result.confidence}
          </p>
          <p className="prediction-result-disclaimer">
            This is a model estimate based on the submitted inputs. It is not a
            confirmed HAB observation, a validated forecast, or an official alert.
          </p>
        </section>
      )}
    </section>
  );
}
