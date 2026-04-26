
Write-Host "Activate..." -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$venvPath = Join-Path $scriptDir "venv\Scripts\Activate.ps1"
$requirementsPath = Join-Path $scriptDir "requirements.txt"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Host "environment doesn't exist. creating..." -ForegroundColor Yellow
    python -m venv (Join-Path $scriptDir "venv")
    
    if (Test-Path $venvPath) {
        & $venvPath
    } else {
        Write-Host "Failed to create or activate virtual environment" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install --upgrade pip

if (Test-Path $requirementsPath) {
    pip install -r $requirementsPath
} else {
    Write-Host "requirements.txt not found at: $requirementsPath" -ForegroundColor Yellow
}

Write-Host "Starting server..." -ForegroundColor Green
Set-Location $scriptDir
uvicorn main:app --reload --host 127.0.0.1 --port 8000
# uvicorn main:app --reload