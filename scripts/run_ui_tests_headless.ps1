#Requires -Version 5.1
<#
.SYNOPSIS
    Lance les tests UI TestFX en mode headless (sans affichage).
.DESCRIPTION
    Utilise Monocle pour simuler un affichage.
    Flags : -Dtestfx.headless=true -Dprism.order=sw -Dprism.verbose=true
    Si toujours pas d'affichage, ajouter :
      -Dglass.platform=Monocle -Dmonocle.platform=Headless
    Si InaccessibleObjectException sur com.sun.net.httpserver (rare Java 21), ajouter :
      --add-exports jdk.httpserver/com.sun.net.httpserver=ALL-UNNAMED dans pom.xml argLine ui-tests
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$desktopDir = Join-Path $PSScriptRoot "..\desktop-app"
Set-Location $desktopDir

Write-Host "Tests UI TestFX (mode headless Monocle)" -ForegroundColor Cyan
mvn -Pui-tests test `
    -Dtestfx.headless=true `
    -Dprism.order=sw `
    -Dprism.verbose=true

