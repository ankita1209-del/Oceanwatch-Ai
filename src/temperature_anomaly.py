import pandas as pd
import os


def compute_climatology(processed_csv='data/processed/merged_sample.csv'):
    df = pd.read_csv(processed_csv, parse_dates=['time'])
    df['doy'] = pd.to_datetime(df['time']).dt.dayofyear
    clim = df.groupby('doy')['sst'].mean().rename('sst_climatology')
    clim.to_csv('data/metadata/sst_climatology_by_doy.csv')
    return clim


def compute_anomaly_for_date(date, processed_csv='data/processed/merged_sample.csv'):
    if not os.path.exists('data/metadata/sst_climatology_by_doy.csv'):
        compute_climatology(processed_csv)
    clim = pd.read_csv('data/metadata/sst_climatology_by_doy.csv', index_col=0)
    df = pd.read_csv(processed_csv, parse_dates=['time'])
    df['doy'] = df['time'].apply(lambda x: pd.to_datetime(x).dayofyear)
    target = df[df['time'].dt.date == pd.to_datetime(date).date()].copy()
    if target.empty:
        print('No records for the requested date in processed data.')
        return None
    target = target.merge(clim, left_on='doy', right_index=True, how='left')
    target['sst_anomaly'] = target['sst'] - target['sst_climatology']
    def risk(a):
        if a >= 1.0:
            return 'high'
        if a >= 0.5:
            return 'moderate'
        return 'low'
    target['anomaly_risk'] = target['sst_anomaly'].apply(risk)
    out = 'results/temperature_anomaly_{}.csv'.format(pd.to_datetime(date).date())
    target.to_csv(out, index=False)
    return out


if __name__ == '__main__':
    compute_climatology()
    print('Climatology computed and saved.')
