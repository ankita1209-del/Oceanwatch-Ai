import pandas as pd
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import joblib
import xgboost as xgb


def train_models(processed_csv='data/processed/merged_sample_scaled.csv'):
    df = pd.read_csv(processed_csv)
    features = ['chlorophyll','sst','lat','lon','doy']
    target = 'hab_label'
    X = df[features]
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    results = {}

    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    ypred = rf.predict(X_test)
    yprob = rf.predict_proba(X_test)[:,1]
    results['rf'] = {
        'accuracy': accuracy_score(y_test, ypred),
        'precision': precision_score(y_test, ypred, zero_division=0),
        'recall': recall_score(y_test, ypred, zero_division=0),
        'f1': f1_score(y_test, ypred, zero_division=0),
        'roc_auc': roc_auc_score(y_test, yprob) if len(set(y_test))>1 else None,
        'confusion_matrix': confusion_matrix(y_test, ypred).tolist()
    }
    joblib.dump(rf, 'models/rf_hab.joblib')

    try:
        xg = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
        xg.fit(X_train, y_train)
        ypred_x = xg.predict(X_test)
        yprob_x = xg.predict_proba(X_test)[:,1]
        results['xgboost'] = {
            'accuracy': accuracy_score(y_test, ypred_x),
            'precision': precision_score(y_test, ypred_x, zero_division=0),
            'recall': recall_score(y_test, ypred_x, zero_division=0),
            'f1': f1_score(y_test, ypred_x, zero_division=0),
            'roc_auc': roc_auc_score(y_test, yprob_x) if len(set(y_test))>1 else None,
            'confusion_matrix': confusion_matrix(y_test, ypred_x).tolist()
        }
        joblib.dump(xg, 'models/xg_hab.joblib')
    except Exception as e:
        results['xgboost'] = {'error': str(e)}

    # Save results
    pd.DataFrame(results).to_json('results/hab_model_results.json', orient='columns')
    return results


if __name__ == '__main__':
    res = train_models()
    print('Training complete. Results:', res)
