#Requires -Version 5.1
<#
.SYNOPSIS
    Lance les tests Java (JUnit 5) du desktop-app.
.DESCRIPTION
    Par defaut : mvn test (tests unitaires, tag @Tag("ui") exclu via Surefire).
    Avec -Ui    : mvn test -Pui-tests (tests @Tag("ui") seulement, TestFX).
    JaCoCo genere le rapport HTML dans desktop-app/target/site/jacoco/.
.PARAMETER Ui
    Si present, active le profil Maven ui-tests (tests TestFX uniquement).
.EXAMPLE
    .\scripts\test_desktop.ps1
    .\scripts\test_desktop.ps1 -Ui
#>
param(
    [switch]$Ui
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$desktopDir = Join-Path $repoRoot "desktop-app"

Push-Location $desktopDir
try {
    if ($Ui) {
        Write-Host "  > mvn test -Pui-tests [desktop-app -- tests UI TestFX]" -ForegroundColor Cyan
        mvn test -Pui-tests
    } else {
        Write-Host "  > mvn test [desktop-app -- tests unitaires]" -ForegroundColor Cyan
        mvn test
    }
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
