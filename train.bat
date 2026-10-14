@echo off
REM ============================================================
REM  OceanWatch AI — Full Model Training Pipeline
REM  Runs:
REM    Step 1 - Build features.csv from HABSOS observations
REM    Step 2 - Train Model B: XGBoost HAB risk prediction
REM    Step 3 - Train Model A: CNN HAB image detector
REM ============================================================

echo.
echo ============================================================
echo  OceanWatch AI - Training Pipeline
echo ============================================================

REM -- Activate virtual environment if it exists -----------------
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating .venv...
    call .venv\Scripts\activate.bat
) else if exist ".venv-1\Scripts\activate.bat" (
    echo [INFO] Activating .venv-1...
    call .venv-1\Scripts\activate.bat
) else (
    echo [WARN] No virtual environment found. Using system Python.
)

echo.
echo ============================================================
echo  STEP 1: Building features.csv from HABSOS observations
echo ============================================================
python scripts\build_features_from_habsos.py ^
    --input  data\processed\habsos_observations.csv ^
    --output data\processed\features.csv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Feature building failed. Aborting.
    exit /b 1
)

echo.
echo ============================================================
echo  STEP 2: Training Model B - XGBoost HAB Risk Prediction
echo ============================================================
python src\hab_model.py data\processed\features.csv ^
    --training-context "NOAA HABSOS cell-count observations 2026; auto-labeled from CATEGORY field" ^
    --model    models\prediction\xgboost_model.pkl ^
    --metadata models\prediction\model_metadata.json
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] XGBoost training failed. Aborting.
    exit /b 1
)

echo.
echo ============================================================
echo  STEP 3: Training Model A - CNN HAB Image Detector
echo ============================================================
python scripts\train_cnn_model.py ^
    --images    data\images ^
    --model     models\detection\model.pt ^
    --metadata  models\detection\model_metadata.json ^
    --epochs    20 ^
    --batch-size 8
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] CNN training failed.
    exit /b 1
)

echo.
echo ============================================================
echo  Training complete!
echo  Models saved to:
echo    models\prediction\xgboost_model.pkl
echo    models\detection\model.pt
echo  Metadata:
echo    models\prediction\model_metadata.json
echo    models\detection\model_metadata.json
echo ============================================================
pause
