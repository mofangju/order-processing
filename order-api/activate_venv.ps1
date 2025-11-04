# Quick activation script for virtual environment (PowerShell)

if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Run setup_venv.ps1 first." -ForegroundColor Red
    exit 1
}

& .\venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated!" -ForegroundColor Green

