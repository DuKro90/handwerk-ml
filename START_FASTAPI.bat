@echo off
REM FastAPI Local Startup - Double-click to run!

cd /d "%~dp0"

echo ========================================
echo HandwerkML FastAPI - Local Startup
echo ========================================
echo.

echo [1/3] Checking Python...
python --version

echo [2/3] Installing dependencies...
pip install -q -r requirements_fastapi.txt
if %ERRORLEVEL% EQU 0 (
    echo      [OK] Dependencies installed
) else (
    echo      [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [3/3] Starting FastAPI Server...
echo.
echo ========================================
echo FastAPI is starting...
echo ========================================
echo.
echo Once started, open in browser:
echo   http://localhost:8001/docs
echo.
echo To stop the server, close this window or press Ctrl+C
echo.

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001

pause
