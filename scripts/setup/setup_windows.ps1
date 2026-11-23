# One-time setup for running the project without Docker on Windows (PowerShell).
# Needs Python 3.10+ and Node.js 20+.   Run from the project folder:   powershell -ExecutionPolicy Bypass -File scripts\setup\setup_windows.ps1
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

# $ErrorActionPreference does not stop the script when a program such as pip or npm fails, so check each exit code.
function Assert-Ok([string]$What) {
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit code $LASTEXITCODE). Fix the message above and run the script again." }
}

Write-Host "==> Python environment (.venv)"
python -m venv .venv
Assert-Ok "Creating the Python environment (is Python 3.10 or newer on PATH? try: python --version)"
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
Assert-Ok "Upgrading pip"
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt
Assert-Ok "Installing the Python packages"

Write-Host "==> Settings (.env)"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Write-Host "==> Database"
Push-Location backend
& ..\.venv\Scripts\python.exe -m app.db.migrate
Assert-Ok "Creating the database"
Pop-Location

Write-Host "==> Frontend packages"
Push-Location frontend
npm ci
Assert-Ok "Installing the front-end packages (is Node.js 20.19 or newer installed? try: node --version)"
Pop-Location

Write-Host ""
Write-Host "Setup finished. Two more steps:"
Write-Host "  1. Train the text model (10 to 20 minutes, needs internet once):  scripts\training\train_text_model.ps1"
Write-Host "  2. Start the app in two terminals:  scripts\run_backend.ps1   and   scripts\run_frontend.ps1"
