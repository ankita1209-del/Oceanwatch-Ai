# Notebooks

Jupyter notebooks for exploration, feature engineering, and model experiments.

> Run: `jupyter notebook` from the repo root (with venv activated).

## Notebook Order

| File | Purpose | Team Member |
|------|---------|-------------|
| `01_data_exploration.ipynb` | EDA on NOAA HAB data and environmental features | Data Lead |
| `02_feature_engineering.ipynb` | SST/Chl anomalies, normalisation, train/val/test split | Data Lead |
| `03_baseline_model.ipynb` | XGBoost baseline on tabular env. features | AI/ML Engineer |
| `04_cnn_detection.ipynb` | CNN model training and evaluation on image tiles | AI/ML Engineer |

## Rules

- Run `Kernel > Restart & Run All` before committing any notebook
- Clear outputs before committing if outputs are very large (`Cell > All Output > Clear`)
- Keep notebooks focused — one topic per notebook
- Export final results to `models/evaluation/` as JSON metrics files
