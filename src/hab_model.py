"""Train Model B only from a labeled, provenance-documented feature table.

Example:
    python src/hab_model.py data/processed/features.csv \
        --training-context "documented environmental/HAB dataset join"
"""

import argparse
import json
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

FEATURES = [
    "sst_mean",
    "sst_anomaly",
    "chl_a_mean",
    "chl_anomaly",
    "turbidity",
    "wind_speed",
    "wind_direction",
    "current_speed",
    "historical_hab_7d",
    "latitude",
    "longitude",
]
TARGET = "hab_label"


def train_model(
    feature_csv: Path,
    training_context: str,
    model_path: Path,
    metadata_path: Path,
) -> dict:
    frame = pd.read_csv(feature_csv, low_memory=False)
    required = set(FEATURES + [TARGET, "source", "date"])
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Training data must contain verified HAB labels and every model feature; "
            f"missing: {', '.join(sorted(missing))}"
        )
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    frame = frame.dropna(subset=FEATURES + [TARGET, "source", "date"]).copy()
    sources = sorted(frame["source"].astype(str).unique().tolist())
    if not sources:
        raise ValueError("Training rows must retain dataset source attribution")
    training_period = {
        "start": frame["date"].min().date().isoformat(),
        "end": frame["date"].max().date().isoformat(),
    }
    labels = pd.to_numeric(frame[TARGET], errors="coerce")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise ValueError("hab_label must contain only observed binary labels 0 and 1")
    if labels.nunique() != 2:
        raise ValueError("Training requires verified records from both HAB classes")
    if len(frame) < 10:
        raise ValueError("At least 10 complete labeled observations are required for a holdout split")
    if labels.value_counts().min() < 2:
        raise ValueError("At least two verified observations per HAB class are required for evaluation")

    x_train, x_test, y_train, y_test = train_test_split(
        frame[FEATURES],
        labels.astype("int8"),
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)[:, 1]
    metrics = {
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "test_rows": int(len(y_test)),
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    metadata = {
        "model_name": "XGBoost HAB Future-Risk Prediction",
        "version": date.today().isoformat(),
        "training_sources": sources,
        "training_context": training_context,
        "training_period": training_period,
        "features": FEATURES,
        "target": TARGET,
        "metrics": metrics,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature_csv", type=Path)
    parser.add_argument("--training-context", required=True, help="Research notes about the joined datasets")
    parser.add_argument("--model", type=Path, default=Path("models/prediction/xgboost_model.pkl"))
    parser.add_argument("--metadata", type=Path, default=Path("models/prediction/model_metadata.json"))
    args = parser.parse_args()
    result = train_model(
        args.feature_csv,
        args.training_context,
        args.model,
        args.metadata,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
