#Requires -Version 5.1
<#
.SYNOPSIS
    Lance la stack Docker Comic2PDF en arrière-plan (build + up).
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "docker compose up -d --build ..." -ForegroundColor Cyan
docker compose up -d --build

