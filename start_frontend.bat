@echo off
title Frontend - Vite Dev Server

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo [ERROR] node_modules not found, please run: npm install
    pause
    exit /b 1
)

echo ============================================
echo   Starting Frontend Dev Server...
echo   http://localhost:5173
echo ============================================
echo.

echo [INFO] Clearing Vite cache...
if exist "node_modules\.vite" (
    rmdir /s /q "node_modules\.vite"
    echo [INFO] Cache cleared.
)

echo.
echo [INFO] Starting Vite...
call npx vite --host

pause
