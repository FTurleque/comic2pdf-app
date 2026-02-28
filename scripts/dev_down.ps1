#Requires -Version 5.1
<# .SYNOPSIS Arrête la stack Docker Comic2PDF. #>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
docker compose down

