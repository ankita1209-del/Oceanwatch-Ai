# Model Artifacts

This directory stores trained model weights and evaluation artifacts.

> ⚠️ Model weight files (`.pt`, `.json`, `.pkl`, `.h5`) are **git-ignored**.
> Use DVC, HuggingFace Hub, or your team's shared storage to share large files.

## Directory Layout

```
models/
├── detection/           ← Model A (CNN / U-Net) for HAB image detection
│   ├── model.pt         ← PyTorch weights (git-ignored)
│   ├── config.json      ← Architecture config
│   └── README.md
│
├── prediction/          ← Model B (XGBoost → LSTM) for future risk prediction
│   ├── model.json       ← XGBoost model file (git-ignored)
│   ├── feature_cols.txt ← Ordered feature column names
│   └── README.md
│
└── evaluation/          ← Metrics, confusion matrices, ROC curves
    ├── metrics_detection.json
    ├── metrics_prediction.json
    └── plots/
```

## Model A — Detection (CNN)

| Attribute | Value |
|-----------|-------|
| Input | Multispectral satellite image tile |
| Output | HAB probability (0–1) |
| Architecture | ResNet-based CNN; upgrade to U-Net if masks available |
| Framework | PyTorch |
| Save format | `torch.save(model.state_dict(), 'model.pt')` |

## Model B — Prediction (XGBoost)

| Attribute | Value |
|-----------|-------|
| Input | 7-day env. feature vector (SST, Chl-a, turbidity, wind, current, hist. HAB) |
| Output | HAB probability (0–1) + risk level |
| Architecture | XGBoost → graduate to LSTM/GRU if needed |
| Framework | XGBoost / PyTorch |
| Save format | `booster.save_model('model.json')` |

## Required Evaluation Metrics

- **Always report**: Precision, Recall, F1-score, ROC-AUC, Confusion Matrix
- **For segmentation (U-Net)**: IoU (Intersection over Union), Dice coefficient
- **Never report accuracy alone** — HAB events are rare (class imbalance)
