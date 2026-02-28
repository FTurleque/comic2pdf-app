#Requires -Version 5.1
<#
.SYNOPSIS
    Lance l'application desktop JavaFX Comic2PDF.
.DESCRIPTION
    Exporte ORCHESTRATOR_URL vers http://localhost:18083 (port exposé par Docker)
    puis lance mvn javafx:run dans le module desktop-app.
.NOTES
    Prérequis : stack Docker démarrée (scripts/dev_up.ps1), Java 21, Maven 3.9+.
    ORCHESTRATOR_URL est lu via System.getenv() par l'application.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:ORCHESTRATOR_URL = "http://localhost:18083"
$desktopDir = Join-Path $PSScriptRoot "..\desktop-app"
Set-Location $desktopDir

Write-Host "ORCHESTRATOR_URL=$env:ORCHESTRATOR_URL" -ForegroundColor Cyan
Write-Host "Lancement de l'UI desktop via mvn javafx:run ..." -ForegroundColor Cyan
mvn -q javafx:run

