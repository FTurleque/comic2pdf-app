#Requires -Version 5.1
<#
.SYNOPSIS
    Lance tous les tests du projet comic2pdf-app (Python + Java).
.DESCRIPTION
    Enchaine les 4 scripts de test individuels :
      1. scripts/test_prep.ps1           -- pytest + coverage (prep-service)
      2. scripts/test_ocr.ps1            -- pytest + coverage (ocr-service)
      3. scripts/test_orchestrator.ps1   -- pytest + coverage (orchestrator)
      4. scripts/test_desktop.ps1        -- mvn test (desktop-app, sans UI)

    Par defaut : s'arrete au premier echec (comportement CI).
    Avec -ContinueOnError : execute tout et affiche un resume final.

.PARAMETER ContinueOnError
    Si present, continue meme en cas d'echec intermediaire et affiche
    un resume PASS/FAIL a la fin.

.EXAMPLE
    .\scripts\test_all.ps1
    .\scripts\test_all.ps1 -ContinueOnError

.NOTES
    Rapports de couverture Python generes dans chaque service :
      services/<service>/coverage.xml
      services/<service>/htmlcov/index.html
    Rapport JaCoCo Java :
      desktop-app/target/site/jacoco/index.html
#>
param(
    [switch]$ContinueOnError
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$failures = [System.Collections.Generic.List[string]]::new()

function Write-Header([string]$title) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Run-Step {
    param([string]$Name, [string]$ScriptPath)
    Write-Header $Name
    & $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        $failures.Add($Name)
        if (-not $ContinueOnError) {
            Write-Host ""
            Write-Host "  ECHEC : $Name (exit $LASTEXITCODE)" -ForegroundColor Red
            Write-Host "  Arret. Utiliser -ContinueOnError pour tout executer." -ForegroundColor Yellow
            exit 1
        }
    }
}

# ---------------------------------------------------------------------------
# Execution sequentielle
# ---------------------------------------------------------------------------
Run-Step "prep-service"          "$PSScriptRoot\test_prep.ps1"
Run-Step "ocr-service"           "$PSScriptRoot\test_ocr.ps1"
Run-Step "orchestrator"          "$PSScriptRoot\test_orchestrator.ps1"
Run-Step "desktop-app (mvn)"     "$PSScriptRoot\test_desktop.ps1"

# ---------------------------------------------------------------------------
# Resume final (toujours affiche, surtout utile avec -ContinueOnError)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  RESUME GLOBAL" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

$all = @("prep-service", "ocr-service", "orchestrator", "desktop-app (mvn)")
foreach ($step in $all) {
    if ($failures -contains $step) {
        Write-Host ("  {0,-40} [FAIL]" -f $step) -ForegroundColor Red
    } else {
        Write-Host ("  {0,-40} [PASS]" -f $step) -ForegroundColor Green
    }
}
Write-Host ""

if ($failures.Count -gt 0) {
    Write-Host "  RESULTAT GLOBAL : ECHEC ($($failures -join ', '))" -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host "  RESULTAT GLOBAL : SUCCES" -ForegroundColor Green
Write-Host ""
exit 0

