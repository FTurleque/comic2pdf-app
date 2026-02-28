#Requires -Version 5.1
<#
.SYNOPSIS
    Lance les tests UI TestFX en mode visuel (affichage requis).
.DESCRIPTION
    Exécute mvn -Pui-tests test dans desktop-app/.
    Lance UNIQUEMENT les tests @Tag("ui").
    Aucun backend Docker requis (stubs HTTP intégrés aux tests).
.NOTES
    Mode headless : utiliser scripts/run_ui_tests_headless.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$desktopDir = Join-Path $PSScriptRoot "..\desktop-app"
Set-Location $desktopDir

Write-Host "Tests UI TestFX (mode visuel) — mvn -Pui-tests test" -ForegroundColor Cyan
mvn -Pui-tests test

