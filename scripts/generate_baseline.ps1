# Script: generate_baseline.ps1
# Usage: .\scripts\generate_baseline.ps1

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Write-Host "Generating baseline coverage artifacts..."

# Run prep-service tests
Write-Host "Running prep-service tests (pytest)..."
Push-Location "$repoRoot\services\prep-service"
python -m venv .venv 2>$null | Out-Null
# Activate venv if exists (best-effort, tests will run in CI environments with deps)
if (Test-Path .venv\Scripts\Activate.ps1) {
    . .venv\Scripts\Activate.ps1
}
pip install -r requirements-dev.txt
pytest -q --junitxml=../coverage-prep-junit.xml
Pop-Location

# Run ocr-service tests
Write-Host "Running ocr-service tests (pytest)..."
Push-Location "$repoRoot\services\ocr-service"
python -m venv .venv 2>$null | Out-Null
if (Test-Path .venv\Scripts\Activate.ps1) {
    . .venv\Scripts\Activate.ps1
}
pip install -r requirements-dev.txt
pytest -q --junitxml=../coverage-ocr-junit.xml
Pop-Location

# Run orchestrator tests
Write-Host "Running orchestrator tests (pytest)..."
Push-Location "$repoRoot\services\orchestrator"
python -m venv .venv 2>$null | Out-Null
if (Test-Path .venv\Scripts\Activate.ps1) {
    . .venv\Scripts\Activate.ps1
}
pip install -r requirements-dev.txt
pytest -q --junitxml=../coverage-orch-junit.xml
Pop-Location

# Run desktop unit tests (Maven)
Write-Host "Running desktop-app tests (mvn)..."
Push-Location "$repoRoot\desktop-app"
mvn -q test
Pop-Location

Write-Host "Baseline artifacts are in: services/*/coverage.xml, services/*/htmlcov, desktop-app/target/site/jacoco/"
Write-Host "Done."
