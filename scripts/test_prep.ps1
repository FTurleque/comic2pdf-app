#Requires -Version 5.1
<#
.SYNOPSIS
    Lance les tests unitaires + couverture du prep-service.
.DESCRIPTION
    - Cree le venv si absent (py -3 ou python en fallback)
    - Installe les dependances dev (requirements-dev.txt)
    - Lance pytest avec rapport de couverture terminal + XML + HTML
    Sorties : services/prep-service/coverage.xml
              services/prep-service/htmlcov/
.EXAMPLE
    .\scripts\test_prep.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$serviceDir = Join-Path $repoRoot "services\prep-service"

Push-Location $serviceDir
try {
    # --- Creer le venv si absent ---
    if (-not (Test-Path ".venv")) {
        Write-Host "  > Creation du venv (.venv)..." -ForegroundColor Gray
        if (Get-Command py -ErrorAction SilentlyContinue) {
            py -3 -m venv .venv
        } else {
            python -m venv .venv
        }
    }

    $py = ".venv\Scripts\python.exe"

    # --- Dependances dev ---
    Write-Host "  > pip install -r requirements-dev.txt" -ForegroundColor Gray
    & $py -m pip install -q -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # --- Tests + couverture ---
    Write-Host "  > pytest [prep-service]" -ForegroundColor Cyan
    & $py -m pytest -q --tb=short `
        --cov=app `
        --cov-report=term-missing `
        "--cov-report=xml:coverage.xml" `
        "--cov-report=html:htmlcov" `
        tests
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
