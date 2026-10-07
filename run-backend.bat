@echo off
echo ===================================================
echo Starting OceanWatch AI Backend (FastAPI)
echo URL: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo ===================================================
cd /d "%~dp0"
set "PYTHONPATH=%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
) else if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
) else (
    python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
)
pause


