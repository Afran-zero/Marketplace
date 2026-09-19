# Starts Prefect UI + FastAPI + React in three separate windows.
# Usage: .\run_dashboard.ps1

$ProjectRoot = "G:\data-Engineer\marketplus"

Write-Host "Starting Prefect server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& { Set-Location '$ProjectRoot'; & '$ProjectRoot\.venv\Scripts\Activate.ps1'; `$env:PREFECT_API_URL = 'http://127.0.0.1:4200/api'; `$env:PREFECT_SERVER_EPHEMERAL_ENABLED = 'false'; python -m prefect server start --host 127.0.0.1 --port 4200 }"
)

Write-Host "Starting FastAPI backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& { Set-Location '$ProjectRoot'; & '$ProjectRoot\.venv\Scripts\Activate.ps1'; `$env:PREFECT_API_URL = 'http://127.0.0.1:4200/api'; `$env:PREFECT_SERVER_EPHEMERAL_ENABLED = 'false'; python -m uvicorn backend.main:app --port 8000 }"
)

Write-Host "Starting React frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& { Set-Location '$ProjectRoot\frontend'; npm run dev -- --strictPort }"
)

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " All services starting in separate windows" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Prefect UI:  http://127.0.0.1:4200"
Write-Host " FastAPI:     http://127.0.0.1:8000"
Write-Host " Dashboard:   http://localhost:5173"
Write-Host ""
Write-Host " To stop: close each window, or Ctrl+C in each."
