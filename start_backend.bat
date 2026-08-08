@echo off
title Backend - Uvicorn Server

cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found, run run_all.bat first
    pause
    exit /b 1
)

echo ============================================
echo   Starting Backend Server...
echo   http://localhost:8000
echo ============================================
echo.

venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
