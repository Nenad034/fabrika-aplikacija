@echo off
TITLE AI Factory Launcher
echo ==========================================
echo      AI FACTORY - STARTING SYSTEM
echo ==========================================
echo.

:: 1. Start Python Backend
echo [1/3] Starting Python API Server...
start "AI Factory Backend" cmd /k "python api.py"

:: 2. Start Frontend Dev Server
echo [2/3] Starting UI Interface...
cd ui
start "AI Factory UI" cmd /k "npm run dev -- --host"

:: 3. Open Browser
echo [3/3] Opening Browser...
timeout /t 5 >nul
start http://localhost:5173

echo.
echo SUCCESS! System is running.
echo You can close this window, but keep the other two open.
timeout /t 10
