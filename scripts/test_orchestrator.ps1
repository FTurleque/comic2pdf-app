#Requires -Version 5.1
<#
.SYNOPSIS
    Lance les tests unitaires + couverture de l'orchestrateur.
.DESCRIPTION
    - Cree le venv si absent (py -3 ou python en fallback)
    - Installe les dependances dev (requirements-dev.txt)
    - Lance pytest avec rapport de couverture terminal + XML + HTML
    - Impose un seuil minimal de couverture (PY_COV_MIN, défaut: 60%)
    Sorties : services/orchestrator/coverage.xml
              services/orchestrator/htmlcov/
.PARAMETER CovMin
    Seuil minimal de couverture (%). Défaut: 60 (env: PY_COV_MIN).
.EXAMPLE
    .\scripts\test_orchestrator.ps1
    .\scripts\test_orchestrator.ps1 -CovMin 65
#>
[CmdletBinding()]
param(
    [int]$CovMin = [int]($env:PY_COV_MIN -or 60)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$serviceDir = Join-Path $repoRoot "services\orchestrator"

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
    Write-Host "  > pytest [orchestrator] (seuil couverture: $CovMin%)" -ForegroundColor Cyan
    & $py -m pytest -q --tb=short `
        --cov=app `
        --cov-report=term `
        --cov-report=term-missing `
        "--cov-report=xml:coverage.xml" `
        "--cov-report=html:htmlcov" `
        "--cov-fail-under=$CovMin" `
        tests
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
