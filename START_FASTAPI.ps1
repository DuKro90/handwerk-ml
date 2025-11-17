# FastAPI Local Startup Script for Windows PowerShell
# No Docker required!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "HandwerkML FastAPI - Local Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Host "[1/3] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "      $pythonVersion" -ForegroundColor Green

# Step 2: Install dependencies
Write-Host "[2/3] Installing dependencies..." -ForegroundColor Yellow
pip install -q -r requirements_fastapi.txt 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "      [OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "      [ERROR] Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Step 3: Start FastAPI
Write-Host "[3/3] Starting FastAPI Server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FastAPI is starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Once started, open in browser:" -ForegroundColor Yellow
Write-Host "  http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop the server, press Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Start FastAPI with uvicorn
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
