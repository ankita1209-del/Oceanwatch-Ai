@echo off
echo ===================================================
echo Starting OceanWatch AI Backend (FastAPI)
echo URL: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo ===================================================
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
