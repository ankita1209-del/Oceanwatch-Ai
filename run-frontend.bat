@echo off
echo ===================================================
echo Starting OceanWatch AI Frontend (React)
echo URL: http://localhost:3000
echo ===================================================
cd /d "%~dp0frontend"
call npm.cmd run dev
pause

