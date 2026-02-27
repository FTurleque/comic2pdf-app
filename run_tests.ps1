#Requires -Version 5.1
<#
.SYNOPSIS
    Lance tous les tests du projet comic2pdf-app (Python + Java).

.DESCRIPTION
    Pour chaque service Python (prep-service, ocr-service, orchestrator) :
      - Installe les dépendances dev (pip install -r requirements-dev.txt)
      - Lance pytest -q

    Puis pour le module Java :
      - Lance mvn test dans desktop-app/

    Affiche un résumé coloré et retourne un exit code non-zero si un lot échoue.

.NOTES
    Prérequis :
      - Python 3.12 disponible dans le PATH (commande python ou python3)
      - pip disponible
      - Maven 3.9+ disponible dans le PATH
      - Java 21 disponible dans le PATH

    Recommandation : créer un venv par service avant de lancer ce script.
    Voir la section "Tests locaux" du README.md pour les instructions.

.EXAMPLE
    .\run_tests.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Results = @()
$GlobalFailed = $false

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Header([string]$title) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-ResultLine([string]$label, [bool]$ok) {
    $status = if ($ok) { "PASS" } else { "FAIL" }
    $color  = if ($ok) { "Green" } else { "Red" }
    Write-Host ("  {0,-40} [{1}]" -f $label, $status) -ForegroundColor $color
}

function Invoke-PythonTests([string]$serviceDir, [string]$serviceName) {
    Write-Header "Tests Python : $serviceName"
    Push-Location $serviceDir
    $ok = $true
    try {
        # Installation des dépendances dev
        Write-Host "  > pip install -q -r requirements-dev.txt" -ForegroundColor Gray
        & python -m pip install -q -r requirements-dev.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ERREUR : pip install a echoue (rc=$LASTEXITCODE)" -ForegroundColor Red
            $ok = $false
        } else {
            # Lancement de pytest
            Write-Host "  > pytest -q" -ForegroundColor Gray
            & python -m pytest -q
            if ($LASTEXITCODE -ne 0) {
                $ok = $false
            }
        }
    } catch {
        Write-Host "  EXCEPTION : $_" -ForegroundColor Red
        $ok = $false
    } finally {
        Pop-Location
    }
    return $ok
}

function Invoke-MavenTests([string]$moduleDir, [string]$moduleName) {
    Write-Header "Tests Java : $moduleName"
    Push-Location $moduleDir
    $ok = $true
    try {
        Write-Host "  > mvn -q test" -ForegroundColor Gray
        & mvn -q test
        if ($LASTEXITCODE -ne 0) {
            $ok = $false
        }
    } catch {
        Write-Host "  EXCEPTION : $_" -ForegroundColor Red
        $ok = $false
    } finally {
        Pop-Location
    }
    return $ok
}

# ---------------------------------------------------------------------------
# Services Python
# ---------------------------------------------------------------------------

$pythonServices = @(
    @{ Name = "prep-service";   Dir = Join-Path $Root "services\prep-service"  },
    @{ Name = "ocr-service";    Dir = Join-Path $Root "services\ocr-service"   },
    @{ Name = "orchestrator";   Dir = Join-Path $Root "services\orchestrator"  }
)

foreach ($svc in $pythonServices) {
    $passed = Invoke-PythonTests -serviceDir $svc.Dir -serviceName $svc.Name
    $Results += [PSCustomObject]@{ Label = $svc.Name; Ok = [bool]$passed }
    if (-not $passed) { $GlobalFailed = $true }
}

# ---------------------------------------------------------------------------
# Module Java
# ---------------------------------------------------------------------------

$javaOk = Invoke-MavenTests -moduleDir (Join-Path $Root "desktop-app") -moduleName "desktop-app (JUnit 5)"
$Results += [PSCustomObject]@{ Label = "desktop-app (JUnit 5)"; Ok = [bool]$javaOk }
if (-not $javaOk) { $GlobalFailed = $true }

# ---------------------------------------------------------------------------
# Résumé
# ---------------------------------------------------------------------------

Write-Header "RESUME"
foreach ($r in $Results) {
    Write-ResultLine -label $r.Label -ok $r.Ok
}
Write-Host ""

if ($GlobalFailed) {
    Write-Host "  RESULTAT GLOBAL : ECHEC" -ForegroundColor Red
    Write-Host ""
    exit 1
} else {
    Write-Host "  RESULTAT GLOBAL : SUCCES" -ForegroundColor Green
    Write-Host ""
    exit 0
}



