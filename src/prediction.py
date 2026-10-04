import pandas as pd
import joblib
import os
from src.temperature_anomaly import compute_anomaly_for_date


def predict_from_row(row):
    # row: dict with keys lat, lon, time, chlorophyll, sst
    scaler_path = 'data/metadata/scaler.joblib'
    if not os.path.exists(scaler_path):
        raise FileNotFoundError('Scaler not found; run preprocessing first')
    scaler = joblib.load(scaler_path)
    features = ['chlorophyll','sst','lat','lon','doy']
    df = pd.DataFrame([row])
    df['doy'] = pd.to_datetime(df['time']).dt.dayofyear
    X = df[features]
    Xs = scaler.transform(X)
    rf = joblib.load('models/rf_hab.joblib')
    prob = rf.predict_proba(Xs)[:,1][0]
    pred = rf.predict(Xs)[0]
    # temperature anomaly
    anomaly_file = compute_anomaly_for_date(row['time'])
    return {
        'Location': f"{row['lat']}, {row['lon']}",
        'Date': row['time'],
        'SST': row['sst'],
        'HAB_Probability': float(prob),
        'HAB_Risk': 'high' if pred==1 else 'low',
        'Anomaly_File': anomaly_file
    }


if __name__ == '__main__':
    example = {'lat': 26.0, 'lon': -86.0, 'time': pd.Timestamp.today().isoformat(), 'chlorophyll': 3.0, 'sst': 28.5}
    out = predict_from_row(example)
    print(out)
